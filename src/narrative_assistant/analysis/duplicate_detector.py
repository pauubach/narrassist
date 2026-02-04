"""
Detector de contenido duplicado a nivel frase y párrafo.

Detecta:
- Frases duplicadas exactas o casi-exactas
- Párrafos duplicados semánticamente
- Fragmentos copiados/pegados accidentalmente

Complementa al RepetitionDetector que trabaja a nivel palabra.
"""

import logging
import re
import threading
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum
from typing import Optional

from ..core.errors import ErrorSeverity, NarrativeError
from ..core.result import Result

logger = logging.getLogger(__name__)

# =============================================================================
# Singleton
# =============================================================================

_lock = threading.Lock()
_instance: Optional["DuplicateDetector"] = None


def get_duplicate_detector() -> "DuplicateDetector":
    """Obtener instancia singleton del detector de duplicados."""
    global _instance

    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = DuplicateDetector()

    return _instance


def reset_duplicate_detector() -> None:
    """Resetear instancia (para testing)."""
    global _instance
    with _lock:
        _instance = None


# =============================================================================
# Tipos
# =============================================================================


class DuplicateType(Enum):
    """Tipos de duplicados detectados."""

    EXACT_SENTENCE = "exact_sentence"  # Frase idéntica
    NEAR_SENTENCE = "near_sentence"  # Frase casi idéntica (>90% similar)
    EXACT_PARAGRAPH = "exact_paragraph"  # Párrafo idéntico
    NEAR_PARAGRAPH = "near_paragraph"  # Párrafo muy similar
    SEMANTIC_PARAGRAPH = "semantic"  # Párrafo con mismo significado


class DuplicateSeverity(Enum):
    """Severidad del duplicado."""

    CRITICAL = "critical"  # Mismo contenido exacto
    HIGH = "high"  # >95% similitud
    MEDIUM = "medium"  # 85-95% similitud
    LOW = "low"  # 75-85% similitud


@dataclass
class DuplicateLocation:
    """Ubicación de un duplicado."""

    chapter: int
    paragraph: int
    start_char: int
    end_char: int
    text: str  # Extracto del texto

    def to_dict(self) -> dict:
        return {
            "chapter": self.chapter,
            "paragraph": self.paragraph,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "text": self.text[:200] + "..." if len(self.text) > 200 else self.text,
        }


@dataclass
class DuplicateMatch:
    """Un par de contenidos duplicados."""

    # Tipo y severidad
    duplicate_type: DuplicateType
    severity: DuplicateSeverity

    # Similitud
    similarity: float  # 0.0-1.0

    # Ubicaciones
    location1: DuplicateLocation
    location2: DuplicateLocation

    # Distancia entre ocurrencias
    distance_chars: int = 0
    distance_paragraphs: int = 0

    # Confianza
    confidence: float = 0.9

    def to_dict(self) -> dict:
        return {
            "type": self.duplicate_type.value,
            "severity": self.severity.value,
            "similarity": round(self.similarity, 3),
            "location1": self.location1.to_dict(),
            "location2": self.location2.to_dict(),
            "distance_chars": self.distance_chars,
            "distance_paragraphs": self.distance_paragraphs,
            "confidence": round(self.confidence, 2),
        }


@dataclass
class DuplicateReport:
    """Resultado del análisis de duplicados."""

    duplicates: list[DuplicateMatch] = field(default_factory=list)

    # Estadísticas
    sentences_analyzed: int = 0
    paragraphs_analyzed: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    by_severity: dict[str, int] = field(default_factory=dict)

    def add_duplicate(self, dup: DuplicateMatch) -> None:
        """Añadir un duplicado detectado."""
        self.duplicates.append(dup)

        type_key = dup.duplicate_type.value
        self.by_type[type_key] = self.by_type.get(type_key, 0) + 1

        severity_key = dup.severity.value
        self.by_severity[severity_key] = self.by_severity.get(severity_key, 0) + 1

    def get_critical(self) -> list[DuplicateMatch]:
        """Obtener duplicados críticos."""
        return [d for d in self.duplicates if d.severity == DuplicateSeverity.CRITICAL]

    def to_dict(self) -> dict:
        return {
            "duplicates": [d.to_dict() for d in self.duplicates],
            "sentences_analyzed": self.sentences_analyzed,
            "paragraphs_analyzed": self.paragraphs_analyzed,
            "by_type": self.by_type,
            "by_severity": self.by_severity,
            "total_duplicates": len(self.duplicates),
            "critical_count": len(self.get_critical()),
        }


@dataclass
class DuplicateDetectionError(NarrativeError):
    """Error durante la detección de duplicados."""

    original_error: str = ""
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.RECOVERABLE, init=False)

    def __post_init__(self):
        self.message = f"Duplicate detection error: {self.original_error}"
        super().__post_init__()


# =============================================================================
# Detector
# =============================================================================


class DuplicateDetector:
    """
    Detector de contenido duplicado.

    Detecta frases y párrafos duplicados usando:
    - Comparación exacta (hash)
    - Similitud de secuencia (difflib)
    - Similitud semántica (embeddings) para párrafos
    """

    def __init__(self):
        """Inicializar el detector."""
        self._embeddings = None
        self._load_embeddings()

    def _load_embeddings(self) -> None:
        """Cargar modelo de embeddings si está disponible."""
        try:
            from ..nlp.embeddings import get_embeddings_model

            self._embeddings = get_embeddings_model()
        except Exception as e:
            logger.warning(f"Embeddings not available for semantic duplicate detection: {e}")

    def detect_sentence_duplicates(
        self,
        text: str,
        min_sentence_length: int = 30,
        similarity_threshold: float = 0.90,
        chapters: list[dict] | None = None,
    ) -> Result[DuplicateReport]:
        """
        Detectar frases duplicadas.

        Args:
            text: Texto completo a analizar
            min_sentence_length: Longitud mínima de frase para considerar
            similarity_threshold: Umbral de similitud (0.0-1.0)
            chapters: Lista de capítulos con {number, start_char, end_char}

        Returns:
            Result con DuplicateReport
        """
        report = DuplicateReport()

        try:
            # Extraer frases
            sentences = self._extract_sentences(text)
            report.sentences_analyzed = len(sentences)

            # Filtrar frases muy cortas
            sentences = [s for s in sentences if len(s["text"]) >= min_sentence_length]

            if len(sentences) < 2:
                return Result.success(report)

            # Comparar pares de frases
            seen_pairs: set[tuple[int, int]] = set()

            for i, sent1 in enumerate(sentences):
                for j, sent2 in enumerate(sentences):
                    if i >= j:
                        continue

                    pair_key = (min(i, j), max(i, j))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    # Normalizar para comparación
                    text1 = self._normalize_for_comparison(sent1["text"])
                    text2 = self._normalize_for_comparison(sent2["text"])

                    # Comparar
                    if text1 == text2:
                        similarity = 1.0
                    else:
                        similarity = self._sequence_similarity(text1, text2)

                    if similarity < similarity_threshold:
                        continue

                    # Determinar tipo y severidad
                    if similarity == 1.0:
                        dup_type = DuplicateType.EXACT_SENTENCE
                        severity = DuplicateSeverity.CRITICAL
                    elif similarity >= 0.95:
                        dup_type = DuplicateType.NEAR_SENTENCE
                        severity = DuplicateSeverity.HIGH
                    else:
                        dup_type = DuplicateType.NEAR_SENTENCE
                        severity = DuplicateSeverity.MEDIUM

                    # Obtener capítulos
                    ch1 = self._find_chapter(sent1["start"], chapters) if chapters else 0
                    ch2 = self._find_chapter(sent2["start"], chapters) if chapters else 0

                    match = DuplicateMatch(
                        duplicate_type=dup_type,
                        severity=severity,
                        similarity=similarity,
                        location1=DuplicateLocation(
                            chapter=ch1,
                            paragraph=sent1.get("paragraph", 0),
                            start_char=sent1["start"],
                            end_char=sent1["end"],
                            text=sent1["text"],
                        ),
                        location2=DuplicateLocation(
                            chapter=ch2,
                            paragraph=sent2.get("paragraph", 0),
                            start_char=sent2["start"],
                            end_char=sent2["end"],
                            text=sent2["text"],
                        ),
                        distance_chars=abs(sent2["start"] - sent1["end"]),
                        confidence=0.95 if similarity == 1.0 else 0.85,
                    )
                    report.add_duplicate(match)

            return Result.success(report)

        except Exception as e:
            logger.error(f"Error detecting sentence duplicates: {e}")
            return Result.partial(report, [DuplicateDetectionError(original_error=str(e))])

    def detect_paragraph_duplicates(
        self,
        paragraphs: list[dict],
        similarity_threshold: float = 0.85,
        use_semantic: bool = True,
    ) -> Result[DuplicateReport]:
        """
        Detectar párrafos duplicados.

        Args:
            paragraphs: Lista de {text, chapter, paragraph_number, start_char, end_char}
            similarity_threshold: Umbral de similitud
            use_semantic: Usar embeddings para detección semántica

        Returns:
            Result con DuplicateReport
        """
        report = DuplicateReport()
        report.paragraphs_analyzed = len(paragraphs)

        if len(paragraphs) < 2:
            return Result.success(report)

        try:
            # Obtener embeddings si están disponibles
            embeddings = None
            if use_semantic and self._embeddings:
                texts = [p["text"] for p in paragraphs]
                embeddings = self._embeddings.encode(texts)

            # Comparar pares
            seen_pairs: set[tuple[int, int]] = set()

            for i, para1 in enumerate(paragraphs):
                for j, para2 in enumerate(paragraphs):
                    if i >= j:
                        continue

                    pair_key = (min(i, j), max(i, j))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    text1 = self._normalize_for_comparison(para1["text"])
                    text2 = self._normalize_for_comparison(para2["text"])

                    # Similitud textual
                    if text1 == text2:
                        text_sim = 1.0
                    else:
                        text_sim = self._sequence_similarity(text1, text2)

                    # Similitud semántica
                    semantic_sim = 0.0
                    if embeddings is not None:
                        semantic_sim = self._cosine_similarity(embeddings[i], embeddings[j])

                    # Usar la mayor similitud
                    similarity = max(text_sim, semantic_sim)

                    if similarity < similarity_threshold:
                        continue

                    # Determinar tipo y severidad
                    if text_sim == 1.0:
                        dup_type = DuplicateType.EXACT_PARAGRAPH
                        severity = DuplicateSeverity.CRITICAL
                    elif text_sim >= 0.90:
                        dup_type = DuplicateType.NEAR_PARAGRAPH
                        severity = DuplicateSeverity.HIGH
                    elif semantic_sim >= text_sim:
                        dup_type = DuplicateType.SEMANTIC_PARAGRAPH
                        severity = DuplicateSeverity.MEDIUM
                    else:
                        dup_type = DuplicateType.NEAR_PARAGRAPH
                        severity = DuplicateSeverity.MEDIUM

                    match = DuplicateMatch(
                        duplicate_type=dup_type,
                        severity=severity,
                        similarity=similarity,
                        location1=DuplicateLocation(
                            chapter=para1.get("chapter", 0),
                            paragraph=para1.get("paragraph_number", i),
                            start_char=para1.get("start_char", 0),
                            end_char=para1.get("end_char", 0),
                            text=para1["text"],
                        ),
                        location2=DuplicateLocation(
                            chapter=para2.get("chapter", 0),
                            paragraph=para2.get("paragraph_number", j),
                            start_char=para2.get("start_char", 0),
                            end_char=para2.get("end_char", 0),
                            text=para2["text"],
                        ),
                        distance_paragraphs=abs(j - i),
                        confidence=0.95 if text_sim >= 0.95 else 0.80,
                    )
                    report.add_duplicate(match)

            return Result.success(report)

        except Exception as e:
            logger.error(f"Error detecting paragraph duplicates: {e}")
            return Result.partial(report, [DuplicateDetectionError(original_error=str(e))])

    def detect_all(
        self,
        text: str,
        paragraphs: list[dict] | None = None,
        chapters: list[dict] | None = None,
        sentence_threshold: float = 0.90,
        paragraph_threshold: float = 0.85,
    ) -> Result[DuplicateReport]:
        """
        Detectar todos los tipos de duplicados.

        Args:
            text: Texto completo
            paragraphs: Lista de párrafos con metadatos
            chapters: Lista de capítulos con rangos
            sentence_threshold: Umbral para frases
            paragraph_threshold: Umbral para párrafos

        Returns:
            Result con DuplicateReport combinado
        """
        combined = DuplicateReport()

        # Detectar frases duplicadas
        sentence_result = self.detect_sentence_duplicates(
            text, similarity_threshold=sentence_threshold, chapters=chapters
        )
        if sentence_result.is_success:
            combined.sentences_analyzed = sentence_result.value.sentences_analyzed
            for dup in sentence_result.value.duplicates:
                combined.add_duplicate(dup)

        # Detectar párrafos duplicados
        if paragraphs:
            para_result = self.detect_paragraph_duplicates(
                paragraphs, similarity_threshold=paragraph_threshold
            )
            if para_result.is_success:
                combined.paragraphs_analyzed = para_result.value.paragraphs_analyzed
                for dup in para_result.value.duplicates:
                    combined.add_duplicate(dup)

        return Result.success(combined)

    # =========================================================================
    # Helpers
    # =========================================================================

    def _extract_sentences(self, text: str) -> list[dict]:
        """Extraer frases del texto con posiciones."""
        sentences = []

        # Patrón para detectar fin de oración
        sentence_pattern = re.compile(r"[^.!?]+[.!?]+")

        para_num = 0
        for para_match in re.finditer(r"[^\n]+", text):
            para_text = para_match.group()
            para_start = para_match.start()

            for sent_match in sentence_pattern.finditer(para_text):
                sent_text = sent_match.group().strip()
                if sent_text:
                    sentences.append(
                        {
                            "text": sent_text,
                            "start": para_start + sent_match.start(),
                            "end": para_start + sent_match.end(),
                            "paragraph": para_num,
                        }
                    )

            para_num += 1

        return sentences

    def _normalize_for_comparison(self, text: str) -> str:
        """Normalizar texto para comparación."""
        # Lowercase
        text = text.lower()
        # Eliminar espacios múltiples
        text = re.sub(r"\s+", " ", text)
        # Eliminar puntuación extra
        text = re.sub(r"[.,;:!?]+", " ", text)
        # Strip
        text = text.strip()
        return text

    def _sequence_similarity(self, text1: str, text2: str) -> float:
        """Calcular similitud de secuencia usando SequenceMatcher."""
        return SequenceMatcher(None, text1, text2).ratio()

    def _cosine_similarity(self, vec1, vec2) -> float:
        """Calcular similitud coseno."""
        import numpy as np

        dot = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot / (norm1 * norm2))

    def _find_chapter(self, position: int, chapters: list[dict] | None) -> int:
        """Encontrar número de capítulo para una posición."""
        if not chapters:
            return 0

        for ch in chapters:
            if ch.get("start_char", 0) <= position < ch.get("end_char", float("inf")):
                return ch.get("number", 0)

        return 0
