"""
Router: exports
"""

from pathlib import Path
from typing import Any, Optional

import deps
from deps import ApiResponse, _estimate_export_pages, logger
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

@router.get("/api/projects/{project_id}/export/document")
def export_document(
    project_id: int,
    format: str = "docx",
    include_characters: bool = True,
    include_alerts: bool = True,
    include_timeline: bool = True,
    include_relationships: bool = True,
    include_style_guide: bool = True,
    only_main_characters: bool = True,
    only_open_alerts: bool = True,
):
    """
    Exporta el proyecto completo a DOCX o PDF.

    Genera un documento profesional con:
    - Portada con titulo del proyecto
    - Indice automatico
    - Fichas de personajes
    - Alertas/errores encontrados
    - Timeline narrativo
    - Grafo de relaciones
    - Guia de estilo

    Args:
        project_id: ID del proyecto
        format: Formato de exportacion ('docx' o 'pdf')
        include_characters: Incluir fichas de personajes
        include_alerts: Incluir alertas/errores
        include_timeline: Incluir linea temporal
        include_relationships: Incluir relaciones
        include_style_guide: Incluir guia de estilo
        only_main_characters: Solo personajes principales
        only_open_alerts: Solo alertas abiertas

    Returns:
        Archivo DOCX o PDF para descarga
    """
    from fastapi.responses import Response

    try:
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        # Validar formato
        format = format.lower()
        if format not in ("docx", "pdf"):
            return ApiResponse(success=False, error="Formato invalido. Use 'docx' o 'pdf'")

        # Importar exportador
        try:
            from narrative_assistant.exporters.document_exporter import (
                DocumentExporter,
                ExportOptions,
                collect_export_data,
            )
        except ImportError as e:
            logger.error(f"Document exporter not available: {e}")
            return ApiResponse(
                success=False,
                error="Modulo de exportacion de documentos no disponible"
            )

        # Configurar opciones
        options = ExportOptions(
            include_cover=True,
            include_toc=True,
            include_character_sheets=include_characters,
            include_alerts=include_alerts,
            include_timeline=include_timeline,
            include_relationships=include_relationships,
            include_style_guide=include_style_guide,
            include_statistics=True,
            only_main_characters=only_main_characters,
            only_open_alerts=only_open_alerts,
        )

        # Recopilar datos del proyecto
        data_result = collect_export_data(
            project_id=project_id,
            project_manager=deps.project_manager,
            entity_repository=deps.entity_repository,
            alert_repository=deps.alert_repository,
            chapter_repository=deps.chapter_repository,
            options=options,
        )

        if data_result.is_failure:
            return ApiResponse(success=False, error=str(data_result.error))

        export_data = data_result.value

        # Crear exportador
        exporter = DocumentExporter()

        # Exportar segun formato
        if format == "docx":
            result = exporter.export_to_docx(export_data, options)
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            extension = "docx"
        else:
            result = exporter.export_to_pdf(export_data, options)
            content_type = "application/pdf"
            extension = "pdf"

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        # Generar nombre de archivo
        safe_name = "".join(
            c if c.isalnum() or c in (' ', '-', '_') else '_'
            for c in export_data.project_name
        ).strip().replace(' ', '_').lower()

        filename = f"informe_{safe_name}.{extension}"

        # Devolver archivo para descarga
        return Response(
            content=result.value,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\""
            }
        )

    except Exception as e:
        logger.error(f"Error exporting document for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/export/document/preview", response_model=ApiResponse)
def preview_document_export(
    project_id: int,
    include_characters: bool = True,
    include_alerts: bool = True,
    include_timeline: bool = True,
    include_relationships: bool = True,
    include_style_guide: bool = True,
    only_main_characters: bool = True,
    only_open_alerts: bool = True,
):
    """
    Previsualiza los datos que se incluiran en la exportacion.

    Util para mostrar al usuario que se va a exportar antes de generar el documento.

    Args:
        project_id: ID del proyecto
        include_characters: Incluir fichas de personajes
        include_alerts: Incluir alertas/errores
        include_timeline: Incluir linea temporal
        include_relationships: Incluir relaciones
        include_style_guide: Incluir guia de estilo
        only_main_characters: Solo personajes principales
        only_open_alerts: Solo alertas abiertas

    Returns:
        ApiResponse con preview de los datos a exportar
    """
    try:
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        try:
            from narrative_assistant.exporters.document_exporter import (
                ExportOptions,
                collect_export_data,
            )
        except ImportError:
            return ApiResponse(success=False, error="Modulo de exportacion no disponible")

        options = ExportOptions(
            include_cover=True,
            include_toc=True,
            include_character_sheets=include_characters,
            include_alerts=include_alerts,
            include_timeline=include_timeline,
            include_relationships=include_relationships,
            include_style_guide=include_style_guide,
            include_statistics=True,
            only_main_characters=only_main_characters,
            only_open_alerts=only_open_alerts,
        )

        data_result = collect_export_data(
            project_id=project_id,
            project_manager=deps.project_manager,
            entity_repository=deps.entity_repository,
            alert_repository=deps.alert_repository,
            chapter_repository=deps.chapter_repository,
            options=options,
        )

        if data_result.is_failure:
            return ApiResponse(success=False, error=str(data_result.error))

        export_data = data_result.value

        return ApiResponse(
            success=True,
            data={
                "project_name": export_data.project_name,
                "description": export_data.description,
                "sections": {
                    "statistics": {
                        "included": True,
                        "word_count": export_data.word_count,
                        "chapter_count": export_data.chapter_count,
                        "entity_count": export_data.entity_count,
                        "alert_count": export_data.alert_count,
                    },
                    "characters": {
                        "included": include_characters,
                        "count": len(export_data.characters),
                        "names": [c.get("canonical_name", "") for c in export_data.characters[:10]],
                    },
                    "alerts": {
                        "included": include_alerts,
                        "count": len(export_data.alerts),
                        "by_severity": {
                            "critical": len([a for a in export_data.alerts if a.get("severity") == "critical"]),
                            "error": len([a for a in export_data.alerts if a.get("severity") == "error"]),
                            "warning": len([a for a in export_data.alerts if a.get("severity") == "warning"]),
                            "info": len([a for a in export_data.alerts if a.get("severity") == "info"]),
                        }
                    },
                    "timeline": {
                        "included": include_timeline,
                        "event_count": len(export_data.timeline_events),
                    },
                    "relationships": {
                        "included": include_relationships,
                        "count": len(export_data.relationships),
                    },
                    "style_guide": {
                        "included": include_style_guide,
                        "available": export_data.style_guide is not None,
                    }
                },
                "estimated_pages": _estimate_export_pages(export_data),
            }
        )

    except Exception as e:
        logger.error(f"Error previewing document export: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/export/corrected")
def export_corrected_document(
    project_id: int,
    min_confidence: float = 0.5,
    categories: Optional[str] = None,
    as_track_changes: bool = True,
):
    """
    Exporta el documento original con correcciones como Track Changes.

    A diferencia de /export/document que genera un informe, este endpoint
    devuelve el documento original con las correcciones aplicadas como
    revisiones de Word que el autor puede aceptar/rechazar.

    Args:
        project_id: ID del proyecto
        min_confidence: Confianza mínima para incluir correcciones (0.0-1.0)
        categories: Categorías a incluir (separadas por coma), None = todas
        as_track_changes: Si True, aplica como Track Changes; si False, aplica directamente

    Returns:
        Archivo DOCX con correcciones aplicadas
    """
    from fastapi.responses import Response

    try:
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        # Obtener proyecto
        result = deps.project_manager.get(project_id)
        if result.is_failure:
            return ApiResponse(success=False, error=f"Proyecto {project_id} no encontrado")
        project = result.value

        # Verificar que es un documento Word
        if not project.source_path:
            return ApiResponse(
                success=False,
                error="El proyecto no tiene documento fuente asociado"
            )

        source_path = Path(project.source_path)
        if not source_path.exists():
            return ApiResponse(
                success=False,
                error=f"El documento fuente no existe: {source_path}"
            )

        if source_path.suffix.lower() != ".docx":
            return ApiResponse(
                success=False,
                error="Solo se admiten archivos .docx para exportación con Track Changes"
            )

        # Importar exportador
        try:
            from narrative_assistant.corrections.base import CorrectionIssue
            from narrative_assistant.exporters.corrected_document_exporter import (
                CorrectedDocumentExporter,
                TrackChangeOptions,
            )
        except ImportError as e:
            logger.error(f"Corrected document exporter not available: {e}")
            return ApiResponse(
                success=False,
                error="Módulo de exportación de correcciones no disponible"
            )

        # Obtener correcciones del proyecto
        corrections = []

        # Buscar correcciones almacenadas en alertas
        if deps.alert_repository:
            alerts = deps.alert_repository.get_by_project(project_id)
            correction_categories = {
                "typography", "repetition", "agreement", "terminology",
                "regional", "clarity", "grammar"
            }

            for alert in alerts:
                # Solo incluir alertas de corrección con sugerencia
                if alert.category.value.lower() in correction_categories and alert.suggestion:
                    corrections.append(CorrectionIssue(
                        category=alert.category.value.lower(),
                        issue_type=alert.alert_type or "unknown",
                        start_char=alert.start_char or 0,
                        end_char=alert.end_char or 0,
                        text=alert.excerpt or "",
                        explanation=alert.description,
                        suggestion=alert.suggestion,
                        confidence=alert.confidence,
                        context=alert.excerpt or "",
                        chapter_index=alert.chapter,
                        rule_id=None,
                        extra_data={},
                    ))

        if not corrections:
            return ApiResponse(
                success=False,
                error="No hay correcciones para aplicar. Ejecute primero el análisis de correcciones."
            )

        # Parsear categorías
        category_list = None
        if categories:
            category_list = [c.strip().lower() for c in categories.split(",")]

        # Configurar opciones
        options = TrackChangeOptions(
            author="Narrative Assistant",
            include_comments=True,
            min_confidence=min_confidence,
            categories=category_list,
            as_track_changes=as_track_changes,
        )

        # Exportar
        exporter = CorrectedDocumentExporter()
        result = exporter.export(source_path, corrections, options)

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        # Generar nombre de archivo
        safe_name = source_path.stem
        filename = f"{safe_name}_corregido.docx"

        # Devolver archivo
        return Response(
            content=result.value,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\""
            }
        )

    except Exception as e:
        logger.error(f"Error exporting corrected document for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/export/review-report")
def export_review_report(
    project_id: int,
    format: str = "docx",
    min_confidence: float = 0.0,
    include_context: bool = True,
    include_suggestions: bool = True,
    max_issues_per_category: int = 50,
):
    """
    Exporta un informe de revisión editorial a DOCX o PDF.

    Genera un informe detallado con estadísticas de los problemas
    detectados por los 14 detectores de corrección.

    Incluye:
    - Resumen ejecutivo con totales por categoría
    - Distribución por confianza
    - Desglose por capítulo
    - Listado detallado de observaciones
    - Recomendaciones de estilo

    Args:
        project_id: ID del proyecto
        format: Formato de exportación ('docx' o 'pdf')
        min_confidence: Confianza mínima para incluir (0.0-1.0)
        include_context: Incluir contexto de cada observación
        include_suggestions: Incluir sugerencias de corrección
        max_issues_per_category: Máximo de observaciones por categoría

    Returns:
        Archivo DOCX o PDF para descarga
    """
    from fastapi.responses import Response

    try:
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        # Validar formato
        format = format.lower()
        if format not in ("docx", "pdf"):
            return ApiResponse(success=False, error="Formato inválido. Use 'docx' o 'pdf'")

        # Obtener proyecto
        result = deps.project_manager.get(project_id)
        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        project = result.value

        # Importar módulos necesarios
        try:
            from narrative_assistant.corrections.base import CorrectionIssue
            from narrative_assistant.exporters.review_report_exporter import (
                ReviewReportExporter,
                ReviewReportOptions,
            )
        except ImportError as e:
            logger.error(f"Review report exporter not available: {e}")
            return ApiResponse(
                success=False,
                error="Módulo de informes de revisión no disponible"
            )

        # Obtener alertas del proyecto que son de tipo correction
        correction_categories = {
            "typography", "repetition", "agreement", "punctuation",
            "terminology", "regional", "clarity", "grammar",
            "anglicisms", "crutch_words", "glossary", "anacoluto",
            "pov", "orthography"
        }

        # Convertir alertas a CorrectionIssue
        issues = []
        if deps.alert_repository:
            alerts = deps.alert_repository.get_by_project(project_id)
            for alert in alerts:
                category = alert.category.value.lower() if hasattr(alert.category, 'value') else str(alert.category).lower()
                if category in correction_categories:
                    issues.append(CorrectionIssue(
                        category=category,
                        issue_type=alert.alert_type or "unknown",
                        start_char=0,
                        end_char=0,
                        text=alert.excerpt or "",
                        explanation=alert.explanation or alert.description or "",
                        suggestion=alert.suggestion,
                        confidence=alert.confidence or 0.5,
                        context=alert.excerpt or "",
                        chapter_index=alert.chapter,
                        rule_id=None,
                    ))

        if not issues:
            return ApiResponse(
                success=False,
                error="No hay observaciones de corrección para generar el informe. Ejecute primero el análisis del documento."
            )

        # Configurar opciones
        options = ReviewReportOptions(
            document_title=project.name,
            min_confidence=min_confidence,
            include_context=include_context,
            include_suggestions=include_suggestions,
            max_issues_per_category=max_issues_per_category,
        )

        # Crear exportador
        exporter = ReviewReportExporter()

        # Exportar según formato
        if format == "docx":
            result = exporter.export_to_docx(issues, options)
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            extension = "docx"
        else:
            result = exporter.export_to_pdf(issues, options)
            content_type = "application/pdf"
            extension = "pdf"

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        # Generar nombre de archivo
        safe_name = "".join(
            c if c.isalnum() or c in (' ', '-', '_') else '_'
            for c in project.name
        ).strip().replace(' ', '_').lower()

        filename = f"informe_revision_{safe_name}.{extension}"

        # Devolver archivo para descarga
        return Response(
            content=result.value,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\""
            }
        )

    except Exception as e:
        logger.error(f"Error exporting review report for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/export/review-report/preview", response_model=ApiResponse)
def preview_review_report(project_id: int):
    """
    Previsualiza los datos que se incluirán en el informe de revisión.

    Útil para mostrar al usuario estadísticas antes de generar el documento.

    Args:
        project_id: ID del proyecto

    Returns:
        ApiResponse con preview de las estadísticas del informe
    """
    try:
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        # Obtener proyecto
        result = deps.project_manager.get(project_id)
        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        project = result.value

        # Importar módulos
        try:
            from narrative_assistant.corrections.base import CorrectionIssue
            from narrative_assistant.exporters.review_report_exporter import (
                ReviewReportExporter,
                ReviewReportOptions,
            )
        except ImportError:
            return ApiResponse(success=False, error="Módulo de informes no disponible")

        # Obtener alertas de corrección
        correction_categories = {
            "typography", "repetition", "agreement", "punctuation",
            "terminology", "regional", "clarity", "grammar",
            "anglicisms", "crutch_words", "glossary", "anacoluto",
            "pov", "orthography"
        }

        issues = []
        if deps.alert_repository:
            alerts = deps.alert_repository.get_by_project(project_id)
            for alert in alerts:
                category = alert.category.value.lower() if hasattr(alert.category, 'value') else str(alert.category).lower()
                if category in correction_categories:
                    issues.append(CorrectionIssue(
                        category=category,
                        issue_type=alert.alert_type or "unknown",
                        start_char=0,
                        end_char=0,
                        text=alert.excerpt or "",
                        explanation=alert.explanation or alert.description or "",
                        suggestion=alert.suggestion,
                        confidence=alert.confidence or 0.5,
                        context=alert.excerpt or "",
                        chapter_index=alert.chapter,
                    ))

        if not issues:
            return ApiResponse(
                success=True,
                data={
                    "document_title": project.name,
                    "total_issues": 0,
                    "categories": [],
                    "by_confidence": {"high": 0, "medium": 0, "low": 0},
                    "by_chapter": {},
                    "can_export": False,
                    "message": "No hay observaciones de corrección. Ejecute primero el análisis."
                }
            )

        # Preparar datos del informe
        exporter = ReviewReportExporter()
        options = ReviewReportOptions(document_title=project.name)
        data = exporter.prepare_report_data(issues, options)

        # Convertir a diccionario serializable
        categories_preview = [
            {
                "category": cat.category,
                "display_name": cat.display_name,
                "total": cat.total,
                "high_confidence": cat.high_confidence,
                "medium_confidence": cat.medium_confidence,
                "low_confidence": cat.low_confidence,
                "types": dict(cat.by_type),
            }
            for cat in data.categories
        ]

        return ApiResponse(
            success=True,
            data={
                "document_title": data.document_title,
                "total_issues": data.total_issues,
                "categories": categories_preview,
                "by_confidence": data.total_by_confidence,
                "by_chapter": data.by_chapter,
                "top_issues": [
                    {"category": cat, "type": typ, "count": cnt}
                    for cat, typ, cnt in data.top_issues_by_type
                ],
                "can_export": data.total_issues > 0,
            }
        )

    except Exception as e:
        logger.error(f"Error previewing review report for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/export/scrivener")
def export_scrivener(
    project_id: int,
    include_character_notes: bool = Query(True, description="Incluir fichas de personaje"),
    include_alerts_as_notes: bool = Query(True, description="Incluir alertas como notas"),
    include_entity_keywords: bool = Query(True, description="Incluir entidades como keywords"),
):
    """
    Exporta el proyecto a formato Scrivener (.scriv).

    Genera un archivo ZIP que contiene un paquete .scriv compatible
    con Scrivener 3, incluyendo:
    - Estructura de carpetas con capítulos
    - Contenido RTF de cada capítulo
    - Fichas de personaje en carpeta de investigación
    - Alertas como notas de documento
    - Entidades como keywords de Scrivener
    """
    from fastapi.responses import Response

    try:
        from narrative_assistant.exporters.scrivener_exporter import (
            ScrivenerExportOptions,
            export_to_scrivener,
        )

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")

        project = result.value

        options = ScrivenerExportOptions(
            include_character_notes=include_character_notes,
            include_alerts_as_notes=include_alerts_as_notes,
            include_entity_keywords=include_entity_keywords,
        )

        export_result = export_to_scrivener(project_id, options)

        if export_result.is_failure:
            return ApiResponse(success=False, error=str(export_result.error))

        safe_name = "".join(
            c for c in project.name if c.isalnum() or c in " -_."
        ).strip() or "Proyecto"

        return Response(
            content=export_result.value,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_name}.scriv.zip"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting to Scrivener: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/export/characters", response_model=ApiResponse)
def export_characters(
    project_id: int,
    format: str = "json",
    only_main: bool = True,
    include_attributes: bool = True,
    include_mentions: bool = True,
):
    """
    Exporta fichas de personajes en JSON o Markdown.

    Args:
        project_id: ID del proyecto
        format: 'json' o 'md'
        only_main: Solo personajes principales
        include_attributes: Incluir atributos extraídos
        include_mentions: Incluir información de menciones
    """
    try:
        if not deps.entity_repository:
            return ApiResponse(success=False, error="Entity repository not initialized")

        entities = deps.entity_repository.get_by_project(project_id)
        if not entities:
            return ApiResponse(success=False, error="No se encontraron entidades en este proyecto")

        # Filtrar personajes
        characters = [e for e in entities if e.entity_type.value == "character"]
        if only_main:
            characters = [e for e in characters if e.importance.value in ("main", "secondary")]

        if not characters:
            return ApiResponse(success=False, error="No se encontraron personajes para exportar")

        # Obtener atributos si se solicitan
        attrs_by_entity: dict[int, list[dict]] = {}
        if include_attributes:
            all_attrs = deps.entity_repository.get_attributes_by_project(project_id)
            for attr in all_attrs:
                eid = attr["entity_id"]
                attrs_by_entity.setdefault(eid, []).append(attr)

        # Obtener menciones si se solicitan
        mentions_by_entity: dict[int, dict] = {}
        if include_mentions:
            for entity in characters:
                try:
                    mention_list = deps.entity_repository.get_mentions_by_entity(entity.id)
                    chapter_ids = sorted({m.chapter_id for m in mention_list if m.chapter_id})
                    mention_data = {
                        "total_mentions": len(mention_list),
                        "chapters": chapter_ids,
                    }
                    mentions_by_entity[entity.id] = mention_data
                except Exception:
                    pass

        # Construir fichas
        sheets = []
        for entity in characters:
            sheet: dict[str, Any] = {
                "entity_id": entity.id,
                "canonical_name": entity.canonical_name,
                "aliases": entity.aliases or [],
                "entity_type": entity.entity_type.value,
                "importance": entity.importance.value,
            }

            if include_attributes:
                entity_attrs = attrs_by_entity.get(entity.id, [])
                physical = []
                psychological = []
                other = []
                for a in entity_attrs:
                    info = {
                        "key": a["attribute_key"],
                        "value": a["attribute_value"],
                        "confidence": a.get("confidence", 0.5),
                    }
                    cat = (a.get("attribute_type") or "").lower()
                    if cat == "physical":
                        physical.append(info)
                    elif cat == "psychological":
                        psychological.append(info)
                    else:
                        other.append(info)
                sheet["physical_attributes"] = physical
                sheet["psychological_attributes"] = psychological
                sheet["other_attributes"] = other

            if include_mentions:
                m = mentions_by_entity.get(entity.id, {})
                sheet["mentions"] = m if m else {"total": 0, "chapters": []}

            sheets.append(sheet)

        if format.lower() == "md":
            # Generar markdown
            lines = ["# Fichas de Personajes\n"]
            for s in sheets:
                lines.append(f"## {s['canonical_name']}")
                lines.append("")
                if s.get("aliases"):
                    lines.append(f"**También conocido como:** {', '.join(s['aliases'])}")
                lines.append(f"**Tipo:** {s['entity_type']}")
                lines.append(f"**Importancia:** {s['importance']}")
                lines.append("")

                if include_attributes:
                    if s.get("physical_attributes"):
                        lines.append("### Atributos Físicos")
                        for a in s["physical_attributes"]:
                            lines.append(f"- **{a['key'].replace('_', ' ').title()}:** {a['value']} (confianza: {a['confidence']:.0%})")
                        lines.append("")
                    if s.get("psychological_attributes"):
                        lines.append("### Atributos Psicológicos")
                        for a in s["psychological_attributes"]:
                            lines.append(f"- **{a['key'].replace('_', ' ').title()}:** {a['value']} (confianza: {a['confidence']:.0%})")
                        lines.append("")
                    if s.get("other_attributes"):
                        lines.append("### Otros Atributos")
                        for a in s["other_attributes"]:
                            lines.append(f"- **{a['key'].replace('_', ' ').title()}:** {a['value']}")
                        lines.append("")

                if include_mentions and s.get("mentions"):
                    m = s["mentions"]
                    lines.append("### Apariciones")
                    if isinstance(m, dict):
                        lines.append(f"- **Total menciones:** {m.get('total', m.get('total_mentions', 0))}")
                        chapters = m.get("chapters", [])
                        if chapters:
                            lines.append(f"- **Capítulos:** {', '.join(str(c) for c in chapters)}")
                    lines.append("")

                lines.append("---\n")

            return ApiResponse(success=True, data={"content": "\n".join(lines)})
        else:
            return ApiResponse(success=True, data=sheets)

    except Exception as e:
        logger.error(f"Error exporting characters for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/export/report", response_model=ApiResponse)
def export_report(
    project_id: int,
    format: str = "json",
):
    """
    Exporta un informe resumido del análisis en JSON o Markdown.

    Incluye estadísticas generales, resumen de entidades, alertas por categoría
    y observaciones principales.

    Args:
        project_id: ID del proyecto
        format: 'json' o 'md'
    """
    try:
        if not deps.project_manager:
            return ApiResponse(success=False, error="Project manager not initialized")

        result = deps.project_manager.get(project_id)
        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        project = result.value

        # Recopilar estadísticas
        entities = deps.entity_repository.get_by_project(project_id) if deps.entity_repository else []
        alerts = deps.alert_repository.get_by_project(project_id) if deps.alert_repository else []
        chapters = deps.chapter_repository.get_by_project(project_id) if deps.chapter_repository else []

        # Clasificar entidades
        characters = [e for e in entities if e.entity_type.value == "character"]
        locations = [e for e in entities if e.entity_type.value == "location"]

        # Clasificar alertas
        alerts_by_category: dict[str, int] = {}
        alerts_by_severity: dict[str, int] = {"critical": 0, "error": 0, "warning": 0, "info": 0}
        open_alerts = [a for a in alerts if getattr(a, 'status', 'open') == 'open']
        for a in open_alerts:
            cat = a.category.value if hasattr(a.category, 'value') else str(a.category)
            alerts_by_category[cat] = alerts_by_category.get(cat, 0) + 1
            sev = getattr(a, 'severity', 'warning')
            sev_str = sev.value if hasattr(sev, 'value') else str(sev)
            if sev_str in alerts_by_severity:
                alerts_by_severity[sev_str] += 1

        report_data = {
            "project_name": project.name,
            "statistics": {
                "word_count": getattr(project, 'word_count', 0) or 0,
                "chapter_count": len(chapters),
                "character_count": len(characters),
                "location_count": len(locations),
                "total_entities": len(entities),
                "total_alerts": len(open_alerts),
            },
            "alerts_by_category": alerts_by_category,
            "alerts_by_severity": alerts_by_severity,
            "top_alerts": [
                {
                    "category": a.category.value if hasattr(a.category, 'value') else str(a.category),
                    "description": getattr(a, 'description', '') or '',
                    "severity": (a.severity.value if hasattr(a.severity, 'value') else str(getattr(a, 'severity', 'warning'))),
                    "chapter": getattr(a, 'chapter', None),
                }
                for a in sorted(open_alerts, key=lambda x: -(getattr(x, 'confidence', 0) or 0))[:20]
            ],
            "main_characters": [
                {"name": e.canonical_name, "importance": e.importance.value, "aliases": e.aliases or []}
                for e in characters if e.importance.value in ("main", "secondary")
            ],
        }

        if format.lower() == "md":
            lines = [
                f"# Informe de Análisis: {project.name}",
                "",
                "## Estadísticas Generales",
                "",
                f"- **Palabras:** {report_data['statistics']['word_count']:,}",
                f"- **Capítulos:** {report_data['statistics']['chapter_count']}",
                f"- **Personajes:** {report_data['statistics']['character_count']}",
                f"- **Localizaciones:** {report_data['statistics']['location_count']}",
                f"- **Total entidades:** {report_data['statistics']['total_entities']}",
                f"- **Alertas abiertas:** {report_data['statistics']['total_alerts']}",
                "",
            ]

            if alerts_by_severity["critical"] > 0 or alerts_by_severity["error"] > 0:
                lines.append("## Alertas por Severidad")
                lines.append("")
                for sev, count in alerts_by_severity.items():
                    if count > 0:
                        lines.append(f"- **{sev.title()}:** {count}")
                lines.append("")

            if alerts_by_category:
                lines.append("## Alertas por Categoría")
                lines.append("")
                for cat, count in sorted(alerts_by_category.items(), key=lambda x: -x[1]):
                    lines.append(f"- **{cat}:** {count}")
                lines.append("")

            if report_data["main_characters"]:
                lines.append("## Personajes Principales")
                lines.append("")
                for ch in report_data["main_characters"]:
                    aliases = f" ({', '.join(ch['aliases'])})" if ch['aliases'] else ""
                    lines.append(f"- **{ch['name']}**{aliases} — {ch['importance']}")
                lines.append("")

            if report_data["top_alerts"]:
                lines.append("## Observaciones Principales")
                lines.append("")
                for alert in report_data["top_alerts"][:10]:
                    ch_str = f" (cap. {alert['chapter']})" if alert['chapter'] else ""
                    lines.append(f"- [{alert['severity']}] {alert['description']}{ch_str}")
                lines.append("")

            lines.append("---")
            lines.append("_Informe generado por Narrative Assistant_")

            return ApiResponse(success=True, data={"content": "\n".join(lines)})
        else:
            return ApiResponse(success=True, data=report_data)

    except Exception as e:
        logger.error(f"Error exporting report for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/export/alerts", response_model=ApiResponse)
def export_alerts(
    project_id: int,
    format: str = "json",
    include_pending: bool = True,
    include_resolved: bool = False,
):
    """
    Exporta alertas del proyecto en JSON o CSV.

    Args:
        project_id: ID del proyecto
        format: 'json' o 'csv'
        include_pending: Incluir alertas pendientes/abiertas
        include_resolved: Incluir alertas resueltas
    """
    try:
        if not deps.alert_repository:
            return ApiResponse(success=False, error="Alert repository not initialized")

        all_alerts = deps.alert_repository.get_by_project(project_id)

        # Filtrar por estado
        filtered = []
        for a in all_alerts:
            status = getattr(a, 'status', 'open')
            if status == 'open' and include_pending:
                filtered.append(a)
            elif status in ('resolved', 'accepted', 'rejected') and include_resolved:
                filtered.append(a)

        if not filtered:
            return ApiResponse(success=False, error="No se encontraron alertas con los filtros seleccionados")

        # Serializar alertas
        alert_rows = []
        for a in filtered:
            row = {
                "id": getattr(a, 'id', None),
                "category": a.category.value if hasattr(a.category, 'value') else str(a.category),
                "type": getattr(a, 'alert_type', '') or '',
                "severity": (a.severity.value if hasattr(a.severity, 'value') else str(getattr(a, 'severity', 'warning'))),
                "description": getattr(a, 'description', '') or '',
                "chapter": getattr(a, 'chapter', None),
                "excerpt": getattr(a, 'excerpt', '') or '',
                "suggestion": getattr(a, 'suggestion', '') or '',
                "confidence": getattr(a, 'confidence', 0) or 0,
                "status": getattr(a, 'status', 'open'),
            }
            alert_rows.append(row)

        if format.lower() == "csv":
            import csv
            import io

            output = io.StringIO()
            fieldnames = ["id", "category", "type", "severity", "description", "chapter", "excerpt", "suggestion", "confidence", "status"]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for row in alert_rows:
                writer.writerow(row)

            return ApiResponse(success=True, data={"content": output.getvalue()})
        else:
            return ApiResponse(success=True, data=alert_rows)

    except Exception as e:
        logger.error(f"Error exporting alerts for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


