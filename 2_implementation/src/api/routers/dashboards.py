"""
儀表板數據 API 路由
提供綜合監控儀表板所需的數據
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Query
import asyncpg
import redis.asyncio as redis

from ..dependencies import verify_api_key, get_redis_connection, get_db_pool

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/v1/dashboards",
    tags=["儀表板數據"],
    dependencies=[Depends(verify_api_key)]
)

@router.get("/overview", response_model=Dict[str, Any])
async def get_dashboard_overview(
    time_range: int = Query(3600, description="時間範圍（秒），默認1小時"),
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    redis_conn: redis.Redis = Depends(get_redis_connection)
) -> Dict[str, Any]:
    """
    獲取儀表板概覽數據
    包含系統整體狀態、關鍵指標和實時統計
    """
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(seconds=time_range)
        
        async with db_pool.acquire() as conn:
            # 1. 系統整體統計
            overview_query = """
                SELECT 
                    COUNT(DISTINCT service_name) as total_services,
                    COUNT(DISTINCT endpoint) as total_endpoints,
                    SUM(total_requests) as total_requests,
                    SUM(total_errors) as total_errors,
                    AVG(qps) as avg_qps,
                    AVG(error_rate) as avg_error_rate,
                    AVG(avg_response_time) as avg_response_time
                FROM metrics_aggregated 
                WHERE created_at >= $1 AND created_at <= $2
            """
            
            overview = await conn.fetchrow(overview_query, start_time, end_time)
            
            # 2. 服務健康狀態統計
            health_query = """
                SELECT 
                    service_name,
                    AVG(error_rate) as avg_error_rate,
                    AVG(avg_response_time) as avg_response_time,
                    MAX(created_at) as last_seen
                FROM metrics_aggregated 
                WHERE created_at >= $1 AND created_at <= $2
                GROUP BY service_name
            """
            
            health_rows = await conn.fetch(health_query, start_time, end_time)
            
            # 計算健康狀態
            healthy = 0
            unhealthy = 0
            unknown = 0
            
            for row in health_rows:
                last_seen = row["last_seen"]
                error_rate = float(row["avg_error_rate"])
                response_time = float(row["avg_response_time"])
                
                # 確保時區一致性
                now = datetime.utcnow()
                if last_seen and hasattr(last_seen, 'replace'):
                    if last_seen.tzinfo is not None:
                        last_seen = last_seen.replace(tzinfo=None)
                
                if last_seen and last_seen > now - timedelta(minutes=5):
                    if error_rate > 0.05 or response_time > 2000:
                        unhealthy += 1
                    else:
                        healthy += 1
                else:
                    unknown += 1
            
            # 3. 頂級指標服務
            top_services_query = """
                SELECT 
                    service_name,
                    AVG(qps) as avg_qps,
                    AVG(error_rate) as avg_error_rate,
                    AVG(avg_response_time) as avg_response_time
                FROM metrics_aggregated 
                WHERE created_at >= $1 AND created_at <= $2
                GROUP BY service_name
                ORDER BY avg_qps DESC
                LIMIT 5
            """
            
            top_services = await conn.fetch(top_services_query, start_time, end_time)
            
        # 4. 從 Redis 獲取實時告警統計
        alert_keys = await redis_conn.keys("alert:active:*")
        active_alerts_count = len(alert_keys)
        
        # 分析告警嚴重程度
        critical_alerts = 0
        high_alerts = 0
        medium_alerts = 0
        low_alerts = 0
        
        for key in alert_keys:
            try:
                alert_data = await redis_conn.get(key)
                if alert_data:
                    import json
                    alert = json.loads(alert_data)
                    severity = alert.get("severity", "low")
                    
                    if severity == "critical":
                        critical_alerts += 1
                    elif severity == "high":
                        high_alerts += 1
                    elif severity == "medium":
                        medium_alerts += 1
                    else:
                        low_alerts += 1
            except:
                continue
        
        # 5. 構建響應數據
        return {
            "success": True,
            "data": {
                "system_overview": {
                    "total_services": overview["total_services"] or 0,
                    "total_endpoints": overview["total_endpoints"] or 0,
                    "total_requests": overview["total_requests"] or 0,
                    "total_errors": overview["total_errors"] or 0,
                    "avg_qps": round(float(overview["avg_qps"] or 0), 2),
                    "avg_error_rate": round(float(overview["avg_error_rate"] or 0), 4),
                    "avg_response_time": round(float(overview["avg_response_time"] or 0), 2)
                },
                "service_health": {
                    "healthy": healthy,
                    "unhealthy": unhealthy,
                    "unknown": unknown,
                    "total": healthy + unhealthy + unknown,
                    "health_percentage": round((healthy / (healthy + unhealthy + unknown) * 100) if (healthy + unhealthy + unknown) > 0 else 0, 1)
                },
                "alerts_summary": {
                    "total_active": active_alerts_count,
                    "critical": critical_alerts,
                    "high": high_alerts,
                    "medium": medium_alerts,
                    "low": low_alerts
                },
                "top_services": [
                    {
                        "service_name": row["service_name"],
                        "avg_qps": round(float(row["avg_qps"]), 2),
                        "avg_error_rate": round(float(row["avg_error_rate"]), 4),
                        "avg_response_time": round(float(row["avg_response_time"]), 2)
                    }
                    for row in top_services
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
        logger.error(f"獲取儀表板概覽失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "DASHBOARD_OVERVIEW_ERROR",
                "message": "獲取儀表板概覽失敗",
                "developer_message": str(e)
            }
        )

@router.get("/metrics/timeseries", response_model=Dict[str, Any])
async def get_metrics_timeseries(
    metric: str = Query(..., description="指標類型: qps, error_rate, response_time"),
    service_name: Optional[str] = Query(None, description="服務名稱過濾"),
    hours: int = Query(24, le=168, description="時間範圍（小時）"),
    interval: int = Query(60, description="聚合間隔（分鐘）"),
    db_pool: asyncpg.Pool = Depends(get_db_pool)
) -> Dict[str, Any]:
    """
    獲取指標時間序列數據，用於圖表展示
    """
    try:
        # 驗證指標類型
        valid_metrics = ["qps", "error_rate", "response_time", "p95_response_time", "p99_response_time"]
        if metric not in valid_metrics:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_METRIC",
                    "message": f"無效的指標類型，支持的類型: {', '.join(valid_metrics)}"
                }
            )
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # 構建指標欄位映射
        metric_field_map = {
            "qps": "qps",
            "error_rate": "error_rate", 
            "response_time": "avg_response_time",
            "p95_response_time": "p95_response_time",
            "p99_response_time": "p99_response_time"
        }
        
        metric_field = metric_field_map[metric]
        
        async with db_pool.acquire() as conn:
            # 構建查詢條件
            where_conditions = ["created_at >= $1", "created_at <= $2"]
            params = [start_time, end_time]
            
            if service_name:
                where_conditions.append("service_name = $3")
                params.append(service_name)
            
            where_clause = " AND ".join(where_conditions)
            
            # 時間序列查詢
            timeseries_query = f"""
                SELECT 
                    DATE_TRUNC('hour', created_at) + 
                    INTERVAL '{interval} minutes' * FLOOR(EXTRACT(MINUTE FROM created_at) / {interval}) as time_bucket,
                    AVG({metric_field}) as metric_value,
                    COUNT(*) as data_points
                FROM metrics_aggregated 
                WHERE {where_clause}
                GROUP BY time_bucket
                ORDER BY time_bucket
            """
            
            rows = await conn.fetch(timeseries_query, *params)
            
            # 構建時間序列數據
            timeseries_data = []
            for row in rows:
                timeseries_data.append({
                    "timestamp": row["time_bucket"].isoformat(),
                    "value": round(float(row["metric_value"] or 0), 4),
                    "data_points": row["data_points"]
                })
            
            # 計算統計信息
            values = [point["value"] for point in timeseries_data]
            statistics = {
                "min": min(values) if values else 0,
                "max": max(values) if values else 0,
                "avg": round(sum(values) / len(values), 4) if values else 0,
                "data_points": len(timeseries_data)
            }
            
            return {
                "success": True,
                "data": {
                    "metric": metric,
                    "service_name": service_name,
                    "time_range": {
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "hours": hours,
                        "interval_minutes": interval
                    },
                    "timeseries": timeseries_data,
                    "statistics": statistics
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取時間序列數據失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "TIMESERIES_ERROR",
                "message": "獲取時間序列數據失敗",
                "developer_message": str(e)
            }
        )

@router.get("/realtime", response_model=Dict[str, Any])
async def get_realtime_dashboard(
    redis_conn: redis.Redis = Depends(get_redis_connection)
) -> Dict[str, Any]:
    """
    獲取實時儀表板數據
    """
    try:
        # 從 Redis 獲取實時指標，添加錯誤處理
        try:
            metric_keys = await redis_conn.keys("metrics:*")
        except Exception as e:
            logger.warning(f"Redis 連接失敗，返回空實時儀表板: {e}")
            metric_keys = []
        
        # 聚合實時指標
        total_qps = 0
        total_errors = 0
        total_requests = 0
        response_times = []
        services_data = {}
        
        for key in metric_keys:
            try:
                data = await redis_conn.get(key)
                if data:
                    import json
                    metric = json.loads(data)
                    
                    qps = metric.get("qps", 0)
                    error_rate = metric.get("error_rate", 0)
                    response_time = metric.get("avg_response_time", 0)
                    service_name = metric.get("service_name", "unknown")
                    
                    total_qps += qps
                    total_errors += error_rate * qps  # 計算總錯誤數
                    total_requests += qps
                    
                    if response_time > 0:
                        response_times.append(response_time)
                    
                    # 服務數據聚合
                    if service_name not in services_data:
                        services_data[service_name] = {
                            "name": service_name,
                            "status": "healthy",
                            "qps": 0,
                            "error_rate": 0,
                            "avg_response_time": 0,
                            "last_seen": metric.get("timestamp")
                        }
                    
                    svc_data = services_data[service_name]
                    svc_data["qps"] += qps
                    svc_data["error_rate"] = max(svc_data["error_rate"], error_rate)
                    svc_data["avg_response_time"] = max(svc_data["avg_response_time"], response_time)
                    
                    # 狀態判斷
                    if error_rate > 0.1 or response_time > 2000:
                        svc_data["status"] = "unhealthy"
                    elif error_rate > 0.05 or response_time > 1000:
                        svc_data["status"] = "warning"
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"解析實時指標數據失敗 {key}: {e}")
                continue
        
        # 計算全局指標
        overall_error_rate = (total_errors / total_requests) if total_requests > 0 else 0
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # 獲取告警統計，添加錯誤處理
        alert_summary = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "total_active": 0
        }
        
        try:
            alert_keys = await redis_conn.keys("alert:active:*")
            for key in alert_keys:
                try:
                    alert_data = await redis_conn.get(key)
                    if alert_data:
                        import json
                        alert = json.loads(alert_data)
                        severity = alert.get("severity", "low")
                        if severity in alert_summary:
                            alert_summary[severity] += 1
                        alert_summary["total_active"] += 1
                except Exception as e:
                    logger.warning(f"解析告警數據失敗 {key}: {e}")
                    continue
        except Exception as e:
            logger.warning(f"獲取告警數據失敗: {e}")
        
        return {
            "success": True,
            "data": {
                "real_time_metrics": {
                    "total_qps": round(total_qps, 2),
                    "overall_error_rate": round(overall_error_rate, 4),
                    "avg_response_time": round(avg_response_time, 2),
                    "total_services": len(services_data)
                },
                "services_status": list(services_data.values()),
                "alerts_summary": alert_summary,
                "last_updated": datetime.utcnow().isoformat()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"獲取實時儀表板失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "REALTIME_DASHBOARD_ERROR",
                "message": "獲取實時儀表板失敗",
                "developer_message": str(e)
            }
        ) 