"""
Enrichment phases 10-13: pre-compute and cache analysis results.

These phases run after the main analysis (phases 1-9) and persist results
in the enrichment_cache table for instant retrieval from GET endpoints.

Phase 10: Relationships (network, timeline, profiles, locations, emotional, archetypes)
Phase 11: Voice (profiles, deviations, register, focalization)
Phase 12: Prose (sticky, energy, echo, pacing, tension, sensory, readability, variation, dialogue, structure)
Phase 13: Health (chapter progress, narrative templates, narrative health)

S8a-07..10: Pipeline enrichment implementation.
"""

import hashlib
import json
import logging
import re
import time
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# Cache helper
# ============================================================================


def _cache_result(
    db_session: Any,
    project_id: int,
    enrichment_type: str,
    result: Any,
    phase: int,
    entity_scope: str | None = None,
) -> bool:
    """Store an enrichment result in the cache table.

    Returns True if result was written, False if early cutoff (output unchanged).
    """
    try:
        result_json = json.dumps(result, ensure_ascii=False, default=str, sort_keys=True)
        output_hash = hashlib.sha256(result_json.encode()).hexdigest()[:16]

        with db_session.connection() as conn:
            # Early cutoff: si el output_hash no cambió, solo marcar completed
            scope_filter = "entity_scope IS NULL" if entity_scope is None else "entity_scope = ?"
            params = [project_id, enrichment_type]
            if entity_scope is not None:
                params.append(entity_scope)

            existing = conn.execute(
                f"""SELECT output_hash, status FROM enrichment_cache
                    WHERE project_id = ? AND enrichment_type = ? AND {scope_filter}
                    LIMIT 1""",
                params,
            ).fetchone()

            if existing and existing[0] == output_hash and existing[1] in ("completed", "stale"):
                # Output no cambió — solo actualizar status y timestamp
                update_params = [project_id, enrichment_type]
                if entity_scope is not None:
                    update_params.append(entity_scope)
                conn.execute(
                    f"""UPDATE enrichment_cache
                        SET status = 'completed', updated_at = datetime('now')
                        WHERE project_id = ? AND enrichment_type = ? AND {scope_filter}""",
                    update_params,
                )
                conn.commit()
                logger.debug(f"Early cutoff: {enrichment_type} unchanged for project {project_id}")
                return False

            conn.execute(
                """INSERT OR REPLACE INTO enrichment_cache
                   (project_id, enrichment_type, entity_scope, status,
                    output_hash, result_json, phase, revision,
                    computed_at, updated_at)
                   VALUES (?, ?, ?, 'completed', ?, ?, ?, 0,
                           datetime('now'), datetime('now'))""",
                (project_id, enrichment_type, entity_scope, output_hash, result_json, phase),
            )
            conn.commit()
            return True
    except Exception as e:
        logger.warning(f"Failed to cache {enrichment_type} for project {project_id}: {e}")
        return False


def _mark_failed(
    db_session: Any,
    project_id: int,
    enrichment_type: str,
    error: str,
    phase: int,
) -> None:
    """Mark an enrichment as failed in the cache table."""
    try:
        with db_session.connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO enrichment_cache
                   (project_id, enrichment_type, entity_scope, status,
                    error_message, phase, revision,
                    updated_at)
                   VALUES (?, ?, NULL, 'failed', ?, ?, 0, datetime('now'))""",
                (project_id, enrichment_type, error, phase),
            )
            conn.commit()
    except Exception:
        pass  # Best effort


def capture_entity_fingerprint(db_session: Any, project_id: int) -> str:
    """S8a-17: Capture entity state fingerprint for mutation detection.

    Returns a hash of entity IDs + updated_at timestamps.
    If entities are mutated during enrichment, this fingerprint changes.
    """
    try:
        with db_session.connection() as conn:
            rows = conn.execute(
                """SELECT id, canonical_name, updated_at
                   FROM entities WHERE project_id = ?
                   ORDER BY id""",
                (project_id,),
            ).fetchall()
        raw = "|".join(f"{r[0]}:{r[1]}:{r[2]}" for r in rows)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
    except Exception:
        return ""


def invalidate_enrichment_if_mutated(
    db_session: Any, project_id: int, saved_fingerprint: str
) -> bool:
    """S8a-17 + S8c-11: Check if entities were mutated during enrichment.

    If the fingerprint changed, mark entity-dependent enrichments as stale
    (granular invalidation) instead of deleting everything.
    Returns True if cache was invalidated.
    """
    if not saved_fingerprint:
        return False

    current = capture_entity_fingerprint(db_session, project_id)
    if current != saved_fingerprint:
        logger.warning(
            f"[Enrichment] Entity mutation detected for project {project_id} "
            f"(before={saved_fingerprint}, after={current}). Marking stale."
        )
        try:
            from routers._invalidation import ATTRIBUTE_DEPENDENT_TYPES, ENTITY_DEPENDENT_TYPES

            affected_types = ENTITY_DEPENDENT_TYPES | ATTRIBUTE_DEPENDENT_TYPES
            placeholders = ",".join("?" for _ in affected_types)

            with db_session.connection() as conn:
                conn.execute(
                    f"""UPDATE enrichment_cache
                        SET status = 'stale', updated_at = datetime('now')
                        WHERE project_id = ?
                        AND enrichment_type IN ({placeholders})
                        AND status = 'completed'""",
                    [project_id] + list(affected_types),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to mark enrichment stale: {e}")
            # Fallback: delete all (legacy behavior)
            try:
                with db_session.connection() as conn:
                    conn.execute(
                        "DELETE FROM enrichment_cache WHERE project_id = ?",
                        (project_id,),
                    )
                    conn.commit()
            except Exception:
                pass
        return True
    return False


def _run_enrichment(
    db_session: Any,
    project_id: int,
    enrichment_type: str,
    phase: int,
    compute_fn,
    label: str,
    input_payload: Any | None = None,
    ctx: dict | None = None,
) -> bool:
    """Run a single enrichment computation with error handling.

    Marks cache as 'computing' before starting. On success, stores result
    atomically. On failure, marks as 'failed' with error message.

    Returns True if successful, False otherwise.
    """
    if input_payload is None:
        try:
            with db_session.connection() as conn:
                chapter_meta = conn.execute(
                    """
                    SELECT COUNT(*) AS c, COALESCE(MAX(updated_at), '') AS ts
                    FROM chapters WHERE project_id = ?
                    """,
                    (project_id,),
                ).fetchone()
                entity_meta = conn.execute(
                    """
                    SELECT COUNT(*) AS c, COALESCE(MAX(updated_at), '') AS ts
                    FROM entities WHERE project_id = ?
                    """,
                    (project_id,),
                ).fetchone()
                invalidation_meta = conn.execute(
                    """
                    SELECT COALESCE(MAX(revision), 0) AS rev
                    FROM invalidation_events WHERE project_id = ?
                    """,
                    (project_id,),
                ).fetchone()
            input_payload = {
                "enrichment_type": enrichment_type,
                "phase": phase,
                "chapter_count": int(chapter_meta["c"] if chapter_meta else 0),
                "chapter_ts": chapter_meta["ts"] if chapter_meta else "",
                "entity_count": int(entity_meta["c"] if entity_meta else 0),
                "entity_ts": entity_meta["ts"] if entity_meta else "",
                "invalidation_revision": int(invalidation_meta["rev"] if invalidation_meta else 0),
            }
        except Exception:
            input_payload = {"enrichment_type": enrichment_type, "phase": phase}

    input_hash = _hash_payload(input_payload)

    # Fast skip por input_hash antes de computar (Sprint C).
    if input_hash:
        try:
            with db_session.connection() as conn:
                cached = conn.execute(
                    """
                    SELECT status, input_hash
                    FROM enrichment_cache
                    WHERE project_id = ? AND enrichment_type = ? AND entity_scope IS NULL
                    LIMIT 1
                    """,
                    (project_id, enrichment_type),
                ).fetchone()
                if cached and cached[0] == "completed" and cached[1] == input_hash:
                    logger.info(
                        "[Enrichment] %s skipped (input_hash unchanged: %s)",
                        label,
                        input_hash,
                    )
                    return True
        except Exception:
            pass

    # Marcar como 'computing' antes de empezar (S8c-10)
    try:
        with db_session.connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO enrichment_cache
                   (project_id, enrichment_type, entity_scope, status, phase, input_hash, updated_at)
                   VALUES (?, ?, NULL, 'computing', ?, ?, datetime('now'))""",
                (project_id, enrichment_type, phase, input_hash),
            )
            conn.commit()
    except Exception:
        pass  # Best effort

    try:
        t0 = time.time()
        result = compute_fn()
        elapsed = time.time() - t0
        changed = _cache_result(db_session, project_id, enrichment_type, result, phase)
        if input_hash:
            try:
                with db_session.connection() as conn:
                    conn.execute(
                        """
                        UPDATE enrichment_cache
                        SET input_hash = ?, updated_at = datetime('now')
                        WHERE project_id = ? AND enrichment_type = ? AND entity_scope IS NULL
                        """,
                        (input_hash, project_id, enrichment_type),
                    )
                    conn.commit()
            except Exception:
                pass
        if ctx is not None:
            timings = ctx.setdefault("phase_durations_json", {})
            if isinstance(timings, dict):
                timings[enrichment_type] = round(elapsed, 3)
        cutoff_note = "" if changed else " (early cutoff)"
        logger.info(f"[Enrichment] {label} completed in {elapsed:.1f}s{cutoff_note}")
        return True
    except Exception as e:
        logger.warning(f"[Enrichment] {label} failed: {e}", exc_info=True)
        _mark_failed(db_session, project_id, enrichment_type, str(e)[:500], phase)
        return False


# ============================================================================
# Data loaders (shared across phases)
# ============================================================================


def _load_entities(db_session, project_id):
    """Load entities from DB."""
    from narrative_assistant.entities.repository import get_entity_repository

    repo = get_entity_repository(db_session)
    return repo.get_entities_by_project(project_id)


def _load_chapters(db_session, project_id):
    """Load chapters from DB."""
    from narrative_assistant.persistence.chapter import get_chapter_repository

    repo = get_chapter_repository(db_session)
    return repo.get_by_project(project_id)


def _build_full_text(chapters):
    """Build full text from chapters."""
    return "\n\n".join(ch.content for ch in chapters if ch.content)


def _chapters_to_dicts(chapters):
    """Convert chapter objects to dicts for analysis functions."""
    result = []
    offset = 0
    for ch in chapters:
        content = ch.content or ""
        result.append(
            {
                "number": ch.chapter_number,
                "title": ch.title or f"Capítulo {ch.chapter_number}",
                "content": content,
                "start_char": offset,
                "end_char": offset + len(content),
            }
        )
        offset += len(content) + 2  # +2 for \n\n separator
    return result


def _entities_to_dicts(entities):
    """Convert entity objects to dicts for analysis functions."""
    result = []
    for e in entities:
        etype = e.entity_type.value if hasattr(e.entity_type, "value") else str(e.entity_type)
        result.append(
            {
                "id": e.id,
                "name": e.canonical_name,
                "entity_type": etype,
                "aliases": getattr(e, "aliases", []) or [],
                "importance": getattr(e, "importance", None),
            }
        )
    return result


def _detect_all_dialogues(chapters):
    """Detect dialogues in all chapters. Returns list of (speaker_hint, text, start, end, chapter_num)."""
    from narrative_assistant.nlp.dialogue import detect_dialogues

    all_dialogues = []
    for ch in chapters:
        try:
            dialogues = detect_dialogues(ch.content or "")
            for d in dialogues:
                speaker_hint = d[0] if len(d) > 0 else None
                text = d[1] if len(d) > 1 else ""
                start = d[2] if len(d) > 2 else 0
                end = d[3] if len(d) > 3 else len(text)
                all_dialogues.append(
                    {
                        "speaker_hint": speaker_hint,
                        "text": text,
                        "start_char": start,
                        "end_char": end,
                        "chapter": ch.chapter_number,
                    }
                )
        except Exception as e:
            logger.warning(f"Dialogue detection failed for chapter {ch.chapter_number}: {e}")
    return all_dialogues


# ============================================================================
# Phase 10: Relationships enrichment
# ============================================================================


def run_relationships_enrichment(ctx: dict, tracker) -> None:
    """Phase 10: Pre-compute relationship-related analysis."""
    phase_key = "relationships"
    phase_index = 9  # 0-indexed (10th phase)

    tracker.start_phase(phase_key, phase_index, "Analizando relaciones entre personajes...")

    project_id = ctx["project_id"]
    db = ctx["db_session"]

    try:
        entities = _load_entities(db, project_id)
        chapters = _load_chapters(db, project_id)
        chapters_dicts = _chapters_to_dicts(chapters)
        # entities_dicts and full_text computed on demand by individual phases

        character_entities = [
            e
            for e in entities
            if (e.entity_type.value if hasattr(e.entity_type, "value") else str(e.entity_type))
            in ("character", "animal", "creature")
        ]

        total_steps = 6
        step = 0

        # --- 10a: Character Network ---
        step += 1
        tracker.update_progress(phase_key, step / total_steps, "Calculando red de personajes...")
        _run_enrichment(
            db,
            project_id,
            "character_network",
            10,
            lambda: _compute_character_network(db, project_id, entities, chapters),
            "character_network",
        )

        # --- 10b: Character Timeline ---
        step += 1
        tracker.update_progress(phase_key, step / total_steps, "Generando línea temporal...")
        _run_enrichment(
            db,
            project_id,
            "character_timeline",
            10,
            lambda: _compute_character_timeline(db, project_id, entities, chapters),
            "character_timeline",
        )

        # --- 10c: Character Profiles (6 indicators) ---
        step += 1
        tracker.update_progress(phase_key, step / total_steps, "Perfilando personajes...")
        _run_enrichment(
            db,
            project_id,
            "character_profiles",
            10,
            lambda: _compute_character_profiles(db, project_id, entities, chapters),
            "character_profiles",
        )

        # --- 10d: Emotional Analysis ---
        step += 1
        tracker.update_progress(phase_key, step / total_steps, "Analizando coherencia emocional...")
        _run_enrichment(
            db,
            project_id,
            "emotional_analysis",
            10,
            lambda: _compute_emotional_analysis(chapters, character_entities),
            "emotional_analysis",
        )

        # --- 10e: Character Archetypes ---
        step += 1
        tracker.update_progress(phase_key, step / total_steps, "Detectando arquetipos...")
        _run_enrichment(
            db,
            project_id,
            "character_archetypes",
            10,
            lambda: _compute_character_archetypes(
                db, project_id, entities, chapters, chapters_dicts
            ),
            "character_archetypes",
        )

        # --- 10f: Character Knowledge ---
        step += 1
        tracker.update_progress(
            phase_key, step / total_steps, "Analizando conocimiento entre personajes..."
        )
        _run_enrichment(
            db,
            project_id,
            "character_knowledge",
            10,
            lambda: _compute_character_knowledge(project_id, entities, chapters),
            "character_knowledge",
        )

    except Exception as e:
        logger.error(f"[Phase 10] Relationships enrichment failed: {e}", exc_info=True)

    tracker.complete_phase(phase_key, phase_index)


def _compute_character_network(db, project_id, entities, chapters):
    """Compute character network metrics (centrality, bridges, clustering)."""
    from narrative_assistant.analysis.character_network import CharacterNetworkAnalyzer
    from narrative_assistant.entities.repository import get_entity_repository

    entity_repo = get_entity_repository(db)
    entity_names = {}
    cooccurrences = []
    PROXIMITY_WINDOW = 500

    for entity in entities:
        etype = (
            entity.entity_type.value
            if hasattr(entity.entity_type, "value")
            else str(entity.entity_type)
        )
        if etype not in ("character", "animal", "creature"):
            continue
        entity_names[entity.id] = entity.canonical_name

    # Build co-occurrence matrix from mentions
    for ch in chapters:
        ch_mentions = []
        for eid in entity_names:
            mentions = entity_repo.get_mentions_by_entity(eid)
            for m in mentions:
                if hasattr(m, "chapter_id") and m.chapter_id and hasattr(ch, "id"):
                    if m.chapter_id == ch.id:
                        ch_mentions.append((eid, getattr(m, "start_char", 0) or 0))
                elif hasattr(m, "start_char"):
                    ch_mentions.append((eid, getattr(m, "start_char", 0) or 0))

        ch_mentions.sort(key=lambda x: x[1])
        for i, (eid1, pos1) in enumerate(ch_mentions):
            for j in range(i + 1, len(ch_mentions)):
                eid2, pos2 = ch_mentions[j]
                if pos2 - pos1 > PROXIMITY_WINDOW:
                    break
                if eid1 != eid2:
                    cooccurrences.append(
                        {
                            "entity1_id": eid1,
                            "entity2_id": eid2,
                            "chapter": ch.chapter_number,
                            "distance_chars": pos2 - pos1,
                        }
                    )

    analyzer = CharacterNetworkAnalyzer()
    report = analyzer.analyze(cooccurrences, entity_names, len(chapters))
    return report.to_dict() if hasattr(report, "to_dict") else report


def _compute_character_timeline(db, project_id, entities, chapters):
    """Build character timeline (appearances per chapter)."""
    from narrative_assistant.entities.repository import get_entity_repository

    entity_repo = get_entity_repository(db)
    # chapter_map omitted — ch_number_map sufficient for current usage
    ch_number_map = {ch.id: ch.chapter_number for ch in chapters if hasattr(ch, "id")}

    characters = []
    for entity in entities:
        etype = (
            entity.entity_type.value
            if hasattr(entity.entity_type, "value")
            else str(entity.entity_type)
        )
        if etype not in ("character", "animal", "creature"):
            continue

        mentions = entity_repo.get_mentions_by_entity(entity.id)
        ch_counts: dict[int, int] = {}
        for m in mentions:
            ch_id = getattr(m, "chapter_id", None)
            ch_num = ch_number_map.get(ch_id, 0) if ch_id else 0
            ch_counts[ch_num] = ch_counts.get(ch_num, 0) + 1

        if not ch_counts:
            continue

        appearances = [
            {"chapter": ch_num, "mentions": count} for ch_num, count in sorted(ch_counts.items())
        ]

        characters.append(
            {
                "entity_id": entity.id,
                "name": entity.canonical_name,
                "entity_type": etype,
                "importance": getattr(entity, "importance", None),
                "total_mentions": sum(ch_counts.values()),
                "chapters_present": len(ch_counts),
                "first_chapter": min(ch_counts.keys()),
                "last_chapter": max(ch_counts.keys()),
                "appearances": appearances,
            }
        )

    characters.sort(key=lambda c: c["total_mentions"], reverse=True)

    return {
        "characters": characters,
        "chapters": [{"number": ch.chapter_number, "title": ch.title} for ch in chapters],
        "total_chapters": len(chapters),
    }


def _compute_character_profiles(db, project_id, entities, chapters):
    """Compute 6-indicator character profiles."""
    from narrative_assistant.analysis.character_profiling import CharacterProfiler
    from narrative_assistant.entities.repository import get_entity_repository

    entity_repo = get_entity_repository(db)

    # Build mentions list and chapter_texts
    mentions_list = []
    for entity in entities:
        etype = (
            entity.entity_type.value
            if hasattr(entity.entity_type, "value")
            else str(entity.entity_type)
        )
        if etype not in ("character", "animal", "creature"):
            continue
        ch_number_map = {ch.id: ch.chapter_number for ch in chapters if hasattr(ch, "id")}
        ems = entity_repo.get_mentions_by_entity(entity.id)
        for m in ems:
            ch_id = getattr(m, "chapter_id", None)
            ch_num = ch_number_map.get(ch_id, 0) if ch_id else 0
            mentions_list.append(
                {
                    "entity_id": entity.id,
                    "entity_name": entity.canonical_name,
                    "chapter": ch_num,
                }
            )

    chapter_texts = {ch.chapter_number: (ch.content or "") for ch in chapters}

    profiler = CharacterProfiler()
    profiles = profiler.build_profiles(mentions_list, chapter_texts)

    return {
        "profiles": [p.to_dict() if hasattr(p, "to_dict") else p for p in profiles],
        "count": len(profiles),
    }


def _compute_emotional_analysis(chapters, character_entities):
    """Compute emotional coherence analysis."""
    from narrative_assistant.analysis.emotional_coherence import get_emotional_coherence_checker
    from narrative_assistant.nlp.dialogue import detect_dialogues

    checker = get_emotional_coherence_checker()
    character_names = [e.canonical_name for e in character_entities]

    all_incoherences = []
    chapters_analyzed = 0

    for ch in chapters:
        content = ch.content or ""
        if len(content) < 50:
            continue
        try:
            dialogues = detect_dialogues(content)
            result = checker.analyze_chapter(content, ch.chapter_number, character_names, dialogues)
            if hasattr(result, "incoherences"):
                for inc in result.incoherences:
                    d = inc.to_dict() if hasattr(inc, "to_dict") else inc
                    if isinstance(d, dict):
                        d["chapter_id"] = ch.chapter_number
                    all_incoherences.append(d)
            chapters_analyzed += 1
        except Exception as e:
            logger.warning(f"Emotional analysis failed for chapter {ch.chapter_number}: {e}")

    return {
        "incoherences": all_incoherences,
        "stats": {
            "total": len(all_incoherences),
            "chapters_analyzed": chapters_analyzed,
        },
    }


def _compute_character_archetypes(db, project_id, entities, chapters, chapters_dicts):
    """Compute character archetypes (basic mode — no LLM)."""
    from narrative_assistant.analysis.chapter_summary import analyze_chapter_progress
    from narrative_assistant.analysis.character_archetypes import CharacterArchetypeAnalyzer
    from narrative_assistant.analysis.character_profiling import CharacterProfiler
    from narrative_assistant.entities.repository import get_entity_repository
    from narrative_assistant.relationships.repository import get_relationship_repository

    # Use basic mode to avoid LLM dependency
    progress_result = analyze_chapter_progress(project_id, mode="basic")

    if hasattr(progress_result, "is_failure") and progress_result.is_failure:
        return {"characters": [], "archetype_distribution": {}}

    progress_data = progress_result.value if hasattr(progress_result, "value") else progress_result
    character_arcs = (
        progress_data.get("character_arcs", []) if isinstance(progress_data, dict) else []
    )

    # Get relationships
    rel_repo = get_relationship_repository(db)
    relationships = rel_repo.get_by_project(project_id)
    rel_dicts = [r.to_dict() if hasattr(r, "to_dict") else r for r in relationships]

    # Get profiles
    entity_repo = get_entity_repository(db)
    ch_number_map = {ch.id: ch.chapter_number for ch in chapters if hasattr(ch, "id")}
    mentions_list = []
    for entity in entities:
        etype = (
            entity.entity_type.value
            if hasattr(entity.entity_type, "value")
            else str(entity.entity_type)
        )
        if etype not in ("character", "animal", "creature"):
            continue
        ems = entity_repo.get_mentions_by_entity(entity.id)
        for m in ems:
            ch_id = getattr(m, "chapter_id", None)
            ch_num = ch_number_map.get(ch_id, 0) if ch_id else 0
            mentions_list.append(
                {
                    "entity_id": entity.id,
                    "entity_name": entity.canonical_name,
                    "chapter": ch_num,
                }
            )

    chapter_texts = {ch.chapter_number: (ch.content or "") for ch in chapters}
    profiler = CharacterProfiler()
    profiles = profiler.build_profiles(mentions_list, chapter_texts)

    entities_data = _entities_to_dicts(entities)

    analyzer = CharacterArchetypeAnalyzer()
    report = analyzer.analyze(
        entities_data=entities_data,
        character_arcs=character_arcs,
        relationships=rel_dicts,
        profiles=[p.to_dict() if hasattr(p, "to_dict") else p for p in profiles],
        total_chapters=len(chapters),
    )

    return report.to_dict() if hasattr(report, "to_dict") else report


def _compute_character_knowledge(project_id, entities, chapters):
    """Compute character knowledge (rules mode — no LLM)."""
    from narrative_assistant.analysis.character_knowledge import (
        CharacterKnowledgeAnalyzer,
        KnowledgeExtractionMode,
    )

    analyzer = CharacterKnowledgeAnalyzer()
    character_entities = [
        e
        for e in entities
        if (e.entity_type.value if hasattr(e.entity_type, "value") else str(e.entity_type))
        in ("character", "animal", "creature")
    ]

    for ch in chapters:
        try:
            analyzer.analyze_narration(
                ch.content or "",
                ch.chapter_number,
                0,  # start_char
                extraction_mode=KnowledgeExtractionMode.RULES,
            )
        except Exception as e:
            logger.warning(f"Knowledge extraction failed for chapter {ch.chapter_number}: {e}")

    all_knowledge = analyzer.get_all_knowledge()
    knowledge_dicts = [k.to_dict() if hasattr(k, "to_dict") else k for k in all_knowledge]

    return {
        "project_id": project_id,
        "knowledge_facts": knowledge_dicts,
        "total_facts": len(knowledge_dicts),
        "characters_analyzed": len(character_entities),
        "chapters_analyzed": len(chapters),
        "extraction_mode": "rules",
    }


# ============================================================================
# Phase 11: Voice enrichment
# ============================================================================


def run_voice_enrichment(ctx: dict, tracker) -> None:
    """Phase 11: Pre-compute voice-related analysis."""
    phase_key = "voice"
    phase_index = 10

    tracker.start_phase(phase_key, phase_index, "Perfilando voces de personajes...")

    project_id = ctx["project_id"]
    db = ctx["db_session"]

    try:
        entities = _load_entities(db, project_id)
        chapters = _load_chapters(db, project_id)
        dialogues = _detect_all_dialogues(chapters)

        character_entities = [
            e
            for e in entities
            if (e.entity_type.value if hasattr(e.entity_type, "value") else str(e.entity_type))
            in ("character", "animal", "creature")
        ]

        entity_data = [
            {"id": e.id, "name": e.canonical_name, "aliases": getattr(e, "aliases", []) or []}
            for e in character_entities
        ]

        total_steps = 4
        step = 0

        # --- 11a: Voice Profiles ---
        step += 1
        tracker.update_progress(phase_key, step / total_steps, "Construyendo perfiles de voz...")
        profiles_result = None

        def compute_voice_profiles():
            nonlocal profiles_result
            from narrative_assistant.voice.profiles import VoiceProfileBuilder

            builder = VoiceProfileBuilder()
            profiles = builder.build_profiles(dialogues, entity_data)
            profiles_result = profiles
            return [p.to_dict() if hasattr(p, "to_dict") else p for p in profiles]

        _run_enrichment(
            db, project_id, "voice_profiles", 11, compute_voice_profiles, "voice_profiles"
        )

        # --- 11b: Voice Deviations ---
        step += 1
        tracker.update_progress(phase_key, step / total_steps, "Detectando desviaciones de voz...")
        if profiles_result:
            _run_enrichment(
                db,
                project_id,
                "voice_deviations",
                11,
                lambda: _compute_voice_deviations(profiles_result, dialogues),
                "voice_deviations",
            )

        # --- 11c: Register Analysis ---
        step += 1
        tracker.update_progress(phase_key, step / total_steps, "Analizando registro lingüístico...")
        _run_enrichment(
            db,
            project_id,
            "register_analysis",
            11,
            lambda: _compute_register_analysis(chapters, dialogues),
            "register_analysis",
        )

        # --- 11d: Focalization Violations ---
        step += 1
        tracker.update_progress(phase_key, step / total_steps, "Verificando focalización...")
        _run_enrichment(
            db,
            project_id,
            "focalization_violations",
            11,
            lambda: _compute_focalization_violations(db, project_id, chapters, character_entities),
            "focalization_violations",
        )

    except Exception as e:
        logger.error(f"[Phase 11] Voice enrichment failed: {e}", exc_info=True)

    tracker.complete_phase(phase_key, phase_index)


def _compute_voice_deviations(profiles, dialogues):
    """Compute voice deviations from baseline profiles."""
    from narrative_assistant.voice.deviations import VoiceDeviationDetector

    detector = VoiceDeviationDetector()
    deviations = detector.detect_deviations(profiles, dialogues)
    return [d.to_dict() if hasattr(d, "to_dict") else d for d in deviations]


def _compute_register_analysis(chapters, dialogues):
    """Compute register/formality analysis."""
    from narrative_assistant.voice.register import RegisterChangeDetector

    # Build segments from chapters
    segments = []
    dialogue_positions = set()
    for d in dialogues:
        dialogue_positions.add((d["chapter"], d["start_char"]))

    for ch in chapters:
        content = ch.content or ""
        # Split into paragraphs as segments
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        offset = 0
        for para in paragraphs:
            pos = content.find(para, offset)
            if pos == -1:
                pos = offset
            is_dialogue = para.startswith(("—", "–", "-", "«", '"'))
            segments.append((para, ch.chapter_number, pos, is_dialogue))
            offset = pos + len(para)

    detector = RegisterChangeDetector()
    detector.analyze_document(segments)
    changes = detector.detect_changes(min_severity="medium")
    summary = detector.get_summary()

    return {
        "changes": [c.to_dict() if hasattr(c, "to_dict") else c for c in changes],
        "summary": summary
        if isinstance(summary, dict)
        else (summary.to_dict() if hasattr(summary, "to_dict") else {}),
        "total_segments": len(segments),
    }


def _compute_focalization_violations(db, project_id, chapters, character_entities):
    """Compute focalization violations."""
    from narrative_assistant.focalization import (
        FocalizationDeclarationService,
        FocalizationViolationDetector,
        SQLiteFocalizationRepository,
    )

    repo = SQLiteFocalizationRepository(db)
    service = FocalizationDeclarationService(repo)
    characters = [e.canonical_name for e in character_entities]
    detector = FocalizationViolationDetector(service, characters)

    all_violations = []
    for ch in chapters:
        try:
            violations = detector.detect_violations(project_id, ch.content or "", ch.chapter_number)
            for v in violations:
                all_violations.append(v.to_dict() if hasattr(v, "to_dict") else v)
        except Exception as e:
            logger.warning(f"Focalization check failed for chapter {ch.chapter_number}: {e}")

    return {
        "violations": all_violations,
        "total": len(all_violations),
        "chapters_analyzed": len(chapters),
    }


# ============================================================================
# Phase 12: Prose enrichment
# ============================================================================


def run_prose_enrichment(ctx: dict, tracker) -> None:
    """Phase 12: Pre-compute prose/style analysis."""
    phase_key = "prose"
    phase_index = 11

    tracker.start_phase(phase_key, phase_index, "Evaluando estilo de escritura...")

    project_id = ctx["project_id"]
    db = ctx["db_session"]

    try:
        chapters = _load_chapters(db, project_id)
        chapters_dicts = _chapters_to_dicts(chapters)
        full_text = _build_full_text(chapters)

        total_steps = 10
        step = 0

        # --- 12a: Sticky Sentences ---
        step += 1
        tracker.update_progress(phase_key, step / total_steps, "Detectando frases pegajosas...")
        _run_enrichment(
            db,
            project_id,
            "sticky_sentences",
            12,
            lambda: _compute_sticky_sentences(chapters),
            "sticky_sentences",
        )

        # --- 12b: Sentence Energy ---
        step += 1
        tracker.update_progress(phase_key, step / total_steps, "Midiendo energía narrativa...")
        _run_enrichment(
            db,
            project_id,
            "sentence_energy",
            12,
            lambda: _compute_sentence_energy(chapters),
            "sentence_energy",
        )

        # --- 12c: Echo Report (lexical only — skip semantic to avoid embeddings) ---
        step += 1
        tracker.update_progress(phase_key, step / total_steps, "Buscando repeticiones...")
        _run_enrichment(
            db, project_id, "echo_report", 12, lambda: _compute_echo_report(chapters), "echo_report"
        )

        # --- 12d: Pacing Analysis ---
        step += 1
        tracker.update_progress(phase_key, step / total_steps, "Analizando ritmo narrativo...")
        _run_enrichment(
            db,
            project_id,
            "pacing_analysis",
            12,
            lambda: _compute_pacing_analysis(chapters_dicts),
            "pacing_analysis",
        )

        # --- 12e: Tension Curve ---
        step += 1
        tracker.update_progress(phase_key, step / total_steps, "Trazando curva de tensión...")
        _run_enrichment(
            db,
            project_id,
            "tension_curve",
            12,
            lambda: _compute_tension_curve(chapters_dicts, full_text),
            "tension_curve",
        )

        # --- 12f: Sensory Report ---
        step += 1
        tracker.update_progress(phase_key, step / total_steps, "Evaluando detalles sensoriales...")
        _run_enrichment(
            db,
            project_id,
            "sensory_report",
            12,
            lambda: _compute_sensory_report(full_text, chapters_dicts),
            "sensory_report",
        )

        # --- 12g: Age Readability ---
        step += 1
        tracker.update_progress(phase_key, step / total_steps, "Calculando legibilidad...")
        _run_enrichment(
            db,
            project_id,
            "age_readability",
            12,
            lambda: _compute_readability(full_text),
            "age_readability",
        )

        # --- 12h: Sentence Variation ---
        step += 1
        tracker.update_progress(phase_key, step / total_steps, "Analizando variación sintáctica...")
        _run_enrichment(
            db,
            project_id,
            "sentence_variation",
            12,
            lambda: _compute_sentence_variation(chapters),
            "sentence_variation",
        )

        # --- 12i: Dialogue Validation ---
        step += 1
        tracker.update_progress(phase_key, step / total_steps, "Validando diálogos...")
        _run_enrichment(
            db,
            project_id,
            "dialogue_validation",
            12,
            lambda: _compute_dialogue_validation(chapters),
            "dialogue_validation",
        )

        # --- 12j: Narrative Structure ---
        step += 1
        tracker.update_progress(phase_key, step / total_steps, "Detectando estructura narrativa...")
        _run_enrichment(
            db,
            project_id,
            "narrative_structure",
            12,
            lambda: _compute_narrative_structure(full_text, chapters_dicts),
            "narrative_structure",
        )

    except Exception as e:
        logger.error(f"[Phase 12] Prose enrichment failed: {e}", exc_info=True)

    tracker.complete_phase(phase_key, phase_index)


def _compute_sticky_sentences(chapters):
    """Compute sticky (high glue word %) sentences."""
    from narrative_assistant.nlp.style.sticky_sentences import get_sticky_sentence_detector

    detector = get_sticky_sentence_detector()
    all_sticky = []
    stats = {"total_sentences": 0, "total_sticky": 0}
    for ch in chapters:
        report = detector.analyze(ch.content or "", threshold=0.45)
        if hasattr(report, "sticky_sentences"):
            for s in report.sticky_sentences:
                d = s.to_dict() if hasattr(s, "to_dict") else s
                if isinstance(d, dict):
                    d["chapter"] = ch.chapter_number
                all_sticky.append(d)
        stats["total_sentences"] += getattr(report, "total_sentences", 0)
        stats["total_sticky"] += len(getattr(report, "sticky_sentences", []))
    return {"sticky_sentences": all_sticky, "stats": stats}


def _compute_sentence_energy(chapters):
    """Compute sentence energy (passive voice, weak verbs)."""
    from narrative_assistant.nlp.style.sentence_energy import get_sentence_energy_detector

    detector = get_sentence_energy_detector()
    all_low = []
    stats = {"avg_energy": 0, "chapters": 0}
    energy_sum = 0
    for ch in chapters:
        report = detector.analyze(ch.content or "", chapter=ch.chapter_number)
        if hasattr(report, "low_energy_sentences"):
            for s in report.low_energy_sentences:
                d = s.to_dict() if hasattr(s, "to_dict") else s
                if isinstance(d, dict):
                    d["chapter"] = ch.chapter_number
                all_low.append(d)
        energy_sum += getattr(report, "avg_energy", 0.5)
        stats["chapters"] += 1
    stats["avg_energy"] = energy_sum / max(stats["chapters"], 1)
    return {"low_energy_sentences": all_low, "stats": stats}


def _compute_echo_report(chapters):
    """Compute lexical repetitions (no semantic to avoid embedding cost)."""
    from narrative_assistant.nlp.style.repetition_detector import get_repetition_detector

    detector = get_repetition_detector()
    all_repetitions = []
    for ch in chapters:
        report = detector.detect_lexical(ch.content or "", min_distance=3)
        if hasattr(report, "repetitions"):
            for r in report.repetitions:
                d = r.to_dict() if hasattr(r, "to_dict") else r
                if isinstance(d, dict):
                    d["chapter"] = ch.chapter_number
                all_repetitions.append(d)
    return {"repetitions": all_repetitions, "total": len(all_repetitions)}


def _compute_pacing_analysis(chapters_dicts):
    """Compute pacing metrics per chapter."""
    from narrative_assistant.analysis.pacing import get_pacing_analyzer

    analyzer = get_pacing_analyzer()
    result = analyzer.analyze(chapters_dicts)
    if hasattr(result, "to_dict"):
        return result.to_dict()
    if hasattr(result, "chapter_metrics"):
        return {
            "chapter_metrics": [
                m.to_dict() if hasattr(m, "to_dict") else m for m in result.chapter_metrics
            ],
        }
    return result


def _compute_tension_curve(chapters_dicts, full_text):
    """Compute tension curve across chapters."""
    from narrative_assistant.analysis.pacing import compute_tension_curve

    result = compute_tension_curve(chapters_dicts, full_text)
    return result.to_dict() if hasattr(result, "to_dict") else result


def _compute_sensory_report(full_text, chapters_dicts):
    """Compute sensory details analysis (5 senses)."""
    from narrative_assistant.nlp.style.sensory_report import get_sensory_analyzer

    analyzer = get_sensory_analyzer()
    report = analyzer.analyze(full_text, chapters=chapters_dicts)
    return report.to_dict() if hasattr(report, "to_dict") else report


def _compute_readability(full_text):
    """Compute age-readability analysis."""
    from narrative_assistant.nlp.style.readability import get_readability_analyzer

    analyzer = get_readability_analyzer()
    report = analyzer.analyze_for_age(full_text)
    return report.to_dict() if hasattr(report, "to_dict") else report


def _compute_sentence_variation(chapters):
    """Compute sentence length variation stats."""
    SENTENCE_RE = re.compile(r"[^.!?…]+[.!?…]+")
    chapter_results = []
    all_lengths = []

    for ch in chapters:
        sentences = SENTENCE_RE.findall(ch.content or "")
        lengths = [len(s.split()) for s in sentences if len(s.split()) > 2]
        if not lengths:
            continue
        avg = sum(lengths) / len(lengths)
        variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
        std = variance**0.5
        cv = std / avg if avg > 0 else 0
        chapter_results.append(
            {
                "chapter": ch.chapter_number,
                "avg_length": round(avg, 1),
                "std_dev": round(std, 1),
                "variation_coefficient": round(cv, 3),
                "min_length": min(lengths),
                "max_length": max(lengths),
                "sentence_count": len(lengths),
            }
        )
        all_lengths.extend(lengths)

    global_avg = sum(all_lengths) / len(all_lengths) if all_lengths else 0
    global_var = (
        sum((l - global_avg) ** 2 for l in all_lengths) / len(all_lengths) if all_lengths else 0
    )
    global_std = global_var**0.5
    global_cv = global_std / global_avg if global_avg > 0 else 0

    return {
        "global_stats": {
            "avg_length": round(global_avg, 1),
            "std_dev": round(global_std, 1),
            "variation_coefficient": round(global_cv, 3),
            "min_length": min(all_lengths) if all_lengths else 0,
            "max_length": max(all_lengths) if all_lengths else 0,
            "total_sentences": len(all_lengths),
        },
        "chapters": chapter_results,
    }


def _compute_dialogue_validation(chapters):
    """Validate dialogue attribution."""
    from narrative_assistant.nlp.dialogue_validator import DialogueContextValidator

    validator = DialogueContextValidator()
    chapters_info = [
        {"number": ch.chapter_number, "start_char": 0, "content": ch.content or ""}
        for ch in chapters
    ]
    report = validator.validate_all(chapters_info)
    return report.to_dict() if hasattr(report, "to_dict") else report


def _compute_narrative_structure(full_text, chapters_dicts):
    """Detect prolepsis/analepsis in narrative."""
    from narrative_assistant.analysis.narrative_structure import get_narrative_structure_detector

    detector = get_narrative_structure_detector()
    report = detector.detect_all(full_text, chapters_dicts, min_confidence=0.5)
    return report.to_dict() if hasattr(report, "to_dict") else report


# ============================================================================
# Phase 13: Health enrichment
# ============================================================================


def run_health_enrichment(ctx: dict, tracker) -> None:
    """Phase 13: Pre-compute narrative health analysis."""
    phase_key = "health"
    phase_index = 12

    tracker.start_phase(phase_key, phase_index, "Evaluando salud narrativa...")

    project_id = ctx["project_id"]
    db = ctx["db_session"]

    try:
        entities = _load_entities(db, project_id)
        chapters = _load_chapters(db, project_id)
        chapters_dicts = _chapters_to_dicts(chapters)
        entities_dicts = _entities_to_dicts(entities)

        total_steps = 3
        step = 0

        # --- 13a: Chapter Progress (basic mode — no LLM) ---
        step += 1
        tracker.update_progress(
            phase_key, step / total_steps, "Analizando progreso por capítulo..."
        )
        progress_data = None

        def compute_chapter_progress():
            nonlocal progress_data
            from narrative_assistant.analysis.chapter_summary import analyze_chapter_progress

            result = analyze_chapter_progress(project_id, mode="basic")
            if hasattr(result, "is_failure") and result.is_failure:
                raise RuntimeError(f"Chapter progress failed: {result.error}")
            data = result.value if hasattr(result, "value") else result
            progress_data = data
            return data.to_dict() if hasattr(data, "to_dict") else data

        _run_enrichment(
            db, project_id, "chapter_progress", 13, compute_chapter_progress, "chapter_progress"
        )

        # --- 13b: Narrative Templates ---
        step += 1
        tracker.update_progress(
            phase_key, step / total_steps, "Comparando con plantillas narrativas..."
        )
        if progress_data is not None:
            _run_enrichment(
                db,
                project_id,
                "narrative_templates",
                13,
                lambda: _compute_narrative_templates(progress_data, chapters_dicts, len(chapters)),
                "narrative_templates",
            )

        # --- 13c: Narrative Health (12 dimensions) ---
        step += 1
        tracker.update_progress(phase_key, step / total_steps, "Calculando puntuación de salud...")
        if progress_data is not None:
            _run_enrichment(
                db,
                project_id,
                "narrative_health",
                13,
                lambda: _compute_narrative_health(
                    progress_data, chapters_dicts, entities_dicts, len(chapters)
                ),
                "narrative_health",
            )

    except Exception as e:
        logger.error(f"[Phase 13] Health enrichment failed: {e}", exc_info=True)

    tracker.complete_phase(phase_key, phase_index)


def _compute_narrative_templates(progress_data, chapters_dicts, total_chapters):
    """Match narrative against known templates (3 Acts, Hero's Journey, etc.)."""
    from narrative_assistant.analysis.narrative_templates import NarrativeTemplateAnalyzer

    analyzer = NarrativeTemplateAnalyzer()

    # Extract chapters_data from progress_data
    pd = (
        progress_data
        if isinstance(progress_data, dict)
        else (progress_data.to_dict() if hasattr(progress_data, "to_dict") else {})
    )
    ch_data = pd.get("chapters", chapters_dicts)

    report = analyzer.analyze(ch_data, total_chapters)
    return report.to_dict() if hasattr(report, "to_dict") else report


def _compute_narrative_health(progress_data, chapters_dicts, entities_dicts, total_chapters):
    """Compute 12-dimension narrative health check."""
    from narrative_assistant.analysis.narrative_health import NarrativeHealthChecker

    checker = NarrativeHealthChecker()

    pd = (
        progress_data
        if isinstance(progress_data, dict)
        else (progress_data.to_dict() if hasattr(progress_data, "to_dict") else {})
    )
    character_arcs = pd.get("character_arcs", [])
    chekhov_elements = pd.get("chekhov_elements", [])
    abandoned_threads = pd.get("abandoned_threads", [])
    ch_data = pd.get("chapters", chapters_dicts)

    report = checker.check(
        chapters_data=ch_data,
        total_chapters=total_chapters,
        entities_data=entities_dicts,
        character_arcs=character_arcs,
        chekhov_elements=chekhov_elements,
        abandoned_threads=abandoned_threads,
    )
    return report.to_dict() if hasattr(report, "to_dict") else report


# ============================================================================
# S15: Version metrics (post-Phase 13 hook)
# ============================================================================


def write_version_metrics(ctx: dict) -> int | None:
    """S15-03: Persist aggregated metrics for this analysis as a version.

    Called after Phase 13 completes. Reads metrics from enrichment_cache
    and analysis context to build a version_metrics row.
    """
    project_id = ctx["project_id"]
    db = ctx["db_session"]

    try:
        with db.connection() as conn:
            # Determine next version_num for this project
            row = conn.execute(
                "SELECT COALESCE(MAX(version_num), 0) FROM version_metrics WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            next_version = (row[0] if row else 0) + 1

            # Get latest snapshot_id (if any)
            snap_row = conn.execute(
                "SELECT id FROM analysis_snapshots WHERE project_id = ? ORDER BY created_at DESC LIMIT 1",
                (project_id,),
            ).fetchone()
            snapshot_id = snap_row[0] if snap_row else None

            # Alert count (open alerts)
            alert_row = conn.execute(
                "SELECT COUNT(*) FROM alerts WHERE project_id = ? AND status != 'resolved'",
                (project_id,),
            ).fetchone()
            alert_count = alert_row[0] if alert_row else 0
            severity_rows = conn.execute(
                """
                SELECT severity, COUNT(*) AS cnt
                FROM alerts
                WHERE project_id = ? AND status != 'resolved'
                GROUP BY severity
                """,
                (project_id,),
            ).fetchall()
            severity_counts = {str(r[0] or "").lower(): int(r[1]) for r in severity_rows}
            critical_count = severity_counts.get("critical", 0) + severity_counts.get("high", 0)
            warning_count = severity_counts.get("warning", 0) + severity_counts.get("medium", 0)
            info_count = severity_counts.get("info", 0) + severity_counts.get("low", 0)

            # Word count + chapter count from project
            proj_row = conn.execute(
                "SELECT word_count, chapter_count FROM projects WHERE id = ?",
                (project_id,),
            ).fetchone()
            word_count = proj_row[0] if proj_row else ctx.get("word_count", 0)
            chapter_count = proj_row[1] if proj_row else ctx.get("chapters_count", 0)

            # Entity count
            entity_row = conn.execute(
                "SELECT COUNT(*) FROM entities WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            entity_count = entity_row[0] if entity_row else 0

            # Health score from enrichment_cache (narrative_health)
            health_score = None
            health_row = conn.execute(
                """SELECT result_json FROM enrichment_cache
                   WHERE project_id = ? AND enrichment_type = 'narrative_health'
                   AND status = 'completed' LIMIT 1""",
                (project_id,),
            ).fetchone()
            if health_row and health_row[0]:
                try:
                    health_data = json.loads(health_row[0])
                    health_score = health_data.get("overall_score") or health_data.get(
                        "health_score"
                    )
                except (json.JSONDecodeError, TypeError):
                    pass

            # Formality avg from enrichment_cache (register_analysis)
            formality_avg = None
            reg_row = conn.execute(
                """SELECT result_json FROM enrichment_cache
                   WHERE project_id = ? AND enrichment_type = 'register_analysis'
                   AND status = 'completed' LIMIT 1""",
                (project_id,),
            ).fetchone()
            if reg_row and reg_row[0]:
                try:
                    reg_data = json.loads(reg_row[0])
                    summary = reg_data.get("summary", {})
                    formality_avg = summary.get("avg_formality") or summary.get("formality_avg")
                except (json.JSONDecodeError, TypeError):
                    pass

            # Dialogue ratio — average across chapters
            dialogue_ratio = None
            dr_rows = conn.execute(
                "SELECT dialogue_ratio FROM chapters WHERE project_id = ? AND dialogue_ratio IS NOT NULL",
                (project_id,),
            ).fetchall()
            if dr_rows:
                dialogue_ratio = sum(r[0] for r in dr_rows) / len(dr_rows)

            prev_snapshot_id = ctx.get("pre_analysis_snapshot_id")
            alerts_new_count = 0
            alerts_resolved_count = 0
            alerts_unchanged_count = 0
            if prev_snapshot_id:
                prev_alerts = conn.execute(
                    """
                    SELECT content_hash FROM snapshot_alerts
                    WHERE snapshot_id = ?
                    """,
                    (prev_snapshot_id,),
                ).fetchall()
                current_alerts = conn.execute(
                    """
                    SELECT content_hash FROM alerts
                    WHERE project_id = ? AND status != 'resolved'
                    """,
                    (project_id,),
                ).fetchall()
                prev_set = {str(r[0]) for r in prev_alerts if r[0]}
                current_set = {str(r[0]) for r in current_alerts if r[0]}
                if prev_set or current_set:
                    alerts_new_count = len(current_set - prev_set)
                    alerts_resolved_count = len(prev_set - current_set)
                    alerts_unchanged_count = len(current_set & prev_set)

            chapter_diff = ctx.get("version_chapter_diff", {}) or {}
            entity_diff = ctx.get("version_entity_diff", {}) or {}
            phase_durations_json = json.dumps(
                ctx.get("phase_durations_json", {}), ensure_ascii=False, sort_keys=True
            )
            run_mode = str(ctx.get("run_mode") or "full")
            duration_total_sec = float(ctx.get("duration_total_sec") or 0.0)

            conn.execute(
                """INSERT OR REPLACE INTO version_metrics
                   (project_id, version_num, snapshot_id, alert_count, word_count,
                    entity_count, chapter_count, health_score, formality_avg, dialogue_ratio,
                    alerts_new_count, alerts_resolved_count, alerts_unchanged_count,
                    critical_count, warning_count, info_count,
                    entities_new_count, entities_removed_count, entities_renamed_count,
                    chapter_added_count, chapter_removed_count, chapter_reordered_count,
                    run_mode, duration_total_sec, phase_durations_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    project_id,
                    next_version,
                    snapshot_id,
                    alert_count,
                    word_count,
                    entity_count,
                    chapter_count,
                    health_score,
                    formality_avg,
                    dialogue_ratio,
                    alerts_new_count,
                    alerts_resolved_count,
                    alerts_unchanged_count,
                    critical_count,
                    warning_count,
                    info_count,
                    int(entity_diff.get("new_entities", 0)),
                    int(entity_diff.get("removed_entities", 0)),
                    int(entity_diff.get("renamed", entity_diff.get("renamed_entities", 0))),
                    int(chapter_diff.get("added", 0)),
                    int(chapter_diff.get("removed", 0)),
                    0,  # chapter_reordered_count (pendiente de algoritmo dedicado)
                    run_mode,
                    duration_total_sec,
                    phase_durations_json,
                ),
            )
            conn.commit()

            logger.info(
                f"[S15] Version {next_version} metrics written for project {project_id}: "
                f"alerts={alert_count}, words={word_count}, health={health_score}"
            )
            return int(next_version)

    except Exception as e:
        logger.warning(f"[S15] Failed to write version metrics for project {project_id}: {e}")
    return None


def _hash_payload(payload: Any) -> str:
    """Hash estable para detectar si los inputs de una fase cambiaron."""
    try:
        packed = json.dumps(payload, ensure_ascii=False, default=str, sort_keys=True)
    except Exception:
        packed = str(payload)
    return hashlib.sha256(packed.encode("utf-8")).hexdigest()[:16]
