"""
Router: license
"""

from fastapi import APIRouter
import deps
from deps import logger
from deps import ApiResponse
from fastapi import Body
from fastapi import Request
from deps import DeviceDeactivationRequest, LicenseActivationRequest

router = APIRouter()

@router.get("/api/license/status", response_model=ApiResponse)
async def get_license_status():
    """
    Obtiene el estado actual de la licencia.

    Returns:
        ApiResponse con informacion de la licencia activa
    """
    try:
        verifier = get_license_verifier()
        if not verifier:
            return ApiResponse(
                success=True,
                data={
                    "status": "no_license",
                    "tier": None,
                    "modules": [],
                    "devices_used": 0,
                    "devices_max": 0,
                    "manuscripts_used": 0,
                    "manuscripts_max": 0,
                    "expires_at": None,
                    "is_trial": False,
                    "offline_days_remaining": None,
                }
            )

        result = verifier.get_current_license()

        if result.is_failure:
            return ApiResponse(
                success=True,
                data={
                    "status": "no_license",
                    "error": str(result.error),
                    "tier": None,
                    "modules": [],
                }
            )

        license_info = result.value
        return ApiResponse(
            success=True,
            data={
                "status": "active" if license_info.is_active else "expired",
                "tier": license_info.tier.value if license_info.tier else None,
                "modules": [m.value for m in license_info.modules] if license_info.modules else [],
                "devices_used": license_info.devices_used,
                "devices_max": license_info.max_devices,
                "manuscripts_used": license_info.manuscripts_used_this_period,
                "manuscripts_max": license_info.manuscripts_per_month,
                "expires_at": license_info.expires_at.isoformat() if license_info.expires_at else None,
                "is_trial": license_info.is_trial,
                "offline_days_remaining": license_info.offline_grace_days_remaining,
            }
        )

    except Exception as e:
        logger.error(f"Error getting license status: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.post("/api/license/activate", response_model=ApiResponse)
async def activate_license(request: LicenseActivationRequest):
    """
    Activa una licencia con la clave proporcionada.

    Args:
        request: Clave de licencia

    Returns:
        ApiResponse con resultado de la activacion
    """
    try:
        verifier = get_license_verifier()
        if not verifier:
            return ApiResponse(success=False, error="Modulo de licencias no disponible")

        result = verifier.activate_license(request.license_key)

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        license_info = result.value
        return ApiResponse(
            success=True,
            data={
                "message": "Licencia activada correctamente",
                "tier": license_info.tier.value if license_info.tier else None,
                "modules": [m.value for m in license_info.modules] if license_info.modules else [],
            }
        )

    except Exception as e:
        logger.error(f"Error activating license: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.post("/api/license/verify", response_model=ApiResponse)
async def verify_license():
    """
    Verifica la licencia actual (online si es posible).

    Returns:
        ApiResponse con resultado de la verificacion
    """
    try:
        verifier = get_license_verifier()
        if not verifier:
            return ApiResponse(success=False, error="Modulo de licencias no disponible")

        result = verifier.verify_license()

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        return ApiResponse(
            success=True,
            data={
                "valid": result.value.is_valid,
                "message": result.value.message,
                "verified_online": result.value.verified_online,
            }
        )

    except Exception as e:
        logger.error(f"Error verifying license: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/license/devices", response_model=ApiResponse)
async def get_license_devices():
    """
    Obtiene la lista de dispositivos registrados en la licencia.

    Returns:
        ApiResponse con lista de dispositivos
    """
    try:
        verifier = get_license_verifier()
        if not verifier:
            return ApiResponse(success=False, error="Modulo de licencias no disponible")

        result = verifier.get_devices()

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        devices = result.value
        return ApiResponse(
            success=True,
            data={
                "devices": [
                    {
                        "fingerprint": d.fingerprint[:8] + "...",  # Parcial por privacidad
                        "name": d.name,
                        "status": d.status.value,
                        "last_seen": d.last_seen.isoformat() if d.last_seen else None,
                        "is_current": d.is_current,
                    }
                    for d in devices
                ],
                "max_devices": verifier.max_devices,
            }
        )

    except Exception as e:
        logger.error(f"Error getting devices: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.post("/api/license/devices/deactivate", response_model=ApiResponse)
async def deactivate_device(request: DeviceDeactivationRequest):
    """
    Desactiva un dispositivo de la licencia.

    Args:
        request: Fingerprint del dispositivo a desactivar

    Returns:
        ApiResponse con resultado de la desactivacion
    """
    try:
        verifier = get_license_verifier()
        if not verifier:
            return ApiResponse(success=False, error="Modulo de licencias no disponible")

        result = verifier.deactivate_device(request.device_fingerprint)

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        return ApiResponse(
            success=True,
            data={
                "message": "Dispositivo desactivado",
                "cooldown_hours": 48,
            }
        )

    except Exception as e:
        logger.error(f"Error deactivating device: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/license/usage", response_model=ApiResponse)
async def get_license_usage():
    """
    Obtiene el uso de la licencia en el periodo actual.

    Returns:
        ApiResponse con estadisticas de uso
    """
    try:
        verifier = get_license_verifier()
        if not verifier:
            return ApiResponse(success=False, error="Modulo de licencias no disponible")

        result = verifier.get_usage()

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        usage = result.value
        return ApiResponse(
            success=True,
            data={
                "period_start": usage.period_start.isoformat(),
                "period_end": usage.period_end.isoformat(),
                "manuscripts_used": usage.manuscripts_used,
                "manuscripts_limit": usage.manuscripts_limit,
                "manuscripts_remaining": max(0, usage.manuscripts_limit - usage.manuscripts_used),
                "unlimited": usage.manuscripts_limit == -1,
            }
        )

    except Exception as e:
        logger.error(f"Error getting usage: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.post("/api/license/record-manuscript", response_model=ApiResponse)
async def record_manuscript_usage(project_id: int = Body(..., embed=True)):
    """
    Registra el uso de un manuscrito contra la cuota.

    Args:
        project_id: ID del proyecto/manuscrito

    Returns:
        ApiResponse con resultado del registro
    """
    try:
        verifier = get_license_verifier()
        if not verifier:
            # Sin verificador, permitir uso (desarrollo)
            return ApiResponse(success=True, data={"allowed": True})

        result = verifier.record_manuscript_usage(project_id)

        if result.is_failure:
            error = result.error
            return ApiResponse(
                success=False,
                error=str(error),
                data={"allowed": False, "reason": error.__class__.__name__}
            )

        return ApiResponse(
            success=True,
            data={
                "allowed": True,
                "manuscripts_remaining": result.value.manuscripts_remaining,
            }
        )

    except Exception as e:
        logger.error(f"Error recording manuscript usage: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


@router.get("/api/license/check-module/{module_name}", response_model=ApiResponse)
async def check_module_access(module_name: str):
    """
    Verifica si el usuario tiene acceso a un módulo específico.

    Args:
        module_name: Nombre del módulo (CORE, NARRATIVA, VOZ_ESTILO, AVANZADO)

    Returns:
        ApiResponse indicando si tiene acceso
    """
    try:
        verifier = get_license_verifier()
        if not verifier:
            # Sin verificador, permitir todo (desarrollo)
            return ApiResponse(success=True, data={"has_access": True})

        result = verifier.check_module_access(module_name)

        if result.is_failure:
            return ApiResponse(
                success=True,
                data={
                    "has_access": False,
                    "reason": str(result.error),
                }
            )

        return ApiResponse(
            success=True,
            data={
                "has_access": True,
                "module": module_name,
            }
        )

    except Exception as e:
        logger.error(f"Error checking module access: {e}", exc_info=True)
        return ApiResponse(success=False, error=str(e))


