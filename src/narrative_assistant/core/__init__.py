"""
Core module - Errores, configuración, dispositivos y resultados.
"""

from .config import (
    AlertConfig,
    AppConfig,
    GPUConfig,
    NLPConfig,
    ParsingConfig,
    PersistenceConfig,
    get_config,
    reset_config,
    set_config,
)
from .device import (
    DeviceDetector,
    DeviceInfo,
    DeviceType,
    get_device,
    get_device_detector,
    get_torch_device_string,
    reset_device_detector,
)
from .errors import (
    ChapterProcessingError,
    CorruptedDocumentError,
    DatabaseError,
    DeviceCooldownError,
    DeviceLimitError,
    DocumentAlreadyExistsError,
    EmptyDocumentError,
    ErrorSeverity,
    LicenseExpiredError,
    LicenseNotFoundError,
    LicenseOfflineError,
    # Licensing errors
    LicensingError,
    ModelNotLoadedError,
    ModuleNotLicensedError,
    NarrativeError,
    NLPError,
    OutOfMemoryError,
    ParsingError,
    ProjectNotFoundError,
    QuotaExceededError,
    ResourceError,
    ScannedPDFError,
    UnsupportedFormatError,
)
from .resource_manager import (
    HeavyTaskSemaphore,
    ResourceManager,
    ResourceRecommendation,
    ResourceTier,
    SystemCapabilities,
    get_resource_manager,
)
from .result import Result
from .utils import (
    format_duration,
    format_duration_verbose,
)
from .patterns import (
    SingletonMeta,
    singleton,
    lazy_singleton,
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
    # Patterns
    "SingletonMeta",
    "singleton",
    "lazy_singleton",
]
