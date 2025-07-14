#!/usr/bin/env python3
"""
FastAPI 測試啟動腳本
用於測試基礎 API 服務是否正常運行
"""

import asyncio
import sys
import os
import uvicorn
import logging

# 添加 src 目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_basic_functionality():
    """測試基本功能"""
    try:
        # 測試配置加載
        from api.config import get_settings
        settings = get_settings()
        logger.info(f"✅ 配置加載成功 - 環境: {settings.ENVIRONMENT}")
        
        # 測試資料庫連接
        from api.database import test_database_connection
        db_ok = await test_database_connection()
        if db_ok:
            logger.info("✅ 資料庫連接測試成功")
        else:
            logger.error("❌ 資料庫連接測試失敗")
        
        # 測試 Redis 連接
        from api.cache import get_redis_health
        redis_status = await get_redis_health()
        logger.info(f"Redis 狀態: {redis_status}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 基本功能測試失敗: {e}")
        return False


def main():
    """主函數"""
    logger.info("🚀 Model API 監控系統測試啟動...")
    
    # 測試基本功能
    try:
        test_result = asyncio.run(test_basic_functionality())
        if not test_result:
            logger.error("基本功能測試失敗，請檢查配置")
            return
    except Exception as e:
        logger.error(f"測試過程中發生錯誤: {e}")
        return
    
    # 啟動 FastAPI 服務
    try:
        from api.main import app
        from api.config import get_settings
        
        settings = get_settings()
        
        logger.info(f"📡 啟動 FastAPI 服務...")
        logger.info(f"🌐 服務地址: http://{settings.API_HOST}:{settings.API_PORT}")
        logger.info(f"📚 API 文檔: http://{settings.API_HOST}:{settings.API_PORT}/docs")
        logger.info(f"🔍 健康檢查: http://{settings.API_HOST}:{settings.API_PORT}/health")
        
        uvicorn.run(
            app,
            host=settings.API_HOST,
            port=settings.API_PORT,
            reload=settings.DEBUG,
            log_level="info"
        )
        
    except Exception as e:
        logger.error(f"❌ 啟動 FastAPI 服務失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 