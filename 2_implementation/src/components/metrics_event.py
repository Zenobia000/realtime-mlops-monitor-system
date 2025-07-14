"""
指標事件數據結構
定義監控攔截器收集的事件格式和類型
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid


class EventType(str, Enum):
    """事件類型枚舉"""
    API_REQUEST = "api_request"
    API_RESPONSE = "api_response"
    API_ERROR = "api_error"
    SYSTEM_HEALTH = "system_health"


class MetricsEvent(BaseModel):
    """
    指標事件模型
    
    根據 WBS 要求的事件格式設計：
    - timestamp: 事件時間戳
    - api_endpoint: API 端點路徑
    - response_time_ms: 響應時間(毫秒)
    - status_code: HTTP 狀態碼
    - service_name: 服務名稱
    """
    
    # 基本事件資訊
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="事件唯一ID")
    event_type: EventType = Field(default=EventType.API_REQUEST, description="事件類型")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="事件時間戳")
    
    # API 監控核心指標
    service_name: str = Field(..., description="服務名稱")
    api_endpoint: str = Field(..., description="API 端點路徑")
    http_method: str = Field(..., description="HTTP 方法")
    status_code: int = Field(..., description="HTTP 狀態碼")
    
    # 性能指標
    response_time_ms: float = Field(..., description="響應時間(毫秒)")
    request_size_bytes: Optional[int] = Field(default=None, description="請求大小(bytes)")
    response_size_bytes: Optional[int] = Field(default=None, description="響應大小(bytes)")
    
    # 請求上下文
    client_ip: Optional[str] = Field(default=None, description="客戶端IP")
    user_agent: Optional[str] = Field(default=None, description="用戶代理")
    trace_id: Optional[str] = Field(default=None, description="追蹤ID")
    
    # 錯誤資訊
    error_message: Optional[str] = Field(default=None, description="錯誤訊息")
    error_type: Optional[str] = Field(default=None, description="錯誤類型")
    
    # 額外元數據
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")
    
    class Config:
        """Pydantic 配置"""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_rabbitmq_message(self) -> Dict[str, Any]:
        """
        轉換為 RabbitMQ 訊息格式
        
        Returns:
            Dict[str, Any]: 適合發送到 RabbitMQ 的訊息格式
        """
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "service_name": self.service_name,
            "api_endpoint": self.api_endpoint,
            "http_method": self.http_method,
            "status_code": self.status_code,
            "response_time_ms": self.response_time_ms,
            "request_size_bytes": self.request_size_bytes,
            "response_size_bytes": self.response_size_bytes,
            "client_ip": self.client_ip,
            "user_agent": self.user_agent,
            "trace_id": self.trace_id,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_request_response(
        cls,
        service_name: str,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: float,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None,
        error_message: Optional[str] = None,
        trace_id: Optional[str] = None,
        **kwargs
    ) -> "MetricsEvent":
        """
        從請求響應信息創建事件
        
        Args:
            service_name: 服務名稱
            endpoint: API 端點
            method: HTTP 方法
            status_code: 狀態碼
            response_time_ms: 響應時間
            **kwargs: 其他可選參數
            
        Returns:
            MetricsEvent: 創建的事件實例
        """
        event_type = EventType.API_ERROR if status_code >= 400 else EventType.API_RESPONSE
        
        return cls(
            event_type=event_type,
            service_name=service_name,
            api_endpoint=endpoint,
            http_method=method,
            status_code=status_code,
            response_time_ms=response_time_ms,
            client_ip=client_ip,
            user_agent=user_agent,
            request_size_bytes=request_size,
            response_size_bytes=response_size,
            error_message=error_message,
            trace_id=trace_id,
            metadata=kwargs
        )
    
    def is_error(self) -> bool:
        """判斷是否為錯誤事件"""
        return self.status_code >= 400
    
    def is_slow_response(self, threshold_ms: float = 1000.0) -> bool:
        """判斷是否為慢響應"""
        return self.response_time_ms > threshold_ms
    
    def get_endpoint_key(self) -> str:
        """獲取端點標識符，用於指標聚合"""
        return f"{self.service_name}:{self.http_method}:{self.api_endpoint}"


class HealthEvent(BaseModel):
    """系統健康事件"""
    
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = Field(default=EventType.SYSTEM_HEALTH)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    service_name: str = Field(..., description="服務名稱")
    health_status: str = Field(..., description="健康狀態: healthy, unhealthy, degraded")
    cpu_usage: Optional[float] = Field(default=None, description="CPU 使用率")
    memory_usage: Optional[float] = Field(default=None, description="記憶體使用率")
    disk_usage: Optional[float] = Field(default=None, description="磁碟使用率")
    active_connections: Optional[int] = Field(default=None, description="活躍連接數")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        } 