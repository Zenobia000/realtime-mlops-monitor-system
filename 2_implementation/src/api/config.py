"""
配置管理模組
使用 Pydantic Settings 管理環境變數配置
"""

from functools import lru_cache
from typing import List, Literal
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """應用程式配置類別"""
    
    # API 基本配置
    API_HOST: str = Field(default="0.0.0.0", description="API 服務主機")
    API_PORT: int = Field(default=8001, description="監控 API 服務端口")
    TEST_MODEL_API_PORT: int = Field(default=8002, description="測試模型 API 端口")
    API_KEY: str = Field(default="monitor_api_key_dev_2025", description="API 認證金鑰")
    
    # 環境配置
    ENVIRONMENT: Literal["development", "staging", "production"] = Field(
        default="development", description="運行環境"
    )
    DEBUG: bool = Field(default=True, description="除錯模式")
    
    # 資料庫配置 (匹配 platform-timescaledb 服務)
    DATABASE_URL: str = Field(
        default="postgresql://admin:admin123@localhost:5433/platform_db",
        description="資料庫連接字串"
    )
    POSTGRES_HOST: str = Field(default="localhost", description="PostgreSQL 主機")
    POSTGRES_PORT: int = Field(default=5433, description="PostgreSQL 端口")
    POSTGRES_DB: str = Field(default="platform_db", description="資料庫名稱")
    POSTGRES_USER: str = Field(default="admin", description="資料庫用戶")
    POSTGRES_PASSWORD: str = Field(default="admin123", description="資料庫密碼")
    
    # Redis 配置 (匹配 platform-redis 服務)
    REDIS_URL: str = Field(
        default="redis://:admin123@localhost:6380",
        description="Redis 連接字串"
    )
    REDIS_HOST: str = Field(default="localhost", description="Redis 主機")
    REDIS_PORT: int = Field(default=6380, description="Redis 端口")
    REDIS_PASSWORD: str = Field(default="admin123", description="Redis 密碼")
    
    # RabbitMQ 配置 (匹配 platform-rabbitmq 服務)
    RABBITMQ_URL: str = Field(
        default="amqp://admin:admin123@localhost:5672/",
        description="RabbitMQ 連接字串"
    )
    RABBITMQ_HOST: str = Field(default="localhost", description="RabbitMQ 主機")
    RABBITMQ_PORT: int = Field(default=5672, description="RabbitMQ 端口")
    RABBITMQ_USER: str = Field(default="admin", description="RabbitMQ 用戶")
    RABBITMQ_PASSWORD: str = Field(default="admin123", description="RabbitMQ 密碼")
    RABBITMQ_MANAGEMENT_PORT: int = Field(default=15672, description="RabbitMQ 管理端口")
    
    # 指標處理配置
    WINDOW_SIZE_SECONDS: int = Field(default=60, description="滑動視窗大小(秒)")
    AGGREGATION_INTERVAL: int = Field(default=5, description="聚合間隔(秒)")
    METRICS_QUEUE_NAME: str = Field(default="metrics.api_requests", description="指標佇列名稱")
    ALERTS_QUEUE_NAME: str = Field(default="alerts.notifications", description="告警佇列名稱")
    
    # 告警閾值配置
    P95_LATENCY_THRESHOLD: int = Field(default=500, description="P95延遲告警閾值(ms)")
    P99_LATENCY_THRESHOLD: int = Field(default=1000, description="P99延遲告警閾值(ms)")
    ERROR_RATE_THRESHOLD: float = Field(default=0.05, description="錯誤率告警閾值")
    QPS_LOW_THRESHOLD: int = Field(default=1, description="低QPS告警閾值")
    
    # 日誌配置
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="日誌級別"
    )
    LOG_FORMAT: Literal["json", "text"] = Field(default="json", description="日誌格式")
    
    # CORS 配置
    ALLOWED_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080"
        ],
        description="允許的跨域來源"
    )
    
    class Config:
        """Pydantic 配置"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"  # 允許額外的環境變數


@lru_cache()
def get_settings() -> Settings:
    """
    獲取應用程式配置
    使用 lru_cache 確保配置只讀取一次
    """
    return Settings()


# 方便的配置獲取函數
def get_database_url() -> str:
    """獲取資料庫連接字串"""
    return get_settings().DATABASE_URL


def get_redis_url() -> str:
    """獲取 Redis 連接字串"""
    return get_settings().REDIS_URL


def get_rabbitmq_url() -> str:
    """獲取 RabbitMQ 連接字串"""
    return get_settings().RABBITMQ_URL


def is_development() -> bool:
    """是否為開發環境"""
    return get_settings().ENVIRONMENT == "development"


def is_debug() -> bool:
    """是否為除錯模式"""
    return get_settings().DEBUG 