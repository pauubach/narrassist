"""
Sistema de validación adaptativa de menciones de entidades.

Implementa un sistema de 2 niveles para validar si una mención de entidad
es un referente principal (sujeto/objeto) o un contexto posesivo/genitivo.

Niveles:
1. Regex heurística (1ms): Patrones claros de alta confianza
2. spaCy deps (50ms): Análisis sintáctico para casos ambiguos

Ejemplo:
    >>> validator = create_validator_chain()
    >>> mention = Mention(text="Isabel", position=40)
    >>> context = "El farmacéutico, amante secreto de Isabel, preparó el veneno."
    >>> result = validator.validate(mention, context, {"Isabel"})
    >>> result.is_valid
    False
    >>> result.confidence
    0.90
    >>> result.reasoning
    'Modificador posesivo: amante de Isabel'
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import Protocol

logger = logging.getLogger(__name__)


class ValidationMethod(Enum):
    """Método usado para validación de mención."""

    REGEX = "regex"
    SPACY = "spacy"
    LLM = "llm"  # Futuro


class ConfidenceLevel(Enum):
    """Niveles estándar de confianza."""

    VERY_HIGH = 0.95  # Patrón regex claro
    HIGH = 0.85  # spaCy deps unívoco
    MEDIUM = 0.70  # spaCy deps con excepción
    LOW = 0.50  # Caso ambiguo
    VERY_LOW = 0.30  # Rechazar


@dataclass(frozen=True)
class Mention:
    """Mención de entidad en texto."""

    text: str  # Texto de la entidad (ej: "Isabel")
    position: int  # Posición de inicio en el texto


@dataclass
class ValidationResult:
    """Resultado inmutable de validación de mención."""

    is_valid: bool  # ¿Mención válida (no filtrar)?
    confidence: float  # 0.0-1.0
    method: ValidationMethod  # Método usado
    reasoning: str  # Explicación para debugging
    metadata: dict  # Info adicional (deps, patterns, etc.)

    def should_accept(self, threshold: float = 0.7) -> bool:
        """¿Aceptar mención automáticamente?"""
        return self.is_valid and self.confidence >= threshold

    def needs_review(self, low: float = 0.4, high: float = 0.85) -> bool:
        """¿Requiere revisión manual?"""
        return low <= self.confidence < high


class MentionValidator(Protocol):
    """Protocolo para validadores de menciones (permite extensión)."""

    def validate(
        self, mention: Mention, context: str, entities: set[str]
    ) -> ValidationResult:
        """
        Valida si una mención debe mantenerse o filtrarse.

        Args:
            mention: Mención a validar
            context: Texto completo o contexto amplio
            entities: Set de nombres de entidades conocidas

        Returns:
            ValidationResult con decisión y confianza
        """
        ...


class RegexValidator:
    """
    Validador basado en patrones regex (Nivel 1).

    Detecta casos claros de alta confianza sin necesidad de parsing sintáctico.
    """

    # Patrones de alta confianza para FILTRAR (contextos posesivos)
    POSSESSIVE_PATTERNS = {
        # "el amante de Isabel" → FILTRAR
        "possessive_de": r"\b(el|la|los|las|un|una)\s+([a-záéíóúñü]+(?:\s+[a-záéíóúñü]+)*)\s+de[l]?\s*$",
        # "casa de María" → FILTRAR
        "possessive_simple": r"\b([a-záéíóúñü]+)\s+de[l]?\s*$",
    }

    # Patrones de alta confianza para MANTENER (sujetos claros)
    SUBJECT_PATTERNS = {
        # "Isabel preparó..." → MANTENER
        "sentence_start_verb": r"^{entity}\s+(preparó|ordenó|entró|salió|llegó|vio|dijo|fue|era|es|estaba|había)",
        # Inicio de oración con mayúscula → MANTENER
        "sentence_start": r"^\s*{entity}\s+",
    }

    # Verbos de comunicación (excepción: NO filtrar "habla de/a Isabel")
    COMMUNICATION_VERBS = {
        "habla",
        "hablaba",
        "hablan",
        "trata",
        "trataba",
        "tratan",
        "menciona",
        "mencionaba",
        "mencionan",
        "mencionó",  # Añadido pasado
        "dice",
        "decía",
        "dicen",
        "dijo",  # Añadido pasado
        "cuenta",
        "contaba",
        "cuentan",
        "contó",  # Añadido pasado
        "narra",
        "narraba",
        "narran",
        "narró",  # Añadido pasado
    }

    # Palabras a excluir como sustantivos
    EXCLUDED_WORDS = {"de", "del", "al", "el", "la", "los", "las", "y", "o"}

    def __init__(self, next_validator: MentionValidator | None = None):
        """
        Inicializa validador regex.

        Args:
            next_validator: Siguiente validador en la cadena (Chain of Responsibility)
        """
        self.next = next_validator
        self._compiled_patterns = self._compile_patterns()

    @lru_cache(maxsize=1)
    def _compile_patterns(self) -> dict:
        """Compila patrones regex una sola vez."""
        compiled = {}
        for name, pattern in self.POSSESSIVE_PATTERNS.items():
            compiled[name] = re.compile(pattern, re.IGNORECASE)
        return compiled

    def validate(
        self, mention: Mention, context: str, entities: set[str]
    ) -> ValidationResult:
        """
        Valida mención usando patrones regex.

        Returns:
            ValidationResult con alta confianza si match claro,
            o delega al siguiente validador si caso ambiguo.
        """
        # Extraer contexto antes de la mención (50 chars)
        mention_start = mention.position
        mention_end = mention.position + len(mention.text)
        context_start = max(0, mention_start - 50)
        before = context[context_start:mention_start]

        # NIVEL 1A: Detectar posesivos claros → FILTRAR
        possessive_result = self._check_possessive_patterns(mention, before)
        if possessive_result:
            return possessive_result

        # NIVEL 1B: Detectar sujetos claros → MANTENER
        subject_result = self._check_subject_patterns(mention, context, mention_start)
        if subject_result:
            return subject_result

        # NIVEL 1C: Delegar al siguiente nivel (spaCy) si ambiguo
        if self.next:
            return self.next.validate(mention, context, entities)

        # Sin siguiente nivel, aceptar con confianza baja
        return ValidationResult(
            is_valid=True,  # Default: aceptar si no hay evidencia contraria
            confidence=0.60,
            method=ValidationMethod.REGEX,
            reasoning="No match con patrones regex claros",
            metadata={},
        )

    def _check_possessive_patterns(
        self, mention: Mention, before: str
    ) -> ValidationResult | None:
        """
        Detecta patrones posesivos claros.

        Returns:
            ValidationResult si match claro, None si ambiguo.
        """
        # Patrón principal: "el SUSTANTIVO de ENTIDAD"
        possessive_pattern = self._compiled_patterns["possessive_de"]
        match = possessive_pattern.search(before)

        if match:
            noun_phrase = match.group(2).lower().strip()

            # Si hay al menos una palabra sustantiva, es posesivo
            words = noun_phrase.split()
            substantive_words = [w for w in words if w not in self.EXCLUDED_WORDS]

            if substantive_words:
                # Excepción: verbo de comunicación
                last_word = substantive_words[-1]
                if last_word in self.COMMUNICATION_VERBS:
                    return ValidationResult(
                        is_valid=True,
                        confidence=0.75,
                        method=ValidationMethod.REGEX,
                        reasoning=f"Excepción: verbo comunicativo '{last_word}'",
                        metadata={"verb": last_word, "pattern": "communication"},
                    )

                # Posesivo claro → FILTRAR
                return ValidationResult(
                    is_valid=False,
                    confidence=0.95,
                    method=ValidationMethod.REGEX,
                    reasoning=f"Patrón posesivo claro: '{match.group(2)} de {mention.text}'",
                    metadata={"pattern": "possessive_de", "noun": match.group(2)},
                )

        # Patrón simple: "SUSTANTIVO de ENTIDAD" (sin artículo)
        simple_pattern = re.compile(
            r"\b([a-záéíóúñü]+)\s+de[l]?\s*$", re.IGNORECASE
        )
        simple_match = simple_pattern.search(before)

        if simple_match:
            word = simple_match.group(1).lower()

            # Excepción: verbo de comunicación
            if word in self.COMMUNICATION_VERBS:
                return ValidationResult(
                    is_valid=True,
                    confidence=0.75,
                    method=ValidationMethod.REGEX,
                    reasoning=f"Excepción: verbo comunicativo '{word}'",
                    metadata={"verb": word, "pattern": "communication"},
                )

            # Sustantivo posesivo
            if word not in self.EXCLUDED_WORDS:
                return ValidationResult(
                    is_valid=False,
                    confidence=0.90,
                    method=ValidationMethod.REGEX,
                    reasoning=f"Patrón posesivo simple: '{word} de {mention.text}'",
                    metadata={"pattern": "possessive_simple", "noun": word},
                )

        return None  # No match claro

    def _check_subject_patterns(
        self, mention: Mention, context: str, mention_start: int
    ) -> ValidationResult | None:
        """
        Detecta sujetos claros (inicio de oración + verbo).

        Returns:
            ValidationResult si match claro, None si ambiguo.
        """
        # Extraer contexto antes (para verificar "verbo a ENTIDAD")
        context_start = max(0, mention_start - 50)
        before = context[context_start:mention_start]
        mention_end = mention_start + len(mention.text)
        after = context[mention_end : mention_end + 50]

        # ===================================================================
        # PATRONES ADICIONALES ESPAÑOLES (Mejora 6)
        # ===================================================================

        # Patrón 1: GERUNDIO - "siendo Isabel la reina"
        gerundio_pattern = re.compile(
            r"\b(siendo|estando|habiendo|viniendo|yendo)\s*$", re.IGNORECASE
        )
        if gerundio_pattern.search(before):
            return ValidationResult(
                is_valid=True,
                confidence=0.88,
                method=ValidationMethod.REGEX,
                reasoning=f"Construcción con gerundio: '{gerundio_pattern.search(before).group(1)} {mention.text}'",
                metadata={"pattern": "gerundio"},
            )

        # Patrón 2: PASIVA - "fue escrito por Isabel"
        pasiva_pattern = re.compile(
            r"\bpor\s*$", re.IGNORECASE
        )
        if pasiva_pattern.search(before):
            # Verificar que antes hay verbo en pasiva
            before_extended = context[max(0, mention_start - 100):mention_start]
            if re.search(r"\b(fue|fueron|era|eran|ha sido|había sido)\s+\w+\s+por\s*$", before_extended, re.IGNORECASE):
                return ValidationResult(
                    is_valid=True,
                    confidence=0.90,
                    method=ValidationMethod.REGEX,
                    reasoning=f"Complemento agente (pasiva): 'por {mention.text}'",
                    metadata={"pattern": "passive_agent"},
                )

        # Patrón 3: VOCATIVO - "¡Isabel, ven aquí!"
        vocativo_pattern = re.compile(
            r"[¡!]\s*$", re.IGNORECASE
        )
        if vocativo_pattern.search(before) and re.match(r"\s*[,!]", after):
            return ValidationResult(
                is_valid=True,
                confidence=0.92,
                method=ValidationMethod.REGEX,
                reasoning=f"Vocativo (llamada directa): '¡{mention.text}!'",
                metadata={"pattern": "vocative"},
            )

        # Patrón 4: APOSICIÓN - "la reina, Isabel, entró" o "su hermana, María, era"
        aposicion_pattern = re.compile(
            r",\s*$", re.IGNORECASE
        )
        if aposicion_pattern.search(before) and re.match(r"\s*,", after):
            # Verificar que antes hay sustantivo con determinante (probablemente aposición)
            if re.search(r"\b(el|la|los|las|su|sus|mi|mis|tu|tus)\s+\w+\s*,\s*$", before, re.IGNORECASE):
                return ValidationResult(
                    is_valid=True,
                    confidence=0.88,
                    method=ValidationMethod.REGEX,
                    reasoning=f"Aposición: 'X, {mention.text}, ...'",
                    metadata={"pattern": "apposition"},
                )

        # ===================================================================
        # PATRONES ORIGINALES
        # ===================================================================

        # Patrón: "VERBO a ENTIDAD" (objeto directo con preposición "a")
        # Ej: "Mencionó a Roberto", "Vio a María"
        verb_a_pattern = re.compile(
            r"\b([a-záéíóúñü]+)\s+a\s*$", re.IGNORECASE
        )
        verb_a_match = verb_a_pattern.search(before)
        if verb_a_match:
            verb = verb_a_match.group(1).lower()
            # Lista amplia de verbos que toman objeto directo con "a"
            if verb in self.COMMUNICATION_VERBS or verb in {
                "vio", "vieron", "ve", "ver", "encuentra", "encontró",
                "conoció", "conoce", "ayudó", "ayuda"
            }:
                return ValidationResult(
                    is_valid=True,
                    confidence=0.85,
                    method=ValidationMethod.REGEX,
                    reasoning=f"Objeto directo: '{verb} a {mention.text}'",
                    metadata={"verb": verb, "pattern": "verb_a"},
                )

        # Verificar si está al inicio de oración (después de punto o inicio de texto)
        if mention_start < 3 or (
            mention_start > 0 and context[mention_start - 2] == "."
        ):
            # Patrones de verbos típicos
            verb_pattern = re.compile(
                r"^\s+(preparó|ordenó|entró|salió|llegó|vio|dijo|fue|era|es|estaba|había|hizo|tomó|cogió)",
                re.IGNORECASE,
            )
            if verb_pattern.match(after):
                return ValidationResult(
                    is_valid=True,
                    confidence=0.95,
                    method=ValidationMethod.REGEX,
                    reasoning="Sujeto claro: inicio de oración + verbo",
                    metadata={"pattern": "sentence_start_verb"},
                )

            # Al menos inicio de oración → alta probabilidad de sujeto
            return ValidationResult(
                is_valid=True,
                confidence=0.82,
                method=ValidationMethod.REGEX,
                reasoning="Inicio de oración (probable sujeto)",
                metadata={"pattern": "sentence_start"},
            )

        return None  # No match claro


class SpacyValidator:
    """
    Validador basado en análisis sintáctico con spaCy (Nivel 2).

    Analiza dependencias sintácticas para determinar el rol gramatical
    de la mención en la oración.
    """

    # Roles sintácticos que deben FILTRARSE (NO son referentes principales)
    FILTER_DEP_LABELS = {
        "nmod",  # Modificador nominal: "el amante de Isabel"
        "nmod:poss",  # Posesivo: "su casa"
        "case",  # Marcador de caso: "de" en "de Isabel"
        "fixed",  # Expresión fija: "de acuerdo"
    }

    # Roles sintácticos que deben MANTENERSE (SÍ son referentes principales)
    KEEP_DEP_LABELS = {
        "nsubj",  # Sujeto nominal
        "nsubj:pass",  # Sujeto pasivo
        "csubj",  # Sujeto oracional
        "obj",  # Objeto directo
        "dobj",  # Objeto directo (alias)
        "iobj",  # Objeto indirecto
        "ROOT",  # Raíz de la oración
        "conj",  # Conjunción: "María y Isabel"
        "appos",  # Aposición: "la reina, Isabel"
        "vocative",  # Vocativo: "¡María, ven aquí!"
    }

    # Verbos de comunicación (excepción para obl)
    COMMUNICATION_VERBS = {
        "hablar",
        "tratar",
        "mencionar",
        "decir",
        "contar",
        "narrar",
        "relatar",
        "referirse",
        "aludir",
        "comentar",
    }

    def __init__(self, nlp=None, next_validator: MentionValidator | None = None):
        """
        Inicializa validador spaCy.

        Args:
            nlp: Modelo spaCy cargado (si None, se carga bajo demanda)
            next_validator: Siguiente validador (LLM futuro)
        """
        self._nlp = nlp
        self.next = next_validator

    @property
    def nlp(self):
        """Lazy loading del modelo spaCy."""
        if self._nlp is None:
            from narrative_assistant.nlp.spacy_gpu import load_spacy_model

            self._nlp = load_spacy_model()
        return self._nlp

    def validate(
        self, mention: Mention, context: str, entities: set[str]
    ) -> ValidationResult:
        """
        Valida mención usando análisis sintáctico de spaCy.

        Returns:
            ValidationResult con decisión basada en rol sintáctico.
        """
        try:
            doc = self.nlp(context)
            token = self._find_token(doc, mention.position, mention.text)

            if not token:
                return ValidationResult(
                    is_valid=True,
                    confidence=0.60,
                    method=ValidationMethod.SPACY,
                    reasoning="Token no encontrado en parse (aceptar por defecto)",
                    metadata={},
                )

            # Verificar rol sintáctico
            dep = token.dep_

            # Caso 1: Modificador nominal (potencial posesivo)
            if dep in {"nmod", "nmod:poss"}:
                # Verificar si hay "de/del" en los hijos del HEAD
                has_de = any(
                    child.dep_ == "case" and child.text.lower() in ("de", "del")
                    for child in token.head.children
                )

                if has_de:
                    # Excepción: HEAD es verbo de comunicación
                    if (
                        token.head.pos_ == "VERB"
                        and token.head.lemma_ in self.COMMUNICATION_VERBS
                    ):
                        return ValidationResult(
                            is_valid=True,
                            confidence=0.80,
                            method=ValidationMethod.SPACY,
                            reasoning=f"Objeto de verbo comunicativo: {token.head.lemma_}",
                            metadata={
                                "dep": dep,
                                "head": token.head.text,
                                "verb": token.head.lemma_,
                            },
                        )

                    # Posesivo claro → FILTRAR
                    return ValidationResult(
                        is_valid=False,
                        confidence=0.90,
                        method=ValidationMethod.SPACY,
                        reasoning=f"Modificador posesivo: {token.head.text} de {token.text}",
                        metadata={"dep": dep, "head": token.head.text},
                    )

            # Caso 2: Marcador de caso (no es entidad en sí)
            if dep == "case":
                return ValidationResult(
                    is_valid=False,
                    confidence=0.98,
                    method=ValidationMethod.SPACY,
                    reasoning="Marcador de caso (preposición, no entidad)",
                    metadata={"dep": dep},
                )

            # Caso 3: Oblicuo (verificar si es posesivo o argumento verbal)
            if dep == "obl":
                # Si HEAD es sustantivo → posesivo (FILTRAR)
                if token.head.pos_ == "NOUN":
                    return ValidationResult(
                        is_valid=False,
                        confidence=0.85,
                        method=ValidationMethod.SPACY,
                        reasoning=f"Oblicuo posesivo: {token.head.text}",
                        metadata={"dep": dep, "head": token.head.text},
                    )
                # Si HEAD es verbo de comunicación → MANTENER
                if (
                    token.head.pos_ == "VERB"
                    and token.head.lemma_ in self.COMMUNICATION_VERBS
                ):
                    return ValidationResult(
                        is_valid=True,
                        confidence=0.78,
                        method=ValidationMethod.SPACY,
                        reasoning=f"Argumento de verbo comunicativo: {token.head.lemma_}",
                        metadata={"dep": dep, "verb": token.head.lemma_},
                    )

            # Caso 4: Roles válidos (sujeto, objeto) → MANTENER
            if dep in self.KEEP_DEP_LABELS:
                return ValidationResult(
                    is_valid=True,
                    confidence=0.95,
                    method=ValidationMethod.SPACY,
                    reasoning=f"Rol sintáctico principal: {dep}",
                    metadata={"dep": dep},
                )

            # Caso 5: Rol no cubierto → confianza moderada (delegar a LLM si existe)
            if self.next:
                return self.next.validate(mention, context, entities)

            # Sin LLM, aceptar con confianza moderada
            return ValidationResult(
                is_valid=True,
                confidence=0.70,
                method=ValidationMethod.SPACY,
                reasoning=f"Rol sintáctico ambiguo: {dep}",
                metadata={"dep": dep},
            )

        except Exception as e:
            logger.warning(f"Error en spaCy validation: {e}")
            return ValidationResult(
                is_valid=True,
                confidence=0.60,
                method=ValidationMethod.SPACY,
                reasoning=f"Error en análisis: {str(e)}",
                metadata={"error": str(e)},
            )

    def _find_token(self, doc, char_offset: int, entity_text: str):
        """
        Encuentra el token en el Doc por offset de caracteres.

        Args:
            doc: spacy.Doc parseado
            char_offset: Posición de inicio del token en el texto original
            entity_text: Texto de la entidad (para verificar match)

        Returns:
            spacy.Token si se encuentra, None si no.
        """
        for token in doc:
            # spaCy token.idx es el offset de caracteres
            if token.idx == char_offset and token.text == entity_text:
                return token
            # Match aproximado (dentro de 2 chars, útil si hay whitespace)
            if abs(token.idx - char_offset) <= 2 and token.text.lower() == entity_text.lower():
                return token

        # Fallback: buscar por texto ignorando posición exacta
        for token in doc:
            if token.text.lower() == entity_text.lower():
                # Verificar que está cerca del offset esperado (±10 chars)
                if abs(token.idx - char_offset) <= 10:
                    return token

        return None


def create_validator_chain(
    use_spacy: bool = True, use_llm: bool = False, nlp=None
) -> MentionValidator:
    """
    Crea cadena de validadores según configuración.

    Args:
        use_spacy: Si usar spaCy para análisis sintáctico
        use_llm: Si usar LLM para casos ambiguos (futuro)
        nlp: Modelo spaCy pre-cargado (opcional)

    Returns:
        Validador raíz de la cadena (Chain of Responsibility)

    Ejemplo:
        >>> validator = create_validator_chain()  # Regex + spaCy
        >>> validator = create_validator_chain(use_spacy=False)  # Solo Regex
        >>> validator = create_validator_chain(use_llm=True)  # Regex + spaCy + LLM
    """
    next_validator = None

    # Nivel 3: LLM (futuro)
    if use_llm:
        # TODO: Implementar LLMValidator cuando sea necesario
        logger.warning("LLM validator no implementado aún, usando solo spaCy")

    # Nivel 2: spaCy
    if use_spacy:
        next_validator = SpacyValidator(nlp=nlp, next_validator=next_validator)

    # Nivel 1: Regex
    regex_validator = RegexValidator(next_validator=next_validator)

    return regex_validator


# Compatibilidad con código antiguo
def get_mention_validator(use_spacy: bool = True) -> MentionValidator:
    """
    Obtiene validador de menciones (factory).

    Args:
        use_spacy: Si usar análisis sintáctico con spaCy

    Returns:
        Validador configurado
    """
    return create_validator_chain(use_spacy=use_spacy)
