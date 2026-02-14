"""
Utilidades centralizadas de análisis morfológico basadas en spaCy.

Reemplaza listas hardcodeadas de verbos, sustantivos, etc. con consultas
al modelo lingüístico de spaCy, que cubre ~97% de formas en español.

Uso:
    from narrative_assistant.nlp.morpho_utils import (
        is_verb, is_proper_noun, get_gender, get_number,
        get_verb_mood, normalize_name, is_person_verb_context,
    )

    for token in doc:
        if is_verb(token):
            ...  # Es verbo, no debería ser entidad NER
"""

import logging
import re
import unicodedata

logger = logging.getLogger(__name__)

# Pequeño override set para errores conocidos de spaCy en español.
# spaCy clasifica incorrectamente algunas formas como NOUN o PROPN.
# Solo incluir casos comprobados donde spaCy falla consistentemente.
_SPACY_VERB_OVERRIDES = frozenset(
    {
        # Participios que spaCy a veces clasifica como ADJ/NOUN
        # pero que en contexto de inicio de oración son claramente verbos
        "sabiendo",
        "siendo",
        "teniendo",
        "habiendo",
        # Formas de voseo que spaCy no reconoce bien
        "hablás",
        "tenés",
        "podés",
        "querés",
        "sabés",
        "venís",
        "salís",
    }
)

# Formas que spaCy marca como VERB pero que en español son nombres propios
# o sustantivos comunes (falsos positivos de spaCy).
_SPACY_NOT_VERB_OVERRIDES = frozenset(
    {
        "mercedes",  # Nombre propio
        "dolores",  # Nombre propio
        "mar",  # Sustantivo/nombre propio
        "cruz",  # Sustantivo/nombre propio
        "rosa",  # Sustantivo/nombre propio
        "iris",  # Sustantivo/nombre propio
        "alba",  # Nombre propio
        "aurora",  # Nombre propio
        "esperanza",  # Nombre propio
        "pilar",  # Nombre propio
        "amparo",  # Nombre propio
        "consuelo",  # Nombre propio
        "sol",  # Nombre propio
    }
)


def is_verb(token) -> bool:
    """
    Determina si un token es forma verbal usando POS tags de spaCy.

    Cubre TODAS las conjugaciones: indicativo, subjuntivo, imperativo,
    gerundio, participio, condicional, infinitivo, formas compuestas.

    Args:
        token: Token de spaCy (con pos_, tag_, morph, text)

    Returns:
        True si es forma verbal
    """
    text_lower = token.text.lower()

    # Override: formas que spaCy no detecta bien
    if text_lower in _SPACY_VERB_OVERRIDES:
        return True

    # Override: formas que spaCy marca como verbo pero son nombres
    if text_lower in _SPACY_NOT_VERB_OVERRIDES:
        return False

    # Criterio principal: POS tag de spaCy
    if token.pos_ in ("VERB", "AUX"):
        return True

    # Criterio secundario: tag_ (más específico que pos_)
    return bool(hasattr(token, "tag_") and token.tag_ and token.tag_.startswith("V"))


def is_auxiliary(token) -> bool:
    """Determina si un token es verbo auxiliar (haber, ser, estar)."""
    return token.pos_ == "AUX"  # type: ignore[no-any-return]


def is_proper_noun(token) -> bool:
    """
    Determina si un token es nombre propio usando POS tags de spaCy.

    Args:
        token: Token de spaCy

    Returns:
        True si es nombre propio
    """
    return token.pos_ == "PROPN"  # type: ignore[no-any-return]


def is_noun(token) -> bool:
    """Determina si un token es sustantivo común."""
    return token.pos_ == "NOUN"  # type: ignore[no-any-return]


def is_adjective(token) -> bool:
    """Determina si un token es adjetivo."""
    return token.pos_ == "ADJ"  # type: ignore[no-any-return]


def is_pronoun(token) -> bool:
    """Determina si un token es pronombre."""
    return token.pos_ == "PRON"  # type: ignore[no-any-return]


def is_determiner(token) -> bool:
    """Determina si un token es determinante (artículo, demostrativo)."""
    return token.pos_ == "DET"  # type: ignore[no-any-return]


def get_gender(token) -> str | None:
    """
    Obtiene el género gramatical de un token.

    Returns:
        "Masc", "Fem", o None si no aplica
    """
    gender = token.morph.get("Gender")
    return gender[0] if gender else None


def get_number(token) -> str | None:
    """
    Obtiene el número gramatical de un token.

    Returns:
        "Sing", "Plur", o None si no aplica
    """
    number = token.morph.get("Number")
    return number[0] if number else None


def get_person(token) -> str | None:
    """
    Obtiene la persona gramatical de un verbo conjugado.

    Returns:
        "1", "2", "3", o None si no aplica
    """
    person = token.morph.get("Person")
    return person[0] if person else None


def get_verb_mood(token) -> str | None:
    """
    Obtiene el modo verbal de un token.

    Returns:
        "Ind" (indicativo), "Sub" (subjuntivo), "Imp" (imperativo),
        "Cnd" (condicional), o None si no es verbo conjugado
    """
    mood = token.morph.get("Mood")
    return mood[0] if mood else None


def get_verb_tense(token) -> str | None:
    """
    Obtiene el tiempo verbal de un token.

    Returns:
        "Pres", "Past", "Fut", "Imp", o None
    """
    tense = token.morph.get("Tense")
    return tense[0] if tense else None


def get_verb_form(token) -> str | None:
    """
    Obtiene la forma verbal: finito, infinitivo, gerundio, participio.

    Returns:
        "Fin", "Inf", "Ger", "Part", o None
    """
    vform = token.morph.get("VerbForm")
    return vform[0] if vform else None


def is_subjunctive(token) -> bool:
    """Determina si el verbo está en modo subjuntivo."""
    return get_verb_mood(token) == "Sub"


def is_conditional(token) -> bool:
    """Determina si el verbo está en modo condicional."""
    return get_verb_mood(token) == "Cnd"


def is_imperative(token) -> bool:
    """Determina si el verbo está en modo imperativo."""
    return get_verb_mood(token) == "Imp"


def is_gerund(token) -> bool:
    """Determina si el token es gerundio."""
    return get_verb_form(token) == "Ger"


def is_participle(token) -> bool:
    """Determina si el token es participio."""
    return get_verb_form(token) == "Part"


def is_infinitive(token) -> bool:
    """Determina si el token es infinitivo."""
    return get_verb_form(token) == "Inf"


# =========================================================================
# Normalización de nombres (acento-safe)
# =========================================================================

# Patrón para eliminar marcas combinantes (acentos) de Unicode
_COMBINING_MARK_RE = re.compile(r"[\u0300-\u036f]")


def normalize_name(text: str) -> str:
    """
    Normaliza un nombre eliminando acentos y convirtiendo a minúsculas.

    Esto permite que "María" y "Maria" se fusionen como la misma entidad.
    También "García" y "Garcia", "José" y "Jose", etc.

    Args:
        text: Nombre a normalizar

    Returns:
        Nombre normalizado sin acentos, en minúsculas
    """
    # NFKD descompone caracteres acentuados en base + combining mark
    normalized = unicodedata.normalize("NFKD", text)
    # Eliminar combining marks (acentos)
    stripped = _COMBINING_MARK_RE.sub("", normalized)
    return stripped.lower().strip()


def names_match(name1: str, name2: str) -> bool:
    """
    Compara dos nombres ignorando acentos y capitalización.

    "María García" == "Maria Garcia" → True
    "José" == "jose" → True
    """
    return normalize_name(name1) == normalize_name(name2)


# =========================================================================
# Análisis de contexto para reclasificación de entidades
# =========================================================================

# Tokens que preceden a un topónimo/local, NO a una persona
_LOCATION_CONTEXT_TOKENS = frozenset(
    {
        "calle",
        "avenida",
        "barrio",
        "zona",
        "plaza",
        "paseo",
        "carretera",
        "camino",
        "vía",
        "distrito",
        "pueblo",
        "bar",
        "restaurante",
        "tienda",
        "hotel",
        "taberna",
        "los",
        "las",  # "los García" (familia/lugar) — requiere contexto adicional
    }
)

# Preposiciones que indican ubicación (no persona)
_LOCATION_PREPOSITIONS = frozenset({"en", "desde", "hacia", "hasta", "por"})


def is_person_context(doc, entity_start: int, entity_end: int) -> bool:
    """
    Determina si el contexto alrededor de una entidad sugiere que es persona.

    Analiza tokens previos y relaciones de dependencia para distinguir:
    - "García" (persona) de "la García" (bar/taberna)
    - "Fernández" (persona) de "calle Fernández" (lugar)

    Args:
        doc: Documento spaCy procesado
        entity_start: Carácter de inicio de la entidad
        entity_end: Carácter de fin de la entidad

    Returns:
        True si el contexto sugiere persona, False si sugiere lugar/cosa
    """
    # Encontrar tokens de la entidad
    entity_tokens = [t for t in doc if t.idx >= entity_start and t.idx < entity_end]
    if not entity_tokens:
        return True  # Sin contexto, asumir persona (default conservador)

    first_token = entity_tokens[0]

    # Verificar tokens previos
    if first_token.i > 0:
        prev_token = doc[first_token.i - 1]
        prev_lower = prev_token.text.lower()

        # Si el token previo es indicador de lugar → NO es persona
        if prev_lower in _LOCATION_CONTEXT_TOKENS:
            return False

        # Si hay preposición de lugar antes → NO es persona
        if prev_lower in _LOCATION_PREPOSITIONS:
            return False

        # Verificar 2 tokens atrás: "en la García" → lugar
        if first_token.i > 1:
            prev2 = doc[first_token.i - 2]
            if prev2.text.lower() in _LOCATION_PREPOSITIONS and is_determiner(prev_token):
                return False

    # Verificar si la entidad es sujeto de verbo "de persona"
    for token in entity_tokens:
        if token.dep_ in ("nsubj", "nsubj:pass"):
            head = token.head
            if is_verb(head):
                return True  # Sujeto de verbo → probablemente persona

    # Verificar si hay verbo de acción humana (hablar, caminar, sentir, pensar)
    for token in entity_tokens:
        for child in token.children:
            if child.dep_ in ("acl", "relcl", "appos"):
                return True  # Tiene cláusula relativa → probablemente persona

    return True  # Default: asumir persona


def has_explicit_subject(verb_token) -> bool:
    """
    Verifica si un verbo conjugado tiene sujeto explícito en el parse.

    Útil para detectar pro-drop: verbos sin sujeto explícito en español
    implican un pronombre omitido.

    Args:
        verb_token: Token de verbo en spaCy

    Returns:
        True si tiene nsubj explícito, False si es candidato a pro-drop
    """
    return any(child.dep_ in ("nsubj", "nsubj:pass") for child in verb_token.children)


def detect_pro_drop_person(verb_token) -> tuple[str, str] | None:
    """
    Detecta la persona/número de un verbo conjugado sin sujeto explícito (pro-drop).

    En español: "Entré en la habitación" → sujeto omitido = 1a persona singular.

    Args:
        verb_token: Token de verbo conjugado en spaCy

    Returns:
        Tupla (person, number) como ("1", "Sing"), o None si no aplica
    """
    if not is_verb(verb_token):
        return None

    if has_explicit_subject(verb_token):
        return None

    person = get_person(verb_token)
    number = get_number(verb_token)

    if person and number:
        return (person, number)

    return None


# =========================================================================
# Desambiguación de "como" y marcadores de metáfora
# =========================================================================


def is_comparison_como(token) -> bool:
    """
    Determina si un token "como" es comparación/metáfora vs otros usos.

    Usos de "como" en español:
    1. Comparación: "Sus ojos eran como diamantes" → True
    2. Manera: "Como lo hizo" → False
    3. Temporal: "Como llegó, vimos..." → False
    4. Condicional: "Como no vuelvas..." → False
    5. Aproximación: "Tenía como veinte años" → False
    6. Causal: "Como estaba cansado..." → False

    Usa relaciones de dependencia de spaCy para desambiguar.

    Args:
        token: Token de spaCy para "como"

    Returns:
        True si es comparación/metáfora
    """
    if token.text.lower() != "como":
        return False

    # dep_ == "mark" → conjunción subordinante (temporal, condicional, causal)
    if token.dep_ == "mark":
        return False

    # dep_ == "advmod" → adverbio de manera ("como lo hizo")
    if token.dep_ == "advmod":
        # Verificar si modifica un verbo (manera) o un adjetivo (comparación)
        return token.head.pos_ != "VERB"  # type: ignore[no-any-return]

    # dep_ == "case" → preposición/marcador de caso
    if token.dep_ == "case":
        return False

    # dep_ == "cc" o "conj" → coordinante
    if token.dep_ in ("cc", "conj"):
        return False

    # Si depende de un adjetivo o sustantivo → probablemente comparación
    if token.head.pos_ in ("ADJ", "NOUN"):
        return True

    # Si va seguido de "si" → "como si" = comparación hipotética
    if token.i + 1 < len(token.doc) and token.doc[token.i + 1].text.lower() == "si":
        return True

    # Default: si no encaja en patrones claros, asumir que podría ser comparación
    # pero con baja confianza (el caller debería reducir confianza, no filtrar)
    return True


def is_hypothetical_context(token) -> bool:
    """
    Determina si un token está en contexto hipotético (subjuntivo, condicional).

    Útil para clasificar atributos: "si fuera alto" → atributo hipotético,
    no real.

    Args:
        token: Token de spaCy

    Returns:
        True si el contexto es hipotético
    """
    # El propio token es subjuntivo/condicional
    if is_verb(token) and (is_subjunctive(token) or is_conditional(token)):
        return True

    # El head (verbo que gobierna) es subjuntivo/condicional
    head = token.head
    if is_verb(head) and (is_subjunctive(head) or is_conditional(head)):
        return True

    # Buscar "si" condicional en la oración
    sent = token.sent if hasattr(token, "sent") else None
    if sent:
        for t in sent:
            if t.text.lower() == "si" and t.dep_ == "mark":
                # Verificar que el "si" gobierna un verbo en subjuntivo
                if is_verb(t.head) and is_subjunctive(t.head):
                    return True

    return False
