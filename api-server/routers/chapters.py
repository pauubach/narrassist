"""
Router: chapters
"""

from typing import Optional

import deps
from deps import ApiResponse, logger
from fastapi import APIRouter, HTTPException, Query

from narrative_assistant.alerts.models import AlertStatus

router = APIRouter()

@router.get("/api/projects/{project_id}/chapters", response_model=ApiResponse)
def list_chapters(project_id: int):
    """
    Lista todos los capítulos de un proyecto.

    Args:
        project_id: ID del proyecto

    Returns:
        ApiResponse con lista de capítulos
    """
    try:
        if not deps.chapter_repository:
            return ApiResponse(success=False, error="Chapter repository not initialized")

        # Verificar que el proyecto existe
        if deps.project_manager:
            result = deps.project_manager.get(project_id)
            if result.is_failure:
                raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        # Obtener capítulos reales de la base de datos
        chapters = deps.chapter_repository.get_by_project(project_id)

        # Función helper para convertir secciones a dict recursivamente
        def section_to_dict(section) -> dict:
            return {
                "id": section.id,
                "project_id": section.project_id,
                "chapter_id": section.chapter_id,
                "parent_section_id": section.parent_section_id,
                "section_number": section.section_number,
                "title": section.title,
                "heading_level": section.heading_level,
                "start_char": section.start_char,
                "end_char": section.end_char,
                "subsections": [section_to_dict(s) for s in section.subsections]
            }

        # Convertir a formato de respuesta con secciones
        chapters_data = []
        for ch in chapters:
            # Obtener secciones jerárquicas de este capítulo
            sections = []
            if deps.section_repository:
                sections = deps.section_repository.get_by_chapter_hierarchical(ch.id)

            chapters_data.append({
                "id": ch.id,
                "project_id": ch.project_id,
                "title": ch.title or f"Capítulo {ch.chapter_number}",
                "content": ch.content,
                "chapter_number": ch.chapter_number,
                "word_count": ch.word_count,
                "position_start": ch.start_char,
                "position_end": ch.end_char,
                "structure_type": ch.structure_type,
                "created_at": ch.created_at,
                "updated_at": ch.updated_at,
                "sections": [section_to_dict(s) for s in sections]
            })

        return ApiResponse(success=True, data=chapters_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing chapters for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/chapters/{chapter_number}/annotations", response_model=ApiResponse)
def get_chapter_annotations(project_id: int, chapter_number: int):
    """
    Obtiene anotaciones de gramática y ortografía para un capítulo.

    Devuelve errores gramaticales y ortográficos con posiciones para
    resaltar en el visor de documento.

    Args:
        project_id: ID del proyecto
        chapter_number: Número de capítulo

    Returns:
        ApiResponse con lista de anotaciones (errores gramaticales/ortográficos)
    """
    try:
        if not deps.alert_repository:
            return ApiResponse(success=False, error="Alert repository not initialized")

        # Obtener alertas de gramática y ortografía para este capítulo
        alerts_result = deps.alert_repository.get_by_project(project_id)

        if alerts_result.is_failure:
            return ApiResponse(success=False, error=str(alerts_result.error))

        all_alerts = alerts_result.value

        # Filtrar por categoría y capítulo
        annotations = []
        grammar_categories = {'grammar', 'orthography', 'spelling'}
        active_statuses = {AlertStatus.NEW, AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED, AlertStatus.IN_PROGRESS}

        for alert in all_alerts:
            # Solo incluir alertas de gramática/ortografía
            category_value = alert.category.value if hasattr(alert.category, 'value') else str(alert.category)
            if category_value not in grammar_categories:
                continue

            # Solo incluir alertas de este capítulo
            if alert.chapter != chapter_number:
                continue

            # Solo alertas activas
            if alert.status not in active_statuses:
                continue

            annotations.append({
                "id": alert.id,
                "type": category_value,
                "severity": alert.severity.value if hasattr(alert.severity, 'value') else str(alert.severity),
                "title": alert.title,
                "description": alert.description,
                "start_char": getattr(alert, 'start_char', None),
                "end_char": getattr(alert, 'end_char', None),
                "suggestion": alert.suggestion,
                "excerpt": getattr(alert, 'excerpt', None),
            })

        return ApiResponse(success=True, data={
            "chapter_number": chapter_number,
            "annotations": annotations,
            "total_count": len(annotations)
        })

    except Exception as e:
        logger.error(f"Error getting chapter annotations: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/style-guide", response_model=ApiResponse)
def get_style_guide(project_id: int, format: str = "json", preview: bool = False):
    """
    Genera y devuelve la guía de estilo del proyecto.

    La guía incluye:
    - Decisiones de grafía (variantes de nombres, acentos)
    - Lista de entidades canónicas (personajes, lugares, organizaciones)
    - Análisis estilístico (diálogos, puntuación, números)
    - Estadísticas del texto
    - Inconsistencias y recomendaciones

    Args:
        project_id: ID del proyecto
        format: Formato de respuesta ('json', 'markdown' o 'pdf')
        preview: Si es True, devuelve un resumen para previsualización

    Returns:
        ApiResponse con la guía de estilo
    """
    try:
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        # Obtener proyecto
        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        project = result.value

        # Obtener texto completo para análisis estilístico
        full_text = ""
        if deps.chapter_repository:
            chapters = deps.chapter_repository.get_by_project(project_id)
            full_text = "\n\n".join(ch.content for ch in chapters if ch.content)

        # Generar guía de estilo
        from narrative_assistant.exporters.style_guide import generate_style_guide

        style_result = generate_style_guide(
            project_id=project_id,
            project_name=project.name,
            text=full_text
        )

        if style_result.is_failure:
            return ApiResponse(success=False, error=str(style_result.error))

        style_guide = style_result.value

        # Si es preview, devolver resumen simplificado
        if preview:
            preview_data = {
                "project_name": project.name,
                "generated_date": style_guide.generated_date,
                "total_entities": style_guide.total_entities,
                "total_spelling_variants": style_guide.total_spelling_variants,
                "characters_count": len(style_guide.characters),
                "locations_count": len(style_guide.locations),
                "organizations_count": len(style_guide.organizations),
                "has_style_analysis": style_guide.style_analysis is not None,
                "spelling_decisions_preview": [
                    {
                        "canonical_form": d.canonical_form,
                        "variants_count": len(d.variants)
                    }
                    for d in style_guide.spelling_decisions[:5]
                ],
                "characters_preview": [
                    {
                        "name": c.canonical_name,
                        "importance": c.importance,
                        "aliases_count": len(c.aliases)
                    }
                    for c in sorted(
                        style_guide.characters,
                        key=lambda x: {"principal": 0, "critical": 0, "high": 1, "medium": 2, "low": 3, "minimal": 4}.get(x.importance, 5)
                    )[:10]
                ],
                "style_summary": None
            }

            if style_guide.style_analysis:
                sa = style_guide.style_analysis
                preview_data["style_summary"] = {
                    "dialogue_style": sa.dialogue_style,
                    "number_style": sa.number_style,
                    "total_words": sa.statistics.total_words,
                    "total_sentences": sa.statistics.total_sentences,
                    "consistency_issues_count": len(sa.consistency_issues),
                    "recommendations_count": len(sa.recommendations)
                }

            return ApiResponse(success=True, data={
                "format": "preview",
                "preview": preview_data,
                "project_name": project.name
            })

        # Devolver en el formato solicitado
        if format == "markdown":
            return ApiResponse(success=True, data={
                "format": "markdown",
                "content": style_guide.to_markdown(),
                "project_name": project.name
            })
        elif format == "pdf":
            # Generar PDF como base64 string
            import base64
            import io

            try:
                # Intentar usar reportlab si está disponible
                from reportlab.lib import colors
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
                from reportlab.lib.units import cm
                from reportlab.platypus import (
                    Paragraph,
                    SimpleDocTemplate,
                    Spacer,
                    Table,
                    TableStyle,
                )

                buffer = io.BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
                styles = getSampleStyleSheet()

                # Estilos personalizados
                title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=18, spaceAfter=20)
                heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=14, spaceAfter=10, spaceBefore=15)
                normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=10, spaceAfter=6)

                elements = []

                # Título
                elements.append(Paragraph(f"Guía de Estilo - {style_guide.project_name}", title_style))
                elements.append(Paragraph(f"Generado: {style_guide.generated_date}", normal_style))
                elements.append(Spacer(1, 20))

                # Resumen
                elements.append(Paragraph("Resumen", heading_style))
                summary_data = [
                    ["Total de entidades", str(style_guide.total_entities)],
                    ["Personajes", str(len(style_guide.characters))],
                    ["Ubicaciones", str(len(style_guide.locations))],
                    ["Organizaciones", str(len(style_guide.organizations))],
                    ["Variaciones de grafía", str(style_guide.total_spelling_variants)],
                ]
                summary_table = Table(summary_data, colWidths=[8*cm, 4*cm])
                summary_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                elements.append(summary_table)
                elements.append(Spacer(1, 15))

                # Personajes principales
                if style_guide.characters:
                    elements.append(Paragraph("Personajes Principales", heading_style))
                    main_chars = [c for c in style_guide.characters if c.importance in ("principal", "critical", "high")][:10]
                    for char in main_chars:
                        char_text = f"<b>{char.canonical_name}</b>"
                        if char.aliases:
                            char_text += f" (también: {', '.join(char.aliases[:3])})"
                        elements.append(Paragraph(char_text, normal_style))
                    elements.append(Spacer(1, 10))

                # Decisiones de grafía
                if style_guide.spelling_decisions:
                    elements.append(Paragraph("Decisiones de Grafía", heading_style))
                    for decision in style_guide.spelling_decisions[:10]:
                        decision_text = f"<b>{decision.canonical_form}</b>: {', '.join(decision.variants) if decision.variants else 'Sin variantes'}"
                        elements.append(Paragraph(decision_text, normal_style))
                    elements.append(Spacer(1, 10))

                # Análisis estilístico
                if style_guide.style_analysis:
                    sa = style_guide.style_analysis
                    elements.append(Paragraph("Análisis Estilístico", heading_style))
                    style_info = [
                        f"Estilo de diálogos: {sa.dialogue_style}",
                        f"Estilo de números: {sa.number_style}",
                        f"Total de palabras: {sa.statistics.total_words:,}",
                        f"Total de oraciones: {sa.statistics.total_sentences:,}",
                    ]
                    for info in style_info:
                        elements.append(Paragraph(info, normal_style))

                    if sa.consistency_issues:
                        elements.append(Spacer(1, 10))
                        elements.append(Paragraph("Inconsistencias detectadas:", normal_style))
                        for issue in sa.consistency_issues[:5]:
                            elements.append(Paragraph(f"• {issue}", normal_style))

                # Construir PDF
                doc.build(elements)
                pdf_bytes = buffer.getvalue()
                pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

                return ApiResponse(success=True, data={
                    "format": "pdf",
                    "content": pdf_base64,
                    "content_type": "application/pdf",
                    "filename": f"guia_estilo_{project.name}.pdf",
                    "project_name": project.name
                })

            except ImportError:
                # Si reportlab no está disponible, devolver error con sugerencia
                return ApiResponse(
                    success=False,
                    error="Exportación PDF no disponible. Instale reportlab: pip install reportlab",
                    data={
                        "format": "pdf",
                        "fallback_format": "markdown",
                        "content": style_guide.to_markdown(),
                        "project_name": project.name
                    }
                )
        else:
            return ApiResponse(success=True, data={
                "format": "json",
                "content": style_guide.to_dict(),
                "project_name": project.name
            })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating style guide for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/timeline", response_model=ApiResponse)
def get_project_timeline(project_id: int, force_refresh: bool = False):
    """
    Obtiene el timeline temporal del proyecto.

    Lee el timeline desde la base de datos si ya fue analizado.
    Solo recalcula si no hay datos o se fuerza el refresh.

    Args:
        project_id: ID del proyecto
        force_refresh: Si True, recalcula el timeline ignorando el caché

    Returns:
        ApiResponse con datos del timeline:
        - events: Lista de eventos temporales
        - markers_count: Número de marcadores detectados
        - anchor_count: Número de anclas temporales (fechas absolutas)
        - time_span: Rango temporal de la historia (si se puede determinar)
        - mermaid: Diagrama Mermaid del timeline
    """
    try:
        if not deps.chapter_repository:
            return ApiResponse(success=False, error="Chapter repository not initialized")

        # Verificar que el proyecto existe
        if deps.project_manager:
            result = deps.project_manager.get(project_id)
            if result.is_failure:
                raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        # Intentar leer timeline desde la base de datos
        from narrative_assistant.persistence.timeline import TimelineRepository

        timeline_repo = TimelineRepository()

        # Límite de eventos para proteger al frontend
        MAX_TIMELINE_EVENTS = 5000

        if not force_refresh and timeline_repo.has_timeline(project_id):
            # Leer desde BD (rápido)
            total_count = timeline_repo.count_events(project_id)
            events = timeline_repo.get_events(
                project_id, max_events=MAX_TIMELINE_EVENTS
            )
            truncated = total_count > MAX_TIMELINE_EVENTS
            markers_count = timeline_repo.get_markers_count(project_id)

            # Contar tipos de eventos
            anchor_count = sum(1 for e in events if e.story_date_resolution in ("EXACT_DATE", "MONTH", "YEAR"))
            analepsis_count = sum(1 for e in events if e.narrative_order == "ANALEPSIS")
            prolepsis_count = sum(1 for e in events if e.narrative_order == "PROLEPSIS")

            # Convertir a formato esperado por el frontend
            events_data = [e.to_dict() for e in events]

            logger.info(f"Timeline loaded from DB for project {project_id}: {len(events)} events (total: {total_count})")

            return ApiResponse(
                success=True,
                data={
                    "events": events_data,
                    "markers_count": markers_count,
                    "anchor_count": anchor_count,
                    "analepsis_count": analepsis_count,
                    "prolepsis_count": prolepsis_count,
                    "time_span": None,  # No disponible desde BD
                    "mermaid": None,  # No disponible desde BD
                    "inconsistencies": [],  # Las inconsistencias están en alerts
                    "from_cache": True,
                    "truncated": truncated,
                    "total_events": total_count,
                },
                message="Timeline cargado desde base de datos"
            )

        # Si no hay datos en BD o se fuerza refresh, calcular
        chapters = deps.chapter_repository.get_by_project(project_id)

        if not chapters:
            return ApiResponse(
                success=True,
                data={
                    "events": [],
                    "markers_count": 0,
                    "anchor_count": 0,
                    "time_span": None,
                    "mermaid": "No hay capítulos para analizar.",
                    "inconsistencies": [],
                },
                message="El proyecto no tiene capítulos para analizar"
            )

        # Importar módulo temporal
        from narrative_assistant.temporal import (
            TemporalConsistencyChecker,
            TemporalMarkerExtractor,
            TimelineBuilder,
        )
        from narrative_assistant.temporal.entity_mentions import load_entity_mentions_by_chapter

        # Extraer marcadores temporales
        marker_extractor = TemporalMarkerExtractor()
        all_markers = []

        # Cargar menciones de personajes por capítulo para asociar edades y
        # construir temporal_instance_id (A@40, A@45) desde el extractor.
        entity_mentions_by_chapter: dict[int, list[tuple[int, int, int]]] = {}
        try:
            if deps.entity_repository:
                entities = deps.entity_repository.get_entities_by_project(
                    project_id, active_only=True,
                )
                entity_mentions_by_chapter = load_entity_mentions_by_chapter(
                    entities, chapters, deps.entity_repository,
                )
        except Exception as e:
            logger.debug(f"Could not load entity mentions for temporal extraction: {e}")

        for chapter in chapters:
            chapter_mentions = entity_mentions_by_chapter.get(chapter.chapter_number, [])
            if chapter_mentions:
                chapter_markers = marker_extractor.extract_with_entities(
                    text=chapter.content,
                    entity_mentions=chapter_mentions,
                    chapter=chapter.chapter_number,
                )
            else:
                chapter_markers = marker_extractor.extract(
                    text=chapter.content,
                    chapter=chapter.chapter_number,
                )
            all_markers.extend(chapter_markers)
            logger.debug(f"Chapter {chapter.chapter_number}: {len(chapter_markers)} markers, text length: {len(chapter.content)}")

        logger.info(f"Timeline extraction: {len(chapters)} chapters, {len(all_markers)} total markers")

        # Construir timeline (con contenido para análisis lingüístico)
        builder = TimelineBuilder()
        chapter_data = [
            {
                "number": ch.chapter_number,
                "title": ch.title or f"Capítulo {ch.chapter_number}",
                "start_position": ch.start_char,
                "content": ch.content,
            }
            for ch in chapters
        ]

        timeline = builder.build_from_markers(all_markers, chapter_data)

        # Verificar consistencia
        checker = TemporalConsistencyChecker()
        inconsistencies = checker.check(timeline, all_markers)

        # Exportar datos
        json_data = builder.export_to_json()
        mermaid = builder.export_to_mermaid()

        # Persistir timeline si se calculó
        try:
            from narrative_assistant.persistence.timeline import (
                TemporalMarkerData,
                TimelineEventData,
            )

            events_data = []
            for event in timeline.events:
                story_date_str = event.story_date.isoformat() if event.story_date else None
                events_data.append(TimelineEventData(
                    id=None,
                    project_id=project_id,
                    event_id=event.id,
                    chapter=event.chapter,
                    paragraph=event.paragraph,
                    description=event.description,
                    story_date=story_date_str,
                    story_date_resolution=event.story_date_resolution.value if event.story_date_resolution else "UNKNOWN",
                    narrative_order=event.narrative_order.value if event.narrative_order else "CHRONOLOGICAL",
                    discourse_position=event.discourse_position,
                    confidence=event.confidence,
                    # Importante: estos campos deben persistirse para que el timeline
                    # cacheado en BD conserve exactamente la semántica temporal de memoria.
                    # Si se omiten, al leer desde caché se pierden Día 0/dayOffset y la
                    # instancia temporal (A@40 vs A@45), generando inconsistencias de UI/lógica.
                    day_offset=event.day_offset,
                    weekday=event.weekday,
                    temporal_instance_id=event.temporal_instance_id,
                ))

            markers_data = []
            for marker in all_markers:
                markers_data.append(TemporalMarkerData(
                    id=None,
                    project_id=project_id,
                    chapter=marker.chapter,
                    marker_type=marker.marker_type.value if hasattr(marker.marker_type, 'value') else str(marker.marker_type),
                    text=marker.text,
                    start_char=marker.start_char,
                    end_char=marker.end_char,
                    confidence=marker.confidence,
                    year=marker.year,
                    month=marker.month,
                    day=marker.day,
                    direction=marker.direction.value if hasattr(marker, 'direction') and marker.direction and hasattr(marker.direction, 'value') else getattr(marker, 'direction', None),
                    quantity=getattr(marker, 'quantity', None),
                    magnitude=getattr(marker, 'magnitude', None),
                    age=getattr(marker, 'age', None),
                    entity_id=getattr(marker, 'entity_id', None),
                ))

            timeline_repo.save_events(project_id, events_data)
            timeline_repo.save_markers(project_id, markers_data)
            logger.info(f"Timeline persisted for project {project_id}")
        except Exception as e:
            logger.warning(f"Failed to persist timeline: {e}")

        # Formatear inconsistencias
        inconsistencies_data = [
            {
                "type": inc.inconsistency_type.value,
                "severity": inc.severity.value,
                "description": inc.description,
                "chapter": inc.chapter,
                "expected": inc.expected,
                "found": inc.found,
                "suggestion": inc.suggestion,
                "confidence": inc.confidence,
            }
            for inc in inconsistencies
        ]

        all_events = json_data["events"]
        total_events = len(all_events)
        truncated = total_events > MAX_TIMELINE_EVENTS
        if truncated:
            all_events = all_events[:MAX_TIMELINE_EVENTS]

        return ApiResponse(
            success=True,
            data={
                "events": all_events,
                "markers_count": len(all_markers),
                "anchor_count": json_data["anchor_events"],
                "analepsis_count": json_data["analepsis_count"],
                "prolepsis_count": json_data["prolepsis_count"],
                "time_span": json_data["time_span"],
                "mermaid": mermaid,
                "inconsistencies": inconsistencies_data,
                "from_cache": False,
                "truncated": truncated,
                "total_events": total_events,
            }
        )

    except HTTPException:
        raise
    except ImportError as e:
        logger.error(f"Temporal module not available: {e}")
        return ApiResponse(
            success=False,
            error="Módulo de análisis temporal no disponible"
        )
    except Exception as e:
        logger.error(f"Error getting timeline for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/temporal-markers", response_model=ApiResponse)
def get_temporal_markers(project_id: int, chapter_number: Optional[int] = Query(None, description="Filtrar por número de capítulo")):
    """
    Obtiene los marcadores temporales detectados en el proyecto.

    Args:
        project_id: ID del proyecto
        chapter_number: Filtrar por número de capítulo (opcional)

    Returns:
        ApiResponse con lista de marcadores temporales
    """
    try:
        if not deps.chapter_repository:
            return ApiResponse(success=False, error="Chapter repository not initialized")

        # Obtener capítulos
        chapters = deps.chapter_repository.get_by_project(project_id)

        if chapter_number is not None:
            chapters = [ch for ch in chapters if ch.chapter_number == chapter_number]

        if not chapters:
            return ApiResponse(
                success=True,
                data=[],
                message="No se encontraron capítulos"
            )

        # Importar y extraer marcadores
        from narrative_assistant.temporal import TemporalMarkerExtractor

        extractor = TemporalMarkerExtractor()
        all_markers = []

        for ch in chapters:
            markers = extractor.extract(ch.content, chapter=ch.chapter_number)
            for m in markers:
                all_markers.append({
                    "text": m.text,
                    "type": m.marker_type.value,
                    "chapter": m.chapter,
                    "start_char": m.start_char,
                    "end_char": m.end_char,
                    "direction": m.direction,
                    "magnitude": m.magnitude,
                    "quantity": m.quantity,
                    "age": m.age,
                    "year": m.year,
                    "month": m.month,
                    "day": m.day,
                    "confidence": m.confidence,
                })

        return ApiResponse(success=True, data=all_markers)

    except Exception as e:
        logger.error(f"Error getting temporal markers: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/chapters/{chapter_number}/emotional-analysis", response_model=ApiResponse)
def get_chapter_emotional_analysis(project_id: int, chapter_number: int):
    """
    Obtiene el análisis emocional de un capítulo específico.
    """
    try:
        from narrative_assistant.analysis.emotional_coherence import (
            get_emotional_coherence_checker,
        )
        from narrative_assistant.nlp.dialogue import detect_dialogues

        # Obtener el capítulo
        chapter = deps.chapter_repository.get_chapter(project_id, chapter_number)  # type: ignore[attr-defined]
        if not chapter:
            return ApiResponse(
                success=False,
                error=f"Capítulo {chapter_number} no encontrado"
            )

        # Obtener personajes
        entities = deps.entity_repository.get_entities_by_project(project_id)  # type: ignore[attr-defined]
        character_names = [
            e.canonical_name for e in entities if deps.is_character_entity(e)
        ]

        # Extraer diálogos
        dialogue_result = detect_dialogues(chapter.content)
        if dialogue_result.is_success:
            dialogues = [
                (
                    d.speaker_hint or "desconocido",
                    d.text,
                    d.start_char,
                    d.end_char,
                )
                for d in dialogue_result.value.dialogues  # type: ignore[union-attr]
            ]
        else:
            dialogues = []

        # Analizar
        checker = get_emotional_coherence_checker()
        incoherences = checker.analyze_chapter(
            chapter_text=chapter.content,
            entity_names=character_names,
            dialogues=dialogues,
            chapter_id=chapter_number,
        )

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "chapter_number": chapter_number,
                "incoherences": [inc.to_dict() for inc in incoherences],
                "dialogues_analyzed": len(dialogues),
                "characters_checked": len(character_names),
            }
        )

    except ImportError as e:
        logger.error(f"Module import error: {e}")
        return ApiResponse(
            success=False,
            error="Módulo de análisis emocional no disponible"
        )
    except Exception as e:
        logger.error(f"Error in chapter emotional analysis: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/chapters/{chapter_number}/register-analysis", response_model=ApiResponse)
def get_chapter_register_analysis(
    project_id: int,
    chapter_number: int,
    min_severity: str = Query("low", description="Severidad mínima: low, medium, high")
):
    """
    Analiza el registro narrativo de un capítulo específico.

    Devuelve análisis detallado con segmentos, cambios y resumen
    para un solo capítulo.

    Returns:
        ApiResponse con análisis de registro del capítulo
    """
    try:
        from narrative_assistant.nlp.dialogue import detect_dialogues
        from narrative_assistant.persistence.chapter import get_chapter_repository
        from narrative_assistant.voice.register import (
            RegisterChangeDetector,
        )

        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)
        chapter = next((c for c in chapters if c.chapter_number == chapter_number), None)

        if not chapter:
            raise HTTPException(status_code=404, detail=f"Capítulo {chapter_number} no encontrado")

        # Detect dialogues
        dialogue_result = detect_dialogues(chapter.content)
        dialogue_ranges = []
        if dialogue_result.is_success:
            dialogue_ranges = [
                (d.start_char, d.end_char)
                for d in dialogue_result.value.dialogues
            ]

        # Segment by paragraph
        segments = []
        paragraphs = chapter.content.split('\n\n')
        position = 0

        for para in paragraphs:
            if para.strip():
                is_dialogue = any(
                    start <= position <= end
                    for start, end in dialogue_ranges
                )
                segments.append((
                    para.strip(),
                    chapter.chapter_number,
                    position,
                    is_dialogue
                ))
            position += len(para) + 2

        if not segments:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "chapter_number": chapter_number,
                    "analyses": [],
                    "changes": [],
                    "summary": {},
                }
            )

        # Analyze
        detector = RegisterChangeDetector()
        analyses = detector.analyze_document(segments)
        changes = detector.detect_changes(min_severity)
        summary = detector.get_summary()

        # Per-chapter register distribution
        register_counts: dict[str, int] = {}
        narrative_count = 0
        dialogue_count = 0
        for i, a in enumerate(analyses):
            reg = a.primary_register.value
            register_counts[reg] = register_counts.get(reg, 0) + 1
            if segments[i][3]:
                dialogue_count += 1
            else:
                narrative_count += 1

        # Dominant register
        dominant = max(register_counts, key=register_counts.get) if register_counts else "neutral"

        # Consistency: % of segments with the dominant register
        total_segs = len(analyses)
        consistency = (register_counts.get(dominant, 0) / total_segs * 100) if total_segs > 0 else 100

        analyses_data = [
            {
                "segment_index": i,
                "chapter": segments[i][1],
                "is_dialogue": segments[i][3],
                "primary_register": a.primary_register.value,
                "register_scores": {k.value: v for k, v in a.register_scores.items()},
                "confidence": a.confidence,
                "formal_indicators": list(a.formal_indicators)[:5],
                "colloquial_indicators": list(a.colloquial_indicators)[:5],
            }
            for i, a in enumerate(analyses)
        ]

        changes_data = [
            {
                "from_register": c.from_register.value,
                "to_register": c.to_register.value,
                "severity": c.severity,
                "explanation": c.explanation,
                "chapter": c.chapter,
                "position": c.position,
                "context_before": c.context_before[:100] if c.context_before else "",
                "context_after": c.context_after[:100] if c.context_after else "",
            }
            for c in changes
        ]

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "chapter_number": chapter_number,
                "chapter_title": getattr(chapter, 'title', '') or '',
                "analyses": analyses_data,
                "changes": changes_data,
                "summary": {
                    **summary,
                    "dominant_register": dominant,
                    "consistency_pct": round(consistency, 1),
                    "register_distribution": register_counts,
                    "narrative_segments": narrative_count,
                    "dialogue_segments": dialogue_count,
                },
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing chapter register: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/chapters/{chapter_number}/dialogue-attributions", response_model=ApiResponse)
def get_dialogue_attributions(project_id: int, chapter_number: int):
    """
    Obtiene atribución de hablantes para los diálogos de un capítulo.

    Utiliza múltiples estrategias para identificar quién habla cada diálogo:
    - Detección explícita (verbo de habla + nombre)
    - Alternancia (patrón A-B-A-B)
    - Perfil de voz (comparación estilística)
    - Proximidad (entidad mencionada cerca)

    Returns:
        ApiResponse con atribuciones de diálogos y estadísticas
    """
    try:
        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.nlp.dialogue import detect_dialogues
        from narrative_assistant.persistence.chapter import get_chapter_repository
        from narrative_assistant.voice.profiles import VoiceProfileBuilder
        from narrative_assistant.voice.speaker_attribution import SpeakerAttributor

        # Verificar proyecto
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        # Obtener capítulo específico
        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)
        chapter = next((c for c in chapters if c.chapter_number == chapter_number), None)

        if not chapter:
            raise HTTPException(status_code=404, detail=f"Capítulo {chapter_number} no encontrado")

        # Obtener entidades (personajes)
        entity_repo = get_entity_repository()
        entities = entity_repo.get_entities_by_project(project_id, active_only=True)
        characters = [e for e in entities if deps.is_character_entity(e)]

        # Obtener menciones de entidades en el capítulo
        entity_mentions = []
        for entity in characters:
            mentions = entity_repo.get_mentions_by_entity(entity.id)
            for m in mentions:
                if m.chapter_id == chapter.id:
                    entity_mentions.append((entity.id, m.start_char, m.end_char))

        # Detectar diálogos
        dialogue_result = detect_dialogues(chapter.content)
        if dialogue_result.is_failure:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "chapter_number": chapter_number,
                    "attributions": [],
                    "stats": {},
                    "message": "No se pudieron detectar diálogos"
                }
            )

        dialogues = dialogue_result.value.dialogues
        if not dialogues:
            return ApiResponse(
                success=True,
                data={
                    "project_id": project_id,
                    "chapter_number": chapter_number,
                    "attributions": [],
                    "stats": {},
                    "message": "No hay diálogos en este capítulo"
                }
            )

        # Preparar datos de entidades para el atribuidor
        entity_data = [
            type('Entity', (), {
                'id': e.id,
                'canonical_name': e.canonical_name,
                'aliases': e.aliases or []
            })()
            for e in characters
        ]

        # Construir perfiles de voz (opcional, mejora precisión)
        voice_profiles = None
        try:
            # Obtener todos los diálogos del proyecto para perfiles
            all_dialogues = []
            for ch in chapters:
                ch_dialogue_result = detect_dialogues(ch.content)
                if ch_dialogue_result.is_success:
                    for d in ch_dialogue_result.value.dialogues:
                        all_dialogues.append({
                            "text": d.text,
                            "speaker_id": d.speaker_id,
                            "chapter": ch.chapter_number,
                            "position": d.start_char,
                        })

            if all_dialogues:
                entity_dict_data = [
                    {"id": e.id, "name": e.canonical_name, "aliases": e.aliases}
                    for e in characters
                ]
                builder = VoiceProfileBuilder()
                profiles = builder.build_profiles(all_dialogues, entity_dict_data)
                voice_profiles = {p.entity_id: p for p in profiles}
        except Exception as e:
            logger.warning(f"Could not build voice profiles: {e}")

        # Atribuir hablantes
        attributor = SpeakerAttributor(entity_data, voice_profiles)
        attributions = attributor.attribute_dialogues(
            dialogues, entity_mentions, chapter.content
        )
        stats = attributor.get_attribution_stats(attributions)

        # Serializar atribuciones
        attributions_data = [
            {
                "dialogue_index": i,
                "text": dialogues[i].text[:100] + "..." if len(dialogues[i].text) > 100 else dialogues[i].text,
                "start_char": dialogues[i].start_char,
                "end_char": dialogues[i].end_char,
                "speaker_id": attr.speaker_id,
                "speaker_name": attr.speaker_name,
                "confidence": attr.confidence.value,
                "method": attr.attribution_method.value,
                "speech_verb": attr.speech_verb,
                "alternatives": [
                    {"id": alt[0], "name": alt[1], "score": alt[2]}
                    for alt in (attr.alternative_speakers or [])[:3]
                ],
            }
            for i, attr in enumerate(attributions)
        ]

        # Aplicar correcciones del usuario (override con máxima confianza)
        try:
            from narrative_assistant.persistence.database import get_database
            db = get_database()
            corrections = db.fetchall(
                """
                SELECT sc.dialogue_start_char, sc.dialogue_end_char,
                       sc.corrected_speaker_id, e.name as corrected_speaker_name
                FROM speaker_corrections sc
                JOIN entities e ON e.id = sc.corrected_speaker_id
                WHERE sc.project_id = ? AND sc.chapter_number = ?
                """,
                (project_id, chapter_number),
            )

            corr_map = {
                (c["dialogue_start_char"], c["dialogue_end_char"]): c
                for c in corrections
            }
            for attr_data in attributions_data:
                key = (attr_data["start_char"], attr_data["end_char"])
                if key in corr_map:
                    corr = corr_map[key]
                    attr_data["speaker_id"] = corr["corrected_speaker_id"]
                    attr_data["speaker_name"] = corr["corrected_speaker_name"]
                    attr_data["confidence"] = "high"
                    attr_data["method"] = "user_correction"
        except Exception as e:
            logger.debug(f"Could not apply speaker corrections: {e}")

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "chapter_number": chapter_number,
                "attributions": attributions_data,
                "stats": stats,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error attributing speakers: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/chapters/{chapter_number}/focalization/suggest", response_model=ApiResponse)
def suggest_chapter_focalization(project_id: int, chapter_number: int):
    """Sugiere la focalización más probable para un capítulo."""
    try:
        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.focalization import (  # type: ignore[attr-defined]
            FocalizationDeclarationService,
            SQLiteFocalizationRepository,
        )
        from narrative_assistant.persistence.chapter import get_chapter_repository

        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)
        chapter = next((c for c in chapters if c.chapter_number == chapter_number), None)

        if not chapter:
            raise HTTPException(status_code=404, detail=f"Capítulo {chapter_number} no encontrado")

        entity_repo = get_entity_repository()
        entities = entity_repo.get_entities_by_project(project_id, active_only=True)
        characters = [e for e in entities if deps.is_character_entity(e)]

        repo = SQLiteFocalizationRepository()
        service = FocalizationDeclarationService(repository=repo)
        suggestion = service.suggest_focalization(project_id, chapter_number, chapter.content, characters)

        focalizer_names = []
        for fid in suggestion.get("suggested_focalizers", []):
            entity = next((e for e in characters if e.id == fid), None)
            if entity:
                focalizer_names.append({"id": fid, "name": entity.canonical_name or entity.name})

        return ApiResponse(
            success=True,
            data={
                "chapter_number": chapter_number,
                "chapter_title": chapter.title or f"Capítulo {chapter_number}",
                "suggested_type": suggestion["suggested_type"].value if suggestion["suggested_type"] else None,
                "suggested_focalizers": focalizer_names,
                "confidence": suggestion["confidence"],
                "evidence": suggestion["evidence"],
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error suggesting focalization: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/{project_id}/focalization/suggest-all", response_model=ApiResponse)
def suggest_all_focalizations(project_id: int, auto_apply: bool = False):
    """
    Sugiere focalizacion para todos los capitulos sin declaracion.

    Si auto_apply=True, aplica automaticamente sugerencias con confianza >= 0.65.
    """
    try:
        from narrative_assistant.entities.repository import get_entity_repository
        from narrative_assistant.focalization import (  # type: ignore[attr-defined]
            FocalizationDeclarationService,
            SQLiteFocalizationRepository,
        )
        from narrative_assistant.persistence.chapter import get_chapter_repository

        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        chapter_repo = get_chapter_repository()
        chapters = chapter_repo.get_by_project(project_id)
        entity_repo = get_entity_repository()
        entities = entity_repo.get_entities_by_project(project_id, active_only=True)
        characters = [e for e in entities if deps.is_character_entity(e)]

        repo = SQLiteFocalizationRepository()
        service = FocalizationDeclarationService(repository=repo)

        # Obtener declaraciones existentes
        existing = service.get_all_declarations(project_id)
        declared_chapters = {d.chapter for d in existing}

        suggestions = []
        applied = 0

        for chapter in chapters:
            if chapter.chapter_number in declared_chapters:
                continue
            if not chapter.content or len(chapter.content.strip()) < 50:
                continue

            suggestion = service.suggest_focalization(
                project_id, chapter.chapter_number, chapter.content, characters
            )

            focalizer_names = []
            for fid in suggestion.get("suggested_focalizers", []):
                entity = next((e for e in characters if e.id == fid), None)
                if entity:
                    focalizer_names.append({"id": fid, "name": entity.canonical_name or entity.name})

            sug_data = {
                "chapter_number": chapter.chapter_number,
                "chapter_title": chapter.title or f"Capítulo {chapter.chapter_number}",
                "suggested_type": suggestion["suggested_type"].value if suggestion["suggested_type"] else None,
                "suggested_focalizers": focalizer_names,
                "confidence": suggestion["confidence"],
                "evidence": suggestion["evidence"],
                "applied": False,
            }

            # Auto-aplicar si confianza suficiente
            if auto_apply and suggestion["suggested_type"] and suggestion["confidence"] >= 0.65:
                try:
                    service.declare_focalization(
                        project_id=project_id,
                        chapter=chapter.chapter_number,
                        focalization_type=suggestion["suggested_type"],
                        focalizer_ids=suggestion.get("suggested_focalizers", []),
                        declared_by="system_suggestion",
                        notes=f"Auto-sugerido (confianza: {suggestion['confidence']:.0%})",
                    )
                    sug_data["applied"] = True
                    applied += 1
                except Exception as e:
                    logger.warning(f"Error applying suggestion for ch {chapter.chapter_number}: {e}")

            suggestions.append(sug_data)

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "suggestions": suggestions,
                "total_chapters": len(chapters),
                "already_declared": len(declared_chapters),
                "suggested": len(suggestions),
                "auto_applied": applied,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error suggesting all focalizations: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/chapters/{chapter_number}/scenes", response_model=ApiResponse)
def get_chapter_scenes(project_id: int, chapter_number: int):
    """Obtiene las escenas de un capítulo específico."""
    try:
        from narrative_assistant.scenes import SceneService

        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail=f"Proyecto {project_id} no encontrado")

        service = SceneService()
        scenes = service.get_scenes_by_chapter(project_id, chapter_number)

        return ApiResponse(
            success=True,
            data={
                "project_id": project_id,
                "chapter_number": chapter_number,
                "scenes": [
                    {
                        "id": s.scene.id,
                        "scene_number": s.scene.scene_number,
                        "start_char": s.scene.start_char,
                        "end_char": s.scene.end_char,
                        "word_count": s.scene.word_count,
                        "excerpt": s.excerpt,
                        "tags": {
                            "scene_type": s.tags.scene_type.value if s.tags and s.tags.scene_type else None,
                            "tone": s.tags.tone.value if s.tags and s.tags.tone else None,
                            "location_name": s.location_name,
                            "participant_names": s.participant_names,
                            "summary": s.tags.summary if s.tags else None,
                        } if s.tags else None,
                        "custom_tags": [ct.tag_name for ct in s.custom_tags],
                    }
                    for s in scenes
                ],
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chapter scenes: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")
