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
]
