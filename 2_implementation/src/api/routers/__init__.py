"""
API 路由模組
"""

from .metrics import router as metrics_router
from .alerts import router as alerts_router
from .services import router as services_router
from .dashboards import router as dashboards_router
from .realtime import router as realtime_router

__all__ = [
    "metrics_router",
    "alerts_router", 
    "services_router",
    "dashboards_router",
    "realtime_router"
] 