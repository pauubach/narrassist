"""
Router para historial de cambios y undo/redo universal.

Endpoints:
- GET  /api/projects/{id}/history           — Lista historial con filtros
- GET  /api/projects/{id}/history/undoable   — Acciones pendientes de deshacer
- GET  /api/projects/{id}/history/count      — Conteo para badge del sidebar
- POST /api/projects/{id}/undo              — Ctrl+Z: deshacer última acción
- POST /api/projects/{id}/undo/{entry_id}   — Deshacer acción específica
- POST /api/projects/{id}/undo-batch/{batch_id} — Deshacer operación compuesta
- GET  /api/projects/{id}/history/{entry_id}/can-undo — Verificar si se puede deshacer
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query

from deps import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["history"])


@router.get("/api/projects/{project_id}/history", response_model=ApiResponse)
def get_history(
    project_id: int,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    undoable_only: bool = False,
):
    """Obtiene el historial de cambios de un proyecto."""
    try:
        from narrative_assistant.persistence.history import HistoryManager
        history = HistoryManager(project_id)
        entries = history.get_history(
            limit=limit,
            offset=offset,
            target_type=target_type,
            target_id=target_id,
            undoable_only=undoable_only,
        )
        return ApiResponse(
            success=True,
            data=[e.to_dict() for e in entries],
        )
    except Exception as e:
        logger.error(f"Error getting history: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error obteniendo historial")


@router.get("/api/projects/{project_id}/history/undoable", response_model=ApiResponse)
def get_undoable_history(
    project_id: int,
    limit: int = Query(50, ge=1, le=200),
):
    """Obtiene solo las acciones que se pueden deshacer (para el panel de historial)."""
    try:
        from narrative_assistant.persistence.history import HistoryManager
        history = HistoryManager(project_id)
        entries = history.get_history(limit=limit, undoable_only=True)
        return ApiResponse(
            success=True,
            data=[e.to_dict() for e in entries],
        )
    except Exception as e:
        logger.error(f"Error getting undoable history: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error obteniendo historial")


@router.get("/api/projects/{project_id}/history/count", response_model=ApiResponse)
def get_undoable_count(project_id: int):
    """Obtiene el conteo de acciones deshacer pendientes (para badge del sidebar)."""
    try:
        from narrative_assistant.persistence.history import HistoryManager
        history = HistoryManager(project_id)
        count = history.get_undoable_count()
        return ApiResponse(success=True, data={"count": count})
    except Exception as e:
        logger.error(f"Error getting undoable count: {e}", exc_info=True)
        return ApiResponse(success=True, data={"count": 0})


@router.get("/api/projects/{project_id}/history/{entry_id}/can-undo", response_model=ApiResponse)
def can_undo(project_id: int, entry_id: int):
    """Verifica si una acción específica se puede deshacer."""
    try:
        from narrative_assistant.persistence.history import HistoryManager
        history = HistoryManager(project_id)
        ok, reason = history.can_undo(entry_id)
        return ApiResponse(
            success=True,
            data={"can_undo": ok, "reason": reason},
        )
    except Exception as e:
        logger.error(f"Error checking can_undo: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error verificando undo")


@router.post("/api/projects/{project_id}/undo", response_model=ApiResponse)
def undo_last(project_id: int):
    """Deshace la última acción (Ctrl+Z)."""
    try:
        from narrative_assistant.persistence.history import HistoryManager
        history = HistoryManager(project_id)
        result = history.undo_last()

        if result.success:
            return ApiResponse(
                success=True,
                data={
                    "entry_id": result.entry_id,
                    "message": result.message,
                },
                message=result.message,
            )
        else:
            return ApiResponse(
                success=False,
                error=result.message,
                data={"conflicts": result.conflicts} if result.conflicts else None,
            )
    except Exception as e:
        logger.error(f"Error undoing last action: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error deshaciendo acción")


@router.post("/api/projects/{project_id}/undo/{entry_id}", response_model=ApiResponse)
def undo_entry(project_id: int, entry_id: int):
    """Deshace una acción específica por ID (undo selectivo)."""
    try:
        from narrative_assistant.persistence.history import HistoryManager
        history = HistoryManager(project_id)
        result = history.undo(entry_id)

        if result.success:
            return ApiResponse(
                success=True,
                data={
                    "entry_id": result.entry_id,
                    "message": result.message,
                },
                message=result.message,
            )
        else:
            return ApiResponse(
                success=False,
                error=result.message,
                data={"conflicts": result.conflicts} if result.conflicts else None,
            )
    except Exception as e:
        logger.error(f"Error undoing entry {entry_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error deshaciendo acción")


@router.post("/api/projects/{project_id}/undo-batch/{batch_id}", response_model=ApiResponse)
def undo_batch(project_id: int, batch_id: str):
    """Deshace todas las acciones de una operación compuesta (batch)."""
    try:
        from narrative_assistant.persistence.history import HistoryManager
        history = HistoryManager(project_id)
        result = history.undo_batch(batch_id)

        if result.success:
            return ApiResponse(
                success=True,
                data={"batch_id": batch_id, "message": result.message},
                message=result.message,
            )
        else:
            return ApiResponse(
                success=False,
                error=result.message,
                data={"conflicts": result.conflicts} if result.conflicts else None,
            )
    except Exception as e:
        logger.error(f"Error undoing batch {batch_id}: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error deshaciendo operación")
