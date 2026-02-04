"""
Relationships module - Detección y análisis de relaciones entre entidades.

Componentes:
- models: Tipos de relación, dataclasses para relaciones
- detector: Detección automática de relaciones desde texto
- repository: Persistencia de relaciones en BD
- analyzer: Verificación de coherencia relacional
"""

from .analyzer import (
    InteractionCoherenceChecker,
    RelationshipAnalyzer,
)
from .detector import (
    DetectedRelation,
    RelationDetectionConfig,
    RelationDetectionMethod,
    RelationDetectionResult,
    # Basic detector
    RelationshipDetector,
    # Voting system
    VotingRelationshipDetector,
    detect_relationships_from_text,
    detect_relationships_voting,
    get_voting_relationship_detector,
    reset_voting_detector,
)
from .inference import (
    ExpectationInferenceEngine,
    get_expectation_inference_engine,
)
from .models import (
    CoherenceAlert,
    EntityContext,
    EntityRelationship,
    InferredExpectations,
    RelationCategory,
    RelationshipChange,
    RelationshipEvidence,
    # Dataclasses
    RelationshipType,
    # Enums
    RelationType,
    RelationValence,
    TextReference,
)
from .repository import (
    RelationshipRepository,
)

__all__ = [
    # Enums
    "RelationType",
    "RelationCategory",
    "RelationValence",
    # Dataclasses
    "RelationshipType",
    "EntityRelationship",
    "RelationshipChange",
    "RelationshipEvidence",
    "TextReference",
    "InferredExpectations",
    "EntityContext",
    "CoherenceAlert",
    # Basic Detector
    "RelationshipDetector",
    "DetectedRelation",
    "detect_relationships_from_text",
    # Voting Detector (recommended)
    "VotingRelationshipDetector",
    "RelationDetectionConfig",
    "RelationDetectionMethod",
    "RelationDetectionResult",
    "detect_relationships_voting",
    "get_voting_relationship_detector",
    "reset_voting_detector",
    # Repository
    "RelationshipRepository",
    # Analyzer
    "RelationshipAnalyzer",
    "InteractionCoherenceChecker",
    # Inference
    "ExpectationInferenceEngine",
    "get_expectation_inference_engine",
]
