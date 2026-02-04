"""
Core module - Errores, configuración, dispositivos y resultados.
"""

from .errors import (
    NarrativeError,
    ErrorSeverity,
    ParsingError,
    CorruptedDocumentError,
    EmptyDocumentError,
    UnsupportedFormatError,
    ScannedPDFError,
    NLPError,
    ModelNotLoadedError,
    ChapterProcessingError,
    DatabaseError,
    ProjectNotFoundError,
    DocumentAlreadyExistsError,
    ResourceError,
    OutOfMemoryError,
    # Licensing errors
    LicensingError,
    LicenseNotFoundError,
    LicenseExpiredError,
    LicenseOfflineError,
    DeviceLimitError,
    DeviceCooldownError,
    QuotaExceededError,
    ModuleNotLicensedError,
)
from .result import Result
from .device import (
    DeviceType,
    DeviceInfo,
    DeviceDetector,
    get_device,
    get_device_detector,
    get_torch_device_string,
    reset_device_detector,
)
from .config import (
    GPUConfig,
    NLPConfig,
    ParsingConfig,
    AlertConfig,
    PersistenceConfig,
    AppConfig,
    get_config,
    set_config,
    reset_config,
)
from .utils import (
    format_duration,
    format_duration_verbose,
)
from .resource_manager import (
    ResourceManager,
    ResourceTier,
    SystemCapabilities,
    ResourceRecommendation,
    HeavyTaskSemaphore,
    get_resource_manager,
)

__all__ = [
    # Errors
    "NarrativeError",
    "ErrorSeverity",
    "ParsingError",
    "CorruptedDocumentError",
    "EmptyDocumentError",
    "UnsupportedFormatError",
    "ScannedPDFError",
    "NLPError",
    "ModelNotLoadedError",
    "ChapterProcessingError",
    "DatabaseError",
    "ProjectNotFoundError",
    "DocumentAlreadyExistsError",
    "ResourceError",
    "OutOfMemoryError",
    # Licensing Errors
    "LicensingError",
    "LicenseNotFoundError",
    "LicenseExpiredError",
    "LicenseOfflineError",
    "DeviceLimitError",
    "DeviceCooldownError",
    "QuotaExceededError",
    "ModuleNotLicensedError",
    # Result
    "Result",
    # Device
    "DeviceType",
    "DeviceInfo",
    "DeviceDetector",
    "get_device",
    "get_device_detector",
    "get_torch_device_string",
    "reset_device_detector",
    # Config
    "GPUConfig",
    "NLPConfig",
    "ParsingConfig",
    "AlertConfig",
    "PersistenceConfig",
    "AppConfig",
    "get_config",
    "set_config",
    "reset_config",
    # Utils
    "format_duration",
    "format_duration_verbose",
    # Resource Management
    "ResourceManager",
    "ResourceTier",
    "SystemCapabilities",
    "ResourceRecommendation",
    "HeavyTaskSemaphore",
    "get_resource_manager",
]
