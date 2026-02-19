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
    title: str | None = None

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
    title: str | None = None

    description: str = ""
    explanation: str = ""
    suggestion: str = ""

    # Valores para contexto
    actual_value: float = 0.0
    expected_range: tuple = (0.0, 0.0)
    comparison_value: float | None = None  # Media del documento

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
            "chapter_metrics": [
                m.to_dict() if hasattr(m, "to_dict") else m for m in self.chapter_metrics
            ],
            "issues": [i.to_dict() if hasattr(i, "to_dict") else i for i in self.issues],
            "summary": self.summary,
        }


# Verbos de acción comunes en español
ACTION_VERBS = {
    "correr",
    "saltar",
    "golpear",
    "lanzar",
    "gritar",
    "huir",
    "perseguir",
    "luchar",
    "atacar",
    "defender",
    "escapar",
    "caer",
    "subir",
    "bajar",
    "empujar",
    "tirar",
    "agarrar",
    "soltar",
    "romper",
    "abrir",
    "cerrar",
    "entrar",
    "salir",
    "llegar",
    "partir",
    "arrancar",
    "frenar",
    "chocar",
    "disparar",
    "apuñalar",
    "matar",
    "herir",
    "sangrar",
    "morir",
    "nacer",
}


@dataclass
class GenreBenchmarks:
    """Benchmarks de referencia para un género literario."""

    genre_code: str
    genre_label: str
    min_chapter_words: int
    max_chapter_words: int
    dialogue_ratio_range: tuple[float, float]
    avg_sentence_length_range: tuple[float, float]
    avg_tension: tuple[float, float]  # Rango típico de tensión media
    expected_arc_types: list[str]  # Tipos de arco típicos del género
    chapter_variance_threshold: float
    dense_block_threshold: int
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "genre_code": self.genre_code,
            "genre_label": self.genre_label,
            "min_chapter_words": self.min_chapter_words,
            "max_chapter_words": self.max_chapter_words,
            "dialogue_ratio_range": list(self.dialogue_ratio_range),
            "avg_sentence_length_range": list(self.avg_sentence_length_range),
            "avg_tension": list(self.avg_tension),
            "expected_arc_types": self.expected_arc_types,
            "chapter_variance_threshold": self.chapter_variance_threshold,
            "dense_block_threshold": self.dense_block_threshold,
            "notes": self.notes,
        }


# Benchmarks de referencia por género literario
# Basados en análisis de convenciones editoriales y guías de estilo
GENRE_BENCHMARKS: dict[str, GenreBenchmarks] = {
    "FIC": GenreBenchmarks(
        genre_code="FIC",
        genre_label="Ficción narrativa",
        min_chapter_words=800,
        max_chapter_words=8000,
        dialogue_ratio_range=(0.20, 0.55),
        avg_sentence_length_range=(12.0, 22.0),
        avg_tension=(0.35, 0.65),
        expected_arc_types=["mountain", "wave", "rising"],
        chapter_variance_threshold=2.0,
        dense_block_threshold=500,
        notes="Equilibrio entre narración y diálogo. Arco clásico esperado.",
    ),
    "MEM": GenreBenchmarks(
        genre_code="MEM",
        genre_label="Memorias / Autobiografía",
        min_chapter_words=1000,
        max_chapter_words=10000,
        dialogue_ratio_range=(0.05, 0.35),
        avg_sentence_length_range=(15.0, 28.0),
        avg_tension=(0.20, 0.50),
        expected_arc_types=["wave", "rising", "mountain"],
        chapter_variance_threshold=2.5,
        dense_block_threshold=700,
        notes="Predomina la narración reflexiva. Capítulos más largos.",
    ),
    "BIO": GenreBenchmarks(
        genre_code="BIO",
        genre_label="Biografía",
        min_chapter_words=1500,
        max_chapter_words=12000,
        dialogue_ratio_range=(0.05, 0.30),
        avg_sentence_length_range=(16.0, 28.0),
        avg_tension=(0.20, 0.45),
        expected_arc_types=["rising", "mountain", "wave"],
        chapter_variance_threshold=2.5,
        dense_block_threshold=800,
        notes="Narración expositiva predominante con citas ocasionales.",
    ),
    "CEL": GenreBenchmarks(
        genre_code="CEL",
        genre_label="Libro de famosos / Influencer",
        min_chapter_words=500,
        max_chapter_words=5000,
        dialogue_ratio_range=(0.10, 0.40),
        avg_sentence_length_range=(10.0, 20.0),
        avg_tension=(0.30, 0.55),
        expected_arc_types=["wave", "mountain"],
        chapter_variance_threshold=2.0,
        dense_block_threshold=400,
        notes="Capítulos cortos y dinámicos. Lenguaje accesible.",
    ),
    "DIV": GenreBenchmarks(
        genre_code="DIV",
        genre_label="Divulgación",
        min_chapter_words=1500,
        max_chapter_words=12000,
        dialogue_ratio_range=(0.0, 0.15),
        avg_sentence_length_range=(18.0, 30.0),
        avg_tension=(0.15, 0.40),
        expected_arc_types=["rising", "flat", "wave"],
        chapter_variance_threshold=2.0,
        dense_block_threshold=1000,
        notes="Prosa expositiva densa. Poco o nulo diálogo.",
    ),
    "ENS": GenreBenchmarks(
        genre_code="ENS",
        genre_label="Ensayo",
        min_chapter_words=1500,
        max_chapter_words=15000,
        dialogue_ratio_range=(0.0, 0.10),
        avg_sentence_length_range=(20.0, 35.0),
        avg_tension=(0.15, 0.35),
        expected_arc_types=["rising", "mountain", "flat"],
        chapter_variance_threshold=3.0,
        dense_block_threshold=1200,
        notes="Prosa académica con oraciones largas. Alta densidad léxica.",
    ),
    "AUT": GenreBenchmarks(
        genre_code="AUT",
        genre_label="Autoayuda",
        min_chapter_words=800,
        max_chapter_words=6000,
        dialogue_ratio_range=(0.05, 0.25),
        avg_sentence_length_range=(10.0, 20.0),
        avg_tension=(0.25, 0.50),
        expected_arc_types=["rising", "mountain", "wave"],
        chapter_variance_threshold=1.8,
        dense_block_threshold=500,
        notes="Capítulos regulares, lenguaje directo. Incluye ejercicios y anécdotas.",
    ),
    "TEC": GenreBenchmarks(
        genre_code="TEC",
        genre_label="Manual técnico",
        min_chapter_words=500,
        max_chapter_words=8000,
        dialogue_ratio_range=(0.0, 0.05),
        avg_sentence_length_range=(14.0, 25.0),
        avg_tension=(0.10, 0.25),
        expected_arc_types=["flat", "rising"],
        chapter_variance_threshold=3.0,
        dense_block_threshold=1500,
        notes="Prosa técnica sin diálogo. Ritmo uniforme.",
    ),
    "PRA": GenreBenchmarks(
        genre_code="PRA",
        genre_label="Libro práctico (cocina, DIY)",
        min_chapter_words=300,
        max_chapter_words=4000,
        dialogue_ratio_range=(0.0, 0.10),
        avg_sentence_length_range=(8.0, 18.0),
        avg_tension=(0.15, 0.35),
        expected_arc_types=["flat", "wave"],
        chapter_variance_threshold=3.0,
        dense_block_threshold=600,
        notes="Secciones cortas con instrucciones. Oraciones concisas.",
    ),
    "INF": GenreBenchmarks(
        genre_code="INF",
        genre_label="Infantil / Juvenil",
        min_chapter_words=200,
        max_chapter_words=3000,
        dialogue_ratio_range=(0.25, 0.65),
        avg_sentence_length_range=(8.0, 16.0),
        avg_tension=(0.35, 0.70),
        expected_arc_types=["mountain", "wave"],
        chapter_variance_threshold=2.0,
        dense_block_threshold=300,
        notes="Capítulos cortos, mucho diálogo, oraciones simples.",
    ),
    "DRA": GenreBenchmarks(
        genre_code="DRA",
        genre_label="Teatro / Guion",
        min_chapter_words=200,
        max_chapter_words=5000,
        dialogue_ratio_range=(0.60, 0.95),
        avg_sentence_length_range=(6.0, 15.0),
        avg_tension=(0.40, 0.75),
        expected_arc_types=["mountain", "rising", "wave"],
        chapter_variance_threshold=2.5,
        dense_block_threshold=200,
        notes="Dominado por diálogo. Acotaciones breves.",
    ),
    "GRA": GenreBenchmarks(
        genre_code="GRA",
        genre_label="Novela gráfica / Cómic",
        min_chapter_words=100,
        max_chapter_words=2000,
        dialogue_ratio_range=(0.30, 0.80),
        avg_sentence_length_range=(5.0, 12.0),
        avg_tension=(0.40, 0.70),
        expected_arc_types=["mountain", "wave"],
        chapter_variance_threshold=2.0,
        dense_block_threshold=200,
        notes="Texto breve. Alta proporción de diálogo en bocadillos.",
    ),
}


def get_genre_benchmarks(genre_code: str) -> GenreBenchmarks | None:
    """Obtiene los benchmarks para un género dado."""
    return GENRE_BENCHMARKS.get(genre_code)


def compute_percentile_rank(value: float, range_min: float, range_max: float) -> int:
    """
    Calcula el percentil aproximado de un valor dentro de un rango de referencia.

    El rango (min, max) se interpreta como P10-P90 del género.
    Valores fuera del rango se extrapolan hasta P0/P100.

    Returns:
        Percentil estimado (0-100).
    """
    if range_max <= range_min:
        return 50
    # El rango min..max cubre P10..P90 (80% de la distribución)
    # Normalizamos: 0.0 = range_min (P10), 1.0 = range_max (P90)
    normalized = (value - range_min) / (range_max - range_min)
    # Mapear [0, 1] -> [10, 90], con extrapolación fuera
    percentile = 10 + normalized * 80
    return max(0, min(100, round(percentile)))


def compare_with_benchmarks(
    metrics: dict,
    genre_code: str,
) -> dict | None:
    """
    Compara las métricas de un documento contra los benchmarks de su género.

    Args:
        metrics: Diccionario con métricas globales del documento
        genre_code: Código del género (FIC, MEM, TEC, etc.)

    Returns:
        Diccionario con comparación o None si el género no tiene benchmarks
    """
    benchmarks = GENRE_BENCHMARKS.get(genre_code)
    if not benchmarks:
        return None

    deviations = []

    # Comparar longitud de capítulos
    avg_words = metrics.get("avg_chapter_words", 0)
    if avg_words > 0:
        if avg_words < benchmarks.min_chapter_words:
            deviations.append(
                {
                    "metric": "avg_chapter_words",
                    "label": "Longitud media de capítulo",
                    "actual": round(avg_words),
                    "expected_range": [benchmarks.min_chapter_words, benchmarks.max_chapter_words],
                    "status": "below",
                    "message": f"Los capítulos son cortos para {benchmarks.genre_label} "
                    f"(media {round(avg_words)} vs mínimo {benchmarks.min_chapter_words})",
                }
            )
        elif avg_words > benchmarks.max_chapter_words:
            deviations.append(
                {
                    "metric": "avg_chapter_words",
                    "label": "Longitud media de capítulo",
                    "actual": round(avg_words),
                    "expected_range": [benchmarks.min_chapter_words, benchmarks.max_chapter_words],
                    "status": "above",
                    "message": f"Los capítulos son largos para {benchmarks.genre_label} "
                    f"(media {round(avg_words)} vs máximo {benchmarks.max_chapter_words})",
                }
            )

    # Comparar ratio de diálogo
    dialogue_ratio = metrics.get("dialogue_ratio", -1)
    if dialogue_ratio >= 0:
        low, high = benchmarks.dialogue_ratio_range
        if dialogue_ratio < low:
            deviations.append(
                {
                    "metric": "dialogue_ratio",
                    "label": "Ratio de diálogo",
                    "actual": round(dialogue_ratio, 3),
                    "expected_range": [low, high],
                    "status": "below",
                    "message": f"Poco diálogo para {benchmarks.genre_label} "
                    f"({round(dialogue_ratio * 100, 1)}% vs {round(low * 100)}%-{round(high * 100)}%)",
                }
            )
        elif dialogue_ratio > high:
            deviations.append(
                {
                    "metric": "dialogue_ratio",
                    "label": "Ratio de diálogo",
                    "actual": round(dialogue_ratio, 3),
                    "expected_range": [low, high],
                    "status": "above",
                    "message": f"Mucho diálogo para {benchmarks.genre_label} "
                    f"({round(dialogue_ratio * 100, 1)}% vs {round(low * 100)}%-{round(high * 100)}%)",
                }
            )

    # Comparar longitud de oraciones
    avg_sent_len = metrics.get("avg_sentence_length", 0)
    if avg_sent_len > 0:
        low, high = benchmarks.avg_sentence_length_range
        if avg_sent_len < low:
            deviations.append(
                {
                    "metric": "avg_sentence_length",
                    "label": "Longitud media de oración",
                    "actual": round(avg_sent_len, 1),
                    "expected_range": [low, high],
                    "status": "below",
                    "message": f"Oraciones cortas para {benchmarks.genre_label} "
                    f"({round(avg_sent_len, 1)} vs {low}-{high} palabras)",
                }
            )
        elif avg_sent_len > high:
            deviations.append(
                {
                    "metric": "avg_sentence_length",
                    "label": "Longitud media de oración",
                    "actual": round(avg_sent_len, 1),
                    "expected_range": [low, high],
                    "status": "above",
                    "message": f"Oraciones largas para {benchmarks.genre_label} "
                    f"({round(avg_sent_len, 1)} vs {low}-{high} palabras)",
                }
            )

    # Comparar tensión media
    avg_tension = metrics.get("avg_tension")
    if avg_tension is not None:
        low, high = benchmarks.avg_tension
        tension_status = "within"
        if avg_tension < low:
            tension_status = "below"
        elif avg_tension > high:
            tension_status = "above"
        if tension_status != "within":
            deviations.append(
                {
                    "metric": "avg_tension",
                    "label": "Tensión narrativa media",
                    "actual": round(avg_tension, 3),
                    "expected_range": [low, high],
                    "status": tension_status,
                    "message": f"Tensión {'baja' if tension_status == 'below' else 'alta'} "
                    f"para {benchmarks.genre_label} "
                    f"({round(avg_tension, 2)} vs {low}-{high})",
                }
            )

    # Comparar arco narrativo
    arc_type = metrics.get("tension_arc_type", "")
    arc_match = arc_type in benchmarks.expected_arc_types if arc_type else None

    if arc_type and not arc_match:
        deviations.append(
            {
                "metric": "tension_arc_type",
                "label": "Tipo de arco narrativo",
                "actual": arc_type,
                "expected": benchmarks.expected_arc_types,
                "status": "mismatch",
                "message": f"El arco narrativo '{arc_type}' no es habitual en {benchmarks.genre_label} "
                f"(esperados: {', '.join(benchmarks.expected_arc_types)})",
            }
        )

    # Calcular percentiles para todas las métricas numéricas
    percentiles: dict[str, int] = {}
    if avg_words > 0:
        percentiles["avg_chapter_words"] = compute_percentile_rank(
            avg_words, benchmarks.min_chapter_words, benchmarks.max_chapter_words
        )
    if dialogue_ratio >= 0:
        low, high = benchmarks.dialogue_ratio_range
        percentiles["dialogue_ratio"] = compute_percentile_rank(dialogue_ratio, low, high)
    if avg_sent_len > 0:
        low, high = benchmarks.avg_sentence_length_range
        percentiles["avg_sentence_length"] = compute_percentile_rank(avg_sent_len, low, high)
    if avg_tension is not None:
        low, high = benchmarks.avg_tension
        percentiles["avg_tension"] = compute_percentile_rank(avg_tension, low, high)

    # Añadir percentil a cada desviación numérica
    for dev in deviations:
        metric = dev.get("metric", "")
        if metric in percentiles:
            dev["percentile_rank"] = percentiles[metric]

    # Generar sugerencias accionables a partir de las desviaciones
    suggestions = _generate_pacing_suggestions(deviations, benchmarks, arc_type, arc_match)

    return {
        "genre": benchmarks.to_dict(),
        "deviations": deviations,
        "deviation_count": len(deviations),
        "arc_type_match": arc_match,
        "arc_type_expected": benchmarks.expected_arc_types,
        "arc_type_actual": arc_type,
        "suggestions": suggestions,
        "percentiles": percentiles,
    }


def _generate_pacing_suggestions(
    deviations: list[dict],
    benchmarks: GenreBenchmarks,
    arc_type: str,
    arc_match: bool | None,
) -> list[dict]:
    """
    Genera sugerencias de corrección basadas en las desviaciones detectadas.

    Args:
        deviations: Lista de desviaciones encontradas
        benchmarks: Benchmarks del género
        arc_type: Tipo de arco narrativo detectado
        arc_match: Si el arco coincide con los esperados

    Returns:
        Lista de sugerencias con prioridad y texto
    """
    suggestions = []

    for dev in deviations:
        metric = dev["metric"]
        status = dev["status"]

        if metric == "avg_chapter_words":
            if status == "below":
                suggestions.append(
                    {
                        "metric": metric,
                        "priority": "medium",
                        "suggestion": f"Los capítulos son más cortos de lo habitual en {benchmarks.genre_label}. "
                        f"Considere desarrollar más las escenas, añadir descripciones "
                        f"o contextualización para alcanzar al menos {benchmarks.min_chapter_words} palabras.",
                    }
                )
            else:
                suggestions.append(
                    {
                        "metric": metric,
                        "priority": "medium",
                        "suggestion": f"Los capítulos son más largos de lo habitual en {benchmarks.genre_label}. "
                        f"Considere dividir capítulos extensos en secciones o capítulos más cortos "
                        f"para mantener el ritmo del lector.",
                    }
                )

        elif metric == "dialogue_ratio":
            if status == "below":
                low_pct = round(benchmarks.dialogue_ratio_range[0] * 100)
                suggestions.append(
                    {
                        "metric": metric,
                        "priority": "medium",
                        "suggestion": f"El manuscrito tiene poco diálogo para {benchmarks.genre_label}. "
                        f"Convertir pasajes narrativos en escenas dialogadas puede "
                        f"dinamizar el ritmo. Referencia: al menos {low_pct}% de diálogo.",
                    }
                )
            else:
                high_pct = round(benchmarks.dialogue_ratio_range[1] * 100)
                suggestions.append(
                    {
                        "metric": metric,
                        "priority": "low",
                        "suggestion": f"El manuscrito tiene mucho diálogo para {benchmarks.genre_label}. "
                        f"Intercalar más narración, descripción o reflexión entre diálogos "
                        f"puede equilibrar el ritmo. Referencia: máximo {high_pct}%.",
                    }
                )

        elif metric == "avg_sentence_length":
            if status == "below":
                suggestions.append(
                    {
                        "metric": metric,
                        "priority": "low",
                        "suggestion": f"Las oraciones son cortas para {benchmarks.genre_label}. "
                        f"Combinar oraciones simples con coordinación o subordinación "
                        f"puede dar mayor fluidez y complejidad al texto.",
                    }
                )
            else:
                suggestions.append(
                    {
                        "metric": metric,
                        "priority": "medium",
                        "suggestion": f"Las oraciones son largas para {benchmarks.genre_label}. "
                        f"Dividir oraciones complejas en dos o tres más simples "
                        f"facilita la lectura y mejora la claridad.",
                    }
                )

        elif metric == "avg_tension":
            if status == "below":
                suggestions.append(
                    {
                        "metric": metric,
                        "priority": "high",
                        "suggestion": f"La tensión narrativa es baja para {benchmarks.genre_label}. "
                        f"Introducir conflictos, preguntas sin respuesta o situaciones "
                        f"de urgencia puede aumentar el interés del lector.",
                    }
                )
            else:
                suggestions.append(
                    {
                        "metric": metric,
                        "priority": "low",
                        "suggestion": f"La tensión narrativa es alta para {benchmarks.genre_label}. "
                        f"Incluir momentos de calma, reflexión o descanso narrativo "
                        f"evita la fatiga del lector y da más impacto a los clímax.",
                    }
                )

        elif metric == "tension_arc_type":
            expected = ", ".join(benchmarks.expected_arc_types)
            suggestions.append(
                {
                    "metric": metric,
                    "priority": "low",
                    "suggestion": f"El arco de tensión '{arc_type}' difiere de los habituales "
                    f"en {benchmarks.genre_label} ({expected}). Esto no es necesariamente "
                    f"un problema, pero revise que la estructura sirve a la intención narrativa.",
                }
            )

    return suggestions


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
        words = re.findall(r"\b\w+\b", text.lower())
        word_count = len(words)
        unique_words = set(words)

        # Contar oraciones
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        sentence_count = len(sentences)

        # Contar párrafos
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        paragraph_count = len(paragraphs) or 1

        # Detectar diálogos
        dialogue_lines = []
        for para in paragraphs:
            if para.startswith(("—", "-", "«", '"', "'")):
                dialogue_lines.append(para)

        dialogue_words_count = sum(len(re.findall(r"\b\w+\b", line)) for line in dialogue_lines)

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
                issues.append(
                    PacingIssue(
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
                    )
                )

            elif m.word_count > self.max_chapter_words:
                issues.append(
                    PacingIssue(
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
                    )
                )

        return issues

    def _check_chapter_balance(self, metrics: list[PacingMetrics]) -> list[PacingIssue]:
        """Detecta desequilibrios entre capítulos."""
        issues: list[PacingIssue] = []

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
                issues.append(
                    PacingIssue(
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
                    )
                )

            elif ratio < 1 / self.chapter_variance_threshold:
                issues.append(
                    PacingIssue(
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
                    )
                )

        return issues

    def _check_dialogue_ratio(self, metrics: list[PacingMetrics]) -> list[PacingIssue]:
        """Detecta capítulos con ratio de diálogo fuera de rango."""
        issues = []
        min_ratio, max_ratio = self.dialogue_ratio_range

        for m in metrics:
            if m.word_count < 100:  # Ignorar capítulos muy cortos
                continue

            if m.dialogue_ratio < min_ratio:
                issues.append(
                    PacingIssue(
                        issue_type=PacingIssueType.TOO_LITTLE_DIALOGUE,
                        severity=PacingSeverity.INFO,
                        segment_id=m.segment_id,
                        segment_type=m.segment_type,
                        title=m.title,
                        description=(
                            f"Capítulo {m.segment_id}: solo {m.dialogue_ratio * 100:.0f}% es diálogo"
                        ),
                        explanation=(
                            f"Este capítulo tiene muy poco diálogo ({m.dialogue_ratio * 100:.0f}%). "
                            f"Mucha narración seguida puede ralentizar el ritmo."
                        ),
                        suggestion="Considere añadir diálogos para dinamizar.",
                        actual_value=m.dialogue_ratio,
                        expected_range=self.dialogue_ratio_range,
                    )
                )

            elif m.dialogue_ratio > max_ratio:
                issues.append(
                    PacingIssue(
                        issue_type=PacingIssueType.TOO_MUCH_DIALOGUE,
                        severity=PacingSeverity.INFO,
                        segment_id=m.segment_id,
                        segment_type=m.segment_type,
                        title=m.title,
                        description=(
                            f"Capítulo {m.segment_id}: {m.dialogue_ratio * 100:.0f}% es diálogo"
                        ),
                        explanation=(
                            f"Este capítulo tiene mucho diálogo ({m.dialogue_ratio * 100:.0f}%). "
                            f"Puede sentirse como un guión o carecer de contexto."
                        ),
                        suggestion="Considere añadir narración, acotaciones o descripciones.",
                        actual_value=m.dialogue_ratio,
                        expected_range=self.dialogue_ratio_range,
                    )
                )

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
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

            # Buscar secuencias largas sin diálogo
            consecutive_narrative = 0
            narrative_words = 0

            for _i, para in enumerate(paragraphs):
                is_dialogue = para.startswith(("—", "-", "«", '"', "'"))

                if is_dialogue:
                    # Resetear contador
                    if narrative_words > self.dense_block_threshold:
                        issues.append(
                            PacingIssue(
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
                            )
                        )
                    consecutive_narrative = 0
                    narrative_words = 0
                else:
                    consecutive_narrative += 1
                    narrative_words += len(re.findall(r"\b\w+\b", para))

            # Verificar al final del capítulo
            if narrative_words > self.dense_block_threshold:
                issues.append(
                    PacingIssue(
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
                    )
                )

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
            "chapter_word_variance": max(word_counts) / min(word_counts)
            if min(word_counts) > 0
            else 0,
            "avg_dialogue_ratio": sum(dialogue_ratios) / len(dialogue_ratios)
            if dialogue_ratios
            else 0,
            "issues_count": len(issues),
            "issues_by_type": {
                t.value: sum(1 for i in issues if i.issue_type == t) for t in PacingIssueType
            },
            "issues_by_severity": {
                s.value: sum(1 for i in issues if i.severity == s) for s in PacingSeverity
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
_pacing_analyzer: PacingAnalyzer | None = None
_lock = __import__("threading").Lock()


def get_pacing_analyzer(**kwargs) -> PacingAnalyzer:
    """Obtiene o crea el analizador de ritmo singleton."""
    global _pacing_analyzer
    if _pacing_analyzer is None:
        with _lock:
            if _pacing_analyzer is None:
                _pacing_analyzer = PacingAnalyzer(**kwargs)
    return _pacing_analyzer


@dataclass
class TensionPoint:
    """Un punto en la curva de tensión narrativa."""

    chapter: int
    title: str
    tension_score: float  # 0.0-1.0
    components: dict  # Desglose de factores que contribuyen
    word_count: int
    position_ratio: float  # 0.0-1.0, posición relativa en el documento

    def to_dict(self) -> dict:
        return {
            "chapter": self.chapter,
            "title": self.title,
            "tension_score": round(self.tension_score, 3),
            "components": {k: round(v, 3) for k, v in self.components.items()},
            "word_count": self.word_count,
            "position_ratio": round(self.position_ratio, 3),
        }


@dataclass
class TensionCurve:
    """Curva de tensión narrativa completa."""

    points: list[TensionPoint]
    avg_tension: float = 0.0
    max_tension: float = 0.0
    min_tension: float = 0.0
    tension_arc_type: str = ""  # rising, falling, mountain, valley, flat, wave

    def to_dict(self) -> dict:
        return {
            "points": [p.to_dict() for p in self.points],
            "avg_tension": round(self.avg_tension, 3),
            "max_tension": round(self.max_tension, 3),
            "min_tension": round(self.min_tension, 3),
            "tension_arc_type": self.tension_arc_type,
        }


def compute_tension_curve(
    chapters: list[dict],
    full_text: str = "",
) -> TensionCurve:
    """
    Calcula la curva de tensión narrativa del documento.

    La tensión se estima a partir de señales textuales:
    - Densidad de verbos de acción (más acción = más tensión)
    - Longitud de oraciones (oraciones cortas = más tensión)
    - Ratio de diálogo (diálogo intenso puede indicar conflicto)
    - Signos de puntuación expresivos (!, ?) = más tensión
    - Longitud de párrafos (párrafos cortos = ritmo más rápido)

    Args:
        chapters: Lista de capítulos con 'number', 'title', 'content'
        full_text: Texto completo del documento (opcional)

    Returns:
        TensionCurve con puntos por capítulo y metadatos
    """
    if not chapters:
        return TensionCurve(points=[])

    analyzer = PacingAnalyzer()
    points = []

    # Calcular métricas por capítulo
    all_metrics = []
    for ch in chapters:
        metrics = analyzer._compute_metrics(
            text=ch.get("content", ""),
            segment_id=ch.get("number", 0),
            segment_type="chapter",
            title=ch.get("title", ""),
        )
        all_metrics.append((ch, metrics))

    # Calcular puntuación expresiva por capítulo
    exclamation_ratios = []
    question_ratios = []
    for ch, metrics in all_metrics:
        content = ch.get("content", "")
        word_count = metrics.word_count or 1
        exclamations = content.count("!") + content.count("¡")
        questions = content.count("?") + content.count("¿")
        exclamation_ratios.append(exclamations / word_count * 100)
        question_ratios.append(questions / word_count * 100)

    # Normalizar componentes respecto al documento
    action_ratios = [m.action_verb_ratio for _, m in all_metrics]
    sentence_lengths = [m.avg_sentence_length for _, m in all_metrics]
    paragraph_lengths = [m.avg_paragraph_length for _, m in all_metrics]
    dialogue_ratios = [m.dialogue_ratio for _, m in all_metrics]

    def normalize(values: list[float]) -> list[float]:
        """Normaliza valores al rango 0-1."""
        if not values:
            return values
        min_v = min(values)
        max_v = max(values)
        if max_v == min_v:
            return [0.5] * len(values)
        return [(v - min_v) / (max_v - min_v) for v in values]

    norm_action = normalize(action_ratios)
    norm_sent_len = normalize(sentence_lengths)
    norm_para_len = normalize(paragraph_lengths)
    norm_dialogue = normalize(dialogue_ratios)
    norm_exclamation = normalize(exclamation_ratios)
    norm_question = normalize(question_ratios)

    total_words = sum(m.word_count for _, m in all_metrics)
    cumulative_words = 0

    for i, (ch, metrics) in enumerate(all_metrics):
        # Componentes de tensión (más alto = más tensión)
        action_score = norm_action[i]  # Más acción = más tensión
        short_sentences = 1.0 - norm_sent_len[i]  # Oraciones cortas = más tensión
        short_paragraphs = 1.0 - norm_para_len[i]  # Párrafos cortos = más ritmo
        dialogue_intensity = norm_dialogue[i]  # Más diálogo = más conflicto potencial
        exclamation_score = norm_exclamation[i]  # Puntuación expresiva
        question_score = norm_question[i]  # Interrogación = incertidumbre

        # Ponderación de componentes
        weights = {
            "action": 0.25,
            "short_sentences": 0.20,
            "short_paragraphs": 0.10,
            "dialogue": 0.15,
            "exclamation": 0.15,
            "question": 0.15,
        }

        components = {
            "action": action_score,
            "short_sentences": short_sentences,
            "short_paragraphs": short_paragraphs,
            "dialogue": dialogue_intensity,
            "exclamation": exclamation_score,
            "question": question_score,
        }

        tension_score = sum(components[k] * weights[k] for k in weights)
        # Clamp al rango 0-1
        tension_score = max(0.0, min(1.0, tension_score))

        # Posición relativa en el documento
        cumulative_words += metrics.word_count
        position_ratio = cumulative_words / total_words if total_words > 0 else 0.0

        points.append(
            TensionPoint(
                chapter=ch.get("number", i + 1),
                title=ch.get("title", f"Capítulo {ch.get('number', i + 1)}"),
                tension_score=tension_score,
                components=components,
                word_count=metrics.word_count,
                position_ratio=position_ratio,
            )
        )

    # Calcular metadatos de la curva
    tension_scores = [p.tension_score for p in points]
    avg_tension = sum(tension_scores) / len(tension_scores) if tension_scores else 0.0
    max_tension = max(tension_scores) if tension_scores else 0.0
    min_tension = min(tension_scores) if tension_scores else 0.0

    # Clasificar tipo de arco narrativo
    arc_type = _classify_tension_arc(tension_scores)

    return TensionCurve(
        points=points,
        avg_tension=avg_tension,
        max_tension=max_tension,
        min_tension=min_tension,
        tension_arc_type=arc_type,
    )


def _classify_tension_arc(scores: list[float]) -> str:
    """
    Clasifica el tipo de arco de tensión narrativa.

    Tipos:
    - rising: Tensión creciente (inicio-climax)
    - falling: Tensión decreciente (climax-resolución)
    - mountain: Sube y baja (arco clásico)
    - valley: Baja y sube (inversión)
    - wave: Oscilación (múltiples picos)
    - flat: Sin variación significativa
    """
    if len(scores) < 3:
        return "flat"

    n = len(scores)
    first_third = sum(scores[: n // 3]) / max(n // 3, 1)
    mid_third = sum(scores[n // 3 : 2 * n // 3]) / max(n // 3, 1)
    last_third = sum(scores[2 * n // 3 :]) / max(n - 2 * (n // 3), 1)

    # Detectar variación
    variance = max(scores) - min(scores)
    if variance < 0.15:
        return "flat"

    # Contar picos (cambios de dirección)
    direction_changes = 0
    for i in range(1, len(scores) - 1):
        if (scores[i] > scores[i - 1] and scores[i] > scores[i + 1]) or (
            scores[i] < scores[i - 1] and scores[i] < scores[i + 1]
        ):
            direction_changes += 1

    if direction_changes >= len(scores) // 3:
        return "wave"

    # Clasificar por tercios
    threshold = 0.08
    if first_third < mid_third - threshold and mid_third > last_third + threshold:
        return "mountain"
    elif first_third > mid_third + threshold and mid_third < last_third - threshold:
        return "valley"
    elif first_third < last_third - threshold:
        return "rising"
    elif first_third > last_third + threshold:
        return "falling"

    return "wave"
