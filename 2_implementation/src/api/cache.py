"""
Redis 快取管理模組
用於即時數據快取和會話管理
"""

import json
import logging
from typing import Any, Dict, Optional, Union
import redis.asyncio as redis
from redis.exceptions import RedisError, ConnectionError

from .config import get_settings

logger = logging.getLogger(__name__)

# 全域 Redis 連接池
redis_pool = None
redis_client = None


async def init_redis():
    """初始化 Redis 連接池"""
    global redis_pool, redis_client
    
    try:
        settings = get_settings()
        
        # 創建連接池
        redis_pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=20,
            retry_on_timeout=True,
            decode_responses=True,
        )
        
        # 創建 Redis 客戶端
        redis_client = redis.Redis(connection_pool=redis_pool)
        
        # 測試連接
        await redis_client.ping()
        
        logger.info("✅ Redis 連接初始化成功")
        
    except Exception as e:
        logger.error(f"❌ Redis 連接初始化失敗: {e}")
        raise


async def get_redis_client() -> redis.Redis:
    """
    獲取 Redis 客戶端
    用於依賴注入
    """
    if redis_client is None:
        await init_redis()
    
    return redis_client


async def get_redis_health() -> str:
    """
    檢查 Redis 健康狀態
    返回: "healthy", "unhealthy", "unknown"
    """
    try:
        if redis_client is None:
            await init_redis()
        
        # 執行 ping 命令
        response = await redis_client.ping()
        
        if response:
            logger.debug("✅ Redis 健康檢查通過")
            return "healthy"
        else:
            return "unhealthy"
            
    except ConnectionError:
        logger.error("❌ Redis 連接失敗")
        return "unhealthy"
    except Exception as e:
        logger.error(f"❌ Redis 健康檢查失敗: {e}")
        return "unhealthy"


async def set_cache(
    key: str, 
    value: Union[str, Dict, Any], 
    ttl: Optional[int] = None
) -> bool:
    """
    設置快取值
    
    Args:
        key: 快取鍵
        value: 快取值 (自動序列化 JSON)
        ttl: 過期時間 (秒)，None 表示不過期
        
    Returns:
        bool: 是否設置成功
    """
    try:
        client = await get_redis_client()
        
        # 序列化值
        if isinstance(value, (dict, list)):
            serialized_value = json.dumps(value, ensure_ascii=False)
        else:
            serialized_value = str(value)
        
        # 設置快取
        if ttl:
            await client.setex(key, ttl, serialized_value)
        else:
            await client.set(key, serialized_value)
        
        logger.debug(f"✅ 快取設置成功: {key}")
        return True
        
    except Exception as e:
        logger.error(f"❌ 快取設置失敗 {key}: {e}")
        return False


async def get_cache(key: str, as_json: bool = True) -> Optional[Any]:
    """
    獲取快取值
    
    Args:
        key: 快取鍵
        as_json: 是否嘗試解析為 JSON
        
    Returns:
        快取值，如果不存在返回 None
    """
    try:
        client = await get_redis_client()
        
        value = await client.get(key)
        
        if value is None:
            return None
        
        # 嘗試解析 JSON
        if as_json:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # 如果不是 JSON，返回原始字符串
                return value
        else:
            return value
            
    except Exception as e:
        logger.error(f"❌ 快取獲取失敗 {key}: {e}")
        return None


async def delete_cache(key: str) -> bool:
    """
    刪除快取值
    
    Args:
        key: 快取鍵
        
    Returns:
        bool: 是否刪除成功
    """
    try:
        client = await get_redis_client()
        
        result = await client.delete(key)
        
        logger.debug(f"✅ 快取刪除: {key}, 影響數量: {result}")
        return result > 0
        
    except Exception as e:
        logger.error(f"❌ 快取刪除失敗 {key}: {e}")
        return False


async def exists_cache(key: str) -> bool:
    """
    檢查快取鍵是否存在
    
    Args:
        key: 快取鍵
        
    Returns:
        bool: 是否存在
    """
    try:
        client = await get_redis_client()
        
        result = await client.exists(key)
        return result > 0
        
    except Exception as e:
        logger.error(f"❌ 快取檢查失敗 {key}: {e}")
        return False


async def set_real_time_metrics(service_name: str, metrics: Dict[str, Any]) -> bool:
    """
    設置即時指標數據
    
    Args:
        service_name: 服務名稱
        metrics: 指標數據
        
    Returns:
        bool: 是否設置成功
    """
    cache_key = f"real_time_metrics:{service_name}"
    
    # 添加時間戳
    metrics_with_timestamp = {
        **metrics,
        "last_updated": "2025-07-01T10:30:00Z"  # TODO: 實現動態時間戳
    }
    
    # 設置 5 分鐘過期時間
    return await set_cache(cache_key, metrics_with_timestamp, ttl=300)


async def get_real_time_metrics(service_name: str) -> Optional[Dict[str, Any]]:
    """
    獲取即時指標數據
    
    Args:
        service_name: 服務名稱
        
    Returns:
        指標數據字典，如果不存在返回 None
    """
    cache_key = f"real_time_metrics:{service_name}"
    return await get_cache(cache_key, as_json=True)


async def get_all_real_time_metrics() -> Dict[str, Dict[str, Any]]:
    """
    獲取所有服務的即時指標數據
    
    Returns:
        所有服務的指標數據字典
    """
    try:
        client = await get_redis_client()
        
        # 查找所有即時指標的鍵
        pattern = "real_time_metrics:*"
        keys = await client.keys(pattern)
        
        metrics_data = {}
        
        for key in keys:
            # 提取服務名稱
            service_name = key.replace("real_time_metrics:", "")
            
            # 獲取指標數據
            metrics = await get_cache(key, as_json=True)
            
            if metrics:
                metrics_data[service_name] = metrics
        
        return metrics_data
        
    except Exception as e:
        logger.error(f"❌ 獲取所有即時指標失敗: {e}")
        return {}


async def close_redis():
    """關閉 Redis 連接"""
    global redis_client, redis_pool
    
    try:
        if redis_client:
            await redis_client.aclose()
            logger.info("✅ Redis 客戶端已關閉")
        
        if redis_pool:
            await redis_pool.disconnect()
            logger.info("✅ Redis 連接池已關閉")
            
    except Exception as e:
        logger.error(f"❌ 關閉 Redis 連接時發生錯誤: {e}")


# 快取鍵常量
class CacheKeys:
    """快取鍵常量定義"""
    
    # 即時指標
    REAL_TIME_METRICS = "real_time_metrics:{service_name}"
    
    # 服務狀態
    SERVICE_STATUS = "service_status:{service_name}"
    
    # 告警狀態
    ACTIVE_ALERTS = "active_alerts"
    
    # API 響應快取
    API_RESPONSE = "api_response:{endpoint}:{params_hash}"
    
    @staticmethod
    def real_time_metrics(service_name: str) -> str:
        """生成即時指標快取鍵"""
        return f"real_time_metrics:{service_name}"
    
    @staticmethod
    def service_status(service_name: str) -> str:
        """生成服務狀態快取鍵"""
        return f"service_status:{service_name}" 