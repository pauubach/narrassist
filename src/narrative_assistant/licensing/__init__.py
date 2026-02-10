"""
Sistema de licencias para Narrative Assistant.

Proporciona:
- Modelos de datos para licencias, dispositivos y suscripciones
- Verificacion online/offline con periodo de gracia
- Fingerprinting de hardware para vinculacion de dispositivos
- Control de cuotas de paginas (250 palabras = 1 pagina)
- Verificacion de features por tier
"""

from .fingerprint import (
    FingerprintGenerator,
    HardwareDetector,
    HardwareInfo,
    get_device_display_info,
    get_hardware_fingerprint,
    get_hardware_info,
    verify_fingerprint,
)
from .models import (
    DEVICE_DEACTIVATION_COOLDOWN_HOURS,
    # Schema
    LICENSING_SCHEMA_SQL,
    # Constantes
    OFFLINE_GRACE_PERIOD_DAYS,
    TIER_FEATURES,
    WORDS_PER_PAGE,
    Device,
    DeviceStatus,
    License,
    LicenseFeature,
    LicenseStatus,
    # Enums
    LicenseTier,
    Subscription,
    # Clases de datos
    TierLimits,
    UsageRecord,
    initialize_licensing_schema,
    words_to_pages,
)
from .gating import (
    apply_license_gating,
    get_allowed_features,
    is_feature_allowed,
    is_licensing_enabled,
)
from .verification import (
    DeviceCooldownError,
    DeviceLimitError,
    # Errores
    LicenseError,
    LicenseExpiredError,
    LicenseNotFoundError,
    LicenseOfflineError,
    # Clase principal
    LicenseVerifier,
    QuotaExceededError,
    TierFeatureError,
    # Resultados
    VerificationResult,
    activate_license,
    check_feature_access,
    check_quota,
    deactivate_device,
    # Funciones publicas
    get_cached_license,
    get_license_info,
    record_manuscript_usage,
    verify_license,
)

__all__ = [
    # Enums
    "LicenseTier",
    "LicenseFeature",
    "LicenseStatus",
    "DeviceStatus",
    # Constantes
    "OFFLINE_GRACE_PERIOD_DAYS",
    "DEVICE_DEACTIVATION_COOLDOWN_HOURS",
    "WORDS_PER_PAGE",
    "TIER_FEATURES",
    # Modelos
    "TierLimits",
    "License",
    "Device",
    "Subscription",
    "UsageRecord",
    # Funciones auxiliares
    "words_to_pages",
    # Schema
    "LICENSING_SCHEMA_SQL",
    "initialize_licensing_schema",
    # Fingerprinting
    "HardwareInfo",
    "HardwareDetector",
    "FingerprintGenerator",
    "get_hardware_fingerprint",
    "get_hardware_info",
    "verify_fingerprint",
    "get_device_display_info",
    # Errores
    "LicenseError",
    "LicenseNotFoundError",
    "LicenseExpiredError",
    "LicenseOfflineError",
    "DeviceLimitError",
    "DeviceCooldownError",
    "QuotaExceededError",
    "TierFeatureError",
    # Verificacion
    "VerificationResult",
    "LicenseVerifier",
    "get_cached_license",
    "verify_license",
    "activate_license",
    "check_feature_access",
    "check_quota",
    "record_manuscript_usage",
    "deactivate_device",
    "get_license_info",
    # Gating
    "is_licensing_enabled",
    "is_feature_allowed",
    "get_allowed_features",
    "apply_license_gating",
]
