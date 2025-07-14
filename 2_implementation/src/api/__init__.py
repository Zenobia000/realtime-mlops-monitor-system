"""
Model API 監控系統 - API 模組
提供 FastAPI 應用程式和相關功能
"""

from .main import app
from .config import get_settings
from .database import init_database, get_db_health
from .cache import init_redis, get_redis_health

__version__ = "1.0.0"
__author__ = "Vibe Coder"

__all__ = [
    "app",
    "get_settings", 
    "init_database",
    "get_db_health",
    "init_redis", 
    "get_redis_health"
] 