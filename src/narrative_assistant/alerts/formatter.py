"""
Utilidades para formatear alertas y contexto.

Centraliza la lógica de formateo de texto para alertas,
evitando duplicación en AlertEngine.
"""


class AlertFormatter:
    """
    Formateador de texto para alertas.

    Centraliza la lógica de:
    - Truncar texto largo
    - Formatear contexto con comillas tipográficas
    - Formatear excerpts y explicaciones
    """

    DEFAULT_MAX_LENGTH = 100

    @staticmethod
    def truncate(text: str, max_length: int = DEFAULT_MAX_LENGTH) -> str:
        """
        Trunca texto largo añadiendo puntos suspensivos.

        Args:
            text: Texto a truncar
            max_length: Longitud máxima (default: 100)

        Returns:
            Texto truncado o original si es menor que max_length
        """
        if len(text) <= max_length:
            return text
        return f"{text[:max_length]}..."

    @staticmethod
    def format_context(
        text: str,
        prefix: str = "En contexto",
        max_length: int = DEFAULT_MAX_LENGTH,
        use_quotes: bool = True,
    ) -> str:
        """
        Formatea un texto como contexto con comillas tipográficas.

        Args:
            text: Texto del contexto
            prefix: Prefijo antes del contexto (ej: "En contexto", "Contexto")
            max_length: Longitud máxima antes de truncar
            use_quotes: Si usar comillas tipográficas «»

        Returns:
            Texto formateado: "En contexto: «texto truncado...»"
        """
        if not text:
            return ""

        truncated = AlertFormatter.truncate(text, max_length)

        if use_quotes:
            return f"{prefix}: «{truncated}»"
        return f"{prefix}: {truncated}"

    @staticmethod
    def format_explanation_with_context(
        base_explanation: str, context: str, max_length: int = DEFAULT_MAX_LENGTH
    ) -> str:
        """
        Añade contexto a una explicación si está disponible.

        Args:
            base_explanation: Explicación base de la alerta
            context: Contexto opcional a añadir
            max_length: Longitud máxima del contexto

        Returns:
            Explicación con contexto añadido, o explicación base si no hay contexto
        """
        if not context:
            return base_explanation

        formatted_context = AlertFormatter.format_context(
            context, prefix="Contexto", max_length=max_length
        )
        return f"{base_explanation}. {formatted_context}"

    @staticmethod
    def format_excerpt(
        text: str,
        max_length: int = 200,
        context_before: str | None = None,
        context_after: str | None = None,
    ) -> str:
        """
        Formatea un excerpt de texto, opcionalmente con contexto antes/después.

        Args:
            text: Texto principal
            max_length: Longitud máxima
            context_before: Texto antes (para transiciones)
            context_after: Texto después (para transiciones)

        Returns:
            Excerpt formateado
        """
        if context_before and context_after:
            # Formato para transiciones: "...antes | después..."
            before_part = context_before[-50:] if len(context_before) > 50 else context_before
            after_part = context_after[:50] if len(context_after) > 50 else context_after
            return f"...{before_part} | {after_part}..."

        return AlertFormatter.truncate(text, max_length)

    @staticmethod
    def format_attribute_inconsistency(
        attr_name: str, value1: str, value2: str, entity_name: str
    ) -> dict:
        """
        Formatea el título y descripción para una inconsistencia de atributo.

        Args:
            attr_name: Nombre del atributo (display name)
            value1: Primer valor encontrado
            value2: Segundo valor encontrado
            entity_name: Nombre de la entidad

        Returns:
            Dict con 'title' y 'description'
        """
        return {
            "title": f"Inconsistencia en {attr_name}",
            "description": f"{entity_name} tiene valores contradictorios: «{value1}» vs «{value2}»",
        }

    @staticmethod
    def format_sources_for_extra_data(
        value1: str, value1_source: dict, value2: str, value2_source: dict
    ) -> list:
        """
        Formatea las fuentes para el extra_data de una alerta de inconsistencia.

        Args:
            value1: Primer valor
            value1_source: Info de ubicación del primer valor
            value2: Segundo valor
            value2_source: Info de ubicación del segundo valor

        Returns:
            Lista de dicts con info de cada fuente
        """

        def get_excerpt(source: dict) -> str:
            return source.get("text", source.get("excerpt", ""))

        return [
            {
                "value": value1,
                "chapter": value1_source.get("chapter"),
                "position": value1_source.get("position"),
                "excerpt": get_excerpt(value1_source),
            },
            {
                "value": value2,
                "chapter": value2_source.get("chapter"),
                "position": value2_source.get("position"),
                "excerpt": get_excerpt(value2_source),
            },
        ]


# Instancia singleton para uso conveniente
_formatter: AlertFormatter | None = None


def get_alert_formatter() -> AlertFormatter:
    """Obtiene la instancia singleton del formateador."""
    global _formatter
    if _formatter is None:
        _formatter = AlertFormatter()
    return _formatter
