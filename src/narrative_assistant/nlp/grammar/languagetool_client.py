"""
Cliente para LanguageTool local.

LanguageTool es una herramienta de análisis gramatical open-source que
proporciona +2000 reglas para español. Se ejecuta localmente como servidor
Java en localhost:8081.

Ventajas sobre reglas regex:
- Análisis contextual (distingue "de que" correcto vs incorrecto)
- Más de 2000 reglas para español
- Detección de concordancia compleja
- Sugerencias de corrección precisas

Uso:
    from narrative_assistant.nlp.grammar.languagetool_client import (
        get_languagetool_client,
        is_languagetool_available,
    )

    if is_languagetool_available():
        client = get_languagetool_client()
        result = client.check("Pienso de que vendrá.")
        for match in result.matches:
            print(f"Error: {match.message}")
            print(f"Sugerencia: {match.replacements}")
"""

import logging
import threading
from dataclasses import dataclass, field
from typing import Optional
import json

from ...core.errors import NLPError, ErrorSeverity
from ...core.result import Result

logger = logging.getLogger(__name__)

# URL por defecto del servidor LanguageTool
DEFAULT_LT_URL = "http://localhost:8081/v2"
DEFAULT_LANGUAGE = "es"
DEFAULT_TIMEOUT = 30  # segundos


@dataclass
class LTMatch:
    """Un error detectado por LanguageTool."""

    message: str                          # Mensaje de error
    short_message: str = ""               # Mensaje corto
    offset: int = 0                       # Posición de inicio en el texto
    length: int = 0                       # Longitud del error
    replacements: list[str] = field(default_factory=list)  # Sugerencias
    rule_id: str = ""                     # ID de la regla (ej: "DEQUEISMO")
    rule_description: str = ""            # Descripción de la regla
    rule_category: str = ""               # Categoría (Grammar, Typos, etc.)
    context_text: str = ""                # Texto de contexto
    context_offset: int = 0               # Offset en el contexto

    def to_dict(self) -> dict:
        """Convertir a diccionario."""
        return {
            "message": self.message,
            "short_message": self.short_message,
            "offset": self.offset,
            "length": self.length,
            "replacements": self.replacements,
            "rule_id": self.rule_id,
            "rule_description": self.rule_description,
            "rule_category": self.rule_category,
            "context_text": self.context_text,
            "context_offset": self.context_offset,
        }


@dataclass
class LTCheckResult:
    """Resultado de verificación de LanguageTool."""

    matches: list[LTMatch] = field(default_factory=list)
    language_code: str = ""
    language_name: str = ""
    detected_language: str = ""

    @property
    def has_errors(self) -> bool:
        return len(self.matches) > 0

    @property
    def error_count(self) -> int:
        return len(self.matches)

    def to_dict(self) -> dict:
        """Convertir a diccionario."""
        return {
            "matches": [m.to_dict() for m in self.matches],
            "language_code": self.language_code,
            "language_name": self.language_name,
            "detected_language": self.detected_language,
            "has_errors": self.has_errors,
            "error_count": self.error_count,
        }


@dataclass
class LTClientError(NLPError):
    """Error del cliente LanguageTool."""

    original_error: str = ""
    message: str = field(init=False)
    severity: ErrorSeverity = field(default=ErrorSeverity.RECOVERABLE, init=False)

    def __post_init__(self):
        self.message = f"LanguageTool client error: {self.original_error}"
        super().__post_init__()


class LanguageToolClient:
    """
    Cliente para el servidor LanguageTool local.

    LanguageTool debe estar ejecutándose en localhost:8081.
    Ver: scripts/setup_languagetool.py para instalación.
    """

    def __init__(
        self,
        url: str = DEFAULT_LT_URL,
        language: str = DEFAULT_LANGUAGE,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """
        Inicializar cliente.

        Args:
            url: URL base del servidor LT (default: http://localhost:8081/v2)
            language: Código de idioma (default: es)
            timeout: Timeout en segundos para requests
        """
        self.url = url.rstrip("/")
        self.language = language
        self.timeout = timeout
        self._available: Optional[bool] = None

    def is_available(self, force_check: bool = False) -> bool:
        """
        Verificar si el servidor LanguageTool está disponible.

        Args:
            force_check: Si True, ignora el cache y verifica de nuevo

        Returns:
            True si el servidor responde, False en caso contrario
        """
        if self._available is not None and not force_check:
            return self._available

        try:
            import urllib.request
            import urllib.error

            # Intentar conectar al endpoint de información
            url = f"{self.url}/languages"
            req = urllib.request.Request(url, method="GET")

            with urllib.request.urlopen(req, timeout=5) as response:
                self._available = response.status == 200

        except Exception as e:
            logger.debug(f"LanguageTool not available: {e}")
            self._available = False

        return self._available

    def refresh_availability(self) -> bool:
        """
        Refrescar el estado de disponibilidad (forzar nueva verificación).

        Returns:
            True si el servidor está disponible
        """
        self._available = None
        return self.is_available(force_check=True)

    def check(
        self,
        text: str,
        language: Optional[str] = None,
        disabled_rules: Optional[list[str]] = None,
        enabled_rules: Optional[list[str]] = None,
        enabled_only: bool = False,
    ) -> Result[LTCheckResult]:
        """
        Verificar texto con LanguageTool.

        Args:
            text: Texto a verificar
            language: Idioma (usa default si no se especifica)
            disabled_rules: Lista de IDs de reglas a desactivar
            enabled_rules: Lista de IDs de reglas a activar
            enabled_only: Si True, solo usa las reglas habilitadas explícitamente

        Returns:
            Result con LTCheckResult
        """
        if not text or not text.strip():
            return Result.success(LTCheckResult())

        if not self.is_available():
            return Result.failure(
                LTClientError(original_error="LanguageTool server not available")
            )

        try:
            import urllib.request
            import urllib.parse
            import urllib.error

            # Construir datos del request
            data = {
                "text": text,
                "language": language or self.language,
            }

            if disabled_rules:
                data["disabledRules"] = ",".join(disabled_rules)

            if enabled_rules:
                data["enabledRules"] = ",".join(enabled_rules)

            if enabled_only:
                data["enabledOnly"] = "true"

            # Codificar datos
            encoded_data = urllib.parse.urlencode(data).encode("utf-8")

            # Hacer request
            url = f"{self.url}/check"
            req = urllib.request.Request(
                url,
                data=encoded_data,
                method="POST",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                response_data = response.read().decode("utf-8")
                result_json = json.loads(response_data)

            # Parsear resultado
            matches = []
            for match_data in result_json.get("matches", []):
                match = LTMatch(
                    message=match_data.get("message", ""),
                    short_message=match_data.get("shortMessage", ""),
                    offset=match_data.get("offset", 0),
                    length=match_data.get("length", 0),
                    replacements=[
                        r.get("value", "")
                        for r in match_data.get("replacements", [])[:5]  # Limitar
                    ],
                    rule_id=match_data.get("rule", {}).get("id", ""),
                    rule_description=match_data.get("rule", {}).get("description", ""),
                    rule_category=match_data.get("rule", {}).get("category", {}).get("name", ""),
                    context_text=match_data.get("context", {}).get("text", ""),
                    context_offset=match_data.get("context", {}).get("offset", 0),
                )
                matches.append(match)

            # Info del idioma
            language_info = result_json.get("language", {})

            result = LTCheckResult(
                matches=matches,
                language_code=language_info.get("code", ""),
                language_name=language_info.get("name", ""),
                detected_language=language_info.get("detectedLanguage", {}).get("code", ""),
            )

            return Result.success(result)

        except urllib.error.URLError as e:
            self._available = False
            return Result.failure(
                LTClientError(original_error=f"Connection error: {e}")
            )
        except json.JSONDecodeError as e:
            return Result.failure(
                LTClientError(original_error=f"Invalid JSON response: {e}")
            )
        except Exception as e:
            logger.error(f"LanguageTool check error: {e}")
            return Result.failure(
                LTClientError(original_error=str(e))
            )

    def check_chunked(
        self,
        text: str,
        chunk_size: int = 10000,
        **kwargs,
    ) -> Result[LTCheckResult]:
        """
        Verificar texto largo dividiéndolo en chunks.

        LanguageTool tiene límite de caracteres por request.
        Esta función divide el texto y ajusta los offsets.

        Args:
            text: Texto a verificar
            chunk_size: Tamaño máximo de cada chunk
            **kwargs: Argumentos adicionales para check()

        Returns:
            Result con LTCheckResult consolidado
        """
        if len(text) <= chunk_size:
            return self.check(text, **kwargs)

        all_matches = []
        current_offset = 0

        # Dividir por párrafos para no cortar oraciones
        paragraphs = text.split("\n\n")
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 > chunk_size:
                # Procesar chunk actual
                if current_chunk:
                    result = self.check(current_chunk, **kwargs)
                    if result.is_success:
                        for match in result.value.matches:
                            # Ajustar offset
                            match.offset += current_offset
                            all_matches.append(match)

                    current_offset += len(current_chunk)
                    current_chunk = ""

            current_chunk += para + "\n\n"

        # Procesar último chunk
        if current_chunk:
            result = self.check(current_chunk.rstrip(), **kwargs)
            if result.is_success:
                for match in result.value.matches:
                    match.offset += current_offset
                    all_matches.append(match)

        return Result.success(LTCheckResult(
            matches=all_matches,
            language_code=self.language,
        ))

    def get_available_rules(self) -> Result[list[dict]]:
        """
        Obtener lista de reglas disponibles.

        Returns:
            Result con lista de diccionarios de reglas
        """
        if not self.is_available():
            return Result.failure(
                LTClientError(original_error="LanguageTool server not available")
            )

        try:
            import urllib.request
            import urllib.parse

            data = urllib.parse.urlencode({"language": self.language}).encode("utf-8")
            url = f"{self.url}/rules"

            req = urllib.request.Request(
                url,
                data=data,
                method="POST",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                response_data = response.read().decode("utf-8")
                rules = json.loads(response_data)

            return Result.success(rules)

        except Exception as e:
            return Result.failure(
                LTClientError(original_error=str(e))
            )


# Singleton thread-safe
_lt_client: Optional[LanguageToolClient] = None
_lt_lock = threading.Lock()


def get_languagetool_client(
    url: str = DEFAULT_LT_URL,
    language: str = DEFAULT_LANGUAGE,
) -> LanguageToolClient:
    """
    Obtener cliente LanguageTool singleton.

    Args:
        url: URL del servidor
        language: Idioma por defecto

    Returns:
        Instancia de LanguageToolClient
    """
    global _lt_client

    if _lt_client is None:
        with _lt_lock:
            if _lt_client is None:
                _lt_client = LanguageToolClient(url=url, language=language)

    return _lt_client


def is_languagetool_available() -> bool:
    """
    Verificar si LanguageTool está disponible.

    Returns:
        True si el servidor está activo
    """
    return get_languagetool_client().is_available()


def reset_languagetool_client():
    """Resetear singleton (para testing)."""
    global _lt_client
    with _lt_lock:
        _lt_client = None
