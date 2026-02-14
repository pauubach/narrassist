"""
Extracción temporal por LLM (Nivel B).

Usa el LLM local (Ollama) para extraer instancias temporales de personajes
que escapan a la detección regex del Nivel A.

Características:
- Procesamiento por capítulo (no cross-chapter)
- Validación de evidencia textual
- Umbral de confianza configurable
- Graceful degradation si el LLM no está disponible
- Merge con resultados del Nivel A (regex tiene prioridad)
"""

import json
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Tipos de instancia válidos que aceptamos del LLM
_VALID_TYPES = frozenset({"age", "phase", "year", "offset"})
_VALID_PHASES = frozenset({"child", "teen", "young", "adult", "elder"})


@dataclass
class LLMTemporalInstance:
    """Instancia temporal detectada por el LLM."""

    entity_name: str
    instance_type: str  # age, phase, year, offset
    value: int | str
    evidence: str
    confidence: float
    entity_id: int | None = None  # Se resuelve después del match con entidades


def extract_temporal_instances_llm(
    chapter_text: str,
    entity_names: list[str],
    min_confidence: float = 0.6,
    max_text_length: int = 3000,
) -> list[LLMTemporalInstance]:
    """
    Extrae instancias temporales de un capítulo usando el LLM.

    Args:
        chapter_text: Texto del capítulo
        entity_names: Nombres de personajes conocidos
        min_confidence: Confianza mínima para aceptar detección
        max_text_length: Máximo de caracteres a enviar al LLM

    Returns:
        Lista de instancias temporales detectadas, o [] si LLM no disponible
    """
    try:
        from narrative_assistant.llm.client import get_llm_client, is_llm_available

        if not is_llm_available():
            return []

        client = get_llm_client()
        if not client:
            return []
    except ImportError:
        logger.debug("Módulo LLM no disponible para extracción temporal")
        return []

    if not entity_names or not chapter_text.strip():
        return []

    from narrative_assistant.llm.prompts import (
        RECOMMENDED_TEMPERATURES,
        TEMPORAL_EXTRACTION_EXAMPLES,
        TEMPORAL_EXTRACTION_SYSTEM,
        TEMPORAL_EXTRACTION_TEMPLATE,
        build_prompt,
    )

    # Truncar texto si es muy largo para el LLM
    text_for_llm = chapter_text[:max_text_length]
    if len(chapter_text) > max_text_length:
        text_for_llm += "\n[...texto truncado...]"

    prompt = build_prompt(
        TEMPORAL_EXTRACTION_TEMPLATE,
        examples=TEMPORAL_EXTRACTION_EXAMPLES,
        entity_names=", ".join(entity_names),
        chapter_text=text_for_llm,
    )

    try:
        response = client.complete(
            prompt,
            system=TEMPORAL_EXTRACTION_SYSTEM,
            temperature=RECOMMENDED_TEMPERATURES.get("temporal_extraction", 0.2),
            max_tokens=500,
        )

        if not response:
            return []

        instances = _parse_llm_response(
            response, entity_names, chapter_text, min_confidence,
        )
        return instances

    except Exception as e:
        logger.debug(f"Error en extracción temporal LLM: {e}")
        return []


def _parse_llm_response(
    response: str,
    entity_names: list[str],
    chapter_text: str,
    min_confidence: float,
) -> list[LLMTemporalInstance]:
    """Parsea y valida la respuesta JSON del LLM."""
    # Intentar extraer JSON del response (a veces viene con texto extra)
    json_match = re.search(r"\[.*\]", response, re.DOTALL)
    if not json_match:
        logger.debug("Respuesta LLM sin JSON válido: %s", response[:200])
        return []

    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError:
        logger.debug("JSON inválido en respuesta LLM")
        return []

    if not isinstance(data, list):
        return []

    # Normalizar nombres conocidos para matching flexible
    name_lower_set = {n.lower() for n in entity_names}

    instances: list[LLMTemporalInstance] = []
    for item in data:
        if not isinstance(item, dict):
            continue

        instance = _validate_item(item, name_lower_set, chapter_text, min_confidence)
        if instance:
            instances.append(instance)

    return instances


def _validate_item(
    item: dict,
    known_names_lower: set[str],
    chapter_text: str,
    min_confidence: float,
) -> LLMTemporalInstance | None:
    """Valida un item individual de la respuesta LLM."""
    entity = item.get("entity", "")
    inst_type = item.get("type", "")
    value = item.get("value")
    evidence = item.get("evidence", "")
    confidence = item.get("confidence", 0.0)

    # Validar tipo
    if inst_type not in _VALID_TYPES:
        return None

    # Validar confianza
    try:
        confidence = float(confidence)
    except (ValueError, TypeError):
        return None
    if confidence < min_confidence:
        return None

    # Validar entidad conocida
    if entity.lower() not in known_names_lower:
        logger.debug("LLM temporal: entidad '%s' no conocida, descartada", entity)
        return None

    # Validar valor según tipo
    if inst_type == "age":
        try:
            value = int(value)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            return None
        if value < 0 or value > 130:
            return None
    elif inst_type == "phase":
        if isinstance(value, str):
            value = value.lower()
        if value not in _VALID_PHASES:
            return None
    elif inst_type == "year":
        try:
            value = int(value)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            return None
        if value < 0 or value > 2100:
            return None
    elif inst_type == "offset":
        try:
            value = int(value)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            return None
        if abs(value) > 200:
            return None

    # Validar evidencia: la cita debe existir en el texto original
    if evidence and len(evidence) > 3:
        if evidence.lower() not in chapter_text.lower():
            logger.debug(
                "LLM temporal: evidencia no encontrada en texto: %r", evidence[:80],
            )
            # Reducir confianza pero no descartar completamente
            confidence *= 0.6
            if confidence < min_confidence:
                return None

    return LLMTemporalInstance(
        entity_name=entity,
        instance_type=inst_type,
        value=value,  # type: ignore[arg-type]
        evidence=evidence,
        confidence=confidence,
    )


def resolve_entity_ids(
    instances: list[LLMTemporalInstance],
    entity_name_to_id: dict[str, int],
) -> list[LLMTemporalInstance]:
    """Resuelve entity_id a partir del nombre para cada instancia."""
    for inst in instances:
        name_lower = inst.entity_name.lower()
        inst.entity_id = entity_name_to_id.get(name_lower)
    return [inst for inst in instances if inst.entity_id is not None]


def build_instance_id(instance: LLMTemporalInstance) -> str | None:
    """Construye temporal_instance_id en el formato estándar."""
    if instance.entity_id is None:
        return None
    eid = instance.entity_id
    if instance.instance_type == "age":
        return f"{eid}@age:{instance.value}"
    if instance.instance_type == "phase":
        return f"{eid}@phase:{instance.value}"
    if instance.instance_type == "year":
        return f"{eid}@year:{instance.value}"
    if instance.instance_type == "offset":
        sign = "+" if int(instance.value) >= 0 else ""
        return f"{eid}@offset_years:{sign}{instance.value}"
    return None


def merge_with_regex_instances(
    regex_instance_ids: set[str],
    llm_instances: list[LLMTemporalInstance],
) -> list[LLMTemporalInstance]:
    """
    Merge: regex tiene prioridad. Solo retorna LLM instances que son nuevas.

    Args:
        regex_instance_ids: Set de temporal_instance_id ya detectados por regex
        llm_instances: Instancias detectadas por LLM

    Returns:
        Solo las instancias LLM que NO duplican detecciones regex
    """
    new_instances: list[LLMTemporalInstance] = []
    for inst in llm_instances:
        iid = build_instance_id(inst)
        if iid and iid not in regex_instance_ids:
            new_instances.append(inst)
        elif iid:
            logger.debug("LLM temporal: %s ya detectado por regex, descartado", iid)
    return new_instances
