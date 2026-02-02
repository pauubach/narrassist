"""
Router: alerts
"""

from fastapi import APIRouter
import deps
import json
from deps import logger
from deps import ApiResponse
from fastapi import Request
from typing import Optional, Any
from deps import AlertResponse, _verify_alert_ownership

router = APIRouter()

@router.get("/api/projects/{project_id}/alerts", response_model=ApiResponse)
async def list_alerts(
    project_id: int,
    status: Optional[str] = None,
    current_chapter: Optional[int] = None,
):
    """
    Lista todas las alertas de un proyecto, opcionalmente priorizadas.

    Args:
        project_id: ID del proyecto
        status: Filtrar por estado (open, resolved, dismissed)
        current_chapter: Capítulo actual para priorizar alertas cercanas

    Returns:
        ApiResponse con lista de alertas (priorizadas si current_chapter se especifica)
    """
    try:
        alert_repo = deps.alert_repository

        # Obtener alertas - usar método priorizado si se especifica capítulo
        if current_chapter is not None:
            result = alert_repo.get_by_project_prioritized(project_id, current_chapter=current_chapter)
        else:
            result = alert_repo.get_by_project(project_id)
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

        alerts_data = [
            AlertResponse(
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
                start_char=getattr(a, 'start_char', None),
                end_char=getattr(a, 'end_char', None),
                excerpt=getattr(a, 'excerpt', None) or '',
                status=a.status.value if hasattr(a.status, 'value') else str(a.status),
                entity_ids=getattr(a, 'entity_ids', []) or [],
                confidence=getattr(a, 'confidence', 0.0) or 0.0,
                created_at=a.created_at.isoformat() if hasattr(a.created_at, 'isoformat') else str(a.created_at),
                updated_at=a.updated_at.isoformat() if hasattr(a, 'updated_at') and a.updated_at else None,
                resolved_at=a.resolved_at.isoformat() if hasattr(a, 'resolved_at') and a.resolved_at else None,
                extra_data=getattr(a, 'extra_data', None) or {},
            )
            for a in alerts
        ]

        return ApiResponse(success=True, data=alerts_data)
    except Exception as e:
        logger.error(f"Error listing alerts for project {project_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.patch("/api/projects/{project_id}/alerts/{alert_id}/status", response_model=ApiResponse)
async def update_alert_status(project_id: int, alert_id: int, request: Request):
    """
    Actualiza el status de una alerta.

    Args:
        project_id: ID del proyecto
        alert_id: ID de la alerta
        request: Body con {"status": "resolved"|"dismissed"|"open"}

    Returns:
        ApiResponse confirmando el cambio
    """
    try:
        data = await request.json()
        new_status_str = data.get('status', '').lower()

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
        return ApiResponse(success=False, error=str(e))


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
        return ApiResponse(success=False, error=str(e))


