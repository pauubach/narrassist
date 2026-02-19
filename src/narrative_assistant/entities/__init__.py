"""
Entities module - Gestión de entidades narrativas.

Componentes:
- models: Modelos de datos para entidades y menciones
- repository: Acceso a datos de entidades en SQLite
- fusion: Servicio de fusión manual de entidades
"""

from typing import Any

from .fusion import (
    EntityFusionService,
    get_fusion_service,
    reset_fusion_service,
    run_automatic_fusion,
)
from .models import (
    Entity,
    EntityImportance,
    EntityMention,
    EntityType,
    MergeHistory,
    MergeSuggestion,
)
from .repository import (
    EntityRepository,
    get_entity_repository,
    reset_entity_repository,
)

# Semantic fusion depends on NLP libraries (numpy, sentence-transformers).
# These are NOT available in embedded Python (production) until the user
# installs the full NLP stack. Gracefully degrade if missing.
SemanticFusionService: Any
SemanticFusionResult: Any
get_semantic_fusion_service: Any
reset_semantic_fusion_service: Any
update_fusion_threshold: Any

try:
    from .semantic_fusion import (
        SemanticFusionResult as _SemanticFusionResult,
        SemanticFusionService as _SemanticFusionService,
        get_semantic_fusion_service as _get_semantic_fusion_service,
        reset_semantic_fusion_service as _reset_semantic_fusion_service,
        update_fusion_threshold as _update_fusion_threshold,
    )

    SemanticFusionService = _SemanticFusionService
    SemanticFusionResult = _SemanticFusionResult
    get_semantic_fusion_service = _get_semantic_fusion_service
    reset_semantic_fusion_service = _reset_semantic_fusion_service
    update_fusion_threshold = _update_fusion_threshold
except ImportError:
    SemanticFusionService = None
    SemanticFusionResult = None
    get_semantic_fusion_service = None
    reset_semantic_fusion_service = None
    update_fusion_threshold = None

__all__ = [
    # Models
    "EntityType",
    "EntityImportance",
    "Entity",
    "EntityMention",
    "MergeHistory",
    "MergeSuggestion",
    # Repository
    "EntityRepository",
    "get_entity_repository",
    "reset_entity_repository",
    # Fusion
    "EntityFusionService",
    "get_fusion_service",
    "reset_fusion_service",
    "run_automatic_fusion",
    # Semantic Fusion
    "SemanticFusionService",
    "SemanticFusionResult",
    "get_semantic_fusion_service",
    "reset_semantic_fusion_service",
    "update_fusion_threshold",
]
