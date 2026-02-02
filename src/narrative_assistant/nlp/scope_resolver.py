"""
Resolución de scope gramatical para vinculación de entidades y atributos.

Reemplaza ventanas de caracteres fijas (400, 500 chars) con scope basado en
unidades lingüísticas reales: oraciones, párrafos y relaciones de dependencia.

Uso:
    from narrative_assistant.nlp.scope_resolver import ScopeResolver

    resolver = ScopeResolver(doc, text)
    subject = resolver.find_subject_for_predicate(token)
    entity = resolver.find_nearest_entity_by_scope(position, entity_mentions)
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

from . import morpho_utils

logger = logging.getLogger(__name__)

# Límite de seguridad en caracteres (fallback si scope lingüístico falla)
MAX_CHAR_FALLBACK = 1500

# Número de oraciones vecinas a considerar para scope
SENTENCE_WINDOW = 3


@dataclass
class ScopeSpan:
    """Rango de caracteres de un scope lingüístico."""
    start: int
    end: int
    scope_type: str  # "sentence", "paragraph", "chapter"

    @property
    def length(self) -> int:
        return self.end - self.start

    def contains(self, position: int) -> bool:
        return self.start <= position < self.end


class ScopeResolver:
    """
    Resuelve scope lingüístico para vinculación de entidades.

    En vez de usar una ventana fija de N caracteres, usa:
    1. Oración actual + N oraciones previas (sentence_scope)
    2. Límites de párrafo (paragraph_scope)
    3. Relaciones de dependencia para encontrar sujeto gramatical
    """

    def __init__(self, doc, text: str):
        """
        Args:
            doc: Documento spaCy procesado
            text: Texto completo del documento
        """
        self.doc = doc
        self.text = text
        self._paragraph_boundaries = self._compute_paragraph_boundaries()
        self._sentence_spans = self._compute_sentence_spans()

    def _compute_paragraph_boundaries(self) -> list[tuple[int, int]]:
        """Calcula los límites de todos los párrafos del texto."""
        boundaries = []
        start = 0
        for match in re.finditer(r"\n\s*\n", self.text):
            end = match.start()
            if end > start:
                boundaries.append((start, end))
            start = match.end()
        # Último párrafo
        if start < len(self.text):
            boundaries.append((start, len(self.text)))
        return boundaries

    def _compute_sentence_spans(self) -> list[tuple[int, int]]:
        """Calcula los spans de todas las oraciones del doc."""
        spans = []
        for sent in self.doc.sents:
            spans.append((sent.start_char, sent.end_char))
        return spans

    def sentence_scope(
        self, position: int, window: int = SENTENCE_WINDOW
    ) -> ScopeSpan:
        """
        Retorna el scope de oración actual + N oraciones previas.

        Args:
            position: Posición en caracteres del elemento a resolver
            window: Número de oraciones previas a incluir (default 3)

        Returns:
            ScopeSpan con el rango de oraciones
        """
        # Encontrar índice de la oración que contiene esta posición
        current_idx = None
        for i, (start, end) in enumerate(self._sentence_spans):
            if start <= position < end:
                current_idx = i
                break
            # Si la posición cae entre oraciones, usar la siguiente
            if position < start:
                current_idx = max(0, i - 1)
                break

        if current_idx is None:
            # Posición fuera de rango, usar última oración
            current_idx = len(self._sentence_spans) - 1

        # Scope = oración actual + `window` oraciones previas
        start_idx = max(0, current_idx - window)
        scope_start = self._sentence_spans[start_idx][0]
        scope_end = self._sentence_spans[current_idx][1]

        return ScopeSpan(
            start=scope_start,
            end=scope_end,
            scope_type="sentence",
        )

    def paragraph_scope(self, position: int) -> ScopeSpan:
        """
        Retorna el scope del párrafo que contiene la posición.

        Args:
            position: Posición en caracteres

        Returns:
            ScopeSpan del párrafo
        """
        for start, end in self._paragraph_boundaries:
            if start <= position < end:
                return ScopeSpan(start=start, end=end, scope_type="paragraph")

        # Fallback: todo el texto
        return ScopeSpan(
            start=0, end=len(self.text), scope_type="paragraph"
        )

    def find_subject_for_predicate(self, predicate_token) -> Optional[str]:
        """
        Dado un token predicativo (adjetivo, participio), encuentra el sujeto.

        Usa el árbol de dependencias de spaCy para buscar el sujeto
        gramatical, en vez de buscar la entidad más cercana en chars.

        Ejemplo: "Juan era alto." → para "alto", devuelve "Juan"
        Ejemplo: "Las manos de María eran delicadas." → para "delicadas", devuelve "manos"

        Args:
            predicate_token: Token adjetivo/participio/sustantivo predicativo

        Returns:
            Texto del sujeto encontrado, o None
        """
        # Caso 1: El predicado depende directamente de un verbo copulativo
        head = predicate_token.head
        if morpho_utils.is_verb(head):
            # Buscar nsubj del verbo
            for child in head.children:
                if child.dep_ in ("nsubj", "nsubj:pass"):
                    return self._expand_entity_span(child)

        # Caso 2: El predicado ES el head (aposición, atributo directo)
        for child in predicate_token.children:
            if child.dep_ in ("nsubj", "nsubj:pass"):
                return self._expand_entity_span(child)

        # Caso 3: Buscar en ancestros (cadena de dependencias)
        current = predicate_token
        for _ in range(5):  # Máximo 5 niveles
            if current.head == current:
                break
            current = current.head
            if morpho_utils.is_verb(current):
                for child in current.children:
                    if child.dep_ in ("nsubj", "nsubj:pass"):
                        return self._expand_entity_span(child)

        return None

    def _expand_entity_span(self, token) -> str:
        """
        Expande un token de sujeto a la entidad completa.

        "Juan" → "Juan"
        token que es parte de "Juan García" → "Juan García"
        """
        # Si el token tiene ent_type_, usar el span de la entidad de spaCy
        if token.ent_type_:
            for ent in self.doc.ents:
                if ent.start <= token.i < ent.end:
                    return ent.text

        # Si no, expandir con dependencias (compound, flat)
        tokens_in_span = [token]
        for child in token.children:
            if child.dep_ in ("compound", "flat", "flat:name", "appos"):
                tokens_in_span.append(child)

        tokens_in_span.sort(key=lambda t: t.i)
        return " ".join(t.text for t in tokens_in_span)

    def find_nearest_entity_by_scope(
        self,
        position: int,
        entity_mentions: list[tuple[str, int, int, str]],
        prefer_subject: bool = True,
    ) -> Optional[tuple[str, float]]:
        """
        Encuentra la entidad más relevante para una posición usando scope gramatical.

        Reemplaza _find_nearest_entity() que usaba ventana de 400 chars.

        Estrategia:
        1. Intentar encontrar sujeto gramatical vía dependency parsing
        2. Si no, buscar entidad más cercana en la misma oración
        3. Si no, buscar en oraciones vecinas (scope de oración)
        4. Fallback: proximidad con límite de 1500 chars

        Args:
            position: Posición del atributo/predicado en el texto
            entity_mentions: Lista de (name, start_char, end_char, entity_type)
            prefer_subject: Si True, preferir sujeto gramatical

        Returns:
            Tupla (entity_name, confidence) o None
        """
        if not entity_mentions:
            return None

        # Paso 1: Intentar sujeto gramatical
        if prefer_subject:
            token_at_pos = self._token_at_position(position)
            if token_at_pos:
                subject = self.find_subject_for_predicate(token_at_pos)
                if subject:
                    # Buscar en entity_mentions la que coincida con el sujeto
                    subject_lower = morpho_utils.normalize_name(subject)
                    for name, start, end, etype in entity_mentions:
                        if morpho_utils.normalize_name(name) == subject_lower:
                            return (name, 0.95)  # Alta confianza: sujeto gramatical

        # Paso 2: Buscar en la misma oración
        sent_scope = self.sentence_scope(position, window=0)
        candidates_in_sentence = [
            (name, start, end, etype)
            for name, start, end, etype in entity_mentions
            if sent_scope.contains(start)
        ]

        if candidates_in_sentence:
            # Tomar la más cercana por posición dentro de la oración
            best = min(
                candidates_in_sentence,
                key=lambda x: abs(x[1] - position),
            )
            return (best[0], 0.85)  # Buena confianza: misma oración

        # Paso 3: Buscar en scope de oraciones vecinas
        wider_scope = self.sentence_scope(position, window=SENTENCE_WINDOW)
        candidates_in_scope = [
            (name, start, end, etype)
            for name, start, end, etype in entity_mentions
            if wider_scope.contains(start)
        ]

        if candidates_in_scope:
            best = min(
                candidates_in_scope,
                key=lambda x: abs(x[1] - position),
            )
            # Confianza decreciente por distancia en oraciones
            distance_chars = abs(best[1] - position)
            confidence = max(0.5, 0.8 - (distance_chars / 2000))
            return (best[0], confidence)

        # Paso 4: Respetar límite de párrafo
        para_scope = self.paragraph_scope(position)
        candidates_in_paragraph = [
            (name, start, end, etype)
            for name, start, end, etype in entity_mentions
            if para_scope.contains(start)
        ]

        if candidates_in_paragraph:
            best = min(
                candidates_in_paragraph,
                key=lambda x: abs(x[1] - position),
            )
            return (best[0], 0.45)  # Baja confianza: mismo párrafo pero lejos

        # Paso 5: Fallback con límite de seguridad
        fallback_candidates = [
            (name, start, end, etype)
            for name, start, end, etype in entity_mentions
            if abs(start - position) < MAX_CHAR_FALLBACK
        ]

        if fallback_candidates:
            best = min(
                fallback_candidates,
                key=lambda x: abs(x[1] - position),
            )
            return (best[0], 0.3)  # Muy baja confianza

        return None

    def _token_at_position(self, char_position: int):
        """Encuentra el token de spaCy en una posición de caracteres."""
        for token in self.doc:
            if token.idx <= char_position < token.idx + len(token.text):
                return token
        return None


def find_subject_in_scope(doc, token) -> Optional[str]:
    """
    Función de conveniencia: dado un token, busca su sujeto gramatical.

    Args:
        doc: Documento spaCy
        token: Token para el que buscar sujeto

    Returns:
        Texto del sujeto, o None
    """
    resolver = ScopeResolver(doc, doc.text)
    return resolver.find_subject_for_predicate(token)
