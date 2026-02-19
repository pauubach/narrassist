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
from typing import Literal

logger = logging.getLogger(__name__)

# Lock para thread-safety en singleton
_config_lock = threading.Lock()


def _get_default_data_dir() -> Path:
    """
    Determina el directorio de datos según el entorno.

    - Producción (NA_EMBEDDED=1): usa LOCALAPPDATA/Narrative Assistant (Windows)
      o ~/.local/share/narrative-assistant (Linux/Mac)
    - Desarrollo: usa ~/.narrative_assistant
    """
    is_embedded = os.environ.get("NA_EMBEDDED") == "1"

    if is_embedded:
        # Modo producción - usar rutas estándar del sistema
        if sys.platform == "win32":
            localappdata = os.environ.get("LOCALAPPDATA", "")
            if localappdata:
                return Path(localappdata) / "Narrative Assistant" / "data"
        elif sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "Narrative Assistant"
        else:
            # Linux
            xdg_data = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
            return Path(xdg_data) / "narrative-assistant"

    # Modo desarrollo - ruta legacy
    return Path.home() / ".narrative_assistant"


DevicePreference = Literal["auto", "cuda", "mps", "cpu"]


@dataclass
class GPUConfig:
    """Configuración de GPU/dispositivo."""

    # Preferencia de dispositivo: auto, cuda, mps, cpu
    device_preference: DevicePreference = "auto"

    # spaCy específico
    spacy_gpu_enabled: bool = True
    spacy_gpu_memory_limit: int | None = None  # MB, None = sin límite

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
            device_preference=str(os.getenv("NA_DEVICE", "auto")),
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
    spacy_model_path: Path | None = None  # Ruta local, None = usar default

    # Embeddings
    embeddings_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embeddings_model_path: Path | None = None  # Ruta local, None = usar default

    # Transformer NER (PlanTL RoBERTa)
    transformer_ner_enabled: bool = True
    transformer_ner_model: str = "roberta-base-bne"

    # Correferencia
    coreference_enabled: bool = True

    # Umbrales de análisis
    min_entity_confidence: float = 0.5
    context_window_chars: int = 50
    similarity_threshold: float = 0.85  # Para sugerir fusiones de entidades (legacy)
    # Umbral para fusión semántica automática
    # NOTA: 0.65 es demasiado bajo para embeddings multilingual (genera muchos falsos positivos)
    # Valor recomendado: 0.80-0.85 para evitar fusiones absurdas
    semantic_fusion_threshold: float = 0.82

    # Redundancia semántica (HABILITADA POR DEFECTO)
    semantic_redundancy_enabled: bool = True
    semantic_redundancy_threshold: float = 0.85  # Umbral similitud (0.70-0.95)
    semantic_redundancy_mode: str = "balanced"  # fast, balanced, thorough

    @classmethod
    def from_env(cls) -> "NLPConfig":
        """Crea configuración desde variables de entorno."""
        config = cls()

        if spacy_path := os.getenv("NA_SPACY_MODEL_PATH"):
            config.spacy_model_path = Path(spacy_path)

        if embeddings_path := os.getenv("NA_EMBEDDINGS_MODEL_PATH"):
            config.embeddings_model_path = Path(embeddings_path)

        # Semantic redundancy config
        config.semantic_redundancy_enabled = (
            os.getenv("NA_SEMANTIC_REDUNDANCY_ENABLED", "true").lower() == "true"
        )
        if threshold := os.getenv("NA_SEMANTIC_REDUNDANCY_THRESHOLD"):
            config.semantic_redundancy_threshold = float(threshold)
        if mode := os.getenv("NA_SEMANTIC_REDUNDANCY_MODE"):
            config.semantic_redundancy_mode = mode

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
class GrammarConfig:
    """Configuración del corrector gramatical."""

    # Habilitar/deshabilitar reglas específicas
    check_dequeismo: bool = True
    check_queismo: bool = True
    check_laismo: bool = True
    check_loismo: bool = True
    check_gender_agreement: bool = True
    check_number_agreement: bool = True
    check_redundancy: bool = True
    check_punctuation: bool = True
    check_sentence_structure: bool = True

    # LanguageTool (opcional, requiere Java)
    use_languagetool: bool = True  # Intentar usar si está disponible
    languagetool_url: str = "http://localhost:8081"

    # LLM para análisis contextual (opcional)
    use_llm: bool = False  # Usar Ollama para análisis avanzado

    # Umbral de confianza mínimo para mostrar errores
    min_confidence: float = 0.5

    # Usar análisis spaCy más preciso (más lento)
    use_spacy_analysis: bool = True

    @classmethod
    def from_env(cls) -> "GrammarConfig":
        """Crea configuración desde variables de entorno."""
        return cls(
            use_languagetool=os.getenv("NA_USE_LANGUAGETOOL", "true").lower() == "true",
            languagetool_url=os.getenv("NA_LANGUAGETOOL_URL", "http://localhost:8081"),
            use_llm=os.getenv("NA_GRAMMAR_USE_LLM", "false").lower() == "true",
            min_confidence=float(os.getenv("NA_GRAMMAR_MIN_CONFIDENCE", "0.5")),
        )


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


def _find_project_root() -> Path | None:
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
    grammar: GrammarConfig = field(default_factory=GrammarConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    persistence: PersistenceConfig = field(default_factory=PersistenceConfig)

    # Directorios
    data_dir: Path = field(default_factory=_get_default_data_dir)
    cache_dir: Path = field(default_factory=lambda: _get_default_data_dir() / "cache")
    models_dir: Path | None = None  # Directorio de modelos locales

    # Logging
    log_level: str = "INFO"
    log_file: Path | None = None

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
    def spacy_model_path(self) -> Path | None:
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
    def embeddings_model_path(self) -> Path | None:
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
    def load(cls, config_path: Path | None = None) -> "AppConfig":
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
        config.grammar = GrammarConfig.from_env()

        if log_level := os.getenv("NA_LOG_LEVEL"):
            config.log_level = log_level

        if data_dir := os.getenv("NA_DATA_DIR"):
            config.data_dir = Path(data_dir)
            config.cache_dir = config.data_dir / "cache"

        # Asegurar que los directorios existan después de cualquier override
        config.data_dir.mkdir(parents=True, exist_ok=True)
        config.cache_dir.mkdir(parents=True, exist_ok=True)

        # Re-detectar modelos para el data_dir final
        config._detect_models_dir()

        return config

    @classmethod
    def _load_from_file(cls, path: Path) -> "AppConfig":
        """Carga configuración desde archivo TOML/YAML."""
        if path.suffix == ".toml":
            try:
                import tomllib

                with open(path, "rb") as f:
                    data = tomllib.load(f)

                config = cls()

                # Mapear GPU config
                if gpu_data := data.get("gpu"):
                    config.gpu = GPUConfig(
                        device_preference=gpu_data.get("device_preference", "auto"),
                        spacy_gpu_enabled=gpu_data.get("spacy_gpu_enabled", True),
                        spacy_gpu_memory_limit=gpu_data.get("spacy_gpu_memory_limit"),
                        embeddings_gpu_enabled=gpu_data.get("embeddings_gpu_enabled", True),
                        embeddings_batch_size_gpu=gpu_data.get("embeddings_batch_size_gpu", 64),
                        embeddings_batch_size_cpu=gpu_data.get("embeddings_batch_size_cpu", 16),
                        max_gpu_memory_fraction=gpu_data.get("max_gpu_memory_fraction", 0.8),
                    )

                # Mapear NLP config
                if nlp_data := data.get("nlp"):
                    config.nlp = NLPConfig(
                        spacy_model=nlp_data.get("spacy_model", "es_core_news_lg"),
                        spacy_model_path=Path(nlp_data["spacy_model_path"])
                        if nlp_data.get("spacy_model_path")
                        else None,
                        embeddings_model=nlp_data.get(
                            "embeddings_model", "paraphrase-multilingual-MiniLM-L12-v2"
                        ),
                        embeddings_model_path=Path(nlp_data["embeddings_model_path"])
                        if nlp_data.get("embeddings_model_path")
                        else None,
                        coreference_enabled=nlp_data.get("coreference_enabled", True),
                        min_entity_confidence=nlp_data.get("min_entity_confidence", 0.5),
                        context_window_chars=nlp_data.get("context_window_chars", 50),
                        similarity_threshold=nlp_data.get("similarity_threshold", 0.85),
                    )

                # Mapear Grammar config
                if grammar_data := data.get("grammar"):
                    config.grammar = GrammarConfig(
                        check_dequeismo=grammar_data.get("check_dequeismo", True),
                        check_queismo=grammar_data.get("check_queismo", True),
                        check_laismo=grammar_data.get("check_laismo", True),
                        check_loismo=grammar_data.get("check_loismo", True),
                        check_gender_agreement=grammar_data.get("check_gender_agreement", True),
                        check_number_agreement=grammar_data.get("check_number_agreement", True),
                        check_redundancy=grammar_data.get("check_redundancy", True),
                        check_punctuation=grammar_data.get("check_punctuation", True),
                        check_sentence_structure=grammar_data.get("check_sentence_structure", True),
                        use_languagetool=grammar_data.get("use_languagetool", True),
                        languagetool_url=grammar_data.get(
                            "languagetool_url", "http://localhost:8081"
                        ),
                        use_llm=grammar_data.get("use_llm", False),
                        min_confidence=grammar_data.get("min_confidence", 0.5),
                        use_spacy_analysis=grammar_data.get("use_spacy_analysis", True),
                    )

                # Mapear Alerts config
                if alerts_data := data.get("alerts"):
                    config.alerts = AlertConfig(
                        show_hints=alerts_data.get("show_hints", True),
                        auto_dismiss_low_confidence=alerts_data.get(
                            "auto_dismiss_low_confidence", False
                        ),
                        min_confidence_to_show=alerts_data.get("min_confidence_to_show", 0.3),
                    )

                # Mapear Persistence config
                if persistence_data := data.get("persistence"):
                    config.persistence = PersistenceConfig(
                        autosave_interval_seconds=persistence_data.get(
                            "autosave_interval_seconds", 60
                        ),
                        autosave_enabled=persistence_data.get("autosave_enabled", True),
                        max_history_entries=persistence_data.get("max_history_entries", 1000),
                        keep_dismissed_alerts=persistence_data.get("keep_dismissed_alerts", True),
                        fingerprint_sample_size=persistence_data.get(
                            "fingerprint_sample_size", 10000
                        ),
                        similarity_threshold_same_doc=persistence_data.get(
                            "similarity_threshold_same_doc", 0.95
                        ),
                    )

                # Mapear directorios y logging
                if data_dir := data.get("data_dir"):
                    config.data_dir = Path(data_dir)
                    config.cache_dir = config.data_dir / "cache"
                if log_level := data.get("log_level"):
                    config.log_level = log_level

                logger.info(f"Configuración cargada desde {path}")
                return config

            except ImportError:
                logger.warning("tomllib no disponible, usando defaults")
            except Exception as e:
                logger.warning(f"Error cargando config: {e}")

        return cls()

    def save(self, path: Path | None = None) -> Path:
        """Guarda configuración a archivo TOML."""
        if path is None:
            path = self.data_dir / "config.toml"
        elif isinstance(path, str):
            path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Construir diccionario de configuración
        config_dict = {
            "gpu": {
                "device_preference": self.gpu.device_preference,
                "spacy_gpu_enabled": self.gpu.spacy_gpu_enabled,
                "spacy_gpu_memory_limit": self.gpu.spacy_gpu_memory_limit,
                "embeddings_gpu_enabled": self.gpu.embeddings_gpu_enabled,
                "embeddings_batch_size_gpu": self.gpu.embeddings_batch_size_gpu,
                "embeddings_batch_size_cpu": self.gpu.embeddings_batch_size_cpu,
                "max_gpu_memory_fraction": self.gpu.max_gpu_memory_fraction,
            },
            "nlp": {
                "spacy_model": self.nlp.spacy_model,
                "spacy_model_path": str(self.nlp.spacy_model_path)
                if self.nlp.spacy_model_path
                else None,
                "embeddings_model": self.nlp.embeddings_model,
                "embeddings_model_path": str(self.nlp.embeddings_model_path)
                if self.nlp.embeddings_model_path
                else None,
                "coreference_enabled": self.nlp.coreference_enabled,
                "min_entity_confidence": self.nlp.min_entity_confidence,
                "context_window_chars": self.nlp.context_window_chars,
                "similarity_threshold": self.nlp.similarity_threshold,
            },
            "grammar": {
                "check_dequeismo": self.grammar.check_dequeismo,
                "check_queismo": self.grammar.check_queismo,
                "check_laismo": self.grammar.check_laismo,
                "check_loismo": self.grammar.check_loismo,
                "check_gender_agreement": self.grammar.check_gender_agreement,
                "check_number_agreement": self.grammar.check_number_agreement,
                "check_redundancy": self.grammar.check_redundancy,
                "check_punctuation": self.grammar.check_punctuation,
                "check_sentence_structure": self.grammar.check_sentence_structure,
                "use_languagetool": self.grammar.use_languagetool,
                "languagetool_url": self.grammar.languagetool_url,
                "use_llm": self.grammar.use_llm,
                "min_confidence": self.grammar.min_confidence,
                "use_spacy_analysis": self.grammar.use_spacy_analysis,
            },
            "alerts": {
                "show_hints": self.alerts.show_hints,
                "auto_dismiss_low_confidence": self.alerts.auto_dismiss_low_confidence,
                "min_confidence_to_show": self.alerts.min_confidence_to_show,
            },
            "persistence": {
                "autosave_interval_seconds": self.persistence.autosave_interval_seconds,
                "autosave_enabled": self.persistence.autosave_enabled,
                "max_history_entries": self.persistence.max_history_entries,
                "keep_dismissed_alerts": self.persistence.keep_dismissed_alerts,
                "fingerprint_sample_size": self.persistence.fingerprint_sample_size,
                "similarity_threshold_same_doc": self.persistence.similarity_threshold_same_doc,
            },
            "data_dir": str(self.data_dir),
            "log_level": self.log_level,
        }

        # Escribir TOML manualmente (tomllib es solo lectura)
        lines = ["# Narrative Assistant Configuration\n"]
        for section, values in config_dict.items():
            if isinstance(values, dict):
                lines.append(f"\n[{section}]\n")
                for key, value in values.items():
                    if value is None:
                        continue
                    elif isinstance(value, bool):
                        lines.append(f"{key} = {str(value).lower()}\n")
                    elif isinstance(value, str):
                        lines.append(f'{key} = "{value}"\n')
                    elif isinstance(value, (int, float)):
                        lines.append(f"{key} = {value}\n")
            else:
                if isinstance(values, str):
                    lines.append(f'{section} = "{values}"\n')
                else:
                    lines.append(f"{section} = {values}\n")

        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        logger.info(f"Configuración guardada en {path}")
        return path


# Singleton thread-safe
_config: AppConfig | None = None


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
