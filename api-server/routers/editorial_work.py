"""
Router: editorial_work — Export/Import de trabajo editorial (.narrassist)

Permite a equipos editoriales compartir decisiones (fusiones, descartes,
atributos verificados, reglas de supresión) sin transferir texto del manuscrito.

Endpoints:
  POST /api/projects/{id}/export-work        → descarga .narrassist
  POST /api/projects/{id}/import-work/preview → preview de importación
  POST /api/projects/{id}/import-work/confirm → aplica importación
"""

import json
import tempfile
from pathlib import Path

import deps
from deps import ApiResponse, logger
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

router = APIRouter()

MAX_IMPORT_BYTES = 10 * 1024 * 1024  # 10 MB


# ── Request models ──────────────────────────────────────────


class ImportConfirmRequest(BaseModel):
    """Body para confirmar una importación."""

    import_data: dict
    import_entity_merges: bool = True
    import_alert_decisions: bool = True
    import_verified_attributes: bool = True
    import_suppression_rules: bool = True
    conflict_overrides: dict[str, str] | None = None


# ── Helpers ─────────────────────────────────────────────────


def _check_export_import_feature() -> ApiResponse | None:
    """Verifica acceso a la feature EXPORT_IMPORT. Retorna error o None si OK."""
    try:
        from narrative_assistant.licensing.models import LicenseFeature
        from narrative_assistant.licensing.verification import LicenseVerifier

        verifier = LicenseVerifier()
        result = verifier.check_feature(LicenseFeature.EXPORT_IMPORT)
        if result.is_failure:
            return ApiResponse(
                success=False,
                error="Esta función requiere el plan Editorial. "
                "Actualice su licencia para usar export/import de trabajo editorial.",
            )
    except Exception:
        # Sin módulo de licensing (dev) → permitir
        pass
    return None


def _get_project_or_error(project_id: int):
    """Obtiene proyecto o lanza HTTPException 404."""
    if not deps.project_manager:
        raise HTTPException(status_code=503, detail="Project manager not initialized")
    result = deps.project_manager.get(project_id)
    if result.is_failure:
        raise HTTPException(
            status_code=404, detail=f"Proyecto {project_id} no encontrado"
        )
    return result.value


# ── Endpoints ───────────────────────────────────────────────


@router.post("/api/projects/{project_id}/export-work")
async def export_work(project_id: int):
    """
    Exporta el trabajo editorial del proyecto como archivo .narrassist.

    Genera un JSON con: entity merges, alert decisions, verified attributes
    y suppression rules. NO incluye texto del manuscrito.

    Returns:
        Archivo .narrassist para descarga
    """
    from fastapi.responses import Response

    try:
        # Feature gate
        gate_error = _check_export_import_feature()
        if gate_error:
            return gate_error

        project = _get_project_or_error(project_id)

        from narrative_assistant.persistence.editorial_work import (
            export_editorial_work,
        )

        result = export_editorial_work(
            project_id=project_id,
            project_name=project.name,
            project_fingerprint=getattr(project, "document_fingerprint", "") or "",
            exported_by="",
        )

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        # Serializar a JSON
        json_bytes = json.dumps(result.value, ensure_ascii=False, indent=2).encode(
            "utf-8"
        )

        # Nombre de archivo seguro
        safe_name = (
            "".join(
                c if c.isalnum() or c in (" ", "-", "_") else "_" for c in project.name
            )
            .strip()
            .replace(" ", "_")
            .lower()
        )
        filename = f"trabajo_editorial_{safe_name}.narrassist"

        logger.info(
            f"Exported editorial work for project {project_id}: {len(json_bytes)} bytes"
        )

        return Response(
            content=json_bytes,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting editorial work: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post(
    "/api/projects/{project_id}/import-work/preview", response_model=ApiResponse
)
async def import_work_preview(
    project_id: int,
    file: UploadFile = File(...),
):
    """
    Preview de importación: analiza el archivo .narrassist y muestra
    qué se aplicará, qué ya está hecho y qué conflictos hay.

    Args:
        project_id: ID del proyecto destino
        file: Archivo .narrassist

    Returns:
        ApiResponse con preview (estadísticas, conflictos, warnings)
    """
    try:
        # Feature gate
        gate_error = _check_export_import_feature()
        if gate_error:
            return gate_error

        _get_project_or_error(project_id)

        # Leer y validar archivo
        content = await file.read()
        if len(content) > MAX_IMPORT_BYTES:
            return ApiResponse(
                success=False,
                error=f"El archivo excede el límite de {MAX_IMPORT_BYTES // (1024 * 1024)} MB",
            )

        try:
            import_data = json.loads(content.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return ApiResponse(
                success=False,
                error=f"El archivo no contiene JSON válido: {e}",
            )

        from narrative_assistant.persistence.editorial_work import preview_import

        result = preview_import(project_id, import_data)

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        # Devolver preview + import_data para el paso confirm
        preview_dict = result.value.to_dict()
        preview_dict["import_data"] = import_data

        return ApiResponse(success=True, data=preview_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing import: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post(
    "/api/projects/{project_id}/import-work/confirm", response_model=ApiResponse
)
async def import_work_confirm(
    project_id: int,
    body: ImportConfirmRequest,
):
    """
    Confirma y aplica la importación del trabajo editorial.

    Args:
        project_id: ID del proyecto destino
        body: Datos de importación + toggles por sección + overrides de conflictos

    Returns:
        ApiResponse con estadísticas de lo aplicado
    """
    try:
        # Feature gate
        gate_error = _check_export_import_feature()
        if gate_error:
            return gate_error

        _get_project_or_error(project_id)

        from narrative_assistant.persistence.editorial_work import confirm_import

        result = confirm_import(
            project_id=project_id,
            import_data=body.import_data,
            import_entity_merges=body.import_entity_merges,
            import_alert_decisions=body.import_alert_decisions,
            import_verified_attributes=body.import_verified_attributes,
            import_suppression_rules=body.import_suppression_rules,
            conflict_overrides=body.conflict_overrides,
        )

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        return ApiResponse(
            success=True,
            data=result.value,
            message="Trabajo editorial importado correctamente",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming import: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")
