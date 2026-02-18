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

# Pronombres preposicionales que indican género (para desambiguación)
_MASC_PRONOUNS = frozenset({"él", "el"})  # "en él" (preposicional)
_FEM_PRONOUNS = frozenset({"ella"})

# Verbos de percepción/dirección que combinan con "en él/ella" para indicar
# que el sujeto de "sus" es la OTRA persona (no el pronombre)
_GAZE_VERBS = frozenset({
    "clavar", "posar", "fijar", "dirigir", "volver", "posarse",
    "clavarse", "fijarse", "dirigirse",
})


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

    def is_in_relative_clause(self, char_position: int) -> tuple[bool, int | None]:
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

    def sentence_scope(self, position: int, window: int = SENTENCE_WINDOW) -> ScopeSpan:
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
        return ScopeSpan(start=0, end=len(self.text), scope_type="paragraph")

    # =========================================================================
    # Resolución de sujeto gramatical
    # =========================================================================

    def find_subject_for_predicate(self, predicate_token) -> str | None:
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

    def _find_subject_token(self, predicate_token) -> tuple[str | None, object | None]:
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
                    # Si el sujeto es un NOUN con nmod PROPN, devolver el PROPN
                    propn = self._follow_genitive_to_propn(child)
                    if propn is not None:
                        return (self._expand_entity_span(propn), propn)
                    return (self._expand_entity_span(child), child)

        # Caso 2: El predicado ES el head (aposición, atributo directo)
        for child in predicate_token.children:
            if child.dep_ in ("nsubj", "nsubj:pass"):
                propn = self._follow_genitive_to_propn(child)
                if propn is not None:
                    return (self._expand_entity_span(propn), propn)
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
                        propn = self._follow_genitive_to_propn(child)
                        if propn is not None:
                            return (self._expand_entity_span(propn), propn)
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

    def _follow_genitive_to_propn(self, subject_token) -> object | None:
        """
        Si el sujeto es un NOUN con un hijo nmod que es PROPN con case 'de',
        devuelve ese PROPN. Permite resolver "La mirada de Juan" → Juan.

        Solo sigue la cadena si el sujeto no es un nombre propio (PROPN)
        ya que en ese caso el sujeto ya es la entidad directa.

        Args:
            subject_token: Token del sujeto gramatical

        Returns:
            Token PROPN si se encuentra, None si no aplica
        """
        if subject_token.pos_ != "NOUN":
            return None

        for child in subject_token.children:
            if child.dep_ == "nmod" and child.pos_ == "PROPN":
                # Verificar que tiene preposición "de"
                has_de = any(
                    c.dep_ == "case" and c.text.lower() == "de"
                    for c in child.children
                )
                if has_de:
                    return child
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
                    return ent.text  # type: ignore[no-any-return]

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

    def _find_copular_identity(self, subject_token) -> str | None:
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
        return bool(n1_stripped == n2 or n1 == n2_stripped)

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

        # No restaurar entidades que están en una RC cuando el atributo
        # está fuera de ella. Es preferible no resolver (None) a resolver
        # incorrectamente a una entidad dentro de la cláusula relativa.
        return filtered

    # =========================================================================
    # Detección de ambigüedad
    # =========================================================================

    def _is_ambiguous_context(
        self,
        position: int,
        entity_mentions: list[tuple[str, int, int, str]],
    ) -> bool:
        """
        Detecta si el contexto de atribución es genuinamente ambiguo.

        Cuando ni un lector humano puede determinar con certeza a quién
        pertenece el atributo, el resolver debe retornar None para que
        el sistema genere una alerta de revisión manual.

        Patrones ambiguos en español:
        1. "Cuando X verbo a Y, tenía atributo" — la subordinada introduce
           dos candidatos igualmente válidos.
        2. "X verbo a Y. Sus atributo le + verbo" — 'le' no desambigua género.
        3. "X le dijo a Y que tenía atributo" — subordinada completiva con
           dos candidatos posibles.

        Args:
            position: Posición del atributo en el texto
            entity_mentions: Lista de entidades candidatas

        Returns:
            True si el contexto es genuinamente ambiguo
        """
        # Solo es ambiguo si hay >= 2 entidades PERSONA distintas en scope
        unique_per_names = set()
        for name, start, end, etype in entity_mentions:
            if etype == "PER":
                unique_per_names.add(name)
        if len(unique_per_names) < 2:
            return False

        # Encontrar la oración que contiene el atributo
        attr_sent_idx = None
        for i, (s_start, s_end) in enumerate(self._sentence_spans):
            if s_start <= position < s_end:
                attr_sent_idx = i
                break
        if attr_sent_idx is None:
            return False

        attr_sent_start, attr_sent_end = self._sentence_spans[attr_sent_idx]
        attr_sent_text = self.text[attr_sent_start:attr_sent_end]

        # Patrón 1: "Cuando X verbo a Y, tenía..." (subordinada temporal)
        # La clave es que hay una subordinada con "cuando" que introduce
        # dos entidades antes del verbo principal con el atributo.
        if self._is_cuando_subordinate_ambiguity(
            position, attr_sent_idx, entity_mentions
        ):
            return True

        # Patrón 2: "X verbo a Y. Sus <atributo> le/se <verbo>"
        # Donde la oración previa tiene sujeto y objeto, y la oración
        # del atributo usa "sus" + "le" (que no indica género).
        if self._is_sus_le_ambiguity(position, attr_sent_idx, entity_mentions):
            return True

        # Patrón 3: "X le dijo a Y que tenía <atributo>"
        # Subordinada completiva con "que tenía/que era" donde ambos
        # X (sujeto) e Y (objeto indirecto) son candidatos.
        if self._is_decir_que_ambiguity(position, attr_sent_idx, entity_mentions):
            return True

        return False

    def _is_cuando_subordinate_ambiguity(
        self,
        position: int,
        attr_sent_idx: int,
        entity_mentions: list[tuple[str, int, int, str]],
    ) -> bool:
        """
        Detecta el patrón "Cuando X verbo a Y, tenía <atributo>".

        Este patrón es sistemáticamente ambiguo porque la subordinada
        temporal introduce dos candidatos igualmente válidos para el
        verbo principal.

        Returns:
            True si se detecta el patrón ambiguo
        """
        attr_sent_start, attr_sent_end = self._sentence_spans[attr_sent_idx]

        # Buscar "cuando" al inicio de la oración o en una oración previa
        # que forme parte de la misma unidad sintáctica
        sent_text = self.text[attr_sent_start:attr_sent_end].strip()

        # Check if "cuando" appears at the beginning of the sentence
        # (possibly as part of the same sentence that contains the attribute)
        has_cuando = False
        cuando_search_start = attr_sent_start

        # Also check the previous sentence (the subordinate might be parsed
        # as a separate sentence by spaCy)
        if attr_sent_idx > 0:
            prev_start, prev_end = self._sentence_spans[attr_sent_idx - 1]
            prev_text = self.text[prev_start:prev_end].strip()
            if re.match(r"(?i)cuando\s", prev_text):
                has_cuando = True
                cuando_search_start = prev_start

        if re.match(r"(?i)cuando\s", sent_text):
            has_cuando = True

        if not has_cuando:
            return False

        # Verify there are >= 2 different PERSON entities in the cuando clause
        # region (from cuando to the attribute position)
        entities_in_cuando_region = set()
        for name, start, end, etype in entity_mentions:
            if etype == "PER" and cuando_search_start <= start < position:
                entities_in_cuando_region.add(name)

        if len(entities_in_cuando_region) < 2:
            return False

        # Verify the verb at the attribute position has no explicit subject
        # (i.e., it's a pro-drop that inherits ambiguously)
        attr_token = self._token_at_position(position)
        if attr_token is not None:
            # Walk up to find the governing verb
            verb = self._find_governing_verb(attr_token)
            if verb is not None and not morpho_utils.has_explicit_subject(verb):
                logger.debug(
                    f"Ambiguity detected: 'cuando' subordinate with "
                    f"{entities_in_cuando_region} and pro-drop verb"
                )
                return True

        return False

    def _is_sus_le_ambiguity(
        self,
        position: int,
        attr_sent_idx: int,
        entity_mentions: list[tuple[str, int, int, str]],
    ) -> bool:
        """
        Detecta "X verbo a Y. Sus <atributo> le <verbo>" — ambiguo porque
        'le' no indica género en español.

        Returns:
            True si se detecta el patrón ambiguo
        """
        attr_sent_start, attr_sent_end = self._sentence_spans[attr_sent_idx]
        sent_text = self.text[attr_sent_start:attr_sent_end]

        # Check if the sentence contains "sus" before the attribute
        # and "le" or "se" after, but NOT "en él/ella" (which disambiguates)
        text_before_attr = self.text[attr_sent_start:position].lower()
        text_after_attr = self.text[position:attr_sent_end].lower()

        has_possessive_sus = bool(re.search(r"\bsus\b", text_before_attr))
        if not has_possessive_sus:
            return False

        # Check for "le llamaron" / "le resultaban" pattern (no gender info)
        has_le_verb = bool(re.search(r"\ble\s+\w+", text_after_attr))
        if not has_le_verb:
            return False

        # Check that there's NO gendered pronoun that could disambiguate
        has_gendered_pronoun = bool(
            re.search(r"\ben\s+(?:él|ella)\b", sent_text.lower())
        )
        if has_gendered_pronoun:
            return False

        # Check that the previous sentence has both a subject and object
        # (i.e., two candidate entities)
        if attr_sent_idx > 0:
            prev_start, prev_end = self._sentence_spans[attr_sent_idx - 1]
            prev_entities = set()
            for name, start, end, etype in entity_mentions:
                if etype == "PER" and prev_start <= start < prev_end:
                    prev_entities.add(name)
            if len(prev_entities) >= 2:
                logger.debug(
                    f"Ambiguity detected: 'Sus + le' pattern with "
                    f"{prev_entities} in previous sentence"
                )
                return True

        return False

    def _is_decir_que_ambiguity(
        self,
        position: int,
        attr_sent_idx: int,
        entity_mentions: list[tuple[str, int, int, str]],
    ) -> bool:
        """
        Detecta "X le dijo a Y que tenía <atributo>" — ambiguo porque
        'que tenía' puede referirse al sujeto (X) o al objeto indirecto (Y).

        Returns:
            True si se detecta el patrón ambiguo
        """
        attr_sent_start, attr_sent_end = self._sentence_spans[attr_sent_idx]
        sent_text = self.text[attr_sent_start:attr_sent_end]
        sent_lower = sent_text.lower()

        # Check for "le dijo/contó/explicó a ENTITY que tenía/era/llevaba"
        speech_verbs = r"(?:dijo|contó|explicó|comentó|confesó|indicó|señaló|mencionó|advirtió)"
        que_verbs = r"(?:tenía|era|llevaba|mostraba|lucía)"
        pattern = rf"\ble\s+{speech_verbs}\s+a\s+\w+.*?\bque\s+{que_verbs}\b"

        if not re.search(pattern, sent_lower):
            return False

        # Verify there are >= 2 different entities in this sentence
        entities_in_sent = set()
        for name, start, end, etype in entity_mentions:
            if etype == "PER" and attr_sent_start <= start < attr_sent_end:
                entities_in_sent.add(name)

        if len(entities_in_sent) >= 2:
            logger.debug(
                f"Ambiguity detected: 'le dijo a X que tenía' pattern "
                f"with {entities_in_sent}"
            )
            return True

        return False

    def _find_governing_verb(self, token):
        """
        Encuentra el verbo que gobierna un token, subiendo por el árbol
        de dependencias.

        Returns:
            Token del verbo gobernante, o None
        """
        current = token
        for _ in range(7):
            if morpho_utils.is_verb(current):
                return current
            if current.head == current:
                break
            current = current.head
        return None

    # =========================================================================
    # Desambiguación por pronombres (él/ella)
    # =========================================================================

    def _disambiguate_by_pronoun(
        self,
        position: int,
        entity_mentions: list[tuple[str, int, int, str]],
    ) -> tuple[str, float] | None:
        """
        Desambigua atribución usando pronombres preposicionales (él/ella).

        Patrón: "Sus <atributo> se clavaron en él/ella"
        - "en él" → el referente de "sus" es la OTRA persona (no él)
        - "en ella" → el referente de "sus" es la OTRA persona (no ella)

        La lógica es: si los ojos "se clavaron en X", entonces X es el
        TARGET de la mirada, y "sus" pertenece a quien mira (la otra persona).

        Args:
            position: Posición del atributo en el texto
            entity_mentions: Lista de entidades candidatas

        Returns:
            (entity_name, confidence) si se puede desambiguar, None si no
        """
        # Encontrar la oración del atributo
        attr_sent_start = None
        attr_sent_end = None
        for s_start, s_end in self._sentence_spans:
            if s_start <= position < s_end:
                attr_sent_start = s_start
                attr_sent_end = s_end
                break
        if attr_sent_start is None:
            return None

        sent_text = self.text[attr_sent_start:attr_sent_end]
        sent_lower = sent_text.lower()

        # Check for "en él" / "en ella" in the sentence
        # También detectar "en el" sin tilde cuando funciona como pronombre (dep=obl)
        pronoun_gender = None  # The gender of the person being looked AT
        pron_match = re.search(r"\ben\s+(él|ella|el)\b", sent_lower)
        if pron_match:
            pronoun_text = pron_match.group(1)
            if pronoun_text in ("él",):
                pronoun_gender = "Masc"
            elif pronoun_text == "ella":
                pronoun_gender = "Fem"
            elif pronoun_text == "el":
                # "el" sin tilde: solo tratar como pronombre si es obl en dep parsing
                match_start_in_doc = attr_sent_start + pron_match.start(1)
                token = self._token_at_position(match_start_in_doc)
                if token is not None and token.dep_ in ("obl", "obl:arg"):
                    pronoun_gender = "Masc"

        if pronoun_gender is None:
            return None

        # The pronoun tells us who is being looked AT (the target).
        # "Sus ojos" belong to the OTHER person.
        # We need to identify which entity the pronoun refers to and return
        # the OTHER entity.

        # Collect entities from the previous sentence + current sentence
        attr_sent_idx = None
        for i, (s_start, s_end) in enumerate(self._sentence_spans):
            if s_start <= position < s_end:
                attr_sent_idx = i
                break
        if attr_sent_idx is None:
            return None

        # Gather candidate entities from nearby sentences
        search_start = self._sentence_spans[max(0, attr_sent_idx - 2)][0]
        search_end = attr_sent_end

        candidates = []
        seen_names = set()
        for name, start, end, etype in entity_mentions:
            if etype == "PER" and search_start <= start < search_end and name not in seen_names:
                candidates.append((name, start, end, etype))
                seen_names.add(name)

        if len(candidates) < 2:
            return None

        # Try to determine gender of each entity using spaCy morphology
        # Match the pronoun gender to find the TARGET entity
        target_entity = None
        other_entities = []

        for name, start, end, etype in candidates:
            token = self._token_at_position(start)
            if token is not None:
                gender = morpho_utils.get_gender(token)
                if gender == pronoun_gender:
                    target_entity = name
                else:
                    other_entities.append(name)
            else:
                other_entities.append(name)

        # If we couldn't match by morphology, try name heuristics
        if target_entity is None:
            for name, start, end, etype in candidates:
                # Common Spanish feminine name endings
                name_lower = name.lower().rstrip("s")
                if pronoun_gender == "Fem" and name_lower.endswith("a"):
                    target_entity = name
                elif pronoun_gender == "Masc" and not name_lower.endswith("a"):
                    target_entity = name

                if target_entity:
                    other_entities = [
                        n for n, _, _, _ in candidates if n != target_entity
                    ]
                    break

        if target_entity and other_entities:
            # "Sus ojos" belong to the first of the OTHER entities
            # (the one who is doing the looking, not the target)
            owner = other_entities[0]
            logger.debug(
                f"Pronoun disambiguation: 'en {pronoun_text}' → target={target_entity}, "
                f"owner of 'sus'={owner}"
            )
            return (owner, 0.88)

        return None

    # =========================================================================
    # Resolución principal de entidad por scope
    # =========================================================================

    def find_nearest_entity_by_scope(
        self,
        position: int,
        entity_mentions: list[tuple[str, int, int, str]],
        prefer_subject: bool = True,
    ) -> tuple[str, float] | None:
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

        # Paso 0: Buscar genitivo "de X" (máxima prioridad)
        # "Los ojos de Juan brillaban" → Juan (nmod de "ojos")
        genitive_result = self._find_genitive_owner(position, entity_mentions)
        if genitive_result:
            return genitive_result

        # Paso 0.5: Desambiguación por pronombres (él/ella)
        # "Sus ojos se clavaron en él" → sus = la OTRA persona (no él)
        pronoun_result = self._disambiguate_by_pronoun(position, entity_mentions)
        if pronoun_result:
            return pronoun_result

        # Paso 0.7: Detección de ambigüedad genuina
        # Si el contexto es genuinamente ambiguo, retornar None para que
        # el sistema genere una alerta de revisión manual.
        if self._is_ambiguous_context(position, entity_mentions):
            logger.debug(
                f"Ambiguous context detected at position {position}, "
                f"returning None"
            )
            return None

        # Paso 1: Intentar sujeto gramatical
        if prefer_subject:
            token_at_pos = self._token_at_position(position)
            if token_at_pos:
                subject_text, subject_token = self._find_subject_token(token_at_pos)
                if subject_text:
                    # 1a: Matching flexible con entity_mentions
                    subject_match = None
                    for name, _start, _end, _etype in entity_mentions:
                        if self._names_match_flexible(subject_text, name):
                            subject_match = name
                            break

                    # 1b: Identidad copulativa
                    # "La mujer ... era María" → subject="mujer" → identity="María"
                    identity_match = None
                    if subject_token is not None:
                        identity = self._find_copular_identity(subject_token)
                        if identity:
                            for name, _start, _end, _etype in entity_mentions:
                                if self._names_match_flexible(identity, name):
                                    identity_match = name
                                    break

                    # Decisión: si el sujeto es un NOUN descriptivo ("mujer", "hombre")
                    # y la identidad copulativa resuelve a un nombre propio en las
                    # entidades, preferir el nombre propio.
                    if identity_match:
                        is_descriptive_noun = (
                            subject_token is not None and subject_token.pos_ == "NOUN"  # type: ignore[attr-defined]
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
            # Separar candidatos antes y después de la posición
            before_pos = [c for c in candidates_in_sentence if c[1] < position]
            after_pos = [c for c in candidates_in_sentence if c[1] >= position]

            # Preferir entidades ANTES de la posición del atributo
            if before_pos:
                best = min(before_pos, key=lambda x: abs(x[1] - position))
                return (best[0], 0.85)

            # Si solo hay entidades DESPUÉS, verificar que no son complementos objeto
            # "Sus ojos azules miraban con curiosidad a María"
            #   → "a María" = objeto, NO poseedora de "Sus ojos"
            if after_pos:
                non_object_candidates = []
                for name, start, end, etype in after_pos:
                    if self._is_object_complement(start):
                        continue  # Es complemento, no poseedora
                    non_object_candidates.append((name, start, end, etype))

                if non_object_candidates:
                    best = min(non_object_candidates, key=lambda x: abs(x[1] - position))
                    return (best[0], 0.75)
            # Si todas las entidades en la oración son objetos, continuar a Step 4

        # Paso 3.5: Buscar sujeto de la oración anterior (pro-drop)
        # En español, el sujeto tácito hereda del sujeto de la oración anterior.
        # Esto tiene prioridad sobre la búsqueda por proximidad en wider scope.
        if prefer_subject:
            prev_subject = self._find_previous_sentence_subject(
                position, filtered_mentions
            )
            if prev_subject:
                return prev_subject

        # Paso 4: Buscar en scope de oraciones vecinas
        wider_scope = self.sentence_scope(position, window=SENTENCE_WINDOW)
        candidates_in_scope = []
        for name, start, end, etype in filtered_mentions:
            if not wider_scope.contains(start):
                continue
            # Filtrar complementos objeto DESPUÉS de la posición del atributo
            if start > position and self._is_object_complement(start):
                continue
            # Filtrar entidades con rol de objeto ANTES de la posición
            # "María saludó a Juan. Sus ojos brillaban." → Juan es objeto, no sujeto
            if start < position and self._mention_syntactic_role(start) == "object":
                continue
            candidates_in_scope.append((name, start, end, etype))

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
            and not (start > position and self._is_object_complement(start))
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
            and not (start > position and self._is_object_complement(start))
        ]

        if fallback_candidates:
            best = min(
                fallback_candidates,
                key=lambda x: abs(x[1] - position),
            )
            return (best[0], 0.3)  # Muy baja confianza

        return None

    def _find_genitive_owner(
        self,
        position: int,
        entity_mentions: list[tuple[str, int, int, str]],
    ) -> tuple[str, float] | None:
        """
        Busca un propietario genitivo ("de X") para la posición del atributo.

        Detecta patrones como:
        - "Los ojos de Juan" → Juan (nmod de "ojos")
        - "Los ojos verdes de María" → María (nmod de "ojos" con adj intercalado)
        - "Brillaban los ojos azules de Pedro" → Pedro

        Busca en el token del atributo y sus descendientes/ancestros
        un nmod con case "de" que sea PROPN y coincida con una entidad.

        Args:
            position: Posición del atributo en el texto
            entity_mentions: Lista de entidades candidatas

        Returns:
            (entity_name, confidence) si se encuentra genitivo, None si no
        """
        token = self._token_at_position(position)
        if token is None:
            return None

        # El token en la posición es el body-part ("ojos").
        # Buscar hijos nmod con case "de" que sean entidades
        genitive_entity = self._check_nmod_children(token, entity_mentions)
        if genitive_entity:
            return genitive_entity

        # También revisar el head del token si es un body-part token
        # modificado por un adjetivo (p.ej. "ojos" es head de "azules")
        if token.head != token and token.head.pos_ == "NOUN":
            genitive_entity = self._check_nmod_children(token.head, entity_mentions)
            if genitive_entity:
                return genitive_entity

        return None

    def _check_nmod_children(
        self,
        token,
        entity_mentions: list[tuple[str, int, int, str]],
    ) -> tuple[str, float] | None:
        """
        Busca hijos nmod+case('de') que coincidan con una entidad.

        Args:
            token: Token del que buscar hijos nmod
            entity_mentions: Lista de entidades candidatas

        Returns:
            (entity_name, confidence) si se encuentra, None si no
        """
        for child in token.children:
            if child.dep_ == "nmod":
                # Verificar que tiene preposición "de"
                has_de = any(
                    c.dep_ == "case" and c.text.lower() == "de"
                    for c in child.children
                )
                if has_de:
                    child_text = self._expand_entity_span(child)
                    for name, _start, _end, _etype in entity_mentions:
                        if self._names_match_flexible(child_text, name):
                            return (name, 0.93)
        return None

    def _mention_syntactic_role(self, mention_start: int) -> str:
        """
        Determina el rol sintáctico de la entidad en mention_start.

        Returns:
            'subject', 'object', 'genitive' o 'other'
        """
        token = self._token_at_position(mention_start)
        if token is None:
            return "other"
        if token.dep_ in {"nsubj", "nsubj:pass"}:
            return "subject"
        if token.dep_ in {"obj", "obl", "iobj", "dobj", "obl:arg"}:
            return "object"
        if token.dep_ == "nmod" and any(
            c.text.lower() == "de" for c in token.children if c.dep_ == "case"
        ):
            return "genitive"
        return "other"

    def _find_previous_sentence_subject(
        self,
        position: int,
        entity_mentions: list[tuple[str, int, int, str]],
    ) -> tuple[str, float] | None:
        """
        Busca el sujeto de la oración inmediatamente anterior.

        En español, el sujeto tácito de una oración hereda del sujeto
        de la oración anterior (pro-drop). Esta función busca en la
        oración previa una entidad con rol de sujeto (nsubj).

        Args:
            position: Posición del atributo actual
            entity_mentions: Lista de entidades candidatas

        Returns:
            (entity_name, confidence) si se encuentra un sujeto previo, None si no
        """
        # Encontrar la oración actual
        current_sent_idx = None
        for i, (start, end) in enumerate(self._sentence_spans):
            if start <= position < end:
                current_sent_idx = i
                break

        if current_sent_idx is None or current_sent_idx == 0:
            return None

        # Buscar en las oraciones previas (más cercana primero)
        for sent_idx in range(current_sent_idx - 1, max(-1, current_sent_idx - 3), -1):
            sent_start, sent_end = self._sentence_spans[sent_idx]

            # Buscar entidades con rol de sujeto en esa oración
            subject_candidates = []
            object_candidates = []
            for name, start, end, etype in entity_mentions:
                if sent_start <= start < sent_end:
                    role = self._mention_syntactic_role(start)
                    if role == "subject":
                        subject_candidates.append((name, start, end, etype))
                    elif role == "object":
                        object_candidates.append((name, start, end, etype))

            if subject_candidates:
                # Devolver el primer sujeto (el más cercano al inicio de la oración)
                best = min(subject_candidates, key=lambda x: x[1])
                distance = current_sent_idx - sent_idx
                confidence = max(0.6, 0.8 - (distance * 0.05))
                return (best[0], confidence)

        return None

    def _is_object_complement(self, mention_start: int) -> bool:
        """
        Detecta si una mención de entidad funciona como complemento objeto.

        Usa dos estrategias combinadas:
        1. **Dep parsing (spaCy)**: si el token en mention_start tiene dep_
           en {obj, obl, iobj, dobj, nmod} → es complemento.
        2. **Heurística de "a personal"**: en español, "a + ENTIDAD" marca
           objeto directo/indirecto de persona. Detecta "a", "al" y
           preposiciones que introducen complementos: "contra", "hacia",
           "sobre", "para", "por", "ante", "tras".

        Args:
            mention_start: Posición de inicio de la mención en el texto

        Returns:
            True si la mención es complemento (no debe recibir atributos)
        """
        # Extraer la palabra justo antes de la mención (para ambas estrategias)
        prefix_start = max(0, mention_start - 10)
        prefix = self.doc.text[prefix_start:mention_start].strip()
        last_word = prefix.split()[-1].lower() if prefix else ""

        # Excepción: "de X" indica genitivo/posesivo, no complemento objeto.
        # "con los de María" → "de María" es posesivo, no objeto.
        # No marcar como objeto si la preposición inmediata es "de"/"del".
        if last_word in {"de", "del"}:
            return False

        # Estrategia 1: dep parsing
        token = self._token_at_position(mention_start)
        if token is not None and token.dep_ in {
            "obj", "obl", "iobj", "dobj", "nmod", "obl:arg",
        }:
            return True

        # Estrategia 2: "a personal" y preposiciones de complemento
        if last_word in {"a", "al", "contra", "hacia", "sobre", "para", "ante", "tras"}:
            return True

        return False

    def _token_at_position(self, char_position: int):
        """Encuentra el token de spaCy en una posición de caracteres."""
        for token in self.doc:
            if token.idx <= char_position < token.idx + len(token.text):
                return token
        return None


def find_subject_in_scope(doc, token) -> str | None:
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
