"""
Router: events

Endpoints para detección y export de eventos narrativos.

Endpoints:
- GET /api/projects/{project_id}/chapters/{chapter_number}/events - Eventos de un capítulo
- GET /api/projects/{project_id}/events/export - Exportar eventos (CSV/JSON)
- GET /api/projects/{project_id}/events/stats - Estadísticas de eventos
"""

import csv
import io
import json
import logging
from collections import Counter
from datetime import datetime
from typing import Literal, Optional

import deps
from deps import ApiResponse
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Chapter Events Endpoint
# ============================================================================

@router.get("/api/projects/{project_id}/chapters/{chapter_number}/events", response_model=ApiResponse)
def get_chapter_events(project_id: int, chapter_number: int):
    """
    Obtiene eventos narrativos detectados en un capítulo específico.

    Lee primero de la tabla narrative_events (si existe).
    Si no hay datos persistidos, detecta on-the-fly (fallback para proyectos pre-migración).

    Args:
        project_id: ID del proyecto
        chapter_number: Número de capítulo

    Returns:
        ApiResponse con eventos agrupados por tier
    """
    try:
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        if not deps.chapter_repository:
            return ApiResponse(success=False, error="Chapter repository not initialized")

        chapters = deps.chapter_repository.get_by_project(project_id)
        chapter = next((ch for ch in chapters if ch.chapter_number == chapter_number), None)

        if not chapter:
            raise HTTPException(status_code=404, detail=f"Capítulo {chapter_number} no encontrado")

        from narrative_assistant.analysis.event_types import EVENT_TIER_MAP, EventTier
        from narrative_assistant.persistence.event_repository import get_event_repository

        # Intentar leer de tabla narrative_events primero
        event_repo = get_event_repository()
        result = event_repo.get_by_chapter(project_id, chapter_number)

        events = []
        if result.is_success and result.value:
            # Hay eventos persistidos, convertir a DetectedEvent
            from narrative_assistant.analysis.event_detection import DetectedEvent
            from narrative_assistant.analysis.event_types import EventType

            events = [
                DetectedEvent(
                    event_type=EventType(e.event_type),
                    description=e.description,
                    confidence=e.confidence,
                    start_char=e.start_char,
                    end_char=e.end_char,
                    entity_ids=e.entity_ids,
                    metadata=e.metadata,
                )
                for e in result.value
            ]
            logger.info(f"Loaded {len(events)} events from narrative_events table")
        else:
            # Fallback: detectar on-the-fly (proyectos pre-migración v30)
            logger.info(f"No persisted events found, detecting on-the-fly for chapter {chapter_number}")
            from narrative_assistant.analysis.event_detection import detect_events_in_chapter
            from narrative_assistant.nlp.spacy_gpu import load_spacy_model

            nlp = load_spacy_model()

            # Get previous chapter text for POV change detection
            prev_chapter_text = None
            if chapter_number > 1:
                prev_ch = next((ch for ch in chapters if ch.chapter_number == chapter_number - 1), None)
                if prev_ch:
                    prev_chapter_text = prev_ch.content

            events = detect_events_in_chapter(
                text=chapter.content,
                chapter_number=chapter_number,
                nlp=nlp,
                enable_llm=False,
                prev_chapter_text=prev_chapter_text
            )

        def event_to_dict(e):
            return {
                "event_type": e.event_type.value,
                "description": e.description,
                "confidence": round(e.confidence, 2),
                "start_char": e.start_char,
                "end_char": e.end_char,
                "entity_ids": e.entity_ids,
                "metadata": e.metadata,
            }

        tier1 = [event_to_dict(e) for e in events if EVENT_TIER_MAP.get(e.event_type) == EventTier.TIER_1]
        tier2 = [event_to_dict(e) for e in events if EVENT_TIER_MAP.get(e.event_type) == EventTier.TIER_2]
        tier3 = [event_to_dict(e) for e in events if EVENT_TIER_MAP.get(e.event_type) == EventTier.TIER_3]

        events_by_type = Counter(e.event_type.value for e in events)

        return ApiResponse(success=True, data={
            "project_id": project_id,
            "chapter_number": chapter_number,
            "chapter_title": getattr(chapter, "title", None),
            "total_events": len(events),
            "tier1_events": tier1,
            "tier2_events": tier2,
            "tier3_events": tier3,
            "events_by_type": dict(events_by_type),
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting events for project {project_id} chapter {chapter_number}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


# ============================================================================
# Export Endpoint
# ============================================================================

@router.get("/api/projects/{project_id}/events/export")
def export_events(
    project_id: int,
    format: Literal["csv", "json"] = "csv",
    tier_filter: Optional[Literal["1", "2", "3"]] = None,
    event_types: Optional[str] = Query(None, description="CSV de tipos: promise,injury,flashback_start"),
    critical_only: bool = False,
    chapter_start: Optional[int] = None,
    chapter_end: Optional[int] = None,
):
    """
    Exporta eventos narrativos del proyecto en CSV o JSON.

    Filtros disponibles:
    - tier_filter: Filtrar por tier (1=críticos, 2=enriquecimiento, 3=género)
    - event_types: Lista de tipos separados por coma
    - critical_only: Solo eventos críticos sin resolver (sin pair)
    - chapter_start/end: Rango de capítulos

    Returns:
        CSV (UTF-8 BOM) o JSON con eventos filtrados
    """
    try:
        # Validar proyecto existe
        if not deps.project_manager:
            raise HTTPException(status_code=500, detail="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        project = result.value

        # Obtener capítulos
        if not deps.chapter_repository:
            raise HTTPException(status_code=500, detail="Chapter repository not initialized")

        chapters = deps.chapter_repository.get_by_project(project_id)

        # Filtrar por rango de capítulos
        if chapter_start is not None or chapter_end is not None:
            chapters = [
                ch for ch in chapters
                if (chapter_start is None or ch.chapter_number >= chapter_start)
                and (chapter_end is None or ch.chapter_number <= chapter_end)
            ]

        # Detectar eventos en todos los capítulos
        from narrative_assistant.analysis.event_detection import detect_events_in_chapter
        from narrative_assistant.nlp.spacy_gpu import load_spacy_model

        nlp = load_spacy_model()
        all_events = []
        prev_chapter_text = None

        for chapter in sorted(chapters, key=lambda c: c.chapter_number):
            events = detect_events_in_chapter(
                text=chapter.content,
                chapter_number=chapter.chapter_number,
                nlp=nlp,
                enable_llm=False,  # Sin LLM para export rápido
                prev_chapter_text=prev_chapter_text
            )

            # Añadir metadata de capítulo a cada evento
            for event in events:
                event.metadata["chapter"] = chapter.chapter_number

            all_events.extend(events)
            prev_chapter_text = chapter.content

        logger.info(f"Detected {len(all_events)} total events before filtering")

        # Aplicar filtros
        filtered_events = _apply_event_filters(
            all_events,
            tier_filter=tier_filter,
            event_types_str=event_types,
            critical_only=critical_only
        )

        logger.info(f"Filtered to {len(filtered_events)} events")

        # Límite de eventos
        MAX_EVENTS = 50_000
        if len(filtered_events) > MAX_EVENTS:
            raise HTTPException(
                status_code=413,
                detail=f"Demasiados eventos ({len(filtered_events)}). Máximo: {MAX_EVENTS}"
            )

        # Generar export según formato
        if format == "csv":
            return _export_csv(project, filtered_events)
        else:
            return _export_json(project, filtered_events, tier_filter, event_types, critical_only, chapter_start, chapter_end)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting events for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


def _apply_event_filters(events, tier_filter, event_types_str, critical_only):
    """Aplica filtros a lista de eventos."""
    from narrative_assistant.analysis.event_types import EVENT_TIER_MAP

    filtered = events

    # Filtro por tier
    if tier_filter:
        tier_int = int(tier_filter)
        filtered = [
            e for e in filtered
            if EVENT_TIER_MAP.get(e.event_type) and EVENT_TIER_MAP[e.event_type].value == tier_int
        ]

    # Filtro por tipos
    if event_types_str:
        types = {t.strip().lower() for t in event_types_str.split(",")}
        filtered = [e for e in filtered if e.event_type.value in types]

    # Filtro critical_only (eventos sin par resuelto)
    if critical_only:
        from narrative_assistant.analysis.event_continuity import EventContinuityTracker

        tracker = EventContinuityTracker()

        # Agrupar por capítulo
        events_by_chapter = {}
        for event in filtered:
            ch = event.metadata.get("chapter", 0)
            if ch not in events_by_chapter:
                events_by_chapter[ch] = []
            events_by_chapter[ch].append(event)

        # Rastrear continuidad
        for ch_num in sorted(events_by_chapter.keys()):
            for event in events_by_chapter[ch_num]:
                tracker.track_event(event, chapter=ch_num)

        issues = tracker.check_continuity()

        # Construir set de eventos sin resolver
        unresolved_event_ids = set()
        for issue in issues:
            for source_event in issue.source_events:
                # Usar (event_type, start_char) como ID único
                event_id = (source_event.event_type.value, source_event.start_char)
                unresolved_event_ids.add(event_id)

        filtered = [
            e for e in filtered
            if (e.event_type.value, e.start_char) in unresolved_event_ids
        ]

    return filtered


def _export_csv(project, events):
    """Genera CSV con UTF-8 BOM para Excel Windows."""
    from narrative_assistant.analysis.event_types import EVENT_TIER_MAP

    output = io.StringIO()

    # UTF-8 BOM para Excel Windows (crítico para caracteres españoles)
    output.write('\ufeff')

    writer = csv.DictWriter(output, fieldnames=[
        "chapter", "event_type", "tier", "description", "confidence",
        "start_char", "end_char", "entity_ids", "metadata"
    ])

    writer.writeheader()

    for event in events:
        tier = EVENT_TIER_MAP.get(event.event_type)
        tier_num = tier.value if tier else ""

        # Extraer chapter de metadata
        chapter = event.metadata.get("chapter", "")

        # Copiar metadata sin el campo chapter para evitar duplicación
        clean_metadata = {k: v for k, v in event.metadata.items() if k != "chapter"}

        writer.writerow({
            "chapter": chapter,
            "event_type": event.event_type.value,
            "tier": tier_num,
            "description": event.description,
            "confidence": f"{event.confidence:.2f}",
            "start_char": event.start_char,
            "end_char": event.end_char,
            "entity_ids": json.dumps(event.entity_ids),
            "metadata": json.dumps(clean_metadata, ensure_ascii=False)
        })

    csv_content = output.getvalue()
    output.close()

    # Generar nombre de archivo seguro
    safe_name = "".join(
        c if c.isalnum() or c in (' ', '-', '_') else '_'
        for c in project.name
    ).strip().replace(' ', '_').lower()[:50]  # Limitar longitud

    filename = f"eventos_{safe_name}.csv"

    return StreamingResponse(
        iter([csv_content.encode('utf-8')]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


def _export_json(project, events, tier_filter, event_types, critical_only, chapter_start, chapter_end):
    """Genera JSON con schema consistente."""
    from narrative_assistant.analysis.event_types import EVENT_TIER_MAP

    data = {
        "project_id": project.id,
        "project_name": project.name,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "total_events": len(events),
        "filters_applied": {
            "tier": tier_filter,
            "event_types": event_types.split(",") if event_types else None,
            "critical_only": critical_only,
            "chapter_range": [chapter_start, chapter_end] if chapter_start or chapter_end else None
        },
        "events": [
            {
                "chapter": e.metadata.get("chapter"),
                "event_type": e.event_type.value,
                "tier": EVENT_TIER_MAP.get(e.event_type).value if EVENT_TIER_MAP.get(e.event_type) else None,
                "description": e.description,
                "confidence": round(e.confidence, 2),
                "start_char": e.start_char,
                "end_char": e.end_char,
                "entity_ids": e.entity_ids,
                "metadata": {k: v for k, v in e.metadata.items() if k != "chapter"}
            }
            for e in events
        ]
    }

    return ApiResponse(success=True, data=data)


# ============================================================================
# Stats Endpoint
# ============================================================================

@router.get("/api/projects/{project_id}/events/stats")
def get_event_stats(project_id: int):
    """
    Obtiene estadísticas agregadas de eventos del proyecto.

    Returns:
        - Eventos críticos sin resolver
        - Capítulos vacíos (sin tier1)
        - Event clusters (3+ eventos del mismo tipo en un capítulo)
        - Densidad de eventos por capítulo
    """
    try:
        # Validar proyecto
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        # Obtener capítulos
        if not deps.chapter_repository:
            return ApiResponse(success=False, error="Chapter repository not initialized")

        chapters = deps.chapter_repository.get_by_project(project_id)

        if not chapters:
            return ApiResponse(success=True, data={
                "project_id": project_id,
                "total_events": 0,
                "critical_unresolved": {"count": 0, "by_type": {}, "details": []},
                "empty_chapters": [],
                "event_clusters": [],
                "density_by_chapter": []
            })

        # Detectar eventos
        from narrative_assistant.analysis.event_detection import detect_events_in_chapter
        from narrative_assistant.nlp.spacy_gpu import load_spacy_model

        nlp = load_spacy_model()
        events_by_chapter = {}
        prev_chapter_text = None

        for chapter in sorted(chapters, key=lambda c: c.chapter_number):
            events = detect_events_in_chapter(
                text=chapter.content,
                chapter_number=chapter.chapter_number,
                nlp=nlp,
                enable_llm=False,
                prev_chapter_text=prev_chapter_text
            )
            events_by_chapter[chapter.chapter_number] = events
            prev_chapter_text = chapter.content

        # Calcular stats
        stats = _calculate_event_stats(events_by_chapter, chapters, project_id)

        return ApiResponse(success=True, data=stats)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating event stats for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


def _calculate_event_stats(events_by_chapter, chapters, project_id):
    """Calcula estadísticas de eventos."""
    from narrative_assistant.analysis.event_continuity import EventContinuityTracker
    from narrative_assistant.analysis.event_types import EVENT_TIER_MAP, EventTier

    # 1. Rastrear continuidad para eventos críticos sin resolver
    tracker = EventContinuityTracker()

    for ch_num in sorted(events_by_chapter.keys()):
        for event in events_by_chapter[ch_num]:
            tracker.track_event(event, chapter=ch_num)

    issues = tracker.check_continuity()
    critical_issues = [
        i for i in issues
        if i.severity in ("critical", "high")
    ]

    critical_by_type = Counter(i.event_type.value for i in critical_issues)

    critical_unresolved = {
        "count": len(critical_issues),
        "by_type": dict(critical_by_type),
        "details": [
            {
                "event_type": i.event_type.value,
                "description": i.description,
                "chapter": i.source_events[0].metadata.get("chapter") if i.source_events else None,
                "severity": i.severity
            }
            for i in critical_issues[:10]  # Top 10
        ]
    }

    # 2. Capítulos vacíos (sin eventos tier1)
    empty_chapters = []
    for ch_num, events in events_by_chapter.items():
        tier1_count = sum(
            1 for e in events
            if EVENT_TIER_MAP.get(e.event_type) == EventTier.TIER_1
        )
        if tier1_count == 0:
            empty_chapters.append(ch_num)

    # 3. Event clusters (3+ eventos del mismo tipo en un capítulo)
    clusters = []
    for ch_num, events in events_by_chapter.items():
        type_counts = Counter(e.event_type.value for e in events)
        for event_type, count in type_counts.most_common():
            if count >= 3:
                clusters.append({
                    "event_type": event_type,
                    "chapter": ch_num,
                    "count": count,
                    "description": f"{count} {event_type} en cap. {ch_num}"
                })

    # Ordenar por count descendente y tomar top 3
    clusters.sort(key=lambda x: x["count"], reverse=True)
    clusters = clusters[:3]

    # 4. Densidad por capítulo
    density_by_chapter = []
    for chapter in sorted(chapters, key=lambda c: c.chapter_number):
        ch_num = chapter.chapter_number
        events = events_by_chapter.get(ch_num, [])

        tier1 = sum(1 for e in events if EVENT_TIER_MAP.get(e.event_type) == EventTier.TIER_1)
        tier2 = sum(1 for e in events if EVENT_TIER_MAP.get(e.event_type) == EventTier.TIER_2)
        tier3 = sum(1 for e in events if EVENT_TIER_MAP.get(e.event_type) == EventTier.TIER_3)

        density_by_chapter.append({
            "chapter": ch_num,
            "tier1": tier1,
            "tier2": tier2,
            "tier3": tier3,
            "total": tier1 + tier2 + tier3
        })

    # Total de eventos
    total_events = sum(len(events) for events in events_by_chapter.values())

    return {
        "project_id": project_id,
        "total_events": total_events,
        "critical_unresolved": critical_unresolved,
        "empty_chapters": empty_chapters,
        "event_clusters": clusters,
        "density_by_chapter": density_by_chapter
    }
