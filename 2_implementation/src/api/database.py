"""
資料庫連接管理模組
使用 SQLAlchemy 管理 PostgreSQL + TimescaleDB 連接
"""

import asyncio
import logging
from typing import AsyncGenerator, Optional
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from .config import get_settings

logger = logging.getLogger(__name__)

# 全域變數
async_engine = None
async_session_factory = None
sync_engine = None

class Base(DeclarativeBase):
    """SQLAlchemy 基礎模型類別"""
    metadata = MetaData()


async def init_database():
    """初始化資料庫連接"""
    global async_engine, async_session_factory, sync_engine
    
    try:
        settings = get_settings()
        
        # 將 postgresql:// 轉換為 postgresql+asyncpg://
        async_database_url = settings.DATABASE_URL.replace(
            "postgresql://", "postgresql+asyncpg://"
        )
        
        # 創建異步引擎
        async_engine = create_async_engine(
            async_database_url,
            echo=settings.DEBUG,
            poolclass=NullPool if settings.DEBUG else None,
            pool_pre_ping=True,
        )
        
        # 創建異步會話工廠
        async_session_factory = async_sessionmaker(
            async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        # 創建同步引擎 (用於某些操作)
        sync_engine = create_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_pre_ping=True,
        )
        
        logger.info("✅ 資料庫連接初始化成功")
        
    except Exception as e:
        logger.error(f"❌ 資料庫連接初始化失敗: {e}")
        raise


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    獲取異步資料庫會話
    用於 FastAPI 依賴注入
    """
    if async_session_factory is None:
        await init_database()
    
    async with async_session_factory() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"資料庫會話錯誤: {e}")
            raise
        finally:
            await session.close()


def get_sync_session():
    """
    獲取同步資料庫會話
    用於某些需要同步操作的場景
    """
    if sync_engine is None:
        raise RuntimeError("資料庫未初始化")
    
    Session = sessionmaker(bind=sync_engine)
    return Session()


async def get_db_health() -> str:
    """
    檢查資料庫健康狀態
    返回: "healthy", "unhealthy", "unknown"
    """
    try:
        if async_engine is None:
            await init_database()
        
        # 使用異步連接測試
        async with async_engine.connect() as conn:
            # 執行簡單查詢
            result = await conn.execute(text("SELECT 1 as health_check"))
            row = result.fetchone()
            
            if row and row[0] == 1:
                # 檢查 TimescaleDB 擴展
                ts_result = await conn.execute(
                    text("SELECT extname FROM pg_extension WHERE extname = 'timescaledb'")
                )
                ts_row = ts_result.fetchone()
                
                if ts_row:
                    logger.debug("✅ PostgreSQL + TimescaleDB 健康檢查通過")
                    return "healthy"
                else:
                    logger.warning("⚠️ TimescaleDB 擴展未找到")
                    return "healthy"  # PostgreSQL 本身是健康的
            else:
                return "unhealthy"
                
    except Exception as e:
        logger.error(f"❌ 資料庫健康檢查失敗: {e}")
        return "unhealthy"


async def test_database_connection():
    """測試資料庫連接並顯示基本資訊"""
    try:
        if async_engine is None:
            await init_database()
        
        async with async_engine.connect() as conn:
            # 測試基本連接
            result = await conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"PostgreSQL 版本: {version}")
            
            # 檢查 TimescaleDB
            ts_result = await conn.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'")
            )
            ts_row = ts_result.fetchone()
            
            if ts_row:
                logger.info(f"TimescaleDB 版本: {ts_row[0]}")
            else:
                logger.warning("TimescaleDB 擴展未安裝")
            
            # 檢查監控相關表
            tables_result = await conn.execute(
                text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('metrics_aggregated', 'alert_rules', 'service_info')
                """)
            )
            
            existing_tables = [row[0] for row in tables_result.fetchall()]
            logger.info(f"現有監控表: {existing_tables}")
            
            return True
            
    except Exception as e:
        logger.error(f"資料庫連接測試失敗: {e}")
        return False


async def close_database():
    """關閉資料庫連接"""
    global async_engine, sync_engine
    
    try:
        if async_engine:
            await async_engine.dispose()
            logger.info("✅ 異步資料庫連接已關閉")
        
        if sync_engine:
            sync_engine.dispose()
            logger.info("✅ 同步資料庫連接已關閉")
            
    except Exception as e:
        logger.error(f"❌ 關閉資料庫連接時發生錯誤: {e}")


# 資料庫模型定義 (基於設計文檔)
from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, TIMESTAMP, UUID, Text, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

class MetricsAggregated(Base):
    """聚合指標表"""
    __tablename__ = "metrics_aggregated"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    window_start = Column(TIMESTAMP(timezone=True), nullable=False)
    window_end = Column(TIMESTAMP(timezone=True), nullable=False)
    service_name = Column(String(255), nullable=True)
    endpoint = Column(String(255), nullable=True)  # 實際欄位名稱
    metric_type = Column(String(50), nullable=False)
    qps = Column(DECIMAL(10, 2), nullable=True, default=0)
    error_rate = Column(DECIMAL(5, 2), nullable=True, default=0)
    avg_response_time = Column(DECIMAL(10, 2), nullable=True, default=0)  # 實際欄位名稱
    p95_response_time = Column(DECIMAL(10, 2), nullable=True, default=0)  # 實際欄位名稱
    p99_response_time = Column(DECIMAL(10, 2), nullable=True, default=0)  # 實際欄位名稱
    total_requests = Column(Integer, nullable=True, default=0)
    total_errors = Column(Integer, nullable=True, default=0)
    additional_data = Column(JSONB, nullable=True)  # JSONB 欄位
    created_at = Column(TIMESTAMP(timezone=True), nullable=True, default=func.now())


class AlertRules(Base):
    """告警規則表"""
    __tablename__ = "alert_rules"
    
    id = Column(UUID, primary_key=True)
    name = Column(String(200), nullable=False)
    service_name = Column(String(100), nullable=False)
    metric = Column(String(50), nullable=False)
    threshold = Column(DECIMAL(10, 2), nullable=False)
    operator = Column(String(20), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())


class ServiceInfo(Base):
    """服務資訊表"""
    __tablename__ = "service_info"
    
    service_name = Column(String(100), primary_key=True)
    display_name = Column(String(200))
    endpoints = Column(ARRAY(Text))
    status = Column(String(20), nullable=False, default='unknown')
    last_seen = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    monitoring_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=func.now()) 