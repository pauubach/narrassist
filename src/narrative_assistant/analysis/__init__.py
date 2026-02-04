"""
Analysis module - Detección de inconsistencias narrativas.

Componentes:
- attribute_consistency: Verificación de consistencia de atributos
  con lematización, sinónimos y antónimos.
- relationship_clustering: Análisis de relaciones entre personajes
  usando múltiples técnicas con votación (co-ocurrencia, dendrogramas,
  community detection, embeddings).
"""

# attribute_consistency uses only stdlib + internal modules
import contextlib

from .attribute_consistency import (
    # Clase principal
    AttributeConsistencyChecker,
    # Tipos principales
    AttributeInconsistency,
    InconsistencyType,
    check_attribute_consistency,
    # Funciones de conveniencia
    get_consistency_checker,
    reset_consistency_checker,
    # Utilidades (para tests)
    reset_lemma_cache,
)

# Modules below depend on NLP libraries (numpy, spacy, sentence-transformers).
# They are NOT available in embedded Python (production) until the user
# installs the full NLP stack. Gracefully degrade if missing.
with contextlib.suppress(ImportError):
    from .relationship_clustering import (
        CharacterCluster,
        CoOccurrence,
        InferredRelation,
        KnowledgeAsymmetry,
        RelationshipClusteringEngine,
        RelationStrength,
        RelationValence,
        extract_cooccurrences_from_chapters,
    )

with contextlib.suppress(ImportError):
    from .character_knowledge import (
        CharacterKnowledgeAnalyzer,
        DirectedMention,
        Intention,
        IntentionType,
        KnowledgeAsymmetryReport,
        KnowledgeFact,
        KnowledgeType,
        MentionType,
        Opinion,
        OpinionValence,
    )

with contextlib.suppress(ImportError):
    from .emotional_coherence import (
        EmotionalCoherenceChecker,
        EmotionalIncoherence,
        IncoherenceType,
        get_emotional_coherence_checker,
        reset_emotional_coherence_checker,
    )

with contextlib.suppress(ImportError):
    from .vital_status import (
        DeathEvent,
        PostMortemAppearance,
        VitalStatus,
        VitalStatusAnalyzer,
        VitalStatusReport,
        analyze_vital_status,
    )

with contextlib.suppress(ImportError):
    from .semantic_redundancy import (
        DuplicateType,
        RedundancyMode,
        RedundancyReport,
        SemanticDuplicate,
        SemanticRedundancyDetector,
        get_semantic_redundancy_detector,
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
    # Tipos - Semantic Redundancy
    "DuplicateType",
    "RedundancyMode",
    # Dataclasses - Semantic Redundancy
    "SemanticDuplicate",
    "RedundancyReport",
    # Clase - Semantic Redundancy
    "SemanticRedundancyDetector",
    # Funciones - Semantic Redundancy
    "get_semantic_redundancy_detector",
]
