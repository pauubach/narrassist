"""
Utilidades compartidas de análisis a nivel de oración.

Funciones extraídas para DRY: usadas por attr_entity_resolution,
pro_drop_scorer, y potencialmente otros módulos de la pipeline NLP.

T1: Normalización de sentence breaks falsos
T2: Detección de señales lingüísticas de continuidad cross-sentence
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sentence Splitting — Canonical Implementation
# ---------------------------------------------------------------------------
# Pattern consolidado de clarity.py / anacoluto.py (más robusto)
_SENTENCE_END_RE = re.compile(r'[.!?]+(?:\s|$|"|\)|»|\')')


def split_sentences(
    text: str,
    min_length: int = 10,
) -> list[tuple[str, int, int]]:
    """
    Divide texto en oraciones con posiciones de inicio/fin.

    Esta es la implementación canónica consolidada de:
    - clarity.py, anacoluto.py, sticky_sentences.py, sentence_energy.py,
      readability.py, grammar_checker.py, repetition.py

    Args:
        text: Texto a dividir en oraciones
        min_length: Longitud mínima de fragmento final sin puntuación

    Returns:
        Lista de tuplas (texto_oración, start_char, end_char)

    Examples:
        >>> split_sentences("Juan corrió. María saltó.")
        [('Juan corrió.', 0, 13), ('María saltó.', 14, 27)]
    """
    sentences = []
    current_start = 0

    for match in _SENTENCE_END_RE.finditer(text):
        end = match.end()
        sentence_text = text[current_start:end].strip()

        if sentence_text:
            sentences.append((sentence_text, current_start, end))

        current_start = end

    # Última oración si no termina en puntuación
    if current_start < len(text):
        remaining = text[current_start:].strip()
        if remaining and len(remaining) >= min_length:
            sentences.append((remaining, current_start, len(text)))

    return sentences


# ---------------------------------------------------------------------------
# T1: Normalización de sentence breaks falsos
# ---------------------------------------------------------------------------
# Puntos suspensivos → 1 solo break, no 3
_ELLIPSIS_RE = re.compile(r"\.{2,}")
# Abreviaturas españolas comunes seguidas de punto
_ABBREVIATION_RE = re.compile(
    r"\b(Dr|Dra|Sr|Sra|Srta|Prof|Ing|Lic|Gral|Col|Cmdt|Av|Jr|"
    r"St|Sto|Sta|etc|approx|aprox|pág|págs|vol|núm|ed|ej|"
    r"p|pp|fig|cap|art|sec|tel|dept|adm|Excmo|Ilmo)\.",
    re.IGNORECASE,
)
# Números decimales: 1.85, 3.14
_DECIMAL_RE = re.compile(r"(\d)\.\d")
# Iniciales: J.R.R., A.B.
_INITIALS_RE = re.compile(r"\b[A-ZÁÉÍÓÚÑ]\.")
# Enumeraciones: 1. 2. 3.
_ENUMERATION_RE = re.compile(r"(?:^|\s)\d+\.")


def normalize_sentence_breaks(text_between: str) -> int:
    """
    Cuenta sentence breaks reales descartando falsos positivos.

    Normaliza puntos suspensivos, abreviaturas, decimales, iniciales
    y enumeraciones antes de contar.
    """
    t = text_between
    # Puntos suspensivos → un solo carácter placeholder
    t = _ELLIPSIS_RE.sub("…", t)
    # Abreviaturas → eliminar el punto
    t = _ABBREVIATION_RE.sub(lambda m: m.group(1), t)
    # Decimales → eliminar el punto entre dígitos
    t = _DECIMAL_RE.sub(r"\1", t)
    # Iniciales → eliminar el punto tras la letra
    t = _INITIALS_RE.sub("", t)
    # Enumeraciones → eliminar el punto tras el número
    t = _ENUMERATION_RE.sub("", t)
    # Contar solo los breaks reales que quedan
    return sum(1 for c in t if c in ".!?…")


# ---------------------------------------------------------------------------
# T2: Penalización base y detección de señales de continuidad
# ---------------------------------------------------------------------------
CROSS_SENTENCE_BASE_PENALTY = 175

# Patrones regex para detección de señales (Tier 1 — sin spaCy)
_GERUND_START_RE = re.compile(
    r"[.!?]\s+[A-ZÁÉÍÓÚÑ]?\w*(?:ando|endo|iendo)\b", re.IGNORECASE
)
_CAUSAL_START_RE = re.compile(
    r"[.!?]\s+(?:porque|ya que|puesto que|dado que|como)\b", re.IGNORECASE
)
_PARTICIPLE_START_RE = re.compile(
    r"[.!?]\s+(?:siendo|cansad[oa]|convencid[oa]|satisfech[oa]|"
    r"rendid[oa]|decidid[oa]|harto[a]?|agostad[oa])\b",
    re.IGNORECASE,
)
_TEMPORAL_START_RE = re.compile(
    r"[.!?]\s+(?:entonces|luego|después|acto seguido|a continuación|"
    r"seguidamente|al instante|inmediatamente)\b",
    re.IGNORECASE,
)
_ADVERSATIVE_START_RE = re.compile(
    r"[.!?]\s+(?:sin embargo|no obstante|a pesar de|aun así|con todo|"
    r"pese a)\b",
    re.IGNORECASE,
)
_COPULAR_PRODROP_RE = re.compile(
    r"[.!?]\s+(?:Era|Fue|Estaba|Parecía|Tenía|Llevaba)\b"
)
_POSSESSIVE_START_RE = re.compile(
    r"[.!?]\s+(?:Su|Sus)\s", re.IGNORECASE
)


def detect_continuity_signal(
    text: str, entity_end: int, attr_position: int, doc=None
) -> float:
    """
    Detecta señales lingüísticas de continuidad entre oraciones.

    Tier 1: Regex (siempre disponible)
    Tier 2: spaCy morph (cuando doc disponible)

    Returns:
        0.0 (sin señal, penalty completo) a 1.0 (señal fuerte, sin penalty)
    """
    span = text[entity_end:attr_position]
    if not span:
        return 0.0

    signal = 0.0

    # --- Tier 1: Regex ---
    if _GERUND_START_RE.search(span):
        signal = max(signal, 0.80)
    if _CAUSAL_START_RE.search(span):
        signal = max(signal, 0.75)
    if _COPULAR_PRODROP_RE.search(span):
        signal = max(signal, 0.65)
    if _PARTICIPLE_START_RE.search(span):
        signal = max(signal, 0.75)
    if _TEMPORAL_START_RE.search(span):
        signal = max(signal, 0.55)
    if _POSSESSIVE_START_RE.search(span):
        signal = max(signal, 0.50)
    if _ADVERSATIVE_START_RE.search(span):
        signal = max(signal, 0.40)

    # --- Tier 2: spaCy (si disponible) ---
    if doc is not None and signal < 0.80:
        try:
            signal = _detect_continuity_signal_spacy(
                doc, entity_end, attr_position, signal
            )
        except Exception:
            pass  # Graceful degradation: mantener señal regex

    return signal


def _detect_continuity_signal_spacy(
    doc, entity_end: int, attr_position: int, base_signal: float
) -> float:
    """Tier 2: detección con spaCy morph/dep."""
    from . import morpho_utils

    signal = base_signal

    # Encontrar la oración que contiene attr_position
    attr_sent = None
    for sent in doc.sents:
        if sent.start_char <= attr_position < sent.end_char:
            attr_sent = sent
            break
    if attr_sent is None:
        return signal

    # Primer token significativo de la oración del atributo
    first_token = None
    for token in attr_sent:
        if not token.is_space and not token.is_punct:
            first_token = token
            break
    if first_token is None:
        return signal

    # Gerundio sin sujeto propio
    if morpho_utils.is_gerund(first_token):
        has_own_subj = any(
            c.dep_ in ("nsubj", "nsubj:pass") for c in first_token.subtree
        )
        if not has_own_subj:
            signal = max(signal, 0.85)

    # Participio sin sujeto propio
    if morpho_utils.is_participle(first_token):
        has_own_subj = any(
            c.dep_ in ("nsubj", "nsubj:pass") for c in first_token.subtree
        )
        if not has_own_subj:
            signal = max(signal, 0.80)

    # Verbo copulativo sin sujeto (pro-drop)
    if morpho_utils.is_verb(first_token) and not morpho_utils.is_gerund(first_token):
        if not morpho_utils.has_explicit_subject(first_token):
            lemma = (first_token.lemma_ or "").lower()
            if lemma in ("ser", "estar", "parecer", "tener", "llevar"):
                signal = max(signal, 0.70)
            else:
                person = morpho_utils.get_person(first_token)
                if person == "3":
                    signal = max(signal, 0.60)

    return signal


# ---------------------------------------------------------------------------
# Extract sentence context — Canonical Implementation
# ---------------------------------------------------------------------------


def extract_sentence_context(
    text: str,
    position: int,
    max_len: int = 200,
    context_window: int = 80,
) -> str:
    """
    Extrae la oración que contiene la posición dada.

    Implementación canónica consolidada de:
    - grammar_checker._extract_sentence
    - semantic_checker._extract_sentence
    - spelling_checker._extract_sentence
    - voting_checker._extract_sentence
    - repetition_detector._extract_sentence

    Busca límites de oración (.!?\\n) hacia atrás y adelante.
    Si la oración supera max_len, centra una ventana de context_window
    alrededor de la posición.

    Args:
        text: Texto completo
        position: Posición (char offset) del punto de interés
        max_len: Longitud máxima de la oración extraída
        context_window: Radio de contexto si se trunca

    Returns:
        Texto de la oración (posiblemente truncado con "...")
    """
    if not text or position < 0 or position >= len(text):
        return ""

    # Buscar inicio de oración
    start = position
    while start > 0 and text[start - 1] not in ".!?\n":
        start -= 1
        if position - start > max_len:
            break

    # Buscar fin de oración
    end = position
    while end < len(text) and text[end] not in ".!?\n":
        end += 1
        if end - position > max_len:
            break

    sentence = text[start : end + 1].strip()

    if len(sentence) > max_len:
        word_start = position - start
        context_start = max(0, word_start - context_window)
        context_end = min(len(sentence), word_start + context_window)
        sentence = "..." + sentence[context_start:context_end] + "..."

    return sentence
