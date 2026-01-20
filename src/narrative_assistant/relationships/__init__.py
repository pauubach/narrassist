"""
Relationships module - Detección y análisis de relaciones entre entidades.

Componentes:
- models: Tipos de relación, dataclasses para relaciones
- detector: Detección automática de relaciones desde texto
- repository: Persistencia de relaciones en BD
- analyzer: Verificación de coherencia relacional
"""

from .models import (
    # Enums
    RelationType,
    RelationCategory,
    RelationValence,
    # Dataclasses
    RelationshipType,
    EntityRelationship,
    RelationshipChange,
    RelationshipEvidence,
    TextReference,
    InferredExpectations,
    EntityContext,
    CoherenceAlert,
)

from .detector import (
    # Basic detector
    RelationshipDetector,
    DetectedRelation,
    detect_relationships_from_text,
    # Voting system
    VotingRelationshipDetector,
    RelationDetectionConfig,
    RelationDetectionMethod,
    RelationDetectionResult,
    detect_relationships_voting,
    get_voting_relationship_detector,
    reset_voting_detector,
)

from .repository import (
    RelationshipRepository,
)

from .analyzer import (
    RelationshipAnalyzer,
    InteractionCoherenceChecker,
)

from .inference import (
    ExpectationInferenceEngine,
    get_expectation_inference_engine,
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
