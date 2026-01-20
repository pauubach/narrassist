"""
Analizador de ritmo narrativo (pacing).

Detecta problemas de ritmo como:
- Capítulos/escenas desproporcionadas
- Desequilibrios entre diálogo y narración
- Zonas de densidad léxica extrema
- Cambios abruptos de ritmo

Útil para correctores y editores que buscan
mantener un ritmo consistente y apropiado.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class PacingIssueType(Enum):
    """Tipos de problemas de ritmo detectables."""
    CHAPTER_TOO_SHORT = "chapter_too_short"
    CHAPTER_TOO_LONG = "chapter_too_long"
    UNBALANCED_CHAPTERS = "unbalanced_chapters"
    TOO_MUCH_DIALOGUE = "too_much_dialogue"
    TOO_LITTLE_DIALOGUE = "too_little_dialogue"
    DENSE_TEXT_BLOCK = "dense_text_block"
    SPARSE_TEXT_BLOCK = "sparse_text_block"
    RHYTHM_SHIFT = "rhythm_shift"
    SCENE_TOO_SHORT = "scene_too_short"
    SCENE_TOO_LONG = "scene_too_long"


class PacingSeverity(Enum):
    """Severidad del problema de ritmo."""
    INFO = "info"  # Observación, no necesariamente un problema
    SUGGESTION = "suggestion"  # Sugerencia de mejora
    WARNING = "warning"  # Problema potencial
    ISSUE = "issue"  # Problema claro


@dataclass
class PacingMetrics:
    """Métricas de ritmo para un segmento de texto."""
    segment_id: int
    segment_type: str  # "chapter", "scene", "paragraph"
    title: Optional[str] = None

    # Métricas básicas
    word_count: int = 0
    char_count: int = 0
    sentence_count: int = 0
    paragraph_count: int = 0

    # Diálogos
    dialogue_lines: int = 0
    dialogue_words: int = 0
    dialogue_ratio: float = 0.0  # % del texto que es diálogo

    # Densidad
    avg_sentence_length: float = 0.0
    avg_paragraph_length: float = 0.0
    lexical_density: float = 0.0  # Palabras únicas / total palabras

    # Acción vs descripción (estimación básica)
    action_verb_ratio: float = 0.0

    def to_dict(self) -> dict:
        """Convierte a diccionario."""
        return {
            "segment_id": self.segment_id,
            "segment_type": self.segment_type,
            "title": self.title,
            "word_count": self.word_count,
            "char_count": self.char_count,
            "sentence_count": self.sentence_count,
            "paragraph_count": self.paragraph_count,
            "dialogue_lines": self.dialogue_lines,
            "dialogue_words": self.dialogue_words,
            "dialogue_ratio": round(self.dialogue_ratio, 3),
            "avg_sentence_length": round(self.avg_sentence_length, 1),
            "avg_paragraph_length": round(self.avg_paragraph_length, 1),
            "lexical_density": round(self.lexical_density, 3),
            "action_verb_ratio": round(self.action_verb_ratio, 3),
        }


@dataclass
class PacingIssue:
    """Un problema de ritmo detectado."""
    issue_type: PacingIssueType
    severity: PacingSeverity
    segment_id: int
    segment_type: str
    title: Optional[str] = None

    description: str = ""
    explanation: str = ""
    suggestion: str = ""

    # Valores para contexto
    actual_value: float = 0.0
    expected_range: tuple = (0.0, 0.0)
    comparison_value: Optional[float] = None  # Media del documento

    def to_dict(self) -> dict:
        """Convierte a diccionario."""
        return {
            "issue_type": self.issue_type.value,
            "severity": self.severity.value,
            "segment_id": self.segment_id,
            "segment_type": self.segment_type,
            "title": self.title,
            "description": self.description,
            "explanation": self.explanation,
            "suggestion": self.suggestion,
            "actual_value": round(self.actual_value, 2),
            "expected_range": self.expected_range,
            "comparison_value": round(self.comparison_value, 2) if self.comparison_value else None,
        }


@dataclass
class PacingAnalysisResult:
    """Resultado del análisis de ritmo."""
    document_metrics: dict = field(default_factory=dict)
    chapter_metrics: list = field(default_factory=list)
    issues: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convierte a diccionario."""
        return {
            "document_metrics": self.document_metrics,
            "chapter_metrics": [m.to_dict() if hasattr(m, 'to_dict') else m for m in self.chapter_metrics],
            "issues": [i.to_dict() if hasattr(i, 'to_dict') else i for i in self.issues],
            "summary": self.summary,
        }


# Verbos de acción comunes en español
ACTION_VERBS = {
    'correr', 'saltar', 'golpear', 'lanzar', 'gritar', 'huir', 'perseguir',
    'luchar', 'atacar', 'defender', 'escapar', 'caer', 'subir', 'bajar',
    'empujar', 'tirar', 'agarrar', 'soltar', 'romper', 'abrir', 'cerrar',
    'entrar', 'salir', 'llegar', 'partir', 'arrancar', 'frenar', 'chocar',
    'disparar', 'apuñalar', 'matar', 'herir', 'sangrar', 'morir', 'nacer',
}


class PacingAnalyzer:
    """
    Analizador de ritmo narrativo.

    Umbrales configurables:
    - min_chapter_words: Mínimo palabras por capítulo (default: 500)
    - max_chapter_words: Máximo palabras por capítulo (default: 10000)
    - dialogue_ratio_range: Rango aceptable de % diálogo (default: 0.15-0.60)
    - chapter_variance_threshold: Varianza máxima entre capítulos (default: 2.0)
    """

    def __init__(
        self,
        min_chapter_words: int = 500,
        max_chapter_words: int = 10000,
        dialogue_ratio_range: tuple = (0.15, 0.60),
        chapter_variance_threshold: float = 2.0,
        dense_block_threshold: int = 500,  # Palabras sin diálogo
    ):
        self.min_chapter_words = min_chapter_words
        self.max_chapter_words = max_chapter_words
        self.dialogue_ratio_range = dialogue_ratio_range
        self.chapter_variance_threshold = chapter_variance_threshold
        self.dense_block_threshold = dense_block_threshold

    def analyze(
        self,
        chapters: list[dict],
        full_text: str = "",
    ) -> PacingAnalysisResult:
        """
        Analiza el ritmo narrativo de un documento.

        Args:
            chapters: Lista de diccionarios con 'number', 'title', 'content'
            full_text: Texto completo (opcional, para métricas globales)

        Returns:
            PacingAnalysisResult con métricas y problemas detectados
        """
        result = PacingAnalysisResult()

        if not chapters:
            return result

        # 1. Calcular métricas por capítulo
        all_metrics = []
        for ch in chapters:
            metrics = self._compute_metrics(
                text=ch.get("content", ""),
                segment_id=ch.get("number", 0),
                segment_type="chapter",
                title=ch.get("title", ""),
            )
            all_metrics.append(metrics)

        result.chapter_metrics = all_metrics

        # 2. Métricas del documento completo
        if full_text:
            doc_metrics = self._compute_metrics(
                text=full_text,
                segment_id=0,
                segment_type="document",
                title="Documento completo",
            )
            result.document_metrics = doc_metrics.to_dict()
        else:
            # Agregar métricas de capítulos
            result.document_metrics = self._aggregate_metrics(all_metrics)

        # 3. Detectar problemas
        issues = []

        # 3.1 Capítulos muy cortos/largos
        issues.extend(self._check_chapter_lengths(all_metrics))

        # 3.2 Desequilibrio entre capítulos
        issues.extend(self._check_chapter_balance(all_metrics))

        # 3.3 Ratio de diálogo
        issues.extend(self._check_dialogue_ratio(all_metrics))

        # 3.4 Bloques densos (mucho texto sin diálogo)
        issues.extend(self._check_dense_blocks(chapters))

        result.issues = issues

        # 4. Resumen
        result.summary = self._create_summary(all_metrics, issues)

        return result

    def _compute_metrics(
        self,
        text: str,
        segment_id: int,
        segment_type: str,
        title: str = "",
    ) -> PacingMetrics:
        """Calcula métricas de ritmo para un segmento de texto."""
        if not text:
            return PacingMetrics(
                segment_id=segment_id,
                segment_type=segment_type,
                title=title,
            )

        # Contar palabras
        words = re.findall(r'\b\w+\b', text.lower())
        word_count = len(words)
        unique_words = set(words)

        # Contar oraciones
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        sentence_count = len(sentences)

        # Contar párrafos
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        paragraph_count = len(paragraphs) or 1

        # Detectar diálogos
        dialogue_pattern = r'^[\s]*[—\-«"\'"].*?[»"\'"]?\s*$'
        dialogue_lines = []
        for para in paragraphs:
            if para.startswith(('—', '-', '«', '"', "'")):
                dialogue_lines.append(para)

        dialogue_words_count = sum(
            len(re.findall(r'\b\w+\b', line))
            for line in dialogue_lines
        )

        # Ratio de diálogo
        dialogue_ratio = dialogue_words_count / word_count if word_count > 0 else 0.0

        # Longitudes promedio
        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0.0
        avg_paragraph_length = word_count / paragraph_count if paragraph_count > 0 else 0.0

        # Densidad léxica
        lexical_density = len(unique_words) / word_count if word_count > 0 else 0.0

        # Ratio de verbos de acción
        action_count = sum(1 for w in words if w in ACTION_VERBS)
        action_verb_ratio = action_count / word_count if word_count > 0 else 0.0

        return PacingMetrics(
            segment_id=segment_id,
            segment_type=segment_type,
            title=title,
            word_count=word_count,
            char_count=len(text),
            sentence_count=sentence_count,
            paragraph_count=paragraph_count,
            dialogue_lines=len(dialogue_lines),
            dialogue_words=dialogue_words_count,
            dialogue_ratio=dialogue_ratio,
            avg_sentence_length=avg_sentence_length,
            avg_paragraph_length=avg_paragraph_length,
            lexical_density=lexical_density,
            action_verb_ratio=action_verb_ratio,
        )

    def _aggregate_metrics(self, metrics_list: list[PacingMetrics]) -> dict:
        """Agrega métricas de múltiples segmentos."""
        if not metrics_list:
            return {}

        total_words = sum(m.word_count for m in metrics_list)
        total_chars = sum(m.char_count for m in metrics_list)
        total_sentences = sum(m.sentence_count for m in metrics_list)
        total_paragraphs = sum(m.paragraph_count for m in metrics_list)
        total_dialogue_words = sum(m.dialogue_words for m in metrics_list)

        return {
            "total_words": total_words,
            "total_chars": total_chars,
            "total_sentences": total_sentences,
            "total_paragraphs": total_paragraphs,
            "total_chapters": len(metrics_list),
            "avg_chapter_words": total_words / len(metrics_list) if metrics_list else 0,
            "dialogue_ratio": total_dialogue_words / total_words if total_words > 0 else 0,
            "avg_sentence_length": total_words / total_sentences if total_sentences > 0 else 0,
        }

    def _check_chapter_lengths(self, metrics: list[PacingMetrics]) -> list[PacingIssue]:
        """Detecta capítulos demasiado cortos o largos."""
        issues = []

        for m in metrics:
            if m.word_count < self.min_chapter_words:
                issues.append(PacingIssue(
                    issue_type=PacingIssueType.CHAPTER_TOO_SHORT,
                    severity=PacingSeverity.WARNING,
                    segment_id=m.segment_id,
                    segment_type=m.segment_type,
                    title=m.title,
                    description=f"Capítulo {m.segment_id} tiene solo {m.word_count} palabras",
                    explanation=(
                        f"Los capítulos muy cortos ({m.word_count} palabras) pueden "
                        f"interrumpir el flujo narrativo o parecer incompletos."
                    ),
                    suggestion=(
                        "Considere expandir el contenido, fusionar con otro capítulo "
                        "o verificar si es intencional (ej: capítulo de transición)."
                    ),
                    actual_value=m.word_count,
                    expected_range=(self.min_chapter_words, self.max_chapter_words),
                ))

            elif m.word_count > self.max_chapter_words:
                issues.append(PacingIssue(
                    issue_type=PacingIssueType.CHAPTER_TOO_LONG,
                    severity=PacingSeverity.SUGGESTION,
                    segment_id=m.segment_id,
                    segment_type=m.segment_type,
                    title=m.title,
                    description=f"Capítulo {m.segment_id} tiene {m.word_count} palabras",
                    explanation=(
                        f"Los capítulos muy largos ({m.word_count} palabras) pueden "
                        f"cansar al lector o dificultar encontrar puntos de pausa."
                    ),
                    suggestion=(
                        "Considere dividir en dos capítulos si hay un punto de quiebre natural."
                    ),
                    actual_value=m.word_count,
                    expected_range=(self.min_chapter_words, self.max_chapter_words),
                ))

        return issues

    def _check_chapter_balance(self, metrics: list[PacingMetrics]) -> list[PacingIssue]:
        """Detecta desequilibrios entre capítulos."""
        issues = []

        if len(metrics) < 2:
            return issues

        word_counts = [m.word_count for m in metrics if m.word_count > 0]
        if not word_counts:
            return issues

        avg = sum(word_counts) / len(word_counts)
        if avg == 0:
            return issues

        for m in metrics:
            if m.word_count == 0:
                continue

            ratio = m.word_count / avg

            if ratio > self.chapter_variance_threshold:
                issues.append(PacingIssue(
                    issue_type=PacingIssueType.UNBALANCED_CHAPTERS,
                    severity=PacingSeverity.INFO,
                    segment_id=m.segment_id,
                    segment_type=m.segment_type,
                    title=m.title,
                    description=(
                        f"Capítulo {m.segment_id} es {ratio:.1f}x más largo que el promedio"
                    ),
                    explanation=(
                        f"Este capítulo ({m.word_count} palabras) es significativamente "
                        f"más largo que el promedio del libro ({avg:.0f} palabras)."
                    ),
                    suggestion="Verificar si el ritmo es intencional.",
                    actual_value=m.word_count,
                    comparison_value=avg,
                ))

            elif ratio < 1 / self.chapter_variance_threshold:
                issues.append(PacingIssue(
                    issue_type=PacingIssueType.UNBALANCED_CHAPTERS,
                    severity=PacingSeverity.INFO,
                    segment_id=m.segment_id,
                    segment_type=m.segment_type,
                    title=m.title,
                    description=(
                        f"Capítulo {m.segment_id} es {ratio:.1f}x más corto que el promedio"
                    ),
                    explanation=(
                        f"Este capítulo ({m.word_count} palabras) es significativamente "
                        f"más corto que el promedio del libro ({avg:.0f} palabras)."
                    ),
                    suggestion="Verificar si el ritmo es intencional.",
                    actual_value=m.word_count,
                    comparison_value=avg,
                ))

        return issues

    def _check_dialogue_ratio(self, metrics: list[PacingMetrics]) -> list[PacingIssue]:
        """Detecta capítulos con ratio de diálogo fuera de rango."""
        issues = []
        min_ratio, max_ratio = self.dialogue_ratio_range

        for m in metrics:
            if m.word_count < 100:  # Ignorar capítulos muy cortos
                continue

            if m.dialogue_ratio < min_ratio:
                issues.append(PacingIssue(
                    issue_type=PacingIssueType.TOO_LITTLE_DIALOGUE,
                    severity=PacingSeverity.INFO,
                    segment_id=m.segment_id,
                    segment_type=m.segment_type,
                    title=m.title,
                    description=(
                        f"Capítulo {m.segment_id}: solo {m.dialogue_ratio*100:.0f}% es diálogo"
                    ),
                    explanation=(
                        f"Este capítulo tiene muy poco diálogo ({m.dialogue_ratio*100:.0f}%). "
                        f"Mucha narración seguida puede ralentizar el ritmo."
                    ),
                    suggestion="Considere añadir diálogos para dinamizar.",
                    actual_value=m.dialogue_ratio,
                    expected_range=self.dialogue_ratio_range,
                ))

            elif m.dialogue_ratio > max_ratio:
                issues.append(PacingIssue(
                    issue_type=PacingIssueType.TOO_MUCH_DIALOGUE,
                    severity=PacingSeverity.INFO,
                    segment_id=m.segment_id,
                    segment_type=m.segment_type,
                    title=m.title,
                    description=(
                        f"Capítulo {m.segment_id}: {m.dialogue_ratio*100:.0f}% es diálogo"
                    ),
                    explanation=(
                        f"Este capítulo tiene mucho diálogo ({m.dialogue_ratio*100:.0f}%). "
                        f"Puede sentirse como un guión o carecer de contexto."
                    ),
                    suggestion="Considere añadir narración, acotaciones o descripciones.",
                    actual_value=m.dialogue_ratio,
                    expected_range=self.dialogue_ratio_range,
                ))

        return issues

    def _check_dense_blocks(self, chapters: list[dict]) -> list[PacingIssue]:
        """Detecta bloques de texto muy densos (sin diálogo)."""
        issues = []

        for ch in chapters:
            content = ch.get("content", "")
            chapter_num = ch.get("number", 0)

            if not content:
                continue

            # Dividir en párrafos
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

            # Buscar secuencias largas sin diálogo
            consecutive_narrative = 0
            narrative_words = 0

            for i, para in enumerate(paragraphs):
                is_dialogue = para.startswith(('—', '-', '«', '"', "'"))

                if is_dialogue:
                    # Resetear contador
                    if narrative_words > self.dense_block_threshold:
                        issues.append(PacingIssue(
                            issue_type=PacingIssueType.DENSE_TEXT_BLOCK,
                            severity=PacingSeverity.SUGGESTION,
                            segment_id=chapter_num,
                            segment_type="chapter",
                            title=ch.get("title", ""),
                            description=(
                                f"Cap. {chapter_num}: Bloque de {narrative_words} palabras "
                                f"sin diálogo"
                            ),
                            explanation=(
                                f"Hay un bloque de {consecutive_narrative} párrafos "
                                f"({narrative_words} palabras) sin diálogo. "
                                f"Esto puede hacer la lectura densa."
                            ),
                            suggestion="Considere intercalar diálogos o dividir en escenas.",
                            actual_value=narrative_words,
                            expected_range=(0, self.dense_block_threshold),
                        ))
                    consecutive_narrative = 0
                    narrative_words = 0
                else:
                    consecutive_narrative += 1
                    narrative_words += len(re.findall(r'\b\w+\b', para))

            # Verificar al final del capítulo
            if narrative_words > self.dense_block_threshold:
                issues.append(PacingIssue(
                    issue_type=PacingIssueType.DENSE_TEXT_BLOCK,
                    severity=PacingSeverity.SUGGESTION,
                    segment_id=chapter_num,
                    segment_type="chapter",
                    title=ch.get("title", ""),
                    description=(
                        f"Cap. {chapter_num}: Bloque final de {narrative_words} palabras "
                        f"sin diálogo"
                    ),
                    explanation=(
                        f"El capítulo termina con {consecutive_narrative} párrafos "
                        f"({narrative_words} palabras) sin diálogo."
                    ),
                    suggestion="Considere si es intencional como cierre descriptivo.",
                    actual_value=narrative_words,
                    expected_range=(0, self.dense_block_threshold),
                ))

        return issues

    def _create_summary(
        self,
        metrics: list[PacingMetrics],
        issues: list[PacingIssue],
    ) -> dict:
        """Crea resumen del análisis de ritmo."""
        if not metrics:
            return {}

        word_counts = [m.word_count for m in metrics]
        dialogue_ratios = [m.dialogue_ratio for m in metrics if m.word_count > 100]

        return {
            "total_chapters": len(metrics),
            "total_words": sum(word_counts),
            "avg_chapter_words": sum(word_counts) / len(metrics),
            "min_chapter_words": min(word_counts),
            "max_chapter_words": max(word_counts),
            "chapter_word_variance": max(word_counts) / min(word_counts) if min(word_counts) > 0 else 0,
            "avg_dialogue_ratio": sum(dialogue_ratios) / len(dialogue_ratios) if dialogue_ratios else 0,
            "issues_count": len(issues),
            "issues_by_type": {
                t.value: sum(1 for i in issues if i.issue_type == t)
                for t in PacingIssueType
            },
            "issues_by_severity": {
                s.value: sum(1 for i in issues if i.severity == s)
                for s in PacingSeverity
            },
        }


def analyze_pacing(
    chapters: list[dict],
    full_text: str = "",
    **kwargs,
) -> PacingAnalysisResult:
    """
    Función de conveniencia para analizar ritmo narrativo.

    Args:
        chapters: Lista de capítulos con 'number', 'title', 'content'
        full_text: Texto completo del documento (opcional)
        **kwargs: Parámetros para PacingAnalyzer

    Returns:
        PacingAnalysisResult
    """
    analyzer = PacingAnalyzer(**kwargs)
    return analyzer.analyze(chapters, full_text)


# Singleton para uso global
_pacing_analyzer: Optional[PacingAnalyzer] = None
_lock = __import__("threading").Lock()


def get_pacing_analyzer(**kwargs) -> PacingAnalyzer:
    """Obtiene o crea el analizador de ritmo singleton."""
    global _pacing_analyzer
    if _pacing_analyzer is None:
        with _lock:
            if _pacing_analyzer is None:
                _pacing_analyzer = PacingAnalyzer(**kwargs)
    return _pacing_analyzer
