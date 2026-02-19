"""
Pipeline principal de extracción de atributos híbrido.

Orquesta múltiples extractores usando:
- Strategy Pattern: Cada extractor implementa BaseExtractor
- Complexity Router: Selecciona extractores según complejidad del texto
- Result Aggregator: Combina resultados con votación ponderada
"""

import logging
from dataclasses import dataclass
from typing import Any

from .aggregator import ResultAggregator
from .base import (
    AggregatedAttribute,
    BaseExtractor,
    ExtractionContext,
    ExtractionMethod,
)
from .router import ComplexityRouter

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """
    Configuración del pipeline de extracción.

    Attributes:
        use_regex: Habilitar extractor regex
        use_dependency: Habilitar extractor de dependencias
        use_embeddings: Habilitar extractor semántico
        use_llm: Habilitar extractor LLM (requiere Ollama)
        min_confidence: Confianza mínima para incluir atributos
        complexity_threshold_for_llm: Umbral de complejidad para usar LLM
        parallel_extraction: Ejecutar extractores en paralelo
        max_workers: Número máximo de workers para paralelismo
        enable_cache: Habilitar cache de resultados
        cache_ttl_seconds: TTL del cache en segundos
    """

    use_regex: bool = True
    use_dependency: bool = True
    use_embeddings: bool = True
    use_llm: bool = False  # Deshabilitado por defecto

    min_confidence: float = 0.5
    complexity_threshold_for_llm: float = 0.7

    parallel_extraction: bool = True
    max_workers: int = 4

    enable_cache: bool = True
    cache_ttl_seconds: int = 3600


class AttributeExtractionPipeline:
    """
    Pipeline principal de extracción de atributos.

    Combina múltiples extractores para máxima cobertura y precisión:
    1. RegexExtractor: Patrones de alta precisión
    2. DependencyExtractor: Análisis gramatical
    3. EmbeddingsExtractor: Clasificación semántica
    4. LLMExtractor: Refinamiento con LLM local (opcional)

    Example:
        >>> pipeline = AttributeExtractionPipeline()
        >>> attributes = pipeline.extract(
        ...     "María tenía los ojos azules y era alta.",
        ...     entity_names=["María"]
        ... )
        >>> for attr in attributes:
        ...     print(f"{attr.entity_name}: {attr.attribute_type.value} = {attr.value}")
    """

    def __init__(
        self,
        config: PipelineConfig | None = None,
        extractors: list[BaseExtractor] | None = None,
    ):
        """
        Inicializa el pipeline.

        Args:
            config: Configuración del pipeline
            extractors: Lista de extractores personalizados (opcional)
        """
        self.config = config or PipelineConfig()
        self.router = ComplexityRouter(
            complexity_threshold_for_llm=self.config.complexity_threshold_for_llm
        )
        self.aggregator = ResultAggregator(min_confidence=self.config.min_confidence)

        # Inicializar extractores
        self.extractors = extractors or self._create_default_extractors()

        # Cache de resultados
        self._cache: dict[str, list[AggregatedAttribute]] = {}

        # spaCy doc compartido (para evitar reprocesar)
        self._nlp = None

    @property
    def nlp(self):
        """Lazy loading del modelo spaCy."""
        if self._nlp is None:
            from ..spacy_gpu import load_spacy_model

            self._nlp = load_spacy_model()
        return self._nlp

    def _create_default_extractors(self) -> list[BaseExtractor]:
        """Crea extractores según configuración."""
        extractors: list[BaseExtractor] = []

        if self.config.use_regex:
            from .extractors.regex_extractor import RegexExtractor

            extractors.append(RegexExtractor())
            logger.debug("RegexExtractor enabled")

        if self.config.use_dependency:
            from .extractors.dependency_extractor import DependencyExtractor

            extractors.append(DependencyExtractor())
            logger.debug("DependencyExtractor enabled")

        if self.config.use_embeddings:
            try:
                from .extractors.embeddings_extractor import EmbeddingsExtractor

                extractors.append(EmbeddingsExtractor())
                logger.debug("EmbeddingsExtractor enabled")
            except ImportError as e:
                logger.warning(f"EmbeddingsExtractor not available: {e}")

        if self.config.use_llm:
            try:
                from .extractors.llm_extractor import LLMExtractor

                extractors.append(LLMExtractor())
                logger.debug("LLMExtractor enabled")
            except ImportError as e:
                logger.warning(f"LLMExtractor not available: {e}")

        return extractors

    def extract(
        self,
        text: str,
        entity_names: list[str],
        entity_mentions: list[tuple[str, int, int, str | None]] | None = None,
        chapter: int | None = None,
    ) -> list[AggregatedAttribute]:
        """
        Extrae atributos del texto.

        Args:
            text: Texto a analizar
            entity_names: Nombres de entidades conocidas
            entity_mentions: Lista de menciones con posiciones (name, start, end, type)
            chapter: Número de capítulo (opcional)

        Returns:
            Lista de atributos agregados de todos los extractores
        """
        if not text or not entity_names:
            return []

        # Cache check
        cache_key = self._get_cache_key(text, entity_names)
        if self.config.enable_cache and cache_key in self._cache:
            logger.debug("Cache hit for attribute extraction")
            return self._cache[cache_key]

        # Pre-procesar texto con spaCy (compartir entre extractores)
        doc = self.nlp(text)

        # Crear contexto
        context = ExtractionContext(
            text=text,
            entity_names=entity_names,
            entity_mentions=entity_mentions,
            chapter=chapter,
            doc=doc,
        )

        # Analizar complejidad
        complexity = self.router.analyze(text)
        logger.debug(
            f"Complexity: {complexity.score:.2f}, "
            f"recommended: {[m.value for m in complexity.recommended_extractors]}"
        )

        # Seleccionar extractores
        selected_extractors = self._select_extractors(complexity)
        logger.info(f"Using extractors: {[e.method.value for e in selected_extractors]}")

        # Ejecutar extractores
        results = self._run_extractors(selected_extractors, context)

        # Agregar resultados
        aggregated = self.aggregator.aggregate(results)

        # Cache store
        if self.config.enable_cache:
            self._cache[cache_key] = aggregated

        logger.info(f"Extracted {len(aggregated)} attributes (aggregated)")
        return aggregated

    def _get_cache_key(self, text: str, entity_names: list[str]) -> str:
        """Genera clave de cache."""
        return f"{hash(text)}:{':'.join(sorted(entity_names))}"

    def _select_extractors(
        self,
        complexity: Any,
    ) -> list[BaseExtractor]:
        """
        Selecciona extractores basándose en complejidad.

        Siempre incluye regex y dependency como baseline.
        Embeddings y LLM solo para casos más complejos.
        """
        selected = []

        for extractor in self.extractors:
            # LLM solo para casos muy complejos
            if extractor.method == ExtractionMethod.SEMANTIC_LLM:
                if complexity.score >= self.config.complexity_threshold_for_llm:
                    selected.append(extractor)
            # Embeddings para casos medianos
            elif extractor.method == ExtractionMethod.EMBEDDINGS:
                if complexity.score >= 0.3:
                    selected.append(extractor)
            # Regex y Dependency siempre
            else:
                selected.append(extractor)

        return selected

    def _run_extractors(
        self,
        extractors: list[BaseExtractor],
        context: ExtractionContext,
    ) -> list:
        """
        Ejecuta extractores.

        Args:
            extractors: Lista de extractores a ejecutar
            context: Contexto de extracción

        Returns:
            Lista de ExtractionResult
        """
        if self.config.parallel_extraction and len(extractors) > 1:
            return self._run_parallel(extractors, context)
        else:
            return self._run_sequential(extractors, context)

    def _run_sequential(
        self,
        extractors: list[BaseExtractor],
        context: ExtractionContext,
    ) -> list:
        """Ejecución secuencial de extractores."""
        results = []

        for extractor in extractors:
            try:
                result = extractor.extract(context)
                results.append(result)
                logger.debug(
                    f"{extractor.method.value}: {len(result.attributes)} attributes extracted"
                )
            except Exception as e:
                logger.warning(f"Extractor {extractor.method.value} failed: {e}")

        return results

    def _run_parallel(
        self,
        extractors: list[BaseExtractor],
        context: ExtractionContext,
    ) -> list:
        """Ejecución paralela de extractores."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = []

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {executor.submit(e.extract, context): e for e in extractors}

            for future in as_completed(futures):
                extractor = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.debug(
                        f"{extractor.method.value}: {len(result.attributes)} attributes extracted"
                    )
                except Exception as e:
                    logger.warning(f"Extractor {extractor.method.value} failed: {e}")

        return results

    def clear_cache(self) -> None:
        """Limpia el cache de resultados."""
        self._cache.clear()


# =============================================================================
# Singleton
# =============================================================================

_pipeline_instance: AttributeExtractionPipeline | None = None
_pipeline_lock = None


def get_extraction_pipeline(
    config: PipelineConfig | None = None,
) -> AttributeExtractionPipeline:
    """
    Obtiene singleton del pipeline de extracción.

    Args:
        config: Configuración (solo se usa en primera llamada)

    Returns:
        Instancia del pipeline
    """
    global _pipeline_instance, _pipeline_lock

    if _pipeline_lock is None:
        import threading

        _pipeline_lock = threading.Lock()

    if _pipeline_instance is None:
        with _pipeline_lock:
            if _pipeline_instance is None:
                _pipeline_instance = AttributeExtractionPipeline(config=config)

    return _pipeline_instance


def reset_extraction_pipeline() -> None:
    """Resetea el singleton (útil para tests)."""
    global _pipeline_instance
    _pipeline_instance = None
