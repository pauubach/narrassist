"""
Router de complejidad para selección de extractores.

Analiza el texto y determina qué extractores son más apropiados
basándose en:
- Longitud y estructura de oraciones
- Presencia de metáforas y comparaciones
- Indicadores de género literario
- Complejidad gramatical
"""

import logging
import re
from dataclasses import dataclass, field

from .base import ExtractionMethod

logger = logging.getLogger(__name__)


@dataclass
class ComplexityScore:
    """
    Puntuación de complejidad de un texto.

    Attributes:
        score: Puntuación de 0.0 (simple) a 1.0 (muy complejo)
        reasons: Razones de la puntuación
        recommended_extractors: Extractores recomendados
        detected_genre: Género detectado si aplica
    """

    score: float
    reasons: list[str] = field(default_factory=list)
    recommended_extractors: list[ExtractionMethod] = field(default_factory=list)
    detected_genre: str = "realistic"

    @property
    def is_simple(self) -> bool:
        """True si el texto es simple (score < 0.3)."""
        return self.score < 0.3

    @property
    def is_complex(self) -> bool:
        """True si el texto es complejo (score >= 0.6)."""
        return self.score >= 0.6

    @property
    def needs_llm(self) -> bool:
        """True si se recomienda usar LLM."""
        return ExtractionMethod.SEMANTIC_LLM in self.recommended_extractors


class ComplexityRouter:
    """
    Analiza la complejidad del texto y recomienda extractores.

    Criterios de complejidad:
    - Oraciones largas (> 30 palabras)
    - Múltiples cláusulas (comas, punto y coma)
    - Comparaciones y metáforas explícitas
    - Referencias pronominales complejas
    - Vocabulario de género (fantasy, sci-fi)
    - Descripciones con enumeraciones

    Example:
        >>> router = ComplexityRouter()
        >>> result = router.analyze("María tenía ojos azules.")
        >>> print(result.score)  # ~0.1 (simple)
        >>> print(result.recommended_extractors)  # [REGEX, DEPENDENCY]
    """

    # Indicadores de metáforas y comparaciones
    METAPHOR_PATTERNS = [
        r"\bcomo\s+(?:un|una|el|la)\b",  # "ojos como el mar"
        r"\bparec[ií]a\b",  # "parecía una estrella"
        r"\bsemejante\s+a\b",
        r"\btan\s+\w+\s+como\b",  # "tan azules como"
        r"\bser\s+(?:un|una)\s+\w+\s+de\b",  # "era un pozo de"
        r"\bbrillar\s+como\b",
        r"\breflejar\b",
    ]

    # Estructuras gramaticales complejas
    COMPLEX_STRUCTURES = [
        r",\s*(?:que|quien|cual|cuyo|donde)\b",  # Cláusulas relativas
        r";\s*\w",  # Punto y coma
        r"\b(?:aunque|mientras|cuando|si)\b.*,",  # Subordinadas
        r",\s*y\s+(?:que|con)\b",  # Coordinadas complejas
        r"—[^—]+—",  # Incisos con guiones largos
        r"\([^)]{10,}\)",  # Paréntesis largos
    ]

    # Indicadores de género literario
    GENRE_INDICATORS = {
        "fantasy": [
            r"\belfo[s]?\b",
            r"\benano[s]?\b",
            r"\bdrag[oó]n(?:es)?\b",
            r"\bmagia\b",
            r"\bhechiz",
            r"\brunas?\b",
            r"\borco[s]?\b",
            r"\btroll[s]?\b",
            r"\bvampiro[s]?\b",
            r"\bhada[s]?\b",
            r"\bbruj[oa]s?\b",
            r"\bconjuro[s]?\b",
            r"\bencantamiento\b",
            r"\breino\s+de\b",
            r"\bespada\s+m[aá]gica\b",
        ],
        "sci-fi": [
            r"\bescamosa\b",
            r"\bextraterrestre[s]?\b",
            r"\bandroide[s]?\b",
            r"\bciborg[s]?\b",
            r"\bespacial\b",
            r"\bgal[aá]ctic[oa]\b",
            r"\bplaneta\b",
            r"\bnave\b",
            r"\blaser\b",
            r"\bteletransport",
            r"\binteligencia\s+artificial\b",
            r"\brobot[s]?\b",
            r"\balienigena\b",
            r"\bmutante[s]?\b",
        ],
        "realistic": [],  # Por defecto
    }

    # Enumeraciones de atributos
    ENUMERATION_PATTERNS = [
        r"(?:\w+,\s*){2,}\w+\s+y\s+\w+",  # "alto, delgado, moreno y atractivo"
        r"de\s+\w+\s+\w+,\s*(?:\w+\s+){0,2}y\s+\w+",  # "de pelo negro, largo y ondulado"
        r"con\s+\w+\s+\w+\s+y\s+\w+\s+\w+",  # "con ojos azules y cabello rubio"
    ]

    def __init__(
        self,
        complexity_threshold_for_llm: float = 0.7,
    ):
        """
        Inicializa el router.

        Args:
            complexity_threshold_for_llm: Umbral para recomendar LLM
        """
        self.llm_threshold = complexity_threshold_for_llm

        # Compilar patrones
        self._metaphor_re = [re.compile(p, re.IGNORECASE) for p in self.METAPHOR_PATTERNS]
        self._complex_re = [re.compile(p, re.IGNORECASE) for p in self.COMPLEX_STRUCTURES]
        self._enum_re = [re.compile(p, re.IGNORECASE) for p in self.ENUMERATION_PATTERNS]
        self._genre_re = {
            genre: [re.compile(p, re.IGNORECASE) for p in patterns]
            for genre, patterns in self.GENRE_INDICATORS.items()
        }

    def analyze(self, text: str) -> ComplexityScore:
        """
        Analiza la complejidad del texto.

        Args:
            text: Texto a analizar

        Returns:
            ComplexityScore con puntuación y recomendaciones
        """
        score = 0.0
        reasons = []

        # 1. Longitud de oraciones
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if sentences:
            avg_words = sum(len(s.split()) for s in sentences) / len(sentences)
            if avg_words > 40:
                score += 0.25
                reasons.append(f"Oraciones muy largas (avg: {avg_words:.0f} palabras)")
            elif avg_words > 30:
                score += 0.15
                reasons.append(f"Oraciones largas (avg: {avg_words:.0f} palabras)")
            elif avg_words > 20:
                score += 0.05
                reasons.append(f"Oraciones moderadas (avg: {avg_words:.0f} palabras)")

        # 2. Metáforas y comparaciones
        metaphor_count = sum(len(p.findall(text)) for p in self._metaphor_re)
        if metaphor_count > 0:
            metaphor_score = min(0.3, 0.1 * metaphor_count)
            score += metaphor_score
            reasons.append(f"Metáforas/comparaciones detectadas: {metaphor_count}")

        # 3. Estructuras gramaticales complejas
        complex_count = sum(len(p.findall(text)) for p in self._complex_re)
        if complex_count > 0:
            complex_score = min(0.25, 0.08 * complex_count)
            score += complex_score
            reasons.append(f"Estructuras complejas: {complex_count}")

        # 4. Género literario
        genre = self._detect_genre(text)
        if genre != "realistic":
            score += 0.15
            reasons.append(f"Género detectado: {genre}")

        # 5. Enumeraciones de atributos
        enum_count = sum(len(p.findall(text)) for p in self._enum_re)
        if enum_count > 0:
            score += min(0.15, 0.05 * enum_count)
            reasons.append(f"Enumeraciones de atributos: {enum_count}")

        # 6. Referencias pronominales (difíciles de resolver)
        pronoun_patterns = [
            r"\b(?:él|ella|ellos|ellas)\s+(?:tenía|era|llevaba)",
            r"\bsu[s]?\s+(?:ojos|pelo|cabello|rostro)",
        ]
        pronoun_count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in pronoun_patterns)
        if pronoun_count > 2:
            score += 0.1
            reasons.append(f"Referencias pronominales: {pronoun_count}")

        # Normalizar score
        score = min(1.0, score)

        # Determinar extractores recomendados
        recommended = self._recommend_extractors(score, genre)

        logger.debug(
            f"Complexity analysis: score={score:.2f}, genre={genre}, reasons={len(reasons)}"
        )

        return ComplexityScore(
            score=score,
            reasons=reasons,
            recommended_extractors=recommended,
            detected_genre=genre,
        )

    def _detect_genre(self, text: str) -> str:
        """Detecta el género literario del texto."""
        text_lower = text.lower()

        for genre, patterns in self._genre_re.items():
            if genre == "realistic":
                continue

            matches = sum(1 for p in patterns if p.search(text_lower))
            if matches >= 2:  # Al menos 2 indicadores
                return genre

        return "realistic"

    def _recommend_extractors(
        self,
        score: float,
        genre: str,
    ) -> list[ExtractionMethod]:
        """
        Recomienda extractores basándose en complejidad y género.

        Estrategia:
        - Simple (< 0.3): Regex + Dependency (rápido)
        - Medio (0.3-0.6): Dependency + Embeddings
        - Complejo (>= 0.6): Dependency + Embeddings + LLM
        - Fantasy/Sci-fi: Siempre incluir Embeddings (vocabulario inusual)
        """
        recommended = []

        # Regex siempre para casos simples/medianos
        if score < 0.6:
            recommended.append(ExtractionMethod.REGEX)

        # Dependency siempre (backbone del sistema)
        recommended.append(ExtractionMethod.DEPENDENCY)

        # Embeddings para casos medianos o géneros especiales
        if score >= 0.3 or genre != "realistic":
            recommended.append(ExtractionMethod.EMBEDDINGS)

        # LLM solo para casos muy complejos
        if score >= self.llm_threshold:
            recommended.append(ExtractionMethod.SEMANTIC_LLM)

        return recommended

    def should_use_llm(self, text: str) -> bool:
        """
        Determina rápidamente si se debe usar LLM.

        Método de conveniencia para decisiones rápidas.
        """
        result = self.analyze(text)
        return result.needs_llm

    def get_extractors_for_batch(
        self,
        texts: list[str],
    ) -> dict[ExtractionMethod, list[int]]:
        """
        Agrupa textos por extractor recomendado.

        Útil para procesamiento en batch, donde diferentes textos
        pueden ir a diferentes extractores.

        Args:
            texts: Lista de textos a procesar

        Returns:
            Diccionario de método -> índices de textos
        """
        result: dict[ExtractionMethod, list[int]] = {method: [] for method in ExtractionMethod}

        for i, text in enumerate(texts):
            analysis = self.analyze(text)
            for method in analysis.recommended_extractors:
                result[method].append(i)

        return result
