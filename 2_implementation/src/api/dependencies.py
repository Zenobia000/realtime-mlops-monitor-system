"""
FastAPI 依賴注入模組
定義通用的依賴注入函數
"""

import logging
from typing import Annotated
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import get_settings
from .database import get_async_session, AsyncSession
from .cache import get_redis_client
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# HTTP Bearer 認證方案 (可選使用)
security = HTTPBearer(auto_error=False)


async def verify_api_key(
    x_api_key: Annotated[str, Header(alias="X-API-Key")] = None,
    authorization: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    驗證 API Key
    支持兩種認證方式:
    1. Header: X-API-Key
    2. Bearer Token: Authorization: Bearer <api_key>
    """
    settings = get_settings()
    provided_key = None
    
    # 方式1: X-API-Key Header
    if x_api_key:
        provided_key = x_api_key
        auth_method = "Header"
    
    # 方式2: Bearer Token
    elif authorization and authorization.scheme.lower() == "bearer":
        provided_key = authorization.credentials
        auth_method = "Bearer"
    
    # 沒有提供任何認證
    if not provided_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": "MISSING_API_KEY",
                    "message": "需要 API Key 認證",
                    "developer_message": "請在 Header 中提供 X-API-Key 或使用 Bearer Token"
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 驗證 API Key
    if provided_key != settings.API_KEY:
        logger.warning(f"無效的 API Key 嘗試: {provided_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "error": {
                    "code": "INVALID_API_KEY",
                    "message": "無效的 API Key",
                    "developer_message": "請檢查您的 API Key 是否正確"
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.debug(f"✅ API Key 認證成功 (方式: {auth_method})")
    return provided_key


async def get_current_user(api_key: str = Depends(verify_api_key)) -> dict:
    """
    獲取當前用戶資訊
    基於 API Key 返回用戶資訊
    """
    # TODO: 實現用戶系統後，根據 API Key 查詢用戶資訊
    return {
        "api_key": api_key[:8] + "...",  # 遮罩 API Key
        "permissions": ["read"],  # MVP 版本只有讀取權限
        "user_type": "monitor_user"
    }


# 資料庫會話依賴
DatabaseSession = Annotated[AsyncSession, Depends(get_async_session)]


# Redis 客戶端依賴
RedisClient = Annotated[redis.Redis, Depends(get_redis_client)]


# API Key 認證依賴
APIKeyAuth = Annotated[str, Depends(verify_api_key)]


# 當前用戶依賴
CurrentUser = Annotated[dict, Depends(get_current_user)]


def require_permissions(required_permissions: list[str]):
    """
    需要特定權限的依賴注入裝飾器
    
    Args:
        required_permissions: 需要的權限列表
        
    Returns:
        依賴注入函數
    """
    async def check_permissions(current_user: CurrentUser):
        user_permissions = current_user.get("permissions", [])
        
        # 檢查是否有所需權限
        for permission in required_permissions:
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "success": False,
                        "error": {
                            "code": "INSUFFICIENT_PERMISSIONS",
                            "message": f"需要 {permission} 權限",
                            "developer_message": f"當前用戶權限: {user_permissions}, 需要權限: {required_permissions}"
                        }
                    }
                )
        
        return current_user
    
    return check_permissions


# 常用權限檢查依賴
RequireReadPermission = Depends(require_permissions(["read"]))
RequireWritePermission = Depends(require_permissions(["write"]))
RequireAdminPermission = Depends(require_permissions(["admin"]))


class RateLimiter:
    """
    簡單的速率限制器 (基於 Redis)
    """
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    async def __call__(
        self, 
        x_api_key: APIKeyAuth,
        redis_client: RedisClient
    ):
        """
        檢查速率限制
        """
        # 使用 API Key 作為限制標識
        rate_limit_key = f"rate_limit:{x_api_key[:16]}"
        
        try:
            # 獲取當前請求數
            current_requests = await redis_client.get(rate_limit_key)
            
            if current_requests is None:
                # 第一次請求，設置初始值
                await redis_client.setex(rate_limit_key, self.window_seconds, 1)
                remaining = self.max_requests - 1
            else:
                current_count = int(current_requests)
                
                if current_count >= self.max_requests:
                    # 超過限制
                    ttl = await redis_client.ttl(rate_limit_key)
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail={
                            "success": False,
                            "error": {
                                "code": "RATE_LIMIT_EXCEEDED",
                                "message": "請求頻率超過限制",
                                "developer_message": f"每 {self.window_seconds} 秒最多 {self.max_requests} 次請求"
                            }
                        },
                        headers={
                            "X-RateLimit-Limit": str(self.max_requests),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(ttl),
                            "Retry-After": str(ttl)
                        }
                    )
                
                # 增加請求計數
                await redis_client.incr(rate_limit_key)
                remaining = self.max_requests - current_count - 1
            
            logger.debug(f"速率限制檢查通過，剩餘請求數: {remaining}")
            return {
                "limit": self.max_requests,
                "remaining": remaining,
                "window_seconds": self.window_seconds
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"速率限制檢查失敗: {e}")
            # 如果速率限制檢查失敗，允許請求通過（優雅降級）
            return {
                "limit": self.max_requests,
                "remaining": self.max_requests,
                "window_seconds": self.window_seconds
            }


# 預定義的速率限制器
DefaultRateLimit = RateLimiter(max_requests=300, window_seconds=60)  # 每分鐘 300 次
StrictRateLimit = RateLimiter(max_requests=60, window_seconds=60)    # 每分鐘 60 次
ApiRateLimit = Annotated[dict, Depends(DefaultRateLimit)]


def get_pagination_params(
    offset: int = 0,
    limit: int = 50
) -> dict:
    """
    分頁參數依賴注入
    
    Args:
        offset: 偏移量 (預設 0)
        limit: 每頁數量 (預設 50，最大 1000)
        
    Returns:
        分頁參數字典
    """
    # 限制最大分頁大小
    if limit > 1000:
        limit = 1000
    
    if limit < 1:
        limit = 1
    
    if offset < 0:
        offset = 0
    
    return {
        "offset": offset,
        "limit": limit
    }


# 分頁依賴
PaginationParams = Annotated[dict, Depends(get_pagination_params)]


# 額外的資料庫和 Redis 依賴函數
async def get_db_connection():
    """
    獲取資料庫連接
    (為兼容性保留，實際使用 get_async_session)
    """
    async for session in get_async_session():
        yield session


async def get_redis_connection():
    """
    獲取 Redis 連接
    (為兼容性保留，實際使用 get_redis_client)
    """
    return await get_redis_client()


# 新的 asyncpg 池連接依賴 (用於原生 SQL 查詢)
import asyncpg
from typing import Optional

_db_pool: Optional[asyncpg.Pool] = None

async def init_db_pool():
    """初始化 asyncpg 連接池"""
    global _db_pool
    if _db_pool is None:
        settings = get_settings()
        _db_pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
        logger.info("✅ AsyncPG 連接池初始化成功")

async def get_db_pool() -> asyncpg.Pool:
    """獲取 asyncpg 連接池"""
    global _db_pool
    if _db_pool is None:
        await init_db_pool()
    return _db_pool

async def close_db_pool():
    """關閉資料庫連接池"""
    global _db_pool
    if _db_pool:
        await _db_pool.close()
        _db_pool = None
        logger.info("✅ AsyncPG 連接池已關閉") 