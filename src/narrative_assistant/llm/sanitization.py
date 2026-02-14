"""
Sanitización de entradas y salidas para el LLM.

Protege contra:
- Inyección de prompts (prompt injection)
- Respuestas malformadas del LLM
- Contenido inesperado en nombres de entidades
- Desbordamiento de contexto

Principios:
1. Las entradas del manuscrito son datos, NO instrucciones
2. Los nombres de personajes se escapan antes de insertar en prompts
3. Las respuestas del LLM se validan contra esquemas esperados
4. El contexto se trunca de forma semántica (por oraciones, no por chars)
"""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Patrones de inyección comunes en prompts
INJECTION_PATTERNS = [
    # Instrucciones directas
    r"(?i)ignore\s+(all\s+)?previous\s+instructions?",
    r"(?i)forget\s+(all\s+)?previous",
    r"(?i)disregard\s+(all\s+)?above",
    r"(?i)new\s+instructions?\s*:",
    r"(?i)system\s*:\s*you\s+are",
    r"(?i)override\s+system\s+prompt",
    # Delimitadores de sistema
    r"<\|system\|>",
    r"<\|assistant\|>",
    r"\[INST\]",
    r"\[/INST\]",
    r"<<SYS>>",
    r"<</SYS>>",
    # Jailbreak patterns
    r"(?i)do\s+anything\s+now",
    r"(?i)pretend\s+you\s+are",
    r"(?i)act\s+as\s+if",
    r"(?i)you\s+are\s+now\s+(?:a|an|the)\s+",
    # Patrones adicionales de inyección (A-10)
    r"(?i)respond\s+only\s+with",
    r"(?i)output\s+the\s+(?:system|initial)\s+prompt",
    r"(?i)repeat\s+(?:your|the)\s+(?:system|initial)\s+(?:prompt|instructions?)",
    r"(?i)translate\s+(?:the|your)\s+(?:system|above)\s+(?:prompt|message)",
    r"(?i)(?:olvida|ignora)\s+(?:todas?\s+)?(?:las\s+)?instrucciones?\s+anteriores?",
    r"(?i)nuevas?\s+instrucciones?\s*:",
    r"(?i)ahora\s+eres\s+(?:un|una)\s+",
    r"(?i)actúa\s+como\s+si",
]

# Caracteres de control que no deberían estar en texto narrativo
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Longitudes máximas por tipo de campo
MAX_LENGTHS = {
    "character_name": 100,
    "trait": 200,
    "context": 2000,
    "text_fragment": 5000,
}


def sanitize_for_prompt(text: str, max_length: int = 5000) -> str:
    """
    Sanitiza texto del manuscrito antes de insertarlo en un prompt.

    Escapa/elimina contenido que podría ser interpretado como
    instrucción por el LLM.

    Args:
        text: Texto del manuscrito
        max_length: Longitud máxima permitida

    Returns:
        Texto sanitizado seguro para insertar en prompt.
    """
    if not text:
        return ""

    # 1. Eliminar caracteres de control
    cleaned = CONTROL_CHARS.sub("", text)

    # 2. Detectar y neutralizar patrones de inyección
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, cleaned):
            logger.warning(
                f"Patrón de inyección detectado en texto: {pattern}"
            )
            # Neutralizar envolviendo en comillas y prefijando
            cleaned = re.sub(pattern, "[FILTERED]", cleaned)

    # 3. Truncar por longitud manteniendo oraciones completas
    if len(cleaned) > max_length:
        cleaned = truncate_by_sentence(cleaned, max_length)

    return cleaned


def sanitize_entity_name(name: str) -> str:
    """
    Sanitiza un nombre de entidad antes de usarlo en un prompt.

    Los nombres de personajes van directamente al prompt y podrían
    contener inyecciones si el manuscrito incluye nombres maliciosos.

    Args:
        name: Nombre de la entidad

    Returns:
        Nombre sanitizado.
    """
    if not name:
        return ""

    # Eliminar caracteres de control
    cleaned = CONTROL_CHARS.sub("", name)

    # Limitar longitud
    cleaned = cleaned[:MAX_LENGTHS["character_name"]]

    # Solo permitir letras, números, espacios, puntuación básica
    cleaned = re.sub(r"[^\w\s\-'.áéíóúñüÁÉÍÓÚÑÜ]", "", cleaned)

    # Detectar inyección en nombre
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, cleaned):
            logger.warning(f"Posible inyección en nombre de entidad: {name[:50]}")
            return cleaned[:20]  # Truncar agresivamente

    return cleaned.strip()


def validate_llm_response(
    response_text: str,
    expected_keys: list[str] | None = None,
) -> dict | None:
    """
    Valida y parsea la respuesta del LLM.

    Args:
        response_text: Texto de respuesta del LLM
        expected_keys: Lista de claves esperadas en el JSON

    Returns:
        Diccionario parseado o None si no es válido.
    """
    if not response_text:
        return None

    # Intentar extraer JSON de la respuesta
    json_text = extract_json_from_response(response_text)
    if not json_text:
        return None

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        logger.warning("Respuesta del LLM no es JSON válido")
        return None

    if not isinstance(data, dict):
        logger.warning("Respuesta del LLM no es un objeto JSON")
        return None

    # Validar claves esperadas
    if expected_keys:
        missing = [k for k in expected_keys if k not in data]
        if missing:
            logger.warning(f"Claves faltantes en respuesta LLM: {missing}")
            # No rechazar completamente, solo advertir

    # Sanitizar valores de texto en la respuesta
    sanitized = _sanitize_response_values(data)

    return sanitized  # type: ignore[no-any-return]


def extract_json_from_response(text: str) -> str | None:
    """
    Extrae el primer bloque JSON de una respuesta del LLM.

    Maneja casos como:
    - JSON puro
    - JSON dentro de ```json ... ```
    - Texto antes/después del JSON
    """
    if not text:
        return None

    text = text.strip()

    # Caso 1: respuesta es JSON puro
    if text.startswith("{") or text.startswith("["):
        return text

    # Caso 2: JSON en bloque de código
    json_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if json_block:
        return json_block.group(1).strip()

    # Caso 3: buscar primer { ... } o [ ... ]
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        return brace_match.group()

    bracket_match = re.search(r"\[.*\]", text, re.DOTALL)
    if bracket_match:
        return bracket_match.group()

    return None


def truncate_by_sentence(text: str, max_length: int) -> str:
    """
    Trunca texto por oraciones completas.

    Corta en el último punto/signo de puntuación antes del límite.
    """
    if len(text) <= max_length:
        return text

    # Buscar último fin de oración antes del límite
    truncated = text[:max_length]

    for sep in [". ", "? ", "! ", "\n"]:
        last_sep = truncated.rfind(sep)
        if last_sep > max_length * 0.5:
            return truncated[: last_sep + 1]

    # Fallback: cortar en último espacio
    last_space = truncated.rfind(" ")
    if last_space > max_length * 0.5:
        return truncated[:last_space] + "..."

    return truncated + "..."


def _sanitize_response_values(data: Any, depth: int = 0) -> Any:
    """Sanitiza valores de texto en la respuesta del LLM recursivamente."""
    if depth > 10:
        return data

    if isinstance(data, dict):
        return {k: _sanitize_response_values(v, depth + 1) for k, v in data.items()}
    if isinstance(data, list):
        return [_sanitize_response_values(item, depth + 1) for item in data]
    if isinstance(data, str):
        # Eliminar caracteres de control
        return CONTROL_CHARS.sub("", data)

    return data
