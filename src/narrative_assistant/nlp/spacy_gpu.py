"""
Configuración de GPU para spaCy.

spaCy soporta GPU a través de:
- cupy (CUDA) en Linux/Windows
- thinc-apple-ops (MPS) en macOS Apple Silicon

IMPORTANTE: El beneficio de GPU en spaCy es MODERADO (~1.5-2x) porque:
- Los modelos transformer (trf) se benefician más que los CNN (lg)
- es_core_news_lg es CNN, no transformer
- Para beneficio real usar: es_dep_news_trf (si disponible)

SEGURIDAD: Los modelos DEBEN estar en local. No se permite descarga automática
para garantizar que los manuscritos nunca salen de la máquina del usuario.
"""

import logging
import threading
from typing import Optional

from ..core.config import get_config
from ..core.device import get_device_detector, DeviceType
from ..core.errors import ModelNotLoadedError

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
                    "CuPy no instalado. spaCy usará CPU. "
                    "Para GPU instale: pip install cupy-cuda12x"
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
    model_name: Optional[str] = None,
    enable_gpu: Optional[bool] = None,
    disable_components: Optional[list[str]] = None,
):
    """
    Carga modelo spaCy con configuración de GPU.

    Args:
        model_name: Nombre del modelo (default: config)
        enable_gpu: Forzar GPU (None = auto desde config)
        disable_components: Componentes a deshabilitar para mejor rendimiento

    Returns:
        Modelo spaCy cargado

    Raises:
        ModelNotLoadedError: Si el modelo no está disponible
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

    # SEGURIDAD: Usar SOLO modelo local
    # No permitir descarga automática para proteger manuscritos
    model_path = config.spacy_model_path

    if model_path is None:
        raise ModelNotLoadedError(
            model_name=model_name,
            hint=(
                "Modelo spaCy no encontrado en local. "
                "Ejecuta: python scripts/download_models.py\n"
                "SEGURIDAD: No se permite descarga automática para "
                "proteger los manuscritos del usuario."
            ),
        )

    model_to_load = str(model_path)
    logger.info(f"Cargando modelo spaCy local: {model_to_load}")

    try:
        if disable_components:
            nlp = spacy.load(model_to_load, disable=disable_components)
            logger.debug(f"Componentes deshabilitados: {disable_components}")
        else:
            nlp = spacy.load(model_to_load)
    except OSError as e:
        raise ModelNotLoadedError(
            model_name=model_name,
            hint=f"Error cargando modelo local: {e}",
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
