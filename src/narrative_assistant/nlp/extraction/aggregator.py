"""
Agregador de resultados con votación ponderada multicapa.

Combina resultados de múltiples extractores usando:
- Pesos diferenciados por precisión y recall de cada método
- Votación multicapa: primero métodos rápidos, luego semánticos, finalmente LLM
- Boost por unanimidad entre métodos de diferentes familias
- Penalización por conflictos

Arquitectura de capas:
    CAPA 1 (Sintáctica - Rápida):
        - RegexExtractor: Alta precisión (0.95), bajo recall
        - DependencyExtractor: Buena precisión (0.85), buen recall

    CAPA 2 (Semántica - Media):
        - EmbeddingsExtractor: Precisión media (0.70), alto recall

    CAPA 3 (LLM - Costosa):
        - LLMExtractor: Alta precisión (0.90), alto recall, costoso

La votación considera:
    - Acuerdo entre capas diferentes vale más que dentro de la misma capa
    - LLM se usa para verificar conflictos entre capas 1-2
    - Consenso unánime entre 3+ métodos → alta confianza
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

from .base import (
    AggregatedAttribute,
    AttributeType,
    ExtractedAttribute,
    ExtractionMethod,
    ExtractionResult,
)

logger = logging.getLogger(__name__)


class ExtractionLayer(Enum):
    """Capas de extracción por costo computacional."""

    SYNTACTIC = "syntactic"  # Regex, Dependency
    SEMANTIC = "semantic"  # Embeddings
    LLM = "llm"  # LLM local


# Mapeo de métodos a capas
METHOD_TO_LAYER = {
    ExtractionMethod.REGEX: ExtractionLayer.SYNTACTIC,
    ExtractionMethod.DEPENDENCY: ExtractionLayer.SYNTACTIC,
    ExtractionMethod.EMBEDDINGS: ExtractionLayer.SEMANTIC,
    ExtractionMethod.SEMANTIC_LLM: ExtractionLayer.LLM,
}


@dataclass
class MethodMetrics:
    """Métricas de rendimiento esperado por método."""

    precision: float  # Probabilidad de que un positivo sea correcto
    recall: float  # Probabilidad de detectar un positivo
    cost: float  # Costo relativo (0-1, mayor = más costoso)
    layer: ExtractionLayer


# Métricas por método (basadas en evaluación empírica)
METHOD_METRICS = {
    ExtractionMethod.REGEX: MethodMetrics(
        precision=0.95,  # Muy preciso pero solo para patrones conocidos
        recall=0.40,  # Bajo recall, muchos casos no cubiertos
        cost=0.1,
        layer=ExtractionLayer.SYNTACTIC,
    ),
    ExtractionMethod.DEPENDENCY: MethodMetrics(
        precision=0.85,  # Buena precisión general
        recall=0.70,  # Buen recall para estructuras gramaticales
        cost=0.3,
        layer=ExtractionLayer.SYNTACTIC,
    ),
    ExtractionMethod.EMBEDDINGS: MethodMetrics(
        precision=0.70,  # Precisión media, puede confundir semejanzas
        recall=0.80,  # Alto recall, detecta muchos casos
        cost=0.4,
        layer=ExtractionLayer.SEMANTIC,
    ),
    ExtractionMethod.SEMANTIC_LLM: MethodMetrics(
        precision=0.90,  # Alta precisión con buen contexto
        recall=0.85,  # Alto recall
        cost=1.0,  # Más costoso
        layer=ExtractionLayer.LLM,
    ),
}


class ResultAggregator:
    """
    Agrega resultados de múltiples extractores usando votación ponderada multicapa.

    Estrategia multicapa:
    1. Agrupa atributos por (entidad, tipo)
    2. Prioriza acuerdo entre capas diferentes (sintáctica + semántica)
    3. Usa F1-score ponderado para calcular confianza final
    4. Boost por acuerdo cross-layer, penalización por conflicto

    La votación considera precisión, recall y costo de cada método.
    Métodos de alta precisión tienen más peso en caso de conflicto.
    Métodos de alto recall contribuyen cuando otros no detectan.

    Example:
        >>> aggregator = ResultAggregator(min_confidence=0.5)
        >>> results = [regex_result, dependency_result, embeddings_result]
        >>> aggregated = aggregator.aggregate(results)
        >>> for attr in aggregated:
        ...     print(f"{attr.entity_name}.{attr.attribute_type}: {attr.value}")
    """

    def _calculate_method_weight(self, method: ExtractionMethod) -> float:
        """
        Calcula peso del método basado en F1-score de precisión y recall.

        F1 = 2 * (precision * recall) / (precision + recall)
        """
        metrics = METHOD_METRICS.get(method)
        if not metrics:
            return 0.5

        # F1-score como base
        f1 = 2 * (metrics.precision * metrics.recall) / (metrics.precision + metrics.recall)

        # Ajustar por costo inverso (métodos más baratos ligeramente favorecidos)
        cost_factor = 1.0 - (metrics.cost * 0.1)  # Max 10% reducción por costo

        return f1 * cost_factor

    def __init__(
        self,
        min_confidence: float = 0.5,
        boost_unanimous: float = 1.10,
        boost_cross_layer: float = 1.20,
        penalty_contested: float = 0.80,
    ):
        """
        Inicializa el agregador.

        Args:
            min_confidence: Confianza mínima para incluir en resultado
            boost_unanimous: Multiplicador para consenso unánime (misma capa)
            boost_cross_layer: Multiplicador para consenso entre capas diferentes
            penalty_contested: Multiplicador para consenso contestado
        """
        self.min_confidence = min_confidence
        self.boost_unanimous = boost_unanimous
        self.boost_cross_layer = boost_cross_layer
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
    ) -> AggregatedAttribute | None:
        """
        Resuelve un grupo de atributos usando votación multicapa.

        Estrategia multicapa:
        1. Único extractor → usar precisión del método
        2. Misma capa de acuerdo → boost moderado
        3. Cross-layer agreement → boost significativo (más confiable)
        4. Conflicto → usar precisión para decidir, penalizar confianza

        La idea es que si métodos de diferentes familias (sintáctico vs semántico)
        coinciden, la confianza es mayor que si solo métodos similares coinciden.
        """
        if not attrs:
            return None

        if len(attrs) == 1:
            # Único extractor - usar métricas del método
            attr = attrs[0]
            metrics = METHOD_METRICS.get(attr.extraction_method)
            if metrics:
                # Confianza = confianza del extractor * precisión esperada del método
                final_conf = attr.confidence * metrics.precision
            else:
                final_conf = attr.confidence * 0.5

            return AggregatedAttribute(
                entity_name=attr.entity_name,
                attribute_type=attr_type,
                value=attr.value,
                final_confidence=final_conf,
                sources=[(attr.extraction_method, attr.confidence)],
                consensus_level="single",
                chapter=attr.chapter,
                is_negated=attr.is_negated,
            )

        # Múltiples extractores - agrupar por valor normalizado
        value_votes: dict[str, list[tuple[ExtractedAttribute, float]]] = defaultdict(list)

        for attr in attrs:
            value_normalized = attr.value.lower().strip()
            weight = self._calculate_method_weight(attr.extraction_method)
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

        # Analizar capas involucradas
        layers_in_agreement = set()
        for attr, _ in best_attrs:
            layer = METHOD_TO_LAYER.get(attr.extraction_method)
            if layer:
                layers_in_agreement.add(layer)

        # Determinar nivel de consenso con lógica multicapa
        total_extractors = len(attrs)
        winning_extractors = len(best_attrs)
        num_layers_agree = len(layers_in_agreement)

        if len(value_votes) == 1:
            # Todos de acuerdo
            if num_layers_agree >= 2:
                # Cross-layer unanimous - muy confiable
                consensus = "cross_layer_unanimous"
                confidence_modifier = self.boost_cross_layer
            else:
                consensus = "unanimous"
                confidence_modifier = self.boost_unanimous
        elif winning_extractors > total_extractors / 2:
            # Mayoría
            if num_layers_agree >= 2:
                # Cross-layer majority - bastante confiable
                consensus = "cross_layer_majority"
                confidence_modifier = self.boost_cross_layer * 0.9
            else:
                consensus = "majority"
                confidence_modifier = 1.0
        else:
            # Conflicto - usar método de mayor precisión para decidir
            consensus = "contested"
            # Verificar si el ganador incluye método de alta precisión
            has_high_precision = any(
                METHOD_METRICS.get(
                    attr.extraction_method, MethodMetrics(0.5, 0.5, 0.5, ExtractionLayer.SYNTACTIC)
                ).precision
                >= 0.85
                for attr, _ in best_attrs
            )
            if has_high_precision:
                confidence_modifier = self.penalty_contested * 1.1  # Menos penalización
            else:
                confidence_modifier = self.penalty_contested

        # Calcular confianza final
        avg_weighted_conf = best_score / winning_extractors
        final_confidence = min(1.0, avg_weighted_conf * confidence_modifier)

        # Obtener valor original con formato (mayúsculas originales)
        original_value = best_value
        original_entity = entity_name
        chapter = None
        is_negated = False

        # Preferir el valor del método de mayor precisión
        best_precision = 0.0
        for attr, _ in best_attrs:
            metrics = METHOD_METRICS.get(attr.extraction_method)
            precision = metrics.precision if metrics else 0.5
            if precision > best_precision and attr.value.lower().strip() == best_value:
                best_precision = precision
                original_value = attr.value
                original_entity = attr.entity_name
                chapter = attr.chapter
                is_negated = attr.is_negated

        # Crear lista de fuentes
        sources = [(attr.extraction_method, conf) for attr, conf in best_attrs]

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
                conflicts.append(
                    {
                        "entity": entity,
                        "attribute_type": attr_type.value,
                        "values": dict(values.items()),
                    }
                )

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
