"""
Utilidades generales del core.

Funciones de ayuda para formateo, conversión y otras operaciones comunes.
"""


def format_duration(seconds: float, threshold_minutes: int = 180) -> str:
    """
    Formatea una duración en segundos de forma legible.

    - Si seconds <= threshold (default 180), muestra en segundos
    - Si seconds > threshold, muestra en minutos y segundos

    Args:
        seconds: Duración en segundos
        threshold_minutes: Umbral en segundos para cambiar a formato minutos (default 180)

    Returns:
        String formateado: "45.23s" o "12m 34s"

    Examples:
        >>> format_duration(45.23)
        '45.2s'
        >>> format_duration(180.0)
        '180.0s'
        >>> format_duration(181.0)
        '3m 1s'
        >>> format_duration(2735.8)
        '45m 36s'
    """
    if seconds <= threshold_minutes:
        return f"{seconds:.1f}s"

    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    return f"{minutes}m {remaining_seconds}s"


def format_duration_verbose(seconds: float, threshold_minutes: int = 180) -> str:
    """
    Formatea una duración de forma más descriptiva.

    Similar a format_duration pero con texto completo.

    Args:
        seconds: Duración en segundos
        threshold_minutes: Umbral para cambiar formato

    Returns:
        String formateado: "45.2 segundos" o "12 minutos y 34 segundos"

    Examples:
        >>> format_duration_verbose(45.23)
        '45.2 segundos'
        >>> format_duration_verbose(2735.8)
        '45 minutos y 36 segundos'
    """
    if seconds <= threshold_minutes:
        return f"{seconds:.1f} segundos"

    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)

    if remaining_seconds == 0:
        return f"{minutes} minutos"
    return f"{minutes} minutos y {remaining_seconds} segundos"
