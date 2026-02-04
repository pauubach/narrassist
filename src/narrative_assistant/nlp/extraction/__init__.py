"""
Pipeline de extracción de atributos híbrido.

Este módulo implementa una arquitectura de extracción en capas que combina:
1. Extracción rápida (regex + dependency parsing)
2. Enriquecimiento semántico (embeddings)
3. Refinamiento con LLM local (opcional, Ollama)

La arquitectura usa:
- Strategy Pattern: Cada extractor implementa BaseExtractor
- Complexity Router: Selecciona extractores según complejidad del texto
- Result Aggregator: Combina resultados con votación ponderada

Uso:
    >>> from narrative_assistant.nlp.extraction import AttributeExtractionPipeline
    >>> pipeline = AttributeExtractionPipeline()
    >>> attributes = pipeline.extract(text, entity_names=["María", "Juan"])
"""

from .aggregator import ResultAggregator
from .base import (
    AggregatedAttribute,
    AttributeType,
    BaseExtractor,
    ExtractedAttribute,
    ExtractionContext,
    ExtractionMethod,
    ExtractionResult,
)
from .pipeline import (
    AttributeExtractionPipeline,
    PipelineConfig,
    get_extraction_pipeline,
    reset_extraction_pipeline,
)
from .router import ComplexityRouter, ComplexityScore

__all__ = [
    # Base
    "BaseExtractor",
    "ExtractionContext",
    "ExtractionMethod",
    "ExtractionResult",
    "ExtractedAttribute",
    "AggregatedAttribute",
    "AttributeType",
    # Router
    "ComplexityRouter",
    "ComplexityScore",
    # Aggregator
    "ResultAggregator",
    # Pipeline
    "AttributeExtractionPipeline",
    "PipelineConfig",
    "get_extraction_pipeline",
    "reset_extraction_pipeline",
]
