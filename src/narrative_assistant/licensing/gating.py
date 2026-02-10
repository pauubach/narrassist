"""
Feature gating: controla que features del pipeline estan disponibles.

Usa NA_LICENSING_ENABLED=true para activar las restricciones por tier.
Por defecto (false), todas las features estan desbloqueadas (modo desarrollo).
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from .models import TIER_FEATURES, LicenseFeature, LicenseTier

if TYPE_CHECKING:
    from narrative_assistant.pipelines.unified_analysis import UnifiedConfig

logger = logging.getLogger(__name__)


def is_licensing_enabled() -> bool:
    """Comprueba si el sistema de licencias esta activo."""
    return os.environ.get("NA_LICENSING_ENABLED", "false").lower() == "true"


def is_feature_allowed(feature: LicenseFeature, tier: LicenseTier | None = None) -> bool:
    """
    Comprueba si una feature esta permitida.

    Si licensing esta desactivado (desarrollo), siempre retorna True.
    Si esta activado, comprueba el tier actual.
    """
    if not is_licensing_enabled():
        return True

    if tier is None:
        # Sin licencia activa -> solo features basicas
        tier = LicenseTier.CORRECTOR

    return feature in TIER_FEATURES[tier]


def get_allowed_features(tier: LicenseTier | None = None) -> frozenset[LicenseFeature]:
    """Retorna el conjunto de features permitidas para el tier dado."""
    if not is_licensing_enabled():
        return frozenset(LicenseFeature)

    if tier is None:
        tier = LicenseTier.CORRECTOR

    return TIER_FEATURES[tier]


# Mapping: LicenseFeature -> campos de UnifiedConfig que controla
_FEATURE_CONFIG_MAP: dict[LicenseFeature, list[str]] = {
    LicenseFeature.ATTRIBUTE_CONSISTENCY: [
        "run_attributes",
        "run_consistency",
    ],
    LicenseFeature.GRAMMAR_SPELLING: [
        "run_spelling",
        "run_grammar",
    ],
    LicenseFeature.NER_COREFERENCE: [
        "run_ner",
        "run_coreference",
        "run_entity_fusion",
    ],
    LicenseFeature.NAME_VARIANTS: [
        # Name variant detection runs as part of NER post-processing
        # Controlled via a dedicated flag
        "run_name_variants",
    ],
    LicenseFeature.CHARACTER_PROFILING: [
        "run_character_profiling",
    ],
    LicenseFeature.NETWORK_ANALYSIS: [
        "run_network_analysis",
    ],
    LicenseFeature.ANACHRONISM_DETECTION: [
        "run_anachronism_detection",
    ],
    LicenseFeature.OOC_DETECTION: [
        "run_ooc_detection",
    ],
    LicenseFeature.CLASSICAL_SPANISH: [
        "run_classical_spanish",
    ],
    LicenseFeature.MULTI_MODEL: [
        # Controls multi-model voting in NER and coreference
        "run_multi_model_voting",
    ],
    LicenseFeature.FULL_REPORTS: [
        # Controls full export/report generation
        "run_full_reports",
    ],
}


def apply_license_gating(config: UnifiedConfig, tier: LicenseTier | None = None) -> UnifiedConfig:
    """
    Aplica restricciones de licencia a un UnifiedConfig.

    Desactiva las fases del pipeline cuya feature no esta permitida en el tier.
    Si licensing esta desactivado, retorna el config sin cambios.
    """
    if not is_licensing_enabled():
        return config

    allowed = get_allowed_features(tier)
    disabled_features: list[str] = []

    for feature, config_fields in _FEATURE_CONFIG_MAP.items():
        if feature not in allowed:
            for field_name in config_fields:
                if hasattr(config, field_name) and getattr(config, field_name):
                    setattr(config, field_name, False)
                    disabled_features.append(field_name)

    if disabled_features:
        tier_name = tier.display_name if tier else "Sin licencia"
        logger.info(
            f"License gating ({tier_name}): desactivadas {len(disabled_features)} opciones: "
            f"{', '.join(disabled_features)}"
        )

    return config
