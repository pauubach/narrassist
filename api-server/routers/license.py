"""
Router: license

Endpoints para gestion de licencias, dispositivos, cuotas (paginas) y features por tier.
"""

from fastapi import APIRouter, Body

import deps
from deps import ApiResponse, DeviceDeactivationRequest, LicenseActivationRequest
from deps import logger

router = APIRouter()


def get_license_verifier():
    """Obtiene el LicenseVerifier, retorna None si el modulo de licencias no esta disponible."""
    try:
        from narrative_assistant.licensing.verification import LicenseVerifier
        return LicenseVerifier()
    except Exception:
        return None


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
                    "features": [],
                    "devices_used": 0,
                    "devices_max": 0,
                    "pages_used": 0,
                    "pages_max": 0,
                    "pages_remaining": 0,
                    "expires_at": None,
                    "is_trial": False,
                    "offline_days_remaining": None,
                }
            )

        result = verifier.verify()

        if result.is_failure:
            return ApiResponse(
                success=True,
                data={
                    "status": "no_license",
                    "error": str(result.error),
                    "tier": None,
                    "features": [],
                }
            )

        verification = result.value
        license_obj = verification.license

        if license_obj is None:
            return ApiResponse(
                success=True,
                data={
                    "status": "no_license",
                    "tier": None,
                    "features": [],
                }
            )

        return ApiResponse(
            success=True,
            data={
                "status": license_obj.status.value,
                "tier": license_obj.tier.value,
                "features": [f.value for f in sorted(license_obj.features, key=lambda x: x.value)],
                "devices_used": license_obj.active_device_count,
                "devices_max": license_obj.limits.max_devices,
                "pages_used": (
                    license_obj.limits.max_pages_per_month - verification.quota_remaining
                    if verification.quota_remaining is not None
                    else 0
                ),
                "pages_max": license_obj.limits.max_pages_per_month,
                "pages_remaining": verification.quota_remaining,
                "unlimited": license_obj.limits.is_unlimited,
                "expires_at": license_obj.expires_at.isoformat() if license_obj.expires_at else None,
                "is_trial": (
                    license_obj.subscription.status == "trialing"
                    if license_obj.subscription
                    else False
                ),
                "offline_days_remaining": (
                    license_obj.grace_period_remaining.days
                    if license_obj.grace_period_remaining
                    else None
                ),
            }
        )

    except Exception as e:
        logger.error(f"Error getting license status: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


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

        license_obj = result.value
        return ApiResponse(
            success=True,
            data={
                "message": "Licencia activada correctamente",
                "tier": license_obj.tier.value,
                "features": [f.value for f in sorted(license_obj.features, key=lambda x: x.value)],
            }
        )

    except Exception as e:
        logger.error(f"Error activating license: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


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

        result = verifier.verify(force_online=True)

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        return ApiResponse(
            success=True,
            data={
                "valid": result.value.is_valid,
                "message": result.value.message,
            }
        )

    except Exception as e:
        logger.error(f"Error verifying license: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


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

        result = verifier.verify()

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        license_obj = result.value.license
        if not license_obj:
            return ApiResponse(success=False, error="No se encontro licencia")

        return ApiResponse(
            success=True,
            data={
                "devices": [
                    {
                        "id": d.id,
                        "fingerprint": d.hardware_fingerprint[:8] + "...",
                        "name": d.device_name,
                        "status": d.status.value,
                        "last_seen": d.last_seen_at.isoformat() if d.last_seen_at else None,
                        "is_current": d.is_current_device,
                    }
                    for d in license_obj.devices
                ],
                "max_devices": license_obj.limits.max_devices,
            }
        )

    except Exception as e:
        logger.error(f"Error getting devices: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


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
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/license/usage", response_model=ApiResponse)
async def get_license_usage():
    """
    Obtiene el uso de la licencia en el periodo actual (paginas).

    Returns:
        ApiResponse con estadisticas de uso en paginas
    """
    try:
        verifier = get_license_verifier()
        if not verifier:
            return ApiResponse(success=False, error="Modulo de licencias no disponible")

        result = verifier.verify()

        if result.is_failure:
            return ApiResponse(success=False, error=str(result.error))

        verification = result.value
        license_obj = verification.license

        if not license_obj:
            return ApiResponse(success=False, error="No se encontro licencia")

        limits = license_obj.limits
        quota_remaining = verification.quota_remaining

        return ApiResponse(
            success=True,
            data={
                "pages_used": (
                    limits.max_pages_per_month - quota_remaining
                    if quota_remaining is not None
                    else 0
                ),
                "pages_max": limits.max_pages_per_month,
                "pages_remaining": quota_remaining if quota_remaining is not None else -1,
                "unlimited": limits.is_unlimited,
            }
        )

    except Exception as e:
        logger.error(f"Error getting usage: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.post("/api/license/record-usage", response_model=ApiResponse)
async def record_usage(project_id: int = Body(..., embed=True)):
    """
    Registra el uso de un manuscrito contra la cuota de paginas.

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

        result = verifier.check_quota()

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
                "pages_remaining": result.value,
            }
        )

    except Exception as e:
        logger.error(f"Error recording usage: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")


@router.get("/api/license/check-feature/{feature_name}", response_model=ApiResponse)
async def check_feature_access(feature_name: str):
    """
    Verifica si el usuario tiene acceso a una feature segun su tier.

    Args:
        feature_name: Nombre de la feature (attribute_consistency, character_profiling, etc.)

    Returns:
        ApiResponse indicando si tiene acceso
    """
    try:
        verifier = get_license_verifier()
        if not verifier:
            # Sin verificador, permitir todo (desarrollo)
            return ApiResponse(success=True, data={"has_access": True})

        from narrative_assistant.licensing.models import LicenseFeature

        try:
            feature = LicenseFeature(feature_name)
        except ValueError:
            return ApiResponse(
                success=False,
                error=f"Feature desconocida: {feature_name}",
            )

        result = verifier.check_feature(feature)

        if result.is_failure:
            return ApiResponse(
                success=True,
                data={
                    "has_access": False,
                    "reason": str(result.error),
                    "required_tier": "profesional",
                }
            )

        return ApiResponse(
            success=True,
            data={
                "has_access": True,
                "feature": feature_name,
            }
        )

    except Exception as e:
        logger.error(f"Error checking feature access: {e}", exc_info=True)
        return ApiResponse(success=False, error="Error interno del servidor")
