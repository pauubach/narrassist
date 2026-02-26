"""
Enrichment cache helper — shared by all routers.

Provides get_cached_enrichment() which reads from enrichment_cache table.
If data is available and not stale, returns it instantly.
Otherwise returns None so the endpoint can compute on-the-fly (legacy path).

S8a-13: Endpoints GET read from cache/DB instead of computing.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# Schema versions per enrichment type.
#
# Bump the version when the computation logic or output format changes.
# Cached entries with an older schema_version are treated as stale/missing
# and will be recomputed on next access.
#
# ONLY bump the specific enrichment(s) whose code changed.
# ============================================================================

ENRICHMENT_SCHEMA_VERSIONS: dict[str, int] = {
    # Phase 10 — Relationships
    "network_relationships": 1,
    "character_network": 1,  # Network metrics (centralidad, puentes, evolución)
    "timeline": 1,
    "character_timeline": 1,  # Timeline de apariciones por capítulo
    "character_profiles": 1,
    "location_data": 1,
    "character_locations": 1,  # Análisis de ubicaciones de personajes
    "emotional_arcs": 1,
    "emotional_analysis": 1,  # Coherencia emocional
    "character_archetypes": 1,
    "knowledge_state": 1,
    # Phase 11 — Voice
    "voice_profiles": 1,
    "voice_deviations": 1,
    "register_analysis": 1,
    "focalization": 1,
    # Phase 12 — Prose
    "sticky_sentences": 1,
    "sentence_energy": 1,
    "echo_report": 1,
    "pacing_analysis": 1,
    "tension_curve": 1,
    "sensory_report": 1,
    "age_readability": 1,
    "sentence_variation": 1,
    "dialogue_validation": 1,
    "narrative_structure": 1,
    "duplicate_content": 1,
    # Phase 13 — Health
    "chapter_progress": 10,  # v10: expanded global_summary (3-5 frases, balance entre brevedad y detalle)
    "narrative_templates": 1,
    "narrative_health": 1,
}


def get_schema_version(enrichment_type: str) -> int:
    """Returns the current schema version for an enrichment type."""
    return ENRICHMENT_SCHEMA_VERSIONS.get(enrichment_type, 1)


# ============================================================================
# Mapping: enrichment type → enrichment phase name.
#
# Used by fast-path to determine which enrichment phases to re-run
# when schema versions are outdated.
# ============================================================================

ENRICHMENT_TO_PHASE: dict[str, str] = {
    # Phase 10 — Relationships
    "network_relationships": "relationships",
    "character_network": "relationships",
    "timeline": "relationships",
    "character_timeline": "relationships",
    "character_profiles": "relationships",
    "location_data": "relationships",
    "character_locations": "relationships",
    "emotional_arcs": "relationships",
    "emotional_analysis": "relationships",
    "character_archetypes": "relationships",
    "knowledge_state": "relationships",
    # Phase 11 — Voice
    "voice_profiles": "voice",
    "voice_deviations": "voice",
    "register_analysis": "voice",
    "focalization": "voice",
    # Phase 12 — Prose
    "sticky_sentences": "prose",
    "sentence_energy": "prose",
    "echo_report": "prose",
    "pacing_analysis": "prose",
    "tension_curve": "prose",
    "sensory_report": "prose",
    "age_readability": "prose",
    "sentence_variation": "prose",
    "dialogue_validation": "prose",
    "narrative_structure": "prose",
    "duplicate_content": "prose",
    # Phase 13 — Health
    "chapter_progress": "health",
    "narrative_templates": "health",
    "narrative_health": "health",
}


def get_stale_enrichment_phases(
    db_session: Any,
    project_id: int,
) -> set[str]:
    """Check which enrichment phases need recomputation due to schema version bumps.

    Returns a set of phase names (e.g., {"health", "prose"}) that have at least
    one enrichment type with an outdated or missing schema_version in the cache.
    """
    stale_phases: set[str] = set()
    try:
        with db_session.connection() as conn:
            rows = conn.execute(
                """SELECT enrichment_type, schema_version
                   FROM enrichment_cache
                   WHERE project_id = ? AND entity_scope IS NULL""",
                (project_id,),
            ).fetchall()

        cached = {row[0]: (row[1] or 0) for row in rows}

        for etype, required_version in ENRICHMENT_SCHEMA_VERSIONS.items():
            phase = ENRICHMENT_TO_PHASE.get(etype)
            if not phase:
                continue
            cached_version = cached.get(etype, 0)
            if cached_version < required_version:
                stale_phases.add(phase)

    except Exception as e:
        logger.warning(f"Error checking stale enrichment phases: {e}")

    return stale_phases


def get_cached_enrichment(
    db_session: Any,
    project_id: int,
    enrichment_type: str,
    entity_scope: str | None = None,
    allow_stale: bool = False,
) -> dict | list | None:
    """Read a cached enrichment result.

    Returns the parsed JSON result if cache hit, None if miss.
    Rejects entries whose schema_version is older than the current code version.
    """
    try:
        with db_session.connection() as conn:
            if allow_stale:
                status_filter = "status IN ('completed', 'stale')"
            else:
                status_filter = "status = 'completed'"

            scope_filter = "entity_scope IS NULL" if entity_scope is None else "entity_scope = ?"
            params: list = [project_id, enrichment_type]
            if entity_scope is not None:
                params.append(entity_scope)

            row = conn.execute(
                f"""SELECT result_json, status, computed_at, revision, schema_version
                    FROM enrichment_cache
                    WHERE project_id = ? AND enrichment_type = ?
                    AND {scope_filter} AND {status_filter}
                    ORDER BY updated_at DESC LIMIT 1""",
                params,
            ).fetchone()

            if row and row[0]:
                # Check schema version — reject outdated cache entries
                cached_schema = row[4] if len(row) > 4 and row[4] is not None else 0
                required_schema = get_schema_version(enrichment_type)
                if cached_schema < required_schema:
                    logger.info(
                        f"Cache STALE (schema v{cached_schema} < v{required_schema}) "
                        f"for {enrichment_type} project={project_id}"
                    )
                    return None

                result = json.loads(row[0])
                is_stale = row[1] == "stale"
                if is_stale:
                    logger.debug(f"Cache hit (STALE) for {enrichment_type} project={project_id}")
                else:
                    logger.debug(f"Cache hit for {enrichment_type} project={project_id}")
                # Annotate with cache metadata
                if isinstance(result, dict):
                    result["_cache"] = {
                        "hit": True,
                        "stale": is_stale,
                        "computed_at": row[2],
                        "revision": row[3] if len(row) > 3 else 0,
                        "schema_version": cached_schema,
                    }
                return result

    except Exception as e:
        logger.warning(f"Error reading enrichment cache for {enrichment_type}: {e}")

    return None


def get_enrichment_status(
    db_session: Any,
    project_id: int,
    enrichment_type: str,
) -> str | None:
    """Get the status of an enrichment (pending/computing/completed/failed/stale)."""
    try:
        with db_session.connection() as conn:
            row = conn.execute(
                """SELECT status FROM enrichment_cache
                   WHERE project_id = ? AND enrichment_type = ? AND entity_scope IS NULL
                   LIMIT 1""",
                (project_id, enrichment_type),
            ).fetchone()
            return row[0] if row else None
    except Exception:
        return None
