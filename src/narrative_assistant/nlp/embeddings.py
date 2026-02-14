"""
Embeddings semánticos con soporte GPU.

sentence-transformers usa PyTorch, que soporta:
- CUDA (NVIDIA)
- MPS (Apple Silicon)
- CPU

El modelo por defecto es multilingüe y funciona bien para español.

Los modelos se descargan bajo demanda la primera vez que se necesitan
y se guardan en ~/.narrative_assistant/models/ para uso offline posterior.
"""

import logging
import threading
from collections.abc import Callable
from typing import Optional

import numpy as np

from ..core.config import get_config
from ..core.device import get_device_detector, get_torch_device_string
from ..core.errors import ModelNotLoadedError
from ..core.model_manager import ModelType, ensure_embeddings_model, get_model_manager

logger = logging.getLogger(__name__)

# Lock para thread-safety en singleton
_embeddings_lock = threading.Lock()

# Singleton para el modelo
_embeddings_model: Optional["EmbeddingsModel"] = None


class EmbeddingsModel:
    """
    Modelo de embeddings con soporte GPU automático.

    El modelo se descarga automáticamente la primera vez que se necesita
    y se guarda en ~/.narrative_assistant/models/ para uso offline posterior.

    Uso:
        model = EmbeddingsModel()
        embeddings = model.encode(["texto 1", "texto 2"])
        similarity = model.similarity("texto a", "texto b")
    """

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        batch_size: int | None = None,
        auto_download: bool = True,
        progress_callback: Callable[[str, float], None] | None = None,
    ):
        """
        Inicializa modelo de embeddings.

        Args:
            model_name: Nombre del modelo HuggingFace (default: config)
            device: "cuda", "mps", "cpu", o None (auto)
            batch_size: Tamaño de batch (default: auto según device)
            auto_download: Si True, descarga el modelo si no existe (default: True)
            progress_callback: Función para reportar progreso de descarga (mensaje, porcentaje)
        """
        from sentence_transformers import SentenceTransformer

        from ..core.device import get_device_detector, get_safe_batch_size

        config = get_config()
        self.model_name = model_name or config.nlp.embeddings_model

        # Detectar dispositivo y verificar VRAM
        detector = get_device_detector()
        device_info = detector.detect_best_device(config.gpu.device_preference)

        if device is None:
            if config.gpu.embeddings_gpu_enabled:
                # En GPUs con poca VRAM, usar CPU para embeddings
                # Ollama ya usará la GPU para LLM
                if device_info.is_low_vram:
                    logger.warning(
                        f"GPU {device_info.device_name} tiene poca VRAM ({device_info.memory_gb:.1f}GB). "
                        "Usando CPU para embeddings para evitar conflictos con Ollama."
                    )
                    self.device = "cpu"
                else:
                    self.device = get_torch_device_string(config.gpu.device_preference)
            else:
                self.device = "cpu"
        else:
            self.device = device

        # Batch size seguro según dispositivo y VRAM disponible
        if batch_size is None:
            if self.device in ("cuda", "mps"):
                base_batch = config.gpu.embeddings_batch_size_gpu
                self.batch_size = get_safe_batch_size(base_batch, device_info)
            else:
                self.batch_size = config.gpu.embeddings_batch_size_cpu
        else:
            self.batch_size = batch_size

        # Buscar modelo: primero en config explícita, luego en ModelManager
        model_path = config.embeddings_model_path

        if model_path is None:
            # Intentar obtener del ModelManager (descarga bajo demanda)
            manager = get_model_manager()
            existing_path = manager.get_model_path(ModelType.EMBEDDINGS)

            if existing_path:
                model_path = existing_path
            elif auto_download:
                # Descargar modelo
                logger.info("Modelo embeddings no encontrado. Iniciando descarga...")
                result = ensure_embeddings_model(
                    force_download=False, progress_callback=progress_callback
                )
                if result.is_failure:
                    error = result.error
                    raise ModelNotLoadedError(
                        model_name=self.model_name,
                        hint=(
                            f"No se pudo descargar el modelo de embeddings.\n"
                            f"Error: {error.message if error else 'Desconocido'}\n\n"
                            "Verifica tu conexión a internet o descarga manualmente:\n"
                            "  narrative-assistant download-models"
                        ),
                    )
                model_path = result.value
            else:
                raise ModelNotLoadedError(
                    model_name=self.model_name,
                    hint=(
                        "Modelo de embeddings no encontrado en local.\n"
                        "Descarga con: narrative-assistant download-models\n"
                        "O habilita auto_download=True para descarga automática."
                    ),
                )

        model_to_load = str(model_path)
        logger.info(f"Cargando modelo embeddings: {model_to_load}")
        logger.info(f"Dispositivo: {self.device}, batch_size: {self.batch_size}")

        # Cargar modelo
        try:
            self.model = SentenceTransformer(model_to_load, device=self.device)
        except Exception as e:
            raise ModelNotLoadedError(
                model_name=self.model_name,
                hint=f"Error cargando modelo: {e}",
            ) from e

        # Dimensión de los embeddings
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

        logger.info(f"Modelo cargado en {self.device} (dim={self.embedding_dim})")

    def encode(
        self,
        sentences: str | list[str],
        normalize: bool = True,
        show_progress: bool = False,
        clear_cache: bool = False,
    ) -> np.ndarray:
        """
        Genera embeddings para textos.

        Args:
            sentences: Texto o lista de textos
            normalize: Normalizar embeddings (para similitud coseno)
            show_progress: Mostrar barra de progreso
            clear_cache: Si True, libera memoria GPU después de encoding

        Returns:
            Array numpy de embeddings [n_sentences, embedding_dim]
        """
        from ..core.device import clear_gpu_memory

        if isinstance(sentences, str):
            sentences = [sentences]

        try:
            embeddings = self.model.encode(
                sentences,
                batch_size=self.batch_size,
                normalize_embeddings=normalize,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
            )
        except RuntimeError as e:
            # Detectar OOM y hacer fallback a CPU
            error_msg = str(e).lower()
            if "out of memory" in error_msg or "cuda" in error_msg:
                logger.warning("GPU OOM detectado, limpiando memoria y reintentando en CPU")
                # Limpiar memoria GPU
                clear_gpu_memory()

                # Reducir batch size y forzar CPU
                fallback_batch_size = max(4, self.batch_size // 4)
                embeddings = self.model.encode(
                    sentences,
                    batch_size=fallback_batch_size,
                    normalize_embeddings=normalize,
                    show_progress_bar=show_progress,
                    convert_to_numpy=True,
                    device="cpu",
                )
            else:
                raise

        # Limpiar caché si se solicita (importante en sistemas con poca VRAM)
        if clear_cache and self.device != "cpu":
            clear_gpu_memory()

        return embeddings  # type: ignore[no-any-return]

    def similarity(
        self,
        text1: str | list[str],
        text2: str | list[str],
    ) -> float | np.ndarray:
        """
        Calcula similitud coseno entre textos.

        Args:
            text1: Primer texto o lista de textos
            text2: Segundo texto o lista de textos

        Returns:
            Float si ambos son strings, matriz si alguno es lista
        """
        emb1 = self.encode(text1, normalize=True)
        emb2 = self.encode(text2, normalize=True)

        # Similitud coseno (ya normalizados = dot product)
        similarity = np.dot(emb1, emb2.T)

        # Si ambos eran strings, retornar escalar
        if isinstance(text1, str) and isinstance(text2, str):
            return float(similarity[0, 0])

        return similarity  # type: ignore[no-any-return]

    def find_similar(
        self,
        query: str,
        candidates: list[str],
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> list[tuple[int, str, float]]:
        """
        Encuentra los textos más similares a una consulta.

        Args:
            query: Texto de consulta
            candidates: Lista de candidatos
            top_k: Número de resultados
            threshold: Umbral mínimo de similitud

        Returns:
            Lista de (índice, texto, similitud) ordenada por similitud
        """
        if not candidates:
            return []

        query_emb = self.encode(query, normalize=True)
        candidates_emb = self.encode(candidates, normalize=True)

        # Similitudes
        similarities = np.dot(candidates_emb, query_emb.T).flatten()

        # Filtrar por umbral y ordenar
        results = []
        for idx, (text, sim) in enumerate(zip(candidates, similarities, strict=False)):
            if sim >= threshold:
                results.append((idx, text, float(sim)))

        # Ordenar por similitud descendente
        results.sort(key=lambda x: x[2], reverse=True)

        return results[:top_k]

    def get_device_info(self) -> dict:
        """Retorna información del dispositivo actual."""
        detector = get_device_detector()
        device_info = detector.current_device

        return {
            "device": self.device,
            "device_type": device_info.device_type.name if device_info else "unknown",
            "device_name": device_info.device_name if device_info else "unknown",
            "batch_size": self.batch_size,
            "model_name": self.model_name,
            "embedding_dim": self.embedding_dim,
        }

    def warmup(self):
        """Calienta el modelo con una inferencia inicial."""
        logger.debug("Calentando modelo de embeddings...")
        _ = self.encode(["warmup"])
        logger.debug("Modelo calentado")


def get_embeddings_model(
    model_name: str | None = None,
    device: str | None = None,
) -> EmbeddingsModel:
    """
    Obtiene el modelo de embeddings singleton (thread-safe).

    Args:
        model_name: Nombre del modelo (solo para primera inicialización)
        device: Dispositivo (solo para primera inicialización)

    Returns:
        Instancia de EmbeddingsModel
    """
    global _embeddings_model

    if _embeddings_model is None:
        with _embeddings_lock:
            # Double-checked locking
            if _embeddings_model is None:
                _embeddings_model = EmbeddingsModel(model_name=model_name, device=device)

    return _embeddings_model


def encode_texts(
    texts: str | list[str],
    normalize: bool = True,
) -> np.ndarray:
    """
    Atajo para generar embeddings.

    Args:
        texts: Texto o lista de textos
        normalize: Normalizar para similitud coseno

    Returns:
        Array de embeddings
    """
    return get_embeddings_model().encode(texts, normalize=normalize)


def reset_embeddings_model():
    """Resetea el modelo singleton (thread-safe, para testing)."""
    global _embeddings_model
    with _embeddings_lock:
        _embeddings_model = None
