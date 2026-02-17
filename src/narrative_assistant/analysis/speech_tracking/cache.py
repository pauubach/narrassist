"""
Cache en memoria para métricas de habla.

Evita recalcular métricas para el mismo texto, mejorando performance
en re-análisis y comparaciones múltiples.
"""

import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class MetricsCache:
    """
    Cache LRU para métricas de habla.

    Almacena métricas calculadas usando hash del texto como clave.
    Limita memoria usando LRU (Least Recently Used) eviction.
    """

    def __init__(self, max_size: int = 1000):
        """
        Inicializa el cache.

        Args:
            max_size: Máximo número de entradas (default: 1000)
        """
        self._cache: dict[str, dict[str, float]] = {}
        self._access_order: list[str] = []  # LRU tracking
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def get(self, text: str) -> Optional[dict[str, float]]:
        """
        Recupera métricas del cache.

        Args:
            text: Texto a buscar

        Returns:
            Métricas calculadas si existe en cache, None si no
        """
        cache_key = self._hash_text(text)

        if cache_key in self._cache:
            # Hit: Actualizar LRU order
            self._access_order.remove(cache_key)
            self._access_order.append(cache_key)
            self._hits += 1

            logger.debug(f"Cache HIT: {cache_key[:16]}... (hit rate: {self.hit_rate:.1%})")
            return self._cache[cache_key]

        # Miss
        self._misses += 1
        logger.debug(f"Cache MISS: {cache_key[:16]}... (hit rate: {self.hit_rate:.1%})")
        return None

    def set(self, text: str, metrics: dict[str, float]) -> None:
        """
        Almacena métricas en cache.

        Args:
            text: Texto original
            metrics: Métricas calculadas
        """
        cache_key = self._hash_text(text)

        # Eviction si alcanzamos max_size
        if len(self._cache) >= self._max_size:
            # Remover entrada más antigua (LRU)
            oldest_key = self._access_order.pop(0)
            del self._cache[oldest_key]
            logger.debug(f"Cache EVICT: {oldest_key[:16]}... (size: {len(self._cache)})")

        # Almacenar
        self._cache[cache_key] = metrics
        self._access_order.append(cache_key)

        logger.debug(
            f"Cache SET: {cache_key[:16]}... (size: {len(self._cache)}/{self._max_size})"
        )

    def clear(self) -> None:
        """Limpia el cache completamente."""
        size_before = len(self._cache)
        self._cache.clear()
        self._access_order.clear()
        self._hits = 0
        self._misses = 0
        logger.info(f"Cache cleared ({size_before} entries removed)")

    @property
    def hit_rate(self) -> float:
        """Tasa de aciertos del cache (0.0 - 1.0)."""
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total

    @property
    def size(self) -> int:
        """Número actual de entradas en cache."""
        return len(self._cache)

    @staticmethod
    def _hash_text(text: str) -> str:
        """
        Genera hash SHA-256 del texto.

        Args:
            text: Texto a hashear

        Returns:
            Hash hexadecimal (64 caracteres)
        """
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


# Cache global singleton
_global_cache: Optional[MetricsCache] = None


def get_metrics_cache() -> MetricsCache:
    """
    Obtiene instancia global del cache.

    Returns:
        MetricsCache singleton
    """
    global _global_cache

    if _global_cache is None:
        _global_cache = MetricsCache(max_size=1000)
        logger.info("Metrics cache initialized (max_size=1000)")

    return _global_cache


def clear_metrics_cache() -> None:
    """Limpia el cache global."""
    cache = get_metrics_cache()
    cache.clear()
