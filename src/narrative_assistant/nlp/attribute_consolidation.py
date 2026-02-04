"""
Consolidación de Atributos - Agrupación de evidencias múltiples.

Este módulo agrupa atributos duplicados (misma entidad + clave + valor)
y gestiona las evidencias que los soportan.

Por ejemplo, si "María es decidida" se detecta en 5 ubicaciones diferentes,
en lugar de crear 5 atributos duplicados, se crea 1 atributo con 5 evidencias.
"""

import json
import logging
from collections import defaultdict
from dataclasses import dataclass

from ..parsers.base import RawDocument, calculate_page_and_line
from .attributes import AttributeKey, ExtractedAttribute

logger = logging.getLogger(__name__)


@dataclass
class AttributeEvidence:
    """
    Evidencia individual de un atributo.

    Representa una ubicación específica donde se detectó el atributo.
    """

    attribute_id: int | None  # ID del atributo padre (se asigna al guardar)
    start_char: int
    end_char: int
    chapter: int | None
    page: int
    line: int
    excerpt: str
    extraction_method: str
    keywords: list[str]
    confidence: float


def consolidate_attributes(
    attributes: list[ExtractedAttribute],
) -> dict[tuple[str, str, str], list[ExtractedAttribute]]:
    """
    Agrupa atributos duplicados (misma entidad + clave + valor).

    Args:
        attributes: Lista de atributos extraídos (pueden contener duplicados)

    Returns:
        Dict[(entity_name, key, value)] -> [list of evidences]

    Example:
        >>> attributes = [...]  # 5 atributos "María es decidida"
        >>> grouped = consolidate_attributes(attributes)
        >>> print(grouped)
        {
            ("maría", "personality", "decidida"): [attr1, attr2, attr3, attr4, attr5]
        }
    """
    grouped = defaultdict(list)

    for attr in attributes:
        # Normalizar clave: entidad + atributo + valor (case-insensitive)
        entity_name_norm = attr.entity_name.lower().strip()
        key_norm = attr.key.value if isinstance(attr.key, AttributeKey) else str(attr.key)
        value_norm = attr.value.lower().strip()

        unique_key = (entity_name_norm, key_norm, value_norm)
        grouped[unique_key].append(attr)

    logger.info(f"Consolidados {len(attributes)} atributos en {len(grouped)} atributos únicos")

    return grouped


def create_evidences_from_attributes(
    evidences_data: list[ExtractedAttribute],
    raw_document: RawDocument | None = None,
    words_per_page: int = 300,
) -> list[AttributeEvidence]:
    """
    Convierte lista de ExtractedAttribute en lista de AttributeEvidence.

    Args:
        evidences_data: Lista de atributos extraídos (evidencias del mismo atributo)
        raw_document: Documento original (para calcular page/line)
        words_per_page: Palabras por página (default: 300)

    Returns:
        Lista de AttributeEvidence con ubicaciones completas

    Example:
        >>> attrs = [attr1, attr2, attr3]  # 3 detecciones de "decidida"
        >>> evidences = create_evidences_from_attributes(attrs, document)
        >>> print(len(evidences))
        3
        >>> print(evidences[0].page, evidences[0].line)
        5 42
    """
    evidences = []

    for attr in evidences_data:
        # Calcular page/line si tenemos el documento
        if raw_document and attr.start_char >= 0:
            page, line = calculate_page_and_line(attr.start_char, raw_document, words_per_page)
        else:
            # Fallback si no tenemos documento
            page, line = 1, 1

        # Inferir método de extracción
        extraction_method = infer_extraction_method(attr)

        # Extraer keywords
        keywords = extract_keywords(attr)

        # Crear evidencia
        evidence = AttributeEvidence(
            attribute_id=None,  # Se asignará al guardar en BD
            start_char=attr.start_char,
            end_char=attr.end_char,
            chapter=attr.chapter_id,
            page=page,
            line=line,
            excerpt=attr.source_text[:200] if attr.source_text else "",  # Limitar a 200 chars
            extraction_method=extraction_method,
            keywords=keywords,
            confidence=attr.confidence,
        )

        evidences.append(evidence)

    logger.debug(f"Creadas {len(evidences)} evidencias desde {len(evidences_data)} atributos")

    return evidences


def infer_extraction_method(attr: ExtractedAttribute) -> str:
    """
    Determina método de extracción basado en patrones en source_text.

    Args:
        attr: Atributo extraído

    Returns:
        Uno de: "direct_description", "action_inference", "dialogue", "unknown"

    Notes:
        - direct_description: "María era decidida", "tenía ojos azules"
        - action_inference: "María tomó una decisión rápida"
        - dialogue: "—No esperaré más —dijo María"
        - unknown: No se pudo determinar

    Example:
        >>> attr = ExtractedAttribute(..., source_text="María era decidida")
        >>> method = infer_extraction_method(attr)
        >>> print(method)
        "direct_description"
    """
    if not attr.source_text:
        return "unknown"

    text_lower = attr.source_text.lower()

    # Descripción directa: verbos copulativos
    direct_indicators = ["era", "es", "fue", "siendo", "tenía", "tiene", "tuvo"]
    if any(verb in text_lower for verb in direct_indicators):
        return "direct_description"

    # Diálogo: marcadores de diálogo
    dialogue_indicators = ["—", "–", '"', """, """]
    if any(marker in attr.source_text for marker in dialogue_indicators):
        return "dialogue"

    # Acción: verbos de acción
    action_indicators = ["tomó", "decidió", "actuó", "hizo", "dijo", "pensó"]
    if any(verb in text_lower for verb in action_indicators):
        return "action_inference"

    # Por defecto
    return "unknown"


def extract_keywords(attr: ExtractedAttribute) -> list[str]:
    """
    Extrae keywords relevantes del contexto de extracción.

    Args:
        attr: Atributo extraído

    Returns:
        Lista de palabras clave que activaron la detección

    Example:
        >>> attr = ExtractedAttribute(..., value="decidida", source_text="María es muy decidida")
        >>> keywords = extract_keywords(attr)
        >>> print(keywords)
        ["decidida"]
    """
    if not attr.source_text or not attr.value:
        return []

    # Palabras del valor del atributo
    value_words = set(attr.value.lower().split())

    # Palabras del source_text
    source_words = set(attr.source_text.lower().split())

    # Keywords: palabras del valor que aparecen en el contexto
    keywords = value_words.intersection(source_words)

    # Filtrar stopwords comunes
    stopwords = {"el", "la", "los", "las", "de", "del", "un", "una", "y", "o", "a"}
    keywords = {kw for kw in keywords if kw not in stopwords}

    return sorted(keywords)


def get_max_confidence(evidences: list[ExtractedAttribute]) -> float:
    """
    Obtiene la confianza máxima de una lista de evidencias.

    Args:
        evidences: Lista de atributos extraídos

    Returns:
        Confianza máxima (entre 0.0 y 1.0)

    Example:
        >>> attrs = [attr1, attr2, attr3]  # confidences: 0.85, 0.92, 0.78
        >>> max_conf = get_max_confidence(attrs)
        >>> print(max_conf)
        0.92
    """
    if not evidences:
        return 0.0

    return max(attr.confidence for attr in evidences)


def evidence_to_dict(evidence: AttributeEvidence) -> dict:
    """
    Convierte AttributeEvidence a diccionario para guardar en BD.

    Args:
        evidence: Evidencia del atributo

    Returns:
        Diccionario con campos para INSERT en attribute_evidences

    Example:
        >>> evidence = AttributeEvidence(...)
        >>> data = evidence_to_dict(evidence)
        >>> print(data.keys())
        dict_keys(['attribute_id', 'start_char', 'end_char', ...])
    """
    return {
        "attribute_id": evidence.attribute_id,
        "start_char": evidence.start_char,
        "end_char": evidence.end_char,
        "chapter": evidence.chapter,
        "page": evidence.page,
        "line": evidence.line,
        "excerpt": evidence.excerpt,
        "extraction_method": evidence.extraction_method,
        "keywords": json.dumps(evidence.keywords, ensure_ascii=False),
        "confidence": evidence.confidence,
    }
