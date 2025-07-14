"""
統一的 Pydantic 響應模型
提供資料庫欄位與 API 回應格式的映射
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from decimal import Decimal


class MetricsDataResponse(BaseModel):
    """指標數據響應模型 - 統一欄位名稱映射"""
    
    # 基本識別欄位
    id: int
    timestamp: datetime
    service_name: str
    api_endpoint: str = Field(alias="endpoint")  # 資料庫: endpoint -> API: api_endpoint
    
    # 性能指標 (欄位名稱映射)
    qps: float
    error_rate: float
    avg_latency_ms: float = Field(alias="avg_response_time")  # 資料庫: avg_response_time -> API: avg_latency_ms
    p95_latency_ms: float = Field(alias="p95_response_time")  # 資料庫: p95_response_time -> API: p95_latency_ms
    p99_latency_ms: float = Field(alias="p99_response_time")  # 資料庫: p99_response_time -> API: p99_latency_ms
    
    # 統計數據
    total_requests: int
    total_errors: Optional[int] = 0
    
    # 時間欄位
    created_at: datetime
    
    class Config:
        """Pydantic 配置"""
        populate_by_name = True  # 允許使用別名和原始欄位名
        from_attributes = True  # 支援 SQLAlchemy ORM
        

class ServiceMetricsResponse(BaseModel):
    """服務指標響應模型"""
    
    service_name: str
    status: str  # healthy, unhealthy, unknown
    
    # 聚合指標
    avg_qps: float
    avg_error_rate: float
    avg_latency_ms: float = Field(alias="avg_response_time")
    p95_latency_ms: float = Field(alias="p95_response_time") 
    p99_latency_ms: float = Field(alias="p99_response_time")
    
    # 統計數據
    total_requests: int
    total_errors: int
    endpoint_count: int
    
    # 時間
    last_seen: datetime
    
    class Config:
        populate_by_name = True
        from_attributes = True


class EndpointMetricsResponse(BaseModel):
    """端點指標響應模型"""
    
    api_endpoint: str = Field(alias="endpoint")
    service_name: str
    
    # 性能指標
    avg_qps: float
    avg_error_rate: float
    avg_latency_ms: float = Field(alias="avg_response_time")
    p95_latency_ms: float = Field(alias="p95_response_time")
    p99_latency_ms: float = Field(alias="p99_response_time")
    
    # 統計
    total_requests: int
    total_errors: int
    
    # 狀態
    status: str
    last_seen: datetime
    
    class Config:
        populate_by_name = True
        from_attributes = True


class RealTimeMetricsResponse(BaseModel):
    """實時指標響應模型"""
    
    service_name: str
    api_endpoint: str
    qps: float
    avg_latency_ms: float
    p95_latency_ms: float  
    p99_latency_ms: float
    error_rate: float
    total_requests: int
    status: str  # healthy, warning, critical
    last_updated: datetime


class AlertRuleResponse(BaseModel):
    """告警規則響應模型"""
    
    id: str
    name: str
    service_name: str
    metric: str
    threshold: float
    operator: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class ActiveAlertResponse(BaseModel):
    """活躍告警響應模型"""
    
    id: str
    rule_id: Optional[str] = None
    service_name: str
    metric: str
    current_value: float
    threshold: float
    severity: str
    started_at: datetime
    resolved_at: Optional[datetime] = None
    message: str


class ServiceInfoResponse(BaseModel):
    """服務信息響應模型"""
    
    service_name: str
    display_name: Optional[str] = None
    endpoints: List[str] = []
    status: str
    last_seen: datetime
    monitoring_enabled: bool
    created_at: datetime
    updated_at: datetime


# 工具函數：資料庫記錄轉換為響應模型
def db_metrics_to_response(db_record) -> Dict[str, Any]:
    """
    將資料庫記錄轉換為標準化的 API 響應格式
    處理欄位名稱映射
    """
    return {
        "id": db_record.get("id"),
        "timestamp": db_record.get("timestamp"),
        "service_name": db_record.get("service_name"),
        "api_endpoint": db_record.get("endpoint"),  # 映射欄位名稱
        "qps": float(db_record.get("qps", 0)),
        "error_rate": float(db_record.get("error_rate", 0)),
        "avg_latency_ms": float(db_record.get("avg_response_time", 0)),  # 映射欄位名稱
        "p95_latency_ms": float(db_record.get("p95_response_time", 0)),  # 映射欄位名稱
        "p99_latency_ms": float(db_record.get("p99_response_time", 0)),  # 映射欄位名稱
        "total_requests": db_record.get("total_requests", 0),
        "total_errors": db_record.get("total_errors", 0),
        "created_at": db_record.get("created_at")
    }


def db_service_to_response(db_record) -> Dict[str, Any]:
    """
    將服務資料庫記錄轉換為響應格式
    """
    return {
        "service_name": db_record.get("service_name"),
        "avg_qps": float(db_record.get("avg_qps", 0)),
        "avg_error_rate": float(db_record.get("avg_error_rate", 0)),
        "avg_latency_ms": float(db_record.get("avg_response_time", 0)),  # 映射欄位名稱
        "p95_latency_ms": float(db_record.get("p95_response_time", 0)),  # 映射欄位名稱
        "p99_latency_ms": float(db_record.get("p99_response_time", 0)),  # 映射欄位名稱
        "total_requests": db_record.get("total_requests", 0),
        "total_errors": db_record.get("total_errors", 0),
        "endpoint_count": db_record.get("endpoint_count", 0),
        "last_seen": db_record.get("last_seen")
    }


def db_endpoint_to_response(db_record) -> Dict[str, Any]:
    """
    將端點資料庫記錄轉換為響應格式
    """
    return {
        "api_endpoint": db_record.get("endpoint"),  # 映射欄位名稱
        "avg_qps": float(db_record.get("avg_qps", 0)),
        "avg_error_rate": float(db_record.get("avg_error_rate", 0)),
        "avg_latency_ms": float(db_record.get("avg_response_time", 0)),  # 映射欄位名稱
        "p95_latency_ms": float(db_record.get("p95_response_time", 0)),  # 映射欄位名稱
        "p99_latency_ms": float(db_record.get("p99_response_time", 0)),  # 映射欄位名稱
        "total_requests": db_record.get("total_requests", 0),
        "total_errors": db_record.get("total_errors", 0),
        "last_seen": db_record.get("last_seen")
    } 