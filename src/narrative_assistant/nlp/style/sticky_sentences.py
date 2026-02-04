"""
Detector de oraciones pesadas (Sticky Sentences).

Detecta oraciones con exceso de "glue words" (palabras pegamento) que
dificultan la lectura. Las glue words son palabras funcionales como:
- Artículos (el, la, los, las)
- Preposiciones (de, en, a, por, para)
- Conjunciones (y, que, pero)
- Pronombres (se, lo, le)

El objetivo es mantener el porcentaje de glue words por debajo del 40%.
Oraciones con más del 40-45% de glue words se consideran "pegajosas".

Inspirado en ProWritingAid's Sticky Sentences report.

Referencias:
- ProWritingAid: https://prowritingaid.com/art/125/the-sticky-sentence-report.aspx
"""

import logging
import re
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ...core.errors import ErrorSeverity, NLPError
from ...core.result import Result

logger = logging.getLogger(__name__)

# =============================================================================
# Singleton
# =============================================================================

_lock = threading.Lock()
_instance: Optional["StickySentenceDetector"] = None


def get_sticky_sentence_detector() -> "StickySentenceDetector":
    """Obtener instancia singleton del detector de oraciones pesadas."""
    global _instance

    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = StickySentenceDetector()

    return _instance


def reset_sticky_sentence_detector() -> None:
    """Resetear instancia (para testing)."""
    global _instance
    with _lock:
        _instance = None


# =============================================================================
# Tipos
# =============================================================================


class StickinessSeverity(Enum):
    """Severidad del problema de pegajosidad."""

    CRITICAL = "critical"  # >60% glue words - muy difícil de leer
    HIGH = "high"  # 50-60% glue words - problemático
    MEDIUM = "medium"  # 45-50% glue words - mejorable
    LOW = "low"  # 40-45% glue words - aceptable pero denso


@dataclass
class StickySentence:
    """Una oración detectada como pegajosa."""

    # Texto
    text: str
    start_char: int
    end_char: int

    # Métricas
    total_words: int
    glue_words: int
    glue_percentage: float  # 0.0-1.0

    # Severidad
    severity: StickinessSeverity

    # Análisis detallado
    glue_word_list: list[str] = field(default_factory=list)
    content_word_list: list[str] = field(default_factory=list)

    # Contexto
    chapter: int = 0
    paragraph: int = 0
    sentence_in_paragraph: int = 0

    @property
    def glue_percentage_display(self) -> str:
        """Porcentaje formateado para mostrar."""
        return f"{self.glue_percentage * 100:.1f}%"

    @property
    def recommendation(self) -> str:
        """Recomendación para mejorar la oración."""
        if self.severity == StickinessSeverity.CRITICAL:
            return "Esta oración es muy difícil de leer. Considere reescribirla completamente."
        elif self.severity == StickinessSeverity.HIGH:
            return "Oración densa. Intente eliminar palabras innecesarias o dividirla."
        elif self.severity == StickinessSeverity.MEDIUM:
            return "Oración algo pesada. Busque formas más directas de expresar la idea."
        else:
            return "Oración aceptable pero podría ser más fluida."

    def to_dict(self) -> dict:
        """Convertir a diccionario."""
        return {
            "text": self.text[:200] + "..." if len(self.text) > 200 else self.text,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "total_words": self.total_words,
            "glue_words": self.glue_words,
            "glue_percentage": round(self.glue_percentage, 3),
            "glue_percentage_display": self.glue_percentage_display,
            "severity": self.severity.value,
            "glue_word_list": self.glue_word_list[:10],  # Primeras 10
            "recommendation": self.recommendation,
            "chapter": self.chapter,
        }


@dataclass
class StickyReport:
    """Resultado del análisis de oraciones pegajosas."""

    # Oraciones detectadas
    sticky_sentences: list[StickySentence] = field(default_factory=list)

    # Estadísticas globales
    total_sentences: int = 0
    total_words: int = 0
    total_glue_words: int = 0
    avg_glue_percentage: float = 0.0

    # Por severidad
    by_severity: dict[str, int] = field(default_factory=dict)

    # Distribución
    clean_sentences: int = 0  # <40% glue
    borderline_sentences: int = 0  # 40-45%
    sticky_sentences_count: int = 0  # >45%

    # Recomendaciones
    recommendations: list[str] = field(default_factory=list)

    # Umbral usado
    threshold: float = 0.40

    def add_sticky(self, sentence: StickySentence) -> None:
        """Añadir una oración pegajosa."""
        self.sticky_sentences.append(sentence)

        severity_key = sentence.severity.value
        self.by_severity[severity_key] = self.by_severity.get(severity_key, 0) + 1

    @property
    def stickiness_score(self) -> float:
        """
        Puntuación de pegajosidad del texto (0-100).

        100 = texto muy limpio (pocas oraciones pegajosas)
        0 = texto muy denso (muchas oraciones pegajosas)
        """
        if self.total_sentences == 0:
            return 100.0

        # Calcular basado en proporción de oraciones pegajosas y su severidad
        weighted_sticky = 0
        for sent in self.sticky_sentences:
            if sent.severity == StickinessSeverity.CRITICAL:
                weighted_sticky += 4
            elif sent.severity == StickinessSeverity.HIGH:
                weighted_sticky += 2
            elif sent.severity == StickinessSeverity.MEDIUM:
                weighted_sticky += 1
            else:
                weighted_sticky += 0.5

        max_penalty = self.total_sentences * 4
        penalty = weighted_sticky / max_penalty if max_penalty > 0 else 0

        return max(0, min(100, (1 - penalty) * 100))

    def to_dict(self) -> dict:
        """Convertir a diccionario."""
        return {
            "sticky_sentences": [s.to_dict() for s in self.sticky_sentences],
            "statistics": {
                "total_sentences": self.total_sentences,
                "total_words": self.total_words,
                "total_glue_words": self.total_glue_words,
                "avg_glue_percentage": round(self.avg_glue_percentage, 3),
                "avg_glue_percentage_display": f"{self.avg_glue_percentage * 100:.1f}%",
            },
            "distribution": {
                "clean": self.clean_sentences,
                "borderline": self.borderline_sentences,
                "sticky": self.sticky_sentences_count,
            },
            "by_severity": self.by_severity,
            "stickiness_score": round(self.stickiness_score, 1),
            "threshold": self.threshold,
            "recommendations": self.recommendations,
        }


# =============================================================================
# Glue Words (Palabras Pegamento) en Español
# =============================================================================

# Artículos
ARTICLES = {
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "unos",
    "unas",
    "al",
    "del",
}

# Preposiciones
PREPOSITIONS = {
    "a",
    "ante",
    "bajo",
    "cabe",
    "con",
    "contra",
    "de",
    "desde",
    "durante",
    "en",
    "entre",
    "hacia",
    "hasta",
    "mediante",
    "para",
    "por",
    "según",
    "sin",
    "so",
    "sobre",
    "tras",
    "versus",
    "vía",
}

# Conjunciones
CONJUNCTIONS = {
    "y",
    "e",
    "ni",
    "o",
    "u",
    "pero",
    "sino",
    "mas",
    "aunque",
    "porque",
    "pues",
    "como",
    "que",
    "si",
    "cuando",
    "donde",
    "mientras",
    "luego",
    "conque",
    "así",
}

# Pronombres átonos y relativos
PRONOUNS = {
    "me",
    "te",
    "se",
    "nos",
    "os",
    "le",
    "les",
    "lo",
    "la",
    "los",
    "las",
    "yo",
    "tú",
    "él",
    "ella",
    "ello",
    "nosotros",
    "nosotras",
    "vosotros",
    "vosotras",
    "ellos",
    "ellas",
    "mi",
    "mis",
    "tu",
    "tus",
    "su",
    "sus",
    "nuestro",
    "nuestra",
    "nuestros",
    "nuestras",
    "vuestro",
    "vuestra",
    "vuestros",
    "vuestras",
    "este",
    "esta",
    "esto",
    "estos",
    "estas",
    "ese",
    "esa",
    "eso",
    "esos",
    "esas",
    "aquel",
    "aquella",
    "aquello",
    "aquellos",
    "aquellas",
    "quien",
    "quienes",
    "cual",
    "cuales",
    "cuyo",
    "cuya",
    "cuyos",
    "cuyas",
    "qué",
    "quién",
    "cuál",
    "cuánto",
    "cuánta",
    "cuántos",
    "cuántas",
}

# Verbos auxiliares muy comunes (formas conjugadas)
AUXILIARY_VERBS = {
    # Ser
    "soy",
    "eres",
    "es",
    "somos",
    "sois",
    "son",
    "era",
    "eras",
    "éramos",
    "erais",
    "eran",
    "fui",
    "fuiste",
    "fue",
    "fuimos",
    "fuisteis",
    "fueron",
    "seré",
    "serás",
    "será",
    "seremos",
    "seréis",
    "serán",
    "sería",
    "serías",
    "seríamos",
    "seríais",
    "serían",
    "sea",
    "seas",
    "seamos",
    "seáis",
    "sean",
    "fuera",
    "fueras",
    "fuéramos",
    "fuerais",
    "fueran",
    "fuese",
    "fueses",
    "fuésemos",
    "fueseis",
    "fuesen",
    # Estar
    "estoy",
    "estás",
    "está",
    "estamos",
    "estáis",
    "están",
    "estaba",
    "estabas",
    "estábamos",
    "estabais",
    "estaban",
    "estuve",
    "estuviste",
    "estuvo",
    "estuvimos",
    "estuvisteis",
    "estuvieron",
    "estaré",
    "estarás",
    "estará",
    "estaremos",
    "estaréis",
    "estarán",
    # Haber
    "he",
    "has",
    "ha",
    "hemos",
    "habéis",
    "han",
    "había",
    "habías",
    "habíamos",
    "habíais",
    "habían",
    "hube",
    "hubiste",
    "hubo",
    "hubimos",
    "hubisteis",
    "hubieron",
    "habré",
    "habrás",
    "habrá",
    "habremos",
    "habréis",
    "habrán",
    "hay",
    "haya",
    "hayas",
    "hayamos",
    "hayáis",
    "hayan",
    # Tener (auxiliar)
    "tengo",
    "tienes",
    "tiene",
    "tenemos",
    "tenéis",
    "tienen",
}

# Adverbios muy comunes
COMMON_ADVERBS = {
    "no",
    "sí",
    "ya",
    "muy",
    "más",
    "menos",
    "tan",
    "tanto",
    "bien",
    "mal",
    "así",
    "también",
    "tampoco",
    "ahora",
    "entonces",
    "después",
    "antes",
    "luego",
    "aquí",
    "allí",
    "allá",
    "acá",
    "ahí",
    "siempre",
    "nunca",
    "jamás",
    "todavía",
    "aún",
    "solo",
    "sólo",
    "solamente",
}

# Palabras muy cortas funcionales
SHORT_FUNCTIONAL = {
    "al",
    "del",
    "a",
    "e",
    "o",
    "u",
    "y",
}

# Conjunto completo de glue words
GLUE_WORDS = (
    ARTICLES
    | PREPOSITIONS
    | CONJUNCTIONS
    | PRONOUNS
    | AUXILIARY_VERBS
    | COMMON_ADVERBS
    | SHORT_FUNCTIONAL
)


# =============================================================================
# Detector
# =============================================================================


class StickySentenceDetector:
    """
    Detector de oraciones pegajosas (Sticky Sentences).

    Analiza el texto para encontrar oraciones con un alto porcentaje
    de "glue words" (palabras funcionales que no aportan significado
    concreto pero son necesarias para la gramática).

    Un texto con muchas oraciones pegajosas es difícil de leer
    porque el lector tiene que "pegarse" a través de muchas palabras
    sin contenido real.
    """

    def __init__(
        self,
        threshold: float = 0.40,
        min_words: int = 5,
    ):
        """
        Inicializar detector.

        Args:
            threshold: Umbral de glue words para considerar oración pegajosa (default 40%)
            min_words: Mínimo de palabras para analizar una oración
        """
        self.threshold = threshold
        self.min_words = min_words

        # Patrón para dividir en oraciones
        self._sentence_pattern = re.compile(r"[.!?]+(?:\s+|$)|[\n]{2,}", re.UNICODE)

        # Patrón para extraer palabras
        self._word_pattern = re.compile(r"\b([a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+)\b", re.UNICODE)

    def analyze(
        self,
        text: str,
        threshold: float | None = None,
        chapter: int = 0,
    ) -> Result[StickyReport]:
        """
        Analizar texto para detectar oraciones pegajosas.

        Args:
            text: Texto a analizar
            threshold: Umbral opcional (override del default)
            chapter: Número de capítulo para contexto

        Returns:
            Result con StickyReport
        """
        if not text or not text.strip():
            return Result.success(StickyReport())

        threshold = threshold or self.threshold
        report = StickyReport(threshold=threshold)

        try:
            # Dividir en oraciones
            sentences = self._split_sentences(text)
            report.total_sentences = len(sentences)

            all_glue_percentages = []

            for sent_text, start, end in sentences:
                # Tokenizar
                words = self._tokenize(sent_text)

                if len(words) < self.min_words:
                    continue

                # Contar glue words
                glue_count = 0
                glue_list = []
                content_list = []

                for word in words:
                    word_lower = word.lower()
                    if word_lower in GLUE_WORDS:
                        glue_count += 1
                        glue_list.append(word)
                    else:
                        content_list.append(word)

                total = len(words)
                glue_pct = glue_count / total if total > 0 else 0

                report.total_words += total
                report.total_glue_words += glue_count
                all_glue_percentages.append(glue_pct)

                # Clasificar
                if glue_pct < threshold:
                    report.clean_sentences += 1
                elif glue_pct < 0.45:
                    report.borderline_sentences += 1
                else:
                    report.sticky_sentences_count += 1

                # Solo reportar si supera el umbral
                if glue_pct >= threshold:
                    severity = self._get_severity(glue_pct)

                    sticky = StickySentence(
                        text=sent_text,
                        start_char=start,
                        end_char=end,
                        total_words=total,
                        glue_words=glue_count,
                        glue_percentage=glue_pct,
                        severity=severity,
                        glue_word_list=glue_list,
                        content_word_list=content_list,
                        chapter=chapter,
                    )
                    report.add_sticky(sticky)

            # Calcular promedio
            if all_glue_percentages:
                report.avg_glue_percentage = sum(all_glue_percentages) / len(all_glue_percentages)

            # Generar recomendaciones
            report.recommendations = self._generate_recommendations(report)

            return Result.success(report)

        except Exception as e:
            logger.error(f"Error analyzing sticky sentences: {e}", exc_info=True)
            error = NLPError(
                message=f"Error en análisis de oraciones pesadas: {e}",
                severity=ErrorSeverity.MEDIUM,
            )
            return Result.failure(error)

    def analyze_by_chapter(
        self,
        chapters: list[tuple[int, str]],  # [(chapter_num, content), ...]
    ) -> dict[int, StickyReport]:
        """
        Analizar texto por capítulo.

        Args:
            chapters: Lista de tuplas (número_capítulo, contenido)

        Returns:
            Dict de chapter_num -> StickyReport
        """
        results = {}
        for chapter_num, content in chapters:
            result = self.analyze(content, chapter=chapter_num)
            if result.is_success:
                results[chapter_num] = result.value
        return results

    def get_sentence_analysis(self, sentence: str) -> dict:
        """
        Obtener análisis detallado de una oración específica.

        Args:
            sentence: Oración a analizar

        Returns:
            Dict con análisis detallado
        """
        words = self._tokenize(sentence)

        analysis = {
            "sentence": sentence,
            "words": [],
            "total_words": len(words),
            "glue_words": 0,
            "content_words": 0,
            "glue_percentage": 0.0,
            "is_sticky": False,
        }

        for word in words:
            word_lower = word.lower()
            is_glue = word_lower in GLUE_WORDS

            analysis["words"].append(
                {
                    "word": word,
                    "is_glue": is_glue,
                    "category": self._get_glue_category(word_lower) if is_glue else "content",
                }
            )

            if is_glue:
                analysis["glue_words"] += 1
            else:
                analysis["content_words"] += 1

        if analysis["total_words"] > 0:
            analysis["glue_percentage"] = analysis["glue_words"] / analysis["total_words"]
            analysis["is_sticky"] = analysis["glue_percentage"] >= self.threshold

        return analysis

    # =========================================================================
    # Helpers
    # =========================================================================

    def _split_sentences(self, text: str) -> list[tuple[str, int, int]]:
        """Dividir texto en oraciones con posiciones."""
        sentences = []

        # Dividir por puntuación
        parts = self._sentence_pattern.split(text)

        current_pos = 0
        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Buscar posición real en el texto
            start = text.find(part, current_pos)
            if start == -1:
                start = current_pos
            end = start + len(part)

            # Verificar que tiene palabras
            if self._word_pattern.search(part):
                sentences.append((part, start, end))

            current_pos = end

        return sentences

    def _tokenize(self, text: str) -> list[str]:
        """Extraer palabras del texto."""
        return self._word_pattern.findall(text)

    def _get_severity(self, glue_pct: float) -> StickinessSeverity:
        """Obtener severidad según porcentaje de glue words."""
        if glue_pct >= 0.60:
            return StickinessSeverity.CRITICAL
        elif glue_pct >= 0.50:
            return StickinessSeverity.HIGH
        elif glue_pct >= 0.45:
            return StickinessSeverity.MEDIUM
        else:
            return StickinessSeverity.LOW

    def _get_glue_category(self, word: str) -> str:
        """Obtener categoría de una glue word."""
        if word in ARTICLES:
            return "article"
        elif word in PREPOSITIONS:
            return "preposition"
        elif word in CONJUNCTIONS:
            return "conjunction"
        elif word in PRONOUNS:
            return "pronoun"
        elif word in AUXILIARY_VERBS:
            return "auxiliary_verb"
        elif word in COMMON_ADVERBS:
            return "adverb"
        else:
            return "other"

    def _generate_recommendations(self, report: StickyReport) -> list[str]:
        """Generar recomendaciones basadas en el análisis."""
        recommendations = []

        if report.total_sentences == 0:
            return recommendations

        sticky_ratio = len(report.sticky_sentences) / report.total_sentences

        # Recomendaciones según proporción de oraciones pegajosas
        if sticky_ratio > 0.30:
            recommendations.append(
                f"El {sticky_ratio * 100:.0f}% de las oraciones son pegajosas. "
                "Considere una revisión general del estilo."
            )
        elif sticky_ratio > 0.15:
            recommendations.append(
                f"Hay {len(report.sticky_sentences)} oraciones que podrían ser más directas."
            )

        # Recomendaciones según severidad
        critical = report.by_severity.get("critical", 0)
        high = report.by_severity.get("high", 0)

        if critical > 0:
            recommendations.append(
                f"Hay {critical} oraciones con severidad crítica (>60% glue words). "
                "Estas requieren atención inmediata."
            )

        if high > 3:
            recommendations.append(
                f"Hay {high} oraciones problemáticas. "
                "Intente usar verbos más directos y reducir preposiciones encadenadas."
            )

        # Promedio global
        if report.avg_glue_percentage > 0.35:
            recommendations.append(
                f"El promedio de glue words ({report.avg_glue_percentage * 100:.0f}%) es alto. "
                "El texto podría beneficiarse de un estilo más directo."
            )

        # Tips específicos
        if len(report.sticky_sentences) > 0:
            recommendations.append(
                "Tip: Busque construcciones como 'el hecho de que' o 'en relación con' "
                "que pueden simplificarse."
            )

        return recommendations


# =============================================================================
# Funciones de utilidad
# =============================================================================


def is_glue_word(word: str) -> bool:
    """Verificar si una palabra es una glue word."""
    return word.lower() in GLUE_WORDS


def get_glue_words() -> set[str]:
    """Obtener el conjunto completo de glue words."""
    return GLUE_WORDS.copy()


def calculate_glue_index(text: str) -> float:
    """
    Calcular el índice de pegajosidad de un texto.

    Returns:
        Float 0-1 indicando proporción de glue words
    """
    detector = get_sticky_sentence_detector()
    words = detector._tokenize(text)

    if not words:
        return 0.0

    glue_count = sum(1 for w in words if w.lower() in GLUE_WORDS)
    return glue_count / len(words)
