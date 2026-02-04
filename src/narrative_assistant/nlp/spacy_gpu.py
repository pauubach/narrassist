"""
Configuración de GPU para spaCy.

spaCy soporta GPU a través de:
- cupy (CUDA) en Linux/Windows
- thinc-apple-ops (MPS) en macOS Apple Silicon

IMPORTANTE: El beneficio de GPU en spaCy es MODERADO (~1.5-2x) porque:
- Los modelos transformer (trf) se benefician más que los CNN (lg)
- es_core_news_lg es CNN, no transformer
- Para beneficio real usar: es_dep_news_trf (si disponible)

Los modelos se descargan bajo demanda la primera vez que se necesitan
y se guardan en ~/.narrative_assistant/models/ para uso offline posterior.
"""

import logging
import threading
from collections.abc import Callable

from ..core.config import get_config
from ..core.device import DeviceType, get_device_detector
from ..core.errors import ModelNotLoadedError
from ..core.model_manager import ModelType, ensure_spacy_model, get_model_manager

logger = logging.getLogger(__name__)

# Lock para thread-safety en flags globales
_spacy_gpu_lock = threading.Lock()

# Flag global para evitar reconfiguración
_gpu_configured: bool = False
_gpu_active: bool = False


def setup_spacy_gpu() -> bool:
    """
    Configura spaCy para usar GPU si está disponible (thread-safe).

    Returns:
        True si GPU está activa, False si usa CPU
    """
    global _gpu_configured, _gpu_active

    if _gpu_configured:
        return _gpu_active

    with _spacy_gpu_lock:
        # Double-checked locking
        if _gpu_configured:
            return _gpu_active

        import spacy

        config = get_config()
        detector = get_device_detector()

        if not config.gpu.spacy_gpu_enabled:
            logger.info("spaCy GPU deshabilitado por configuración")
            spacy.require_cpu()
            _gpu_configured = True
            _gpu_active = False
            return False

        device = detector.detect_best_device(config.gpu.device_preference)

        # CUDA: Usar cupy
        if device.device_type == DeviceType.CUDA:
            try:
                import cupy

                # Configurar límite de memoria si especificado
                if config.gpu.spacy_gpu_memory_limit:
                    mempool = cupy.get_default_memory_pool()
                    limit_bytes = config.gpu.spacy_gpu_memory_limit * 1024 * 1024
                    mempool.set_limit(size=limit_bytes)
                    logger.info(
                        f"Límite de memoria GPU spaCy: {config.gpu.spacy_gpu_memory_limit} MB"
                    )

                # Activar GPU en spaCy
                spacy.require_gpu(device.device_id)
                logger.info(f"spaCy usando CUDA GPU: {device.device_name}")
                _gpu_configured = True
                _gpu_active = True
                return True

            except ImportError:
                logger.warning(
                    "CuPy no instalado. spaCy usará CPU. Para GPU instale: pip install cupy-cuda12x"
                )
            except Exception as e:
                logger.warning(f"Error configurando CUDA para spaCy: {e}")

        # MPS: Apple Silicon
        elif device.device_type == DeviceType.MPS:
            try:
                # spaCy 3.5+ soporta MPS via thinc
                # Nota: El soporte MPS en spaCy es limitado
                spacy.require_gpu()
                logger.info("spaCy intentando usar Apple MPS")
                _gpu_configured = True
                _gpu_active = True
                return True
            except Exception as e:
                logger.warning(f"Error configurando MPS para spaCy: {e}")

        # CPU fallback
        spacy.require_cpu()
        logger.info("spaCy usando CPU")
        _gpu_configured = True
        _gpu_active = False
        return False


def load_spacy_model(
    model_name: str | None = None,
    enable_gpu: bool | None = None,
    disable_components: list[str] | None = None,
    auto_download: bool = True,
    progress_callback: Callable[[str, float], None] | None = None,
):
    """
    Carga modelo spaCy con configuración de GPU.

    El modelo se descarga automáticamente la primera vez que se necesita
    y se guarda en ~/.narrative_assistant/models/ para uso offline posterior.

    Args:
        model_name: Nombre del modelo (default: config)
        enable_gpu: Forzar GPU (None = auto desde config)
        disable_components: Componentes a deshabilitar para mejor rendimiento
        auto_download: Si True, descarga el modelo si no existe (default: True)
        progress_callback: Función para reportar progreso de descarga (mensaje, porcentaje)

    Returns:
        Modelo spaCy cargado

    Raises:
        ModelNotLoadedError: Si el modelo no está disponible y no se puede descargar
    """
    import spacy

    config = get_config()
    model_name = model_name or config.nlp.spacy_model

    # Configurar GPU antes de cargar
    if enable_gpu is None:
        enable_gpu = config.gpu.spacy_gpu_enabled

    if enable_gpu:
        setup_spacy_gpu()
    else:
        spacy.require_cpu()

    # Buscar modelo: primero en config explícita, luego en ModelManager
    model_path = config.spacy_model_path

    if model_path is None:
        # Intentar obtener del ModelManager (descarga bajo demanda)
        manager = get_model_manager()
        existing_path = manager.get_model_path(ModelType.SPACY)

        if existing_path:
            model_path = existing_path
        elif auto_download:
            # Descargar modelo
            logger.info("Modelo spaCy no encontrado. Iniciando descarga...")
            result = ensure_spacy_model(force_download=False, progress_callback=progress_callback)
            if result.is_failure:
                error = result.error
                raise ModelNotLoadedError(
                    model_name=model_name,
                    hint=(
                        f"No se pudo descargar el modelo spaCy.\n"
                        f"Error: {error.message if error else 'Desconocido'}\n\n"
                        "Verifica tu conexión a internet o descarga manualmente:\n"
                        "  narrative-assistant download-models"
                    ),
                )
            model_path = result.value
        else:
            raise ModelNotLoadedError(
                model_name=model_name,
                hint=(
                    "Modelo spaCy no encontrado en local.\n"
                    "Descarga con: narrative-assistant download-models\n"
                    "O habilita auto_download=True para descarga automática."
                ),
            )

    model_to_load = str(model_path)
    logger.info(f"Cargando modelo spaCy: {model_to_load}")

    try:
        if disable_components:
            nlp = spacy.load(model_to_load, disable=disable_components)
            logger.debug(f"Componentes deshabilitados: {disable_components}")
        else:
            nlp = spacy.load(model_to_load)
    except OSError as e:
        raise ModelNotLoadedError(
            model_name=model_name,
            hint=f"Error cargando modelo: {e}",
        ) from e

    # Log información del modelo
    logger.debug(f"Pipeline activo: {nlp.pipe_names}")

    return nlp


def get_spacy_gpu_status() -> dict:
    """
    Retorna estado de GPU para spaCy.

    Returns:
        Dict con información de GPU
    """
    status = {
        "gpu_available": False,
        "gpu_active": _gpu_active,
        "backend": "cpu",
        "device_name": None,
        "cupy_version": None,
        "spacy_version": None,
    }

    try:
        import spacy

        status["spacy_version"] = spacy.__version__
    except ImportError:
        pass

    try:
        import cupy

        status["cupy_version"] = cupy.__version__
        status["gpu_available"] = True
        try:
            props = cupy.cuda.runtime.getDeviceProperties(0)
            status["device_name"] = props["name"].decode()
        except Exception:
            pass
    except ImportError:
        pass

    # Verificar si GPU está activa
    try:
        from thinc.api import get_current_ops

        ops = get_current_ops()
        ops_type = str(type(ops)).lower()
        if "cupy" in ops_type:
            status["gpu_active"] = True
            status["backend"] = "cuda"
        elif "mps" in ops_type or "metal" in ops_type:
            status["gpu_active"] = True
            status["backend"] = "mps"
    except Exception:
        pass

    return status


def reset_gpu_config():
    """Resetea la configuración de GPU (thread-safe, para testing)."""
    global _gpu_configured, _gpu_active
    with _spacy_gpu_lock:
        _gpu_configured = False
        _gpu_active = False
