"""
指標查詢 API 路由
提供實時和歷史監控指標數據查詢
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
import asyncpg
import redis.asyncio as redis

from ..dependencies import verify_api_key, get_db_connection, get_redis_connection, get_db_pool
from ..models import db_metrics_to_response, db_service_to_response, db_endpoint_to_response

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/v1/metrics",
    tags=["指標查詢"],
    dependencies=[Depends(verify_api_key)]
)

# 請求/響應模型
class TimeRange(BaseModel):
    """時間範圍模型"""
    start_time: datetime = Field(..., description="開始時間 (ISO 8601 格式)")
    end_time: datetime = Field(..., description="結束時間 (ISO 8601 格式)")

class MetricFilter(BaseModel):
    """指標過濾器"""
    service_name: Optional[str] = Field(None, description="服務名稱")
    endpoint: Optional[str] = Field(None, description="端點路徑")
    metric_type: Optional[str] = Field("endpoint", description="指標類型: endpoint, service")

class MetricResponse(BaseModel):
    """指標響應模型"""
    id: int
    timestamp: datetime
    service_name: str
    endpoint: str
    metric_type: str
    qps: float
    error_rate: float
    avg_response_time: float
    p95_response_time: float
    p99_response_time: float
    total_requests: int
    total_errors: int

class MetricsSummary(BaseModel):
    """指標摘要"""
    total_services: int
    total_endpoints: int
    total_requests: int
    average_qps: float
    average_error_rate: float
    average_response_time: float

@router.get("/summary", response_model=Dict[str, Any])
async def get_metrics_summary(
    time_range: Optional[int] = Query(3600, description="時間範圍（秒），默認1小時"),
    db_pool: asyncpg.Pool = Depends(get_db_pool)
) -> Dict[str, Any]:
    """
    獲取指標摘要統計
    """
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(seconds=time_range)
        
        async with db_pool.acquire() as conn:
            # 查詢指標摘要
            summary_query = """
                SELECT 
                    COUNT(DISTINCT service_name) as total_services,
                    COUNT(DISTINCT CASE WHEN metric_type = 'endpoint' THEN endpoint END) as total_endpoints,
                    SUM(total_requests) as total_requests,
                    AVG(qps) as average_qps,
                    AVG(error_rate) as average_error_rate,
                    AVG(avg_response_time) as average_response_time
                FROM metrics_aggregated 
                WHERE created_at >= $1 AND created_at <= $2
            """
            
            summary = await conn.fetchrow(summary_query, start_time, end_time)
            
            # 查詢服務分佈
            services_query = """
                SELECT 
                    service_name,
                    COUNT(*) as metric_count,
                    AVG(qps) as avg_qps,
                    AVG(error_rate) as avg_error_rate,
                    AVG(avg_response_time) as avg_response_time
                FROM metrics_aggregated 
                WHERE created_at >= $1 AND created_at <= $2
                GROUP BY service_name
                ORDER BY avg_qps DESC
            """
            
            services_data = await conn.fetch(services_query, start_time, end_time)
            
            return {
                "success": True,
                "data": {
                    "summary": {
                        "total_services": summary["total_services"] or 0,
                        "total_endpoints": summary["total_endpoints"] or 0,
                        "total_requests": summary["total_requests"] or 0,
                        "average_qps": round(float(summary["average_qps"] or 0), 2),
                        "average_error_rate": round(float(summary["average_error_rate"] or 0), 4),
                        "average_response_time": round(float(summary["average_response_time"] or 0), 2)
                    },
                    "services": [
                        {
                            "service_name": row["service_name"],
                            "metric_count": row["metric_count"],
                            "avg_qps": round(float(row["avg_qps"]), 2),
                            "avg_error_rate": round(float(row["avg_error_rate"]), 4),
                            "avg_latency_ms": round(float(row["avg_response_time"]), 2)  # 統一欄位名稱
                        }
                        for row in services_data
                    ],
                    "time_range": {
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "duration_seconds": time_range
                    }
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"獲取指標摘要失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "METRICS_SUMMARY_ERROR",
                "message": "獲取指標摘要失敗",
                "developer_message": str(e)
            }
        )

@router.get("/historical", response_model=Dict[str, Any])
async def get_historical_metrics(
    service_name: Optional[str] = Query(None, description="服務名稱過濾"),
    endpoint: Optional[str] = Query(None, description="端點過濾"),
    start_time: Optional[datetime] = Query(None, description="開始時間"),
    end_time: Optional[datetime] = Query(None, description="結束時間"),
    limit: int = Query(100, le=1000, description="返回記錄數限制"),
    offset: int = Query(0, description="分頁偏移"),
    db_pool: asyncpg.Pool = Depends(get_db_pool)
) -> Dict[str, Any]:
    """
    查詢歷史指標數據
    支持時間範圍、服務、端點過濾和分頁
    """
    try:
        # 默認時間範圍：最近24小時
        if not end_time:
            end_time = datetime.utcnow()
        if not start_time:
            start_time = end_time - timedelta(hours=24)
            
        # 構建查詢條件
        where_conditions = ["created_at >= $1", "created_at <= $2"]
        params = [start_time, end_time]
        param_count = 2
        
        if service_name:
            param_count += 1
            where_conditions.append(f"service_name = ${param_count}")
            params.append(service_name)
            
        if endpoint:
            param_count += 1
            where_conditions.append(f"endpoint = ${param_count}")
            params.append(endpoint)
        
        where_clause = " AND ".join(where_conditions)
        
        async with db_pool.acquire() as conn:
            # 查詢總數
            count_query = f"""
                SELECT COUNT(*) 
                FROM metrics_aggregated 
                WHERE {where_clause}
            """
            total_count = await conn.fetchval(count_query, *params)
            
            # 查詢數據
            data_query = f"""
                SELECT 
                    id, timestamp, window_start, window_end,
                    service_name, endpoint, metric_type,
                    qps, error_rate, avg_response_time,
                    p95_response_time, p99_response_time,
                    total_requests, total_errors,
                    additional_data, created_at
                FROM metrics_aggregated 
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_count + 1} OFFSET ${param_count + 2}
            """
            
            params.extend([limit, offset])
            rows = await conn.fetch(data_query, *params)
            
            # 轉換數據格式 - 使用統一的欄位名稱
            metrics_data = []
            for row in rows:
                metrics_data.append({
                    "id": row["id"],
                    "timestamp": row["timestamp"].isoformat(),
                    "window_start": row["window_start"].isoformat(),
                    "window_end": row["window_end"].isoformat(),
                    "service_name": row["service_name"],
                    "api_endpoint": row["endpoint"],  # 統一欄位名稱
                    "metric_type": row["metric_type"],
                    "qps": float(row["qps"]),
                    "error_rate": float(row["error_rate"]),
                    "avg_latency_ms": float(row["avg_response_time"]),  # 統一欄位名稱
                    "p95_latency_ms": float(row["p95_response_time"]),  # 統一欄位名稱
                    "p99_latency_ms": float(row["p99_response_time"]),  # 統一欄位名稱
                    "total_requests": row["total_requests"],
                    "total_errors": row["total_errors"],
                    "additional_data": row["additional_data"],
                    "created_at": row["created_at"].isoformat()
                })
            
            return {
                "success": True,
                "data": {
                    "metrics": metrics_data,
                    "pagination": {
                        "total": total_count,
                        "limit": limit,
                        "offset": offset,
                        "has_more": offset + limit < total_count
                    },
                    "filters": {
                        "service_name": service_name,
                        "endpoint": endpoint,
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat()
                    }
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"查詢歷史指標失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "HISTORICAL_METRICS_ERROR",
                "message": "查詢歷史指標失敗",
                "developer_message": str(e)
            }
        )

@router.get("/real-time", response_model=Dict[str, Any])
async def get_real_time_metrics(
    service_name: Optional[str] = Query(None, description="服務名稱過濾"),
    redis_conn: redis.Redis = Depends(get_redis_connection)
) -> Dict[str, Any]:
    """
    獲取實時指標數據（從 Redis 快取）
    """
    try:
        # 查詢 Redis 中的實時數據，添加錯誤處理
        try:
            pattern = "metrics:*"
            keys = await redis_conn.keys(pattern)
        except Exception as e:
            logger.warning(f"Redis 連接失敗，返回空指標列表: {e}")
            keys = []
        
        real_time_data = []
        for key in keys:
            try:
                data = await redis_conn.get(key)
                if data:
                    import json
                    metric_data = json.loads(data)
                    
                    # 服務名稱過濾
                    if service_name and metric_data.get("service_name") != service_name:
                        continue
                        
                    real_time_data.append(metric_data)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"解析 Redis 數據失敗 {key}: {e}")
                continue
        
        # 按服務分組統計
        service_stats = {}
        for data in real_time_data:
            svc_name = data.get("service_name", "unknown")
            if svc_name not in service_stats:
                service_stats[svc_name] = {
                    "service_name": svc_name,
                    "endpoints": 0,
                    "total_qps": 0,
                    "avg_error_rate": 0,
                    "avg_response_time": 0,
                    "last_updated": None
                }
            
            stats = service_stats[svc_name]
            stats["endpoints"] += 1
            stats["total_qps"] += data.get("qps", 0)
            stats["avg_error_rate"] += data.get("error_rate", 0)
            stats["avg_response_time"] += data.get("avg_response_time", 0)
            
            # 更新時間戳
            if not stats["last_updated"] or data.get("timestamp", "") > stats["last_updated"]:
                stats["last_updated"] = data.get("timestamp")
        
        # 計算平均值
        for stats in service_stats.values():
            if stats["endpoints"] > 0:
                stats["avg_error_rate"] = round(stats["avg_error_rate"] / stats["endpoints"], 4)
                stats["avg_response_time"] = round(stats["avg_response_time"] / stats["endpoints"], 2)
                stats["total_qps"] = round(stats["total_qps"], 2)
        
        return {
            "success": True,
            "data": {
                "real_time_metrics": real_time_data,
                "service_summary": list(service_stats.values()),
                "total_services": len(service_stats),
                "total_metrics": len(real_time_data),
                "cache_ttl_seconds": 300  # Redis TTL
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"獲取實時指標失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "REAL_TIME_METRICS_ERROR",
                "message": "獲取實時指標失敗",
                "developer_message": str(e)
            }
        )

@router.get("/services", response_model=Dict[str, Any])
async def get_services_list(
    db_pool: asyncpg.Pool = Depends(get_db_pool)
) -> Dict[str, Any]:
    """
    獲取所有監控服務列表
    """
    try:
        async with db_pool.acquire() as conn:
            query = """
                SELECT 
                    service_name,
                    COUNT(DISTINCT endpoint) as endpoint_count,
                    COUNT(*) as metric_count,
                    AVG(qps) as avg_qps,
                    AVG(error_rate) as avg_error_rate,
                    AVG(avg_response_time) as avg_response_time,
                    MAX(created_at) as last_seen
                FROM metrics_aggregated 
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                GROUP BY service_name
                ORDER BY service_name
            """
            
            rows = await conn.fetch(query)
            
            services = []
            for row in rows:
                # 確保時區一致性
                last_seen = row["last_seen"]
                now = datetime.utcnow()
                if last_seen and hasattr(last_seen, 'replace'):
                    if last_seen.tzinfo is not None:
                        last_seen = last_seen.replace(tzinfo=None)
                
                services.append({
                    "service_name": row["service_name"],
                    "endpoint_count": row["endpoint_count"],
                    "metric_count": row["metric_count"],
                    "avg_qps": round(float(row["avg_qps"]), 2),
                    "avg_error_rate": round(float(row["avg_error_rate"]), 4),
                    "avg_latency_ms": round(float(row["avg_response_time"]), 2),  # 統一欄位名稱
                    "last_seen": row["last_seen"].isoformat(),
                    "status": "active" if last_seen and last_seen > now - timedelta(minutes=5) else "inactive"
                })
            
            return {
                "success": True,
                "data": {
                    "services": services,
                    "total_count": len(services)
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"獲取服務列表失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SERVICES_LIST_ERROR", 
                "message": "獲取服務列表失敗",
                "developer_message": str(e)
            }
        )

@router.get("/services/{service_name}/endpoints", response_model=Dict[str, Any])
async def get_service_endpoints(
    service_name: str,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
) -> Dict[str, Any]:
    """
    獲取指定服務的所有端點
    """
    try:
        async with db_pool.acquire() as conn:
            query = """
                SELECT 
                    endpoint,
                    COUNT(*) as metric_count,
                    AVG(qps) as avg_qps,
                    AVG(error_rate) as avg_error_rate,
                    AVG(avg_response_time) as avg_response_time,
                    AVG(p95_response_time) as avg_p95_response_time,
                    AVG(p99_response_time) as avg_p99_response_time,
                    MAX(created_at) as last_seen
                FROM metrics_aggregated 
                WHERE service_name = $1 
                AND created_at >= NOW() - INTERVAL '24 hours'
                GROUP BY endpoint
                ORDER BY endpoint
            """
            
            rows = await conn.fetch(query, service_name)
            
            if not rows:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "code": "SERVICE_NOT_FOUND",
                        "message": f"服務 '{service_name}' 不存在或無數據"
                    }
                )
            
            endpoints = []
            for row in rows:
                # 確保時區一致性
                last_seen = row["last_seen"]
                now = datetime.utcnow()
                if last_seen and hasattr(last_seen, 'replace'):
                    if last_seen.tzinfo is not None:
                        last_seen = last_seen.replace(tzinfo=None)
                
                endpoints.append({
                    "api_endpoint": row["endpoint"],  # 統一欄位名稱
                    "metric_count": row["metric_count"],
                    "avg_qps": round(float(row["avg_qps"]), 2),
                    "avg_error_rate": round(float(row["avg_error_rate"]), 4),
                    "avg_latency_ms": round(float(row["avg_response_time"]), 2),  # 統一欄位名稱
                    "p95_latency_ms": round(float(row["avg_p95_response_time"]), 2),  # 統一欄位名稱
                    "p99_latency_ms": round(float(row["avg_p99_response_time"]), 2),  # 統一欄位名稱
                    "last_seen": row["last_seen"].isoformat(),
                    "status": "active" if last_seen and last_seen > now - timedelta(minutes=5) else "inactive"
                })
            
            return {
                "success": True,
                "data": {
                    "service_name": service_name,
                    "endpoints": endpoints,
                    "total_count": len(endpoints)
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取服務端點失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SERVICE_ENDPOINTS_ERROR",
                "message": "獲取服務端點失敗", 
                "developer_message": str(e)
            }
        ) 