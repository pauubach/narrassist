"""
Módulo de correcciones editoriales.

Detecta problemas de tipografía, repeticiones, concordancia y otros
aspectos lingüísticos que complementan el análisis narrativo.
"""

from .base import BaseDetector, CorrectionIssue
from .config import CorrectionConfig
from .types import (
    AgreementIssueType,
    RepetitionIssueType,
    TypographyIssueType,
)

__all__ = [
    "BaseDetector",
    "CorrectionIssue",
    "CorrectionConfig",
    "TypographyIssueType",
    "RepetitionIssueType",
    "AgreementIssueType",
]
