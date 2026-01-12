# -*- coding: utf-8 -*-
"""
Fusión semántica de entidades usando embeddings y (opcionalmente) LLMs.

Este módulo complementa fusion.py con capacidades de IA para:
1. Calcular similaridad semántica usando embeddings
2. Resolver correferencia nominal compleja ("El parque" → "Parque del Retiro")
3. (Futuro) Integración con Claude API para casos complejos

NOTA: La integración con LLM está preparada pero no implementada en MVP.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from ..core.result import Result
from ..core.errors import NarrativeError, ErrorSeverity
from ..nlp.embeddings import get_embeddings_model
from .models import Entity, EntityType

logger = logging.getLogger(__name__)

# Umbral de similaridad semántica para sugerir fusión
SEMANTIC_SIMILARITY_THRESHOLD = 0.65

# Contextos que indican referencia anafórica
ANAPHORIC_MARKERS = [
    "el ", "la ", "los ", "las ",  # Artículos definidos
    "ese ", "esa ", "esos ", "esas ",  # Demostrativos
    "aquel ", "aquella ", "dicho ", "dicha ",  # Referencias
    "mismo ", "misma ",  # Identidad
]


@dataclass
class SemanticFusionResult:
    """Resultado de análisis de fusión semántica."""
    should_merge: bool
    similarity: float
    reason: str
    confidence: float
    method: str  # "embeddings", "dictionary", "llm"


class SemanticFusionService:
    """
    Servicio de fusión basado en similaridad semántica.

    Usa embeddings de sentence-transformers para calcular
    similaridad entre entidades más allá de coincidencia textual.

    Ejemplo:
        >>> service = SemanticFusionService()
        >>> result = service.should_merge(entity1, entity2, context="narrativa aquí...")
        >>> if result.should_merge:
        ...     print(f"Fusionar con confianza {result.confidence}")
    """

    def __init__(
        self,
        similarity_threshold: float = SEMANTIC_SIMILARITY_THRESHOLD,
        use_llm: bool = False,  # Preparado para futuro
    ):
        """
        Inicializa el servicio.

        Args:
            similarity_threshold: Umbral mínimo de similaridad semántica
            use_llm: Si True, usa LLM para casos complejos (no implementado)
        """
        self.similarity_threshold = similarity_threshold
        self.use_llm = use_llm
        self._embeddings = None

    @property
    def embeddings(self):
        """Lazy loading del modelo de embeddings."""
        if self._embeddings is None:
            self._embeddings = get_embeddings_model()
        return self._embeddings

    def compute_semantic_similarity(
        self,
        entity1: Entity,
        entity2: Entity,
    ) -> float:
        """
        Calcula similaridad semántica entre dos entidades usando embeddings.

        Args:
            entity1: Primera entidad
            entity2: Segunda entidad

        Returns:
            Similaridad entre 0.0 y 1.0
        """
        try:
            # Combinar nombre canónico y aliases
            text1 = entity1.canonical_name
            text2 = entity2.canonical_name

            # Añadir contexto de tipo
            type_prefix1 = self._get_type_context(entity1.entity_type)
            type_prefix2 = self._get_type_context(entity2.entity_type)

            full_text1 = f"{type_prefix1} {text1}"
            full_text2 = f"{type_prefix2} {text2}"

            similarity = self.embeddings.similarity(full_text1, full_text2)

            logger.debug(
                f"Semantic similarity: '{text1}' vs '{text2}' = {similarity:.3f}"
            )

            return float(similarity)

        except Exception as e:
            logger.warning(f"Error computing semantic similarity: {e}")
            return 0.0

    def _get_type_context(self, entity_type: EntityType) -> str:
        """Genera contexto textual para el tipo de entidad."""
        type_contexts = {
            EntityType.CHARACTER: "persona llamada",
            EntityType.LOCATION: "lugar llamado",
            EntityType.ORGANIZATION: "organización llamada",
            EntityType.OBJECT: "objeto llamado",
            EntityType.EVENT: "evento llamado",
            EntityType.CREATURE: "criatura llamada",
            EntityType.BUILDING: "edificio llamado",
            EntityType.REGION: "región llamada",
            EntityType.FACTION: "facción llamada",
            EntityType.FAMILY: "familia llamada",
            EntityType.CONCEPT: "concepto de",
        }
        return type_contexts.get(entity_type, "")

    def should_merge(
        self,
        entity1: Entity,
        entity2: Entity,
        narrative_context: Optional[str] = None,
    ) -> SemanticFusionResult:
        """
        Determina si dos entidades deberían fusionarse.

        Combina múltiples señales:
        1. Similaridad semántica (embeddings)
        2. Marcadores anafóricos ("El parque" sugiere referencia)
        3. Contexto narrativo (si se proporciona)

        Args:
            entity1: Primera entidad
            entity2: Segunda entidad
            narrative_context: Contexto narrativo opcional

        Returns:
            SemanticFusionResult con decisión y confianza
        """
        # 1. Calcular similaridad semántica base
        similarity = self.compute_semantic_similarity(entity1, entity2)

        # 2. Detectar marcadores anafóricos
        has_anaphoric = self._has_anaphoric_marker(entity1, entity2)

        # Boost si hay marcador anafórico y el tipo coincide
        if has_anaphoric and entity1.entity_type == entity2.entity_type:
            similarity = min(1.0, similarity * 1.2)

        # 3. Determinar si fusionar
        should_merge = similarity >= self.similarity_threshold

        # 4. Calcular confianza
        confidence = similarity
        if has_anaphoric:
            confidence = min(1.0, confidence + 0.1)

        # 5. Generar razón
        if should_merge:
            reason = f"Similaridad semántica alta ({similarity:.2f})"
            if has_anaphoric:
                reason += " con marcador anafórico"
        else:
            reason = f"Similaridad semántica baja ({similarity:.2f})"

        return SemanticFusionResult(
            should_merge=should_merge,
            similarity=similarity,
            reason=reason,
            confidence=confidence,
            method="embeddings",
        )

    def _has_anaphoric_marker(
        self,
        entity1: Entity,
        entity2: Entity,
    ) -> bool:
        """
        Detecta si alguna entidad tiene un marcador anafórico.

        Marcadores anafóricos (ej: "El parque", "Ese hombre") sugieren
        que la entidad es una referencia a otra mencionada previamente.
        """
        name1 = entity1.canonical_name.lower()
        name2 = entity2.canonical_name.lower()

        for marker in ANAPHORIC_MARKERS:
            if name1.startswith(marker) or name2.startswith(marker):
                return True

        return False

    def resolve_nominal_coreference(
        self,
        anaphoric_entity: Entity,
        candidates: list[Entity],
        narrative_context: Optional[str] = None,
    ) -> Optional[Entity]:
        """
        Resuelve a qué entidad se refiere una mención anafórica.

        Por ejemplo: "El parque" → busca el parque más probable

        Args:
            anaphoric_entity: Entidad con mención anafórica
            candidates: Candidatos posibles
            narrative_context: Contexto para desambiguación

        Returns:
            Entity más probable o None si no hay coincidencia clara
        """
        if not candidates:
            return None

        best_match = None
        best_similarity = 0.0

        for candidate in candidates:
            if candidate.id == anaphoric_entity.id:
                continue

            result = self.should_merge(anaphoric_entity, candidate, narrative_context)

            if result.similarity > best_similarity:
                best_similarity = result.similarity
                best_match = candidate

        # Solo retornar si la confianza es suficiente
        if best_similarity >= self.similarity_threshold:
            logger.info(
                f"Resolved '{anaphoric_entity.canonical_name}' -> "
                f"'{best_match.canonical_name}' (similarity: {best_similarity:.2f})"
            )
            return best_match

        return None


# =============================================================================
# LLM Integration Placeholder (Post-MVP)
# =============================================================================

async def resolve_coreference_with_local_llm(
    text: str,
    mention: str,
    candidates: list[str],
    model_path: Optional[str] = None,
) -> Optional[str]:
    """
    Resuelve correferencia usando un LLM LOCAL.

    IMPORTANTE: Para mantener la privacidad de los manuscritos,
    SOLO se usan modelos ejecutados localmente. Opciones:
    - Ollama (Llama 3, Mistral, Phi-2, etc.)
    - llama.cpp con modelos GGUF
    - Modelos pequeños de HuggingFace en local

    NOTA: No implementado en MVP. Preparado para integración futura.

    Args:
        text: Contexto narrativo
        mention: Mención a resolver ("el parque")
        candidates: Nombres de candidatos posibles
        model_path: Ruta al modelo local (opcional)

    Returns:
        Nombre del candidato más probable o None

    TODO Post-MVP:
        - Integrar con Ollama (más fácil de instalar)
        - O usar llama-cpp-python para modelos GGUF
        - Añadir caching para reducir latencia
        - Probar con Phi-2 o Mistral-7B-Instruct

    Ejemplo de prompt para el LLM:
        "En el siguiente texto narrativo, la mención '{mention}'
        probablemente se refiere a: {candidates}. ¿Cuál es más probable?
        Texto: {text[:500]}..."
    """
    logger.warning(
        "Local LLM coreference resolution not implemented. "
        "This feature is planned for post-MVP. "
        "Consider using Ollama with Phi-2 or Mistral for local inference."
    )
    return None


# =============================================================================
# Singleton
# =============================================================================

_semantic_fusion_service: Optional[SemanticFusionService] = None


def get_semantic_fusion_service(
    similarity_threshold: float = SEMANTIC_SIMILARITY_THRESHOLD,
) -> SemanticFusionService:
    """
    Obtiene singleton del servicio de fusión semántica.

    Args:
        similarity_threshold: Umbral de similaridad

    Returns:
        Instancia única de SemanticFusionService
    """
    global _semantic_fusion_service

    if _semantic_fusion_service is None:
        _semantic_fusion_service = SemanticFusionService(
            similarity_threshold=similarity_threshold,
        )

    return _semantic_fusion_service


def reset_semantic_fusion_service() -> None:
    """Resetea el singleton (útil para tests)."""
    global _semantic_fusion_service
    _semantic_fusion_service = None
