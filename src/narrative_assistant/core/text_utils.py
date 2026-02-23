"""
Utilidades consolidadas de normalización de texto.

Módulo DRY que reemplaza 10+ implementaciones duplicadas de normalize_name,
strip_accents y funciones de similitud dispersas por el codebase.

Uso:
    from narrative_assistant.core.text_utils import (
        normalize_name,
        strip_accents,
        names_match,
        normalize_for_lookup,
        jaccard_similarity,
        token_jaccard,
        char_ngrams,
    )

Módulos que deben usar estas funciones (en vez de reimplementar):
  - nlp/morpho_utils.py (ya exporta normalize_name)
  - entities/semantic_fusion.py (strip_accents, normalize_for_comparison)
  - analysis/entity_matcher.py (_normalize_name, jaccard_similarity)
  - analysis/entity_continuity_service.py (_strip_accents, _normalize_name)
  - analysis/name_variant_detector.py (_normalize)
  - voice/speaker_attribution.py (_normalize_name_key)
  - persistence/manuscript_identity.py (_normalize)
  - persistence/version_diff.py (_normalize_name)
  - pipelines/ua_resolution.py (_normalize_name)
  - pipelines/unified_analysis.py (_normalize_key)
  - pipelines/ua_ner.py (_normalize_key)
"""

from __future__ import annotations

import re
import unicodedata

# Pre-compilados para rendimiento
_COMBINING_MARK_RE = re.compile(r"[\u0300-\u036f]")
_WHITESPACE_RE = re.compile(r"\s+")
_NON_WORD_RE = re.compile(r"[^\w\s]")


def strip_accents(text: str, preserve_ñ: bool = True) -> str:
    """
    Quita acentos diacríticos del texto para comparación.

    Args:
        text: Texto con posibles acentos
        preserve_ñ: Si True (default), mantiene ñ/Ñ (es letra, no acento)

    Returns:
        Texto sin acentos diacríticos

    Examples:
        >>> strip_accents("María")
        'Maria'
        >>> strip_accents("José García")
        'Jose Garcia'
        >>> strip_accents("niño")
        'niño'
        >>> strip_accents("niño", preserve_ñ=False)
        'nino'
    """
    if not text:
        return text

    if preserve_ñ:
        # Preservar ñ/Ñ usando placeholders antes de normalización
        _PH_LOWER = "\x00\x01"
        _PH_UPPER = "\x00\x02"
        text = text.replace("ñ", _PH_LOWER).replace("Ñ", _PH_UPPER)
        normalized = unicodedata.normalize("NFD", text)
        result = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
        result = unicodedata.normalize("NFC", result)
        return result.replace(_PH_LOWER, "ñ").replace(_PH_UPPER, "Ñ")
    else:
        # Versión rápida sin preservar ñ (para comparación de nombres)
        normalized = unicodedata.normalize("NFKD", text)
        return _COMBINING_MARK_RE.sub("", normalized)


def normalize_name(text: str) -> str:
    """
    Normaliza un nombre para comparación: lowercase, sin acentos, sin espacios extra.

    Permite que "María García" y "Maria Garcia" se fusionen como la misma entidad.
    También "José" y "Jose", "García" y "Garcia", etc.

    Args:
        text: Nombre a normalizar

    Returns:
        Nombre normalizado sin acentos, en minúsculas, whitespace colapsado

    Examples:
        >>> normalize_name("María García")
        'maria garcia'
        >>> normalize_name("José  de la   Cruz")
        'jose de la cruz'
    """
    if not text:
        return ""
    # NFKD para descomponer + eliminar combining marks + lower + colapsar whitespace
    stripped = strip_accents(text, preserve_ñ=False)
    return " ".join(stripped.lower().split())


def normalize_for_lookup(word: str) -> str:
    """
    Normaliza una palabra para búsqueda en diccionarios/lexicones.

    Más agresivo que normalize_name: elimina puntuación además de acentos.

    Args:
        word: Palabra a normalizar

    Returns:
        Palabra normalizada para lookup

    Examples:
        >>> normalize_for_lookup("¿Cómo?")
        'como'
        >>> normalize_for_lookup("García-López")
        'garcialopez'
    """
    if not word:
        return ""
    base = normalize_name(word)
    return _NON_WORD_RE.sub("", base).strip()


def names_match(name1: str, name2: str) -> bool:
    """
    Compara dos nombres ignorando acentos y capitalización.

    Args:
        name1: Primer nombre
        name2: Segundo nombre

    Returns:
        True si los nombres normalizados son iguales

    Examples:
        >>> names_match("María García", "Maria Garcia")
        True
        >>> names_match("José", "jose")
        True
    """
    return normalize_name(name1) == normalize_name(name2)


def jaccard_similarity(set_a: set, set_b: set) -> float:
    """
    Calcula similitud Jaccard entre dos conjuntos.

    Args:
        set_a: Primer conjunto
        set_b: Segundo conjunto

    Returns:
        Similitud Jaccard [0.0, 1.0]
    """
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def token_jaccard(text1: str, text2: str) -> float:
    """
    Similitud Jaccard por tokens (palabras).

    Args:
        text1: Primer texto
        text2: Segundo texto

    Returns:
        Similitud Jaccard por tokens [0.0, 1.0]
    """
    tokens1 = set(normalize_name(text1).split())
    tokens2 = set(normalize_name(text2).split())
    return jaccard_similarity(tokens1, tokens2)


def char_ngrams(text: str, n: int = 3) -> set[str]:
    """
    Genera n-gramas de caracteres para similitud por trigrams.

    Args:
        text: Texto a procesar
        n: Tamaño de los n-gramas (default 3)

    Returns:
        Conjunto de n-gramas de caracteres
    """
    normalized = normalize_name(text)
    if len(normalized) < n:
        return {normalized} if normalized else set()
    return {normalized[i : i + n] for i in range(len(normalized) - n + 1)}
