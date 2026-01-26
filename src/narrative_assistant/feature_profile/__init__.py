"""
Sistema de perfiles de features por tipo de documento.

Proporciona configuración de qué features están disponibles
según el tipo de manuscrito (novela, memoria, ensayo, etc.).
"""

from .models import (
    DocumentType,
    DocumentSubtype,
    FeatureAvailability,
    FeatureProfile,
    DOCUMENT_TYPES,
    DOCUMENT_SUBTYPES,
)
from .service import FeatureProfileService

__all__ = [
    "DocumentType",
    "DocumentSubtype",
    "FeatureAvailability",
    "FeatureProfile",
    "FeatureProfileService",
    "DOCUMENT_TYPES",
    "DOCUMENT_SUBTYPES",
]
