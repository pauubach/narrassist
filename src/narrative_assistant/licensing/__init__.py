"""
Sistema de licencias para Narrative Assistant.

Proporciona:
- Modelos de datos para licencias, dispositivos y suscripciones
- Verificacion online/offline con periodo de gracia
- Fingerprinting de hardware para vinculacion de dispositivos
- Control de cuotas de manuscritos
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
    Device,
    DeviceStatus,
    License,
    LicenseBundle,
    LicenseModule,
    LicenseStatus,
    # Enums
    LicenseTier,
    Subscription,
    # Clases de datos
    TierLimits,
    UsageRecord,
    initialize_licensing_schema,
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
    ModuleNotLicensedError,
    QuotaExceededError,
    # Resultados
    VerificationResult,
    activate_license,
    check_module_access,
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
    "LicenseModule",
    "LicenseBundle",
    "LicenseStatus",
    "DeviceStatus",
    # Constantes
    "OFFLINE_GRACE_PERIOD_DAYS",
    "DEVICE_DEACTIVATION_COOLDOWN_HOURS",
    # Modelos
    "TierLimits",
    "License",
    "Device",
    "Subscription",
    "UsageRecord",
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
    "ModuleNotLicensedError",
    # Verificacion
    "VerificationResult",
    "LicenseVerifier",
    "get_cached_license",
    "verify_license",
    "activate_license",
    "check_module_access",
    "check_quota",
    "record_manuscript_usage",
    "deactivate_device",
    "get_license_info",
]
