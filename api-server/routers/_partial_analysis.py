"""
Partial analysis: run only specific phases instead of the full 13-phase pipeline.

Provides:
- Frontend→backend phase name mapping
- Backend dependency graph and resolver
- Context loaders for skipped prerequisite phases
- Partial analysis orchestrator thread function

F-002 fix: the frontend sends {phases, force} but the full-analysis endpoint
(multipart/form-data) silently ignored it. This module powers the new
POST /api/projects/{id}/analyze/partial JSON endpoint.
"""

import logging
import time
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic request model
# ============================================================================

class PartialAnalysisRequest(BaseModel):
    """JSON body for POST /api/projects/{id}/analyze/partial."""
    phases: list[str] = Field(..., min_length=1, description="Frontend phase names")
    force: bool = Field(False, description="Re-run even if phase already completed")


# ============================================================================
# Phase mapping: frontend (15 phases) → backend (13 phases)
# ============================================================================

FRONTEND_TO_BACKEND: dict[str, list[str]] = {
    # Tier 1 is atomic — requesting any Tier 1 phase triggers all three
    "parsing":        ["parsing", "classification", "structure"],
    "structure":      ["parsing", "classification", "structure"],
    # Tier 2: heavy NLP phases
    "entities":       ["ner"],
    "coreference":    ["fusion"],
    "attributes":     ["attributes"],
    "coherence":      ["consistency"],
    "grammar":        ["grammar"],
    "spelling":       ["grammar"],          # same backend phase
    # Tier 3: enrichment (CPU-only, read from DB)
    "relationships":  ["relationships"],
    "voice_profiles": ["voice"],
    "register":       ["prose"],
    "pacing":         ["prose"],            # same backend phase
    "temporal":       ["consistency"],      # sub-phase of consistency
    "emotional":      ["health"],           # sub-phase of health
    "sentiment":      ["health"],           # sub-phase of health
    # No direct backend equivalent
    "focalization":   [],
    "interactions":   [],
}

# Canonical execution order for all backend phases
BACKEND_PHASE_ORDER = [
    "parsing", "classification", "structure",
    "ner", "fusion", "attributes",
    "consistency", "grammar", "alerts",
    "relationships", "voice", "prose", "health",
]

# Backend phase dependencies (what must complete before this phase can run)
BACKEND_PHASE_DEPS: dict[str, list[str]] = {
    "parsing":        [],
    "classification": ["parsing"],
    "structure":      ["parsing"],
    "ner":            ["parsing", "classification", "structure"],
    "fusion":         ["ner"],
    "attributes":     ["fusion"],
    "consistency":    ["attributes"],
    "grammar":        ["parsing", "structure"],
    "alerts":         ["consistency", "grammar"],
    "relationships":  ["fusion"],
    "voice":          ["fusion"],
    "prose":          ["structure"],
    "health":         ["fusion", "structure"],
}

TIER1_PHASES = {"parsing", "classification", "structure"}
TIER2_PHASES = {"ner", "fusion", "attributes", "consistency", "grammar", "alerts"}
TIER3_PHASES = {"relationships", "voice", "prose", "health"}

# Phase display names (Spanish)
PHASE_NAMES: dict[str, str] = {
    "parsing": "Lectura del documento",
    "classification": "Clasificando tipo de documento",
    "structure": "Identificando capítulos",
    "ner": "Buscando personajes y lugares",
    "fusion": "Unificando entidades",
    "attributes": "Analizando características",
    "consistency": "Verificando coherencia",
    "grammar": "Revisando gramática y ortografía",
    "alerts": "Preparando observaciones",
    "relationships": "Analizando relaciones",
    "voice": "Perfilando voces",
    "prose": "Evaluando escritura",
    "health": "Salud narrativa",
}

# Phase weights for progress estimation
PHASE_WEIGHTS: dict[str, float] = {
    "parsing": 0.01,
    "classification": 0.01,
    "structure": 0.01,
    "ner": 0.31,
    "fusion": 0.15,
    "attributes": 0.08,
    "consistency": 0.03,
    "grammar": 0.06,
    "alerts": 0.04,
    "relationships": 0.08,
    "voice": 0.08,
    "prose": 0.08,
    "health": 0.06,
}


# ============================================================================
# Phase completion detection (infer from DB)
# ============================================================================

def get_completed_phases(db_session: Any, project_id: int) -> set[str]:
    """Infer which backend phases have already been completed from DB state."""
    completed: set[str] = set()
    try:
        with db_session.connection() as conn:
            chapter_count = conn.execute(
                "SELECT COUNT(*) FROM chapters WHERE project_id = ?",
                (project_id,),
            ).fetchone()[0]

            entity_count = conn.execute(
                "SELECT COUNT(*) FROM entities WHERE project_id = ?",
                (project_id,),
            ).fetchone()[0]

            alert_count = conn.execute(
                "SELECT COUNT(*) FROM alerts WHERE project_id = ?",
                (project_id,),
            ).fetchone()[0]

            attr_count = conn.execute(
                "SELECT COUNT(*) FROM entity_attributes WHERE entity_id IN "
                "(SELECT id FROM entities WHERE project_id = ?)",
                (project_id,),
            ).fetchone()[0]

            # Check enrichment cache
            def _has_enrichment(etype: str) -> bool:
                row = conn.execute(
                    "SELECT COUNT(*) FROM enrichment_cache "
                    "WHERE project_id = ? AND enrichment_type = ? AND status = 'completed'",
                    (project_id, etype),
                ).fetchone()
                return row and row[0] > 0

        # Tier 1
        if chapter_count > 0:
            completed |= {"parsing", "classification", "structure"}

        # Tier 2
        if entity_count > 0:
            completed |= {"ner", "fusion"}
        if attr_count > 0:
            completed.add("attributes")
        if alert_count > 0:
            completed |= {"consistency", "grammar", "alerts"}

        # Tier 3 (enrichment cache)
        if _has_enrichment("character_network"):
            completed.add("relationships")
        if _has_enrichment("voice_profiles"):
            completed.add("voice")
        if _has_enrichment("sticky_sentences"):
            completed.add("prose")
        if _has_enrichment("narrative_health"):
            completed.add("health")

    except Exception as e:
        logger.warning(f"Error checking completed phases: {e}")

    return completed


# ============================================================================
# Phase resolution: frontend names → ordered backend phases to execute
# ============================================================================

def resolve_backend_phases(
    requested_frontend: list[str],
    completed_phases: set[str],
    force: bool,
) -> list[str]:
    """
    Resolve frontend phase names to an ordered list of backend phases to execute.

    1. Map frontend names → backend names
    2. Remove already-completed phases (unless force=True)
    3. Expand with missing dependencies
    4. Return in canonical execution order
    """
    # Step 1: map frontend → backend
    needed: set[str] = set()
    for fe_phase in requested_frontend:
        for be_phase in FRONTEND_TO_BACKEND.get(fe_phase, []):
            needed.add(be_phase)

    if not needed:
        return []

    # Step 2: remove already completed (unless force)
    if not force:
        needed -= completed_phases

    if not needed:
        return []

    # Step 3: expand dependencies recursively
    expanded: set[str] = set()

    def _expand(phase: str):
        if phase in expanded:
            return
        expanded.add(phase)
        for dep in BACKEND_PHASE_DEPS.get(phase, []):
            if dep not in completed_phases or force:
                _expand(dep)

    for p in list(needed):
        _expand(p)

    # Step 4: return in canonical order
    return [p for p in BACKEND_PHASE_ORDER if p in expanded]


# ============================================================================
# Context loaders: populate ctx from DB for skipped prerequisite phases
# ============================================================================

def load_tier1_context(ctx: dict) -> None:
    """Load Tier 1 outputs (parsing + structure) from DB into ctx."""
    from narrative_assistant.persistence.chapter import get_chapter_repository

    db = ctx["db_session"]
    project_id = ctx["project_id"]

    chapter_repo = get_chapter_repository(db)
    chapters_with_ids = chapter_repo.get_by_project(project_id)

    if not chapters_with_ids:
        raise RuntimeError(
            "No chapters found in DB — Tier 1 (parsing) must run first."
        )

    full_text = "\n\n".join(ch.content for ch in chapters_with_ids if ch.content)
    word_count = sum(len((ch.content or "").split()) for ch in chapters_with_ids)

    chapters_data = []
    for ch in chapters_with_ids:
        chapters_data.append({
            "chapter_number": ch.chapter_number,
            "title": ch.title or f"Capítulo {ch.chapter_number}",
            "content": ch.content or "",
            "start_char": ch.start_char,
            "end_char": ch.end_char,
            "word_count": len((ch.content or "").split()),
            "structure_type": getattr(ch, "structure_type", "flat"),
            "sections": [],
        })

    def find_chapter_id_for_position(start_char: int) -> int | None:
        for ch in chapters_with_ids:
            if ch.start_char <= start_char < ch.end_char:
                return ch.id
        if chapters_with_ids:
            closest = min(
                chapters_with_ids, key=lambda c: abs(c.start_char - start_char)
            )
            return closest.id
        return None

    ctx.setdefault("full_text", full_text)
    ctx.setdefault("word_count", word_count)
    ctx.setdefault("chapters_data", chapters_data)
    ctx.setdefault("chapters_count", len(chapters_data))
    ctx.setdefault("chapters_with_ids", chapters_with_ids)
    ctx.setdefault("find_chapter_id_for_position", find_chapter_id_for_position)
    ctx.setdefault("document_type", "unknown")
    ctx.setdefault("classification", None)

    logger.info(
        f"Loaded Tier 1 context from DB: {len(chapters_data)} chapters, "
        f"{word_count} words"
    )


def load_entity_context(ctx: dict) -> None:
    """Load entity data from DB into ctx (NER + fusion already done)."""
    from narrative_assistant.entities.repository import get_entity_repository

    db = ctx["db_session"]
    project_id = ctx["project_id"]

    entity_repo = get_entity_repository(db)
    entities = entity_repo.get_entities_by_project(project_id)

    ctx.setdefault("entities", entities)
    ctx.setdefault("entity_repo", entity_repo)
    ctx.setdefault("coref_result", None)

    logger.info(f"Loaded entity context from DB: {len(entities)} entities")


def load_attribute_context(ctx: dict) -> None:
    """Load attribute data from DB into ctx (attributes phase already done)."""
    from narrative_assistant.nlp.attributes import ExtractedAttribute

    db = ctx["db_session"]
    project_id = ctx["project_id"]

    attributes = []
    try:
        with db.connection() as conn:
            rows = conn.execute(
                """SELECT ea.attribute_key, ea.attribute_value, ea.attribute_type,
                          ea.confidence, ea.is_verified, e.canonical_name, e.id as entity_id
                   FROM entity_attributes ea
                   JOIN entities e ON ea.entity_id = e.id
                   WHERE e.project_id = ?""",
                (project_id,),
            ).fetchall()

            for r in rows:
                attributes.append(ExtractedAttribute(  # type: ignore[call-arg]
                    entity_name=r["canonical_name"],
                    attribute=r["attribute_key"],
                    value=r["attribute_value"],
                    confidence=r["confidence"] or 0.5,
                    source="database",
                    chapter_number=0,
                    evidence="",
                ))
    except Exception as e:
        logger.warning(f"Error loading attributes from DB: {e}")

    ctx.setdefault("attributes", attributes)
    logger.info(f"Loaded attribute context from DB: {len(attributes)} attributes")


# What ctx keys each phase needs before it can run
_PHASE_CTX_NEEDS: dict[str, list[str]] = {
    "parsing":        [],
    "classification": ["full_text"],
    "structure":      ["full_text"],
    "ner":            ["full_text", "find_chapter_id_for_position"],
    "fusion":         ["full_text", "chapters_data", "entities", "find_chapter_id_for_position"],
    "attributes":     ["full_text", "chapters_data", "entities"],
    "consistency":    ["full_text", "chapters_data", "entities", "attributes"],
    "grammar":        ["full_text"],
    "alerts":         [],  # uses ctx.get() with defaults
    "relationships":  [],  # loads from DB internally
    "voice":          [],  # loads from DB internally
    "prose":          [],  # loads from DB internally
    "health":         [],  # loads from DB internally
}

# Which loader provides which ctx keys
_CTX_LOADERS: dict[str, callable] = {  # type: ignore[valid-type]
    "full_text":                    load_tier1_context,
    "chapters_data":                load_tier1_context,
    "chapters_count":               load_tier1_context,
    "chapters_with_ids":            load_tier1_context,
    "find_chapter_id_for_position": load_tier1_context,
    "word_count":                   load_tier1_context,
    "entities":                     load_entity_context,
    "entity_repo":                  load_entity_context,
    "coref_result":                 load_entity_context,
    "attributes":                   load_attribute_context,
}


def ensure_context(ctx: dict, phase: str) -> None:
    """Load any missing ctx keys required by the given phase."""
    needed = _PHASE_CTX_NEEDS.get(phase, [])
    loaders_called: set[int] = set()
    for key in needed:
        if key not in ctx:
            loader = _CTX_LOADERS.get(key)
            if loader and id(loader) not in loaders_called:
                loader(ctx)
                loaders_called.add(id(loader))
            if key not in ctx:
                raise RuntimeError(
                    f"Context key '{key}' could not be loaded for phase '{phase}'"
                )


# ============================================================================
# Phase-specific cleanup (for force=True re-runs)
# ============================================================================

def cleanup_phase_data(db_session: Any, project_id: int, phase: str) -> None:
    """Delete only the data produced by a specific phase (targeted cleanup)."""
    try:
        with db_session.connection() as conn:
            if phase in ("parsing", "classification", "structure"):
                conn.execute(
                    "DELETE FROM chapters WHERE project_id = ?", (project_id,)
                )
            elif phase == "ner":
                conn.execute(
                    "DELETE FROM entity_mentions WHERE entity_id IN "
                    "(SELECT id FROM entities WHERE project_id = ?)",
                    (project_id,),
                )
                conn.execute(
                    "DELETE FROM attribute_evidences WHERE attribute_id IN "
                    "(SELECT id FROM entity_attributes WHERE entity_id IN "
                    "(SELECT id FROM entities WHERE project_id = ?))",
                    (project_id,),
                )
                conn.execute(
                    "DELETE FROM entity_attributes WHERE entity_id IN "
                    "(SELECT id FROM entities WHERE project_id = ?)",
                    (project_id,),
                )
                conn.execute(
                    "DELETE FROM entities WHERE project_id = ?", (project_id,)
                )
            elif phase == "attributes":
                conn.execute(
                    "DELETE FROM attribute_evidences WHERE attribute_id IN "
                    "(SELECT id FROM entity_attributes WHERE entity_id IN "
                    "(SELECT id FROM entities WHERE project_id = ?))",
                    (project_id,),
                )
                conn.execute(
                    "DELETE FROM entity_attributes WHERE entity_id IN "
                    "(SELECT id FROM entities WHERE project_id = ?)",
                    (project_id,),
                )
            elif phase == "consistency":
                # Consistency sub-products
                conn.execute(
                    "DELETE FROM vital_status_events WHERE project_id = ?",
                    (project_id,),
                )
                conn.execute(
                    "DELETE FROM character_location_events WHERE project_id = ?",
                    (project_id,),
                )
                conn.execute(
                    "DELETE FROM ooc_events WHERE project_id = ?",
                    (project_id,),
                )
            elif phase == "grammar":
                conn.execute(
                    "DELETE FROM alerts WHERE project_id = ? AND category IN "
                    "('grammar', 'spelling', 'correction')",
                    (project_id,),
                )
            elif phase == "alerts":
                conn.execute(
                    "DELETE FROM alerts WHERE project_id = ?", (project_id,)
                )
            elif phase in ("relationships", "voice", "prose", "health"):
                # Enrichment cache entries
                phase_num = {
                    "relationships": 10, "voice": 11, "prose": 12, "health": 13,
                }.get(phase, 0)
                conn.execute(
                    "DELETE FROM enrichment_cache WHERE project_id = ? AND phase = ?",
                    (project_id, phase_num),
                )
        logger.debug(f"Cleaned up data for phase '{phase}' (project {project_id})")
    except Exception as e:
        logger.warning(f"Error cleaning up phase '{phase}': {e}")


# ============================================================================
# Progress helpers
# ============================================================================

def build_partial_progress(
    phases_to_run: list[str],
) -> tuple[list[dict], dict[str, float], list[str]]:
    """Build progress phases, weights, and order for partial analysis.

    Returns:
        (phases_list, normalized_weights, phase_order)
    """
    phases_list = [
        {"id": p, "name": PHASE_NAMES.get(p, p), "completed": False, "current": False}
        for p in phases_to_run
    ]
    raw_weights = {p: PHASE_WEIGHTS.get(p, 0.05) for p in phases_to_run}
    total = sum(raw_weights.values()) or 1.0
    normalized = {k: v / total for k, v in raw_weights.items()}
    return phases_list, normalized, list(phases_to_run)


# ============================================================================
# Partial analysis orchestrator
# ============================================================================

def run_partial_analysis_thread(
    ctx: dict,
    phases_to_run: list[str],
    force: bool,
) -> None:
    """
    Orchestrator for partial analysis — runs in a background thread.

    Similar to run_real_analysis in analysis.py but only executes
    the requested phases and loads context from DB for skipped prerequisites.
    """
    from routers import deps
    from routers._analysis_phases import (
        ProgressTracker,
        apply_license_and_settings,
        claim_heavy_slot_or_queue,
        handle_analysis_error,
        release_heavy_slot,
        run_alerts,
        run_attributes,
        run_classification,
        run_consistency,
        run_finally_cleanup,
        run_fusion,
        run_grammar,
        run_llm_entity_validation,
        run_ner,
        run_ollama_healthcheck,
        run_parsing,
        run_reconciliation,
        run_structure,
    )
    from routers._enrichment_phases import (
        capture_entity_fingerprint,
        invalidate_enrichment_if_mutated,
        run_health_enrichment,
        run_prose_enrichment,
        run_relationships_enrichment,
        run_voice_enrichment,
        write_version_metrics,
    )

    project_id = ctx["project_id"]
    phases_set = set(phases_to_run)
    has_tier1 = bool(phases_set & TIER1_PHASES)
    has_tier2 = bool(phases_set & TIER2_PHASES)
    has_tier3 = bool(phases_set & TIER3_PHASES)

    # Build progress tracker for partial phases only
    progress_phases, partial_weights, partial_order = build_partial_progress(
        phases_to_run
    )
    db_session = deps.get_database()
    ctx["db_session"] = db_session

    tracker = ProgressTracker(
        project_id=project_id,
        phases=progress_phases,
        phase_weights=partial_weights,
        phase_order=partial_order,
        db_session=db_session,
    )

    try:
        # License & settings (always needed for analysis_config)
        apply_license_and_settings(ctx, tracker)

        # --- Phase-specific cleanup if force=True ---
        if force:
            for p in phases_to_run:
                cleanup_phase_data(db_session, project_id, p)

        # --- Tier 1 ---
        if has_tier1:
            run_parsing(ctx, tracker)
            run_classification(ctx, tracker)
            run_structure(ctx, tracker)
        else:
            # Load Tier 1 context from DB for downstream phases
            load_tier1_context(ctx)

        # --- Tier 2 ---
        if has_tier2:
            got_slot = claim_heavy_slot_or_queue(ctx, tracker)
            if not got_slot:
                ctx["queued_for_heavy"] = True
                from narrative_assistant.persistence.project import ProjectManager
                project = ctx["project"]
                project.analysis_status = "queued"
                proj_manager = ProjectManager(db_session)
                proj_manager.update(project)
                logger.info(
                    f"Partial analysis project {project_id}: "
                    f"queued for heavy slot"
                )
                return  # Will be resumed when slot frees

            run_ollama_healthcheck(ctx, tracker)

            # Run only requested Tier 2 phases in order
            if "ner" in phases_set:
                ensure_context(ctx, "ner")
                run_ner(ctx, tracker)
                # LLM validation always follows NER
                run_llm_entity_validation(ctx, tracker)
            if "fusion" in phases_set:
                ensure_context(ctx, "fusion")
                run_fusion(ctx, tracker)
            if "attributes" in phases_set:
                ensure_context(ctx, "attributes")
                run_attributes(ctx, tracker)
            if "consistency" in phases_set:
                ensure_context(ctx, "consistency")
                run_consistency(ctx, tracker)
            if "grammar" in phases_set:
                ensure_context(ctx, "grammar")
                run_grammar(ctx, tracker)
            if "alerts" in phases_set:
                ensure_context(ctx, "alerts")
                run_alerts(ctx, tracker)

            release_heavy_slot(ctx)

        # --- Tier 3 ---
        if has_tier3:
            entity_fp = capture_entity_fingerprint(db_session, project_id)

            if "relationships" in phases_set:
                run_relationships_enrichment(ctx, tracker)
            if "voice" in phases_set:
                run_voice_enrichment(ctx, tracker)
            if "prose" in phases_set:
                run_prose_enrichment(ctx, tracker)
            if "health" in phases_set:
                run_health_enrichment(ctx, tracker)

            invalidate_enrichment_if_mutated(db_session, project_id, entity_fp)

        # S15: Write version metrics after enrichment
        write_version_metrics(ctx)

        # --- Completion ---
        run_reconciliation(ctx, tracker)

        # Mark as completed
        with deps._progress_lock:
            storage = deps.analysis_progress_storage.get(project_id)
            if storage:
                storage["status"] = "completed"
                storage["progress"] = 100
                storage["current_phase"] = "Análisis parcial completado"
                storage["current_action"] = ""
                storage["estimated_seconds_remaining"] = 0

        # Update project status
        from narrative_assistant.persistence.project import ProjectManager
        project = ctx["project"]
        project.analysis_status = "completed"
        total_duration = round(time.time() - ctx["start_time"], 1)
        ProjectManager(db_session).update(project)
        logger.info(
            f"Partial analysis completed for project {project_id} "
            f"({len(phases_to_run)} phases in {total_duration}s)"
        )

    except Exception as e:
        handle_analysis_error(ctx, e)

    finally:
        run_finally_cleanup(ctx)
