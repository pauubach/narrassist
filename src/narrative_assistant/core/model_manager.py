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
import json
import logging
import os
import shutil
import socket
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

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


@dataclass(frozen=True)
class ModelInfo:
    """Información de un modelo para descarga y verificación."""

    model_type: ModelType
    name: str
    display_name: str
    size_mb: int
    sha256: Optional[str]  # None si no se conoce el hash
    source_url: str  # URL informativo (no se usa directamente)
    subdirectory: str  # Subdirectorio dentro de models/


# Definición de modelos conocidos con sus hashes
# NOTA: Los hashes pueden variar entre versiones. Si falla verificación,
# actualizar o establecer a None para omitir verificación.
KNOWN_MODELS: dict[ModelType, ModelInfo] = {
    ModelType.SPACY: ModelInfo(
        model_type=ModelType.SPACY,
        name="es_core_news_lg",
        display_name="spaCy Español (es_core_news_lg)",
        size_mb=500,
        # El hash se calcula sobre el archivo meta.json del modelo
        sha256=None,  # spaCy no provee hashes oficiales
        source_url="https://github.com/explosion/spacy-models",
        subdirectory="spacy",
    ),
    ModelType.EMBEDDINGS: ModelInfo(
        model_type=ModelType.EMBEDDINGS,
        name="paraphrase-multilingual-MiniLM-L12-v2",
        display_name="Sentence Transformers Multilingüe",
        size_mb=500,
        # Hash del archivo config.json del modelo (identificador estable)
        sha256=None,  # Se verificará estructura en lugar de hash
        source_url="https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        subdirectory="embeddings",
    ),
}


@dataclass
class ModelDownloadError(NarrativeError):
    """Error al descargar un modelo."""

    model_name: str = ""
    reason: str = ""
    message: str = ""
    severity: ErrorSeverity = ErrorSeverity.FATAL
    user_message: Optional[str] = None

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
    user_message: Optional[str] = None

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

    def __init__(self, models_dir: Optional[Path] = None):
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

    def _find_bundled_models_dir(self) -> Optional[Path]:
        """
        Busca el directorio de modelos bundled con la app.

        Tauri coloca recursos en diferentes ubicaciones según el OS:
        - Windows: {app_dir}/resources/
        - macOS: {app_bundle}/Contents/Resources/
        - Linux: /usr/share/{app}/resources/ o junto al ejecutable
        """
        import sys

        # Obtener directorio del ejecutable
        if getattr(sys, 'frozen', False):
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

    def get_model_path(self, model_type: ModelType) -> Optional[Path]:
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
            self._verified_paths[model_type] = model_path
            return model_path

        logger.warning(f"Modelo en {model_path} tiene estructura inválida")
        return None

    def ensure_model(
        self,
        model_type: ModelType,
        force_download: bool = False,
        progress_callback: Optional[Callable[[str, float], None]] = None,
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
            download_result = self._download_model(
                model_info, force_download, progress_callback
            )

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
        progress_callback: Optional[Callable[[str, float], None]],
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
            return Result.failure(
                ModelDownloadError(model_name=model_info.name, reason=str(e))
            )

    def _download_spacy_model(
        self,
        model_info: ModelInfo,
        target_dir: Path,
        progress_callback: Optional[Callable[[str, float], None]],
    ) -> Result[Path]:
        """
        Descarga modelo spaCy usando la CLI de spaCy.

        spaCy descarga a su cache y luego copiamos al directorio de modelos.
        """
        try:
            import spacy
            from spacy.cli import download

            if progress_callback:
                progress_callback(f"Descargando {model_info.display_name}...", 0.1)

            # Descargar modelo usando spaCy CLI
            logger.info(f"Ejecutando spacy download {model_info.name}")
            download(model_info.name)

            if progress_callback:
                progress_callback("Copiando modelo a cache local...", 0.7)

            # Cargar para obtener la ruta de instalación
            nlp = spacy.load(model_info.name)
            source_path = Path(nlp.path)

            # Copiar al directorio de modelos
            logger.info(f"Copiando de {source_path} a {target_dir}")
            shutil.copytree(source_path, target_dir)

            if progress_callback:
                progress_callback("Modelo instalado correctamente", 1.0)

            logger.info(f"Modelo spaCy instalado en: {target_dir}")
            return Result.success(target_dir)

        except Exception as e:
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
        progress_callback: Optional[Callable[[str, float], None]],
    ) -> Result[Path]:
        """
        Descarga modelo de embeddings usando sentence-transformers.

        sentence-transformers descarga de HuggingFace Hub.
        """
        try:
            # Temporalmente deshabilitar modo offline para descarga
            old_hf_offline = os.environ.get("HF_HUB_OFFLINE")
            old_transformers_offline = os.environ.get("TRANSFORMERS_OFFLINE")

            os.environ["HF_HUB_OFFLINE"] = "0"
            os.environ["TRANSFORMERS_OFFLINE"] = "0"

            try:
                from sentence_transformers import SentenceTransformer

                if progress_callback:
                    progress_callback(f"Descargando {model_info.display_name}...", 0.1)

                # Descargar modelo
                logger.info(f"Descargando modelo: {model_info.name}")
                model = SentenceTransformer(model_info.name)

                if progress_callback:
                    progress_callback("Guardando modelo en cache local...", 0.8)

                # Guardar en directorio local
                model.save(str(target_dir))

                if progress_callback:
                    progress_callback("Modelo instalado correctamente", 1.0)

                logger.info(f"Modelo embeddings instalado en: {target_dir}")
                return Result.success(target_dir)

            finally:
                # Restaurar variables de entorno
                if old_hf_offline is not None:
                    os.environ["HF_HUB_OFFLINE"] = old_hf_offline
                else:
                    os.environ.pop("HF_HUB_OFFLINE", None)

                if old_transformers_offline is not None:
                    os.environ["TRANSFORMERS_OFFLINE"] = old_transformers_offline
                else:
                    os.environ.pop("TRANSFORMERS_OFFLINE", None)

        except Exception as e:
            return Result.failure(
                ModelDownloadError(
                    model_name=model_info.name,
                    reason=f"Error en descarga embeddings: {e}",
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
            # spaCy requiere meta.json y config.cfg
            required_files = ["meta.json", "config.cfg"]
            for f in required_files:
                if not (model_path / f).exists():
                    logger.warning(f"Archivo faltante en modelo spaCy: {f}")
                    return False
            return True

        elif model_type == ModelType.EMBEDDINGS:
            # sentence-transformers requiere config.json y pytorch_model.bin o model.safetensors
            if not (model_path / "config.json").exists():
                logger.warning("Archivo config.json faltante en modelo embeddings")
                return False

            # Puede tener pytorch_model.bin o model.safetensors
            has_weights = (
                (model_path / "pytorch_model.bin").exists()
                or (model_path / "model.safetensors").exists()
            )
            if not has_weights:
                logger.warning("Archivo de pesos faltante en modelo embeddings")
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
            except (socket.timeout, socket.error):
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

    def clear_cache(self, model_type: Optional[ModelType] = None) -> None:
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
    progress_callback: Optional[Callable[[str, float], None]] = None,
) -> Result[Path]:
    """
    Función de conveniencia para asegurar modelo spaCy.

    Args:
        force_download: Si True, re-descarga aunque exista
        progress_callback: Callback para progreso

    Returns:
        Result con Path al modelo
    """
    return get_model_manager().ensure_model(
        ModelType.SPACY, force_download, progress_callback
    )


def ensure_embeddings_model(
    force_download: bool = False,
    progress_callback: Optional[Callable[[str, float], None]] = None,
) -> Result[Path]:
    """
    Función de conveniencia para asegurar modelo de embeddings.

    Args:
        force_download: Si True, re-descarga aunque exista
        progress_callback: Callback para progreso

    Returns:
        Result con Path al modelo
    """
    return get_model_manager().ensure_model(
        ModelType.EMBEDDINGS, force_download, progress_callback
    )
