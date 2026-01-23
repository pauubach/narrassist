"""
Análisis de legibilidad para textos en español.

Implementa métricas de legibilidad adaptadas al español:
- Índice Flesch-Szigriszt (adaptación española del Flesch Reading Ease)
- Escala INFLESZ (interpretación española)
- Índice Fernández-Huerta
- Estadísticas básicas (oraciones, palabras, sílabas)

Referencias:
- Szigriszt Pazos, F. (1993). Sistemas predictivos de legibilidad del mensaje escrito.
- Fernández Huerta, J. (1959). Medidas sencillas de lecturabilidad.
- Barrio-Cantalejo, I.M. et al. (2008). Validación de la Escala INFLESZ.
"""

import logging
import re
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ...core.result import Result
from ...core.errors import NLPError, ErrorSeverity

logger = logging.getLogger(__name__)

# =============================================================================
# Singleton
# =============================================================================

_lock = threading.Lock()
_instance: Optional["ReadabilityAnalyzer"] = None


def get_readability_analyzer() -> "ReadabilityAnalyzer":
    """Obtener instancia singleton del analizador de legibilidad."""
    global _instance

    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = ReadabilityAnalyzer()

    return _instance


def reset_readability_analyzer() -> None:
    """Resetear instancia (para testing)."""
    global _instance
    with _lock:
        _instance = None


# =============================================================================
# Tipos
# =============================================================================

class ReadabilityLevel(Enum):
    """Nivel de legibilidad según la escala INFLESZ."""
    VERY_EASY = "very_easy"           # Muy fácil (>80)
    EASY = "easy"                      # Fácil (66-80)
    FAIRLY_EASY = "fairly_easy"        # Algo fácil (56-65)
    NORMAL = "normal"                  # Normal (40-55)
    FAIRLY_DIFFICULT = "fairly_difficult"  # Algo difícil (26-39)
    DIFFICULT = "difficult"            # Difícil (11-25)
    VERY_DIFFICULT = "very_difficult"  # Muy difícil (0-10)


@dataclass
class SentenceStats:
    """Estadísticas de una oración."""
    text: str
    word_count: int
    syllable_count: int
    avg_syllables_per_word: float
    flesch_score: float  # Puntuación de esta oración específica


@dataclass
class ReadabilityReport:
    """Reporte completo de legibilidad."""

    # Métricas principales
    flesch_szigriszt: float = 0.0      # Índice Flesch-Szigriszt (0-100)
    fernandez_huerta: float = 0.0       # Índice Fernández-Huerta (0-100)

    # Nivel de legibilidad
    level: ReadabilityLevel = ReadabilityLevel.NORMAL
    level_description: str = ""

    # Estadísticas básicas
    total_chars: int = 0
    total_words: int = 0
    total_sentences: int = 0
    total_syllables: int = 0
    total_paragraphs: int = 0

    # Promedios
    avg_word_length: float = 0.0       # Caracteres por palabra
    avg_syllables_per_word: float = 0.0
    avg_words_per_sentence: float = 0.0
    avg_sentences_per_paragraph: float = 0.0

    # Distribución de longitud de oraciones
    short_sentences: int = 0           # < 10 palabras
    medium_sentences: int = 0          # 10-20 palabras
    long_sentences: int = 0            # 21-35 palabras
    very_long_sentences: int = 0       # > 35 palabras

    # Oraciones problemáticas (muy largas)
    problematic_sentences: list[SentenceStats] = field(default_factory=list)

    # Recomendaciones
    recommendations: list[str] = field(default_factory=list)

    # Público objetivo sugerido
    target_audience: str = ""

    def to_dict(self) -> dict:
        """Convertir a diccionario."""
        return {
            "flesch_szigriszt": round(self.flesch_szigriszt, 2),
            "fernandez_huerta": round(self.fernandez_huerta, 2),
            "level": self.level.value,
            "level_description": self.level_description,
            "statistics": {
                "total_chars": self.total_chars,
                "total_words": self.total_words,
                "total_sentences": self.total_sentences,
                "total_syllables": self.total_syllables,
                "total_paragraphs": self.total_paragraphs,
            },
            "averages": {
                "avg_word_length": round(self.avg_word_length, 2),
                "avg_syllables_per_word": round(self.avg_syllables_per_word, 2),
                "avg_words_per_sentence": round(self.avg_words_per_sentence, 2),
                "avg_sentences_per_paragraph": round(self.avg_sentences_per_paragraph, 2),
            },
            "sentence_distribution": {
                "short": self.short_sentences,
                "medium": self.medium_sentences,
                "long": self.long_sentences,
                "very_long": self.very_long_sentences,
            },
            "problematic_sentences": [
                {
                    "text": s.text[:100] + "..." if len(s.text) > 100 else s.text,
                    "word_count": s.word_count,
                }
                for s in self.problematic_sentences[:5]
            ],
            "recommendations": self.recommendations,
            "target_audience": self.target_audience,
        }


# =============================================================================
# Escala INFLESZ (interpretación española)
# =============================================================================

INFLESZ_SCALE = [
    (80, ReadabilityLevel.VERY_EASY, "Muy fácil",
     "Lectura muy fácil. Apto para todo público, incluyendo niños."),
    (66, ReadabilityLevel.EASY, "Fácil",
     "Lectura fácil. Apto para público general sin formación específica."),
    (56, ReadabilityLevel.FAIRLY_EASY, "Algo fácil",
     "Lectura normal-fácil. Apropiado para educación secundaria."),
    (40, ReadabilityLevel.NORMAL, "Normal",
     "Lectura normal. Apropiado para público adulto con educación media."),
    (26, ReadabilityLevel.FAIRLY_DIFFICULT, "Algo difícil",
     "Lectura algo difícil. Requiere atención y cierta formación."),
    (11, ReadabilityLevel.DIFFICULT, "Difícil",
     "Lectura difícil. Apropiado para público especializado o académico."),
    (0, ReadabilityLevel.VERY_DIFFICULT, "Muy difícil",
     "Lectura muy difícil. Requiere alto nivel de formación."),
]


def get_readability_level(score: float) -> tuple[ReadabilityLevel, str, str]:
    """Obtener nivel de legibilidad según puntuación."""
    for threshold, level, name, description in INFLESZ_SCALE:
        if score >= threshold:
            return level, name, description
    return ReadabilityLevel.VERY_DIFFICULT, "Muy difícil", INFLESZ_SCALE[-1][3]


# =============================================================================
# Conteo de sílabas en español
# =============================================================================

# Vocales en español
VOWELS = set('aeiouáéíóúüAEIOUÁÉÍÓÚÜ')
STRONG_VOWELS = set('aeoáéó')
WEAK_VOWELS = set('iuíúü')


def count_syllables_spanish(word: str) -> int:
    """
    Contar sílabas en una palabra española.

    Algoritmo basado en reglas de silabeo español:
    1. Cada vocal o grupo vocálico forma una sílaba
    2. Los diptongos (vocal fuerte + débil o viceversa) cuentan como una sílaba
    3. Los hiatos (dos vocales fuertes) cuentan como dos sílabas
    4. Los triptongos cuentan como una sílaba

    Returns:
        Número de sílabas (mínimo 1)
    """
    word = word.lower().strip()
    if not word:
        return 0

    # Eliminar caracteres no alfabéticos
    word = re.sub(r'[^a-záéíóúüñ]', '', word)
    if not word:
        return 0

    syllables = 0
    prev_was_vowel = False
    prev_vowel_strong = False

    for i, char in enumerate(word):
        is_vowel = char in VOWELS
        is_strong = char in STRONG_VOWELS

        if is_vowel:
            if not prev_was_vowel:
                # Nueva sílaba
                syllables += 1
            elif prev_vowel_strong and is_strong:
                # Hiato: dos vocales fuertes = dos sílabas
                syllables += 1
            # Si es diptongo (fuerte+débil o débil+fuerte) no incrementamos

            prev_vowel_strong = is_strong
        else:
            prev_vowel_strong = False

        prev_was_vowel = is_vowel

    return max(1, syllables)


def count_syllables_text(text: str) -> tuple[int, int]:
    """
    Contar sílabas y palabras en un texto.

    Returns:
        (total_syllables, total_words)
    """
    words = re.findall(r'\b[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+\b', text)
    total_syllables = sum(count_syllables_spanish(word) for word in words)
    return total_syllables, len(words)


# =============================================================================
# Analizador
# =============================================================================

class ReadabilityAnalyzer:
    """
    Analizador de legibilidad para textos en español.

    Calcula métricas como el índice Flesch-Szigriszt y proporciona
    interpretaciones y recomendaciones.
    """

    def __init__(self):
        """Inicializar analizador."""
        # Patrón para dividir en oraciones
        self._sentence_pattern = re.compile(
            r'[.!?]+(?:\s+|$)|[\n]{2,}',
            re.UNICODE
        )
        # Patrón para dividir en párrafos
        self._paragraph_pattern = re.compile(r'\n\s*\n')

    def analyze(self, text: str) -> Result[ReadabilityReport]:
        """
        Analizar legibilidad de un texto.

        Args:
            text: Texto a analizar

        Returns:
            Result con ReadabilityReport
        """
        if not text or not text.strip():
            return Result.success(ReadabilityReport())

        try:
            # Estadísticas básicas
            total_chars = len(text.replace(' ', '').replace('\n', ''))
            paragraphs = [p.strip() for p in self._paragraph_pattern.split(text) if p.strip()]
            total_paragraphs = len(paragraphs)

            # Dividir en oraciones
            sentences = self._split_sentences(text)
            total_sentences = len(sentences)

            if total_sentences == 0:
                return Result.success(ReadabilityReport(
                    total_chars=total_chars,
                    total_paragraphs=total_paragraphs,
                ))

            # Contar palabras y sílabas
            total_syllables, total_words = count_syllables_text(text)

            if total_words == 0:
                return Result.success(ReadabilityReport(
                    total_chars=total_chars,
                    total_sentences=total_sentences,
                    total_paragraphs=total_paragraphs,
                ))

            # Calcular promedios
            avg_word_length = total_chars / total_words
            avg_syllables_per_word = total_syllables / total_words
            avg_words_per_sentence = total_words / total_sentences
            avg_sentences_per_paragraph = total_sentences / total_paragraphs if total_paragraphs > 0 else 0

            # Calcular índices de legibilidad

            # Índice Flesch-Szigriszt (adaptación española)
            # IFSZ = 206.84 - 62.3 * (sílabas/palabras) - 1.02 * (palabras/oraciones)
            flesch_szigriszt = 206.84 - (62.3 * avg_syllables_per_word) - (1.02 * avg_words_per_sentence)
            flesch_szigriszt = max(0, min(100, flesch_szigriszt))  # Limitar a 0-100

            # Índice Fernández-Huerta
            # P = 206.84 - 0.60P - 1.02F
            # donde P = (sílabas / palabras) * 100, F = palabras / oraciones
            p = (total_syllables / total_words) * 100
            f = total_words / total_sentences
            fernandez_huerta = 206.84 - (0.60 * p) - (1.02 * f)
            fernandez_huerta = max(0, min(100, fernandez_huerta))

            # Obtener nivel de legibilidad
            level, level_name, level_description = get_readability_level(flesch_szigriszt)

            # Analizar distribución de oraciones
            sentence_stats = []
            short_sentences = 0
            medium_sentences = 0
            long_sentences = 0
            very_long_sentences = 0
            problematic_sentences = []

            for sent in sentences:
                sent_syllables, sent_words = count_syllables_text(sent)
                if sent_words == 0:
                    continue

                sent_avg_syl = sent_syllables / sent_words
                sent_score = 206.84 - (62.3 * sent_avg_syl) - (1.02 * sent_words)

                stats = SentenceStats(
                    text=sent,
                    word_count=sent_words,
                    syllable_count=sent_syllables,
                    avg_syllables_per_word=sent_avg_syl,
                    flesch_score=max(0, min(100, sent_score)),
                )
                sentence_stats.append(stats)

                # Clasificar por longitud
                if sent_words < 10:
                    short_sentences += 1
                elif sent_words <= 20:
                    medium_sentences += 1
                elif sent_words <= 35:
                    long_sentences += 1
                else:
                    very_long_sentences += 1
                    problematic_sentences.append(stats)

            # Generar recomendaciones
            recommendations = []

            if avg_words_per_sentence > 25:
                recommendations.append(
                    f"Las oraciones son largas (promedio {avg_words_per_sentence:.1f} palabras). "
                    "Considere dividir algunas oraciones para mejorar la legibilidad."
                )

            if avg_syllables_per_word > 2.2:
                recommendations.append(
                    "El texto utiliza muchas palabras largas. "
                    "Considere usar vocabulario más sencillo donde sea apropiado."
                )

            if very_long_sentences > total_sentences * 0.2:
                recommendations.append(
                    f"Hay {very_long_sentences} oraciones muy largas (>35 palabras). "
                    "Esto puede dificultar la comprensión."
                )

            if short_sentences > total_sentences * 0.5 and total_sentences > 5:
                recommendations.append(
                    "El texto tiene muchas oraciones cortas. "
                    "Considere variar la longitud para un mejor ritmo."
                )

            if flesch_szigriszt < 40:
                recommendations.append(
                    "El texto es difícil de leer. "
                    "Considere simplificar el vocabulario y acortar las oraciones."
                )

            # Determinar público objetivo
            if flesch_szigriszt >= 80:
                target_audience = "Todo público, incluyendo niños de primaria"
            elif flesch_szigriszt >= 66:
                target_audience = "Público general sin formación específica"
            elif flesch_szigriszt >= 56:
                target_audience = "Público con educación secundaria"
            elif flesch_szigriszt >= 40:
                target_audience = "Público adulto con educación media"
            elif flesch_szigriszt >= 26:
                target_audience = "Público con formación superior"
            else:
                target_audience = "Público especializado o académico"

            report = ReadabilityReport(
                flesch_szigriszt=flesch_szigriszt,
                fernandez_huerta=fernandez_huerta,
                level=level,
                level_description=level_description,
                total_chars=total_chars,
                total_words=total_words,
                total_sentences=total_sentences,
                total_syllables=total_syllables,
                total_paragraphs=total_paragraphs,
                avg_word_length=avg_word_length,
                avg_syllables_per_word=avg_syllables_per_word,
                avg_words_per_sentence=avg_words_per_sentence,
                avg_sentences_per_paragraph=avg_sentences_per_paragraph,
                short_sentences=short_sentences,
                medium_sentences=medium_sentences,
                long_sentences=long_sentences,
                very_long_sentences=very_long_sentences,
                problematic_sentences=problematic_sentences,
                recommendations=recommendations,
                target_audience=target_audience,
            )

            return Result.success(report)

        except Exception as e:
            logger.error(f"Error analizando legibilidad: {e}", exc_info=True)
            error = NLPError(
                message=f"Error en análisis de legibilidad: {e}",
                severity=ErrorSeverity.MEDIUM,
            )
            return Result.failure(error)

    def _split_sentences(self, text: str) -> list[str]:
        """Dividir texto en oraciones."""
        # Primero dividir por puntuación
        raw_sentences = self._sentence_pattern.split(text)

        # Limpiar y filtrar
        sentences = []
        for sent in raw_sentences:
            sent = sent.strip()
            if sent and len(sent) > 1:
                # Asegurar que tiene al menos una palabra
                if re.search(r'\b[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+\b', sent):
                    sentences.append(sent)

        return sentences

    def analyze_by_chapter(
        self,
        chapters: list[tuple[str, str]],  # [(título, contenido), ...]
    ) -> dict[str, ReadabilityReport]:
        """
        Analizar legibilidad por capítulo.

        Args:
            chapters: Lista de tuplas (título, contenido)

        Returns:
            Dict de título -> ReadabilityReport
        """
        results = {}
        for title, content in chapters:
            result = self.analyze(content)
            if result.is_success:
                results[title] = result.value
        return results
