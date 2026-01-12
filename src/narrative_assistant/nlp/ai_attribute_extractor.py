# -*- coding: utf-8 -*-
"""
Extractor de Atributos basado en IA.

En lugar de usar patrones regex, este módulo usa:
1. Análisis de dependencias de spaCy
2. Embeddings semánticos para clasificación
3. (Futuro) LLM local para extracción estructurada

Este enfoque es más robusto y generalizable que los patrones regex.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum

from ..core.result import Result
from ..core.errors import NarrativeError, ErrorSeverity

logger = logging.getLogger(__name__)


class AttributeType(Enum):
    """Tipos de atributos que podemos extraer."""
    # Físicos
    EYE_COLOR = "eye_color"
    HAIR_COLOR = "hair_color"
    HAIR_TYPE = "hair_type"  # largo, corto, rizado
    HEIGHT = "height"  # alto, bajo
    BUILD = "build"  # delgado, fornido
    AGE = "age"
    SKIN = "skin"

    # Ubicación
    LOCATION = "location"

    # Otros
    PROFESSION = "profession"
    PERSONALITY = "personality"
    OTHER = "other"


@dataclass
class ExtractedAttribute:
    """Un atributo extraído usando IA."""
    entity_name: str
    attribute_type: AttributeType
    value: str
    confidence: float
    source_text: str
    chapter: Optional[int] = None
    extraction_method: str = "dependency_parsing"


@dataclass
class ExtractionResult:
    """Resultado de la extracción de atributos."""
    attributes: list[ExtractedAttribute] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# Vocabularios para clasificación semántica
PHYSICAL_DESCRIPTORS = {
    "eye_color": ["azul", "azules", "verde", "verdes", "marrón", "marrones",
                  "negro", "negros", "gris", "grises", "avellana", "miel"],
    "hair_color": ["negro", "rubio", "castaño", "pelirrojo", "canoso", "blanco",
                   "moreno", "gris", "rojizo", "dorado", "oscuro", "claro"],
    "hair_type": ["largo", "corto", "liso", "rizado", "ondulado", "recogido",
                  "suelto", "trenzado", "rapado", "calvo"],
    "height": ["alto", "alta", "bajo", "baja", "muy alto", "muy alta",
               "bajito", "bajita", "gigante", "enano"],
    "build": ["delgado", "delgada", "gordo", "gorda", "fornido", "fornida",
              "esbelto", "esbelta", "robusto", "robusta", "musculoso",
              "atlético", "atlética", "corpulento", "flaco", "flaca"],
    "age": ["joven", "viejo", "vieja", "anciano", "anciana", "niño", "niña",
            "adolescente", "adulto", "adulta", "mayor"],
}

# Verbos que introducen descripciones
DESCRIPTION_VERBS = {"ser", "estar", "tener", "llevar", "parecer", "lucir"}


class AIAttributeExtractor:
    """
    Extractor de atributos usando análisis de dependencias de spaCy.

    En lugar de patrones regex, analiza la estructura gramatical:
    - Sujeto + verbo copulativo + atributo
    - Sujeto + tener + sustantivo + adjetivo
    - Adjetivos que modifican sustantivos de partes del cuerpo

    Ejemplo:
        >>> extractor = AIAttributeExtractor()
        >>> result = extractor.extract("María tenía los ojos azules.", ["María"])
        >>> for attr in result.attributes:
        ...     print(f"{attr.entity_name}: {attr.attribute_type.value} = {attr.value}")
    """

    def __init__(self, use_llm: bool = False, llm_model: Optional[str] = None):
        """
        Inicializa el extractor.

        Args:
            use_llm: Si True, usa LLM local para extracción (no implementado)
            llm_model: Ruta al modelo LLM local
        """
        self._nlp = None
        self.use_llm = use_llm
        self.llm_model = llm_model

    @property
    def nlp(self):
        """Lazy loading del modelo spaCy."""
        if self._nlp is None:
            from ..nlp.spacy_gpu import load_spacy_model
            self._nlp = load_spacy_model()
        return self._nlp

    def extract(
        self,
        text: str,
        entity_names: list[str],
        chapter: Optional[int] = None,
    ) -> Result[ExtractionResult]:
        """
        Extrae atributos del texto usando análisis de dependencias.

        Args:
            text: Texto a analizar
            entity_names: Nombres de entidades conocidas
            chapter: Número de capítulo (opcional)

        Returns:
            Result con ExtractionResult
        """
        try:
            result = ExtractionResult()

            # Procesar texto con spaCy
            doc = self.nlp(text)

            # Normalizar nombres de entidades para búsqueda
            entity_names_lower = {name.lower() for name in entity_names}

            # Extraer atributos usando diferentes estrategias

            # 1. Estructura: ENTIDAD + verbo copulativo + ATRIBUTO
            result.attributes.extend(
                self._extract_copulative(doc, entity_names_lower, chapter)
            )

            # 2. Estructura: ENTIDAD + tener + PARTE_CUERPO + ADJETIVO
            result.attributes.extend(
                self._extract_possession(doc, entity_names_lower, chapter)
            )

            # 3. Estructura: ADJETIVO + de + ENTIDAD
            result.attributes.extend(
                self._extract_adjective_of(doc, entity_names_lower, chapter)
            )

            # 4. Pronombres posesivos: "sus ojos azules"
            result.attributes.extend(
                self._extract_possessive(doc, entity_names_lower, chapter)
            )

            # Deduplicar y filtrar
            result.attributes = self._deduplicate(result.attributes)

            logger.info(f"Extracted {len(result.attributes)} attributes using AI")
            return Result.success(result)

        except Exception as e:
            error = NarrativeError(
                message=f"AI attribute extraction failed: {str(e)}",
                severity=ErrorSeverity.RECOVERABLE,
            )
            logger.exception("Error in AI attribute extraction")
            return Result.failure(error)

    def _extract_copulative(
        self,
        doc: Any,
        entity_names: set[str],
        chapter: Optional[int],
    ) -> list[ExtractedAttribute]:
        """
        Extrae atributos de estructuras copulativas.

        Patrones:
        - "María era alta" -> María.height = alta
        - "Juan era un hombre bajo" -> Juan.height = bajo
        """
        attributes = []

        for token in doc:
            # Buscar verbos copulativos (ser, estar, parecer)
            if token.lemma_ in {"ser", "estar", "parecer"} and token.pos_ == "AUX":
                # Buscar sujeto
                subject = None
                for child in token.head.children:
                    if child.dep_ == "nsubj":
                        subject = child
                        break

                if not subject:
                    # Buscar en el propio token
                    for child in token.children:
                        if child.dep_ == "nsubj":
                            subject = child
                            break

                if not subject or subject.text.lower() not in entity_names:
                    # Intentar con pronombres que podrían referirse a entidades
                    if subject and subject.pos_ == "PRON":
                        # Por ahora, asignar al último nombre mencionado
                        # TODO: Mejor resolución de correferencia
                        pass
                    continue

                # Buscar atributo (adjetivo predicativo)
                for child in token.head.children:
                    if child.dep_ in ("acomp", "attr", "ROOT") and child.pos_ == "ADJ":
                        attr_type = self._classify_attribute(child.text)
                        if attr_type:
                            attributes.append(ExtractedAttribute(
                                entity_name=subject.text,
                                attribute_type=attr_type,
                                value=child.text.lower(),
                                confidence=0.85,
                                source_text=token.sent.text,
                                chapter=chapter,
                                extraction_method="dependency_copulative",
                            ))

        return attributes

    def _extract_possession(
        self,
        doc: Any,
        entity_names: set[str],
        chapter: Optional[int],
    ) -> list[ExtractedAttribute]:
        """
        Extrae atributos de estructuras posesivas.

        Patrones:
        - "María tenía los ojos azules" -> María.eye_color = azules
        - "Juan tenía el cabello negro" -> Juan.hair_color = negro
        """
        attributes = []

        body_parts = {
            "ojos": "eye_color",
            "ojo": "eye_color",
            "cabello": "hair_color",
            "pelo": "hair_color",
            "piel": "skin",
            "barba": "hair_color",  # Para barba usamos hair_color con contexto
        }

        for token in doc:
            # Buscar "tener" o "llevar"
            if token.lemma_ in {"tener", "llevar"} and token.pos_ == "VERB":
                subject = None
                obj = None

                # Buscar sujeto
                for child in token.children:
                    if child.dep_ == "nsubj":
                        subject = child
                    elif child.dep_ in ("obj", "dobj"):
                        obj = child

                if not subject or subject.text.lower() not in entity_names:
                    continue

                if not obj:
                    continue

                # Verificar si el objeto es una parte del cuerpo
                obj_lemma = obj.lemma_.lower()
                if obj_lemma not in body_parts:
                    continue

                attr_type_str = body_parts[obj_lemma]

                # Buscar adjetivos que modifican el objeto
                for child in obj.children:
                    if child.pos_ == "ADJ":
                        try:
                            attr_type = AttributeType(attr_type_str)
                        except ValueError:
                            attr_type = AttributeType.OTHER

                        attributes.append(ExtractedAttribute(
                            entity_name=subject.text,
                            attribute_type=attr_type,
                            value=child.text.lower(),
                            confidence=0.9,
                            source_text=token.sent.text,
                            chapter=chapter,
                            extraction_method="dependency_possession",
                        ))

        return attributes

    def _extract_adjective_of(
        self,
        doc: Any,
        entity_names: set[str],
        chapter: Optional[int],
    ) -> list[ExtractedAttribute]:
        """
        Extrae atributos de estructuras "X de ENTIDAD".

        Patrones:
        - "los ojos verdes de María" -> María.eye_color = verdes
        - "el pelo rubio de Juan" -> Juan.hair_color = rubio
        """
        attributes = []

        body_parts_to_attr = {
            "ojos": AttributeType.EYE_COLOR,
            "ojo": AttributeType.EYE_COLOR,
            "cabello": AttributeType.HAIR_COLOR,
            "pelo": AttributeType.HAIR_COLOR,
        }

        for token in doc:
            # Buscar "de" seguido de nombre
            if token.text.lower() == "de" and token.dep_ == "case":
                # El head de "de" debería ser el nombre
                entity_token = token.head
                if entity_token.text.lower() not in entity_names:
                    continue

                # Buscar la estructura completa: "los OJOS VERDES de ENTIDAD"
                # El abuelo de "de" sería "ojos" en este caso
                parent = entity_token.head
                if parent.lemma_.lower() in body_parts_to_attr:
                    # Buscar adjetivo que modifica la parte del cuerpo
                    for child in parent.children:
                        if child.pos_ == "ADJ":
                            attr_type = body_parts_to_attr[parent.lemma_.lower()]
                            attributes.append(ExtractedAttribute(
                                entity_name=entity_token.text,
                                attribute_type=attr_type,
                                value=child.text.lower(),
                                confidence=0.85,
                                source_text=token.sent.text,
                                chapter=chapter,
                                extraction_method="dependency_of",
                            ))

        return attributes

    def _extract_possessive(
        self,
        doc: Any,
        entity_names: set[str],
        chapter: Optional[int],
    ) -> list[ExtractedAttribute]:
        """
        Extrae atributos de pronombres posesivos.

        Patrones:
        - "Sus ojos azules brillaban" -> (última entidad).eye_color = azules
        """
        attributes = []

        body_parts_to_attr = {
            "ojos": AttributeType.EYE_COLOR,
            "ojo": AttributeType.EYE_COLOR,
            "cabello": AttributeType.HAIR_COLOR,
            "pelo": AttributeType.HAIR_COLOR,
        }

        # Track última entidad mencionada para resolver "sus"
        last_entity = None

        for token in doc:
            # Actualizar última entidad
            if token.text.lower() in entity_names:
                last_entity = token.text

            # Buscar posesivos (su, sus)
            if token.text.lower() in {"su", "sus"} and token.pos_ == "DET":
                # El head debería ser el sustantivo (ojos, pelo, etc.)
                noun = token.head

                if noun.lemma_.lower() not in body_parts_to_attr:
                    continue

                if not last_entity:
                    continue

                # Buscar adjetivo que modifica el sustantivo
                for child in noun.children:
                    if child.pos_ == "ADJ":
                        attr_type = body_parts_to_attr[noun.lemma_.lower()]
                        attributes.append(ExtractedAttribute(
                            entity_name=last_entity,
                            attribute_type=attr_type,
                            value=child.text.lower(),
                            confidence=0.7,  # Menor confianza por ambigüedad
                            source_text=token.sent.text,
                            chapter=chapter,
                            extraction_method="dependency_possessive",
                        ))

        return attributes

    def _classify_attribute(self, value: str) -> Optional[AttributeType]:
        """
        Clasifica un valor de atributo en su tipo correspondiente.

        Usa los vocabularios definidos para hacer matching.
        """
        value_lower = value.lower()

        for attr_type, values in PHYSICAL_DESCRIPTORS.items():
            if value_lower in values:
                try:
                    return AttributeType(attr_type)
                except ValueError:
                    continue

        return None

    def _deduplicate(
        self,
        attributes: list[ExtractedAttribute],
    ) -> list[ExtractedAttribute]:
        """
        Elimina atributos duplicados, manteniendo el de mayor confianza.
        """
        seen = {}  # (entity, type, value) -> attribute

        for attr in attributes:
            key = (attr.entity_name.lower(), attr.attribute_type, attr.value)
            if key not in seen or attr.confidence > seen[key].confidence:
                seen[key] = attr

        return list(seen.values())


# =============================================================================
# Singleton
# =============================================================================

_ai_extractor: Optional[AIAttributeExtractor] = None


def get_ai_attribute_extractor(
    use_llm: bool = False,
) -> AIAttributeExtractor:
    """Obtiene singleton del extractor de atributos IA."""
    global _ai_extractor

    if _ai_extractor is None:
        _ai_extractor = AIAttributeExtractor(use_llm=use_llm)

    return _ai_extractor


def reset_ai_extractor() -> None:
    """Resetea el singleton (útil para tests)."""
    global _ai_extractor
    _ai_extractor = None
