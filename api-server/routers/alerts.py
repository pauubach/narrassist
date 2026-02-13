"""
Router: alerts

Endpoints para gestión de alertas, incluyendo:
- CRUD de alertas
- Dismissals persistentes (sobreviven re-análisis)
- Estadísticas de descartes por detector
- Batch operations
"""

from typing import Optional

import deps
from deps import AlertResponse, ApiResponse, _verify_alert_ownership, logger
from fastapi import APIRouter

from narrative_assistant.alerts.models import AlertStatus

router = APIRouter()


def _resolve_alert_positions(alert, chapters_cache: dict | None = None) -> tuple[int | None, int | None]:
    """
    Intenta resolver start_char/end_char para alertas que no los tienen.

    Si la alerta tiene excerpt y chapter pero no start_char, busca el excerpt
    en el texto del capítulo para derivar la posición.

    Returns:
        (start_char, end_char) o (None, None) si no se puede resolver.
    """
    start = getattr(alert, 'start_char', None)
    end = getattr(alert, 'end_char', None)

    if start is not None and end is not None:
        return start, end

    excerpt = getattr(alert, 'excerpt', None)
    chapter_num = getattr(alert, 'chapter', None)

    if not excerpt or not chapter_num or not chapters_cache:
        return start, end

    chapter_data = chapters_cache.get(chapter_num)
    if not chapter_data:
        return start, end

    content = chapter_data.get('content', '')
    chapter_start_offset = chapter_data.get('start_char', 0)

    # Buscar excerpt en el contenido del capítulo
    idx = content.find(excerpt[:80])  # Usar primeros 80 chars para búsqueda
    if idx >= 0:
        start = chapter_start_offset + idx
        end = start + len(excerpt)

    return start, end

@router.get("/api/projects/{project_id}/alerts", response_model=ApiResponse)
async def list_alerts(
    project_id: int,
    status: Optional[str] = None,
    current_chapter: Optional[int] = None,
    severity: Optional[str] = None,
    focus: bool = False,
    chapter_min: Optional[int] = None,
    chapter_max: Optional[int] = None,
):
    """
    Lista todas las alertas de un proyecto, opcionalmente priorizadas.

    Args:
        project_id: ID del proyecto
        status: Filtrar por estado (open, resolved, dismissed)
        current_chapter: Capítulo actual para priorizar alertas cercanas
        severity: Filtrar por severidad (critical, warning, info)
        focus: Si True, modo focus: solo alertas critical y warning con confianza >= 0.7
        chapter_min: Filtrar alertas desde este capítulo (inclusive)
        chapter_max: Filtrar alertas hasta este capítulo (inclusive)

    Returns:
        ApiResponse con lista de alertas (priorizadas si current_chapter se especifica)
    """
    try:
        alert_repo = deps.alert_repository

        # Obtener alertas - usar método priorizado si se especifica capítulo
        if current_chapter is not None:
            result = alert_repo.get_by_project_prioritized(
                project_id,
                current_chapter=current_chapter,
                chapter_min=chapter_min,
                chapter_max=chapter_max,
            )
        else:
            result = alert_repo.get_by_project(
                project_id,
                chapter_min=chapter_min,
                chapter_max=chapter_max,
            )
        if result.is_failure:
            return ApiResponse(success=False, error="Error obteniendo alertas")

        all_alerts = result.value

        # Filtrar por status si se especifica
        if status:
            status_value = status.lower()
            if status_value == 'open':
                # "open" incluye todos los estados no resueltos/descartados
                open_statuses = {'new', 'open', 'acknowledged', 'in_progress'}
                alerts = [a for a in all_alerts if a.status.value in open_statuses]
            else:
                alerts = [a for a in all_alerts if a.status.value == status_value]
        else:
            alerts = all_alerts

        # Filtrar por severidad si se especifica
        if severity:
            sev_lower = severity.lower()
            alerts = [
                a for a in alerts
                if (a.severity.value if hasattr(a.severity, 'value') else str(a.severity)).lower() == sev_lower
            ]

        # Focus mode: solo alertas critical/warning con confianza >= 0.7
        if focus:
            focus_severities = {'critical', 'warning'}
            alerts = [
                a for a in alerts
                if (a.severity.value if hasattr(a.severity, 'value') else str(a.severity)).lower() in focus_severities
                and (getattr(a, 'confidence', 0.0) or 0.0) >= 0.7
            ]

        # Construir cache de capítulos para resolver posiciones faltantes (S6-04)
        chapters_cache = None
        has_missing_positions = any(
            getattr(a, 'start_char', None) is None and getattr(a, 'excerpt', None)
            for a in alerts
        )
        if has_missing_positions and hasattr(deps, 'chapter_repository') and deps.chapter_repository:
            try:
                chapters = deps.chapter_repository.get_by_project(project_id)
                chapters_cache = {
                    c.chapter_number: {
                        'content': c.content,
                        'start_char': c.start_char,
                    }
                    for c in chapters
                }
            except Exception:
                pass  # Si falla, las posiciones quedarán como None

        alerts_data = []
        for a in alerts:
            resolved_start, resolved_end = _resolve_alert_positions(a, chapters_cache)
            # S14: Build previous alert summary if linked
            prev_summary = None
            match_conf = getattr(a, 'match_confidence', None)
            resolution_reason = getattr(a, 'resolution_reason', None)
            prev_snap_id = getattr(a, 'previous_snapshot_alert_id', None)
            if prev_snap_id:
                prev_summary = f"Linked to snapshot alert #{prev_snap_id}"

            alerts_data.append(AlertResponse(
                id=a.id,
                project_id=a.project_id,
                category=a.category.value if hasattr(a.category, 'value') else str(a.category),
                severity=a.severity.value if hasattr(a.severity, 'value') else str(a.severity),
                alert_type=a.alert_type,
                title=a.title,
                description=a.description,
                explanation=a.explanation,
                suggestion=a.suggestion,
                chapter=a.chapter,
                start_char=resolved_start,
                end_char=resolved_end,
                excerpt=getattr(a, 'excerpt', None) or '',
                status=a.status.value if hasattr(a.status, 'value') else str(a.status),
                entity_ids=getattr(a, 'entity_ids', []) or [],
                confidence=getattr(a, 'confidence', 0.0) or 0.0,
                content_hash=getattr(a, 'content_hash', '') or '',
                created_at=a.created_at.isoformat() if hasattr(a.created_at, 'isoformat') else str(a.created_at),
                updated_at=a.updated_at.isoformat() if hasattr(a, 'updated_at') and a.updated_at else None,
                resolved_at=a.resolved_at.isoformat() if hasattr(a, 'resolved_at') and a.resolved_at else None,
                extra_data=getattr(a, 'extra_data', None) or {},
                previous_alert_summary=prev_summary,
                match_confidence=match_conf,
                resolution_reason=resolution_reason,
            ))

        return ApiResponse(success=True, data=alerts_data)
    except Exception as e:
        logger.error(f"Error listing alerts for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.patch("/api/projects/{project_id}/alerts/{alert_id}/status", response_model=ApiResponse)
async def update_alert_status(project_id: int, alert_id: int, body: deps.AlertStatusRequest):
    """
    Actualiza el status de una alerta.

    Args:
        project_id: ID del proyecto
        alert_id: ID de la alerta
        body: AlertStatusRequest con status (resolved|dismissed|open|active|reopen)

    Returns:
        ApiResponse confirmando el cambio
    """
    try:
        new_status_str = body.status.lower()

        # Mapear status string a enum
        status_map = {
            'resolved': AlertStatus.RESOLVED,
            'dismissed': AlertStatus.DISMISSED,
            'open': AlertStatus.OPEN,
            'active': AlertStatus.OPEN,  # alias
            'reopen': AlertStatus.OPEN,  # alias
        }

        if new_status_str not in status_map:
            return ApiResponse(
                success=False,
                error=f"Status inválido: {new_status_str}. Valores válidos: resolved, dismissed, open"
            )

        # Verificar que la alerta existe y pertenece al proyecto
        alert, error = _verify_alert_ownership(alert_id, project_id)
        if error:
            return error

        # Actualizar el status
        alert.status = status_map[new_status_str]
        deps.alert_repository.update(alert)

        # Persistir dismissal para que sobreviva re-análisis
        if new_status_str == 'dismissed' and deps.dismissal_repository:
            reason = body.reason
            scope = body.scope
            if alert.content_hash:
                deps.dismissal_repository.dismiss(
                    project_id=project_id,
                    content_hash=alert.content_hash,
                    alert_type=alert.alert_type,
                    source_module=getattr(alert, 'source_module', ''),
                    scope=scope,
                    reason=reason,
                )
            # Recalibrar confianza del detector tras descarte (BK-22)
            try:
                from narrative_assistant.alerts.engine import get_alert_engine
                engine = get_alert_engine()
                engine.recalibrate_detector(
                    project_id, alert.alert_type, getattr(alert, 'source_module', '')
                )
            except Exception:
                pass  # best-effort
        elif new_status_str in ('open', 'active', 'reopen') and deps.dismissal_repository:
            # Reabrir: eliminar dismissal persistido
            if alert.content_hash:
                deps.dismissal_repository.undismiss(project_id, alert.content_hash)

        status_messages = {
            'resolved': 'Alerta marcada como resuelta',
            'dismissed': 'Alerta descartada',
            'open': 'Alerta reabierta',
            'active': 'Alerta reabierta',
            'reopen': 'Alerta reabierta',
        }

        logger.info(f"Alert {alert_id} status changed to {new_status_str}")

        return ApiResponse(
            success=True,
            data={"id": alert_id, "status": new_status_str},
            message=status_messages[new_status_str]
        )
    except Exception as e:
        logger.error(f"Error updating alert {alert_id} status: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


# Endpoints legacy para compatibilidad (redirigen al nuevo endpoint unificado)


@router.post("/api/projects/{project_id}/alerts/{alert_id}/resolve", response_model=ApiResponse)
async def resolve_alert(project_id: int, alert_id: int):
    """Marca una alerta como resuelta. [DEPRECATED: usar PATCH /status]"""
    alert, error = _verify_alert_ownership(alert_id, project_id)
    if error:
        return error
    alert.status = AlertStatus.RESOLVED
    deps.alert_repository.update(alert)
    return ApiResponse(success=True, message="Alerta marcada como resuelta")


@router.post("/api/projects/{project_id}/alerts/{alert_id}/dismiss", response_model=ApiResponse)
async def dismiss_alert(project_id: int, alert_id: int):
    """Descarta una alerta. [DEPRECATED: usar PATCH /status]"""
    alert, error = _verify_alert_ownership(alert_id, project_id)
    if error:
        return error
    alert.status = AlertStatus.DISMISSED
    deps.alert_repository.update(alert)
    return ApiResponse(success=True, message="Alerta descartada")


@router.post("/api/projects/{project_id}/alerts/{alert_id}/reopen", response_model=ApiResponse)
async def reopen_alert(project_id: int, alert_id: int):
    """Reabre una alerta. [DEPRECATED: usar PATCH /status]"""
    alert, error = _verify_alert_ownership(alert_id, project_id)
    if error:
        return error
    alert.status = AlertStatus.OPEN
    deps.alert_repository.update(alert)
    return ApiResponse(success=True, message="Alerta reabierta")


@router.post("/api/projects/{project_id}/alerts/resolve-all", response_model=ApiResponse)
async def resolve_all_alerts(project_id: int):
    """
    Marca todas las alertas abiertas como resueltas.
    """
    try:
        alert_repo = deps.alert_repository

        # Obtener todas las alertas del proyecto
        result = alert_repo.get_by_project(project_id)
        if result.is_failure:
            return ApiResponse(success=False, error="Error obteniendo alertas")

        all_alerts = result.value

        # Filtrar alertas abiertas y resolverlas
        resolved_count = 0
        for alert in all_alerts:
            if alert.status.value in ['new', 'open', 'acknowledged', 'in_progress']:
                alert.status = AlertStatus.RESOLVED
                alert_repo.update(alert)
                resolved_count += 1

        logger.info(f"Resolved {resolved_count} alerts for project {project_id}")

        return ApiResponse(
            success=True,
            message=f"Se han resuelto {resolved_count} alertas"
        )
    except Exception as e:
        logger.error(f"Error resolving all alerts for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


# =========================================================================
# Dismissal endpoints (persistentes entre re-análisis)
# =========================================================================


@router.post("/api/projects/{project_id}/alerts/dismiss-batch", response_model=ApiResponse)
async def dismiss_batch(project_id: int, body: deps.BatchDismissRequest):
    """
    Descarta múltiples alertas de una vez, persistiendo para re-análisis.

    Body:
        {
            "alert_ids": [1, 2, 3],
            "reason": "false_positive",
            "scope": "instance"
        }
    """
    try:
        if not deps.dismissal_repository:
            return ApiResponse(success=False, error="Dismissal repository not initialized")

        alert_ids = body.alert_ids
        reason = body.reason
        scope = body.scope

        alert_repo = deps.alert_repository
        dismissal_items = []

        for alert_id in alert_ids:
            result = alert_repo.get(alert_id)
            if result.is_success:
                alert = result.value
                if alert.project_id == project_id:
                    # Actualizar estado de la alerta
                    alert.status = AlertStatus.DISMISSED
                    alert_repo.update(alert)

                    # Recoger datos para dismissal persistente
                    if alert.content_hash:
                        dismissal_items.append({
                            "content_hash": alert.content_hash,
                            "alert_type": alert.alert_type,
                            "source_module": getattr(alert, "source_module", ""),
                        })

        # Persistir dismissals en batch
        if dismissal_items:
            deps.dismissal_repository.dismiss_batch(
                project_id=project_id,
                items=dismissal_items,
                scope=scope,
                reason=reason,
            )

            # Recalibrar detectores afectados (BK-22)
            try:
                from narrative_assistant.alerts.engine import get_alert_engine
                engine = get_alert_engine()
                affected = {(item["alert_type"], item["source_module"]) for item in dismissal_items}
                for alert_type, source_module in affected:
                    engine.recalibrate_detector(project_id, alert_type, source_module)
            except Exception:
                pass  # best-effort

        count = len(alert_ids)
        logger.info(f"Batch dismissed {count} alerts for project {project_id}")

        return ApiResponse(
            success=True,
            data={"dismissed_count": count, "persisted_count": len(dismissal_items)},
            message=f"Se han descartado {count} alertas",
        )
    except Exception as e:
        logger.error(f"Error in batch dismiss for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/dismissals/stats", response_model=ApiResponse)
async def get_dismissal_stats(project_id: int):
    """
    Obtiene estadísticas de descartes por tipo de alerta y módulo.

    Útil para identificar qué detectores generan más falsos positivos
    y priorizar mejoras de precisión.
    """
    try:
        if not deps.dismissal_repository:
            return ApiResponse(success=False, error="Dismissal repository not initialized")

        result = deps.dismissal_repository.get_dismissal_stats(project_id)
        if result.is_failure:
            return ApiResponse(success=False, error="Error obteniendo estadísticas")

        # Enriquecer con total de alertas por tipo para calcular FP rate
        stats = result.value
        if deps.alert_repository:
            alert_result = deps.alert_repository.get_by_project(project_id)
            if alert_result.is_success:
                total_by_type: dict[str, int] = {}
                for alert in alert_result.value:
                    total_by_type[alert.alert_type] = total_by_type.get(alert.alert_type, 0) + 1

                # Calcular false positive rate por tipo
                fp_rates = {}
                for alert_type, dismissed_count in stats.get("by_alert_type", {}).items():
                    total = total_by_type.get(alert_type, dismissed_count)
                    fp_rates[alert_type] = {
                        "dismissed": dismissed_count,
                        "total": total,
                        "fp_rate": round(dismissed_count / max(total, 1), 2),
                    }
                stats["fp_rates"] = fp_rates

        return ApiResponse(success=True, data=stats)
    except Exception as e:
        logger.error(f"Error getting dismissal stats for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/{project_id}/alerts/apply-dismissals", response_model=ApiResponse)
async def apply_dismissals(project_id: int):
    """
    Aplica dismissals persistidos a alertas actuales.

    Útil después de un re-análisis: busca alertas cuyo content_hash
    coincida con un dismissal previo y las marca como descartadas.
    """
    try:
        if not deps.alert_repository:
            return ApiResponse(success=False, error="Alert repository not initialized")

        result = deps.alert_repository.apply_dismissals(project_id)
        if result.is_failure:
            return ApiResponse(success=False, error="Error aplicando dismissals")

        count = result.value
        return ApiResponse(
            success=True,
            data={"auto_dismissed_count": count},
            message=f"Se han auto-descartado {count} alertas",
        )
    except Exception as e:
        logger.error(f"Error applying dismissals for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/{project_id}/alerts/recalibrate", response_model=ApiResponse)
async def recalibrate_detectors(project_id: int):
    """
    Recalibra la confianza de todos los detectores según el historial de descartes.

    Para cada par (alert_type, source_module) calcula:
    - fp_rate = dismissed / total
    - calibration_factor = 1 - fp_rate * 0.5

    Las futuras alertas de ese detector se crearán con confianza ajustada.
    """
    try:
        from narrative_assistant.alerts.engine import get_alert_engine
        engine = get_alert_engine()
        results = engine.recalibrate_project(project_id)

        return ApiResponse(
            success=True,
            data={"calibrations": results, "detectors_calibrated": len(results)},
            message=f"Se han recalibrado {len(results)} detectores",
        )
    except Exception as e:
        logger.error(f"Error recalibrating for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/alerts/calibration", response_model=ApiResponse)
async def get_calibration_data(project_id: int):
    """Obtiene los datos de calibración actuales por detector."""
    try:
        from narrative_assistant.persistence.database import get_database
        db = get_database()
        rows = db.fetchall(
            """
            SELECT alert_type, source_module, total_alerts, total_dismissed,
                   fp_rate, calibration_factor, updated_at
            FROM detector_calibration
            WHERE project_id = ?
            ORDER BY fp_rate DESC
            """,
            (project_id,),
        )
        calibrations = [
            {
                "alert_type": r["alert_type"],
                "source_module": r["source_module"],
                "total_alerts": r["total_alerts"],
                "total_dismissed": r["total_dismissed"],
                "fp_rate": r["fp_rate"],
                "calibration_factor": r["calibration_factor"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]
        return ApiResponse(success=True, data={"calibrations": calibrations})
    except Exception as e:
        logger.error(f"Error getting calibration for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


# =========================================================================
# Suppression Rules endpoints
# =========================================================================


@router.get("/api/projects/{project_id}/suppression-rules", response_model=ApiResponse)
async def get_suppression_rules(project_id: int):
    """Obtiene las reglas de supresión del proyecto (incluye globales)."""
    try:
        if not deps.dismissal_repository:
            return ApiResponse(success=False, error="Dismissal repository not initialized")

        result = deps.dismissal_repository.get_suppression_rules(project_id)
        if result.is_failure:
            return ApiResponse(success=False, error="Error obteniendo reglas")

        rules_data = [
            {
                "id": r.id,
                "project_id": r.project_id,
                "rule_type": r.rule_type,
                "pattern": r.pattern,
                "entity_name": r.entity_name,
                "reason": r.reason,
                "is_active": r.is_active,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in result.value
        ]

        return ApiResponse(success=True, data=rules_data)
    except Exception as e:
        logger.error(f"Error getting suppression rules: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/projects/{project_id}/suppression-rules", response_model=ApiResponse)
async def create_suppression_rule(project_id: int, body: deps.SuppressionRuleRequest):
    """
    Crea una regla de supresión.

    Body:
        {
            "rule_type": "alert_type",
            "pattern": "spelling_*",
            "entity_name": null,
            "reason": "No relevante para este proyecto"
        }
    """
    try:
        if not deps.dismissal_repository:
            return ApiResponse(success=False, error="Dismissal repository not initialized")

        result = deps.dismissal_repository.create_suppression_rule(
            rule_type=body.rule_type,
            pattern=body.pattern,
            project_id=project_id,
            entity_name=body.entity_name,
            reason=body.reason or "",
        )

        if result.is_failure:
            return ApiResponse(success=False, error="Error creando regla")

        return ApiResponse(
            success=True,
            data={"id": result.value},
            message="Regla de supresión creada",
        )
    except Exception as e:
        logger.error(f"Error creating suppression rule: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.delete("/api/projects/{project_id}/suppression-rules/{rule_id}", response_model=ApiResponse)
async def delete_suppression_rule(project_id: int, rule_id: int):
    """Elimina una regla de supresión."""
    try:
        if not deps.dismissal_repository:
            return ApiResponse(success=False, error="Dismissal repository not initialized")

        result = deps.dismissal_repository.delete_suppression_rule(rule_id)
        if result.is_failure:
            return ApiResponse(success=False, error="Error eliminando regla")

        return ApiResponse(success=True, message="Regla eliminada")
    except Exception as e:
        logger.error(f"Error deleting suppression rule {rule_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


# =========================================================================
# S14: Revision Intelligence endpoints
# =========================================================================


@router.put("/api/projects/{project_id}/alerts/{alert_id}/mark-resolved", response_model=ApiResponse)
async def mark_alert_resolved(project_id: int, alert_id: int, body: deps.MarkResolvedRequest):
    """
    Confirma manualmente la resolución de una alerta (S14-07).

    Marca como resuelta y registra el motivo (manual, text_changed, etc.).
    """
    try:
        alert, error = _verify_alert_ownership(alert_id, project_id)
        if error:
            return error

        alert.status = AlertStatus.RESOLVED

        deps.alert_repository.update(alert)

        # Write resolution_reason to DB
        try:
            from narrative_assistant.persistence.database import get_database
            db = get_database()
            with db.connection() as conn:
                conn.execute(
                    """UPDATE alerts SET resolution_reason = ? WHERE id = ?""",
                    (body.resolution_reason or "manual", alert_id),
                )
                conn.commit()
        except Exception:
            pass  # Column may not exist in older schemas

        logger.info(
            f"Alert {alert_id} marked resolved: reason={body.resolution_reason}"
        )
        return ApiResponse(
            success=True,
            data={"id": alert_id, "status": "resolved", "resolution_reason": body.resolution_reason},
            message="Alerta marcada como resuelta",
        )
    except Exception as e:
        logger.error(f"Error marking alert {alert_id} resolved: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/projects/{project_id}/comparison/detail", response_model=ApiResponse)
async def get_comparison_detail(project_id: int):
    """
    Obtiene el detalle completo de la última comparación (S14-07).

    Incluye alertas nuevas, resueltas (con resolution_reason), y sin cambio.
    """
    try:
        from narrative_assistant.analysis.comparison import ComparisonService

        service = ComparisonService()
        report = service.compare(project_id)

        if report is None:
            return ApiResponse(
                success=True,
                data={"has_comparison": False},
                message="No hay comparación disponible",
            )

        return ApiResponse(
            success=True,
            data={
                "has_comparison": True,
                **report.to_dict(),
            },
        )
    except Exception as e:
        logger.error(f"Error getting comparison detail: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


