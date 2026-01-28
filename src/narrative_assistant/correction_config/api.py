"""
API de alto nivel para el sistema de configuración de corrección.

Proporciona funciones fáciles de usar desde el API server y frontend.
"""

from typing import Optional

from .models import CorrectionConfig
from .registry import (
    TYPES_REGISTRY,
    SUBTYPES_REGISTRY,
    get_correction_config,
)


def get_types_with_subtypes() -> list[dict]:
    """
    Obtiene la lista completa de tipos con sus subtipos.

    Formato optimizado para el frontend (selector de dos columnas).

    Returns:
        Lista de tipos, cada uno con sus subtipos anidados

    Example:
        >>> types = get_types_with_subtypes()
        >>> types[0]
        {
            "code": "FIC",
            "name": "Ficción",
            "description": "Novela, relatos...",
            "icon": "pi-book",
            "color": "#6366f1",
            "subtypes": [
                {"code": "FIC_LIT", "name": "Novela literaria"},
                {"code": "FIC_GEN", "name": "Novela de género"},
                ...
            ]
        }
    """
    result = []

    for type_code, type_info in TYPES_REGISTRY.items():
        # Buscar subtipos de este tipo
        subtypes = []
        for subtype_code, subtype_info in SUBTYPES_REGISTRY.items():
            if subtype_info.get("parent") == type_code:
                subtypes.append({
                    "code": subtype_code,
                    "name": subtype_info.get("name", subtype_code),
                })

        result.append({
            "code": type_code,
            "name": type_info.get("name", type_code),
            "description": type_info.get("description", ""),
            "icon": type_info.get("icon", "pi-file"),
            "color": type_info.get("color", "#6366f1"),
            "subtypes": subtypes,
        })

    return result


def get_config_for_project(
    type_code: str,
    subtype_code: Optional[str] = None,
    customizations: Optional[dict] = None
) -> dict:
    """
    Obtiene la configuración de corrección para un proyecto.

    Args:
        type_code: Código del tipo de documento
        subtype_code: Código del subtipo (opcional)
        customizations: Dict con overrides personalizados (opcional)
            Formato: {"dialog": {"enabled": False}, "repetition": {"tolerance": "high"}}

    Returns:
        Dict con la configuración completa serializada
    """
    config = get_correction_config(type_code, subtype_code, customizations)
    return config.to_dict()


def get_effective_config(
    type_code: str,
    subtype_code: Optional[str] = None
) -> CorrectionConfig:
    """
    Obtiene el objeto CorrectionConfig efectivo.

    Útil para uso interno en el backend.

    Args:
        type_code: Código del tipo
        subtype_code: Código del subtipo (opcional)

    Returns:
        CorrectionConfig con herencia aplicada
    """
    return get_correction_config(type_code, subtype_code)


def get_type_info(type_code: str) -> Optional[dict]:
    """
    Obtiene información de un tipo específico.

    Args:
        type_code: Código del tipo

    Returns:
        Dict con info del tipo o None si no existe
    """
    return TYPES_REGISTRY.get(type_code.upper())


def get_subtype_info(subtype_code: str) -> Optional[dict]:
    """
    Obtiene información de un subtipo específico.

    Args:
        subtype_code: Código del subtipo

    Returns:
        Dict con info del subtipo o None si no existe
    """
    return SUBTYPES_REGISTRY.get(subtype_code.upper())


def validate_type_subtype(type_code: str, subtype_code: Optional[str] = None) -> tuple[bool, str]:
    """
    Valida que un tipo y subtipo sean compatibles.

    Args:
        type_code: Código del tipo
        subtype_code: Código del subtipo (opcional)

    Returns:
        Tuple (is_valid, error_message)
    """
    type_code = type_code.upper()

    # Validar tipo
    if type_code not in TYPES_REGISTRY:
        return False, f"Tipo desconocido: {type_code}"

    # Si no hay subtipo, es válido
    if not subtype_code:
        return True, ""

    subtype_code = subtype_code.upper()

    # Validar subtipo
    if subtype_code not in SUBTYPES_REGISTRY:
        return False, f"Subtipo desconocido: {subtype_code}"

    # Validar que el subtipo pertenece al tipo
    subtype_parent = SUBTYPES_REGISTRY[subtype_code].get("parent")
    if subtype_parent != type_code:
        return False, f"El subtipo {subtype_code} no pertenece al tipo {type_code}"

    return True, ""


def get_config_diff(
    type_code: str,
    subtype_code: Optional[str] = None
) -> dict:
    """
    Obtiene las diferencias entre la configuración del tipo y subtipo.

    Útil para mostrar en la UI qué parámetros han sido sobrescritos.

    Args:
        type_code: Código del tipo
        subtype_code: Código del subtipo

    Returns:
        Dict con parámetros sobrescritos y sus valores
    """
    from .registry import get_type_defaults, get_subtype_overrides

    type_config = get_type_defaults(type_code)
    subtype_overrides = get_subtype_overrides(subtype_code) if subtype_code else {}

    diff = {
        "type_config": type_config,
        "subtype_overrides": subtype_overrides,
        "effective_overrides": [],
    }

    # Identificar qué parámetros cambian
    for category, values in subtype_overrides.items():
        if isinstance(values, dict):
            for param, value in values.items():
                type_value = type_config.get(category, {}).get(param)
                if type_value != value:
                    diff["effective_overrides"].append({
                        "category": category,
                        "parameter": param,
                        "type_value": type_value,
                        "subtype_value": value,
                    })

    return diff
