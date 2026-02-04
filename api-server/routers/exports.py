"""
Router: exports
"""

from fastapi import APIRouter
import deps
from deps import logger
from deps import ApiResponse
from fastapi import HTTPException
from fastapi import Query
from typing import Optional, Any
from deps import _estimate_export_pages

router = APIRouter()

@router.get("/api/projects/{project_id}/export/document")
async def export_document(
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
        return ApiResponse(success=False, error=str(e))


@router.get("/api/projects/{project_id}/export/document/preview", response_model=ApiResponse)
async def preview_document_export(
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
        except ImportError as e:
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
        return ApiResponse(success=False, error=str(e))


@router.get("/api/projects/{project_id}/export/corrected")
async def export_corrected_document(
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
            from narrative_assistant.exporters.corrected_document_exporter import (
                CorrectedDocumentExporter,
                TrackChangeOptions,
            )
            from narrative_assistant.corrections.base import CorrectionIssue
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
        return ApiResponse(success=False, error=str(e))


@router.get("/api/projects/{project_id}/export/review-report")
async def export_review_report(
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
            from narrative_assistant.exporters.review_report_exporter import (
                ReviewReportExporter,
                ReviewReportOptions,
            )
            from narrative_assistant.corrections.base import CorrectionIssue
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
        return ApiResponse(success=False, error=str(e))


@router.get("/api/projects/{project_id}/export/review-report/preview", response_model=ApiResponse)
async def preview_review_report(project_id: int):
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
            from narrative_assistant.exporters.review_report_exporter import (
                ReviewReportExporter,
                ReviewReportOptions,
            )
            from narrative_assistant.corrections.base import CorrectionIssue
        except ImportError as e:
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
        return ApiResponse(success=False, error=str(e))


@router.get("/api/projects/{project_id}/export/scrivener")
async def export_scrivener(
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
            export_to_scrivener,
            ScrivenerExportOptions,
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
        return ApiResponse(success=False, error=str(e))


