"""
服務狀態 API 路由
提供服務健康狀態和性能監控
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
import asyncpg
import redis.asyncio as redis

from ..dependencies import verify_api_key, get_db_connection, get_redis_connection, get_db_pool
from ..models import db_service_to_response, db_endpoint_to_response

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/v1/services",
    tags=["服務監控"],
    dependencies=[Depends(verify_api_key)]
)

class ServiceHealth(BaseModel):
    """服務健康狀態模型"""
    service_name: str
    status: str  # healthy, unhealthy, unknown
    last_seen: datetime
    endpoint_count: int
    avg_qps: float
    avg_error_rate: float
    avg_response_time: float

class ServiceMetrics(BaseModel):
    """服務指標模型"""
    service_name: str
    total_requests: int
    total_errors: int
    qps: float
    error_rate: float
    avg_response_time: float
    p95_response_time: float
    p99_response_time: float

@router.get("/", response_model=Dict[str, Any])
async def get_services_overview(
    status_filter: Optional[str] = Query(None, description="狀態過濾"),
    db_pool: asyncpg.Pool = Depends(get_db_pool)
) -> Dict[str, Any]:
    """
    獲取所有服務概覽
    """
    try:
        async with db_pool.acquire() as conn:
            query = """
                SELECT 
                    service_name,
                    COUNT(DISTINCT endpoint) as endpoint_count,
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
                last_seen = row["last_seen"]
                
                # 判斷服務健康狀態
                # 確保時區一致性
                now = datetime.utcnow()
                if last_seen and hasattr(last_seen, 'replace'):
                    # 如果 last_seen 是 timezone-aware，轉換為 naive
                    if last_seen.tzinfo is not None:
                        last_seen = last_seen.replace(tzinfo=None)
                
                if last_seen and last_seen > now - timedelta(minutes=5):
                    if row["avg_error_rate"] > 0.1:
                        status = "unhealthy"
                    else:
                        status = "healthy"
                else:
                    status = "unknown"
                
                service_data = {
                    "service_name": row["service_name"],
                    "status": status,
                    "last_seen": last_seen.isoformat(),
                    "endpoint_count": row["endpoint_count"],
                    "avg_qps": round(float(row["avg_qps"]), 2),
                    "avg_error_rate": round(float(row["avg_error_rate"]), 4),
                    "avg_latency_ms": round(float(row["avg_response_time"]), 2)  # 統一欄位名稱
                }
                services.append(service_data)
            
            return {
                "success": True,
                "data": {
                    "services": services,
                    "total_count": len(services)
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"獲取服務概覽失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SERVICES_OVERVIEW_ERROR",
                "message": "獲取服務概覽失敗",
                "developer_message": str(e)
            }
        )

@router.get("/{service_name}/health", response_model=Dict[str, Any])
async def get_service_health(
    service_name: str,
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    redis_conn: redis.Redis = Depends(get_redis_connection)
) -> Dict[str, Any]:
    """
    獲取指定服務的詳細健康狀態
    """
    try:
        async with db_pool.acquire() as conn:
            # 查詢服務基本信息
            service_query = """
                SELECT 
                    service_name,
                    COUNT(DISTINCT endpoint) as endpoint_count,
                    AVG(qps) as avg_qps,
                    AVG(error_rate) as avg_error_rate,
                    AVG(avg_response_time) as avg_response_time,
                    AVG(p95_response_time) as avg_p95_response_time,
                    AVG(p99_response_time) as avg_p99_response_time,
                    MAX(created_at) as last_seen,
                    SUM(total_requests) as total_requests,
                    SUM(total_errors) as total_errors
                FROM metrics_aggregated 
                WHERE service_name = $1 
                AND created_at >= NOW() - INTERVAL '24 hours'
                GROUP BY service_name
            """
            
            service_row = await conn.fetchrow(service_query, service_name)
            
            if not service_row:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "code": "SERVICE_NOT_FOUND",
                        "message": f"服務 '{service_name}' 不存在或無監控數據"
                    }
                )
            
            # 查詢端點健康狀態
            endpoints_query = """
                SELECT 
                    endpoint,
                    AVG(qps) as avg_qps,
                    AVG(error_rate) as avg_error_rate,
                    AVG(avg_response_time) as avg_response_time,
                    MAX(created_at) as last_seen
                FROM metrics_aggregated 
                WHERE service_name = $1 
                AND created_at >= NOW() - INTERVAL '1 hour'
                GROUP BY endpoint
                ORDER BY endpoint
            """
            
            endpoint_rows = await conn.fetch(endpoints_query, service_name)
            
            # 計算健康狀態
            last_seen = service_row["last_seen"]
            error_rate = float(service_row["avg_error_rate"])
            response_time = float(service_row["avg_response_time"])
            
            # 健康檢查邏輯
            health_checks = {
                "data_freshness": {
                    "status": "pass" if last_seen > datetime.utcnow() - timedelta(minutes=5) else "fail",
                    "message": f"最後數據時間: {last_seen.isoformat()}",
                    "threshold": "5 minutes"
                },
                "error_rate": {
                    "status": "pass" if error_rate <= 0.05 else "fail",
                    "message": f"錯誤率: {error_rate:.4f}",
                    "threshold": "≤ 5%"
                },
                "response_time": {
                    "status": "pass" if response_time <= 2000 else "fail",
                    "message": f"平均響應時間: {response_time:.2f}ms",
                    "threshold": "≤ 2000ms"
                }
            }
            
            # 總體健康狀態
            all_checks_pass = all(check["status"] == "pass" for check in health_checks.values())
            overall_status = "healthy" if all_checks_pass else "unhealthy"
            
            # 端點狀態
            endpoints_health = []
            for ep_row in endpoint_rows:
                ep_error_rate = float(ep_row["avg_error_rate"])
                ep_response_time = float(ep_row["avg_response_time"])
                ep_last_seen = ep_row["last_seen"]
                
                ep_status = "healthy"
                if ep_last_seen < datetime.utcnow() - timedelta(minutes=5):
                    ep_status = "stale"
                elif ep_error_rate > 0.05 or ep_response_time > 2000:
                    ep_status = "unhealthy"
                
                endpoints_health.append({
                    "api_endpoint": ep_row["endpoint"],  # 統一欄位名稱
                    "status": ep_status,
                    "avg_qps": round(float(ep_row["avg_qps"]), 2),
                    "avg_error_rate": round(ep_error_rate, 4),
                    "avg_latency_ms": round(ep_response_time, 2),  # 統一欄位名稱
                    "last_seen": ep_last_seen.isoformat()
                })
            
            # 從 Redis 獲取實時狀態
            real_time_key = f"service:status:{service_name}"
            real_time_data = await redis_conn.get(real_time_key)
            real_time_status = None
            if real_time_data:
                try:
                    import json
                    real_time_status = json.loads(real_time_data)
                except:
                    pass
            
            return {
                "success": True,
                "data": {
                    "service_name": service_name,
                    "overall_status": overall_status,
                    "health_checks": health_checks,
                    "metrics": {
                        "endpoint_count": service_row["endpoint_count"],
                        "avg_qps": round(float(service_row["avg_qps"]), 2),
                        "avg_error_rate": round(error_rate, 4),
                        "avg_latency_ms": round(response_time, 2),  # 統一欄位名稱
                        "p95_latency_ms": round(float(service_row["avg_p95_response_time"]), 2),  # 統一欄位名稱
                        "p99_latency_ms": round(float(service_row["avg_p99_response_time"]), 2),  # 統一欄位名稱
                        "total_requests": service_row["total_requests"],
                        "total_errors": service_row["total_errors"]
                    },
                    "endpoints": endpoints_health,
                    "real_time_status": real_time_status,
                    "last_updated": last_seen.isoformat()
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取服務健康狀態失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SERVICE_HEALTH_ERROR",
                "message": "獲取服務健康狀態失敗",
                "developer_message": str(e)
            }
        )

@router.get("/{service_name}/metrics/trend", response_model=Dict[str, Any])
async def get_service_metrics_trend(
    service_name: str,
    hours: int = Query(24, le=168, description="時間範圍（小時），最多7天"),
    interval: int = Query(60, description="聚合間隔（分鐘）"),
    db_pool: asyncpg.Pool = Depends(get_db_pool)
) -> Dict[str, Any]:
    """
    獲取服務指標趨勢數據
    """
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        async with db_pool.acquire() as conn:
            # 時間序列趨勢查詢
            trend_query = """
                SELECT 
                    DATE_TRUNC('hour', created_at) + 
                    INTERVAL '%s minutes' * FLOOR(EXTRACT(MINUTE FROM created_at) / %s) as time_bucket,
                    AVG(qps) as avg_qps,
                    AVG(error_rate) as avg_error_rate,
                    AVG(avg_response_time) as avg_response_time,
                    AVG(p95_response_time) as avg_p95_response_time,
                    SUM(total_requests) as total_requests,
                    SUM(total_errors) as total_errors
                FROM metrics_aggregated 
                WHERE service_name = $1 
                AND created_at >= $2 
                AND created_at <= $3
                GROUP BY time_bucket
                ORDER BY time_bucket
            """ % (interval, interval)
            
            trend_rows = await conn.fetch(trend_query, service_name, start_time, end_time)
            
            if not trend_rows:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "code": "NO_TREND_DATA",
                        "message": f"服務 '{service_name}' 在指定時間範圍內沒有趨勢數據"
                    }
                )
            
            # 構建趨勢數據
            trend_data = []
            for row in trend_rows:
                trend_data.append({
                    "timestamp": row["time_bucket"].isoformat(),
                    "qps": round(float(row["avg_qps"] or 0), 2),
                    "error_rate": round(float(row["avg_error_rate"] or 0), 4),
                    "avg_latency_ms": round(float(row["avg_response_time"] or 0), 2),  # 統一欄位名稱
                    "p95_latency_ms": round(float(row["avg_p95_response_time"] or 0), 2),  # 統一欄位名稱
                    "total_requests": row["total_requests"] or 0,
                    "total_errors": row["total_errors"] or 0
                })
            
            # 計算趨勢統計
            qps_values = [point["qps"] for point in trend_data]
            error_rates = [point["error_rate"] for point in trend_data]
            response_times = [point["avg_latency_ms"] for point in trend_data]  # 統一欄位名稱
            
            trends_analysis = {
                "qps": {
                    "min": min(qps_values) if qps_values else 0,
                    "max": max(qps_values) if qps_values else 0,
                    "avg": round(sum(qps_values) / len(qps_values), 2) if qps_values else 0
                },
                "error_rate": {
                    "min": min(error_rates) if error_rates else 0,
                    "max": max(error_rates) if error_rates else 0,
                    "avg": round(sum(error_rates) / len(error_rates), 4) if error_rates else 0
                },
                "latency_ms": {  # 統一欄位名稱
                    "min": min(response_times) if response_times else 0,
                    "max": max(response_times) if response_times else 0,
                    "avg": round(sum(response_times) / len(response_times), 2) if response_times else 0
                }
            }
            
            return {
                "success": True,
                "data": {
                    "service_name": service_name,
                    "time_range": {
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "hours": hours,
                        "interval_minutes": interval
                    },
                    "trend_data": trend_data,
                    "analysis": trends_analysis,
                    "data_points": len(trend_data)
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取服務趨勢數據失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SERVICE_TREND_ERROR",
                "message": "獲取服務趨勢數據失敗",
                "developer_message": str(e)
            }
        )

@router.get("/comparison", response_model=Dict[str, Any])
async def get_services_comparison(
    services: str = Query(..., description="服務名稱列表，逗號分隔"),
    hours: int = Query(24, le=168, description="比較時間範圍（小時）"),
    db_pool: asyncpg.Pool = Depends(get_db_pool)
) -> Dict[str, Any]:
    """
    比較多個服務的性能指標
    """
    try:
        service_list = [s.strip() for s in services.split(",") if s.strip()]
        if not service_list:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_SERVICES",
                    "message": "請提供至少一個服務名稱"
                }
            )
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        async with db_pool.acquire() as conn:
            # 查詢各服務的聚合指標
            comparison_data = {}
            
            for service_name in service_list:
                query = """
                    SELECT 
                        AVG(qps) as avg_qps,
                        AVG(error_rate) as avg_error_rate,
                        AVG(avg_response_time) as avg_response_time,
                        AVG(p95_response_time) as avg_p95_response_time,
                        AVG(p99_response_time) as avg_p99_response_time,
                        SUM(total_requests) as total_requests,
                        SUM(total_errors) as total_errors,
                        COUNT(DISTINCT endpoint) as endpoint_count,
                        MAX(created_at) as last_seen
                    FROM metrics_aggregated 
                    WHERE service_name = $1 
                    AND created_at >= $2 
                    AND created_at <= $3
                """
                
                row = await conn.fetchrow(query, service_name, start_time, end_time)
                
                if row and row["avg_qps"] is not None:
                    comparison_data[service_name] = {
                        "avg_qps": round(float(row["avg_qps"]), 2),
                        "avg_error_rate": round(float(row["avg_error_rate"]), 4),
                        "avg_latency_ms": round(float(row["avg_response_time"]), 2),  # 統一欄位名稱
                        "p95_latency_ms": round(float(row["avg_p95_response_time"]), 2),  # 統一欄位名稱
                        "p99_latency_ms": round(float(row["avg_p99_response_time"]), 2),  # 統一欄位名稱
                        "total_requests": row["total_requests"],
                        "total_errors": row["total_errors"],
                        "endpoint_count": row["endpoint_count"],
                        "last_seen": row["last_seen"].isoformat() if row["last_seen"] else None
                    }
                else:
                    comparison_data[service_name] = {
                        "avg_qps": 0,
                        "avg_error_rate": 0,
                        "avg_latency_ms": 0,  # 統一欄位名稱
                        "p95_latency_ms": 0,  # 統一欄位名稱
                        "p99_latency_ms": 0,  # 統一欄位名稱
                        "total_requests": 0,
                        "total_errors": 0,
                        "endpoint_count": 0,
                        "last_seen": None,
                        "note": "無數據"
                    }
            
            # 計算排名
            rankings = {
                "best_qps": sorted(comparison_data.items(), key=lambda x: x[1]["avg_qps"], reverse=True),
                "best_error_rate": sorted(comparison_data.items(), key=lambda x: x[1]["avg_error_rate"]),
                "best_latency": sorted(comparison_data.items(), key=lambda x: x[1]["avg_latency_ms"])  # 統一欄位名稱
            }
            
            return {
                "success": True,
                "data": {
                    "services": list(service_list),
                    "time_range": {
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "hours": hours
                    },
                    "comparison": comparison_data,
                    "rankings": {
                        "highest_qps": rankings["best_qps"][0][0] if rankings["best_qps"] else None,
                        "lowest_error_rate": rankings["best_error_rate"][0][0] if rankings["best_error_rate"] else None,
                        "fastest_latency": rankings["best_latency"][0][0] if rankings["best_latency"] else None  # 統一欄位名稱
                    }
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"服務比較失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SERVICES_COMPARISON_ERROR",
                "message": "服務比較失敗",
                "developer_message": str(e)
            }
        ) 