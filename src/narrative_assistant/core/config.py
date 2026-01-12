"""
Sistema de configuración centralizado.

Prioridad de carga:
    CLI flags > Variables de entorno > Archivo config > Defaults
"""

import logging
import os
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

logger = logging.getLogger(__name__)

# Lock para thread-safety en singleton
_config_lock = threading.Lock()

DevicePreference = Literal["auto", "cuda", "mps", "cpu"]


@dataclass
class GPUConfig:
    """Configuración de GPU/dispositivo."""

    # Preferencia de dispositivo: auto, cuda, mps, cpu
    device_preference: DevicePreference = "auto"

    # spaCy específico
    spacy_gpu_enabled: bool = True
    spacy_gpu_memory_limit: Optional[int] = None  # MB, None = sin límite

    # sentence-transformers específico
    embeddings_gpu_enabled: bool = True
    embeddings_batch_size_gpu: int = 64
    embeddings_batch_size_cpu: int = 16

    # Configuración de memoria
    max_gpu_memory_fraction: float = 0.8  # Máximo 80% de VRAM

    @classmethod
    def from_env(cls) -> "GPUConfig":
        """Crea configuración desde variables de entorno."""
        return cls(
            device_preference=os.getenv("NA_DEVICE", "auto"),
            spacy_gpu_enabled=os.getenv("NA_SPACY_GPU", "true").lower() == "true",
            embeddings_gpu_enabled=os.getenv("NA_EMBEDDINGS_GPU", "true").lower() == "true",
            embeddings_batch_size_gpu=int(os.getenv("NA_BATCH_SIZE_GPU", "64")),
            embeddings_batch_size_cpu=int(os.getenv("NA_BATCH_SIZE_CPU", "16")),
        )


@dataclass
class NLPConfig:
    """Configuración de modelos NLP."""

    # spaCy
    spacy_model: str = "es_core_news_lg"
    spacy_model_path: Optional[Path] = None  # Ruta local, None = usar default

    # Embeddings
    embeddings_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embeddings_model_path: Optional[Path] = None  # Ruta local, None = usar default

    # Correferencia
    coreference_enabled: bool = True

    # Umbrales de análisis
    min_entity_confidence: float = 0.5
    context_window_chars: int = 50
    similarity_threshold: float = 0.85  # Para sugerir fusiones de entidades

    @classmethod
    def from_env(cls) -> "NLPConfig":
        """Crea configuración desde variables de entorno."""
        config = cls()

        if spacy_path := os.getenv("NA_SPACY_MODEL_PATH"):
            config.spacy_model_path = Path(spacy_path)

        if embeddings_path := os.getenv("NA_EMBEDDINGS_MODEL_PATH"):
            config.embeddings_model_path = Path(embeddings_path)

        return config


@dataclass
class ParsingConfig:
    """Configuración de parseo de documentos."""

    # Formatos habilitados
    enabled_formats: list[str] = field(
        default_factory=lambda: ["docx", "txt", "md", "pdf", "epub", "odt"]
    )

    # PDF específico
    pdf_min_chars_per_page: int = 100  # Bajo este umbral, se considera escaneado
    pdf_detect_headers_pages: int = 5  # Páginas a analizar para detectar headers

    # Normalización de texto
    normalize_quotes: bool = True
    normalize_dashes: bool = True
    normalize_whitespace: bool = True


@dataclass
class AlertConfig:
    """Configuración de alertas."""

    show_hints: bool = True
    auto_dismiss_low_confidence: bool = False
    min_confidence_to_show: float = 0.3


@dataclass
class PersistenceConfig:
    """Configuración de persistencia y sesiones."""

    # Auto-guardado
    autosave_interval_seconds: int = 60
    autosave_enabled: bool = True

    # Historial
    max_history_entries: int = 1000
    keep_dismissed_alerts: bool = True

    # Fingerprinting de documentos
    fingerprint_sample_size: int = 10000  # Caracteres a usar para fingerprint
    similarity_threshold_same_doc: float = 0.95  # Umbral para considerar mismo doc


def _find_project_root() -> Optional[Path]:
    """Busca la raíz del proyecto (donde está pyproject.toml)."""
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    return None


@dataclass
class AppConfig:
    """Configuración global de la aplicación."""

    gpu: GPUConfig = field(default_factory=GPUConfig)
    nlp: NLPConfig = field(default_factory=NLPConfig)
    parsing: ParsingConfig = field(default_factory=ParsingConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    persistence: PersistenceConfig = field(default_factory=PersistenceConfig)

    # Directorios
    data_dir: Path = field(
        default_factory=lambda: Path.home() / ".narrative_assistant"
    )
    cache_dir: Path = field(
        default_factory=lambda: Path.home() / ".narrative_assistant" / "cache"
    )
    models_dir: Optional[Path] = None  # Directorio de modelos locales

    # Logging
    log_level: str = "INFO"
    log_file: Optional[Path] = None

    def __post_init__(self):
        """Crea directorios si no existen y configura modelos locales."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Buscar directorio de modelos locales
        if self.models_dir is None:
            self._detect_models_dir()

    def _detect_models_dir(self) -> None:
        """Detecta el directorio de modelos locales."""
        # Prioridad:
        # 1. ./models/ (proyecto local)
        # 2. ~/.narrative_assistant/models/ (usuario)
        project_root = _find_project_root()
        if project_root:
            local_models = project_root / "models"
            if local_models.exists():
                self.models_dir = local_models
                logger.debug(f"Usando modelos locales: {local_models}")
                return

        user_models = self.data_dir / "models"
        if user_models.exists():
            self.models_dir = user_models
            logger.debug(f"Usando modelos de usuario: {user_models}")

    @property
    def db_path(self) -> Path:
        """Ruta a la base de datos principal."""
        return self.data_dir / "narrative_assistant.db"

    @property
    def secrets_dir(self) -> Path:
        """Directorio para API keys y secretos."""
        secrets = self.data_dir / "secrets"
        secrets.mkdir(parents=True, exist_ok=True)
        # Permisos restrictivos solo en Unix
        if sys.platform != "win32":
            secrets.chmod(0o700)
        return secrets

    @property
    def spacy_model_path(self) -> Optional[Path]:
        """Ruta al modelo spaCy local, si existe."""
        # Prioridad: config explícita > models_dir > None (usar HF cache)
        if self.nlp.spacy_model_path and self.nlp.spacy_model_path.exists():
            return self.nlp.spacy_model_path

        if self.models_dir:
            local_path = self.models_dir / "spacy" / self.nlp.spacy_model
            if local_path.exists():
                return local_path

        return None

    @property
    def embeddings_model_path(self) -> Optional[Path]:
        """Ruta al modelo de embeddings local, si existe."""
        # Prioridad: config explícita > models_dir > None (usar HF cache)
        if self.nlp.embeddings_model_path and self.nlp.embeddings_model_path.exists():
            return self.nlp.embeddings_model_path

        if self.models_dir:
            local_path = self.models_dir / "embeddings" / self.nlp.embeddings_model
            if local_path.exists():
                return local_path

        return None

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "AppConfig":
        """
        Carga configuración desde archivo y/o variables de entorno.

        Prioridad: Archivo > Variables de entorno > Defaults
        """
        config = cls()

        # Cargar desde archivo si existe
        if config_path and config_path.exists():
            config = cls._load_from_file(config_path)

        # Sobrescribir con variables de entorno
        config.gpu = GPUConfig.from_env()
        config.nlp = NLPConfig.from_env()

        if log_level := os.getenv("NA_LOG_LEVEL"):
            config.log_level = log_level

        if data_dir := os.getenv("NA_DATA_DIR"):
            config.data_dir = Path(data_dir)
            config.cache_dir = config.data_dir / "cache"

        return config

    @classmethod
    def _load_from_file(cls, path: Path) -> "AppConfig":
        """Carga configuración desde archivo TOML/YAML."""
        # Por ahora, solo TOML
        if path.suffix == ".toml":
            try:
                import tomllib

                with open(path, "rb") as f:
                    data = tomllib.load(f)
                # TODO: Mapear data a AppConfig
                logger.info(f"Configuración cargada desde {path}")
            except ImportError:
                logger.warning("tomllib no disponible, usando defaults")
            except Exception as e:
                logger.warning(f"Error cargando config: {e}")

        return cls()

    def save(self, path: Optional[Path] = None) -> Path:
        """Guarda configuración a archivo."""
        path = path or (self.data_dir / "config.toml")
        # TODO: Implementar serialización a TOML
        logger.info(f"Configuración guardada en {path}")
        return path


# Singleton thread-safe
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Obtiene la configuración global (thread-safe)."""
    global _config
    if _config is None:
        with _config_lock:
            # Double-checked locking
            if _config is None:
                _config = AppConfig.load()
    return _config


def set_config(config: AppConfig) -> None:
    """Establece la configuración global (thread-safe)."""
    global _config
    with _config_lock:
        _config = config


def reset_config() -> None:
    """Resetea la configuración a defaults (thread-safe)."""
    global _config
    with _config_lock:
        _config = None
