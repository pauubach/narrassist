"""Bloque temporal extraido del pipeline legacy."""

from __future__ import annotations

import logging
from typing import Any

from ..core.errors import ErrorSeverity, NarrativeError
from ..core.result import Result
from ..entities.models import Entity
from ..entities.repository import get_entity_repository
from ..temporal import TemporalConsistencyChecker, TemporalMarkerExtractor, TimelineBuilder
from .analysis_pipeline_models import ChapterInfo

logger = logging.getLogger(__name__)


def _run_temporal_analysis(
    text: str,
    chapters: list[ChapterInfo],
    project_id: int | None = None,
    entities: list[Entity] | None = None,
) -> Result[dict[str, Any]]:
    """
    Ejecuta analisis temporal completo.

    Extrae marcadores temporales, construye timeline y detecta inconsistencias.
    """
    try:
        marker_extractor = TemporalMarkerExtractor()
        all_markers = []

        entity_mentions_by_chapter: dict[int, list[tuple[int, int, int]]] = {}
        if project_id is not None and entities:
            try:
                from ..persistence.chapter import ChapterRepository
                from ..temporal.entity_mentions import load_entity_mentions_by_chapter

                chapter_repo = ChapterRepository()
                db_chapters = chapter_repo.get_by_project(project_id)
                entity_repo = get_entity_repository()
                entity_mentions_by_chapter = load_entity_mentions_by_chapter(
                    entities, db_chapters, entity_repo,
                )
            except Exception as exc:
                logger.debug(
                    "Could not load entity mentions for temporal analysis pipeline: %s",
                    exc,
                )

        for chapter in chapters:
            chapter_mentions = entity_mentions_by_chapter.get(chapter.number, [])
            if chapter_mentions:
                chapter_markers = marker_extractor.extract_with_entities(
                    text=chapter.content,
                    entity_mentions=chapter_mentions,
                    chapter=chapter.number,
                )
            else:
                chapter_markers = marker_extractor.extract(
                    text=chapter.content,
                    chapter=chapter.number,
                )
            all_markers.extend(chapter_markers)

        logger.info(
            "Extracted %s temporal markers (Level A) from %s chapters",
            len(all_markers),
            len(chapters),
        )

        llm_instance_count = 0
        if entities:
            try:
                from ..temporal.llm_extraction import (
                    build_instance_id,
                    extract_temporal_instances_llm,
                    merge_with_regex_instances,
                    resolve_entity_ids,
                )

                entity_name_to_id = {entity.canonical_name.lower(): entity.id for entity in entities if entity.id}
                entity_names = [entity.canonical_name for entity in entities]

                regex_ids: set[str] = set()
                for marker in all_markers:
                    if marker.temporal_instance_id:
                        regex_ids.add(marker.temporal_instance_id)

                for chapter in chapters:
                    llm_instances = extract_temporal_instances_llm(
                        chapter_text=chapter.content,
                        entity_names=entity_names,
                    )
                    if not llm_instances:
                        continue

                    llm_instances = resolve_entity_ids(llm_instances, entity_name_to_id)
                    new_instances = merge_with_regex_instances(regex_ids, llm_instances)

                    for instance in new_instances:
                        instance_id = build_instance_id(instance)
                        if not instance_id:
                            continue

                        regex_ids.add(instance_id)
                        from ..temporal.markers import MarkerType, TemporalMarker

                        marker = TemporalMarker(
                            text=instance.evidence or instance.entity_name,
                            marker_type=MarkerType.CHARACTER_AGE,
                            start_char=0,
                            end_char=0,
                            chapter=chapter.number,
                            entity_id=instance.entity_id,
                            confidence=instance.confidence,
                            temporal_instance_id=instance_id,
                        )
                        if instance.instance_type == "age":
                            marker.age = int(instance.value)
                        elif instance.instance_type == "phase":
                            marker.age_phase = str(instance.value)
                        elif instance.instance_type == "year":
                            marker.year = int(instance.value)
                        elif instance.instance_type == "offset":
                            marker.relative_year_offset = int(instance.value)

                        all_markers.append(marker)
                        llm_instance_count += 1

                if llm_instance_count > 0:
                    logger.info("Level B (LLM) added %s new temporal instances", llm_instance_count)
            except Exception as exc:
                logger.debug("Level B temporal extraction failed (graceful degradation): %s", exc)

        logger.info("Total temporal markers: %s (Level A + B)", len(all_markers))

        builder = TimelineBuilder()
        chapter_data = [
            {
                "number": chapter.number,
                "title": chapter.title or f"Capitulo {chapter.number}",
                "start_position": chapter.start_char,
                "content": chapter.content,
            }
            for chapter in chapters
        ]

        timeline = builder.build_from_markers(all_markers, chapter_data)
        logger.info(
            "Built timeline with %s events, %s anchors",
            len(timeline.events),
            len(timeline.anchor_events),
        )

        level_c_ok = False
        cross_chapter_result = None
        try:
            from ..temporal.cross_chapter import build_entity_timelines

            level_c_result = build_entity_timelines(
                all_markers, entities or [], timeline,
            )
            if level_c_result.is_success and level_c_result.value is not None:
                cross_chapter_result = level_c_result.value
                level_c_ok = True
                all_markers.extend(cross_chapter_result.inferred_markers)

                logger.info(
                    "Level C: %s entity timelines, %s inferred markers, %s inconsistencies",
                    len(cross_chapter_result.entity_timelines),
                    len(cross_chapter_result.inferred_markers),
                    len(cross_chapter_result.new_inconsistencies),
                )
            else:
                logger.debug("Level C returned failure: %s", level_c_result.error)
        except Exception as exc:
            logger.debug("Level C cross-chapter linking failed (graceful degradation): %s", exc)

        checker = TemporalConsistencyChecker()
        character_ages: dict[int, list[tuple[int, int]]] = {}
        for marker in all_markers:
            if marker.age and marker.entity_id and marker.chapter:
                character_ages.setdefault(marker.entity_id, []).append((marker.chapter, marker.age))

        inconsistencies = checker.check(
            timeline,
            all_markers,
            character_ages=None if level_c_ok else character_ages,
        )

        if level_c_ok and cross_chapter_result:
            inconsistencies.extend(cross_chapter_result.new_inconsistencies)

        logger.info("Found %s temporal inconsistencies", len(inconsistencies))

        return Result.success(
            {
                "timeline": timeline,
                "markers": all_markers,
                "markers_count": len(all_markers),
                "inconsistencies": inconsistencies,
                "entity_timelines": (
                    cross_chapter_result.entity_timelines if cross_chapter_result else {}
                ),
            }
        )

    except Exception as exc:
        error = NarrativeError(
            message=f"Temporal analysis failed: {str(exc)}",
            severity=ErrorSeverity.RECOVERABLE,
        )
        logger.exception("Error during temporal analysis")
        return Result.failure(error)


def _persist_timeline(
    project_id: int,
    timeline,
    markers: list[Any],
) -> None:
    """Persiste timeline y marcadores temporales en base de datos."""
    try:
        from ..persistence.timeline import (
            TemporalMarkerData,
            TimelineEventData,
            TimelineRepository,
        )

        repo = TimelineRepository()

        events_data = []
        for event in timeline.events:
            story_date_str = event.story_date.isoformat() if event.story_date else None

            events_data.append(
                TimelineEventData(
                    id=None,
                    project_id=project_id,
                    event_id=str(event.id),
                    chapter=event.chapter,
                    paragraph=event.paragraph,
                    description=event.description,
                    story_date=story_date_str,
                    story_date_resolution=event.story_date_resolution.value
                    if event.story_date_resolution
                    else "UNKNOWN",
                    narrative_order=event.narrative_order.value
                    if event.narrative_order
                    else "CHRONOLOGICAL",
                    discourse_position=event.discourse_position,
                    confidence=event.confidence,
                )
            )

        markers_data = []
        for marker in markers:
            markers_data.append(
                TemporalMarkerData(
                    id=None,
                    project_id=project_id,
                    chapter=marker.chapter or 0,
                    marker_type=marker.marker_type.value
                    if hasattr(marker.marker_type, "value")
                    else str(marker.marker_type),
                    text=marker.text,
                    start_char=marker.start_char,
                    end_char=marker.end_char,
                    confidence=marker.confidence,
                    year=marker.year,
                    month=marker.month,
                    day=marker.day,
                    direction=marker.direction.value
                    if hasattr(marker, "direction")
                    and marker.direction
                    and hasattr(marker.direction, "value")
                    else getattr(marker, "direction", None),
                    quantity=getattr(marker, "quantity", None),
                    magnitude=getattr(marker, "magnitude", None),
                    age=getattr(marker, "age", None),
                    entity_id=getattr(marker, "entity_id", None),
                )
            )

        repo.save_events(project_id, events_data)
        repo.save_markers(project_id, markers_data)

        logger.info(
            "Persisted timeline for project %s: %s events, %s markers",
            project_id,
            len(events_data),
            len(markers_data),
        )
    except Exception as exc:
        logger.warning("Failed to persist timeline: %s", exc)
