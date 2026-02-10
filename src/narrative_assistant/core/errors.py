"""
Jerarquía de excepciones para el Asistente de Corrección Narrativa.

Severidades:
- RECOVERABLE: Continuar con advertencia (ej: un capítulo falló de 10)
- DEGRADED: Continuar con funcionalidad reducida (ej: sin GPU)
- FATAL: Abortar operación (ej: documento corrupto)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ErrorSeverity(Enum):
    """Nivel de severidad para decidir si abortar o continuar."""

    RECOVERABLE = "recoverable"  # Continuar con advertencia
    DEGRADED = "degraded"  # Continuar con funcionalidad reducida
    FATAL = "fatal"  # Abortar operación


@dataclass
class NarrativeError(Exception):
    """
    Base para todos los errores de la aplicación.

    Attributes:
        message: Mensaje técnico (para logs/debug)
        severity: Nivel de severidad
        user_message: Mensaje amigable para el usuario
        context: Datos adicionales para debug (sanitizados)
    """

    message: str
    severity: ErrorSeverity = ErrorSeverity.RECOVERABLE
    user_message: str | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.user_message is None:
            self.user_message = self.message
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


# =============================================================================
# Errores de Parsing
# =============================================================================


class ParsingError(NarrativeError):
    """Errores al parsear documentos."""

    pass


@dataclass
class CorruptedDocumentError(ParsingError):
    """Documento corrupto o no válido."""

    file_path: str = ""
    original_error: str = ""
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.FATAL, init=False)
    user_message: str | None = field(default=None, init=False)
    context: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.message = f"Cannot parse document: {self.original_error}"
        self.user_message = f"El documento '{self.file_path}' está corrupto o no es válido."
        self.context = {
            "file_path": self.file_path,
            "original_error": self.original_error,
        }
        super().__post_init__()


@dataclass
class EmptyDocumentError(ParsingError):
    """Documento sin contenido textual."""

    file_path: str = ""
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.FATAL, init=False)
    user_message: str | None = field(default=None, init=False)
    context: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.message = "Document has no text content"
        self.user_message = f"El documento '{self.file_path}' está vacío o solo contiene imágenes."
        self.context = {"file_path": self.file_path}
        super().__post_init__()


@dataclass
class UnsupportedFormatError(ParsingError):
    """Formato de documento no soportado."""

    file_path: str = ""
    detected_format: str = ""
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.FATAL, init=False)
    user_message: str | None = field(default=None, init=False)
    context: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.message = f"Unsupported format: {self.detected_format}"
        self.user_message = (
            f"Formato '{self.detected_format}' no soportado. "
            "Formatos válidos: DOCX, TXT, MD, PDF, EPUB, ODT."
        )
        self.context = {
            "file_path": self.file_path,
            "detected_format": self.detected_format,
        }
        super().__post_init__()


@dataclass
class ScannedPDFError(ParsingError):
    """PDF escaneado que requiere OCR externo."""

    file_path: str = ""
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.FATAL, init=False)
    user_message: str | None = field(default=None, init=False)
    context: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.message = "PDF appears to be scanned (no text layer)"
        self.user_message = (
            f"El PDF '{self.file_path}' parece ser escaneado y no contiene texto extraíble. "
            "Usa una herramienta de OCR externa como:\n"
            "  - ocrmypdf input.pdf output.pdf\n"
            "  - Adobe Acrobat Pro\n"
            "  - Google Docs (importar PDF, exportar DOCX)"
        )
        self.context = {"file_path": self.file_path}
        super().__post_init__()


# =============================================================================
# Errores de Pipeline (Fases)
# =============================================================================


@dataclass
class PhaseError(NarrativeError):
    """Error en una fase específica del pipeline de análisis."""

    phase_name: str = ""
    input_summary: str = ""
    output_summary: str = ""
    original_error: str = ""
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.RECOVERABLE, init=False)
    user_message: str | None = field(default=None, init=False)
    context: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.message = f"Phase '{self.phase_name}' failed: {self.original_error}"
        self.user_message = (
            f"La fase '{self.phase_name}' del análisis falló. "
            "Se continuará con los datos disponibles."
        )
        self.context = {
            "phase_name": self.phase_name,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
            "original_error": self.original_error,
        }
        super().__post_init__()


@dataclass
class PhasePreconditionError(NarrativeError):
    """Precondiciones de una fase no se cumplen (fase anterior falló o no produjo datos)."""

    phase_name: str = ""
    missing_data: str = ""
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.RECOVERABLE, init=False)
    user_message: str | None = field(default=None, init=False)
    context: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.message = (
            f"Phase '{self.phase_name}' skipped: missing required data ({self.missing_data})"
        )
        self.user_message = (
            f"Se omitió la fase '{self.phase_name}' porque faltan datos necesarios "
            f"({self.missing_data}). Esto puede deberse a un error en una fase anterior."
        )
        self.context = {
            "phase_name": self.phase_name,
            "missing_data": self.missing_data,
        }
        super().__post_init__()


# =============================================================================
# Errores de NLP
# =============================================================================


class NLPError(NarrativeError):
    """Errores en el pipeline NLP."""

    pass


@dataclass
class ModelNotLoadedError(NLPError):
    """Modelo NLP no disponible en local."""

    model_name: str = ""
    hint: str | None = None  # Mensaje personalizado
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.FATAL, init=False)
    user_message: str | None = field(default=None, init=False)
    context: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.message = f"Model '{self.model_name}' not loaded"
        if self.hint:
            self.user_message = self.hint
        else:
            self.user_message = (
                f"Modelo '{self.model_name}' no encontrado en local.\n"
                f"Ejecuta: python scripts/download_models.py"
            )
        self.context = {"model_name": self.model_name}
        super().__post_init__()


@dataclass
class ChapterProcessingError(NLPError):
    """Error procesando un capítulo específico - continuar con otros."""

    chapter_num: int = 0
    original_error: str = ""
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.RECOVERABLE, init=False)
    user_message: str | None = field(default=None, init=False)
    context: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.message = f"Error processing chapter {self.chapter_num}: {self.original_error}"
        self.user_message = (
            f"Error al analizar el capítulo {self.chapter_num}. Se continuará con el resto."
        )
        self.context = {
            "chapter_num": self.chapter_num,
            "original_error": self.original_error,
        }
        super().__post_init__()


# =============================================================================
# Errores de Base de Datos
# =============================================================================


class DatabaseError(NarrativeError):
    """Errores de SQLite."""

    pass


@dataclass
class ProjectNotFoundError(DatabaseError):
    """Proyecto no existe en BD."""

    project_id: int = 0
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.FATAL, init=False)
    user_message: str | None = field(default=None, init=False)
    context: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.message = f"Project {self.project_id} not found"
        self.user_message = f"No se encontró el proyecto con ID {self.project_id}."
        self.context = {"project_id": self.project_id}
        super().__post_init__()


@dataclass
class DocumentAlreadyExistsError(DatabaseError):
    """Documento ya existe en el proyecto."""

    document_fingerprint: str = ""
    existing_project_name: str = ""
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.FATAL, init=False)
    user_message: str | None = field(default=None, init=False)
    context: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.message = f"Document with fingerprint {self.document_fingerprint} already exists"
        self.user_message = (
            f"Este documento ya fue analizado en el proyecto '{self.existing_project_name}'.\n"
            "¿Deseas continuar donde lo dejaste o crear un análisis nuevo?"
        )
        self.context = {
            "document_fingerprint": self.document_fingerprint,
            "existing_project_name": self.existing_project_name,
        }
        super().__post_init__()


# =============================================================================
# Errores de Recursos
# =============================================================================


class ResourceError(NarrativeError):
    """Errores de recursos del sistema."""

    pass


@dataclass
class OutOfMemoryError(ResourceError):
    """Memoria insuficiente."""

    operation: str = ""
    estimated_mb: int = 0
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.DEGRADED, init=False)
    user_message: str | None = field(default=None, init=False)
    context: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.message = f"Insufficient memory for {self.operation}"
        self.user_message = (
            f"Memoria insuficiente para '{self.operation}'.\n"
            "Intenta cerrar otras aplicaciones o procesar por capítulos."
        )
        self.context = {
            "operation": self.operation,
            "estimated_mb": self.estimated_mb,
        }
        super().__post_init__()


# =============================================================================
# Errores de Licencias
# =============================================================================


class LicensingError(NarrativeError):
    """Errores relacionados con licencias."""

    pass


@dataclass
class LicenseNotFoundError(LicensingError):
    """No se encontró licencia válida."""

    message: str = field(default="No license found", init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.FATAL, init=False)
    user_message: str | None = field(default=None, init=False)
    context: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.user_message = (
            "No se encontró una licencia válida. "
            "Por favor, introduce tu clave de licencia en Configuración."
        )
        super().__post_init__()


@dataclass
class LicenseExpiredError(LicensingError):
    """Licencia expirada."""

    expired_at: str | None = None
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.FATAL, init=False)
    user_message: str | None = field(default=None, init=False)
    context: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.message = "License expired"
        self.user_message = (
            "Tu licencia ha expirado. Por favor, renueva tu suscripción para continuar."
        )
        self.context = {"expired_at": self.expired_at}
        super().__post_init__()


@dataclass
class LicenseOfflineError(LicensingError):
    """No se puede verificar licencia sin conexión."""

    grace_days_remaining: int = 0
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.DEGRADED, init=False)
    user_message: str | None = field(default=None, init=False)
    context: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.message = "Cannot verify license offline"
        if self.grace_days_remaining > 0:
            self.user_message = (
                f"Sin conexión. Modo offline activo ({self.grace_days_remaining} días restantes). "
                "Conéctate a internet para verificar tu licencia."
            )
        else:
            self.user_message = "No se puede verificar la licencia sin conexión a internet."
        self.context = {"grace_days_remaining": self.grace_days_remaining}
        super().__post_init__()


@dataclass
class DeviceLimitError(LicensingError):
    """Límite de dispositivos alcanzado."""

    current_devices: int = 0
    max_devices: int = 0
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.FATAL, init=False)
    user_message: str | None = field(default=None, init=False)
    context: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.message = f"Device limit reached ({self.current_devices}/{self.max_devices})"
        self.user_message = (
            f"Has alcanzado el límite de {self.max_devices} dispositivo(s). "
            "Desactiva un dispositivo existente o actualiza tu plan."
        )
        self.context = {
            "current_devices": self.current_devices,
            "max_devices": self.max_devices,
        }
        super().__post_init__()


@dataclass
class DeviceCooldownError(LicensingError):
    """Dispositivo en período de cooldown tras desactivación."""

    hours_remaining: int = 0
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.FATAL, init=False)
    user_message: str | None = field(default=None, init=False)
    context: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.message = f"Device in cooldown period ({self.hours_remaining}h remaining)"
        self.user_message = (
            f"Este dispositivo fue desactivado recientemente. "
            f"Podrás reactivarlo en {self.hours_remaining} horas."
        )
        self.context = {"hours_remaining": self.hours_remaining}
        super().__post_init__()


@dataclass
class QuotaExceededError(LicensingError):
    """Cuota de paginas excedida."""

    current_usage: int = 0
    max_usage: int = 0
    billing_period: str = ""
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.FATAL, init=False)
    user_message: str | None = field(default=None, init=False)
    context: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.message = f"Page quota exceeded ({self.current_usage}/{self.max_usage})"
        self.user_message = (
            f"Has alcanzado el limite de {self.max_usage} paginas este mes "
            f"({self.current_usage}/{self.max_usage}). "
            "Espera al proximo periodo o actualiza tu plan."
        )
        self.context = {
            "current_usage": self.current_usage,
            "max_usage": self.max_usage,
            "billing_period": self.billing_period,
        }
        super().__post_init__()


@dataclass
class TierFeatureError(LicensingError):
    """Funcionalidad no disponible en el tier actual."""

    feature_name: str = ""
    required_tier: str = ""
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.FATAL, init=False)
    user_message: str | None = field(default=None, init=False)
    context: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self):
        self.message = f"Feature '{self.feature_name}' requires tier '{self.required_tier}'"
        self.user_message = (
            f"Esta funcionalidad requiere el plan {self.required_tier or 'Profesional'}. "
            "Actualiza tu plan para acceder."
        )
        self.context = {
            "feature_name": self.feature_name,
            "required_tier": self.required_tier,
        }
        super().__post_init__()
