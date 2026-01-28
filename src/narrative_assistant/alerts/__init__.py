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
from .repository import AlertRepository, get_alert_repository
from .formatter import AlertFormatter, get_alert_formatter

# AlertEngine depends on analysis modules which import NLP libraries (numpy, spacy).
# These are NOT available in embedded Python (production) until the user
# installs the full NLP stack. Gracefully degrade if missing.
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
