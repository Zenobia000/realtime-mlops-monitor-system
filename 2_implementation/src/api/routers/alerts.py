"""
告警管理 API 路由
提供告警查詢、管理和配置功能
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
import asyncpg
import redis.asyncio as redis

from ..dependencies import verify_api_key, get_db_connection, get_redis_connection, get_db_pool

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/v1/alerts",
    tags=["告警管理"],
    dependencies=[Depends(verify_api_key)]
)

# 告警嚴重程度枚舉
class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertStatus(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"

# 請求/響應模型
class AlertRule(BaseModel):
    """告警規則模型"""
    id: Optional[int] = None
    rule_name: str = Field(..., description="規則名稱")
    rule_type: str = Field(..., description="規則類型: high_error_rate, high_response_time, low_qps 等")
    threshold: float = Field(..., description="閾值")
    severity: AlertSeverity = Field(..., description="嚴重程度")
    enabled: bool = Field(True, description="是否啟用")
    service_name: Optional[str] = Field(None, description="目標服務名稱，為空表示全部服務")
    endpoint: Optional[str] = Field(None, description="目標端點，為空表示全部端點")
    description: Optional[str] = Field(None, description="規則描述")

class Alert(BaseModel):
    """告警模型"""
    id: int
    rule_name: str
    service_name: str
    endpoint: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    threshold: float
    actual_value: float
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None

@router.get("/", response_model=Dict[str, Any])
async def get_alerts(
    status: Optional[AlertStatus] = Query(None, description="告警狀態過濾"),
    severity: Optional[AlertSeverity] = Query(None, description="嚴重程度過濾"),
    service_name: Optional[str] = Query(None, description="服務名稱過濾"),
    limit: int = Query(50, le=500, description="返回記錄數限制"),
    offset: int = Query(0, description="分頁偏移"),
    redis_conn: redis.Redis = Depends(get_redis_connection)
) -> Dict[str, Any]:
    """
    查詢告警列表
    支持狀態、嚴重程度、服務名稱和時間範圍過濾
    """
    try:
        # 從 Redis 獲取告警數據，添加錯誤處理
        try:
            alert_keys = await redis_conn.keys("alert:*")
        except Exception as e:
            logger.warning(f"Redis 連接失敗，返回空告警列表: {e}")
            alert_keys = []
        
        alerts = []
        for key in alert_keys:
            try:
                alert_data = await redis_conn.get(key)
                if alert_data:
                    import json
                    alert = json.loads(alert_data)
                    
                    # 過濾條件
                    if status and alert.get("status") != status:
                        continue
                    if severity and alert.get("severity") != severity:
                        continue
                    if service_name and alert.get("service_name") != service_name:
                        continue
                    
                    alerts.append(alert)
            except Exception as e:
                logger.warning(f"解析告警數據失敗 {key}: {e}")
                continue
        
        # 按觸發時間排序
        alerts.sort(key=lambda x: x.get("triggered_at", ""), reverse=True)
        
        # 分頁處理
        total_count = len(alerts)
        paginated_alerts = alerts[offset:offset + limit]
        
        return {
            "success": True,
            "data": {
                "alerts": paginated_alerts,
                "pagination": {
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + limit < total_count
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"查詢告警失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "ALERTS_QUERY_ERROR",
                "message": "查詢告警失敗",
                "developer_message": str(e)
            }
        )

@router.get("/active", response_model=Dict[str, Any])
async def get_active_alerts(
    severity: Optional[AlertSeverity] = Query(None, description="嚴重程度過濾"),
    redis_conn: redis.Redis = Depends(get_redis_connection)
) -> Dict[str, Any]:
    """
    獲取當前活躍告警
    """
    try:
        # 獲取活躍告警，添加錯誤處理
        try:
            alert_keys = await redis_conn.keys("alert:active:*")
        except Exception as e:
            logger.warning(f"Redis 連接失敗，返回空活躍告警列表: {e}")
            alert_keys = []
        
        active_alerts = []
        for key in alert_keys:
            try:
                alert_data = await redis_conn.get(key)
                if alert_data:
                    import json
                    alert = json.loads(alert_data)
                    
                    if severity and alert.get("severity") != severity:
                        continue
                    
                    active_alerts.append(alert)
            except Exception as e:
                logger.warning(f"解析活躍告警數據失敗 {key}: {e}")
                continue
        
        # 按嚴重程度排序
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        active_alerts.sort(
            key=lambda x: severity_order.get(x.get("severity", "low"), 3)
        )
        
        return {
            "success": True,
            "data": {
                "active_alerts": active_alerts,
                "total_active": len(active_alerts)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"獲取活躍告警失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "ACTIVE_ALERTS_ERROR",
                "message": "獲取活躍告警失敗",
                "developer_message": str(e)
            }
        )

@router.get("/rules", response_model=Dict[str, Any])
async def get_alert_rules(
    enabled: Optional[bool] = Query(None, description="是否啟用過濾"),
    rule_type: Optional[str] = Query(None, description="規則類型過濾"),
    redis_conn: redis.Redis = Depends(get_redis_connection)
) -> Dict[str, Any]:
    """
    獲取告警規則列表
    """
    try:
        # 從 Redis 獲取告警規則 (模擬實際存儲)
        # 實際實現中可能從資料庫或配置文件讀取
        rules_key = "alert:rules"
        rules_data = await redis_conn.get(rules_key)
        
        if not rules_data:
            # 提供默認規則
            default_rules = [
                {
                    "id": 1,
                    "rule_name": "高錯誤率告警",
                    "rule_type": "high_error_rate",
                    "threshold": 0.05,
                    "severity": "high",
                    "enabled": True,
                    "description": "當錯誤率超過 5% 時觸發告警"
                },
                {
                    "id": 2, 
                    "rule_name": "高響應時間告警",
                    "rule_type": "high_response_time",
                    "threshold": 2000.0,
                    "severity": "medium",
                    "enabled": True,
                    "description": "當平均響應時間超過 2000ms 時觸發告警"
                },
                {
                    "id": 3,
                    "rule_name": "低 QPS 告警", 
                    "rule_type": "low_qps",
                    "threshold": 1.0,
                    "severity": "low",
                    "enabled": True,
                    "description": "當 QPS 低於 1.0 時觸發告警"
                },
                {
                    "id": 4,
                    "rule_name": "P99 延遲告警",
                    "rule_type": "high_p99_latency",
                    "threshold": 5000.0,
                    "severity": "high",
                    "enabled": True,
                    "description": "當 P99 延遲超過 5000ms 時觸發告警"
                },
                {
                    "id": 5,
                    "rule_name": "零請求告警",
                    "rule_type": "zero_requests",
                    "threshold": 0.0,
                    "severity": "critical",
                    "enabled": True,
                    "description": "當檢測到零請求時觸發告警"
                }
            ]
            rules = default_rules
        else:
            import json
            rules = json.loads(rules_data)
        
        # 應用過濾條件
        filtered_rules = rules
        if enabled is not None:
            filtered_rules = [r for r in filtered_rules if r.get("enabled") == enabled]
        if rule_type:
            filtered_rules = [r for r in filtered_rules if r.get("rule_type") == rule_type]
        
        # 統計信息
        enabled_count = len([r for r in rules if r.get("enabled", False)])
        disabled_count = len([r for r in rules if not r.get("enabled", False)])
        
        rule_types = list(set(r.get("rule_type") for r in rules))
        
        return {
            "success": True,
            "data": {
                "rules": filtered_rules,
                "statistics": {
                    "total_rules": len(rules),
                    "enabled_rules": enabled_count,
                    "disabled_rules": disabled_count,
                    "rule_types": rule_types
                },
                "filters": {
                    "enabled": enabled,
                    "rule_type": rule_type
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"獲取告警規則失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "ALERT_RULES_ERROR",
                "message": "獲取告警規則失敗",
                "developer_message": str(e)
            }
        )

@router.post("/{alert_id}/acknowledge", response_model=Dict[str, Any])
async def acknowledge_alert(
    alert_id: int,
    redis_conn: redis.Redis = Depends(get_redis_connection)
) -> Dict[str, Any]:
    """
    確認告警
    """
    try:
        # 查找告警
        alert_key = f"alert:active:{alert_id}"
        alert_data = await redis_conn.get(alert_key)
        
        if not alert_data:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "ALERT_NOT_FOUND",
                    "message": f"告警 ID {alert_id} 不存在或已不活躍"
                }
            )
        
        import json
        alert = json.loads(alert_data)
        
        # 更新告警狀態
        alert["status"] = "acknowledged"
        alert["acknowledged_at"] = datetime.utcnow().isoformat()
        
        # 保存更新後的告警
        await redis_conn.set(alert_key, json.dumps(alert))
        
        # 同時保存到歷史記錄
        history_key = f"alert:history:{alert_id}"
        await redis_conn.set(history_key, json.dumps(alert), ex=86400 * 30)  # 保存30天
        
        return {
            "success": True,
            "data": {
                "alert_id": alert_id,
                "status": "acknowledged",
                "acknowledged_at": alert["acknowledged_at"],
                "message": "告警已確認"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"確認告警失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "ACKNOWLEDGE_ALERT_ERROR",
                "message": "確認告警失敗",
                "developer_message": str(e)
            }
        )

@router.post("/{alert_id}/resolve", response_model=Dict[str, Any])
async def resolve_alert(
    alert_id: int,
    redis_conn: redis.Redis = Depends(get_redis_connection)
) -> Dict[str, Any]:
    """
    解決告警
    """
    try:
        # 查找告警
        alert_key = f"alert:active:{alert_id}"
        alert_data = await redis_conn.get(alert_key)
        
        if not alert_data:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "ALERT_NOT_FOUND",
                    "message": f"告警 ID {alert_id} 不存在或已不活躍"
                }
            )
        
        import json
        alert = json.loads(alert_data)
        
        # 更新告警狀態
        alert["status"] = "resolved"
        alert["resolved_at"] = datetime.utcnow().isoformat()
        
        # 移動到已解決告警
        resolved_key = f"alert:resolved:{alert_id}"
        await redis_conn.set(resolved_key, json.dumps(alert), ex=86400 * 30)  # 保存30天
        
        # 從活躍告警中移除
        await redis_conn.delete(alert_key)
        
        return {
            "success": True,
            "data": {
                "alert_id": alert_id,
                "status": "resolved",
                "resolved_at": alert["resolved_at"],
                "message": "告警已解決"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解決告警失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "RESOLVE_ALERT_ERROR",
                "message": "解決告警失敗",
                "developer_message": str(e)
            }
        )

@router.get("/statistics", response_model=Dict[str, Any])
async def get_alert_statistics(
    time_range: Optional[int] = Query(86400, description="時間範圍（秒），默認24小時"),
    redis_conn: redis.Redis = Depends(get_redis_connection)
) -> Dict[str, Any]:
    """
    獲取告警統計信息
    """
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(seconds=time_range)
        
        # 獲取所有告警數據
        all_alert_keys = await redis_conn.keys("alert:*")
        
        alerts_in_range = []
        active_alerts = []
        resolved_alerts = []
        
        for key in all_alert_keys:
            try:
                alert_data = await redis_conn.get(key)
                if alert_data:
                    import json
                    alert = json.loads(alert_data)
                    
                    # 檢查時間範圍
                    triggered_at = datetime.fromisoformat(alert.get("triggered_at", ""))
                    if start_time <= triggered_at <= end_time:
                        alerts_in_range.append(alert)
                    
                    # 分類統計
                    if alert.get("status") == "active":
                        active_alerts.append(alert)
                    elif alert.get("status") == "resolved":
                        resolved_alerts.append(alert)
                        
            except (json.JSONDecodeError, ValueError, Exception) as e:
                logger.warning(f"解析告警統計數據失敗 {key}: {e}")
                continue
        
        # 按嚴重程度統計
        severity_stats = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        service_stats = {}
        rule_type_stats = {}
        
        for alert in alerts_in_range:
            severity = alert.get("severity", "low")
            service = alert.get("service_name", "unknown")
            rule_type = alert.get("rule_name", "unknown")
            
            severity_stats[severity] = severity_stats.get(severity, 0) + 1
            service_stats[service] = service_stats.get(service, 0) + 1
            rule_type_stats[rule_type] = rule_type_stats.get(rule_type, 0) + 1
        
        # 計算解決率
        total_alerts = len(alerts_in_range)
        resolved_count = len([a for a in alerts_in_range if a.get("status") == "resolved"])
        resolution_rate = (resolved_count / total_alerts * 100) if total_alerts > 0 else 0
        
        return {
            "success": True,
            "data": {
                "summary": {
                    "total_alerts_in_period": total_alerts,
                    "active_alerts": len(active_alerts),
                    "resolved_alerts": len(resolved_alerts),
                    "resolution_rate_percent": round(resolution_rate, 2)
                },
                "severity_distribution": severity_stats,
                "service_distribution": dict(sorted(service_stats.items(), key=lambda x: x[1], reverse=True)),
                "rule_type_distribution": dict(sorted(rule_type_stats.items(), key=lambda x: x[1], reverse=True)),
                "time_range": {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": time_range
                },
                "trends": {
                    "most_affected_service": max(service_stats.items(), key=lambda x: x[1])[0] if service_stats else None,
                    "most_common_rule": max(rule_type_stats.items(), key=lambda x: x[1])[0] if rule_type_stats else None,
                    "dominant_severity": max(severity_stats.items(), key=lambda x: x[1])[0] if any(severity_stats.values()) else None
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"獲取告警統計失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "ALERT_STATISTICS_ERROR",
                "message": "獲取告警統計失敗",
                "developer_message": str(e)
            }
        ) 