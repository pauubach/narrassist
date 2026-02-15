"""
Detector de violaciones de estilo según tipo de documento.

Detecta problemas que dependen del registro esperado:
- Subjetividad (1ª persona, verbos de opinión) en textos científicos/técnicos
- Imprecisión (cuantificadores vagos) en textos formales
- Falta de hedging (aserciones categóricas sin matizar)
- Lenguaje emocional en contextos objetivos

El detector usa 4 perfiles:
- strict: Científico/técnico (todo activo, confianza alta)
- formal: Ensayo académico (1ª persona warning, hedging activo)
- moderate: Memorias/autoayuda (solo vagos y hedging)
- free: Ficción (detector desactivado)
"""

from __future__ import annotations

import re

from ..base import BaseDetector, CorrectionIssue
from ..config import StyleRegisterConfig
from ..types import CorrectionCategory, StyleRegisterIssueType

# ============================================================================
# Confianza por perfil e issue type
# ============================================================================

# Valor 0.0 = desactivado para este perfil
PROFILE_CONFIDENCE: dict[str, dict[str, float]] = {
    "strict": {
        "first_person": 0.92,
        "opinion_verb": 0.90,
        "vague_quantifier": 0.88,
        "assertion_no_hedging": 0.92,
        "emotional_language": 0.88,
    },
    "formal": {
        "first_person": 0.70,
        "opinion_verb": 0.65,
        "vague_quantifier": 0.78,
        "assertion_no_hedging": 0.80,
        "emotional_language": 0.68,
    },
    "moderate": {
        "first_person": 0.0,
        "opinion_verb": 0.0,
        "vague_quantifier": 0.60,
        "assertion_no_hedging": 0.60,
        "emotional_language": 0.0,
    },
    "free": {
        "first_person": 0.0,
        "opinion_verb": 0.0,
        "vague_quantifier": 0.0,
        "assertion_no_hedging": 0.0,
        "emotional_language": 0.0,
    },
}

# ============================================================================
# Léxicos
# ============================================================================

# Pronombres de primera persona
FIRST_PERSON_PRONOUNS = {
    "yo",
    "mí",
    "conmigo",
    "me",
    "nos",
    "nosotros",
    "nosotras",
    "nuestro",
    "nuestra",
    "nuestros",
    "nuestras",
}

# Formas conjugadas de verbos de opinión en 1ª persona (sing + plural)
OPINION_VERB_FORMS = {
    "creo",
    "creemos",
    "opino",
    "opinamos",
    "pienso",
    "pensamos",
    "considero",
    "consideramos",
    "supongo",
    "suponemos",
    "estimo",
    "estimamos",
    "juzgo",
    "juzgamos",
}

# Cuantificadores vagos
VAGUE_QUANTIFIERS = {
    "varios",
    "varias",
    "muchos",
    "muchas",
    "algunos",
    "algunas",
    "pocos",
    "pocas",
    "bastante",
    "bastantes",
    "cierto",
    "cierta",
    "ciertos",
    "ciertas",
    "numerosos",
    "numerosas",
}

# Marcadores de aserción categórica (sin matiz)
ASSERTION_PHRASES = [
    "demuestra que",
    "prueba que",
    "confirma que",
    "es evidente que",
    "está claro que",
    "es obvio que",
    "es indiscutible que",
    "resulta innegable que",
    "sin lugar a dudas",
]

ASSERTION_ADVERBS = {
    "indudablemente",
    "claramente",
    "evidentemente",
    "obviamente",
    "indiscutiblemente",
    "innegablemente",
    "incuestionablemente",
}

# Marcadores de hedging (presentes cerca de aserción = no alertar)
HEDGING_MARKERS = {
    "sugiere",
    "indica",
    "parece",
    "podría",
    "podrían",
    "posiblemente",
    "probablemente",
    "aparentemente",
    "puede",
    "pueden",
    "cabría",
    "quizá",
    "quizás",
    "tal vez",
}

# Adverbios emocionales impropios en texto objetivo
EMOTIONAL_MARKERS = {
    "sorprendentemente",
    "desgraciadamente",
    "afortunadamente",
    "increíblemente",
    "tristemente",
    "lamentablemente",
    "maravillosamente",
    "dramáticamente",
    "trágicamente",
    "felizmente",
    "desafortunadamente",
    "asombrosamente",
}

# ============================================================================
# Sugerencias deterministas
# ============================================================================

FIRST_PERSON_SUGGESTIONS: dict[str, str] = {
    "nosotros": "Usar construcción impersonal: «Se observó que…» o «Los resultados muestran…»",
    "nosotras": "Usar construcción impersonal: «Se observó que…» o «Los resultados muestran…»",
    "yo": "Usar forma impersonal: «El autor/a considera…» o «Se considera…»",
    "nuestro": "Usar «del presente estudio» o «de este trabajo»",
    "nuestra": "Usar «del presente estudio» o «de esta investigación»",
    "nuestros": "Usar «del presente estudio» o «de estos datos»",
    "nuestras": "Usar «del presente estudio» o «de estas observaciones»",
}

OPINION_VERB_SUGGESTIONS: dict[str, str] = {
    "creo": "«Los datos sugieren que…» o «La evidencia indica que…»",
    "creemos": "«Los datos sugieren que…» o «Los resultados indican que…»",
    "opino": "«Cabe señalar que…» o «Se puede argumentar que…»",
    "opinamos": "«Cabe señalar que…» o «Se puede argumentar que…»",
    "pienso": "«Los hallazgos apuntan a…» o «Se observa que…»",
    "pensamos": "«Los hallazgos apuntan a…» o «Se observa que…»",
    "considero": "«Se considera que…» o «Es razonable concluir que…»",
    "consideramos": "«Se considera que…» o «Es razonable concluir que…»",
    "supongo": "«Es posible que…» o «Podría inferirse que…»",
    "suponemos": "«Es posible que…» o «Podría inferirse que…»",
}

ASSERTION_SUGGESTION = (
    "Considere usar lenguaje de hedging: «sugiere que…», «indica que…», "
    "«los datos apuntan a…», «podría…»"
)

EMOTIONAL_SUGGESTION = (
    "En textos objetivos, evite adverbios valorativos. "
    "Presente los datos y deje que el lector valore su importancia."
)

VAGUE_SUGGESTION = "Especifique la cantidad o cite las fuentes concretas."

# ============================================================================
# Regex de diálogo para exención
# ============================================================================

# Patrones de diálogo: raya española, comillas angulares, comillas rectas
_DIALOGUE_RE = re.compile(
    r"(?:"
    r"—[^—\n]+(?:—[^—\n]*—[^—\n]+)*"  # Raya española: —texto— inciso —texto
    r"|«[^»]*»"  # Comillas angulares
    r'|"[^"]*"'  # Comillas rectas dobles
    r")",
    re.UNICODE,
)


class StyleRegisterDetector(BaseDetector):
    """
    Detecta violaciones de estilo según tipo/registro de documento.

    Usa lexicones y regex (sin spaCy) para detectar:
    - Primera persona donde debería ser impersonal
    - Verbos de opinión en contextos objetivos
    - Cuantificadores vagos sin cifras
    - Aserciones categóricas sin hedging
    - Lenguaje emocional en textos objetivos
    """

    def __init__(self, config: StyleRegisterConfig | None = None) -> None:
        self.config = config or StyleRegisterConfig()
        self._profile_conf = PROFILE_CONFIDENCE.get(
            self.config.profile, PROFILE_CONFIDENCE["moderate"]
        )
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compila regex para cada sub-detector."""
        # Primera persona: pronombres
        self._first_person_re = re.compile(
            r"\b(" + "|".join(re.escape(w) for w in FIRST_PERSON_PRONOUNS) + r")\b",
            re.IGNORECASE,
        )
        # Verbos de opinión conjugados
        self._opinion_verb_re = re.compile(
            r"\b(" + "|".join(re.escape(w) for w in OPINION_VERB_FORMS) + r")\b",
            re.IGNORECASE,
        )
        # Cuantificadores vagos
        self._vague_re = re.compile(
            r"\b(" + "|".join(re.escape(w) for w in VAGUE_QUANTIFIERS) + r")\b",
            re.IGNORECASE,
        )
        # Frases de aserción
        self._assertion_phrase_re = re.compile(
            r"\b(" + "|".join(re.escape(p) for p in ASSERTION_PHRASES) + r")\b",
            re.IGNORECASE,
        )
        # Adverbios de aserción
        self._assertion_adverb_re = re.compile(
            r"\b(" + "|".join(re.escape(w) for w in ASSERTION_ADVERBS) + r")\b",
            re.IGNORECASE,
        )
        # Hedging (para contexto de aserciones)
        self._hedging_re = re.compile(
            r"\b(" + "|".join(re.escape(w) for w in HEDGING_MARKERS) + r")\b",
            re.IGNORECASE,
        )
        # Lenguaje emocional
        self._emotional_re = re.compile(
            r"\b(" + "|".join(re.escape(w) for w in EMOTIONAL_MARKERS) + r")\b",
            re.IGNORECASE,
        )
        # Verbos 1ª persona plural (-mos) heurístico
        self._first_person_verb_re = re.compile(
            r"\b(encontramos|observamos|analizamos|concluimos|proponemos"
            r"|realizamos|obtuvimos|determinamos|identificamos|evaluamos"
            r"|comprobamos|verificamos|demostramos|presentamos|describimos"
            r"|medimos|calculamos|seleccionamos|comparamos|aplicamos)\b",
            re.IGNORECASE,
        )

    @property
    def category(self) -> CorrectionCategory:
        return CorrectionCategory.STYLE_REGISTER

    @property
    def requires_spacy(self) -> bool:
        return False

    def detect(
        self,
        text: str,
        chapter_index: int | None = None,
        **kwargs,  # noqa: ARG002
    ) -> list[CorrectionIssue]:
        """Ejecuta todos los sub-detectores habilitados."""
        if not self.config.enabled:
            return []

        # Exención de diálogo: reemplazar con espacios (mantener posiciones)
        clean_text = self._mask_dialogue(text) if self.config.skip_dialogue else text

        issues: list[CorrectionIssue] = []

        if self.config.detect_first_person and self._is_active("first_person"):
            issues.extend(self._check_first_person(clean_text, text, chapter_index))

        if self.config.detect_opinion_verbs and self._is_active("opinion_verb"):
            issues.extend(self._check_opinion_verbs(clean_text, text, chapter_index))

        if self.config.detect_vague_quantifiers and self._is_active("vague_quantifier"):
            issues.extend(self._check_vague_quantifiers(clean_text, text, chapter_index))

        if self.config.detect_hedging_gaps and self._is_active("assertion_no_hedging"):
            issues.extend(self._check_hedging_gaps(clean_text, text, chapter_index))

        if self.config.detect_emotional_language and self._is_active("emotional_language"):
            issues.extend(self._check_emotional_language(clean_text, text, chapter_index))

        return issues

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_active(self, issue_key: str) -> bool:
        """Verifica si un issue type está activo según el perfil."""
        return self._profile_conf.get(issue_key, 0.0) > 0.0

    def _get_confidence(self, issue_key: str) -> float:
        """Obtiene confianza del perfil para un issue type."""
        return self._profile_conf.get(issue_key, 0.7)

    def _mask_dialogue(self, text: str) -> str:
        """Reemplaza diálogo con espacios, manteniendo posiciones."""
        result = list(text)
        for m in _DIALOGUE_RE.finditer(text):
            for i in range(m.start(), m.end()):
                result[i] = " "
        return "".join(result)

    # ------------------------------------------------------------------
    # Sub-detectores
    # ------------------------------------------------------------------

    def _check_first_person(
        self, clean_text: str, original_text: str, chapter_index: int | None
    ) -> list[CorrectionIssue]:
        """Detecta pronombres y verbos en primera persona."""
        issues: list[CorrectionIssue] = []
        confidence = self._get_confidence("first_person")

        # Pronombres
        for m in self._first_person_re.finditer(clean_text):
            word = m.group(0).lower()
            suggestion = FIRST_PERSON_SUGGESTIONS.get(word)
            issues.append(
                CorrectionIssue(
                    category=self.category.value,
                    issue_type=StyleRegisterIssueType.FIRST_PERSON_PRONOUN.value,
                    start_char=m.start(),
                    end_char=m.end(),
                    text=original_text[m.start() : m.end()],
                    explanation=(
                        f"Pronombre en 1.ª persona «{m.group(0)}» en texto que requiere "
                        f"registro impersonal."
                    ),
                    suggestion=suggestion,
                    confidence=confidence,
                    context=self._extract_context(original_text, m.start(), m.end()),
                    chapter_index=chapter_index,
                    rule_id="STYLE_FIRST_PERSON_PRONOUN",
                )
            )

        # Verbos 1ª persona plural (heurístico)
        for m in self._first_person_verb_re.finditer(clean_text):
            verb = m.group(0)
            issues.append(
                CorrectionIssue(
                    category=self.category.value,
                    issue_type=StyleRegisterIssueType.FIRST_PERSON_VERB.value,
                    start_char=m.start(),
                    end_char=m.end(),
                    text=original_text[m.start() : m.end()],
                    explanation=(
                        f"Verbo en 1.ª persona «{verb}». "
                        f"Considere forma impersonal: «Se {_to_impersonal(verb)}…»"
                    ),
                    suggestion=f"Se {_to_impersonal(verb)}",
                    confidence=confidence,
                    context=self._extract_context(original_text, m.start(), m.end()),
                    chapter_index=chapter_index,
                    rule_id="STYLE_FIRST_PERSON_VERB",
                )
            )

        return issues

    def _check_opinion_verbs(
        self, clean_text: str, original_text: str, chapter_index: int | None
    ) -> list[CorrectionIssue]:
        """Detecta verbos de opinión en contextos objetivos."""
        issues: list[CorrectionIssue] = []
        confidence = self._get_confidence("opinion_verb")

        for m in self._opinion_verb_re.finditer(clean_text):
            word = m.group(0).lower()
            suggestion = OPINION_VERB_SUGGESTIONS.get(word)
            issues.append(
                CorrectionIssue(
                    category=self.category.value,
                    issue_type=StyleRegisterIssueType.OPINION_VERB.value,
                    start_char=m.start(),
                    end_char=m.end(),
                    text=original_text[m.start() : m.end()],
                    explanation=(
                        f"Verbo de opinión «{m.group(0)}» introduce subjetividad. "
                        f"En textos objetivos, prefiera expresiones basadas en datos."
                    ),
                    suggestion=suggestion,
                    confidence=confidence,
                    context=self._extract_context(original_text, m.start(), m.end()),
                    chapter_index=chapter_index,
                    rule_id="STYLE_OPINION_VERB",
                )
            )

        return issues

    def _check_vague_quantifiers(
        self, clean_text: str, original_text: str, chapter_index: int | None
    ) -> list[CorrectionIssue]:
        """Detecta cuantificadores imprecisos."""
        issues: list[CorrectionIssue] = []
        confidence = self._get_confidence("vague_quantifier")

        for m in self._vague_re.finditer(clean_text):
            issues.append(
                CorrectionIssue(
                    category=self.category.value,
                    issue_type=StyleRegisterIssueType.VAGUE_QUANTIFIER.value,
                    start_char=m.start(),
                    end_char=m.end(),
                    text=original_text[m.start() : m.end()],
                    explanation=(
                        f"Cuantificador impreciso «{m.group(0)}». "
                        f"En textos formales, proporcione cifras o cite fuentes."
                    ),
                    suggestion=VAGUE_SUGGESTION,
                    confidence=confidence,
                    context=self._extract_context(original_text, m.start(), m.end()),
                    chapter_index=chapter_index,
                    rule_id="STYLE_VAGUE_QUANTIFIER",
                )
            )

        return issues

    def _check_hedging_gaps(
        self, clean_text: str, original_text: str, chapter_index: int | None
    ) -> list[CorrectionIssue]:
        """Detecta aserciones categóricas sin hedging cercano."""
        issues: list[CorrectionIssue] = []
        confidence = self._get_confidence("assertion_no_hedging")

        # Buscar frases de aserción
        for m in self._assertion_phrase_re.finditer(clean_text):
            if not self._has_hedging_nearby(clean_text, m.start(), m.end()):
                phrase = m.group(0)
                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type=StyleRegisterIssueType.ASSERTION_NO_HEDGING.value,
                        start_char=m.start(),
                        end_char=m.end(),
                        text=original_text[m.start() : m.end()],
                        explanation=(
                            f"Aserción categórica «{phrase}» sin matización. "
                            f"En escritura formal, modere las afirmaciones absolutas."
                        ),
                        suggestion=ASSERTION_SUGGESTION,
                        confidence=confidence,
                        context=self._extract_context(original_text, m.start(), m.end()),
                        chapter_index=chapter_index,
                        rule_id="STYLE_ASSERTION_NO_HEDGING",
                    )
                )

        # Buscar adverbios de aserción
        for m in self._assertion_adverb_re.finditer(clean_text):
            if not self._has_hedging_nearby(clean_text, m.start(), m.end()):
                adverb = m.group(0)
                issues.append(
                    CorrectionIssue(
                        category=self.category.value,
                        issue_type=StyleRegisterIssueType.ASSERTION_NO_HEDGING.value,
                        start_char=m.start(),
                        end_char=m.end(),
                        text=original_text[m.start() : m.end()],
                        explanation=(
                            f"Adverbio categórico «{adverb}» sin matización. "
                            f"Considere si la certeza está respaldada por evidencia."
                        ),
                        suggestion=ASSERTION_SUGGESTION,
                        confidence=confidence * 0.95,
                        context=self._extract_context(original_text, m.start(), m.end()),
                        chapter_index=chapter_index,
                        rule_id="STYLE_ASSERTION_ADVERB",
                    )
                )

        return issues

    def _check_emotional_language(
        self, clean_text: str, original_text: str, chapter_index: int | None
    ) -> list[CorrectionIssue]:
        """Detecta adverbios emocionales impropios en texto objetivo."""
        issues: list[CorrectionIssue] = []
        confidence = self._get_confidence("emotional_language")

        for m in self._emotional_re.finditer(clean_text):
            issues.append(
                CorrectionIssue(
                    category=self.category.value,
                    issue_type=StyleRegisterIssueType.EMOTIONAL_LANGUAGE.value,
                    start_char=m.start(),
                    end_char=m.end(),
                    text=original_text[m.start() : m.end()],
                    explanation=(
                        f"Adverbio valorativo «{m.group(0)}» aporta subjetividad. "
                        f"En textos objetivos, presente los datos sin valoración emocional."
                    ),
                    suggestion=EMOTIONAL_SUGGESTION,
                    confidence=confidence,
                    context=self._extract_context(original_text, m.start(), m.end()),
                    chapter_index=chapter_index,
                    rule_id="STYLE_EMOTIONAL_LANGUAGE",
                )
            )

        return issues

    def _has_hedging_nearby(self, text: str, start: int, end: int, window: int = 200) -> bool:
        """Verifica si hay marcadores de hedging en un radio de N caracteres."""
        ctx_start = max(0, start - window)
        ctx_end = min(len(text), end + window)
        context = text[ctx_start:ctx_end]
        return bool(self._hedging_re.search(context))


def _to_impersonal(verb: str) -> str:
    """Convierte verbo 1ª plural a forma impersonal heurística."""
    verb_lower = verb.lower()
    # -amos → -ó / -emos → -ió / -imos → -ió
    impersonal_map = {
        "encontramos": "encontró",
        "observamos": "observó",
        "analizamos": "analizó",
        "concluimos": "concluyó",
        "proponemos": "propone",
        "realizamos": "realizó",
        "obtuvimos": "obtuvo",
        "determinamos": "determinó",
        "identificamos": "identificó",
        "evaluamos": "evaluó",
        "comprobamos": "comprobó",
        "verificamos": "verificó",
        "demostramos": "demostró",
        "presentamos": "presenta",
        "describimos": "describe",
        "medimos": "midió",
        "calculamos": "calculó",
        "seleccionamos": "seleccionó",
        "comparamos": "comparó",
        "aplicamos": "aplicó",
    }
    return impersonal_map.get(verb_lower, verb_lower)
