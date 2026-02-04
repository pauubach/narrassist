"""
Sistema de perfiles de features por tipo de documento.

Proporciona configuración de qué features están disponibles
según el tipo de manuscrito (novela, memoria, ensayo, etc.).
"""

from .models import (
    DOCUMENT_SUBTYPES,
    DOCUMENT_TYPES,
    PROFILE_CREATORS,
    DocumentType,
    FeatureAvailability,
    FeatureProfile,
    create_feature_profile,
)
from .service import FeatureProfileService

__all__ = [
    "DocumentType",
    "FeatureAvailability",
    "FeatureProfile",
    "FeatureProfileService",
    "DOCUMENT_TYPES",
    "DOCUMENT_SUBTYPES",
    "PROFILE_CREATORS",
    "create_feature_profile",
]
