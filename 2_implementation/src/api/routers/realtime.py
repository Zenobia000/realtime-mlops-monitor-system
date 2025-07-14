"""
WebSocket 實時數據 API 路由
提供實時監控數據推送
"""

import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
import redis.asyncio as redis

from ..dependencies import get_redis_connection

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/v1/ws",
    tags=["WebSocket 實時數據"]
)

class ConnectionManager:
    """WebSocket 連接管理器"""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """接受新連接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"新的 WebSocket 連接，當前連接數: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """斷開連接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket 連接斷開，當前連接數: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """發送個人消息"""
        try:
            await websocket.send_text(message)
        except:
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        """廣播消息給所有連接"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)
        
        # 清理斷開的連接
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()

@router.websocket("/metrics")
async def websocket_metrics_endpoint(websocket: WebSocket):
    """
    實時指標數據 WebSocket 端點
    """
    await manager.connect(websocket)
    
    try:
        # 獲取 Redis 連接
        redis_client = redis.Redis(host='localhost', port=6380, password='admin123', db=0, decode_responses=True)
        
        while True:
            try:
                # 每5秒推送一次實時數據
                await asyncio.sleep(5)
                
                # 從 Redis 獲取實時指標
                metrics_keys = await redis_client.keys("metrics:*")
                
                real_time_metrics = []
                for key in metrics_keys:
                    try:
                        data = await redis_client.get(key)
                        if data:
                            metric_data = json.loads(data)
                            real_time_metrics.append(metric_data)
                    except:
                        continue
                
                # 構建實時數據響應
                real_time_data = {
                    "type": "metrics_update",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "metrics": real_time_metrics,
                        "summary": {
                            "total_metrics": len(real_time_metrics),
                            "total_qps": sum(m.get("qps", 0) for m in real_time_metrics),
                            "avg_error_rate": sum(m.get("error_rate", 0) for m in real_time_metrics) / len(real_time_metrics) if real_time_metrics else 0,
                            "avg_response_time": sum(m.get("avg_response_time", 0) for m in real_time_metrics) / len(real_time_metrics) if real_time_metrics else 0
                        }
                    }
                }
                
                await manager.send_personal_message(json.dumps(real_time_data), websocket)
                
            except Exception as e:
                logger.error(f"推送實時數據失敗: {e}")
                break
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket 錯誤: {e}")
        manager.disconnect(websocket)

@router.websocket("/alerts")
async def websocket_alerts_endpoint(websocket: WebSocket):
    """
    實時告警數據 WebSocket 端點
    """
    await manager.connect(websocket)
    
    try:
        redis_client = redis.Redis(host='localhost', port=6380, password='admin123', db=0, decode_responses=True)
        
        while True:
            try:
                await asyncio.sleep(3)
                
                # 獲取活躍告警
                alert_keys = await redis_client.keys("alert:active:*")
                
                active_alerts = []
                for key in alert_keys:
                    try:
                        alert_data = await redis_client.get(key)
                        if alert_data:
                            alert = json.loads(alert_data)
                            active_alerts.append(alert)
                    except:
                        continue
                
                # 構建告警數據響應
                alerts_data = {
                    "type": "alerts_update",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "active_alerts": active_alerts,
                        "total_active": len(active_alerts),
                        "severity_counts": {
                            "critical": len([a for a in active_alerts if a.get("severity") == "critical"]),
                            "high": len([a for a in active_alerts if a.get("severity") == "high"]),
                            "medium": len([a for a in active_alerts if a.get("severity") == "medium"]),
                            "low": len([a for a in active_alerts if a.get("severity") == "low"])
                        }
                    }
                }
                
                await manager.send_personal_message(json.dumps(alerts_data), websocket)
                
            except Exception as e:
                logger.error(f"推送告警數據失敗: {e}")
                break
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket 錯誤: {e}")
        manager.disconnect(websocket) 