"""
Modulo de analisis de focalizacion para narrativas.

Proporciona herramientas para:
- Declarar la focalizacion de cada capitulo/escena
- Detectar violaciones a la focalizacion declarada
- Generar alertas de inconsistencias de punto de vista
"""

from .declaration import (
    FocalizationType,
    FocalizationDeclaration,
    FocalizationScope,
    FocalizationDeclarationService,
)
from .violations import (
    ViolationType,
    ViolationSeverity,
    FocalizationViolation,
    FocalizationViolationDetector,
    MENTAL_ACCESS_VERBS,
    MENTAL_ACCESS_PATTERNS,
)

__all__ = [
    # Declaration
    "FocalizationType",
    "FocalizationDeclaration",
    "FocalizationScope",
    "FocalizationDeclarationService",
    # Violations
    "ViolationType",
    "ViolationSeverity",
    "FocalizationViolation",
    "FocalizationViolationDetector",
    "MENTAL_ACCESS_VERBS",
    "MENTAL_ACCESS_PATTERNS",
]
