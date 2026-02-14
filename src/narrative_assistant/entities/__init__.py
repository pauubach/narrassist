"""
Entities module - Gestión de entidades narrativas.

Componentes:
- models: Modelos de datos para entidades y menciones
- repository: Acceso a datos de entidades en SQLite
- fusion: Servicio de fusión manual de entidades
"""

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
try:
    from .semantic_fusion import (
        SemanticFusionResult,
        SemanticFusionService,
        get_semantic_fusion_service,
        reset_semantic_fusion_service,
        update_fusion_threshold,
    )
except ImportError:
    SemanticFusionService = None  # type: ignore[misc, assignment]
    SemanticFusionResult = None  # type: ignore[misc, assignment]
    get_semantic_fusion_service = None  # type: ignore[assignment]
    reset_semantic_fusion_service = None  # type: ignore[assignment]
    update_fusion_threshold = None  # type: ignore[assignment]

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
