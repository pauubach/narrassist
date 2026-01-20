"""
Detector de coherencia narrativa.

Analiza la coherencia semántica entre segmentos de texto consecutivos
para detectar saltos bruscos en la narrativa que podrían indicar:
- Errores de edición (párrafos fuera de lugar)
- Transiciones mal ejecutadas
- Escenas que necesitan conectores narrativos

Usa embeddings semánticos para medir la similitud entre párrafos/escenas
consecutivos y detecta cuando la similitud cae por debajo de un umbral.
"""

import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np

from ...core.errors import NLPError, ErrorSeverity
from ...core.result import Result
from ..embeddings import get_embeddings_model

logger = logging.getLogger(__name__)


class CoherenceBreakType(Enum):
    """Tipos de saltos de coherencia detectados."""

    ABRUPT_TOPIC_CHANGE = "abrupt_topic_change"      # Cambio brusco de tema
    SCENE_DISCONTINUITY = "scene_discontinuity"      # Escena parece fuera de lugar
    TEMPORAL_JUMP = "temporal_jump"                  # Posible salto temporal no marcado
    POV_SHIFT = "pov_shift"                          # Posible cambio de POV no señalado
    TONAL_SHIFT = "tonal_shift"                      # Cambio de tono narrativo


class CoherenceSeverity(Enum):
    """Severidad del problema de coherencia."""

    HIGH = "high"          # Muy brusco, probable error
    MEDIUM = "medium"      # Notable, revisar
    LOW = "low"            # Leve, posiblemente intencional


@dataclass
class CoherenceBreak:
    """Un salto de coherencia detectado."""

    # Ubicación
    segment_before_idx: int            # Índice del segmento anterior
    segment_after_idx: int             # Índice del segmento posterior
    position_char: int                 # Posición aproximada en caracteres
    chapter_id: Optional[int] = None   # Capítulo donde ocurre

    # Contenido (extractos para contexto)
    text_before: str = ""              # Final del segmento anterior
    text_after: str = ""               # Inicio del segmento posterior

    # Análisis
    break_type: CoherenceBreakType = CoherenceBreakType.ABRUPT_TOPIC_CHANGE
    severity: CoherenceSeverity = CoherenceSeverity.MEDIUM
    similarity_score: float = 0.0      # Similitud medida (0-1)
    expected_similarity: float = 0.5   # Similitud esperada (umbral usado)

    # Contexto adicional
    confidence: float = 0.8
    explanation: str = ""

    def to_dict(self) -> dict:
        """Convertir a diccionario."""
        return {
            "segment_before_idx": self.segment_before_idx,
            "segment_after_idx": self.segment_after_idx,
            "position_char": self.position_char,
            "chapter_id": self.chapter_id,
            "text_before": self.text_before,
            "text_after": self.text_after,
            "break_type": self.break_type.value,
            "severity": self.severity.value,
            "similarity_score": self.similarity_score,
            "expected_similarity": self.expected_similarity,
            "confidence": self.confidence,
            "explanation": self.explanation,
        }


@dataclass
class CoherenceReport:
    """Resultado del análisis de coherencia."""

    breaks: list[CoherenceBreak] = field(default_factory=list)
    segments_analyzed: int = 0

    # Estadísticas
    avg_similarity: float = 0.0
    min_similarity: float = 1.0
    max_similarity: float = 0.0
    similarity_std: float = 0.0

    # Por severidad
    by_severity: dict[str, int] = field(default_factory=dict)
    by_type: dict[str, int] = field(default_factory=dict)

    def add_break(self, brk: CoherenceBreak) -> None:
        """Añadir un salto de coherencia."""
        self.breaks.append(brk)

        severity_key = brk.severity.value
        self.by_severity[severity_key] = self.by_severity.get(severity_key, 0) + 1

        type_key = brk.break_type.value
        self.by_type[type_key] = self.by_type.get(type_key, 0) + 1

    @property
    def total_breaks(self) -> int:
        return len(self.breaks)

    @property
    def high_severity_count(self) -> int:
        return self.by_severity.get("high", 0)

    def to_dict(self) -> dict:
        """Convertir a diccionario."""
        return {
            "breaks": [b.to_dict() for b in self.breaks],
            "segments_analyzed": self.segments_analyzed,
            "total_breaks": self.total_breaks,
            "avg_similarity": self.avg_similarity,
            "min_similarity": self.min_similarity,
            "max_similarity": self.max_similarity,
            "similarity_std": self.similarity_std,
            "by_severity": self.by_severity,
            "by_type": self.by_type,
        }


@dataclass
class CoherenceCheckError(NLPError):
    """Error durante el análisis de coherencia."""

    original_error: str = ""
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.RECOVERABLE, init=False)

    def __post_init__(self):
        self.message = f"Coherence check error: {self.original_error}"
        super().__post_init__()


class CoherenceDetector:
    """
    Detector de coherencia narrativa usando embeddings semánticos.

    Analiza la similitud entre segmentos consecutivos de texto para
    detectar saltos bruscos que podrían indicar problemas de edición
    o transiciones narrativas mal ejecutadas.
    """

    # Umbrales por defecto
    DEFAULT_SIMILARITY_THRESHOLD = 0.3    # Por debajo = posible salto
    DEFAULT_HIGH_SEVERITY_THRESHOLD = 0.15  # Muy bajo = probable error
    DEFAULT_MIN_SEGMENT_LENGTH = 50       # Caracteres mínimos por segmento
    DEFAULT_CONTEXT_CHARS = 200           # Caracteres de contexto a mostrar

    def __init__(
        self,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        high_severity_threshold: float = DEFAULT_HIGH_SEVERITY_THRESHOLD,
        min_segment_length: int = DEFAULT_MIN_SEGMENT_LENGTH,
    ):
        """
        Inicializar el detector.

        Args:
            similarity_threshold: Umbral de similitud para detectar saltos
            high_severity_threshold: Umbral para severidad alta
            min_segment_length: Longitud mínima de segmento para analizar
        """
        self._embeddings = None
        self.similarity_threshold = similarity_threshold
        self.high_severity_threshold = high_severity_threshold
        self.min_segment_length = min_segment_length

    def _load_embeddings(self) -> None:
        """Cargar modelo de embeddings si no está cargado."""
        if self._embeddings is None:
            try:
                self._embeddings = get_embeddings_model()
            except Exception as e:
                logger.warning(f"No se pudo cargar modelo de embeddings: {e}")
                raise

    def _segment_text(
        self,
        text: str,
        method: str = "paragraph"
    ) -> list[tuple[int, str]]:
        """
        Segmentar texto en unidades para análisis.

        Args:
            text: Texto completo
            method: "paragraph" | "sentence" | "window"

        Returns:
            Lista de (posición_inicio, texto_segmento)
        """
        segments = []

        if method == "paragraph":
            # Dividir por dobles saltos de línea (párrafos)
            current_pos = 0
            paragraphs = text.split("\n\n")

            for para in paragraphs:
                para = para.strip()
                if len(para) >= self.min_segment_length:
                    segments.append((current_pos, para))
                current_pos += len(para) + 2  # +2 por \n\n

        elif method == "sentence":
            # Dividir por oraciones (usar spaCy si disponible)
            try:
                from ..spacy_gpu import load_spacy_model
                nlp = load_spacy_model()
                doc = nlp(text)

                for sent in doc.sents:
                    if len(sent.text.strip()) >= self.min_segment_length:
                        segments.append((sent.start_char, sent.text.strip()))
            except Exception:
                # Fallback: dividir por puntos
                current_pos = 0
                for part in text.split(". "):
                    part = part.strip()
                    if len(part) >= self.min_segment_length:
                        segments.append((current_pos, part))
                    current_pos += len(part) + 2

        elif method == "window":
            # Ventanas deslizantes de tamaño fijo
            window_size = 500
            step = 250

            for i in range(0, len(text) - window_size, step):
                segment = text[i:i + window_size]
                segments.append((i, segment))

        return segments

    def _classify_break_type(
        self,
        text_before: str,
        text_after: str,
        similarity: float
    ) -> CoherenceBreakType:
        """
        Clasificar el tipo de salto de coherencia.

        Args:
            text_before: Texto antes del salto
            text_after: Texto después del salto
            similarity: Similitud medida

        Returns:
            Tipo de salto detectado
        """
        # Indicadores de cambio temporal
        temporal_markers = [
            "años después", "meses más tarde", "al día siguiente",
            "tiempo atrás", "hace mucho", "en el futuro",
            "mientras tanto", "en ese momento"
        ]

        # Indicadores de cambio de POV
        pov_change_before = any(p in text_before.lower() for p in ["yo ", "me ", "mi "])
        pov_change_after = any(p in text_after.lower() for p in ["él ", "ella ", "ellos "])

        # Detectar tipo
        if any(marker in text_after.lower() for marker in temporal_markers):
            return CoherenceBreakType.TEMPORAL_JUMP

        if pov_change_before != pov_change_after:
            return CoherenceBreakType.POV_SHIFT

        # Detectar cambio tonal (muy simplificado)
        exclamations_before = text_before.count("!") + text_before.count("?")
        exclamations_after = text_after.count("!") + text_after.count("?")

        if abs(exclamations_before - exclamations_after) > 3:
            return CoherenceBreakType.TONAL_SHIFT

        # Por defecto: cambio brusco de tema
        if similarity < 0.1:
            return CoherenceBreakType.SCENE_DISCONTINUITY

        return CoherenceBreakType.ABRUPT_TOPIC_CHANGE

    def detect(
        self,
        text: str,
        chapter_id: Optional[int] = None,
        segment_method: str = "paragraph",
        custom_threshold: Optional[float] = None,
    ) -> Result[CoherenceReport]:
        """
        Detectar saltos de coherencia en un texto.

        Args:
            text: Texto a analizar
            chapter_id: ID del capítulo (opcional)
            segment_method: Método de segmentación ("paragraph", "sentence", "window")
            custom_threshold: Umbral personalizado (sobrescribe el default)

        Returns:
            Result con CoherenceReport
        """
        if not text or len(text.strip()) < self.min_segment_length * 2:
            return Result.success(CoherenceReport())

        try:
            self._load_embeddings()
        except Exception as e:
            return Result.failure(
                CoherenceCheckError(original_error=str(e))
            )

        threshold = custom_threshold or self.similarity_threshold
        report = CoherenceReport()

        try:
            # Segmentar texto
            segments = self._segment_text(text, method=segment_method)
            report.segments_analyzed = len(segments)

            if len(segments) < 2:
                return Result.success(report)

            # Generar embeddings para todos los segmentos
            segment_texts = [s[1] for s in segments]
            embeddings = self._embeddings.encode(segment_texts, normalize=True)

            # Calcular similitudes entre segmentos consecutivos
            similarities = []

            for i in range(len(segments) - 1):
                # Similitud coseno (embeddings ya normalizados)
                sim = float(np.dot(embeddings[i], embeddings[i + 1]))
                similarities.append(sim)

                # Detectar salto si está por debajo del umbral
                if sim < threshold:
                    pos_before, text_before = segments[i]
                    pos_after, text_after = segments[i + 1]

                    # Determinar severidad
                    if sim < self.high_severity_threshold:
                        severity = CoherenceSeverity.HIGH
                    elif sim < threshold * 0.7:
                        severity = CoherenceSeverity.MEDIUM
                    else:
                        severity = CoherenceSeverity.LOW

                    # Clasificar tipo
                    break_type = self._classify_break_type(
                        text_before, text_after, sim
                    )

                    # Crear extractos de contexto
                    context_before = text_before[-self.DEFAULT_CONTEXT_CHARS:].strip()
                    context_after = text_after[:self.DEFAULT_CONTEXT_CHARS].strip()

                    # Generar explicación
                    explanation = self._generate_explanation(
                        break_type, severity, sim, threshold
                    )

                    brk = CoherenceBreak(
                        segment_before_idx=i,
                        segment_after_idx=i + 1,
                        position_char=pos_after,
                        chapter_id=chapter_id,
                        text_before=context_before,
                        text_after=context_after,
                        break_type=break_type,
                        severity=severity,
                        similarity_score=sim,
                        expected_similarity=threshold,
                        confidence=min(0.95, 1.0 - sim),
                        explanation=explanation,
                    )

                    report.add_break(brk)

            # Calcular estadísticas
            if similarities:
                report.avg_similarity = float(np.mean(similarities))
                report.min_similarity = float(np.min(similarities))
                report.max_similarity = float(np.max(similarities))
                report.similarity_std = float(np.std(similarities))

            return Result.success(report)

        except Exception as e:
            logger.error(f"Error en detección de coherencia: {e}")
            return Result.failure(
                CoherenceCheckError(original_error=str(e))
            )

    def detect_in_chapters(
        self,
        chapters: list[dict],
        segment_method: str = "paragraph",
    ) -> Result[CoherenceReport]:
        """
        Detectar saltos de coherencia en múltiples capítulos.

        Args:
            chapters: Lista de dicts con keys 'id', 'content', 'title'
            segment_method: Método de segmentación

        Returns:
            Result con CoherenceReport consolidado
        """
        combined_report = CoherenceReport()

        for chapter in chapters:
            chapter_id = chapter.get("id")
            content = chapter.get("content", "")

            if not content:
                continue

            result = self.detect(
                text=content,
                chapter_id=chapter_id,
                segment_method=segment_method,
            )

            if result.is_success:
                chapter_report = result.value
                combined_report.segments_analyzed += chapter_report.segments_analyzed

                for brk in chapter_report.breaks:
                    combined_report.add_break(brk)

        return Result.success(combined_report)

    def _generate_explanation(
        self,
        break_type: CoherenceBreakType,
        severity: CoherenceSeverity,
        similarity: float,
        threshold: float,
    ) -> str:
        """Generar explicación legible del salto detectado."""

        type_explanations = {
            CoherenceBreakType.ABRUPT_TOPIC_CHANGE:
                "Cambio brusco de tema entre párrafos",
            CoherenceBreakType.SCENE_DISCONTINUITY:
                "La escena parece no conectar con la anterior",
            CoherenceBreakType.TEMPORAL_JUMP:
                "Posible salto temporal no señalado claramente",
            CoherenceBreakType.POV_SHIFT:
                "Posible cambio de punto de vista narrativo",
            CoherenceBreakType.TONAL_SHIFT:
                "Cambio notable en el tono narrativo",
        }

        severity_notes = {
            CoherenceSeverity.HIGH: "Revisar urgentemente",
            CoherenceSeverity.MEDIUM: "Considerar añadir transición",
            CoherenceSeverity.LOW: "Posiblemente intencional",
        }

        base = type_explanations.get(break_type, "Salto de coherencia detectado")
        note = severity_notes.get(severity, "")

        return f"{base}. Similitud: {similarity:.0%} (umbral: {threshold:.0%}). {note}"


# Singleton thread-safe
_coherence_detector: Optional[CoherenceDetector] = None
_coherence_lock = threading.Lock()


def get_coherence_detector(
    similarity_threshold: float = CoherenceDetector.DEFAULT_SIMILARITY_THRESHOLD,
) -> CoherenceDetector:
    """
    Obtener detector de coherencia singleton.

    Args:
        similarity_threshold: Umbral de similitud

    Returns:
        Instancia de CoherenceDetector
    """
    global _coherence_detector

    if _coherence_detector is None:
        with _coherence_lock:
            if _coherence_detector is None:
                _coherence_detector = CoherenceDetector(
                    similarity_threshold=similarity_threshold
                )

    return _coherence_detector


def reset_coherence_detector():
    """Resetear singleton (para testing)."""
    global _coherence_detector
    with _coherence_lock:
        _coherence_detector = None
