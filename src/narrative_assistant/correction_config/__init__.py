"""
Sistema unificado de configuración de corrección.

Centraliza TODOS los parámetros de corrección con herencia tipo → subtipo.
"""

from .api import (
    get_config_for_project,
    get_effective_config,
    get_types_with_subtypes,
)
from .models import (
    CorrectionConfig,
    DialogConfig,
    InheritanceSource,
    ParameterValue,
    RegionalConfig,
    RepetitionConfig,
    SentenceConfig,
    StyleConfig,
)
from .registry import (
    SUBTYPES_REGISTRY,
    TYPES_REGISTRY,
    get_correction_config,
    get_subtype_overrides,
    get_type_defaults,
)

__all__ = [
    # Models
    "CorrectionConfig",
    "DialogConfig",
    "RepetitionConfig",
    "SentenceConfig",
    "StyleConfig",
    "RegionalConfig",
    "InheritanceSource",
    "ParameterValue",
    # Registry
    "get_correction_config",
    "get_type_defaults",
    "get_subtype_overrides",
    "TYPES_REGISTRY",
    "SUBTYPES_REGISTRY",
    # API
    "get_types_with_subtypes",
    "get_config_for_project",
    "get_effective_config",
]
