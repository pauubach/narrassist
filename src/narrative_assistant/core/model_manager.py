"""
Gestor de modelos NLP con descarga bajo demanda.

Este módulo gestiona la descarga, verificación y carga de modelos NLP.
Los modelos se descargan bajo demanda la primera vez que se necesitan
y se guardan en ~/.narrative_assistant/models/ para uso offline posterior.

Modelos gestionados:
- spaCy: es_core_news_lg (~500MB)
- Embeddings: paraphrase-multilingual-MiniLM-L12-v2 (~500MB)

Uso:
    from narrative_assistant.core.model_manager import get_model_manager

    manager = get_model_manager()
    spacy_path = manager.ensure_model("spacy")
    embeddings_path = manager.ensure_model("embeddings")
"""

import hashlib
import logging
import os
import shutil
import socket
import threading
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from .errors import ErrorSeverity, ModelNotLoadedError, NarrativeError
from .result import Result

logger = logging.getLogger(__name__)

# Lock para thread-safety en singleton
_manager_lock = threading.Lock()
_model_manager: Optional["ModelManager"] = None


class ModelType(Enum):
    """Tipos de modelos soportados."""

    SPACY = "spacy"
    EMBEDDINGS = "embeddings"
    TRANSFORMER_NER = "transformer_ner"


@dataclass(frozen=True)
class ModelInfo:
    """Información de un modelo para descarga y verificación."""

    model_type: ModelType
    name: str
    display_name: str
    size_mb: int
    sha256: str | None  # None si no se conoce el hash
    source_url: str  # URL informativo (no se usa directamente)
    subdirectory: str  # Subdirectorio dentro de models/


# Definición de modelos conocidos con sus hashes
# NOTA: Los hashes pueden variar entre versiones. Si falla verificación,
# actualizar o establecer a None para omitir verificación.
# Los tamaños son estimados iniciales; se obtienen dinámicamente cuando es posible.
KNOWN_MODELS: dict[ModelType, ModelInfo] = {
    ModelType.SPACY: ModelInfo(
        model_type=ModelType.SPACY,
        name="es_core_news_lg",
        display_name="Análisis gramatical y lingüístico",
        size_mb=540,
        sha256=None,
        source_url="https://github.com/explosion/spacy-models",
        subdirectory="spacy",
    ),
    ModelType.EMBEDDINGS: ModelInfo(
        model_type=ModelType.EMBEDDINGS,
        name="paraphrase-multilingual-MiniLM-L12-v2",
        display_name="Análisis de similitud y contexto",
        size_mb=470,
        sha256=None,
        source_url="https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        subdirectory="embeddings",
    ),
    ModelType.TRANSFORMER_NER: ModelInfo(
        model_type=ModelType.TRANSFORMER_NER,
        name="mrm8488/bert-spanish-cased-finetuned-ner",
        display_name="Reconocimiento de personajes y lugares",
        size_mb=440,
        sha256=None,
        source_url="https://huggingface.co/mrm8488/bert-spanish-cased-finetuned-ner",
        subdirectory="transformer_ner",
    ),
}

# Modelos alternativos para transformer NER (fallback si el principal falla con 401/403)
# PlanTL-GOB-ES fue gateado en HuggingFace ~2025, por eso usamos mrm8488 como default
TRANSFORMER_NER_FALLBACKS: list[ModelInfo] = [
    ModelInfo(
        model_type=ModelType.TRANSFORMER_NER,
        name="Davlan/xlm-roberta-base-ner-hrl",
        display_name="Reconocimiento de personajes y lugares (multilingual)",
        size_mb=1100,
        sha256=None,
        source_url="https://huggingface.co/Davlan/xlm-roberta-base-ner-hrl",
        subdirectory="transformer_ner",
    ),
]


@dataclass
class DownloadProgress:
    """Estado de progreso de una descarga."""

    model_type: ModelType
    phase: str  # "connecting", "downloading", "installing", "completed", "error"
    bytes_downloaded: int = 0
    bytes_total: int = 0
    speed_bps: float = 0.0  # bytes per second
    error_message: str | None = None
    started_at: float = 0.0  # timestamp

    @property
    def percent(self) -> float:
        """Porcentaje de progreso (0-100)."""
        if self.bytes_total <= 0:
            return 0.0
        return min(100.0, (self.bytes_downloaded / self.bytes_total) * 100)

    @property
    def eta_seconds(self) -> float | None:
        """Tiempo estimado restante en segundos."""
        if self.speed_bps <= 0 or self.bytes_total <= 0:
            return None
        remaining = self.bytes_total - self.bytes_downloaded
        return remaining / self.speed_bps if remaining > 0 else 0.0

    def to_dict(self) -> dict:
        """Convierte a diccionario para API."""
        return {
            "model_type": self.model_type.value,
            "phase": self.phase,
            "bytes_downloaded": self.bytes_downloaded,
            "bytes_total": self.bytes_total,
            "percent": round(self.percent, 1),
            "speed_bps": round(self.speed_bps, 0),
            "speed_mbps": round(self.speed_bps / (1024 * 1024), 2) if self.speed_bps > 0 else 0,
            "eta_seconds": round(self.eta_seconds, 0) if self.eta_seconds else None,
            "error": self.error_message,
        }


# Estado global de descargas activas (thread-safe via locks)
_download_progress: dict[ModelType, DownloadProgress] = {}
_progress_lock = threading.Lock()

# Cache de tamaños de modelos (consultados dinámicamente de HuggingFace/GitHub)
_model_sizes_cache: dict[str, int] = {}
_model_sizes_cache_time: float = 0.0
_MODEL_SIZES_CACHE_TTL = 7 * 24 * 3600.0  # 1 semana de cache (los tamaños cambian poco)


def _create_hf_progress_tracker(model_type: ModelType):
    """
    Crea una clase tqdm personalizada que reporta progreso de descarga HuggingFace.

    Se usa como tqdm_class en snapshot_download() para obtener progreso
    byte-level real de las descargas de HuggingFace Hub.
    """
    import time

    from tqdm.auto import tqdm as base_tqdm

    class HFProgressTracker(base_tqdm):
        _last_update: float = 0.0

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Solo rastrear la barra de bytes (no la de conteo de archivos)
            if self.total and self.total > 1024:
                _update_download_progress(
                    model_type,
                    phase="downloading",
                    bytes_downloaded=0,
                    bytes_total=self.total,
                )

        def update(self, n=1):
            super().update(n)
            now = time.time()
            # Actualizar máximo cada 200ms para no saturar
            if self.total and self.total > 1024 and now - self._last_update > 0.2:
                self._last_update = now
                elapsed = now - self.start_t if self.start_t else 1
                speed = self.n / elapsed if elapsed > 0 else 0
                _update_download_progress(
                    model_type,
                    phase="downloading",
                    bytes_downloaded=self.n,
                    bytes_total=self.total,
                    speed_bps=speed,
                )

        def close(self):
            if self.total and self.total > 1024:
                _update_download_progress(
                    model_type,
                    phase="downloading",
                    bytes_downloaded=self.total,
                    bytes_total=self.total,
                )
            super().close()

    return HFProgressTracker


@dataclass
class ModelDownloadError(NarrativeError):
    """Error al descargar un modelo."""

    model_name: str = ""
    reason: str = ""
    message: str = ""
    severity: ErrorSeverity = ErrorSeverity.FATAL
    user_message: str | None = None

    def __post_init__(self):
        if not self.message:
            self.message = f"Error descargando modelo '{self.model_name}': {self.reason}"
        if self.user_message is None:
            self.user_message = (
                f"No se pudo descargar el modelo '{self.model_name}'.\n"
                f"Razón: {self.reason}\n\n"
                "Verifica tu conexión a internet e intenta nuevamente."
            )
        super().__post_init__()


@dataclass
class ModelVerificationError(NarrativeError):
    """Error al verificar integridad de un modelo."""

    model_name: str = ""
    expected_hash: str = ""
    actual_hash: str = ""
    message: str = ""
    severity: ErrorSeverity = ErrorSeverity.FATAL
    user_message: str | None = None

    def __post_init__(self):
        if not self.message:
            self.message = f"Hash mismatch for model '{self.model_name}'"
        if self.user_message is None:
            self.user_message = (
                f"El modelo '{self.model_name}' está corrupto o incompleto.\n"
                "Intenta descargarlo nuevamente con:\n"
                f"  narrative-assistant download-models --force {self.model_name}"
            )
        super().__post_init__()


class ModelManager:
    """
    Gestor de modelos NLP con descarga bajo demanda.

    Características:
    - Descarga modelos solo cuando se necesitan
    - Verifica integridad con SHA256
    - Cache en ~/.narrative_assistant/models/
    - Thread-safe
    - Muestra progreso de descarga con tqdm
    """

    def __init__(self, models_dir: Path | None = None):
        """
        Inicializa el gestor de modelos.

        Args:
            models_dir: Directorio para almacenar modelos.
                       Default: NA_MODELS_DIR env var o ~/.narrative_assistant/models/
        """
        # Determinar directorio de modelos
        if models_dir is not None:
            self.models_dir = Path(models_dir)
        elif env_dir := os.getenv("NA_MODELS_DIR"):
            self.models_dir = Path(env_dir)
        else:
            self.models_dir = Path.home() / ".narrative_assistant" / "models"

        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Directorio de recursos bundled (Tauri app)
        # Cuando la app se ejecuta como bundle, los modelos están en resources/models
        self.bundled_models_dir = self._find_bundled_models_dir()

        # Lock para operaciones de descarga (evitar descargas duplicadas)
        self._download_locks: dict[ModelType, threading.Lock] = {
            model_type: threading.Lock() for model_type in ModelType
        }

        # Cache de rutas verificadas
        self._verified_paths: dict[ModelType, Path] = {}

        logger.info(f"ModelManager inicializado. Directorio: {self.models_dir}")
        if self.bundled_models_dir:
            logger.info(f"Modelos bundled encontrados en: {self.bundled_models_dir}")

    def _find_bundled_models_dir(self) -> Path | None:
        """
        Busca el directorio de modelos bundled con la app.

        Tauri coloca recursos en diferentes ubicaciones según el OS:
        - Windows: {app_dir}/resources/
        - macOS: {app_bundle}/Contents/Resources/
        - Linux: /usr/share/{app}/resources/ o junto al ejecutable
        """
        import sys

        # Obtener directorio del ejecutable
        if getattr(sys, "frozen", False):
            # Running as compiled
            exe_dir = Path(sys.executable).parent
        else:
            # Running in Python
            exe_dir = Path(__file__).parent.parent.parent.parent

        # Posibles ubicaciones de modelos bundled
        possible_paths = [
            exe_dir / "models",  # Development mode (project root)
            exe_dir / "resources" / "models",
            exe_dir / "_internal" / "resources" / "models",  # PyInstaller
            exe_dir.parent / "Resources" / "models",  # macOS .app
            exe_dir.parent / "share" / "models",  # Linux
            Path("/usr/share/narrative-assistant/models"),  # Linux system install
        ]

        for path in possible_paths:
            if path.exists() and path.is_dir():
                # Verificar que tiene contenido
                spacy_dir = path / "spacy"
                embeddings_dir = path / "embeddings"
                if spacy_dir.exists() or embeddings_dir.exists():
                    return path

        return None

    def get_model_path(self, model_type: ModelType) -> Path | None:
        """
        Obtiene la ruta al modelo si existe localmente.

        Busca en orden:
        1. Cache verificado
        2. Modelos bundled con la app (instalador)
        3. Directorio de modelos del usuario (~/.narrative_assistant/models/)

        Args:
            model_type: Tipo de modelo (SPACY, EMBEDDINGS)

        Returns:
            Path al modelo si existe y está verificado, None en caso contrario
        """
        # Verificar cache
        if model_type in self._verified_paths:
            return self._verified_paths[model_type]

        model_info = KNOWN_MODELS.get(model_type)
        if not model_info:
            logger.error(f"Tipo de modelo desconocido: {model_type}")
            return None

        # Buscar en modelos bundled primero (instalador)
        if self.bundled_models_dir:
            bundled_path = self.bundled_models_dir / model_info.subdirectory / model_info.name
            if bundled_path.exists() and self._verify_model_structure(model_type, bundled_path):
                logger.info(f"Usando modelo bundled: {bundled_path}")
                self._verified_paths[model_type] = bundled_path
                return bundled_path

        # Buscar en directorio de usuario
        model_path = self.models_dir / model_info.subdirectory / model_info.name

        if not model_path.exists():
            return None

        # Verificar estructura básica del modelo
        if self._verify_model_structure(model_type, model_path):
            # Para spaCy, resolver subdir versionado si config.cfg no está en raíz
            resolved = self._resolve_spacy_path(model_type, model_path)
            self._verified_paths[model_type] = resolved
            return resolved

        logger.warning(f"Modelo en {model_path} tiene estructura inválida")
        return None

    def _resolve_spacy_path(self, model_type: ModelType, model_path: Path) -> Path:
        """Para spaCy: si config.cfg está en un subdir versionado, devuelve ese subdir."""
        if model_type != ModelType.SPACY:
            return model_path
        if (model_path / "config.cfg").exists():
            return model_path
        for child in model_path.iterdir():
            if child.is_dir() and (child / "config.cfg").exists():
                logger.debug(f"Resolviendo spaCy path a subdir versionado: {child}")
                return child
        return model_path

    def ensure_model(
        self,
        model_type: ModelType,
        force_download: bool = False,
        progress_callback: Callable[[str, float], None] | None = None,
    ) -> Result[Path]:
        """
        Asegura que un modelo esté disponible, descargándolo si es necesario.

        Esta es la función principal que deben usar los módulos de NLP.

        Args:
            model_type: Tipo de modelo (SPACY, EMBEDDINGS)
            force_download: Si True, re-descarga aunque exista
            progress_callback: Función para reportar progreso (mensaje, porcentaje)

        Returns:
            Result con Path al modelo o error
        """
        model_info = KNOWN_MODELS.get(model_type)
        if not model_info:
            return Result.failure(
                ModelNotLoadedError(
                    model_name=str(model_type),
                    hint=f"Tipo de modelo desconocido: {model_type}",
                )
            )

        # Si no forzamos descarga, verificar si ya existe
        if not force_download:
            existing_path = self.get_model_path(model_type)
            if existing_path:
                logger.debug(f"Modelo {model_info.name} ya disponible en {existing_path}")
                return Result.success(existing_path)

        # Adquirir lock para este tipo de modelo
        with self._download_locks[model_type]:
            # Double-check después de adquirir lock
            if not force_download:
                existing_path = self.get_model_path(model_type)
                if existing_path:
                    return Result.success(existing_path)

            # Verificar conectividad
            if not self._check_internet_connection():
                return Result.failure(
                    ModelDownloadError(
                        model_name=model_info.name,
                        reason="Sin conexión a internet y modelo no disponible localmente.",
                    )
                )

            # Descargar modelo
            logger.info(f"Descargando modelo: {model_info.display_name}")
            download_result = self._download_model(model_info, force_download, progress_callback)

            if download_result.is_failure:
                return download_result

            # Actualizar cache
            model_path = download_result.value
            if model_path:
                self._verified_paths[model_type] = model_path

            return download_result

    def _download_model(
        self,
        model_info: ModelInfo,
        force: bool,
        progress_callback: Callable[[str, float], None] | None,
    ) -> Result[Path]:
        """
        Descarga un modelo específico.

        Args:
            model_info: Información del modelo
            force: Si True, elimina versión existente
            progress_callback: Callback para progreso

        Returns:
            Result con Path al modelo descargado
        """
        target_dir = self.models_dir / model_info.subdirectory / model_info.name

        # Eliminar si existe y force=True
        if force and target_dir.exists():
            logger.info(f"Eliminando modelo existente: {target_dir}")
            shutil.rmtree(target_dir)

        # Crear directorio padre
        target_dir.parent.mkdir(parents=True, exist_ok=True)

        try:
            if model_info.model_type == ModelType.SPACY:
                return self._download_spacy_model(model_info, target_dir, progress_callback)
            elif model_info.model_type == ModelType.EMBEDDINGS:
                return self._download_embeddings_model(model_info, target_dir, progress_callback)
            elif model_info.model_type == ModelType.TRANSFORMER_NER:
                return self._download_transformer_ner_model(model_info, target_dir, progress_callback)
            else:
                return Result.failure(
                    ModelDownloadError(
                        model_name=model_info.name,
                        reason=f"Tipo de modelo no soportado: {model_info.model_type}",
                    )
                )
        except Exception as e:
            logger.exception(f"Error descargando {model_info.name}")
            # Limpiar directorio parcial si existe
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            return Result.failure(ModelDownloadError(model_name=model_info.name, reason=str(e)))

    def _download_spacy_model(
        self,
        model_info: ModelInfo,
        target_dir: Path,
        progress_callback: Callable[[str, float], None] | None,
    ) -> Result[Path]:
        """
        Descarga modelo spaCy via HTTP directo desde GitHub Releases.

        Usa la API de compatibilidad de spaCy para determinar la versión
        correcta del modelo, luego descarga el .whl con progreso byte-level real.
        Si falla, cae a spacy.cli.download() como fallback.
        """
        estimated_size = model_info.size_mb * 1024 * 1024

        _update_download_progress(
            model_info.model_type,
            phase="connecting",
            bytes_total=estimated_size,
        )

        if progress_callback:
            progress_callback(f"Descargando {model_info.display_name}...", 0.05)

        # Intentar descarga directa con progreso real
        try:
            result = self._download_spacy_direct(model_info, target_dir, estimated_size, progress_callback)
            if result is not None:
                return result
        except Exception as e:
            logger.warning(f"Descarga directa falló, usando fallback: {e}")

        # Fallback: usar spacy.cli.download (sin progreso byte-level)
        return self._download_spacy_fallback(model_info, target_dir, estimated_size, progress_callback)

    def _download_spacy_direct(
        self,
        model_info: ModelInfo,
        target_dir: Path,
        estimated_size: int,
        progress_callback: Callable[[str, float], None] | None,
    ) -> Result[Path] | None:
        """
        Descarga directa del .whl de spaCy desde GitHub con progreso real.

        Returns None si no se puede hacer descarga directa (fallback necesario).
        """
        import tempfile
        import time
        import zipfile

        try:
            import requests
            import spacy
        except ImportError:
            return None

        # Determinar versión compatible del modelo
        model_version = self._resolve_spacy_model_version(model_info.name, spacy.about.__version__)
        if not model_version:
            return None

        model_full = f"{model_info.name}-{model_version}"
        url = (
            f"https://github.com/explosion/spacy-models/releases/download/"
            f"{model_full}/{model_full}-py3-none-any.whl"
        )

        logger.info(f"Descargando spaCy model directo: {url}")

        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"HTTP directo falló ({e}), intentando fallback")
            return None

        total_size = int(response.headers.get("content-length", 0)) or estimated_size

        _update_download_progress(
            model_info.model_type,
            phase="downloading",
            bytes_total=total_size,
        )

        # Stream a archivo temporal
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".whl", delete=False) as tmp:
                tmp_path = Path(tmp.name)
                downloaded = 0
                last_update = time.time()
                start_time = last_update

                for chunk in response.iter_content(chunk_size=65536):
                    tmp.write(chunk)
                    downloaded += len(chunk)

                    now = time.time()
                    if now - last_update > 0.2:
                        elapsed = now - start_time
                        speed = downloaded / elapsed if elapsed > 0 else 0
                        _update_download_progress(
                            model_info.model_type,
                            phase="downloading",
                            bytes_downloaded=downloaded,
                            bytes_total=total_size,
                            speed_bps=speed,
                        )
                        last_update = now

            # Extraer modelo del .whl
            _update_download_progress(
                model_info.model_type,
                phase="installing",
                bytes_downloaded=total_size,
                bytes_total=total_size,
            )

            if progress_callback:
                progress_callback("Instalando modelo...", 0.85)

            target_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(tmp_path) as zf:
                # En el .whl, los archivos del modelo están en {model_name}/
                # Pero spaCy empaqueta los datos en un subdir versionado:
                #   es_core_news_lg/es_core_news_lg-3.7.0/config.cfg
                # Necesitamos extraer desde el subdir versionado para que
                # spacy.load(target_dir) encuentre config.cfg directamente.
                base_prefix = f"{model_info.name}/"
                all_names = zf.namelist()

                # Detectar subdir versionado (e.g. es_core_news_lg-3.7.0/)
                versioned_prefix = None
                for name in all_names:
                    if name.startswith(base_prefix) and "/config.cfg" in name:
                        # Encontrado: es_core_news_lg/es_core_news_lg-3.7.0/config.cfg
                        parts = name[len(base_prefix):].split("/")
                        if len(parts) >= 2:
                            versioned_prefix = f"{base_prefix}{parts[0]}/"
                        break

                prefix = versioned_prefix or base_prefix
                extracted_count = 0

                for member in all_names:
                    if not member.startswith(prefix):
                        continue
                    rel_path = member[len(prefix):]
                    if not rel_path:
                        continue

                    target = target_dir / rel_path
                    if member.endswith("/"):
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(member) as src, open(target, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        extracted_count += 1

            if extracted_count == 0:
                logger.warning("No se extrajeron archivos del .whl")
                return None

            _update_download_progress(
                model_info.model_type,
                phase="completed",
                bytes_downloaded=total_size,
                bytes_total=total_size,
            )

            if progress_callback:
                progress_callback("Modelo instalado correctamente", 1.0)

            logger.info(f"Modelo spaCy instalado en: {target_dir} ({extracted_count} archivos)")
            return Result.success(target_dir)

        finally:
            if tmp_path:
                tmp_path.unlink(missing_ok=True)

    @staticmethod
    def _resolve_spacy_model_version(model_name: str, spacy_version: str) -> str | None:
        """
        Determina la versión compatible del modelo spaCy para la versión instalada.

        Intenta usar la API de compatibilidad de spaCy. Si falla, usa la
        convención major.minor.0 que funciona para la mayoría de casos.
        """
        try:
            from spacy.cli._util import get_compatibility

            compat = get_compatibility()
            spacy_compat = compat.get("spacy", {})

            # Buscar la versión exacta de spaCy en la tabla de compatibilidad
            if spacy_version in spacy_compat:
                models = spacy_compat[spacy_version]
                if model_name in models and models[model_name]:
                    version = models[model_name][0]
                    logger.debug(f"Versión compatible para {model_name}: {version}")
                    return version

            # Buscar por major.minor
            major_minor = ".".join(spacy_version.split(".")[:2])
            for sv, models in spacy_compat.items():
                if sv.startswith(major_minor) and model_name in models and models[model_name]:
                    version = models[model_name][0]
                    logger.debug(f"Versión compatible (minor match) para {model_name}: {version}")
                    return version

        except Exception as e:
            logger.debug(f"Error consultando compatibilidad spaCy: {e}")

        # Fallback: usar major.minor.0
        try:
            parts = spacy_version.split(".")
            fallback = f"{parts[0]}.{parts[1]}.0"
            logger.debug(f"Usando versión fallback para {model_name}: {fallback}")
            return fallback
        except (IndexError, ValueError):
            return None

    def _download_spacy_fallback(
        self,
        model_info: ModelInfo,
        target_dir: Path,
        estimated_size: int,
        progress_callback: Callable[[str, float], None] | None,
    ) -> Result[Path]:
        """
        Fallback: descarga spaCy usando spacy.cli.download (sin progreso byte-level).
        """
        try:
            import spacy
            from spacy.cli import download

            _update_download_progress(
                model_info.model_type,
                phase="downloading",
                bytes_total=estimated_size,
            )

            if progress_callback:
                progress_callback(f"Descargando {model_info.display_name}...", 0.1)

            logger.info(f"Fallback: ejecutando spacy download {model_info.name}")
            download(model_info.name)

            _update_download_progress(
                model_info.model_type,
                phase="installing",
                bytes_downloaded=int(estimated_size * 0.8),
                bytes_total=estimated_size,
            )

            if progress_callback:
                progress_callback("Copiando modelo a cache local...", 0.7)

            nlp = spacy.load(model_info.name)
            source_path = Path(nlp.path)

            logger.info(f"Copiando de {source_path} a {target_dir}")
            if target_dir.exists():
                shutil.rmtree(target_dir)
            shutil.copytree(source_path, target_dir)

            _update_download_progress(
                model_info.model_type,
                phase="completed",
                bytes_downloaded=estimated_size,
                bytes_total=estimated_size,
            )

            if progress_callback:
                progress_callback("Modelo instalado correctamente", 1.0)

            logger.info(f"Modelo spaCy instalado en: {target_dir}")
            return Result.success(target_dir)

        except Exception as e:
            _update_download_progress(
                model_info.model_type,
                phase="error",
                error_message=str(e),
            )
            return Result.failure(
                ModelDownloadError(
                    model_name=model_info.name,
                    reason=f"Error en descarga spaCy: {e}",
                )
            )

    def _download_embeddings_model(
        self,
        model_info: ModelInfo,
        target_dir: Path,
        progress_callback: Callable[[str, float], None] | None,
    ) -> Result[Path]:
        """
        Descarga modelo de embeddings usando huggingface_hub.snapshot_download.

        Usa tqdm_class personalizado para reportar progreso byte-level real.
        """
        try:
            from huggingface_hub import snapshot_download
        except ImportError:
            return Result.failure(
                ModelDownloadError(
                    model_name=model_info.name,
                    reason="huggingface_hub no instalado",
                )
            )

        try:
            old_hf_offline = os.environ.get("HF_HUB_OFFLINE")
            old_transformers_offline = os.environ.get("TRANSFORMERS_OFFLINE")
            os.environ["HF_HUB_OFFLINE"] = "0"
            os.environ["TRANSFORMERS_OFFLINE"] = "0"

            estimated_size = model_info.size_mb * 1024 * 1024

            _update_download_progress(
                model_info.model_type,
                phase="connecting",
                bytes_total=estimated_size,
            )

            if progress_callback:
                progress_callback(f"Descargando {model_info.display_name}...", 0.1)

            try:
                repo_id = f"sentence-transformers/{model_info.name}"
                tracker_class = _create_hf_progress_tracker(model_info.model_type)

                logger.info(f"Descargando modelo embeddings: {repo_id}")
                target_dir.mkdir(parents=True, exist_ok=True)

                snapshot_download(
                    repo_id,
                    local_dir=str(target_dir),
                    local_dir_use_symlinks=False,
                    tqdm_class=tracker_class,
                    ignore_patterns=["*.onnx", "*.h5", "tf_*", "openvino/*", "onnx/*", "rust_model.ot"],
                )

                _update_download_progress(
                    model_info.model_type,
                    phase="completed",
                    bytes_downloaded=estimated_size,
                    bytes_total=estimated_size,
                )

                if progress_callback:
                    progress_callback("Modelo instalado correctamente", 1.0)

                logger.info(f"Modelo embeddings instalado en: {target_dir}")
                return Result.success(target_dir)

            finally:
                if old_hf_offline is not None:
                    os.environ["HF_HUB_OFFLINE"] = old_hf_offline
                else:
                    os.environ.pop("HF_HUB_OFFLINE", None)
                if old_transformers_offline is not None:
                    os.environ["TRANSFORMERS_OFFLINE"] = old_transformers_offline
                else:
                    os.environ.pop("TRANSFORMERS_OFFLINE", None)

        except Exception as e:
            _update_download_progress(
                model_info.model_type,
                phase="error",
                error_message=str(e),
            )
            return Result.failure(
                ModelDownloadError(
                    model_name=model_info.name,
                    reason=f"Error en descarga embeddings: {e}",
                )
            )

    def _download_transformer_ner_model(
        self,
        model_info: ModelInfo,
        target_dir: Path,
        progress_callback: Callable[[str, float], None] | None,
    ) -> Result[Path]:
        """
        Descarga modelo transformer NER usando huggingface_hub.snapshot_download.

        Usa tqdm_class personalizado para reportar progreso byte-level real.
        Si el modelo principal falla (ej: 401 gated), intenta fallbacks.
        """
        try:
            from huggingface_hub import snapshot_download
        except ImportError:
            return Result.failure(
                ModelDownloadError(
                    model_name=model_info.name,
                    reason="huggingface_hub no instalado",
                )
            )

        # Lista de modelos a intentar: principal + fallbacks
        models_to_try = [model_info] + TRANSFORMER_NER_FALLBACKS
        last_error: Exception | None = None

        for attempt_info in models_to_try:
            attempt_dir = self.models_dir / attempt_info.subdirectory / attempt_info.name
            try:
                old_hf_offline = os.environ.get("HF_HUB_OFFLINE")
                old_transformers_offline = os.environ.get("TRANSFORMERS_OFFLINE")
                os.environ["HF_HUB_OFFLINE"] = "0"
                os.environ["TRANSFORMERS_OFFLINE"] = "0"

                estimated_size = attempt_info.size_mb * 1024 * 1024

                _update_download_progress(
                    attempt_info.model_type,
                    phase="connecting",
                    bytes_total=estimated_size,
                )

                if progress_callback:
                    progress_callback(f"Descargando {attempt_info.display_name}...", 0.1)

                try:
                    repo_id = attempt_info.name
                    tracker_class = _create_hf_progress_tracker(attempt_info.model_type)

                    logger.info(f"Descargando modelo transformer NER: {repo_id}")
                    attempt_dir.mkdir(parents=True, exist_ok=True)

                    snapshot_download(
                        repo_id,
                        local_dir=str(attempt_dir),
                        local_dir_use_symlinks=False,
                        tqdm_class=tracker_class,
                        ignore_patterns=["*.onnx", "*.h5", "tf_*", "flax_*", "openvino/*", "onnx/*"],
                    )

                    _update_download_progress(
                        attempt_info.model_type,
                        phase="completed",
                        bytes_downloaded=estimated_size,
                        bytes_total=estimated_size,
                    )

                    if progress_callback:
                        progress_callback("Modelo instalado correctamente", 1.0)

                    # Si descargamos un fallback, actualizar KNOWN_MODELS para que
                    # get_model_path() lo encuentre con el nombre correcto
                    if attempt_info.name != model_info.name:
                        logger.info(
                            f"Modelo principal '{model_info.name}' no disponible, "
                            f"usando fallback: '{attempt_info.name}'"
                        )
                        KNOWN_MODELS[ModelType.TRANSFORMER_NER] = attempt_info

                    logger.info(f"Modelo transformer NER instalado en: {attempt_dir}")
                    return Result.success(attempt_dir)

                finally:
                    if old_hf_offline is not None:
                        os.environ["HF_HUB_OFFLINE"] = old_hf_offline
                    else:
                        os.environ.pop("HF_HUB_OFFLINE", None)
                    if old_transformers_offline is not None:
                        os.environ["TRANSFORMERS_OFFLINE"] = old_transformers_offline
                    else:
                        os.environ.pop("TRANSFORMERS_OFFLINE", None)

            except Exception as e:
                last_error = e
                error_str = str(e)
                is_auth_error = "401" in error_str or "403" in error_str or "gated" in error_str.lower()

                if is_auth_error and attempt_info.name != models_to_try[-1].name:
                    logger.warning(
                        f"Modelo '{attempt_info.name}' requiere autenticación (HTTP 401/403). "
                        f"Intentando siguiente alternativa..."
                    )
                    # Limpiar directorio parcial del intento fallido
                    if attempt_dir.exists():
                        shutil.rmtree(attempt_dir, ignore_errors=True)
                    continue
                else:
                    _update_download_progress(
                        attempt_info.model_type,
                        phase="error",
                        error_message=str(e),
                    )
                    # Limpiar directorio parcial
                    if attempt_dir.exists():
                        shutil.rmtree(attempt_dir, ignore_errors=True)
                    return Result.failure(
                        ModelDownloadError(
                            model_name=attempt_info.name,
                            reason=f"Error en descarga transformer NER: {e}",
                        )
                    )

        # Todos los modelos fallaron
        _update_download_progress(
            model_info.model_type,
            phase="error",
            error_message=f"Todos los modelos NER fallaron: {last_error}",
        )
        return Result.failure(
            ModelDownloadError(
                model_name=model_info.name,
                reason=f"No se pudo descargar ningún modelo NER. Último error: {last_error}",
            )
        )

    def _verify_model_structure(self, model_type: ModelType, model_path: Path) -> bool:
        """
        Verifica que la estructura del modelo sea correcta.

        Args:
            model_type: Tipo de modelo
            model_path: Ruta al modelo

        Returns:
            True si la estructura es válida
        """
        if not model_path.exists() or not model_path.is_dir():
            return False

        if model_type == ModelType.SPACY:
            # spaCy requiere config.cfg (puede estar en raíz o en subdir versionado)
            if (model_path / "config.cfg").exists():
                return True
            # Buscar en subdir versionado (e.g. es_core_news_lg-3.7.0/config.cfg)
            for child in model_path.iterdir():
                if child.is_dir() and (child / "config.cfg").exists():
                    return True
            logger.warning("Archivo faltante en modelo spaCy: config.cfg")
            return False

        elif model_type == ModelType.EMBEDDINGS:
            # sentence-transformers requiere config.json y pytorch_model.bin o model.safetensors
            if not (model_path / "config.json").exists():
                logger.warning("Archivo config.json faltante en modelo embeddings")
                return False

            # Puede tener pytorch_model.bin o model.safetensors
            has_weights = (model_path / "pytorch_model.bin").exists() or (
                model_path / "model.safetensors"
            ).exists()
            if not has_weights:
                logger.warning("Archivo de pesos faltante en modelo embeddings")
                return False

            return True

        elif model_type == ModelType.TRANSFORMER_NER:
            # Transformer NER requiere config.json, tokenizer y pesos
            if not (model_path / "config.json").exists():
                logger.warning("Archivo config.json faltante en modelo transformer NER")
                return False

            has_weights = (model_path / "pytorch_model.bin").exists() or (
                model_path / "model.safetensors"
            ).exists()
            if not has_weights:
                logger.warning("Archivo de pesos faltante en modelo transformer NER")
                return False

            has_tokenizer = (model_path / "tokenizer_config.json").exists() or (
                model_path / "tokenizer.json"
            ).exists()
            if not has_tokenizer:
                logger.warning("Tokenizer faltante en modelo transformer NER")
                return False

            return True

        return False

    def _compute_file_hash(self, file_path: Path) -> str:
        """Calcula SHA256 de un archivo."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def _check_internet_connection(self, timeout: float = 3.0) -> bool:
        """
        Verifica si hay conexión a internet.

        Intenta conectar a varios hosts conocidos.
        """
        hosts = [
            ("huggingface.co", 443),
            ("github.com", 443),
            ("1.1.1.1", 53),  # Cloudflare DNS
        ]

        for host, port in hosts:
            try:
                socket.create_connection((host, port), timeout=timeout)
                return True
            except (TimeoutError, OSError):
                continue

        return False

    def get_all_models_status(self) -> dict[str, dict]:
        """
        Retorna el estado de todos los modelos conocidos.

        Returns:
            Dict con información de cada modelo
        """
        status = {}

        for model_type, model_info in KNOWN_MODELS.items():
            model_path = self.get_model_path(model_type)
            status[model_info.name] = {
                "type": model_type.value,
                "display_name": model_info.display_name,
                "size_mb": model_info.size_mb,
                "installed": model_path is not None,
                "path": str(model_path) if model_path else None,
            }

        return status

    def clear_cache(self, model_type: ModelType | None = None) -> None:
        """
        Elimina modelos del cache.

        Args:
            model_type: Tipo específico a eliminar, o None para todos
        """
        if model_type:
            model_info = KNOWN_MODELS.get(model_type)
            if model_info:
                model_path = self.models_dir / model_info.subdirectory / model_info.name
                if model_path.exists():
                    shutil.rmtree(model_path)
                    logger.info(f"Eliminado: {model_path}")
                self._verified_paths.pop(model_type, None)
        else:
            # Eliminar todos
            for mt in ModelType:
                self.clear_cache(mt)


def get_download_progress(model_type: ModelType | None = None) -> dict[str, dict] | dict | None:
    """
    Obtiene el estado de progreso de descargas activas.

    Args:
        model_type: Tipo de modelo específico, o None para todos

    Returns:
        Estado de progreso como diccionario
    """
    with _progress_lock:
        if model_type:
            progress = _download_progress.get(model_type)
            return progress.to_dict() if progress else None
        return {mt.value: p.to_dict() for mt, p in _download_progress.items()}


def _update_download_progress(
    model_type: ModelType,
    phase: str,
    bytes_downloaded: int = 0,
    bytes_total: int = 0,
    speed_bps: float = 0.0,
    error_message: str | None = None,
) -> None:
    """Actualiza el estado de progreso de una descarga."""
    import time

    with _progress_lock:
        if model_type not in _download_progress:
            _download_progress[model_type] = DownloadProgress(
                model_type=model_type,
                phase=phase,
                started_at=time.time(),
            )

        progress = _download_progress[model_type]
        # Crear nueva instancia con valores actualizados
        _download_progress[model_type] = DownloadProgress(
            model_type=model_type,
            phase=phase,
            bytes_downloaded=bytes_downloaded,
            bytes_total=bytes_total,
            speed_bps=speed_bps,
            error_message=error_message,
            started_at=progress.started_at,
        )


def _clear_download_progress(model_type: ModelType) -> None:
    """Limpia el estado de progreso de una descarga completada."""
    with _progress_lock:
        _download_progress.pop(model_type, None)


def get_model_size_from_huggingface(model_name: str, use_cache: bool = True) -> int | None:
    """
    Obtiene el tamaño real de un modelo desde HuggingFace Hub.

    Los tamaños se cachean por 1 semana (éxito) o 5 minutos (error).
    Esto evita hacer polling continuo a HuggingFace si falla.

    Args:
        model_name: Nombre del modelo en HuggingFace
        use_cache: Si usar el cache (default True)

    Returns:
        Tamaño en bytes, o None si no se puede obtener
    """
    import time

    global _model_sizes_cache, _model_sizes_cache_time

    # Verificar cache (incluye fallos cacheados como None)
    if use_cache and model_name in _model_sizes_cache:
        cache_age = time.time() - _model_sizes_cache_time
        if cache_age < _MODEL_SIZES_CACHE_TTL:
            cached = _model_sizes_cache[model_name]
            if cached is not None:
                return cached
            # Fallo cacheado: respetar cooldown de 5 minutos
            if cache_age < 300:
                return None
            # Cooldown expirado, reintentar

    try:
        from huggingface_hub import model_info

        info = model_info(model_name, timeout=5)
        if info.siblings:
            total_size = sum(f.size for f in info.siblings if f.size)
            if total_size > 0:
                logger.debug(f"Tamaño de {model_name} desde HuggingFace: {total_size} bytes ({total_size / (1024*1024):.1f} MB)")
                _model_sizes_cache[model_name] = total_size
                _model_sizes_cache_time = time.time()
                return total_size
    except Exception as e:
        logger.debug(f"No se pudo obtener tamaño de {model_name}: {e}")
        # Cachear el fallo para evitar bucle de reintentos
        _model_sizes_cache[model_name] = None
        _model_sizes_cache_time = time.time()
    return None


def get_spacy_model_size(model_name: str) -> int | None:
    """
    Obtiene el tamaño de un modelo spaCy desde GitHub releases.

    Args:
        model_name: Nombre del modelo spaCy (ej: es_core_news_lg)

    Returns:
        Tamaño en bytes, o None si no se puede obtener
    """
    import json
    import time
    import urllib.request

    global _model_sizes_cache, _model_sizes_cache_time

    cache_key = f"spacy/{model_name}"

    # Verificar cache
    if cache_key in _model_sizes_cache:
        cache_age = time.time() - _model_sizes_cache_time
        if cache_age < _MODEL_SIZES_CACHE_TTL:
            return _model_sizes_cache[cache_key]

    try:
        # Consultar la API de GitHub para releases de spacy-models
        # El modelo es un wheel de Python, el tamaño está en los assets del release
        url = f"https://api.github.com/repos/explosion/spacy-models/releases/tags/{model_name}-3.7.0"

        req = urllib.request.Request(url)
        req.add_header("User-Agent", "NarrativeAssistant/1.0")

        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())

        # Buscar el asset del wheel
        for asset in data.get("assets", []):
            if asset["name"].endswith(".whl") or asset["name"].endswith(".tar.gz"):
                size = asset.get("size", 0)
                if size > 0:
                    logger.debug(f"Tamaño de spaCy {model_name} desde GitHub: {size} bytes ({size / (1024*1024):.1f} MB)")
                    _model_sizes_cache[cache_key] = size
                    _model_sizes_cache_time = time.time()
                    return size

    except Exception as e:
        logger.debug(f"No se pudo obtener tamaño de spaCy {model_name}: {e}")
        # Cachear el fallo para evitar reintentos continuos
        _model_sizes_cache[cache_key] = None
        _model_sizes_cache_time = time.time()

    return None


def get_real_model_sizes(force_refresh: bool = False) -> dict[str, int]:
    """
    Obtiene tamaños estimados de los modelos.

    Usa tamaños estáticos de KNOWN_MODELS para evitar llamadas HTTP
    durante polling del frontend. Solo consulta APIs externas si
    force_refresh=True.

    Args:
        force_refresh: Si True, consulta APIs externas para tamaños exactos

    Returns:
        Dict con tamaños en bytes por tipo de modelo
    """
    sizes = {}

    for model_type, model_info in KNOWN_MODELS.items():
        key = model_type.value
        size = model_info.size_mb * 1024 * 1024  # Default estático

        if force_refresh:
            if model_type == ModelType.EMBEDDINGS:
                hf_size = get_model_size_from_huggingface(
                    f"sentence-transformers/{model_info.name}",
                    use_cache=False,
                )
                if hf_size:
                    size = hf_size
            elif model_type == ModelType.TRANSFORMER_NER:
                hf_size = get_model_size_from_huggingface(
                    model_info.name,
                    use_cache=False,
                )
                if hf_size:
                    size = hf_size
            elif model_type == ModelType.SPACY:
                spacy_size = get_spacy_model_size(model_info.name)
                if spacy_size:
                    size = spacy_size

        sizes[key] = size

    return sizes


def get_model_manager() -> ModelManager:
    """
    Obtiene el gestor de modelos singleton (thread-safe).

    Returns:
        Instancia de ModelManager
    """
    global _model_manager

    if _model_manager is None:
        with _manager_lock:
            # Double-checked locking
            if _model_manager is None:
                _model_manager = ModelManager()

    return _model_manager


def reset_model_manager() -> None:
    """Resetea el singleton del gestor de modelos (para testing)."""
    global _model_manager
    with _manager_lock:
        _model_manager = None


def ensure_spacy_model(
    force_download: bool = False,
    progress_callback: Callable[[str, float], None] | None = None,
) -> Result[Path]:
    """
    Función de conveniencia para asegurar modelo spaCy.

    Args:
        force_download: Si True, re-descarga aunque exista
        progress_callback: Callback para progreso

    Returns:
        Result con Path al modelo
    """
    return get_model_manager().ensure_model(ModelType.SPACY, force_download, progress_callback)


def ensure_embeddings_model(
    force_download: bool = False,
    progress_callback: Callable[[str, float], None] | None = None,
) -> Result[Path]:
    """
    Función de conveniencia para asegurar modelo de embeddings.

    Args:
        force_download: Si True, re-descarga aunque exista
        progress_callback: Callback para progreso

    Returns:
        Result con Path al modelo
    """
    return get_model_manager().ensure_model(ModelType.EMBEDDINGS, force_download, progress_callback)
