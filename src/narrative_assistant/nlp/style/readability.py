"""
Análisis de legibilidad para textos en español.

Implementa métricas de legibilidad adaptadas al español:
- Índice Flesch-Szigriszt (adaptación española del Flesch Reading Ease)
- Escala INFLESZ (interpretación española)
- Índice Fernández-Huerta
- Estadísticas básicas (oraciones, palabras, sílabas)
- Métricas de legibilidad por edad para literatura infantil/juvenil

Referencias:
- Szigriszt Pazos, F. (1993). Sistemas predictivos de legibilidad del mensaje escrito.
- Fernández Huerta, J. (1959). Medidas sencillas de lecturabilidad.
- Barrio-Cantalejo, I.M. et al. (2008). Validación de la Escala INFLESZ.
- Fry, E. (1968). A readability formula that saves time.
- Dale, E. & Chall, J.S. (1948). A formula for predicting readability.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum

from ...core.errors import ErrorSeverity, NLPError
from ...core.patterns import lazy_singleton
from ...core.result import Result

logger = logging.getLogger(__name__)


# =============================================================================
# Tipos
# =============================================================================


class ReadabilityLevel(Enum):
    """Nivel de legibilidad según la escala INFLESZ."""

    VERY_EASY = "very_easy"  # Muy fácil (>80)
    EASY = "easy"  # Fácil (66-80)
    FAIRLY_EASY = "fairly_easy"  # Algo fácil (56-65)
    NORMAL = "normal"  # Normal (40-55)
    FAIRLY_DIFFICULT = "fairly_difficult"  # Algo difícil (26-39)
    DIFFICULT = "difficult"  # Difícil (11-25)
    VERY_DIFFICULT = "very_difficult"  # Muy difícil (0-10)


class AgeGroup(Enum):
    """Grupos de edad para literatura infantil/juvenil."""

    BOARD_BOOK = "board_book"  # INF_BB: 0-3 años
    PICTURE_BOOK = "picture_book"  # INF_PB: 3-5 años
    EARLY_READER = "early_reader"  # INF_ER: 5-8 años
    CHAPTER_BOOK = "chapter_book"  # INF_CB: 6-10 años
    MIDDLE_GRADE = "middle_grade"  # INF_MG: 8-12 años
    YOUNG_ADULT = "young_adult"  # INF_YA: 12+ años
    ADULT = "adult"  # Adulto


# Palabras de alta frecuencia en español para primeros lectores
# Basado en listas de vocabulario básico español
SPANISH_SIGHT_WORDS = {
    # Artículos
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "unos",
    "unas",
    # Pronombres
    "yo",
    "tú",
    "él",
    "ella",
    "nosotros",
    "ellos",
    "ellas",
    "me",
    "te",
    "se",
    "nos",
    # Verbos básicos
    "es",
    "está",
    "son",
    "hay",
    "tiene",
    "va",
    "ve",
    "come",
    "bebe",
    "duerme",
    "juega",
    "corre",
    "salta",
    "lee",
    "escribe",
    "habla",
    "quiere",
    "puede",
    "hace",
    "dice",
    "sabe",
    "viene",
    "sale",
    "entra",
    "mira",
    "oye",
    # Conectores simples
    "y",
    "o",
    "pero",
    "que",
    "si",
    "no",
    "sí",
    "con",
    "sin",
    "para",
    # Preposiciones
    "de",
    "a",
    "en",
    "por",
    "sobre",
    "bajo",
    "entre",
    "hasta",
    "desde",
    # Adverbios básicos
    "muy",
    "más",
    "menos",
    "bien",
    "mal",
    "aquí",
    "allí",
    "ahora",
    "hoy",
    "ya",
    "también",
    "siempre",
    "nunca",
    "después",
    "antes",
    # Adjetivos básicos
    "grande",
    "pequeño",
    "bueno",
    "malo",
    "bonito",
    "feo",
    "nuevo",
    "viejo",
    "alto",
    "largo",
    "corto",
    "gordo",
    "flaco",
    "feliz",
    "triste",
    # Sustantivos básicos
    "casa",
    "mamá",
    "papá",
    "niño",
    "niña",
    "perro",
    "gato",
    "agua",
    "sol",
    "luna",
    "día",
    "noche",
    "amigo",
    "escuela",
    "libro",
    # Números
    "uno",
    "dos",
    "tres",
    "cuatro",
    "cinco",
    "seis",
    "siete",
    "ocho",
    "nueve",
    "diez",
    # Colores
    "rojo",
    "azul",
    "verde",
    "amarillo",
    "blanco",
    "negro",
    "rosa",
    # Preguntas
    "qué",
    "quién",
    "cómo",
    "dónde",
    "cuándo",
    "por qué",
    "cuánto",
}


# Umbrales por grupo de edad
AGE_GROUP_THRESHOLDS = {
    AgeGroup.BOARD_BOOK: {
        "max_words": 300,
        "max_words_per_sentence": 5,
        "max_syllables_per_word": 2.0,
        "min_sight_word_ratio": 0.7,
        "age_range": "0-3 años",
        "grade": "Pre-escolar",
    },
    AgeGroup.PICTURE_BOOK: {
        "max_words": 1000,
        "max_words_per_sentence": 8,
        "max_syllables_per_word": 2.2,
        "min_sight_word_ratio": 0.5,
        "age_range": "3-5 años",
        "grade": "Educación Infantil",
    },
    AgeGroup.EARLY_READER: {
        "max_words": 5000,
        "max_words_per_sentence": 12,
        "max_syllables_per_word": 2.4,
        "min_sight_word_ratio": 0.4,
        "age_range": "5-8 años",
        "grade": "1º-2º Primaria",
    },
    AgeGroup.CHAPTER_BOOK: {
        "max_words": 15000,
        "max_words_per_sentence": 15,
        "max_syllables_per_word": 2.6,
        "min_sight_word_ratio": 0.3,
        "age_range": "6-10 años",
        "grade": "2º-4º Primaria",
    },
    AgeGroup.MIDDLE_GRADE: {
        "max_words": 50000,
        "max_words_per_sentence": 20,
        "max_syllables_per_word": 2.8,
        "min_sight_word_ratio": 0.2,
        "age_range": "8-12 años",
        "grade": "4º-6º Primaria",
    },
    AgeGroup.YOUNG_ADULT: {
        "max_words": 80000,
        "max_words_per_sentence": 25,
        "max_syllables_per_word": 3.0,
        "min_sight_word_ratio": 0.1,
        "age_range": "12+ años",
        "grade": "ESO",
    },
}


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
    flesch_szigriszt: float = 0.0  # Índice Flesch-Szigriszt (0-100)
    fernandez_huerta: float = 0.0  # Índice Fernández-Huerta (0-100)

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
    avg_word_length: float = 0.0  # Caracteres por palabra
    avg_syllables_per_word: float = 0.0
    avg_words_per_sentence: float = 0.0
    avg_sentences_per_paragraph: float = 0.0

    # Distribución de longitud de oraciones
    short_sentences: int = 0  # < 10 palabras
    medium_sentences: int = 0  # 10-20 palabras
    long_sentences: int = 0  # 21-35 palabras
    very_long_sentences: int = 0  # > 35 palabras

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


@dataclass
class AgeReadabilityReport:
    """Reporte de legibilidad adaptado a grupos de edad infantil/juvenil."""

    # Grupo de edad estimado
    estimated_age_group: AgeGroup = AgeGroup.ADULT
    estimated_age_range: str = ""
    estimated_grade_level: str = ""

    # Métricas base (del análisis general)
    flesch_szigriszt: float = 0.0
    total_words: int = 0
    total_sentences: int = 0
    avg_words_per_sentence: float = 0.0
    avg_syllables_per_word: float = 0.0

    # Métricas específicas de edad
    sight_word_count: int = 0
    sight_word_ratio: float = 0.0
    unique_words: int = 0
    vocabulary_diversity: float = 0.0  # unique_words / total_words
    simple_words_ratio: float = 0.0  # Palabras de 1-2 sílabas
    complex_words_ratio: float = 0.0  # Palabras de 4+ sílabas

    # Repetición (importante para primeros lectores)
    repetition_score: float = 0.0  # Mayor = más repetición (bueno para niños pequeños)
    most_repeated_words: list[tuple[str, int]] = field(default_factory=list)

    # Evaluación de adecuación
    is_appropriate: bool = True
    appropriateness_score: float = 100.0  # 0-100
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    # Comparación con grupo objetivo (si se especifica)
    target_age_group: AgeGroup | None = None
    target_comparison: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convertir a diccionario."""
        result = {
            "estimated_age_group": self.estimated_age_group.value,
            "estimated_age_range": self.estimated_age_range,
            "estimated_grade_level": self.estimated_grade_level,
            "metrics": {
                "flesch_szigriszt": round(self.flesch_szigriszt, 2),
                "total_words": self.total_words,
                "total_sentences": self.total_sentences,
                "avg_words_per_sentence": round(self.avg_words_per_sentence, 2),
                "avg_syllables_per_word": round(self.avg_syllables_per_word, 2),
            },
            "vocabulary": {
                "sight_word_count": self.sight_word_count,
                "sight_word_ratio": round(self.sight_word_ratio, 3),
                "unique_words": self.unique_words,
                "vocabulary_diversity": round(self.vocabulary_diversity, 3),
                "simple_words_ratio": round(self.simple_words_ratio, 3),
                "complex_words_ratio": round(self.complex_words_ratio, 3),
            },
            "repetition": {
                "score": round(self.repetition_score, 2),
                "most_repeated": [
                    {"word": w, "count": c} for w, c in self.most_repeated_words[:10]
                ],
            },
            "evaluation": {
                "is_appropriate": self.is_appropriate,
                "appropriateness_score": round(self.appropriateness_score, 1),
                "issues": self.issues,
                "recommendations": self.recommendations,
            },
        }

        if self.target_age_group:
            result["target_comparison"] = {
                "target_age_group": self.target_age_group.value,
                **self.target_comparison,
            }

        return result


# =============================================================================
# Escala INFLESZ (interpretación española)
# =============================================================================

INFLESZ_SCALE = [
    (
        80,
        ReadabilityLevel.VERY_EASY,
        "Muy fácil",
        "Lectura muy fácil. Apto para todo público, incluyendo niños.",
    ),
    (
        66,
        ReadabilityLevel.EASY,
        "Fácil",
        "Lectura fácil. Apto para público general sin formación específica.",
    ),
    (
        56,
        ReadabilityLevel.FAIRLY_EASY,
        "Algo fácil",
        "Lectura normal-fácil. Apropiado para educación secundaria.",
    ),
    (
        40,
        ReadabilityLevel.NORMAL,
        "Normal",
        "Lectura normal. Apropiado para público adulto con educación media.",
    ),
    (
        26,
        ReadabilityLevel.FAIRLY_DIFFICULT,
        "Algo difícil",
        "Lectura algo difícil. Requiere atención y cierta formación.",
    ),
    (
        11,
        ReadabilityLevel.DIFFICULT,
        "Difícil",
        "Lectura difícil. Apropiado para público especializado o académico.",
    ),
    (
        0,
        ReadabilityLevel.VERY_DIFFICULT,
        "Muy difícil",
        "Lectura muy difícil. Requiere alto nivel de formación.",
    ),
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
VOWELS = set("aeiouáéíóúüAEIOUÁÉÍÓÚÜ")
STRONG_VOWELS = set("aeoáéó")
WEAK_VOWELS = set("iuíúü")


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
    word = re.sub(r"[^a-záéíóúüñ]", "", word)
    if not word:
        return 0

    syllables = 0
    prev_was_vowel = False
    prev_vowel_strong = False

    for _i, char in enumerate(word):
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
    words = re.findall(r"\b[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+\b", text)
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
        self._sentence_pattern = re.compile(r"[.!?]+(?:\s+|$)|[\n]{2,}", re.UNICODE)
        # Patrón para dividir en párrafos
        self._paragraph_pattern = re.compile(r"\n\s*\n")

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
            total_chars = len(text.replace(" ", "").replace("\n", ""))
            paragraphs = [p.strip() for p in self._paragraph_pattern.split(text) if p.strip()]
            total_paragraphs = len(paragraphs)

            # Dividir en oraciones
            sentences = self._split_sentences(text)
            total_sentences = len(sentences)

            if total_sentences == 0:
                return Result.success(
                    ReadabilityReport(
                        total_chars=total_chars,
                        total_paragraphs=total_paragraphs,
                    )
                )

            # Contar palabras y sílabas
            total_syllables, total_words = count_syllables_text(text)

            if total_words == 0:
                return Result.success(
                    ReadabilityReport(
                        total_chars=total_chars,
                        total_sentences=total_sentences,
                        total_paragraphs=total_paragraphs,
                    )
                )

            # Calcular promedios
            avg_word_length = total_chars / total_words
            avg_syllables_per_word = total_syllables / total_words
            avg_words_per_sentence = total_words / total_sentences
            avg_sentences_per_paragraph = (
                total_sentences / total_paragraphs if total_paragraphs > 0 else 0
            )

            # Calcular índices de legibilidad

            # Índice Flesch-Szigriszt (adaptación española)
            # IFSZ = 206.84 - 62.3 * (sílabas/palabras) - 1.02 * (palabras/oraciones)
            flesch_szigriszt = (
                206.84 - (62.3 * avg_syllables_per_word) - (1.02 * avg_words_per_sentence)
            )
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
                if re.search(r"\b[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+\b", sent):
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

    def analyze_for_age(
        self,
        text: str,
        target_age_group: AgeGroup | None = None,
    ) -> Result[AgeReadabilityReport]:
        """
        Analizar legibilidad orientada a grupos de edad infantil/juvenil.

        Proporciona métricas específicas para literatura infantil como:
        - Proporción de palabras de alta frecuencia (sight words)
        - Complejidad del vocabulario
        - Patrones de repetición
        - Estimación de edad lectora

        Args:
            text: Texto a analizar
            target_age_group: Grupo de edad objetivo (opcional, para comparación)

        Returns:
            Result con AgeReadabilityReport
        """
        if not text or not text.strip():
            return Result.success(AgeReadabilityReport())

        try:
            # Primero, análisis base de legibilidad
            base_result = self.analyze(text)
            if base_result.is_failure:
                return Result.failure(base_result.error)

            base_report = base_result.value

            # Extraer palabras
            words = re.findall(r"\b[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+\b", text.lower())
            total_words = len(words)

            if total_words == 0:
                return Result.success(AgeReadabilityReport())

            # Contar sight words
            sight_word_count = sum(1 for w in words if w in SPANISH_SIGHT_WORDS)
            sight_word_ratio = sight_word_count / total_words

            # Vocabulario único y diversidad
            word_counts = {}
            for w in words:
                word_counts[w] = word_counts.get(w, 0) + 1

            unique_words = len(word_counts)
            vocabulary_diversity = unique_words / total_words

            # Clasificar por complejidad silábica
            simple_words = 0  # 1-2 sílabas
            complex_words = 0  # 4+ sílabas

            for word in words:
                syllables = count_syllables_spanish(word)
                if syllables <= 2:
                    simple_words += 1
                elif syllables >= 4:
                    complex_words += 1

            simple_words_ratio = simple_words / total_words
            complex_words_ratio = complex_words / total_words

            # Calcular score de repetición (mayor = más repetición)
            # Útil para libros infantiles donde la repetición es deseable
            if unique_words > 0:
                repetition_score = (total_words - unique_words) / total_words * 100
            else:
                repetition_score = 0

            # Palabras más repetidas (excluyendo sight words básicas)
            content_word_counts = {w: c for w, c in word_counts.items() if c > 1 and len(w) > 2}
            most_repeated = sorted(content_word_counts.items(), key=lambda x: x[1], reverse=True)[
                :15
            ]

            # Estimar grupo de edad
            estimated_age_group = self._estimate_age_group(
                flesch_score=base_report.flesch_szigriszt,
                avg_words_per_sentence=base_report.avg_words_per_sentence,
                avg_syllables_per_word=base_report.avg_syllables_per_word,
                sight_word_ratio=sight_word_ratio,
                total_words=total_words,
            )

            thresholds = AGE_GROUP_THRESHOLDS.get(estimated_age_group, {})
            estimated_age_range = thresholds.get("age_range", "Adulto")
            estimated_grade_level = thresholds.get("grade", "")

            # Evaluar adecuación al grupo objetivo
            issues = []
            recommendations = []
            appropriateness_score = 100.0
            target_comparison = {}

            if target_age_group:
                target_thresholds = AGE_GROUP_THRESHOLDS.get(target_age_group, {})

                # Comparar con umbrales del grupo objetivo
                if target_thresholds:
                    max_wps = target_thresholds.get("max_words_per_sentence", 25)
                    max_spw = target_thresholds.get("max_syllables_per_word", 3.0)
                    min_sight = target_thresholds.get("min_sight_word_ratio", 0.0)

                    # Evaluar longitud de oraciones
                    if base_report.avg_words_per_sentence > max_wps:
                        diff = base_report.avg_words_per_sentence - max_wps
                        issues.append(
                            f"Oraciones demasiado largas para {target_thresholds.get('age_range', '')} "
                            f"(promedio {base_report.avg_words_per_sentence:.1f}, máximo recomendado {max_wps})"
                        )
                        appropriateness_score -= min(30, diff * 3)
                        recommendations.append(
                            f"Reducir la longitud de las oraciones a máximo {max_wps} palabras."
                        )

                    # Evaluar complejidad de palabras
                    if base_report.avg_syllables_per_word > max_spw:
                        diff = base_report.avg_syllables_per_word - max_spw
                        issues.append(
                            f"Vocabulario complejo para {target_thresholds.get('age_range', '')} "
                            f"(promedio {base_report.avg_syllables_per_word:.2f} sílabas/palabra)"
                        )
                        appropriateness_score -= min(30, diff * 15)
                        recommendations.append("Usar palabras más cortas y sencillas.")

                    # Evaluar sight words
                    if sight_word_ratio < min_sight:
                        diff = min_sight - sight_word_ratio
                        issues.append(
                            f"Pocas palabras de alta frecuencia para primeros lectores "
                            f"({sight_word_ratio:.1%}, mínimo recomendado {min_sight:.1%})"
                        )
                        appropriateness_score -= min(20, diff * 100)
                        recommendations.append(
                            "Incluir más palabras de uso frecuente (el, la, es, tiene, etc.)."
                        )

                    # Palabras complejas
                    if target_age_group in (AgeGroup.BOARD_BOOK, AgeGroup.PICTURE_BOOK):
                        if complex_words_ratio > 0.05:
                            issues.append(
                                f"Demasiadas palabras complejas ({complex_words_ratio:.1%} con 4+ sílabas)"
                            )
                            appropriateness_score -= 20
                            recommendations.append("Evitar palabras de 4 o más sílabas.")

                    target_comparison = {
                        "target_max_words_per_sentence": max_wps,
                        "actual_words_per_sentence": round(base_report.avg_words_per_sentence, 2),
                        "target_max_syllables": max_spw,
                        "actual_syllables": round(base_report.avg_syllables_per_word, 2),
                        "target_min_sight_ratio": min_sight,
                        "actual_sight_ratio": round(sight_word_ratio, 3),
                    }

            appropriateness_score = max(0, appropriateness_score)
            is_appropriate = appropriateness_score >= 70 and len(issues) == 0

            report = AgeReadabilityReport(
                estimated_age_group=estimated_age_group,
                estimated_age_range=estimated_age_range,
                estimated_grade_level=estimated_grade_level,
                flesch_szigriszt=base_report.flesch_szigriszt,
                total_words=total_words,
                total_sentences=base_report.total_sentences,
                avg_words_per_sentence=base_report.avg_words_per_sentence,
                avg_syllables_per_word=base_report.avg_syllables_per_word,
                sight_word_count=sight_word_count,
                sight_word_ratio=sight_word_ratio,
                unique_words=unique_words,
                vocabulary_diversity=vocabulary_diversity,
                simple_words_ratio=simple_words_ratio,
                complex_words_ratio=complex_words_ratio,
                repetition_score=repetition_score,
                most_repeated_words=most_repeated,
                is_appropriate=is_appropriate,
                appropriateness_score=appropriateness_score,
                issues=issues,
                recommendations=recommendations,
                target_age_group=target_age_group,
                target_comparison=target_comparison,
            )

            return Result.success(report)

        except Exception as e:
            logger.error(f"Error en análisis de legibilidad por edad: {e}", exc_info=True)
            error = NLPError(
                message=f"Error en análisis de legibilidad por edad: {e}",
                severity=ErrorSeverity.MEDIUM,
            )
            return Result.failure(error)

    def _estimate_age_group(
        self,
        flesch_score: float,
        avg_words_per_sentence: float,
        avg_syllables_per_word: float,
        sight_word_ratio: float,
        total_words: int,
    ) -> AgeGroup:
        """
        Estimar grupo de edad basado en métricas de legibilidad.

        Combina múltiples factores para una estimación más precisa.
        """
        # Puntajes por cada métrica
        scores = {
            AgeGroup.BOARD_BOOK: 0,
            AgeGroup.PICTURE_BOOK: 0,
            AgeGroup.EARLY_READER: 0,
            AgeGroup.CHAPTER_BOOK: 0,
            AgeGroup.MIDDLE_GRADE: 0,
            AgeGroup.YOUNG_ADULT: 0,
            AgeGroup.ADULT: 0,
        }

        # Factor: longitud total del texto
        if total_words < 300:
            scores[AgeGroup.BOARD_BOOK] += 3
        elif total_words < 1000:
            scores[AgeGroup.PICTURE_BOOK] += 2
            scores[AgeGroup.BOARD_BOOK] += 1
        elif total_words < 5000:
            scores[AgeGroup.EARLY_READER] += 2
            scores[AgeGroup.PICTURE_BOOK] += 1
        elif total_words < 15000:
            scores[AgeGroup.CHAPTER_BOOK] += 2
            scores[AgeGroup.EARLY_READER] += 1
        elif total_words < 50000:
            scores[AgeGroup.MIDDLE_GRADE] += 2
            scores[AgeGroup.CHAPTER_BOOK] += 1
        elif total_words < 80000:
            scores[AgeGroup.YOUNG_ADULT] += 2
            scores[AgeGroup.MIDDLE_GRADE] += 1
        else:
            scores[AgeGroup.ADULT] += 2
            scores[AgeGroup.YOUNG_ADULT] += 1

        # Factor: palabras por oración
        if avg_words_per_sentence <= 5:
            scores[AgeGroup.BOARD_BOOK] += 3
        elif avg_words_per_sentence <= 8:
            scores[AgeGroup.PICTURE_BOOK] += 2
            scores[AgeGroup.BOARD_BOOK] += 1
        elif avg_words_per_sentence <= 12:
            scores[AgeGroup.EARLY_READER] += 2
        elif avg_words_per_sentence <= 15:
            scores[AgeGroup.CHAPTER_BOOK] += 2
        elif avg_words_per_sentence <= 20:
            scores[AgeGroup.MIDDLE_GRADE] += 2
        elif avg_words_per_sentence <= 25:
            scores[AgeGroup.YOUNG_ADULT] += 2
        else:
            scores[AgeGroup.ADULT] += 2

        # Factor: sílabas por palabra
        if avg_syllables_per_word <= 2.0:
            scores[AgeGroup.BOARD_BOOK] += 2
            scores[AgeGroup.PICTURE_BOOK] += 1
        elif avg_syllables_per_word <= 2.2:
            scores[AgeGroup.PICTURE_BOOK] += 2
            scores[AgeGroup.EARLY_READER] += 1
        elif avg_syllables_per_word <= 2.4:
            scores[AgeGroup.EARLY_READER] += 2
        elif avg_syllables_per_word <= 2.6:
            scores[AgeGroup.CHAPTER_BOOK] += 2
        elif avg_syllables_per_word <= 2.8:
            scores[AgeGroup.MIDDLE_GRADE] += 2
        elif avg_syllables_per_word <= 3.0:
            scores[AgeGroup.YOUNG_ADULT] += 2
        else:
            scores[AgeGroup.ADULT] += 2

        # Factor: proporción de sight words
        if sight_word_ratio >= 0.7:
            scores[AgeGroup.BOARD_BOOK] += 2
        elif sight_word_ratio >= 0.5:
            scores[AgeGroup.PICTURE_BOOK] += 2
        elif sight_word_ratio >= 0.4:
            scores[AgeGroup.EARLY_READER] += 1
        elif sight_word_ratio >= 0.3:
            scores[AgeGroup.CHAPTER_BOOK] += 1

        # Factor: Flesch score
        if flesch_score >= 90:
            scores[AgeGroup.BOARD_BOOK] += 2
            scores[AgeGroup.PICTURE_BOOK] += 1
        elif flesch_score >= 80:
            scores[AgeGroup.PICTURE_BOOK] += 2
            scores[AgeGroup.EARLY_READER] += 1
        elif flesch_score >= 70:
            scores[AgeGroup.EARLY_READER] += 2
            scores[AgeGroup.CHAPTER_BOOK] += 1
        elif flesch_score >= 60:
            scores[AgeGroup.CHAPTER_BOOK] += 2
        elif flesch_score >= 50:
            scores[AgeGroup.MIDDLE_GRADE] += 2
        elif flesch_score >= 40:
            scores[AgeGroup.YOUNG_ADULT] += 2
        else:
            scores[AgeGroup.ADULT] += 2

        # Retornar el grupo con mayor puntuación
        return max(scores.items(), key=lambda x: x[1])[0]


# =============================================================================
# Singleton factory
# =============================================================================


@lazy_singleton
def get_readability_analyzer() -> ReadabilityAnalyzer:
    """Obtener instancia singleton del analizador de legibilidad."""
    return ReadabilityAnalyzer()


def reset_readability_analyzer() -> None:
    """Resetear instancia (para testing)."""
    get_readability_analyzer.reset()
