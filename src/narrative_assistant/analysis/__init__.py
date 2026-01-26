"""
Analysis module - Detección de inconsistencias narrativas.

Componentes:
- attribute_consistency: Verificación de consistencia de atributos
  con lematización, sinónimos y antónimos.
- relationship_clustering: Análisis de relaciones entre personajes
  usando múltiples técnicas con votación (co-ocurrencia, dendrogramas,
  community detection, embeddings).
"""

from .attribute_consistency import (
    # Tipos principales
    AttributeInconsistency,
    InconsistencyType,
    # Clase principal
    AttributeConsistencyChecker,
    # Funciones de conveniencia
    get_consistency_checker,
    reset_consistency_checker,
    check_attribute_consistency,
    # Utilidades (para tests)
    reset_lemma_cache,
)

from .relationship_clustering import (
    # Tipos
    RelationStrength,
    RelationValence,
    CoOccurrence,
    InferredRelation,
    CharacterCluster,
    KnowledgeAsymmetry,
    # Clase principal
    RelationshipClusteringEngine,
    # Funciones de conveniencia
    extract_cooccurrences_from_chapters,
)

from .character_knowledge import (
    # Tipos
    MentionType,
    KnowledgeType,
    OpinionValence,
    IntentionType,
    # Dataclasses
    DirectedMention,
    KnowledgeFact,
    Opinion,
    Intention,
    KnowledgeAsymmetryReport,
    # Clase principal
    CharacterKnowledgeAnalyzer,
)

from .emotional_coherence import (
    # Tipos
    IncoherenceType,
    # Dataclasses
    EmotionalIncoherence,
    # Clase principal
    EmotionalCoherenceChecker,
    # Funciones de conveniencia
    get_emotional_coherence_checker,
    reset_emotional_coherence_checker,
)

from .vital_status import (
    # Tipos
    VitalStatus,
    # Dataclasses
    DeathEvent,
    PostMortemAppearance,
    VitalStatusReport,
    # Clase principal
    VitalStatusAnalyzer,
    # Funciones de conveniencia
    analyze_vital_status,
)

__all__ = [
    # Tipos - Consistency
    "AttributeInconsistency",
    "InconsistencyType",
    # Clase - Consistency
    "AttributeConsistencyChecker",
    # Funciones - Consistency
    "get_consistency_checker",
    "reset_consistency_checker",
    "check_attribute_consistency",
    "reset_lemma_cache",
    # Tipos - Relationships
    "RelationStrength",
    "RelationValence",
    "CoOccurrence",
    "InferredRelation",
    "CharacterCluster",
    "KnowledgeAsymmetry",
    # Clase - Relationships
    "RelationshipClusteringEngine",
    # Funciones - Relationships
    "extract_cooccurrences_from_chapters",
    # Tipos - Character Knowledge
    "MentionType",
    "KnowledgeType",
    "OpinionValence",
    "IntentionType",
    # Dataclasses - Character Knowledge
    "DirectedMention",
    "KnowledgeFact",
    "Opinion",
    "Intention",
    "KnowledgeAsymmetryReport",
    # Clase - Character Knowledge
    "CharacterKnowledgeAnalyzer",
    # Tipos - Emotional Coherence
    "IncoherenceType",
    # Dataclasses - Emotional Coherence
    "EmotionalIncoherence",
    # Clase - Emotional Coherence
    "EmotionalCoherenceChecker",
    # Funciones - Emotional Coherence
    "get_emotional_coherence_checker",
    "reset_emotional_coherence_checker",
    # Tipos - Vital Status
    "VitalStatus",
    # Dataclasses - Vital Status
    "DeathEvent",
    "PostMortemAppearance",
    "VitalStatusReport",
    # Clase - Vital Status
    "VitalStatusAnalyzer",
    # Funciones - Vital Status
    "analyze_vital_status",
]
