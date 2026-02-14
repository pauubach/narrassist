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


def get_cached_enrichment(
    db_session: Any,
    project_id: int,
    enrichment_type: str,
    entity_scope: str | None = None,
    allow_stale: bool = False,
) -> dict | list | None:
    """Read a cached enrichment result.

    Returns the parsed JSON result if cache hit, None if miss.
    """
    try:
        with db_session.connection() as conn:
            if allow_stale:
                status_filter = "status IN ('completed', 'stale')"
            else:
                status_filter = "status = 'completed'"

            scope_filter = "entity_scope IS NULL" if entity_scope is None else "entity_scope = ?"
            params = [project_id, enrichment_type]
            if entity_scope is not None:
                params.append(entity_scope)

            row = conn.execute(
                f"""SELECT result_json, status, computed_at, revision
                    FROM enrichment_cache
                    WHERE project_id = ? AND enrichment_type = ?
                    AND {scope_filter} AND {status_filter}
                    ORDER BY updated_at DESC LIMIT 1""",
                params,
            ).fetchone()

            if row and row[0]:
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
                    }
                return result  # type: ignore[no-any-return]

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
