"""
Mapper entre correction_config y dialogue_style_preference.

Convierte parámetros de configuración de correcciones (dialogue_dash, quote_style)
al formato esperado por el sistema de validación de estilo de diálogo.
"""

import logging

logger = logging.getLogger(__name__)


def map_correction_config_to_dialogue_preference(
    dialogue_dash: str | None,
    quote_style: str | None,
) -> str:
    """
    Mapea configuración de correcciones a preferencia de estilo de diálogo.

    Args:
        dialogue_dash: Tipo de guión (em, en, hyphen, none)
        quote_style: Tipo de comillas (angular, curly, straight, none)

    Returns:
        Preferencia de diálogo: dash, guillemets, quotes, quotes_typographic, no_check
    """
    # Prioridad 1: Si usa guiones (cualquier tipo)
    if dialogue_dash and dialogue_dash != "none":
        return "dash"

    # Prioridad 2: Si usa comillas
    if quote_style:
        if quote_style == "angular":
            return "guillemets"
        elif quote_style == "curly":
            return "quotes_typographic"
        elif quote_style == "straight":
            return "quotes"

    # Default: raya española (más común en español)
    logger.debug(
        f"No dialogue preference found in config (dash={dialogue_dash}, "
        f"quote={quote_style}), defaulting to 'dash'"
    )
    return "dash"


def map_dialogue_preference_to_correction_config(preference: str) -> tuple[str, str]:
    """
    Mapea preferencia de diálogo a configuración de correcciones.

    Args:
        preference: Preferencia de diálogo (dash, guillemets, quotes, quotes_typographic)

    Returns:
        Tuple (dialogue_dash, quote_style)
    """
    if preference == "dash":
        return ("em", "none")
    elif preference == "guillemets":
        return ("none", "angular")
    elif preference == "quotes":
        return ("none", "straight")
    elif preference == "quotes_typographic":
        return ("none", "curly")
    elif preference == "no_check":
        return ("none", "none")

    # Default
    return ("em", "none")
