"""
Detector de redundancia semántica.

Detecta contenido que se repite semánticamente aunque esté escrito
con palabras diferentes, usando embeddings y búsqueda ANN (FAISS).

Basado en el estudio: docs/research/ESTUDIO_REDUNDANCIA_SEMANTICA.md
"""

import logging
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

from narrative_assistant.core import Result, get_resource_manager

logger = logging.getLogger(__name__)

# Intentar importar FAISS
try:
    import faiss

    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS no disponible - usando búsqueda lineal (más lento)")


class DuplicateType(Enum):
    """Tipo de duplicado semántico."""

    TEXTUAL = "textual"  # Casi idéntico, mismo texto reformulado
    THEMATIC = "thematic"  # Mismo tema/idea
    ACTION = "action"  # Misma acción de personaje


class RedundancyMode(Enum):
    """Modo de detección."""

    FAST = "fast"  # LSH/top-100, ~5 seg para 10K oraciones
    BALANCED = "balanced"  # FAISS IVF/top-500, ~30 seg
    THOROUGH = "thorough"  # Exhaustivo, ~5 min


@dataclass
class SemanticDuplicate:
    """Par de textos semánticamente similares."""

    text1: str
    text2: str
    chapter1: int
    chapter2: int
    position1: int  # Índice de oración en el documento
    position2: int
    start_char1: int
    start_char2: int
    similarity: float
    duplicate_type: DuplicateType

    def to_dict(self) -> dict[str, Any]:
        """Serializa a diccionario."""
        return {
            "text1": self.text1,
            "text2": self.text2,
            "chapter1": self.chapter1,
            "chapter2": self.chapter2,
            "position1": self.position1,
            "position2": self.position2,
            "start_char1": self.start_char1,
            "start_char2": self.start_char2,
            "similarity": round(self.similarity, 4),
            "duplicate_type": self.duplicate_type.value,
        }


@dataclass
class RedundancyReport:
    """Reporte de redundancias detectadas."""

    duplicates: list[SemanticDuplicate]
    sentences_analyzed: int
    chapters_analyzed: int
    processing_time_seconds: float
    mode: str
    threshold: float

    # Estadísticas
    textual_count: int = 0
    thematic_count: int = 0
    action_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serializa a diccionario."""
        return {
            "duplicates": [d.to_dict() for d in self.duplicates],
            "sentences_analyzed": self.sentences_analyzed,
            "chapters_analyzed": self.chapters_analyzed,
            "processing_time_seconds": round(self.processing_time_seconds, 2),
            "mode": self.mode,
            "threshold": self.threshold,
            "textual_count": self.textual_count,
            "thematic_count": self.thematic_count,
            "action_count": self.action_count,
            "total_duplicates": len(self.duplicates),
        }


@dataclass
class SentenceInfo:
    """Información de una oración."""

    text: str
    chapter: int
    position: int  # Índice en el documento
    start_char: int  # Posición absoluta


class SemanticRedundancyDetector:
    """
    Detector de redundancia semántica optimizado.

    Usa FAISS para búsqueda ANN (Approximate Nearest Neighbors)
    reduciendo la complejidad de O(n²) a O(n log n).
    """

    # Frases comunes que no deben marcarse como duplicados
    COMMON_PHRASES = {
        "dijo que",
        "se levantó",
        "miró a",
        "pensó en",
        "volvió a",
        "al día siguiente",
        "en ese momento",
        "por la noche",
        "al final",
        "sin embargo",
        "por otra parte",
        "de repente",
        "poco después",
        "mientras tanto",
        "a pesar de",
        "por supuesto",
        "de pronto",
        "una vez más",
        "al mismo tiempo",
        "en realidad",
        "de nuevo",
    }

    # Patrones de diálogo (no comparar diálogos cortos)
    DIALOGUE_PATTERNS = [
        r"^—[^—]{1,50}—?$",  # Diálogo corto con raya
        r'^"[^"]{1,50}"$',  # Diálogo corto con comillas
        r"^«[^»]{1,50}»$",  # Diálogo corto con guillemets
    ]

    def __init__(
        self,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        similarity_threshold: float = 0.85,
        mode: RedundancyMode = RedundancyMode.BALANCED,
        use_gpu: bool | None = None,
        min_sentence_length: int = 20,
        max_sentence_length: int = 500,
    ):
        """
        Inicializa el detector.

        Args:
            model_name: Modelo de sentence-transformers a usar
            similarity_threshold: Umbral de similitud (0.0-1.0)
            mode: Modo de detección (fast, balanced, thorough)
            use_gpu: Usar GPU para embeddings (None = auto-detect)
            min_sentence_length: Longitud mínima de oración (caracteres)
            max_sentence_length: Longitud máxima de oración (caracteres)
        """
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold
        self.mode = mode
        self.min_sentence_length = min_sentence_length
        self.max_sentence_length = max_sentence_length

        # Determinar uso de GPU
        if use_gpu is None:
            rm = get_resource_manager()
            self.use_gpu = rm.recommendation.use_gpu_for_embeddings
        else:
            self.use_gpu = use_gpu

        self._model = None
        self._compiled_dialogue = [re.compile(p) for p in self.DIALOGUE_PATTERNS]

        # Parámetros por modo
        self._mode_params = {
            RedundancyMode.FAST: {"k_neighbors": 50, "nlist": 100},
            RedundancyMode.BALANCED: {"k_neighbors": 100, "nlist": 50},
            RedundancyMode.THOROUGH: {"k_neighbors": 500, "nlist": 20},
        }

    def _get_model(self):
        """Obtiene el modelo de embeddings (lazy loading)."""
        if self._model is None:
            from narrative_assistant.nlp.embeddings import EmbeddingsModel

            self._model = EmbeddingsModel(
                model_name=self.model_name,
                use_gpu=self.use_gpu,
            )
        return self._model

    def detect(
        self,
        chapters: list[dict],
        max_duplicates: int = 100,
    ) -> Result[RedundancyReport]:
        """
        Detecta duplicados semánticos en capítulos.

        Args:
            chapters: Lista de capítulos con 'number', 'content', 'start_char'
            max_duplicates: Máximo de duplicados a reportar

        Returns:
            Result con RedundancyReport
        """
        start_time = time.time()

        try:
            # Extraer oraciones
            sentences = self._extract_sentences(chapters)

            if len(sentences) < 2:
                return Result.success(
                    RedundancyReport(
                        duplicates=[],
                        sentences_analyzed=len(sentences),
                        chapters_analyzed=len(chapters),
                        processing_time_seconds=time.time() - start_time,
                        mode=self.mode.value,
                        threshold=self.similarity_threshold,
                    )
                )

            logger.info(f"Analizando {len(sentences)} oraciones en modo {self.mode.value}")

            # Generar embeddings
            texts = [s.text for s in sentences]
            model = self._get_model()
            embeddings = model.encode(texts, show_progress=len(texts) > 1000)

            if embeddings is None:
                return Result.failure(Exception("Error generando embeddings"))

            # Encontrar duplicados usando FAISS o búsqueda lineal
            if FAISS_AVAILABLE and len(sentences) > 100:
                duplicates = self._find_duplicates_faiss(sentences, embeddings, max_duplicates)
            else:
                duplicates = self._find_duplicates_linear(sentences, embeddings, max_duplicates)

            # Contar por tipo
            textual = sum(1 for d in duplicates if d.duplicate_type == DuplicateType.TEXTUAL)
            thematic = sum(1 for d in duplicates if d.duplicate_type == DuplicateType.THEMATIC)
            action = sum(1 for d in duplicates if d.duplicate_type == DuplicateType.ACTION)

            processing_time = time.time() - start_time
            logger.info(
                f"Redundancia semántica: {len(duplicates)} duplicados encontrados "
                f"en {processing_time:.2f}s"
            )

            return Result.success(
                RedundancyReport(
                    duplicates=duplicates,
                    sentences_analyzed=len(sentences),
                    chapters_analyzed=len(chapters),
                    processing_time_seconds=processing_time,
                    mode=self.mode.value,
                    threshold=self.similarity_threshold,
                    textual_count=textual,
                    thematic_count=thematic,
                    action_count=action,
                )
            )

        except Exception as e:
            logger.error(f"Error en detección de redundancia: {e}", exc_info=True)
            return Result.failure(e)

    def _extract_sentences(self, chapters: list[dict]) -> list[SentenceInfo]:
        """Extrae oraciones de los capítulos."""
        sentences = []
        position = 0

        for chapter in chapters:
            ch_num = chapter.get("number", 0)
            content = chapter.get("content", "")
            ch_start = chapter.get("start_char", 0)

            if not content or not content.strip():
                continue

            # Dividir en oraciones
            # Patrón simple: separar por .!? seguido de espacio y mayúscula
            raw_sentences = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ])", content)

            current_pos = 0
            for sent in raw_sentences:
                sent = sent.strip()

                # Filtrar por longitud
                if len(sent) < self.min_sentence_length:
                    current_pos += len(sent) + 1
                    continue

                if len(sent) > self.max_sentence_length:
                    # Truncar oraciones muy largas
                    sent = sent[: self.max_sentence_length] + "..."

                # Filtrar diálogos cortos
                if self._is_short_dialogue(sent):
                    current_pos += len(sent) + 1
                    continue

                # Filtrar frases comunes
                if self._is_common_phrase(sent):
                    current_pos += len(sent) + 1
                    continue

                sentences.append(
                    SentenceInfo(
                        text=sent,
                        chapter=ch_num,
                        position=position,
                        start_char=ch_start + current_pos,
                    )
                )

                position += 1
                current_pos += len(sent) + 1

        return sentences

    def _is_short_dialogue(self, text: str) -> bool:
        """Verifica si es un diálogo corto."""
        return any(pattern.match(text) for pattern in self._compiled_dialogue)

    def _is_common_phrase(self, text: str) -> bool:
        """Verifica si contiene principalmente frases comunes."""
        text_lower = text.lower()
        return any(phrase in text_lower and len(text) < 100 for phrase in self.COMMON_PHRASES)

    def _find_duplicates_faiss(
        self,
        sentences: list[SentenceInfo],
        embeddings: np.ndarray,
        max_duplicates: int,
    ) -> list[SemanticDuplicate]:
        """Encuentra duplicados usando FAISS."""
        duplicates = []
        seen_pairs = set()

        n_sentences = len(sentences)
        dim = embeddings.shape[1]
        params = self._mode_params[self.mode]

        # Normalizar embeddings para similitud coseno
        faiss.normalize_L2(embeddings)

        # Crear índice FAISS
        if self.mode == RedundancyMode.THOROUGH or n_sentences < 1000:
            # Búsqueda exacta para modo thorough o datasets pequeños
            index = faiss.IndexFlatIP(dim)  # Inner Product = Cosine después de normalizar
        else:
            # Índice IVF para datasets grandes
            nlist = min(params["nlist"], n_sentences // 10)
            nlist = max(nlist, 1)
            quantizer = faiss.IndexFlatIP(dim)
            index = faiss.IndexIVFFlat(quantizer, dim, nlist, faiss.METRIC_INNER_PRODUCT)
            index.train(embeddings)

        index.add(embeddings)

        # Buscar k vecinos más cercanos para cada oración
        k = min(params["k_neighbors"], n_sentences)
        distances, indices = index.search(embeddings, k)

        # Procesar resultados
        for i in range(n_sentences):
            for j_idx in range(k):
                j = indices[i][j_idx]
                similarity = distances[i][j_idx]

                # Ignorar la misma oración
                if i == j:
                    continue

                # Ignorar si similitud bajo umbral
                if similarity < self.similarity_threshold:
                    continue

                # Evitar duplicados de pares
                pair_key = (min(i, j), max(i, j))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                # Crear duplicado
                dup = self._create_duplicate(sentences[i], sentences[j], similarity)
                if dup:
                    duplicates.append(dup)

                if len(duplicates) >= max_duplicates:
                    return duplicates

        # Ordenar por similitud descendente
        duplicates.sort(key=lambda d: -d.similarity)
        return duplicates[:max_duplicates]

    def _find_duplicates_linear(
        self,
        sentences: list[SentenceInfo],
        embeddings: np.ndarray,
        max_duplicates: int,
    ) -> list[SemanticDuplicate]:
        """Encuentra duplicados con búsqueda lineal (fallback sin FAISS)."""
        duplicates: list[dict[str, Any]] = []
        seen_pairs = set()

        n_sentences = len(sentences)

        # Normalizar para similitud coseno
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / (norms + 1e-10)

        # Matriz de similitud (solo triángulo superior)
        for i in range(n_sentences):
            if len(duplicates) >= max_duplicates:
                break

            # Calcular similitudes con todas las oraciones posteriores
            similarities = np.dot(normalized[i], normalized[i + 1 :].T)

            for j_offset, similarity in enumerate(similarities):
                j = i + 1 + j_offset

                if similarity < self.similarity_threshold:
                    continue

                pair_key = (i, j)
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                dup = self._create_duplicate(sentences[i], sentences[j], float(similarity))
                if dup:
                    duplicates.append(dup)

                if len(duplicates) >= max_duplicates:
                    break

        duplicates.sort(key=lambda d: -d.similarity)
        return duplicates[:max_duplicates]

    def _create_duplicate(
        self,
        sent1: SentenceInfo,
        sent2: SentenceInfo,
        similarity: float,
    ) -> SemanticDuplicate | None:
        """Crea un objeto SemanticDuplicate con clasificación de tipo."""
        # Ajustar peso si es mismo capítulo (menos relevante)
        adjusted_sim = similarity
        if sent1.chapter == sent2.chapter:
            adjusted_sim *= 0.9  # Penalizar ligeramente

            # Si están muy cerca, probablemente no es redundancia
            if abs(sent1.position - sent2.position) < 3:
                return None

        if adjusted_sim < self.similarity_threshold:
            return None

        # Clasificar tipo de duplicado
        dup_type = self._classify_duplicate_type(sent1.text, sent2.text, similarity)

        return SemanticDuplicate(
            text1=sent1.text,
            text2=sent2.text,
            chapter1=sent1.chapter,
            chapter2=sent2.chapter,
            position1=sent1.position,
            position2=sent2.position,
            start_char1=sent1.start_char,
            start_char2=sent2.start_char,
            similarity=similarity,
            duplicate_type=dup_type,
        )

    def _classify_duplicate_type(
        self,
        text1: str,
        text2: str,
        similarity: float,
    ) -> DuplicateType:
        """Clasifica el tipo de duplicado."""
        # Similitud muy alta = casi idéntico (textual)
        if similarity >= 0.95:
            return DuplicateType.TEXTUAL

        # Detectar acciones de personajes
        action_verbs = {
            "caminó",
            "corrió",
            "saltó",
            "miró",
            "observó",
            "dijo",
            "pensó",
            "sintió",
            "tomó",
            "dejó",
            "abrió",
            "cerró",
            "entró",
            "salió",
            "subió",
            "bajó",
            "se levantó",
            "se sentó",
        }
        text1_lower = text1.lower()
        text2_lower = text2.lower()

        has_action = any(v in text1_lower and v in text2_lower for v in action_verbs)
        if has_action:
            return DuplicateType.ACTION

        # Por defecto, temático
        return DuplicateType.THEMATIC


def get_semantic_redundancy_detector(
    mode: str = "balanced",
    threshold: float = 0.85,
) -> SemanticRedundancyDetector:
    """
    Factory function para crear detector con configuración.

    Args:
        mode: Modo de detección (fast, balanced, thorough)
        threshold: Umbral de similitud

    Returns:
        SemanticRedundancyDetector configurado
    """
    mode_enum = RedundancyMode(mode)
    return SemanticRedundancyDetector(
        mode=mode_enum,
        similarity_threshold=threshold,
    )
