"""
Detector de sílaba tónica para español.

Proporciona detección híbrida (lista + automática) de sustantivos femeninos
que empiezan por /a/ o /ha/ tónica y requieren artículo masculino.

Estrategia:
1. Lista estática (rápida, 100% confiable) - FAST PATH
2. Detección automática con silabeador (flexible, neologismos) - FALLBACK
3. Cache de resultados (optimización)

Autor: S15 - Investigation based on RAE, Hispanoteca, silabeador
"""

import logging
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

# Cache global para resultados de detección automática
# Evita procesar la misma palabra múltiples veces
_DETECTION_CACHE: dict[str, bool] = {}

# Flag para indicar si silabeador está disponible
_SILABEADOR_AVAILABLE: Optional[bool] = None


def _check_silabeador() -> bool:
    """
    Verifica si la librería silabeador está disponible.

    Returns:
        True si silabeador puede usarse, False si no está instalada o falla
    """
    global _SILABEADOR_AVAILABLE

    if _SILABEADOR_AVAILABLE is not None:
        return _SILABEADOR_AVAILABLE

    try:
        from silabeador import silabear, tonica  # noqa: F401

        _SILABEADOR_AVAILABLE = True
        logger.debug("silabeador disponible para detección automática de sílaba tónica")
        return True
    except ImportError:
        _SILABEADOR_AVAILABLE = False
        logger.warning(
            "silabeador no disponible - solo se usará lista estática. "
            "Instalar con: pip install silabeador"
        )
        return False


def is_feminine_with_stressed_a(word: str, use_automatic_detection: bool = True) -> bool:
    """
    Detecta si una palabra femenina empieza con /a/ o /ha/ tónica.

    Estrategia híbrida:
    1. Verifica si está en cache
    2. Si no, usa detección automática con silabeador (si está disponible)

    Args:
        word: Palabra a analizar (sustantivo femenino)
        use_automatic_detection: Si True, usa silabeador como fallback

    Returns:
        True si la palabra cumple la regla (debe usar "el" en lugar de "la")
        False en caso contrario

    Examples:
        >>> is_feminine_with_stressed_a("agua")
        True  # "el agua"
        >>> is_feminine_with_stressed_a("academia")
        False  # "la academia" (a átona)
        >>> is_feminine_with_stressed_a("amapola")
        False  # "la amapola" (a átona)
    """
    word_lower = word.lower()

    # 1. Verificar cache (optimización)
    if word_lower in _DETECTION_CACHE:
        return _DETECTION_CACHE[word_lower]

    # 2. Verificar que empiece con 'a' o 'ha'
    if not (word_lower.startswith("a") or word_lower.startswith("ha")):
        _DETECTION_CACHE[word_lower] = False
        return False

    # 3. Detección automática (si está habilitada y disponible)
    if use_automatic_detection and _check_silabeador():
        try:
            result = _detect_stressed_a_automatic(word_lower)
            _DETECTION_CACHE[word_lower] = result
            return result
        except Exception as e:
            logger.debug(f"Error en detección automática de '{word}': {e}")
            # Fallback: asumir False (usar "la")
            _DETECTION_CACHE[word_lower] = False
            return False

    # 4. Si no hay detección automática, devolver False (conservador)
    _DETECTION_CACHE[word_lower] = False
    return False


def _detect_stressed_a_automatic(word: str) -> bool:
    """
    Detección automática usando silabeador (requiere librería instalada).

    Args:
        word: Palabra a analizar (lowercase)

    Returns:
        True si la primera sílaba es tónica y empieza con 'a'/'ha'
    """
    try:
        from silabeador import silabear, tonica
    except ImportError:
        return False

    # 1. Silabear la palabra
    syllables = silabear(word)

    if not syllables or len(syllables) == 0:
        return False

    # 2. Obtener índice de sílaba tónica (0-indexed)
    try:
        stressed_index = tonica(word)
    except Exception:
        return False

    # 3. Verificar que la primera sílaba sea la tónica
    if stressed_index != 0:
        return False

    # 4. Verificar que la primera sílaba empiece con 'a' o 'ha'
    first_syllable = syllables[0].lower()

    # Normalizar: remover acentos para comparación
    # 'á' → 'a', 'há' → 'ha'
    first_syllable_normalized = (
        first_syllable.replace("á", "a")
        .replace("à", "a")
        .replace("â", "a")
    )

    return first_syllable_normalized.startswith(("a", "ha"))


@lru_cache(maxsize=512)
def requires_masculine_article(
    word: str,
    is_feminine: bool,
    is_plural: bool = False,
    use_static_list: bool = True,
    use_automatic_detection: bool = True,
) -> bool:
    """
    Determina si un sustantivo femenino requiere artículo masculino.

    Implementación híbrida (S15):
    1. Lista estática (FAST PATH - palabras comunes)
    2. Excepciones explícitas (letras del alfabeto, etc.)
    3. Detección automática (FALLBACK - neologismos, tecnicismos)

    Args:
        word: Sustantivo a evaluar
        is_feminine: True si el sustantivo es femenino
        is_plural: True si está en plural (plural siempre usa "las")
        use_static_list: Si True, usa lista estática de palabras conocidas
        use_automatic_detection: Si True, usa silabeador como fallback

    Returns:
        True si requiere artículo masculino ("el"/"un")
        False si usa artículo femenino normal ("la"/"una")

    Examples:
        >>> requires_masculine_article("agua", is_feminine=True)
        True  # "el agua"
        >>> requires_masculine_article("aguas", is_feminine=True, is_plural=True)
        False  # "las aguas" (plural → femenino)
        >>> requires_masculine_article("a", is_feminine=True)  # letra
        False  # "la a" (excepción RAE)
    """
    # 0. Si no es femenino, no aplica la regla
    if not is_feminine:
        return False

    # 1. Si es plural, SIEMPRE usa artículo femenino
    if is_plural:
        return False

    word_lower = word.lower()

    # 2. Excepciones explícitas (RAE) - SIEMPRE usan "la"
    EXCEPTIONS = {
        "a",      # "la a" (letra del alfabeto)
        "hache",  # "la hache" (letra H)
        "alfa",   # "la alfa" (letra griega)
    }

    if word_lower in EXCEPTIONS:
        return False

    # 3. Lista estática (FAST PATH - palabras comunes)
    if use_static_list:
        FEMININE_WITH_EL = {
            # Grupo 1: Palabras comunes
            "agua", "águila", "alma", "arma", "hambre", "área", "aula", "hacha", "hada",
            "ama", "ala", "alba", "alga", "anca", "ancla", "ansia", "arca", "arpa",
            "asa", "aspa", "asta", "aura", "ave", "aya", "habla", "haba",
            # Grupo 2: Adicionales (S15)
            "acta", "afta", "agria", "alca", "ánfora", "ánima", "ánade", "aria",
            "ascua", "asma", "áurea",
            # Grupo 3: Técnicas/cultas
            "álgebra", "áncora", "ápoda", "árula", "átala", "ábside",
        }

        if word_lower in FEMININE_WITH_EL:
            return True

    # 4. Detección automática (FALLBACK - neologismos, tecnicismos)
    if use_automatic_detection:
        return is_feminine_with_stressed_a(word_lower, use_automatic_detection=True)

    # 5. Por defecto: usar artículo femenino normal (conservador)
    return False


def clear_cache():
    """
    Limpia el cache de detección automática.

    Útil para tests o cuando se necesita forzar re-detección.
    """
    global _DETECTION_CACHE
    _DETECTION_CACHE.clear()
    requires_masculine_article.cache_clear()
    logger.debug("Cache de detección de 'a' tónica limpiado")


def get_cache_stats() -> dict[str, int]:
    """
    Obtiene estadísticas del cache de detección.

    Returns:
        Diccionario con:
        - cached_words: Número de palabras en cache
        - lru_hits: Hits del cache LRU
        - lru_misses: Misses del cache LRU
    """
    cache_info = requires_masculine_article.cache_info()
    return {
        "cached_words": len(_DETECTION_CACHE),
        "lru_hits": cache_info.hits,
        "lru_misses": cache_info.misses,
        "lru_size": cache_info.currsize,
        "lru_maxsize": cache_info.maxsize,
    }
