"""
Model API 監控攔截器
實現非侵入式 API 監控，收集性能指標並發送到 RabbitMQ
"""

import asyncio
import time
import logging
from typing import Callable, Optional, Dict, Any, Union
from datetime import datetime
import traceback

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, StreamingResponse
import uuid

from .metrics_event import MetricsEvent, EventType
from .event_publisher import EventPublisher, publish_metrics_event_async
from ..api.config import get_settings

logger = logging.getLogger(__name__)

class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    FastAPI 監控中間件
    
    實現非侵入式 API 請求監控：
    1. 攔截所有 HTTP 請求
    2. 測量響應時間
    3. 記錄請求/響應元數據
    4. 異步發送監控事件到 RabbitMQ
    5. 確保額外延遲 < 20ms
    """
    
    def __init__(
        self, 
        app: FastAPI,
        service_name: str = "unknown-service",
        enable_detailed_logging: bool = False,
        exclude_paths: Optional[list[str]] = None
    ):
        """
        初始化監控中間件
        
        Args:
            app: FastAPI 應用實例
            service_name: 服務名稱，用於事件標識
            enable_detailed_logging: 是否啟用詳細日誌
            exclude_paths: 要排除監控的路徑列表
        """
        super().__init__(app)
        self.service_name = service_name
        self.enable_detailed_logging = enable_detailed_logging
        self.exclude_paths = exclude_paths or [
            "/health", 
            "/docs", 
            "/redoc", 
            "/openapi.json",
            "/favicon.ico"
        ]
        
        self.settings = get_settings()
        self.event_publisher: Optional[EventPublisher] = None
        
        # 性能統計
        self.stats = {
            "total_requests": 0,
            "total_events_sent": 0,
            "total_send_failures": 0,
            "avg_middleware_overhead_ms": 0.0
        }
        
        logger.info(f"🔍 監控中間件已初始化 - 服務: {service_name}")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        處理 HTTP 請求的核心邏輯
        
        Args:
            request: FastAPI 請求對象
            call_next: 下一個中間件或路由處理器
            
        Returns:
            Response: HTTP 響應
        """
        # 記錄中間件開始時間（用於計算中間件自身開銷）
        middleware_start = time.perf_counter()
        
        # 生成追蹤 ID
        trace_id = str(uuid.uuid4())
        request.state.trace_id = trace_id
        
        # 檢查是否需要排除此路徑
        if self._should_exclude_path(request.url.path):
            return await call_next(request)
        
        # 記錄請求開始時間
        request_start = time.perf_counter()
        
        # 提取請求信息
        request_info = await self._extract_request_info(request)
        
        # 初始化響應相關變量
        response = None
        error_message = None
        error_type = None
        status_code = 500
        
        try:
            # 調用下一個處理器
            response = await call_next(request)
            status_code = response.status_code
            
        except Exception as e:
            # 捕獲並記錄異常
            error_message = str(e)
            error_type = type(e).__name__
            status_code = 500
            
            logger.error(f"API 請求處理異常: {error_message}")
            if self.enable_detailed_logging:
                logger.error(f"異常堆棧: {traceback.format_exc()}")
            
            # 創建錯誤響應
            response = JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "內部伺服器錯誤",
                        "trace_id": trace_id
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # 計算響應時間
        request_end = time.perf_counter()
        response_time_ms = (request_end - request_start) * 1000
        
        # 提取響應信息
        response_info = self._extract_response_info(response)
        
        # 創建監控事件（不阻塞主流程）
        asyncio.create_task(
            self._create_and_send_event(
                request_info,
                response_info,
                response_time_ms,
                status_code,
                error_message,
                error_type,
                trace_id
            )
        )
        
        # 更新統計
        self.stats["total_requests"] += 1
        middleware_end = time.perf_counter()
        middleware_overhead = (middleware_end - middleware_start) * 1000
        
        # 更新平均中間件開銷
        total_requests = self.stats["total_requests"]
        current_avg = self.stats["avg_middleware_overhead_ms"]
        self.stats["avg_middleware_overhead_ms"] = (
            (current_avg * (total_requests - 1) + middleware_overhead) / total_requests
        )
        
        # 記錄性能警告
        if middleware_overhead > 20:  # WBS 要求 < 20ms
            logger.warning(
                f"⚠️ 監控中間件開銷超標: {middleware_overhead:.2f}ms > 20ms "
                f"(請求: {request.url.path})"
            )
        
        if self.enable_detailed_logging:
            logger.debug(
                f"📊 請求監控完成: {request.method} {request.url.path} "
                f"- 狀態: {status_code}, 耗時: {response_time_ms:.2f}ms, "
                f"中間件開銷: {middleware_overhead:.2f}ms"
            )
        
        return response
    
    def _should_exclude_path(self, path: str) -> bool:
        """檢查路徑是否應該被排除"""
        return any(excluded in path for excluded in self.exclude_paths)
    
    async def _extract_request_info(self, request: Request) -> Dict[str, Any]:
        """
        提取請求信息
        
        Args:
            request: FastAPI 請求對象
            
        Returns:
            Dict: 請求信息字典
        """
        try:
            # 獲取客戶端 IP
            client_ip = None
            if hasattr(request, 'client') and request.client:
                client_ip = request.client.host
            
            # 從 headers 中獲取真實 IP（考慮代理）
            forwarded_for = request.headers.get('x-forwarded-for')
            if forwarded_for:
                client_ip = forwarded_for.split(',')[0].strip()
            
            # 獲取請求大小
            content_length = request.headers.get('content-length')
            request_size = int(content_length) if content_length else None
            
            # 提取模型版本資訊（從請求體）
            model_version = None
            model_metadata = {}
            
            # 只對預測相關端點解析請求體
            if request.method == "POST" and ("/predict" in request.url.path):
                try:
                    # 獲取請求體
                    body = await request.body()
                    if body:
                        import json
                        request_data = json.loads(body.decode())
                        
                        # 提取模型版本
                        model_version = request_data.get("model_version")
                        
                        # 提取其他有用的元數據
                        metadata = request_data.get("metadata", {})
                        if metadata:
                            model_metadata.update({
                                "feature_type": metadata.get("feature_type"),
                                "category": metadata.get("category"),
                                "region": metadata.get("region")
                            })
                        
                        # 重建請求體供後續處理使用
                        request._body = body
                        
                except Exception as e:
                    logger.debug(f"解析請求體失敗: {e}")
            
            return {
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params) if request.query_params else None,
                "client_ip": client_ip,
                "user_agent": request.headers.get('user-agent'),
                "content_type": request.headers.get('content-type'),
                "request_size_bytes": request_size,
                "headers": dict(request.headers) if self.enable_detailed_logging else None,
                "model_version": model_version,
                "model_metadata": model_metadata
            }
            
        except Exception as e:
            logger.warning(f"提取請求信息失敗: {e}")
            return {
                "method": request.method,
                "path": request.url.path,
                "client_ip": None,
                "user_agent": None,
                "request_size_bytes": None,
                "model_version": None,
                "model_metadata": {}
            }
    
    def _extract_response_info(self, response: Response) -> Dict[str, Any]:
        """
        提取響應信息
        
        Args:
            response: HTTP 響應對象
            
        Returns:
            Dict: 響應信息字典
        """
        try:
            # 獲取響應大小
            response_size = None
            if hasattr(response, 'headers'):
                content_length = response.headers.get('content-length')
                if content_length:
                    response_size = int(content_length)
                elif hasattr(response, 'body'):
                    # 嘗試從 body 獲取大小
                    if isinstance(response.body, bytes):
                        response_size = len(response.body)
            
            return {
                "status_code": response.status_code,
                "response_size_bytes": response_size,
                "content_type": response.headers.get('content-type') if hasattr(response, 'headers') else None,
                "headers": dict(response.headers) if hasattr(response, 'headers') and self.enable_detailed_logging else None
            }
            
        except Exception as e:
            logger.warning(f"提取響應信息失敗: {e}")
            return {
                "status_code": getattr(response, 'status_code', 500),
                "response_size_bytes": None,
                "content_type": None
            }
    
    async def _create_and_send_event(
        self,
        request_info: Dict[str, Any],
        response_info: Dict[str, Any],
        response_time_ms: float,
        status_code: int,
        error_message: Optional[str],
        error_type: Optional[str],
        trace_id: str
    ):
        """
        創建並異步發送監控事件
        
        此方法在後台執行，不阻塞主要的 API 響應
        """
        try:
            # 動態調整 service_name 來包含模型版本
            model_version = request_info.get("model_version")
            
            # 只處理有明確 model_version 的請求
            if not model_version:
                # 如果沒有明確的 model_version，跳過監控記錄
                logger.debug(f"跳過無版本請求的監控記錄: {request_info['path']}")
                return
            
            # 有模型版本時，記錄帶版本的服務名稱
            service_name = f"{self.service_name}-{model_version}"
            
            # 準備元數據
            metadata = {
                "query_params": request_info.get("query_params"),
                "content_type": request_info.get("content_type"),
                "error_type": error_type
            }
            
            # 添加模型相關元數據
            if model_version:
                metadata["model_version"] = model_version
            
            model_metadata = request_info.get("model_metadata", {})
            if model_metadata:
                metadata.update(model_metadata)
            
            # 創建指標事件
            event = MetricsEvent.from_request_response(
                service_name=service_name,
                endpoint=request_info["path"],
                method=request_info["method"],
                status_code=status_code,
                response_time_ms=response_time_ms,
                client_ip=request_info.get("client_ip"),
                user_agent=request_info.get("user_agent"),
                request_size=request_info.get("request_size_bytes"),
                response_size=response_info.get("response_size_bytes"),
                error_message=error_message,
                trace_id=trace_id,
                **metadata
            )
            
            # 異步發送事件
            success = await publish_metrics_event_async(event)
            
            if success:
                self.stats["total_events_sent"] += 1
                if self.enable_detailed_logging:
                    logger.debug(f"✅ 監控事件已發送: {service_name} {request_info['path']} - {model_version or 'no-version'}")
            else:
                self.stats["total_send_failures"] += 1
                
        except Exception as e:
            logger.error(f"創建或發送監控事件失敗: {e}")
            self.stats["total_send_failures"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取監控統計信息"""
        return {
            **self.stats,
            "service_name": self.service_name,
            "exclude_paths": self.exclude_paths,
            "success_rate": (
                self.stats["total_events_sent"] / max(1, self.stats["total_requests"])
            ) * 100
        }


class ModelAPIMonitor:
    """
    Model API 監控器主類別
    
    提供高級的監控功能封裝：
    1. 自動配置監控中間件
    2. 管理事件發送器生命週期
    3. 提供監控統計和健康檢查
    """
    
    def __init__(
        self,
        service_name: str,
        app: Optional[FastAPI] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化監控器
        
        Args:
            service_name: 服務名稱
            app: FastAPI 應用實例
            config: 監控配置
        """
        self.service_name = service_name
        self.app = app
        self.config = config or {}
        
        self.settings = get_settings()
        self.event_publisher: Optional[EventPublisher] = None
        self.middleware: Optional[MonitoringMiddleware] = None
        
        self._is_started = False
        
        logger.info(f"🔍 ModelAPIMonitor 已初始化 - 服務: {service_name}")
    
    async def start_monitoring(self, app: Optional[FastAPI] = None) -> bool:
        """
        啟動監控功能
        
        Args:
            app: FastAPI 應用實例
            
        Returns:
            bool: 啟動是否成功
        """
        if self._is_started:
            logger.warning("監控器已經啟動")
            return True
        
        try:
            # 使用傳入的 app 或初始化時的 app
            target_app = app or self.app
            if not target_app:
                raise ValueError("必須提供 FastAPI 應用實例")
            
            # 初始化事件發送器
            self.event_publisher = EventPublisher()
            publisher_connected = await self.event_publisher.connect()
            
            if not publisher_connected:
                logger.warning("⚠️ RabbitMQ 連接失敗，但監控將繼續運行")
            
            # 創建並添加監控中間件
            self.middleware = MonitoringMiddleware(
                app=target_app,
                service_name=self.service_name,
                enable_detailed_logging=self.config.get('enable_detailed_logging', False),
                exclude_paths=self.config.get('exclude_paths')
            )
            
            target_app.add_middleware(MonitoringMiddleware, 
                                    service_name=self.service_name,
                                    enable_detailed_logging=self.config.get('enable_detailed_logging', False),
                                    exclude_paths=self.config.get('exclude_paths'))
            
            self._is_started = True
            logger.info(f"✅ 監控器啟動成功 - 服務: {self.service_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 監控器啟動失敗: {e}")
            return False
    
    async def stop_monitoring(self):
        """停止監控功能"""
        if not self._is_started:
            return
        
        try:
            if self.event_publisher:
                await self.event_publisher.disconnect()
            
            self._is_started = False
            logger.info(f"🛑 監控器已停止 - 服務: {self.service_name}")
            
        except Exception as e:
            logger.error(f"停止監控器時發生錯誤: {e}")
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        獲取監控器健康狀態
        
        Returns:
            Dict: 健康狀態信息
        """
        publisher_healthy = False
        if self.event_publisher:
            publisher_healthy = await self.event_publisher.is_healthy()
        
        stats = {}
        if self.middleware:
            stats = self.middleware.get_stats()
        
        return {
            "service_name": self.service_name,
            "is_monitoring": self._is_started,
            "event_publisher_healthy": publisher_healthy,
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def configure(self, config: Dict[str, Any]):
        """
        動態更新監控配置
        
        Args:
            config: 新的配置字典
        """
        self.config.update(config)
        logger.info(f"監控配置已更新: {config}")


# 便捷函數
def add_monitoring_to_app(
    app: FastAPI, 
    service_name: str,
    config: Optional[Dict[str, Any]] = None
) -> ModelAPIMonitor:
    """
    為 FastAPI 應用添加監控功能的便捷函數
    
    Args:
        app: FastAPI 應用實例
        service_name: 服務名稱
        config: 監控配置
        
    Returns:
        ModelAPIMonitor: 監控器實例
    """
    monitor = ModelAPIMonitor(service_name, app, config)
    
    # 立即添加中間件（在應用啟動前）
    try:
        app.add_middleware(
            MonitoringMiddleware,
            service_name=service_name,
            enable_detailed_logging=config.get('enable_detailed_logging', False) if config else False,
            exclude_paths=config.get('exclude_paths') if config else None
        )
        logger.info(f"✅ 監控中間件已添加到應用 - 服務: {service_name}")
    except Exception as e:
        logger.error(f"❌ 添加監控中間件失敗: {e}")
    
    # 在應用啟動時初始化事件發送器
    @app.on_event("startup")
    async def start_event_publisher():
        try:
            monitor.event_publisher = EventPublisher()
            await monitor.event_publisher.connect()
            monitor._is_started = True
            logger.info(f"✅ 事件發送器已啟動 - 服務: {service_name}")
        except Exception as e:
            logger.error(f"❌ 事件發送器啟動失敗: {e}")
    
    @app.on_event("shutdown")
    async def stop_monitoring():
        await monitor.stop_monitoring()
    
    return monitor 