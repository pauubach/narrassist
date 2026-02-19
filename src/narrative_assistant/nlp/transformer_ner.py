"""
NER basado en modelos Transformer (BETO / XLM-RoBERTa).

Proporciona extracción de entidades nombradas usando modelos transformer
fine-tuned para NER en español, como alternativa/complemento a spaCy.

Modelos soportados (en orden de preferencia):
- mrm8488/bert-spanish-cased-finetuned-ner (~440MB, default, público)
- PlanTL-GOB-ES/roberta-base-bne-capitel-ner (~500MB, requiere auth HF)
- PlanTL-GOB-ES/roberta-large-bne-capitel-ner (~1.4GB, requiere auth HF)

NOTA: Los modelos PlanTL-GOB-ES fueron gateados en HuggingFace (~2025)
y requieren autenticación. mrm8488/bert-spanish-cased-finetuned-ner es
el default por ser público y tener buen rendimiento para español.

El modelo se descarga automáticamente la primera vez que se usa
y se guarda en ~/.narrative_assistant/models/transformer_ner/.
"""

import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.config import get_config
from ..core.device import get_device

logger = logging.getLogger(__name__)

# Singleton thread-safe
_lock = threading.Lock()
_instance: "TransformerNERModel | None" = None

# Modelos soportados con sus configuraciones
# NOTA: PlanTL-GOB-ES gateado en HuggingFace (~2025), requiere token de autenticación
TRANSFORMER_NER_MODELS = {
    "beto-ner": {
        "hf_name": "mrm8488/bert-spanish-cased-finetuned-ner",
        "size_mb": 440,
        "params": "110M",
        "min_vram_mb": 700,
    },
    "roberta-base-bne": {
        "hf_name": "PlanTL-GOB-ES/roberta-base-bne-capitel-ner",
        "size_mb": 500,
        "params": "125M",
        "min_vram_mb": 800,
        "requires_auth": True,
    },
    "roberta-large-bne": {
        "hf_name": "PlanTL-GOB-ES/roberta-large-bne-capitel-ner",
        "size_mb": 1400,
        "params": "355M",
        "min_vram_mb": 2500,
        "requires_auth": True,
    },
}

DEFAULT_MODEL = "beto-ner"

# Mapeo de etiquetas del modelo a nuestras etiquetas
# PlanTL CAPITEL usa: B-PER, I-PER, B-LOC, I-LOC, B-ORG, I-ORG, B-OTH, I-OTH
# BETO usa: B-PER, I-PER, B-LOC, I-LOC, B-ORG, I-ORG, B-MISC, I-MISC
LABEL_MAP = {
    "PER": "PER",
    "LOC": "LOC",
    "ORG": "ORG",
    "MISC": "MISC",
    "OTH": "MISC",  # CAPITEL usa OTH en lugar de MISC
}


@dataclass
class TransformerNEREntity:
    """Entidad extraída por el modelo transformer."""

    text: str
    label: str  # PER, LOC, ORG, MISC
    start: int
    end: int
    score: float


class TransformerNERModel:
    """
    Modelo NER basado en transformers con descarga bajo demanda.

    Carga el modelo de HuggingFace la primera vez que se usa.
    Soporta GPU/CPU automático.
    """

    def __init__(
        self,
        model_key: str | None = None,
        device: str | None = None,
        cache_dir: str | Path | None = None,
    ):
        """
        Inicializa el modelo.

        Args:
            model_key: Clave del modelo (ver TRANSFORMER_NER_MODELS). None = auto.
            device: Dispositivo ('cuda', 'cpu', None=auto).
            cache_dir: Directorio de cache para el modelo.
        """
        env_model = os.environ.get("NA_TRANSFORMER_NER_MODEL")
        self._model_key: str = model_key or env_model or DEFAULT_MODEL
        self._pipeline: Any | None = None
        self._load_error: str | None = None
        self._cache_dir = cache_dir

        # Determinar dispositivo
        if device:
            self._device = device
        else:
            device_info = get_device()
            self._device = "cuda" if device_info.device_type.value == "cuda" else "cpu"

        model_info = TRANSFORMER_NER_MODELS.get(self._model_key)
        if not model_info:
            logger.warning(
                f"Modelo transformer NER desconocido: {self._model_key}. Usando {DEFAULT_MODEL}"
            )
            self._model_key = DEFAULT_MODEL
            model_info = TRANSFORMER_NER_MODELS[DEFAULT_MODEL]

        self._hf_model_name: str = str(model_info["hf_name"])
        logger.info(
            f"TransformerNER configurado: {self._model_key} "
            f"({model_info['params']}) en {self._device}"
        )

    @property
    def is_available(self) -> bool:
        """Indica si el modelo se puede cargar (transformers instalado)."""
        try:
            import transformers  # noqa: F401

            return True
        except ImportError:
            return False

    @property
    def is_loaded(self) -> bool:
        """Indica si el modelo ya está cargado en memoria."""
        return self._pipeline is not None

    @property
    def model_name(self) -> str:
        """Nombre del modelo HuggingFace."""
        return self._hf_model_name

    def _get_cache_dir(self) -> Path:
        """Obtiene el directorio de cache para modelos transformer NER."""
        if self._cache_dir:
            return Path(self._cache_dir)
        config = get_config()
        models_dir = config.nlp.spacy_model_path
        if models_dir:
            base = models_dir.parent.parent  # models/ dir
        else:
            base = Path.home() / ".narrative_assistant" / "models"
        cache = base / "transformer_ner"
        cache.mkdir(parents=True, exist_ok=True)
        return cache

    def _ensure_model_downloaded(self) -> Path | None:
        """
        Usa ModelManager para asegurar que el modelo está descargado localmente.

        Returns:
            Path al modelo local si está disponible, None si no se pudo.
        """
        try:
            from ..core.model_manager import ModelType, get_model_manager

            manager = get_model_manager()

            # Primero verificar si ya existe localmente
            existing = manager.get_model_path(ModelType.TRANSFORMER_NER)
            if existing:
                return existing

            # Descargar con progreso gestionado
            logger.info(
                "Modelo transformer NER no encontrado localmente. Iniciando descarga (~500 MB)..."
            )

            def log_progress(message: str, percent: float):
                logger.info(f"[Transformer NER] {message} ({int(percent * 100)}%)")

            result = manager.ensure_model(
                ModelType.TRANSFORMER_NER,
                progress_callback=log_progress,
            )

            if result.is_success:
                return result.value
            else:
                logger.warning(
                    f"ModelManager no pudo descargar: "
                    f"{result.error.message if result.error else 'desconocido'}"
                )
                return None

        except Exception as e:
            logger.warning(f"Error usando ModelManager para transformer NER: {e}")
            return None

    def _load_pipeline(self) -> bool:
        """
        Carga el pipeline de HuggingFace (descarga si es necesario).

        Primero intenta usar ModelManager para garantizar descarga gestionada
        con progreso. Si no está disponible, descarga directamente desde
        HuggingFace.

        Returns:
            True si se cargó correctamente, False en caso de error.
        """
        if self._pipeline is not None:
            return True
        if self._load_error:
            return False

        try:
            from transformers import AutoModelForTokenClassification, AutoTokenizer
            from transformers import pipeline as hf_pipeline
        except ImportError:
            self._load_error = "transformers no instalado. Instalar con: pip install transformers"
            logger.warning(self._load_error)
            return False

        local_model_path = None
        try:
            # Intentar usar ModelManager para descarga gestionada
            local_model_path = self._ensure_model_downloaded()

            if local_model_path:
                model_source = str(local_model_path)
                logger.info(f"Cargando transformer NER desde cache local: {model_source}")
            else:
                model_source = self._hf_model_name
                logger.warning(
                    f"Descarga directa desde HuggingFace: {model_source}. "
                    f"Esto puede tardar varios minutos (~500 MB)..."
                )

            # Determinar device_map para pipeline
            device_arg = 0 if self._device == "cuda" else -1

            logger.info(f"Cargando tokenizer desde: {model_source}")
            tokenizer = AutoTokenizer.from_pretrained(model_source)

            logger.info(f"Cargando pesos del modelo desde: {model_source}")
            model = AutoModelForTokenClassification.from_pretrained(model_source)

            self._pipeline = hf_pipeline(
                "ner",
                model=model,
                tokenizer=tokenizer,
                device=device_arg,
                aggregation_strategy="simple",
            )

            logger.info(f"Modelo transformer NER cargado: {self._hf_model_name} en {self._device}")
            return True

        except Exception as e:
            # Fallback a CPU si GPU falla
            if self._device == "cuda":
                logger.warning(f"Error cargando transformer NER en GPU: {e}. Intentando en CPU...")
                self._device = "cpu"
                try:
                    source = str(local_model_path) if local_model_path else self._hf_model_name
                    self._pipeline = hf_pipeline(
                        "ner",
                        model=source,
                        tokenizer=source,
                        device=-1,
                        aggregation_strategy="simple",
                    )
                    logger.info("Modelo transformer NER cargado en CPU (fallback)")
                    return True
                except Exception as e2:
                    self._load_error = f"Error cargando en CPU: {e2}"
                    logger.error(self._load_error)
                    return False
            else:
                self._load_error = f"Error cargando modelo: {e}"
                logger.error(self._load_error)
                return False

    def extract(self, text: str) -> list[TransformerNEREntity]:
        """
        Extrae entidades del texto usando el modelo transformer.

        Args:
            text: Texto a analizar.

        Returns:
            Lista de entidades extraídas. Lista vacía si el modelo no está
            disponible o hay error.
        """
        if not self._load_pipeline():
            return []

        if not text or not text.strip():
            return []

        try:
            # El pipeline de HuggingFace tiene límite de tokens (512)
            # Para textos largos, procesamos por chunks
            max_chars = 2000  # ~512 tokens en español
            chunks = self._split_text(text, max_chars)

            all_entities: list[TransformerNEREntity] = []
            assert self._pipeline is not None
            for chunk_text, offset in chunks:
                raw_entities = self._pipeline(chunk_text)
                for ent in raw_entities:
                    label = self._normalize_label(ent.get("entity_group", ""))
                    if not label:
                        continue
                    score = float(ent.get("score", 0.0))
                    if score < 0.5:
                        continue
                    entity = TransformerNEREntity(
                        text=ent.get("word", "").strip(),
                        label=label,
                        start=ent.get("start", 0) + offset,
                        end=ent.get("end", 0) + offset,
                        score=score,
                    )
                    # Filtrar entidades vacías o con texto basura (subtokens)
                    if entity.text and len(entity.text) > 1:
                        all_entities.append(entity)

            return all_entities

        except Exception as e:
            logger.error(f"Error en extracción transformer NER: {e}")
            return []

    def _normalize_label(self, raw_label: str) -> str | None:
        """Normaliza etiqueta del modelo a nuestro esquema."""
        # Eliminar prefijo B-/I- si existe
        clean = raw_label
        if clean.startswith(("B-", "I-")):
            clean = clean[2:]
        return LABEL_MAP.get(clean)

    def _split_text(self, text: str, max_chars: int) -> list[tuple[str, int]]:
        """
        Divide el texto en chunks respetando límites de oraciones.

        Returns:
            Lista de (chunk_text, offset_in_original).
        """
        if len(text) <= max_chars:
            return [(text, 0)]

        chunks = []
        start = 0
        while start < len(text):
            end = min(start + max_chars, len(text))
            # Buscar punto de corte natural (fin de oración)
            if end < len(text):
                # Buscar último punto/salto de línea antes del límite
                for sep in ["\n\n", "\n", ". ", "? ", "! "]:
                    last_sep = text[start:end].rfind(sep)
                    if last_sep > max_chars // 2:
                        end = start + last_sep + len(sep)
                        break
            chunks.append((text[start:end], start))
            start = end
        return chunks


def get_transformer_ner(
    model_key: str | None = None,
    force_new: bool = False,
) -> TransformerNERModel:
    """
    Obtiene la instancia singleton del modelo transformer NER.

    Args:
        model_key: Clave del modelo. None = usar default/env var.
        force_new: Si True, crea una nueva instancia.
    """
    global _instance
    if _instance is None or force_new:
        with _lock:
            if _instance is None or force_new:
                _instance = TransformerNERModel(model_key=model_key)
    return _instance


def reset_transformer_ner() -> None:
    """Resetea la instancia singleton (para tests)."""
    global _instance
    with _lock:
        _instance = None
