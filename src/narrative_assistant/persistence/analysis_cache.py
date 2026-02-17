"""
Cache persistente para fases de análisis costosas (NER, correferencias, atributos).

Permite re-análisis 100x más rápido cuando el documento NO ha cambiado.
Invalidación automática por document_fingerprint.

Inspirado en speech_tracking/db_cache.py (v0.10.14).
"""

import hashlib
import json
import logging
import os
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# Feature flag para rollback sin deploy
CACHE_ENABLED = os.getenv("NA_CACHE_ENABLED", "true").lower() == "true"

# Singleton global
_global_cache: Optional["AnalysisCache"] = None
_cache_lock = threading.Lock()


class AnalysisCache:
    """
    Cache persistente para fases de análisis en SQLite.

    Características:
    - Persistencia entre sesiones (sobrevive restart)
    - Invalidación automática por fingerprint
    - Config-aware (cache separado por config diferente)
    - Thread-safe (transacciones SQLite)
    - Índices optimizados (<10ms lookup)
    - Graceful degradation (error → recalculate)
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

    # ========================================================================
    # NER Cache (3-5 min → <1s)
    # ========================================================================

    def get_ner_results(
        self,
        project_id: int,
        document_fingerprint: str,
        config_hash: str,
    ) -> Optional[dict]:
        """
        Recupera resultados de NER del cache.

        Args:
            project_id: ID del proyecto
            document_fingerprint: SHA-256 del documento
            config_hash: Hash de configuración NER (16 chars)

        Returns:
            Dict con {entities_json, entity_count, mention_count} o None
        """
        if not CACHE_ENABLED:
            return None

        try:
            with self._db.connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT entities_json, entity_count, mention_count
                    FROM ner_cache
                    WHERE project_id = ?
                      AND document_fingerprint = ?
                      AND config_hash = ?
                    """,
                    (project_id, document_fingerprint, config_hash),
                )

                row = cursor.fetchone()

                if row:
                    self._hits += 1
                    logger.info(
                        f"[NER_CACHE] HIT: project={project_id}, "
                        f"fp={document_fingerprint[:16]}..., "
                        f"config={config_hash}, "
                        f"entities={row[1]} (hit rate: {self.hit_rate:.1%})"
                    )

                    return {
                        "entities_json": row[0],
                        "entity_count": row[1],
                        "mention_count": row[2],
                    }

                # Miss
                self._misses += 1
                logger.debug(
                    f"[NER_CACHE] MISS: project={project_id}, "
                    f"config={config_hash} (hit rate: {self.hit_rate:.1%})"
                )
                return None

        except Exception as e:
            logger.warning(f"NER cache read failed (continuing): {e}")
            return None  # Graceful degradation

    def set_ner_results(
        self,
        project_id: int,
        document_fingerprint: str,
        config_hash: str,
        entities_json: str,
        entity_count: int,
        mention_count: int,
        processed_chars: int,
    ) -> None:
        """
        Almacena resultados de NER en cache.

        Args:
            project_id: ID del proyecto
            document_fingerprint: SHA-256
            config_hash: Hash de config
            entities_json: JSON serializado de entidades
            entity_count: Número de entidades
            mention_count: Número de menciones
            processed_chars: Caracteres procesados
        """
        if not CACHE_ENABLED:
            return

        try:
            with self._db.connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO ner_cache (
                        project_id,
                        document_fingerprint,
                        config_hash,
                        entities_json,
                        entity_count,
                        mention_count,
                        processed_chars
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        document_fingerprint,
                        config_hash,
                        entities_json,
                        entity_count,
                        mention_count,
                        processed_chars,
                    ),
                )

                conn.commit()

                logger.info(
                    f"[NER_CACHE] SET SUCCESS: project={project_id}, "
                    f"entities={entity_count}, mentions={mention_count}, "
                    f"fp={document_fingerprint[:16]}..."
                )

        except Exception as e:
            logger.warning(f"NER cache write failed (continuing): {e}")
            # No re-raise, graceful degradation

    # ========================================================================
    # Coreference Cache (5-7 min → <1s)
    # ========================================================================

    def get_coref_results(
        self,
        project_id: int,
        document_fingerprint: str,
        config_hash: str,
    ) -> Optional[dict]:
        """
        Recupera resultados de correferencias del cache.

        Returns:
            Dict con {chains_json, chain_count, mention_count} o None
        """
        if not CACHE_ENABLED:
            return None

        try:
            with self._db.connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT chains_json, chain_count, mention_count
                    FROM coreference_cache
                    WHERE project_id = ?
                      AND document_fingerprint = ?
                      AND config_hash = ?
                    """,
                    (project_id, document_fingerprint, config_hash),
                )

                row = cursor.fetchone()

                if row:
                    self._hits += 1
                    logger.info(
                        f"[COREF_CACHE] HIT: project={project_id}, "
                        f"chains={row[1]}, mentions={row[2]} "
                        f"(hit rate: {self.hit_rate:.1%})"
                    )

                    return {
                        "chains_json": row[0],
                        "chain_count": row[1],
                        "mention_count": row[2],
                    }

                # Miss
                self._misses += 1
                logger.debug(
                    f"[COREF_CACHE] MISS: project={project_id} "
                    f"(hit rate: {self.hit_rate:.1%})"
                )
                return None

        except Exception as e:
            logger.warning(f"Coref cache read failed (continuing): {e}")
            return None

    def set_coref_results(
        self,
        project_id: int,
        document_fingerprint: str,
        config_hash: str,
        chains_json: str,
        chain_count: int,
        mention_count: int,
    ) -> None:
        """Almacena resultados de correferencias en cache."""
        if not CACHE_ENABLED:
            return

        try:
            with self._db.connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO coreference_cache (
                        project_id,
                        document_fingerprint,
                        config_hash,
                        chains_json,
                        chain_count,
                        mention_count
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        document_fingerprint,
                        config_hash,
                        chains_json,
                        chain_count,
                        mention_count,
                    ),
                )

                conn.commit()

                logger.info(
                    f"[COREF_CACHE] SET SUCCESS: project={project_id}, "
                    f"chains={chain_count}, mentions={mention_count}"
                )

        except Exception as e:
            logger.warning(f"Coref cache write failed (continuing): {e}")

    # ========================================================================
    # Attribute Cache (30s → <1s)
    # ========================================================================

    def get_attribute_results(
        self,
        project_id: int,
        document_fingerprint: str,
        config_hash: str,
    ) -> Optional[dict]:
        """
        Recupera atributos del cache.

        Returns:
            Dict con {attributes_json, attribute_count, evidence_count} o None
        """
        if not CACHE_ENABLED:
            return None

        try:
            with self._db.connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT attributes_json, attribute_count, evidence_count
                    FROM attribute_cache
                    WHERE project_id = ?
                      AND document_fingerprint = ?
                      AND config_hash = ?
                    """,
                    (project_id, document_fingerprint, config_hash),
                )

                row = cursor.fetchone()

                if row:
                    self._hits += 1
                    logger.info(
                        f"[ATTR_CACHE] HIT: project={project_id}, "
                        f"attrs={row[1]}, evidence={row[2]} "
                        f"(hit rate: {self.hit_rate:.1%})"
                    )

                    return {
                        "attributes_json": row[0],
                        "attribute_count": row[1],
                        "evidence_count": row[2],
                    }

                # Miss
                self._misses += 1
                logger.debug(
                    f"[ATTR_CACHE] MISS: project={project_id} "
                    f"(hit rate: {self.hit_rate:.1%})"
                )
                return None

        except Exception as e:
            logger.warning(f"Attribute cache read failed (continuing): {e}")
            return None

    def set_attribute_results(
        self,
        project_id: int,
        document_fingerprint: str,
        config_hash: str,
        attributes_json: str,
        attribute_count: int,
        evidence_count: int,
    ) -> None:
        """Almacena atributos en cache."""
        if not CACHE_ENABLED:
            return

        try:
            with self._db.connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO attribute_cache (
                        project_id,
                        document_fingerprint,
                        config_hash,
                        attributes_json,
                        attribute_count,
                        evidence_count
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        document_fingerprint,
                        config_hash,
                        attributes_json,
                        attribute_count,
                        evidence_count,
                    ),
                )

                conn.commit()

                logger.info(
                    f"[ATTR_CACHE] SET SUCCESS: project={project_id}, "
                    f"attrs={attribute_count}, evidence={evidence_count}"
                )

        except Exception as e:
            logger.warning(f"Attribute cache write failed (continuing): {e}")

    # ========================================================================
    # Config Hashing (deterministic, reproducible)
    # ========================================================================

    @staticmethod
    def compute_ner_config_hash(config) -> str:
        """
        Computa hash de configuración NER (16 chars).

        Incluye: llm enabled, transformer enabled, gazetteer enabled

        Args:
            config: UnifiedConfig o similar

        Returns:
            Hash hex de 16 caracteres
        """
        # Extraer campos relevantes
        config_dict = {
            "use_llm": getattr(config, "use_llm", False),
            "run_ner": getattr(config, "run_ner", True),
            # Agregar más campos si NERExtractor los usa
        }

        # Serializar a JSON determinístico
        config_json = json.dumps(config_dict, sort_keys=True)

        # SHA-256 y truncar a 16 chars
        return hashlib.sha256(config_json.encode()).hexdigest()[:16]

    @staticmethod
    def compute_coref_config_hash(config) -> str:
        """
        Computa hash de configuración correferencias.

        Incluye: enabled_methods, min_confidence, consensus_threshold, quality_level
        """
        # CorefConfig tiene: enabled_methods, min_confidence, consensus_threshold,
        # quality_level, sensitivity
        if hasattr(config, "enabled_methods"):
            # Es un CorefConfig
            config_dict = {
                "enabled_methods": [str(m) for m in config.enabled_methods],
                "min_confidence": config.min_confidence,
                "consensus_threshold": config.consensus_threshold,
                "quality_level": getattr(config, "quality_level", "rapida"),
                "sensitivity": getattr(config, "sensitivity", 5.0),
            }
        else:
            # Fallback para UnifiedConfig
            config_dict = {
                "run_coreference": getattr(config, "run_coreference", True),
                "use_llm": getattr(config, "use_llm", False),
            }

        config_json = json.dumps(config_dict, sort_keys=True)
        return hashlib.sha256(config_json.encode()).hexdigest()[:16]

    @staticmethod
    def compute_attribute_config_hash(config) -> str:
        """Computa hash de configuración atributos."""
        config_dict = {
            "run_attributes": getattr(config, "run_attributes", True),
            # Agregar más si AttributeExtractor tiene config
        }

        config_json = json.dumps(config_dict, sort_keys=True)
        return hashlib.sha256(config_json.encode()).hexdigest()[:16]

    # ========================================================================
    # Invalidation & Stats
    # ========================================================================

    def invalidate_by_fingerprint(self, old_fingerprint: str) -> int:
        """
        Invalida TODOS los caches cuando documento cambia.

        Args:
            old_fingerprint: SHA-256 del documento viejo

        Returns:
            Número total de entradas eliminadas
        """
        total_deleted = 0

        try:
            with self._db.connection() as conn:
                cursor = conn.cursor()

                # NER cache
                cursor.execute(
                    "DELETE FROM ner_cache WHERE document_fingerprint = ?",
                    (old_fingerprint,),
                )
                total_deleted += cursor.rowcount

                # Coref cache
                cursor.execute(
                    "DELETE FROM coreference_cache WHERE document_fingerprint = ?",
                    (old_fingerprint,),
                )
                total_deleted += cursor.rowcount

                # Attr cache
                cursor.execute(
                    "DELETE FROM attribute_cache WHERE document_fingerprint = ?",
                    (old_fingerprint,),
                )
                total_deleted += cursor.rowcount

                conn.commit()

                if total_deleted > 0:
                    logger.info(
                        f"[CACHE] INVALIDATE: {total_deleted} entries deleted "
                        f"(fingerprint changed)"
                    )

        except Exception as e:
            logger.warning(f"Cache invalidation failed: {e}")

        return total_deleted

    def clear_all(self) -> int:
        """
        Limpia TODO el cache (todos los proyectos).

        Returns:
            Número total de entradas eliminadas
        """
        total_deleted = 0

        try:
            with self._db.connection() as conn:
                cursor = conn.cursor()

                cursor.execute("DELETE FROM ner_cache")
                total_deleted += cursor.rowcount

                cursor.execute("DELETE FROM coreference_cache")
                total_deleted += cursor.rowcount

                cursor.execute("DELETE FROM attribute_cache")
                total_deleted += cursor.rowcount

                conn.commit()

                logger.info(f"[CACHE] CLEAR ALL: {total_deleted} entries deleted")

        except Exception as e:
            logger.warning(f"Cache clear failed: {e}")

        return total_deleted

    def get_stats(self) -> dict:
        """
        Estadísticas del cache.

        Returns:
            Dict con: ner_size, coref_size, attr_size, hits, misses, hit_rate
        """
        stats = {
            "ner_size": 0,
            "coref_size": 0,
            "attr_size": 0,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate,
        }

        try:
            with self._db.connection() as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM ner_cache")
                stats["ner_size"] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM coreference_cache")
                stats["coref_size"] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM attribute_cache")
                stats["attr_size"] = cursor.fetchone()[0]

        except Exception as e:
            logger.warning(f"Cache stats failed: {e}")

        return stats

    @property
    def hit_rate(self) -> float:
        """Tasa de aciertos del cache (0.0 - 1.0)."""
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return float(self._hits / total)


# ============================================================================
# Singleton Pattern
# ============================================================================


def get_analysis_cache() -> AnalysisCache:
    """
    Obtiene instancia global del cache.

    Returns:
        AnalysisCache singleton
    """
    global _global_cache

    if _global_cache is None:
        with _cache_lock:
            if _global_cache is None:
                from .database import get_database

                db = get_database()
                _global_cache = AnalysisCache(db)

                if CACHE_ENABLED:
                    logger.info("Analysis cache initialized (ENABLED)")
                else:
                    logger.warning(
                        "Analysis cache initialized (DISABLED via NA_CACHE_ENABLED=false)"
                    )

    return _global_cache


def clear_analysis_cache() -> int:
    """
    Limpia el cache global.

    Returns:
        Número de entradas eliminadas
    """
    cache = get_analysis_cache()
    return cache.clear_all()
