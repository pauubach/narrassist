"""
Cache persistente de métricas de habla en SQLite.

Almacena snapshots de métricas calculadas por ventana temporal,
permitiendo re-análisis 10-30x más rápido que cálculo desde cero.

Invalidación automática por document_fingerprint cuando el manuscrito cambia.
"""

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# Singleton global
_global_cache: Optional["SpeechMetricsDBCache"] = None
_cache_lock = threading.Lock()


class SpeechMetricsDBCache:
    """
    Cache persistente de métricas de habla en SQLite.

    Características:
    - Persistencia entre sesiones (sobrevive restart)
    - Invalidación automática por fingerprint
    - Thread-safe (usa transacciones SQLite)
    - Índices optimizados para lookup rápido (<10ms)
    """

    def __init__(self, db):
        """
        Inicializa el cache.

        Args:
            db: Instancia de Database (connection pool)
        """
        self._db = db
        self._hits = 0
        self._misses = 0

    def get(
        self,
        character_id: int,
        window_start_chapter: int,
        window_end_chapter: int,
        document_fingerprint: str,
    ) -> Optional[dict[str, float]]:
        """
        Recupera métricas del cache.

        Args:
            character_id: ID de la entidad (personaje)
            window_start_chapter: Capítulo inicial de la ventana
            window_end_chapter: Capítulo final de la ventana
            document_fingerprint: SHA-256 del documento

        Returns:
            Dict con 6 métricas si existe en cache, None si no
        """
        with self._db.connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    filler_rate,
                    formality_score,
                    avg_sentence_length,
                    lexical_diversity,
                    exclamation_rate,
                    question_rate
                FROM character_speech_snapshots
                WHERE character_id = ?
                  AND window_start_chapter = ?
                  AND window_end_chapter = ?
                  AND document_fingerprint = ?
                """,
                (
                    character_id,
                    window_start_chapter,
                    window_end_chapter,
                    document_fingerprint,
                ),
            )

            row = cursor.fetchone()

            if row:
                self._hits += 1
                logger.debug(
                    f"Cache HIT: char={character_id}, "
                    f"window={window_start_chapter}-{window_end_chapter} "
                    f"(hit rate: {self.hit_rate:.1%})"
                )

                return {
                    "filler_rate": row[0],
                    "formality_score": row[1],
                    "avg_sentence_length": row[2],
                    "lexical_diversity": row[3],
                    "exclamation_rate": row[4],
                    "question_rate": row[5],
                }

            # Miss
            self._misses += 1
            logger.debug(
                f"Cache MISS: char={character_id}, "
                f"window={window_start_chapter}-{window_end_chapter} "
                f"(hit rate: {self.hit_rate:.1%})"
            )
            return None

    def set(
        self,
        character_id: int,
        window_start_chapter: int,
        window_end_chapter: int,
        document_fingerprint: str,
        metrics: dict[str, float],
        total_words: int,
        dialogue_count: int,
    ) -> None:
        """
        Almacena métricas en cache.

        Args:
            character_id: ID de la entidad
            window_start_chapter: Capítulo inicial
            window_end_chapter: Capítulo final
            document_fingerprint: SHA-256 del documento
            metrics: Dict con 6 métricas calculadas
            total_words: Total de palabras en la ventana
            dialogue_count: Número de diálogos en la ventana
        """
        with self._db.connection() as conn:
            cursor = conn.cursor()

            # INSERT OR REPLACE (upsert)
            cursor.execute(
                """
                INSERT OR REPLACE INTO character_speech_snapshots (
                    character_id,
                    window_start_chapter,
                    window_end_chapter,
                    filler_rate,
                    formality_score,
                    avg_sentence_length,
                    lexical_diversity,
                    exclamation_rate,
                    question_rate,
                    total_words,
                    dialogue_count,
                    document_fingerprint
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    character_id,
                    window_start_chapter,
                    window_end_chapter,
                    metrics["filler_rate"],
                    metrics["formality_score"],
                    metrics["avg_sentence_length"],
                    metrics["lexical_diversity"],
                    metrics["exclamation_rate"],
                    metrics["question_rate"],
                    total_words,
                    dialogue_count,
                    document_fingerprint,
                ),
            )

            conn.commit()

            logger.debug(
                f"Cache SET: char={character_id}, "
                f"window={window_start_chapter}-{window_end_chapter}"
            )

    def invalidate_by_fingerprint(self, old_fingerprint: str) -> int:
        """
        Invalida cache cuando documento cambia.

        Args:
            old_fingerprint: SHA-256 del documento viejo

        Returns:
            Número de snapshots eliminados
        """
        with self._db.connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                DELETE FROM character_speech_snapshots
                WHERE document_fingerprint = ?
                """,
                (old_fingerprint,),
            )

            deleted = cursor.rowcount
            conn.commit()

            if deleted > 0:
                logger.info(f"Cache INVALIDATE: {deleted} snapshots deleted (fingerprint changed)")

            return deleted

    def clear_all(self) -> int:
        """
        Limpia TODO el cache (todas las versiones de todos los documentos).

        Returns:
            Número de snapshots eliminados
        """
        with self._db.connection() as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM character_speech_snapshots")

            deleted = cursor.rowcount
            conn.commit()

            logger.info(f"Cache CLEAR ALL: {deleted} snapshots deleted")

            return deleted

    def get_stats(self) -> dict:
        """
        Estadísticas del cache.

        Returns:
            Dict con: size (entradas actuales), hits, misses, hit_rate
        """
        with self._db.connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM character_speech_snapshots")
            size = cursor.fetchone()[0]

        return {
            "size": size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate,
        }

    @property
    def hit_rate(self) -> float:
        """Tasa de aciertos del cache (0.0 - 1.0)."""
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total


def get_db_cache() -> SpeechMetricsDBCache:
    """
    Obtiene instancia global del cache.

    Returns:
        SpeechMetricsDBCache singleton
    """
    global _global_cache

    if _global_cache is None:
        with _cache_lock:
            if _global_cache is None:
                from ...persistence.database import get_database

                db = get_database()
                _global_cache = SpeechMetricsDBCache(db)
                logger.info("Speech metrics DB cache initialized")

    return _global_cache


def clear_db_cache() -> int:
    """
    Limpia el cache global.

    Returns:
        Número de snapshots eliminados
    """
    cache = get_db_cache()
    return cache.clear_all()
