"""
存儲管理器服務
負責將聚合指標數據持久化到 PostgreSQL 和 Redis
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import asyncpg
import redis.asyncio as redis

from ..api.config import get_settings

logger = logging.getLogger(__name__)


class StorageManager:
    """
    存儲管理器
    
    負責：
    1. PostgreSQL 批量寫入聚合數據
    2. Redis 快取即時指標
    3. 數據清理和歸檔
    4. 性能優化 (批量操作、連接池)
    """
    
    def __init__(self, 
                 batch_size: int = 100,
                 batch_timeout_seconds: int = 5,
                 redis_ttl_seconds: int = 300):
        """
        初始化存儲管理器
        
        Args:
            batch_size: 批量寫入大小
            batch_timeout_seconds: 批量寫入超時
            redis_ttl_seconds: Redis 快取過期時間
        """
        self.settings = get_settings()
        self.batch_size = batch_size
        self.batch_timeout_seconds = batch_timeout_seconds
        self.redis_ttl_seconds = redis_ttl_seconds
        
        # 批量寫入緩衝區
        self.pending_metrics: List[Dict[str, Any]] = []
        self.last_batch_time = datetime.utcnow()
        
        # 連接池
        self.postgres_pool: Optional[asyncpg.Pool] = None
        self.redis_client: Optional[redis.Redis] = None
        
        # 統計信息
        self.stats = {
            "total_postgres_writes": 0,
            "total_redis_writes": 0,
            "batch_writes": 0,
            "failed_writes": 0,
            "last_write_time": None,
            "start_time": datetime.utcnow()
        }
        
        logger.info(f"StorageManager 已初始化 - 批量大小: {batch_size}")
    
    async def initialize(self) -> bool:
        """
        初始化數據庫連接
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 初始化 PostgreSQL 連接池
            await self._init_postgres_pool()
            
            # 初始化 Redis 連接
            await self._init_redis_client()
            
            # 確保表結構存在
            await self._ensure_table_schema()
            
            logger.info("✅ StorageManager 初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ StorageManager 初始化失敗: {e}")
            return False
    
    async def _init_postgres_pool(self):
        """初始化 PostgreSQL 連接池"""
        try:
            # 解析數據庫 URL
            db_url = self.settings.DATABASE_URL
            
            self.postgres_pool = await asyncpg.create_pool(
                db_url,
                min_size=2,
                max_size=10,
                command_timeout=30,
                server_settings={
                    'jit': 'off'  # 關閉 JIT 以提高小查詢性能
                }
            )
            
            logger.info("PostgreSQL 連接池已創建")
            
        except Exception as e:
            logger.error(f"PostgreSQL 連接池創建失敗: {e}")
            raise
    
    async def _init_redis_client(self):
        """初始化 Redis 連接"""
        try:
            # 解析 Redis URL
            redis_url = self.settings.REDIS_URL
            
            self.redis_client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20
            )
            
            # 測試連接
            await self.redis_client.ping()
            
            logger.info("Redis 連接已建立")
            
        except Exception as e:
            logger.error(f"Redis 連接失敗: {e}")
            raise
    
    async def _ensure_table_schema(self):
        """確保數據庫表結構存在"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS metrics_aggregated (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ NOT NULL,
            window_start TIMESTAMPTZ NOT NULL,
            window_end TIMESTAMPTZ NOT NULL,
            service_name VARCHAR(255),
            endpoint VARCHAR(255),
            metric_type VARCHAR(50) NOT NULL, -- 'overall', 'service', 'endpoint'
            qps DECIMAL(10,2) DEFAULT 0,
            error_rate DECIMAL(5,2) DEFAULT 0,
            avg_response_time DECIMAL(10,2) DEFAULT 0,
            p95_response_time DECIMAL(10,2) DEFAULT 0,
            p99_response_time DECIMAL(10,2) DEFAULT 0,
            total_requests INTEGER DEFAULT 0,
            total_errors INTEGER DEFAULT 0,
            additional_data JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- 為查詢性能創建索引
        CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics_aggregated(timestamp);
        CREATE INDEX IF NOT EXISTS idx_metrics_service ON metrics_aggregated(service_name);
        CREATE INDEX IF NOT EXISTS idx_metrics_endpoint ON metrics_aggregated(endpoint);
        CREATE INDEX IF NOT EXISTS idx_metrics_type ON metrics_aggregated(metric_type);
        CREATE INDEX IF NOT EXISTS idx_metrics_window_start ON metrics_aggregated(window_start);
        """
        
        try:
            async with self.postgres_pool.acquire() as conn:
                await conn.execute(create_table_sql)
            
            logger.info("數據庫表結構已確認")
            
        except Exception as e:
            logger.error(f"創建表結構失敗: {e}")
            raise
    
    async def store_metrics(self, metrics_data: Dict[str, Any]):
        """
        存儲聚合指標數據
        
        Args:
            metrics_data: 聚合指標數據
        """
        try:
            # 更新 Redis 快取
            await self._update_redis_cache(metrics_data)
            
            # 添加到批量寫入緩衝區
            await self._add_to_batch(metrics_data)
            
            # 檢查是否需要執行批量寫入
            await self._check_batch_write()
            
        except Exception as e:
            logger.error(f"存儲指標數據失敗: {e}")
            self.stats["failed_writes"] += 1
    
    async def _update_redis_cache(self, metrics_data: Dict[str, Any]):
        """更新 Redis 快取"""
        try:
            if not self.redis_client:
                return
            
            # 使用 Pipeline 進行批量操作
            pipeline = self.redis_client.pipeline()
            
            # 存儲整體指標
            overall_key = "metrics:overall:current"
            pipeline.setex(
                overall_key,
                self.redis_ttl_seconds,
                json.dumps(metrics_data["overall"])
            )
            
            # 存儲服務級指標
            for service_name, service_metrics in metrics_data.get("services", {}).items():
                service_key = f"metrics:service:{service_name}:current"
                pipeline.setex(
                    service_key,
                    self.redis_ttl_seconds,
                    json.dumps(service_metrics)
                )
            
            # 存儲端點級指標
            for endpoint_key, endpoint_metrics in metrics_data.get("endpoints", {}).items():
                endpoint_redis_key = f"metrics:endpoint:{endpoint_key}:current"
                pipeline.setex(
                    endpoint_redis_key,
                    self.redis_ttl_seconds,
                    json.dumps(endpoint_metrics)
                )
            
            # 存儲完整數據快照
            snapshot_key = "metrics:snapshot:current"
            pipeline.setex(
                snapshot_key,
                self.redis_ttl_seconds,
                json.dumps(metrics_data)
            )
            
            # 執行所有 Redis 操作
            await pipeline.execute()
            
            self.stats["total_redis_writes"] += 1
            logger.debug("Redis 快取已更新")
            
        except Exception as e:
            logger.error(f"更新 Redis 快取失敗: {e}")
    
    async def _add_to_batch(self, metrics_data: Dict[str, Any]):
        """添加數據到批量寫入緩衝區"""
        timestamp = datetime.fromisoformat(metrics_data["timestamp"].replace('Z', '+00:00'))
        window_start = timestamp - timedelta(seconds=metrics_data["window_size_seconds"])
        window_end = timestamp
        
        # 添加整體指標
        overall_record = {
            "timestamp": timestamp,
            "window_start": window_start,
            "window_end": window_end,
            "service_name": None,
            "endpoint": None,
            "metric_type": "overall",
            **metrics_data["overall"],
            "additional_data": {
                "active_windows": metrics_data["active_windows"],
                "window_size_seconds": metrics_data["window_size_seconds"]
            }
        }
        self.pending_metrics.append(overall_record)
        
        # 添加服務級指標
        for service_name, service_metrics in metrics_data.get("services", {}).items():
            service_record = {
                "timestamp": timestamp,
                "window_start": window_start,
                "window_end": window_end,
                "service_name": service_name,
                "endpoint": None,
                "metric_type": "service",
                **service_metrics,
                "additional_data": {}
            }
            self.pending_metrics.append(service_record)
        
        # 添加端點級指標
        for endpoint_key, endpoint_metrics in metrics_data.get("endpoints", {}).items():
            # 解析服務名和端點
            if ":" in endpoint_key:
                service_name, endpoint = endpoint_key.split(":", 1)
            else:
                service_name, endpoint = None, endpoint_key
            
            endpoint_record = {
                "timestamp": timestamp,
                "window_start": window_start,
                "window_end": window_end,
                "service_name": service_name,
                "endpoint": endpoint,
                "metric_type": "endpoint",
                **endpoint_metrics,
                "additional_data": {}
            }
            self.pending_metrics.append(endpoint_record)
    
    async def _check_batch_write(self):
        """檢查是否需要執行批量寫入"""
        now = datetime.utcnow()
        time_since_last_batch = (now - self.last_batch_time).total_seconds()
        
        # 達到批量大小或超過時間閾值
        if (len(self.pending_metrics) >= self.batch_size or 
            time_since_last_batch >= self.batch_timeout_seconds):
            
            await self._execute_batch_write()
    
    async def _execute_batch_write(self):
        """執行批量寫入到 PostgreSQL"""
        if not self.pending_metrics:
            return
        
        try:
            async with self.postgres_pool.acquire() as conn:
                # 準備批量插入 SQL
                insert_sql = """
                INSERT INTO metrics_aggregated (
                    timestamp, window_start, window_end, service_name, endpoint,
                    metric_type, qps, error_rate, avg_response_time,
                    p95_response_time, p99_response_time, total_requests,
                    total_errors, additional_data
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                """
                
                # 準備批量數據
                batch_data = []
                for record in self.pending_metrics:
                    batch_data.append((
                        record["timestamp"],
                        record["window_start"],
                        record["window_end"],
                        record["service_name"],
                        record["endpoint"],
                        record["metric_type"],
                        record["qps"],
                        record["error_rate"],
                        record["avg_response_time"],
                        record["p95_response_time"],
                        record["p99_response_time"],
                        record["total_requests"],
                        record["total_errors"],
                        json.dumps(record["additional_data"])
                    ))
                
                # 執行批量插入
                await conn.executemany(insert_sql, batch_data)
                
                # 更新統計
                self.stats["total_postgres_writes"] += len(batch_data)
                self.stats["batch_writes"] += 1
                self.stats["last_write_time"] = datetime.utcnow()
                
                logger.info(f"批量寫入完成: {len(batch_data)} 條記錄")
                
                # 清空緩衝區
                self.pending_metrics.clear()
                self.last_batch_time = datetime.utcnow()
                
        except Exception as e:
            logger.error(f"批量寫入失敗: {e}")
            self.stats["failed_writes"] += 1
            
            # 如果失敗，清空緩衝區避免堆積
            self.pending_metrics.clear()
            self.last_batch_time = datetime.utcnow()
    
    async def get_cached_metrics(self, metric_type: str = "overall") -> Optional[Dict[str, Any]]:
        """
        從 Redis 獲取快取的指標數據
        
        Args:
            metric_type: 指標類型 ('overall', 'service:name', 'endpoint:key')
            
        Returns:
            Dict: 快取的指標數據
        """
        try:
            if not self.redis_client:
                return None
            
            if metric_type == "overall":
                key = "metrics:overall:current"
            elif metric_type.startswith("service:"):
                service_name = metric_type[8:]  # 移除 'service:' 前綴
                key = f"metrics:service:{service_name}:current"
            elif metric_type.startswith("endpoint:"):
                endpoint_key = metric_type[9:]  # 移除 'endpoint:' 前綴
                key = f"metrics:endpoint:{endpoint_key}:current"
            else:
                key = "metrics:snapshot:current"
            
            cached_data = await self.redis_client.get(key)
            if cached_data:
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logger.error(f"獲取快取數據失敗: {e}")
            return None
    
    async def get_historical_metrics(self, 
                                   start_time: datetime,
                                   end_time: datetime,
                                   service_name: Optional[str] = None,
                                   endpoint: Optional[str] = None,
                                   metric_type: str = "overall") -> List[Dict[str, Any]]:
        """
        從 PostgreSQL 獲取歷史指標數據
        
        Args:
            start_time: 開始時間
            end_time: 結束時間
            service_name: 服務名稱過濾
            endpoint: 端點過濾
            metric_type: 指標類型過濾
            
        Returns:
            List: 歷史指標數據
        """
        try:
            # 構建查詢 SQL
            where_conditions = ["timestamp BETWEEN $1 AND $2", "metric_type = $3"]
            params = [start_time, end_time, metric_type]
            
            if service_name:
                where_conditions.append(f"service_name = ${len(params) + 1}")
                params.append(service_name)
            
            if endpoint:
                where_conditions.append(f"endpoint = ${len(params) + 1}")
                params.append(endpoint)
            
            query_sql = f"""
            SELECT timestamp, window_start, window_end, service_name, endpoint,
                   metric_type, qps, error_rate, avg_response_time,
                   p95_response_time, p99_response_time, total_requests,
                   total_errors, additional_data
            FROM metrics_aggregated
            WHERE {' AND '.join(where_conditions)}
            ORDER BY timestamp DESC
            LIMIT 1000
            """
            
            async with self.postgres_pool.acquire() as conn:
                rows = await conn.fetch(query_sql, *params)
                
                results = []
                for row in rows:
                    results.append({
                        "timestamp": row["timestamp"].isoformat(),
                        "window_start": row["window_start"].isoformat(),
                        "window_end": row["window_end"].isoformat(),
                        "service_name": row["service_name"],
                        "endpoint": row["endpoint"],
                        "metric_type": row["metric_type"],
                        "qps": float(row["qps"]) if row["qps"] else 0.0,
                        "error_rate": float(row["error_rate"]) if row["error_rate"] else 0.0,
                        "avg_response_time": float(row["avg_response_time"]) if row["avg_response_time"] else 0.0,
                        "p95_response_time": float(row["p95_response_time"]) if row["p95_response_time"] else 0.0,
                        "p99_response_time": float(row["p99_response_time"]) if row["p99_response_time"] else 0.0,
                        "total_requests": row["total_requests"] or 0,
                        "total_errors": row["total_errors"] or 0,
                        "additional_data": json.loads(row["additional_data"]) if row["additional_data"] else {}
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"查詢歷史數據失敗: {e}")
            return []
    
    async def cleanup_old_data(self, retention_days: int = 30):
        """
        清理舊數據
        
        Args:
            retention_days: 保留天數
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=retention_days)
            
            async with self.postgres_pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM metrics_aggregated WHERE timestamp < $1",
                    cutoff_time
                )
                
                deleted_count = int(result.split()[-1])  # 提取刪除的行數
                logger.info(f"清理完成: 刪除 {deleted_count} 條舊記錄")
                
        except Exception as e:
            logger.error(f"清理舊數據失敗: {e}")
    
    async def force_batch_write(self):
        """強制執行批量寫入 (用於停機時)"""
        await self._execute_batch_write()
    
    async def close(self):
        """關閉存儲管理器"""
        try:
            # 強制寫入剩餘數據
            await self.force_batch_write()
            
            # 關閉連接
            if self.postgres_pool:
                await self.postgres_pool.close()
            
            if self.redis_client:
                await self.redis_client.close()
            
            logger.info("StorageManager 已關閉")
            
        except Exception as e:
            logger.error(f"關閉 StorageManager 時發生錯誤: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取存儲管理器統計信息"""
        runtime = datetime.utcnow() - self.stats["start_time"]
        
        return {
            **self.stats,
            "pending_metrics_count": len(self.pending_metrics),
            "batch_size": self.batch_size,
            "batch_timeout_seconds": self.batch_timeout_seconds,
            "redis_ttl_seconds": self.redis_ttl_seconds,
            "runtime_seconds": runtime.total_seconds(),
            "avg_writes_per_minute": (self.stats["total_postgres_writes"] / (runtime.total_seconds() / 60)) if runtime.total_seconds() > 0 else 0.0,
            "is_postgres_connected": self.postgres_pool is not None,
            "is_redis_connected": self.redis_client is not None
        } 