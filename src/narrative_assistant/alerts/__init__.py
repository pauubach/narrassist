"""
Sistema de alertas centralizado.

Recibe alertas de todos los módulos de análisis, las clasifica, prioriza
y presenta al usuario de forma unificada.
"""

from .models import (
    Alert,
    AlertCategory,
    AlertSeverity,
    AlertStatus,
    AlertFilter,
)
from .engine import AlertEngine, get_alert_engine
from .repository import AlertRepository, get_alert_repository

__all__ = [
    # Models
    "Alert",
    "AlertCategory",
    "AlertSeverity",
    "AlertStatus",
    "AlertFilter",
    # Engine
    "AlertEngine",
    "get_alert_engine",
    # Repository
    "AlertRepository",
    "get_alert_repository",
]
