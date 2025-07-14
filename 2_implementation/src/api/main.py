"""
Model API 監控系統 - FastAPI 主程式
版本: v1.0
創建時間: 2025-07-01
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .config import get_settings
from .database import get_db_health, init_database
from .cache import get_redis_health
from .dependencies import verify_api_key

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    logger.info("🚀 Model API 監控系統啟動中...")
    
    # 初始化資料庫連接
    await init_database()
    
    # 初始化 AsyncPG 連接池
    from .dependencies import init_db_pool
    await init_db_pool()
    
    # 初始化 Redis 連接
    try:
        from .cache import init_redis
        await init_redis()
        logger.info("✅ Redis 連接初始化成功")
    except Exception as e:
        logger.error(f"❌ Redis 連接初始化失敗: {e}")
    
    logger.info("✅ 系統啟動完成")
    yield
    
    logger.info("🛑 系統正在關閉...")
    
    # 清理資源
    from .dependencies import close_db_pool
    await close_db_pool()
    
    # 關閉 Redis 連接
    try:
        from .cache import close_redis
        await close_redis()
        logger.info("✅ Redis 連接已關閉")
    except Exception as e:
        logger.error(f"❌ 關閉 Redis 連接失敗: {e}")

# 創建 FastAPI 應用程式
app = FastAPI(
    title="Model API 監控系統",
    description="即時監控機器學習模型 API 的性能與狀態",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Vue.js 開發服務器
        "http://localhost:8080",  # 替代前端端口
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/", tags=["根目錄"])
async def root():
    """API 根目錄"""
    return {
        "message": "Model API 監控系統",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health", tags=["系統健康"])
async def health_check() -> Dict[str, Any]:
    """
    系統健康檢查端點
    檢查所有依賴服務的狀態
    """
    try:
        settings = get_settings()
        
        # 檢查資料庫健康狀態
        db_status = await get_db_health()
        
        # 檢查 Redis 健康狀態  
        redis_status = await get_redis_health()
        
        # 整體健康狀態
        all_healthy = db_status == "healthy" and redis_status == "healthy"
        
        health_data = {
            "status": "healthy" if all_healthy else "unhealthy",
            "version": "1.0.0",
            "uptime_seconds": 0,  # TODO: 實現運行時間計算
            "dependencies": {
                "postgresql": db_status,
                "redis": redis_status,
                "rabbitmq": "unknown"  # TODO: 實現 RabbitMQ 健康檢查
            },
            "environment": settings.ENVIRONMENT
        }
        
        if not all_healthy:
            raise HTTPException(status_code=503, detail="服務不健康")
            
        return {
            "success": True,
            "data": health_data,
            "timestamp": "2025-07-01T10:30:00Z"  # TODO: 實現動態時間戳
        }
        
    except Exception as e:
        logger.error(f"健康檢查失敗: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "success": False,
                "error": {
                    "code": "HEALTH_CHECK_FAILED",
                    "message": "系統健康檢查失敗",
                    "developer_message": str(e)
                },
                "timestamp": "2025-07-01T10:30:00Z"
            }
        )

# 註冊 API 路由
try:
    from .routers import (
        metrics_router,
        alerts_router,
        services_router,
        dashboards_router,
        realtime_router
    )
    
    app.include_router(metrics_router)
    app.include_router(alerts_router)
    app.include_router(services_router)
    app.include_router(dashboards_router)
    app.include_router(realtime_router)
    
    logger.info("✅ API 路由註冊成功")
except ImportError as e:
    logger.warning(f"⚠️ 部分 API 路由未找到: {e}")

# API v1 路由群組
@app.get("/v1", tags=["API v1"])
async def api_v1_info():
    """API v1 資訊"""
    return {
        "version": "v1",
        "endpoints": {
            "health": "/health",
            "metrics": "/v1/metrics/*",
            "alerts": "/v1/alerts/*", 
            "services": "/v1/services/*",
            "dashboards": "/v1/dashboards/*"
        },
        "available_routes": [
            "/v1/metrics/summary",
            "/v1/metrics/historical", 
            "/v1/metrics/real-time",
            "/v1/metrics/services",
            "/v1/alerts/",
            "/v1/alerts/active",
            "/v1/services/",
            "/v1/dashboards/overview",
            "/v1/dashboards/metrics/timeseries",
            "/v1/dashboards/realtime"
        ],
        "websocket_endpoints": [
            "/v1/ws/metrics",
            "/v1/ws/alerts"
        ]
    }

# 受保護的示範端點
@app.get("/v1/protected", tags=["API v1"], dependencies=[Depends(verify_api_key)])
async def protected_endpoint():
    """需要 API Key 認證的示範端點"""
    return {
        "success": True,
        "data": {
            "message": "您已成功通過 API Key 認證",
            "access_level": "read"
        },
        "timestamp": "2025-07-01T10:30:00Z"
    }

# 錯誤處理器
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """統一 HTTP 錯誤回應格式"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail if isinstance(exc.detail, str) else "請求錯誤",
                "developer_message": str(exc.detail)
            },
            "timestamp": "2025-07-01T10:30:00Z"
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全域異常處理器"""
    logger.error(f"未處理的異常: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "內部伺服器錯誤",
                "developer_message": "請聯繫系統管理員"
            },
            "timestamp": "2025-07-01T10:30:00Z"
        }
    )

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "src.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level="info"
    ) 