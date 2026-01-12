# -*- coding: utf-8 -*-
"""
Extractor basado en embeddings y similaridad semántica.

Este extractor usa sentence-transformers para:
1. Clasificar valores ambiguos en categorías correctas
2. Encontrar atributos mediante similaridad semántica
3. Separar atributos compuestos de forma inteligente
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


# Templates para cada tipo de atributo
ATTRIBUTE_TEMPLATES = {
    AttributeType.EYE_COLOR: [
        "tiene ojos de color {value}",
        "sus ojos son {value}",
        "ojos {value}",
    ],
    AttributeType.HAIR_COLOR: [
        "tiene el pelo {value}",
        "su cabello es {value}",
        "pelo de color {value}",
    ],
    AttributeType.HAIR_TYPE: [
        "tiene el pelo {value}",
        "su cabello es {value}",
        "cabello {value}",
    ],
    AttributeType.HEIGHT: [
        "es una persona {value}",
        "tiene una estatura {value}",
        "es {value} de altura",
    ],
    AttributeType.BUILD: [
        "tiene complexión {value}",
        "es de cuerpo {value}",
        "su figura es {value}",
    ],
    AttributeType.AGE: [
        "tiene {value} años",
        "es una persona {value}",
        "aparenta ser {value}",
    ],
    AttributeType.SKIN: [
        "tiene piel {value}",
        "su piel es {value}",
        "de tez {value}",
    ],
}

# Valores canónicos para cada tipo de atributo
CANONICAL_VALUES = {
    AttributeType.EYE_COLOR: [
        "azul", "verde", "marrón", "negro", "gris", "avellana", "ámbar", "violeta",
    ],
    AttributeType.HAIR_COLOR: [
        "negro", "rubio", "castaño", "pelirrojo", "canoso", "gris", "blanco",
    ],
    AttributeType.HAIR_TYPE: [
        "largo", "corto", "rizado", "liso", "ondulado",
    ],
    AttributeType.HEIGHT: [
        "alto", "bajo", "mediano",
    ],
    AttributeType.BUILD: [
        "delgado", "fornido", "robusto", "atlético", "corpulento",
    ],
    AttributeType.AGE: [
        "joven", "mayor", "anciano", "adulto",
    ],
    AttributeType.SKIN: [
        "pálido", "moreno", "bronceado", "claro", "oscuro",
    ],
}


class EmbeddingsExtractor(BaseExtractor):
    """
    Extractor basado en embeddings semánticos.

    Funciona de forma complementaria a regex/dependency:
    - Clasifica valores ambiguos (¿"oscuro" es pelo o piel?)
    - Valida extracciones de otros métodos
    - Encuentra atributos mediante búsqueda semántica

    Example:
        >>> extractor = EmbeddingsExtractor()
        >>> # Clasificar un valor ambiguo
        >>> attr_type = extractor.classify_value("oscuro", "su cabello oscuro")
        >>> print(attr_type)  # AttributeType.HAIR_COLOR
    """

    def __init__(self, similarity_threshold: float = 0.6):
        """
        Inicializa el extractor.

        Args:
            similarity_threshold: Umbral mínimo de similaridad semántica
        """
        self.similarity_threshold = similarity_threshold
        self._embeddings = None
        self._template_embeddings: dict[AttributeType, list[Any]] = {}
        self._value_embeddings: dict[AttributeType, dict[str, Any]] = {}

    @property
    def embeddings(self):
        """Lazy loading del modelo de embeddings."""
        if self._embeddings is None:
            from ...embeddings import get_embeddings_model
            self._embeddings = get_embeddings_model()
            self._precompute_embeddings()
        return self._embeddings

    def _precompute_embeddings(self) -> None:
        """Pre-calcula embeddings de templates y valores canónicos."""
        logger.info("Pre-computing embeddings for attribute classification...")

        # Embeddings de valores canónicos por tipo
        for attr_type, values in CANONICAL_VALUES.items():
            self._value_embeddings[attr_type] = {}
            for value in values:
                # Generar texto contextualizado
                templates = ATTRIBUTE_TEMPLATES.get(attr_type, ["{value}"])
                texts = [t.format(value=value) for t in templates]
                avg_text = texts[0] if texts else value

                # Calcular embedding normalizado para similitud coseno
                emb = self._embeddings.encode(avg_text, normalize=True)
                self._value_embeddings[attr_type][value] = emb

        logger.info("Embeddings pre-computed successfully")

    def _compute_similarity(self, emb1, emb2) -> float:
        """
        Calcula similitud coseno entre dos embeddings.

        Args:
            emb1: Primer embedding (numpy array, normalizado)
            emb2: Segundo embedding (numpy array, normalizado)

        Returns:
            Similitud coseno como float
        """
        import numpy as np

        # Aplanar si es necesario
        e1 = emb1.flatten() if hasattr(emb1, 'flatten') else emb1
        e2 = emb2.flatten() if hasattr(emb2, 'flatten') else emb2

        # Dot product de vectores normalizados = similitud coseno
        similarity = float(np.dot(e1, e2))

        return similarity

    @property
    def method(self) -> ExtractionMethod:
        return ExtractionMethod.EMBEDDINGS

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
        }

    def can_handle(self, context: ExtractionContext) -> float:
        """
        Embeddings son útiles para textos con descripciones ambiguas.
        """
        # Menos útil que regex/dependency para extracción directa
        # Pero útil para clasificación y validación
        return 0.5

    def extract(self, context: ExtractionContext) -> ExtractionResult:
        """
        Extrae atributos usando búsqueda semántica.

        Este extractor es más lento pero puede encontrar atributos
        que no coinciden con patrones exactos.
        """
        attributes = []
        errors = []

        try:
            # Forzar carga de embeddings
            _ = self.embeddings

            # Para cada entidad, buscar descripciones en el texto
            for entity_name in context.entity_names:
                entity_attrs = self._extract_for_entity(
                    context.text,
                    entity_name,
                    context.chapter,
                )
                attributes.extend(entity_attrs)

            # Deduplicar
            attributes = self._deduplicate(attributes)

            logger.debug(f"EmbeddingsExtractor found {len(attributes)} attributes")

        except Exception as e:
            errors.append(f"Error in embeddings extraction: {str(e)}")
            logger.exception("Error in embeddings extraction")

        return self._create_result(attributes, errors)

    def _extract_for_entity(
        self,
        text: str,
        entity_name: str,
        chapter: Optional[int],
    ) -> list[ExtractedAttribute]:
        """
        Extrae atributos para una entidad específica.
        """
        attributes = []

        # Encontrar oraciones que mencionan la entidad
        sentences = self._find_entity_sentences(text, entity_name)

        for sentence in sentences:
            # Calcular embedding de la oración (normalizado)
            sent_embedding = self._embeddings.encode(sentence, normalize=True)

            # Comparar con templates de cada tipo de atributo
            for attr_type, value_embs in self._value_embeddings.items():
                for value, value_emb in value_embs.items():
                    # Calcular similitud coseno directamente entre embeddings
                    similarity = self._compute_similarity(sent_embedding, value_emb)

                    if similarity >= self.similarity_threshold:
                        # Verificar que el valor aparece en la oración
                        if value.lower() in sentence.lower():
                            attributes.append(self._create_attribute(
                                entity_name=entity_name,
                                attr_type=attr_type,
                                value=value,
                                confidence=float(similarity) * 0.8,  # Reducir un poco
                                source_text=sentence,
                                chapter=chapter,
                            ))

        return attributes

    def _find_entity_sentences(
        self,
        text: str,
        entity_name: str,
    ) -> list[str]:
        """
        Encuentra oraciones que mencionan una entidad.
        """
        import re

        sentences = re.split(r'[.!?]+', text)
        entity_sentences = []

        entity_lower = entity_name.lower()
        for sentence in sentences:
            sentence = sentence.strip()
            if entity_lower in sentence.lower():
                entity_sentences.append(sentence)

        return entity_sentences

    def classify_value(
        self,
        value: str,
        context_text: str,
    ) -> Optional[AttributeType]:
        """
        Clasifica un valor ambiguo en su tipo de atributo.

        Útil para valores como "oscuro" que pueden ser pelo, ojos o piel.

        Args:
            value: Valor a clasificar (ej: "oscuro")
            context_text: Texto de contexto (ej: "su cabello oscuro")

        Returns:
            AttributeType más probable o None
        """
        # Forzar carga
        _ = self.embeddings

        # Calcular embedding del contexto (normalizado)
        context_emb = self._embeddings.encode(context_text, normalize=True)

        best_type = None
        best_similarity = 0.0

        # Comparar con cada tipo
        for attr_type, value_embs in self._value_embeddings.items():
            for canonical_value, value_emb in value_embs.items():
                similarity = self._compute_similarity(context_emb, value_emb)

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_type = attr_type

        if best_similarity >= self.similarity_threshold:
            return best_type

        return None

    def validate_attribute(
        self,
        attr: ExtractedAttribute,
    ) -> float:
        """
        Valida un atributo extraído por otro método.

        Retorna una puntuación de validez (0-1) basada en
        qué tan bien el valor encaja con el tipo de atributo.

        Args:
            attr: Atributo a validar

        Returns:
            Puntuación de validez (0.0-1.0)
        """
        # Forzar carga
        _ = self.embeddings

        if attr.attribute_type not in self._value_embeddings:
            return 0.5  # No tenemos datos para este tipo

        # Calcular embedding del atributo (normalizado)
        attr_text = f"tiene {attr.attribute_type.value} {attr.value}"
        attr_emb = self._embeddings.encode(attr_text, normalize=True)

        # Comparar con valores canónicos del mismo tipo
        max_similarity = 0.0
        for value, value_emb in self._value_embeddings[attr.attribute_type].items():
            similarity = self._compute_similarity(attr_emb, value_emb)
            max_similarity = max(max_similarity, float(similarity))

        return max_similarity

    def suggest_attribute_type(
        self,
        value: str,
    ) -> list[tuple[AttributeType, float]]:
        """
        Sugiere tipos de atributo para un valor dado.

        Retorna lista ordenada de (tipo, confianza).

        Args:
            value: Valor para el cual sugerir tipos

        Returns:
            Lista de (AttributeType, confianza) ordenada por confianza
        """
        # Forzar carga
        _ = self.embeddings

        suggestions = []
        value_emb = self._embeddings.encode(value, normalize=True)

        for attr_type, value_embs in self._value_embeddings.items():
            max_similarity = 0.0
            for _, canonical_emb in value_embs.items():
                similarity = self._compute_similarity(value_emb, canonical_emb)
                max_similarity = max(max_similarity, float(similarity))

            if max_similarity > 0.3:  # Umbral mínimo
                suggestions.append((attr_type, max_similarity))

        # Ordenar por confianza descendente
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return suggestions

    def _deduplicate(
        self,
        attributes: list[ExtractedAttribute],
    ) -> list[ExtractedAttribute]:
        """Elimina duplicados."""
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
