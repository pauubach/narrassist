"""
Resolución de scope gramatical para vinculación de entidades y atributos.

Reemplaza ventanas de caracteres fijas (400, 500 chars) con scope basado en
unidades lingüísticas reales: oraciones, párrafos y relaciones de dependencia.

Incluye detección de cláusulas relativas y resolución de identidad copulativa
para manejar correctamente:
- "El hombre que María había visto tenía ojos azules" → ojos azules → El hombre
- "La mujer de ojos verdes que Juan conoció era María" → ojos verdes → María

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

# Artículos del español para matching flexible de nombres
_SPANISH_ARTICLES = frozenset({"el", "la", "los", "las", "un", "una", "unos", "unas"})

# Verbos copulativos para detección de identidad copulativa
_COPULAR_LEMMAS = frozenset({"ser", "estar", "parecer", "resultar"})


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
    4. Detección de cláusulas relativas para filtrar entidades irrelevantes
    5. Identidad copulativa ("X era Y") para resolver sujetos no-entidad
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
        self._rc_spans = self._compute_relative_clause_spans()

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

    def _compute_relative_clause_spans(self) -> list[tuple[int, int, int]]:
        """
        Identifica spans de cláusulas relativas usando el árbol de dependencias.

        Busca tokens con dep_ in ('acl', 'relcl') que son raíces de cláusulas
        relativas que modifican un antecedente nominal.

        Returns:
            Lista de (rc_start_char, rc_end_char, antecedent_token_idx)
        """
        spans = []
        for token in self.doc:
            if token.dep_ in ("acl", "relcl"):
                subtree = list(token.subtree)
                if subtree:
                    rc_start = min(t.idx for t in subtree)
                    rc_end = max(t.idx + len(t.text) for t in subtree)
                    spans.append((rc_start, rc_end, token.head.i))
        return spans

    def is_in_relative_clause(self, char_position: int) -> tuple[bool, Optional[int]]:
        """
        Verifica si una posición de caracteres cae dentro de una cláusula relativa.

        Args:
            char_position: Posición en caracteres a verificar

        Returns:
            Tupla (está_en_rc, índice_token_antecedente). El antecedente es el
            token nominal que la RC modifica, o None si no está en RC.
        """
        for rc_start, rc_end, antecedent_idx in self._rc_spans:
            if rc_start <= char_position < rc_end:
                return (True, antecedent_idx)
        return (False, None)

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

    # =========================================================================
    # Resolución de sujeto gramatical
    # =========================================================================

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
        text, _ = self._find_subject_token(predicate_token)
        return text

    def _find_subject_token(self, predicate_token) -> tuple[Optional[str], Optional[object]]:
        """
        Igual que find_subject_for_predicate pero retorna también el token del sujeto.

        Útil para encadenar con búsqueda de identidad copulativa.

        Returns:
            Tupla (subject_text, subject_token) o (None, None)
        """
        # Caso 1: El predicado depende directamente de un verbo
        head = predicate_token.head
        if morpho_utils.is_verb(head):
            for child in head.children:
                if child.dep_ in ("nsubj", "nsubj:pass"):
                    return (self._expand_entity_span(child), child)

        # Caso 2: El predicado ES el head (aposición, atributo directo)
        for child in predicate_token.children:
            if child.dep_ in ("nsubj", "nsubj:pass"):
                return (self._expand_entity_span(child), child)

        # Caso 3: Buscar en ancestros (cadena de dependencias)
        current = predicate_token
        for _ in range(5):  # Máximo 5 niveles
            if current.head == current:
                break
            current = current.head
            if morpho_utils.is_verb(current):
                for child in current.children:
                    if child.dep_ in ("nsubj", "nsubj:pass"):
                        return (self._expand_entity_span(child), child)

        # Caso 4: ROOT nominal con estructura copulativa
        # "La mujer de ojos verdes era María" → mujer=ROOT, Maria=acl+cop
        # spaCy puede anidar la cópula profundamente en el subtree del acl:
        # mujer → conoció(acl) → María(obj) → era(cop)
        if current.head == current and current.pos_ == "NOUN":
            # Buscar cop en el subtree completo de cualquier hijo acl/relcl
            for child in current.children:
                if child.dep_ in ("acl", "relcl"):
                    for desc in child.subtree:
                        if desc.dep_ == "cop":
                            cop_lemma = (desc.lemma_ or "").lower()
                            if cop_lemma in _COPULAR_LEMMAS:
                                return (self._expand_entity_span(current), current)
            # También buscar cop directo (otra variante de parseo)
            for child in current.children:
                if child.dep_ == "cop":
                    return (self._expand_entity_span(current), current)

        return (None, None)

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

    # =========================================================================
    # Identidad copulativa: "X era Y"
    # =========================================================================

    def _find_copular_identity(self, subject_token) -> Optional[str]:
        """
        Busca identidad copulativa para un sujeto.

        En oraciones copulativas ("X era Y", "X es Y"), el sujeto y el predicado
        nominal son correferentes. Si el sujeto no está en entity_mentions pero
        el predicado nominal sí, se puede usar esta relación.

        Ejemplo: "La mujer de ojos verdes que Juan conoció era María."
        → subject_token = "mujer" → identidad copulativa = "María"

        Args:
            subject_token: Token del sujeto gramatical

        Returns:
            Texto de la identidad copulativa, o None
        """
        head = subject_token.head

        # Caso 0: subject es ROOT → buscar acl/relcl con estructura copulativa
        # "La mujer de ojos verdes era María" → mujer=ROOT, Maria=acl, era=cop
        # La cópula puede estar a cualquier profundidad en el subtree:
        # mujer → conoció(acl) → María(obj) → era(cop)
        if head is None or head == subject_token:
            for child in subject_token.children:
                if child.dep_ in ("acl", "relcl"):
                    for desc in child.subtree:
                        if desc.dep_ == "cop":
                            cop_lemma = (desc.lemma_ or "").lower()
                            if cop_lemma in _COPULAR_LEMMAS:
                                # desc.head es el nominal predicativo (la identidad)
                                return self._expand_entity_span(desc.head)
            return None

        # Caso 1: head es verbo copulativo → buscar attr/predicado nominal
        if morpho_utils.is_verb(head):
            lemma = (head.lemma_ or "").lower()
            if lemma in _COPULAR_LEMMAS:
                for child in head.children:
                    if child.dep_ in ("attr", "acomp", "oprd") and child.i != subject_token.i:
                        return self._expand_entity_span(child)

        # Caso 2: head es predicado nominal (estructura con cop)
        # spaCy puede parsear "X era Y" como: Y=ROOT, era=cop→Y, X=nsubj→Y
        if not morpho_utils.is_verb(head):
            for sibling in head.children:
                if sibling.dep_ == "cop":
                    cop_lemma = (sibling.lemma_ or "").lower()
                    if cop_lemma in _COPULAR_LEMMAS:
                        return self._expand_entity_span(head)

        return None

    # =========================================================================
    # Matching flexible de nombres (maneja artículos y acentos)
    # =========================================================================

    @staticmethod
    def _strip_articles(name: str) -> str:
        """Elimina artículos iniciales de un nombre para matching flexible."""
        words = name.strip().split()
        while words and words[0].lower() in _SPANISH_ARTICLES:
            words = words[1:]
        return " ".join(words)

    def _names_match_flexible(self, name1: str, name2: str) -> bool:
        """
        Compara nombres de forma flexible, manejando artículos y acentos.

        "hombre" ↔ "El hombre" → True
        "María" ↔ "Maria" → True
        "mujer" ↔ "La mujer de ojos verdes" → False (demasiado diferente)
        """
        n1 = morpho_utils.normalize_name(name1)
        n2 = morpho_utils.normalize_name(name2)
        if n1 == n2:
            return True

        n1_stripped = morpho_utils.normalize_name(self._strip_articles(name1))
        n2_stripped = morpho_utils.normalize_name(self._strip_articles(name2))

        # Requiere al menos 2 chars tras eliminar artículos para evitar falsos positivos
        if len(n1_stripped) < 2 or len(n2_stripped) < 2:
            return False

        if n1_stripped == n2_stripped:
            return True
        if n1_stripped == n2 or n1 == n2_stripped:
            return True

        return False

    # =========================================================================
    # Filtrado de entidades en cláusulas relativas
    # =========================================================================

    def _filter_rc_entities(
        self,
        attr_position: int,
        entity_mentions: list[tuple[str, int, int, str]],
    ) -> list[tuple[str, int, int, str]]:
        """
        Filtra entidades dentro de cláusulas relativas cuando el atributo está fuera.

        Previene asignar atributos a entidades que están dentro de una RC
        y no son el antecedente del atributo.

        Ejemplo: "El hombre que María había visto tenía ojos azules."
        → "ojos azules" está fuera de la RC
        → "María" está dentro de "que María había visto"
        → Se excluye "María" de los candidatos de proximidad

        Args:
            attr_position: Posición del atributo
            entity_mentions: Lista de entidades candidatas

        Returns:
            Lista filtrada (sin entidades en RC). Si el filtrado elimina
            todos los candidatos, retorna la lista original sin filtrar.
        """
        if not self._rc_spans:
            return entity_mentions

        attr_in_rc, _ = self.is_in_relative_clause(attr_position)
        if attr_in_rc:
            return entity_mentions  # Si el atributo está en RC, no filtrar

        filtered = []
        for mention in entity_mentions:
            name, start, end, etype = mention
            ent_in_rc, _ = self.is_in_relative_clause(start)
            if not ent_in_rc:
                filtered.append(mention)

        # Safety: nunca eliminar todos los candidatos
        return filtered if filtered else entity_mentions

    # =========================================================================
    # Resolución principal de entidad por scope
    # =========================================================================

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
           a. Matching flexible (maneja artículos: "hombre" ↔ "El hombre")
           b. Identidad copulativa ("La mujer era María" → "María")
        2. Filtrar entidades dentro de cláusulas relativas
        3. Buscar entidad más cercana en la misma oración
        4. Buscar en oraciones vecinas (scope de oración)
        5. Fallback: proximidad con límite de 1500 chars

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
                subject_text, subject_token = self._find_subject_token(token_at_pos)
                if subject_text:
                    # 1a: Matching flexible con entity_mentions
                    subject_match = None
                    for name, start, end, etype in entity_mentions:
                        if self._names_match_flexible(subject_text, name):
                            subject_match = name
                            break

                    # 1b: Identidad copulativa
                    # "La mujer ... era María" → subject="mujer" → identity="María"
                    identity_match = None
                    if subject_token is not None:
                        identity = self._find_copular_identity(subject_token)
                        if identity:
                            for name, start, end, etype in entity_mentions:
                                if self._names_match_flexible(identity, name):
                                    identity_match = name
                                    break

                    # Decisión: si el sujeto es un NOUN descriptivo ("mujer", "hombre")
                    # y la identidad copulativa resuelve a un nombre propio en las
                    # entidades, preferir el nombre propio.
                    if identity_match:
                        is_descriptive_noun = (
                            subject_token is not None
                            and subject_token.pos_ == "NOUN"
                        )
                        if is_descriptive_noun or not subject_match:
                            logger.debug(
                                f"Identidad copulativa: '{subject_text}' = '{identity}' "
                                f"→ entidad '{identity_match}'"
                            )
                            return (identity_match, 0.92)

                    if subject_match:
                        return (subject_match, 0.95)  # Alta confianza: sujeto gramatical

        # Paso 2: Filtrar entidades dentro de cláusulas relativas
        filtered_mentions = self._filter_rc_entities(position, entity_mentions)

        # Paso 3: Buscar en la misma oración
        sent_scope = self.sentence_scope(position, window=0)
        candidates_in_sentence = [
            (name, start, end, etype)
            for name, start, end, etype in filtered_mentions
            if sent_scope.contains(start)
        ]

        if candidates_in_sentence:
            # Tomar la más cercana por posición dentro de la oración
            best = min(
                candidates_in_sentence,
                key=lambda x: abs(x[1] - position),
            )
            return (best[0], 0.85)  # Buena confianza: misma oración

        # Paso 4: Buscar en scope de oraciones vecinas
        wider_scope = self.sentence_scope(position, window=SENTENCE_WINDOW)
        candidates_in_scope = [
            (name, start, end, etype)
            for name, start, end, etype in filtered_mentions
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

        # Paso 5: Respetar límite de párrafo
        para_scope = self.paragraph_scope(position)
        candidates_in_paragraph = [
            (name, start, end, etype)
            for name, start, end, etype in filtered_mentions
            if para_scope.contains(start)
        ]

        if candidates_in_paragraph:
            best = min(
                candidates_in_paragraph,
                key=lambda x: abs(x[1] - position),
            )
            return (best[0], 0.45)  # Baja confianza: mismo párrafo pero lejos

        # Paso 6: Fallback con límite de seguridad
        fallback_candidates = [
            (name, start, end, etype)
            for name, start, end, etype in filtered_mentions
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
