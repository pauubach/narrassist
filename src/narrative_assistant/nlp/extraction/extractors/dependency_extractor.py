# -*- coding: utf-8 -*-
"""
Extractor basado en análisis de dependencias de spaCy.

Este extractor analiza la estructura gramatical del texto
para extraer atributos sin depender de patrones literales.

Ventajas sobre regex:
- Más generalizable a diferentes estilos de escritura
- Entiende relaciones gramaticales
- Mejor manejo de oraciones complejas
"""

import logging
from typing import Optional, Any

from ..base import (
    BaseExtractor,
    ExtractionMethod,
    ExtractionContext,
    ExtractionResult,
    ExtractedAttribute,
    AttributeType,
)

logger = logging.getLogger(__name__)


# Vocabularios para clasificación semántica
PHYSICAL_DESCRIPTORS = {
    "eye_color": {
        "azul", "azules", "verde", "verdes", "marrón", "marrones",
        "negro", "negros", "gris", "grises", "avellana", "miel",
        "castaño", "castaños", "ámbar", "violeta", "violetas",
    },
    "hair_color": {
        "negro", "rubio", "castaño", "pelirrojo", "canoso", "blanco",
        "moreno", "gris", "rojizo", "dorado", "oscuro", "claro",
        "platino", "cobrizo", "azabache",
    },
    "hair_type": {
        "largo", "corto", "liso", "rizado", "ondulado", "recogido",
        "suelto", "trenzado", "rapado", "calvo", "espeso", "fino",
    },
    "height": {
        "alto", "alta", "bajo", "baja", "muy alto", "muy alta",
        "bajito", "bajita", "gigante", "enano", "enana",
    },
    "build": {
        "delgado", "delgada", "gordo", "gorda", "fornido", "fornida",
        "esbelto", "esbelta", "robusto", "robusta", "musculoso", "musculosa",
        "atlético", "atlética", "corpulento", "corpulenta", "flaco", "flaca",
    },
    "age": {
        "joven", "viejo", "vieja", "anciano", "anciana", "niño", "niña",
        "adolescente", "adulto", "adulta", "mayor",
    },
    "skin": {
        "pálido", "pálida", "moreno", "morena", "bronceado", "bronceada",
        "claro", "clara", "oscuro", "oscura", "pecoso", "pecosa",
        "escamosa", "escamoso",  # Para fantasy/sci-fi
    },
}

# Mapeo de parte del cuerpo a tipo de atributo
BODY_PARTS_TO_ATTR = {
    "ojos": AttributeType.EYE_COLOR,
    "ojo": AttributeType.EYE_COLOR,
    "cabello": AttributeType.HAIR_COLOR,
    "pelo": AttributeType.HAIR_COLOR,
    "melena": AttributeType.HAIR_COLOR,
    "piel": AttributeType.SKIN,
    "rostro": AttributeType.SKIN,
    "barba": AttributeType.HAIR_COLOR,
    "bigote": AttributeType.HAIR_COLOR,
}

# Partes del cuerpo que pueden tener tipo (largo/corto)
BODY_PARTS_WITH_TYPE = {
    "cabello": AttributeType.HAIR_TYPE,
    "pelo": AttributeType.HAIR_TYPE,
    "melena": AttributeType.HAIR_TYPE,
    "barba": AttributeType.HAIR_TYPE,
}

# Verbos que introducen descripciones
DESCRIPTION_VERBS = {"ser", "estar", "tener", "llevar", "parecer", "lucir"}


class DependencyExtractor(BaseExtractor):
    """
    Extractor de atributos usando análisis de dependencias de spaCy.

    Analiza la estructura gramatical para detectar:
    - Estructuras copulativas: "María era alta"
    - Estructuras posesivas: "María tenía ojos azules"
    - Modificadores: "los ojos verdes de María"
    - Posesivos pronominales: "sus ojos brillaban"

    Example:
        >>> extractor = DependencyExtractor()
        >>> context = ExtractionContext(
        ...     text="María era alta y tenía los ojos azules.",
        ...     entity_names=["María"]
        ... )
        >>> result = extractor.extract(context)
        >>> for attr in result.attributes:
        ...     print(f"{attr.entity_name}: {attr.attribute_type.value} = {attr.value}")
    """

    def __init__(self):
        """Inicializa el extractor."""
        self._nlp = None

    @property
    def nlp(self):
        """Lazy loading del modelo spaCy."""
        if self._nlp is None:
            from ...spacy_gpu import load_spacy_model
            self._nlp = load_spacy_model()
        return self._nlp

    @property
    def method(self) -> ExtractionMethod:
        return ExtractionMethod.DEPENDENCY

    @property
    def supported_attributes(self) -> set[AttributeType]:
        return {
            AttributeType.EYE_COLOR,
            AttributeType.HAIR_COLOR,
            AttributeType.HAIR_TYPE,
            AttributeType.HEIGHT,
            AttributeType.BUILD,
            AttributeType.AGE,
            AttributeType.SKIN,
            AttributeType.DISTINCTIVE_FEATURE,
        }

    def can_handle(self, context: ExtractionContext) -> float:
        """
        Dependency parsing funciona bien para la mayoría de textos.
        """
        word_count = len(context.text.split())

        # Bueno para textos de tamaño medio
        if 20 <= word_count <= 500:
            return 0.8

        # Menos eficiente para textos muy cortos o muy largos
        if word_count < 20:
            return 0.6
        if word_count > 500:
            return 0.7

        return 0.75

    def extract(self, context: ExtractionContext) -> ExtractionResult:
        """
        Extrae atributos usando análisis de dependencias.
        """
        attributes = []
        errors = []

        try:
            # Usar doc pre-procesado si existe, sino procesar
            if context.doc is not None:
                doc = context.doc
            else:
                doc = self.nlp(context.text)

            # Normalizar nombres de entidades
            entity_names_lower = {name.lower() for name in context.entity_names}

            # Estrategia 1: Estructuras copulativas (ser/estar + ADJ)
            attributes.extend(
                self._extract_copulative(doc, entity_names_lower, context.chapter)
            )

            # Estrategia 2: Estructuras posesivas (tener + NOUN + ADJ)
            attributes.extend(
                self._extract_possession(doc, entity_names_lower, context.chapter)
            )

            # Estrategia 3: "ADJ de ENTIDAD" (los ojos verdes de María)
            attributes.extend(
                self._extract_adjective_of(doc, entity_names_lower, context.chapter)
            )

            # Estrategia 4: Posesivos pronominales (sus ojos azules)
            attributes.extend(
                self._extract_possessive(doc, entity_names_lower, context.chapter)
            )

            # Estrategia 5: Enumeraciones de adjetivos
            attributes.extend(
                self._extract_enumerations(doc, entity_names_lower, context.chapter)
            )

            # Separar atributos compuestos
            attributes = self._separate_compound_attributes(attributes)

            # Deduplicar
            attributes = self._deduplicate(attributes)

            logger.debug(f"DependencyExtractor found {len(attributes)} attributes")

        except Exception as e:
            errors.append(f"Error in dependency extraction: {str(e)}")
            logger.exception("Error in dependency extraction")

        return self._create_result(attributes, errors)

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
        - "Ella parecía joven" -> (entidad previa).age = joven
        """
        attributes = []

        for token in doc:
            # Buscar verbos copulativos
            if token.lemma_ in {"ser", "estar", "parecer"} and token.pos_ in {"AUX", "VERB"}:
                # Buscar sujeto
                subject = self._find_subject(token)

                if not subject:
                    continue

                # Verificar si el sujeto es una entidad conocida
                subject_text = subject.text.lower()
                entity_name = None

                if subject_text in entity_names:
                    entity_name = subject.text
                elif subject.pos_ == "PRON":
                    # Resolver pronombre a última entidad
                    entity_name = self._resolve_pronoun(doc, token, entity_names)

                if not entity_name:
                    continue

                # Buscar atributo predicativo (adjetivo)
                for child in token.head.children if token.dep_ == "cop" else token.children:
                    if child.pos_ == "ADJ":
                        attr_type = self._classify_attribute(child.text)
                        if attr_type:
                            attributes.append(self._create_attribute(
                                entity_name=entity_name,
                                attr_type=attr_type,
                                value=child.text.lower(),
                                confidence=0.85,
                                source_text=token.sent.text,
                                chapter=chapter,
                            ))
                    # Buscar en "era un hombre alto"
                    elif child.pos_ == "NOUN":
                        for grandchild in child.children:
                            if grandchild.pos_ == "ADJ":
                                attr_type = self._classify_attribute(grandchild.text)
                                if attr_type:
                                    attributes.append(self._create_attribute(
                                        entity_name=entity_name,
                                        attr_type=attr_type,
                                        value=grandchild.text.lower(),
                                        confidence=0.80,
                                        source_text=token.sent.text,
                                        chapter=chapter,
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

        for token in doc:
            # Buscar "tener" o "llevar"
            if token.lemma_ in {"tener", "llevar"} and token.pos_ == "VERB":
                subject = None
                obj = None

                # Buscar sujeto y objeto
                for child in token.children:
                    if child.dep_ == "nsubj":
                        subject = child
                    elif child.dep_ in {"obj", "dobj"}:
                        obj = child

                if not subject:
                    continue

                # Verificar si es entidad conocida
                subject_text = subject.text.lower()
                entity_name = None

                if subject_text in entity_names:
                    entity_name = subject.text
                else:
                    # Buscar coincidencia parcial
                    for name in entity_names:
                        if subject_text in name or name in subject_text:
                            entity_name = name
                            break

                if not entity_name or not obj:
                    continue

                # Verificar si el objeto es una parte del cuerpo
                obj_lemma = obj.lemma_.lower()

                if obj_lemma in BODY_PARTS_TO_ATTR:
                    base_attr_type = BODY_PARTS_TO_ATTR[obj_lemma]
                    type_attr = BODY_PARTS_WITH_TYPE.get(obj_lemma)

                    # Buscar adjetivos que modifican el objeto
                    for child in obj.children:
                        if child.pos_ == "ADJ":
                            adj_lower = child.text.lower()

                            # Determinar si es color o tipo
                            if type_attr and adj_lower in PHYSICAL_DESCRIPTORS.get("hair_type", set()):
                                attr_type = type_attr
                            else:
                                attr_type = base_attr_type

                            attributes.append(self._create_attribute(
                                entity_name=entity_name,
                                attr_type=attr_type,
                                value=adj_lower,
                                confidence=0.90,
                                source_text=token.sent.text,
                                chapter=chapter,
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

        for token in doc:
            # Buscar "de" seguido de nombre
            if token.text.lower() == "de" and token.dep_ == "case":
                # El head de "de" debería ser el nombre
                entity_token = token.head

                entity_name = None
                if entity_token.text.lower() in entity_names:
                    entity_name = entity_token.text
                else:
                    for name in entity_names:
                        if entity_token.text.lower() in name.lower():
                            entity_name = name
                            break

                if not entity_name:
                    continue

                # Buscar la parte del cuerpo (el abuelo de "de")
                parent = entity_token.head

                if parent.lemma_.lower() in BODY_PARTS_TO_ATTR:
                    base_attr_type = BODY_PARTS_TO_ATTR[parent.lemma_.lower()]

                    # Buscar adjetivo que modifica la parte del cuerpo
                    for child in parent.children:
                        if child.pos_ == "ADJ":
                            attributes.append(self._create_attribute(
                                entity_name=entity_name,
                                attr_type=base_attr_type,
                                value=child.text.lower(),
                                confidence=0.85,
                                source_text=token.sent.text,
                                chapter=chapter,
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

        # Track última entidad mencionada
        last_entity = None

        for token in doc:
            # Actualizar última entidad
            if token.text.lower() in entity_names:
                last_entity = token.text
            else:
                for name in entity_names:
                    if token.text.lower() in name.lower() or name.lower() in token.text.lower():
                        last_entity = name
                        break

            # Buscar posesivos (su, sus)
            if token.text.lower() in {"su", "sus"} and token.pos_ == "DET":
                # El head debería ser el sustantivo
                noun = token.head

                if noun.lemma_.lower() not in BODY_PARTS_TO_ATTR:
                    continue

                if not last_entity:
                    continue

                base_attr_type = BODY_PARTS_TO_ATTR[noun.lemma_.lower()]

                # Buscar adjetivo que modifica el sustantivo
                for child in noun.children:
                    if child.pos_ == "ADJ":
                        attributes.append(self._create_attribute(
                            entity_name=last_entity,
                            attr_type=base_attr_type,
                            value=child.text.lower(),
                            confidence=0.70,  # Menor confianza por ambigüedad
                            source_text=token.sent.text,
                            chapter=chapter,
                        ))

        return attributes

    def _extract_enumerations(
        self,
        doc: Any,
        entity_names: set[str],
        chapter: Optional[int],
    ) -> list[ExtractedAttribute]:
        """
        Extrae atributos de enumeraciones de adjetivos.

        Patrones:
        - "Un hombre alto, delgado y moreno"
        - "María, alta y de ojos claros"
        """
        attributes = []

        for token in doc:
            # Buscar conjunciones "y"
            if token.text.lower() == "y" and token.pos_ == "CCONJ":
                # Buscar adjetivos coordinados
                head = token.head
                if head.pos_ != "ADJ":
                    continue

                # Encontrar todos los adjetivos en la coordinación
                coordinated_adjs = [head]

                for child in head.children:
                    if child.pos_ == "ADJ":
                        coordinated_adjs.append(child)
                    elif child.dep_ == "conj" and child.pos_ == "ADJ":
                        coordinated_adjs.append(child)

                if len(coordinated_adjs) < 2:
                    continue

                # Buscar la entidad asociada
                entity_name = self._find_entity_for_adjectives(head, entity_names, doc)

                if not entity_name:
                    continue

                # Crear atributo para cada adjetivo
                for adj in coordinated_adjs:
                    attr_type = self._classify_attribute(adj.text)
                    if attr_type:
                        attributes.append(self._create_attribute(
                            entity_name=entity_name,
                            attr_type=attr_type,
                            value=adj.text.lower(),
                            confidence=0.75,
                            source_text=head.sent.text,
                            chapter=chapter,
                        ))

        return attributes

    def _find_subject(self, verb_token: Any) -> Optional[Any]:
        """Encuentra el sujeto de un verbo."""
        # Buscar en hijos directos
        for child in verb_token.children:
            if child.dep_ == "nsubj":
                return child

        # Si el verbo es auxiliar, buscar en el head
        if verb_token.dep_ == "cop":
            for child in verb_token.head.children:
                if child.dep_ == "nsubj":
                    return child

        return None

    def _resolve_pronoun(
        self,
        doc: Any,
        pronoun_token: Any,
        entity_names: set[str],
    ) -> Optional[str]:
        """Resuelve un pronombre a la última entidad mencionada."""
        # Buscar hacia atrás la última entidad
        for token in reversed(list(doc[:pronoun_token.i])):
            if token.text.lower() in entity_names:
                return token.text
            for name in entity_names:
                if token.text.lower() in name.lower():
                    return name

        return None

    def _find_entity_for_adjectives(
        self,
        adj_token: Any,
        entity_names: set[str],
        doc: Any,
    ) -> Optional[str]:
        """Encuentra la entidad a la que se refieren los adjetivos."""
        # Buscar en el contexto cercano
        for token in adj_token.sent:
            if token.text.lower() in entity_names:
                return token.text
            for name in entity_names:
                if token.text.lower() in name.lower():
                    return name

        return None

    def _classify_attribute(self, value: str) -> Optional[AttributeType]:
        """
        Clasifica un valor de atributo en su tipo correspondiente.
        """
        value_lower = value.lower()

        for attr_type_str, values in PHYSICAL_DESCRIPTORS.items():
            if value_lower in values:
                try:
                    return AttributeType(attr_type_str)
                except ValueError:
                    continue

        return None

    def _separate_compound_attributes(
        self,
        attributes: list[ExtractedAttribute],
    ) -> list[ExtractedAttribute]:
        """Separa atributos compuestos."""
        result = []
        import re

        hair_colors = PHYSICAL_DESCRIPTORS.get("hair_color", set())
        hair_types = PHYSICAL_DESCRIPTORS.get("hair_type", set())

        for attr in attributes:
            # Buscar patrón "X y Y"
            match = re.search(r'(\w+)\s+y\s+(\w+)', attr.value, re.IGNORECASE)

            if match:
                val1 = match.group(1).lower()
                val2 = match.group(2).lower()

                # Determinar tipos
                type1 = None
                type2 = None

                if val1 in hair_colors:
                    type1 = AttributeType.HAIR_COLOR
                elif val1 in hair_types:
                    type1 = AttributeType.HAIR_TYPE

                if val2 in hair_colors:
                    type2 = AttributeType.HAIR_COLOR
                elif val2 in hair_types:
                    type2 = AttributeType.HAIR_TYPE

                if type1 and type2 and type1 != type2:
                    # Separar
                    result.append(self._create_attribute(
                        entity_name=attr.entity_name,
                        attr_type=type1,
                        value=val1,
                        confidence=attr.confidence * 0.95,
                        source_text=attr.source_text,
                        chapter=attr.chapter,
                    ))
                    result.append(self._create_attribute(
                        entity_name=attr.entity_name,
                        attr_type=type2,
                        value=val2,
                        confidence=attr.confidence * 0.95,
                        source_text=attr.source_text,
                        chapter=attr.chapter,
                    ))
                else:
                    result.append(attr)
            else:
                result.append(attr)

        return result

    def _deduplicate(
        self,
        attributes: list[ExtractedAttribute],
    ) -> list[ExtractedAttribute]:
        """Elimina duplicados manteniendo el de mayor confianza."""
        seen: dict[tuple, ExtractedAttribute] = {}

        for attr in attributes:
            key = (
                attr.entity_name.lower(),
                attr.attribute_type,
                attr.value.lower(),
            )

            if key not in seen or attr.confidence > seen[key].confidence:
                seen[key] = attr

        return list(seen.values())
