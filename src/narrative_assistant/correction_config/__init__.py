"""
Sistema unificado de configuración de corrección.

Centraliza TODOS los parámetros de corrección con herencia tipo → subtipo.
"""

from .models import (
    CorrectionConfig,
    DialogConfig,
    RepetitionConfig,
    SentenceConfig,
    StyleConfig,
    InheritanceSource,
    ParameterValue,
)
from .registry import (
    get_correction_config,
    get_type_defaults,
    get_subtype_overrides,
    TYPES_REGISTRY,
    SUBTYPES_REGISTRY,
)
from .api import (
    get_types_with_subtypes,
    get_config_for_project,
    get_effective_config,
)

__all__ = [
    # Models
    "CorrectionConfig",
    "DialogConfig",
    "RepetitionConfig",
    "SentenceConfig",
    "StyleConfig",
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
