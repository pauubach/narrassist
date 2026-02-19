"""
Sistema de alertas centralizado.

Recibe alertas de todos los módulos de análisis, las clasifica, prioriza
y presenta al usuario de forma unificada.
"""

from .formatter import AlertFormatter, get_alert_formatter
from .models import (
    Alert,
    AlertCategory,
    AlertFilter,
    AlertSeverity,
    AlertStatus,
)
from .repository import AlertRepository, get_alert_repository

# AlertEngine depends on analysis modules which import NLP libraries (numpy, spacy).
# These are NOT available in embedded Python (production) until the user
# installs the full NLP stack. Gracefully degrade if missing.
from typing import TYPE_CHECKING, Optional, Callable
if TYPE_CHECKING:
    from .engine import AlertEngine, get_alert_engine
try:
    from .engine import AlertEngine, get_alert_engine
except ImportError:
    AlertEngine = None
    get_alert_engine = None

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
    # Formatter
    "AlertFormatter",
    "get_alert_formatter",
]
