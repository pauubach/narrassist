# -*- coding: utf-8 -*-
"""
Agregador de resultados con votación ponderada.

Combina resultados de múltiples extractores usando:
- Pesos por método de extracción
- Votación por consenso
- Boost por unanimidad
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from .base import (
    ExtractionMethod,
    ExtractionResult,
    ExtractedAttribute,
    AggregatedAttribute,
    AttributeType,
)

logger = logging.getLogger(__name__)


class ResultAggregator:
    """
    Agrega resultados de múltiples extractores usando votación ponderada.

    Estrategia:
    1. Agrupa atributos por (entidad, tipo)
    2. Para cada grupo, calcula consenso ponderado
    3. Si hay conflicto, usa confianza de extractores para resolver

    Example:
        >>> aggregator = ResultAggregator(min_confidence=0.5)
        >>> results = [regex_result, dependency_result]
        >>> aggregated = aggregator.aggregate(results)
        >>> for attr in aggregated:
        ...     print(f"{attr.entity_name}.{attr.attribute_type}: {attr.value}")
    """

    # Pesos por método de extracción
    # Basados en precisión esperada de cada método
    METHOD_WEIGHTS = {
        ExtractionMethod.REGEX: 0.90,        # Alta precisión para patrones conocidos
        ExtractionMethod.DEPENDENCY: 0.80,   # Buena precisión general
        ExtractionMethod.EMBEDDINGS: 0.65,   # Aproximado, útil para clasificación
        ExtractionMethod.SEMANTIC_LLM: 0.85, # Buena precisión pero costoso
    }

    def __init__(
        self,
        min_confidence: float = 0.5,
        boost_unanimous: float = 1.15,
        penalty_contested: float = 0.85,
    ):
        """
        Inicializa el agregador.

        Args:
            min_confidence: Confianza mínima para incluir en resultado
            boost_unanimous: Multiplicador para consenso unánime
            penalty_contested: Multiplicador para consenso contestado
        """
        self.min_confidence = min_confidence
        self.boost_unanimous = boost_unanimous
        self.penalty_contested = penalty_contested

    def aggregate(
        self,
        results: list[ExtractionResult],
    ) -> list[AggregatedAttribute]:
        """
        Agrega resultados de múltiples extractores.

        Args:
            results: Lista de ExtractionResult de diferentes extractores

        Returns:
            Lista de AggregatedAttribute con consenso
        """
        if not results:
            return []

        # Paso 1: Agrupar por (entidad, tipo)
        grouped = self._group_attributes(results)

        # Paso 2: Resolver cada grupo
        aggregated = []
        for key, attrs in grouped.items():
            entity_name, attr_type = key
            resolved = self._resolve_group(entity_name, attr_type, attrs)

            if resolved and resolved.final_confidence >= self.min_confidence:
                aggregated.append(resolved)

        logger.debug(f"Aggregated {len(aggregated)} attributes from {len(results)} results")
        return aggregated

    def _group_attributes(
        self,
        results: list[ExtractionResult],
    ) -> dict[tuple[str, AttributeType], list[ExtractedAttribute]]:
        """
        Agrupa atributos por (entidad, tipo).
        """
        grouped: dict[tuple[str, AttributeType], list[ExtractedAttribute]] = defaultdict(list)

        for result in results:
            for attr in result.attributes:
                # Normalizar nombre de entidad
                key = (attr.entity_name.lower(), attr.attribute_type)
                grouped[key].append(attr)

        return grouped

    def _resolve_group(
        self,
        entity_name: str,
        attr_type: AttributeType,
        attrs: list[ExtractedAttribute],
    ) -> Optional[AggregatedAttribute]:
        """
        Resuelve un grupo de atributos potencialmente conflictivos.

        Estrategia:
        1. Si todos dicen lo mismo -> unanimidad (boost)
        2. Si mayoría dice lo mismo -> mayoría
        3. Si hay empate -> usar pesos de métodos
        """
        if not attrs:
            return None

        if len(attrs) == 1:
            # Único extractor
            attr = attrs[0]
            weight = self.METHOD_WEIGHTS.get(attr.extraction_method, 0.5)

            return AggregatedAttribute(
                entity_name=attr.entity_name,
                attribute_type=attr_type,
                value=attr.value,
                final_confidence=attr.confidence * weight,
                sources=[(attr.extraction_method, attr.confidence)],
                consensus_level="single",
                chapter=attr.chapter,
                is_negated=attr.is_negated,
            )

        # Múltiples extractores - agrupar por valor normalizado
        value_votes: dict[str, list[tuple[ExtractedAttribute, float]]] = defaultdict(list)

        for attr in attrs:
            value_normalized = attr.value.lower().strip()
            weight = self.METHOD_WEIGHTS.get(attr.extraction_method, 0.5)
            weighted_confidence = attr.confidence * weight
            value_votes[value_normalized].append((attr, weighted_confidence))

        # Elegir valor con mayor puntuación ponderada
        best_value = None
        best_score = 0.0
        best_attrs: list[tuple[ExtractedAttribute, float]] = []

        for value, votes in value_votes.items():
            total_score = sum(conf for _, conf in votes)
            if total_score > best_score:
                best_score = total_score
                best_value = value
                best_attrs = votes

        if not best_value or not best_attrs:
            return None

        # Determinar nivel de consenso
        total_extractors = len(attrs)
        winning_extractors = len(best_attrs)

        if len(value_votes) == 1:
            # Todos de acuerdo
            consensus = "unanimous"
            confidence_modifier = self.boost_unanimous
        elif winning_extractors > total_extractors / 2:
            # Mayoría
            consensus = "majority"
            confidence_modifier = 1.0
        else:
            # Conflicto
            consensus = "contested"
            confidence_modifier = self.penalty_contested

        # Calcular confianza final
        avg_weighted_conf = best_score / winning_extractors
        final_confidence = min(1.0, avg_weighted_conf * confidence_modifier)

        # Obtener valor original con formato (mayúsculas originales)
        original_value = best_value
        original_entity = entity_name
        chapter = None
        is_negated = False

        for attr, _ in best_attrs:
            if attr.value.lower().strip() == best_value:
                original_value = attr.value
                original_entity = attr.entity_name
                chapter = attr.chapter
                is_negated = attr.is_negated
                break

        # Crear lista de fuentes
        sources = [
            (attr.extraction_method, conf)
            for attr, conf in best_attrs
        ]

        return AggregatedAttribute(
            entity_name=original_entity,
            attribute_type=attr_type,
            value=original_value,
            final_confidence=final_confidence,
            sources=sources,
            consensus_level=consensus,
            chapter=chapter,
            is_negated=is_negated,
        )

    def get_conflicts(
        self,
        results: list[ExtractionResult],
    ) -> list[dict]:
        """
        Retorna información sobre atributos en conflicto.

        Útil para debugging y para mostrar al usuario
        casos donde los extractores no están de acuerdo.
        """
        conflicts = []
        grouped = self._group_attributes(results)

        for (entity, attr_type), attrs in grouped.items():
            # Agrupar por valor
            values = defaultdict(list)
            for attr in attrs:
                values[attr.value.lower()].append(attr.extraction_method.value)

            if len(values) > 1:
                conflicts.append({
                    "entity": entity,
                    "attribute_type": attr_type.value,
                    "values": {v: methods for v, methods in values.items()},
                })

        return conflicts

    def merge_with_previous(
        self,
        new_attributes: list[AggregatedAttribute],
        previous_attributes: list[AggregatedAttribute],
    ) -> list[AggregatedAttribute]:
        """
        Combina atributos nuevos con atributos previos.

        Útil para análisis incremental de documentos.
        Los nuevos atributos tienen prioridad.
        """
        # Crear mapa de atributos previos
        prev_map: dict[tuple[str, AttributeType], AggregatedAttribute] = {}
        for attr in previous_attributes:
            key = (attr.entity_name.lower(), attr.attribute_type)
            prev_map[key] = attr

        # Agregar nuevos (sobrescriben previos)
        for attr in new_attributes:
            key = (attr.entity_name.lower(), attr.attribute_type)
            prev_map[key] = attr

        return list(prev_map.values())
