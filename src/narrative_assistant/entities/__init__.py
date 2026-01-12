"""
Entities module - Gestión de entidades narrativas.

Componentes:
- models: Modelos de datos para entidades y menciones
- repository: Acceso a datos de entidades en SQLite
- fusion: Servicio de fusión manual de entidades
"""

from .models import (
    EntityType,
    EntityImportance,
    Entity,
    EntityMention,
    MergeHistory,
    MergeSuggestion,
)
from .repository import (
    EntityRepository,
    get_entity_repository,
    reset_entity_repository,
)
from .fusion import (
    EntityFusionService,
    get_fusion_service,
    reset_fusion_service,
)

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
]
