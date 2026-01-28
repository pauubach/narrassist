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

# Modules below depend on NLP libraries (numpy, spacy, sentence-transformers).
# They are NOT available in embedded Python (production) until the user
# installs the full NLP stack. Gracefully degrade if missing.
try:
    from .relationship_clustering import (
        RelationStrength,
        RelationValence,
        CoOccurrence,
        InferredRelation,
        CharacterCluster,
        KnowledgeAsymmetry,
        RelationshipClusteringEngine,
        extract_cooccurrences_from_chapters,
    )
except ImportError:
    pass

try:
    from .character_knowledge import (
        MentionType,
        KnowledgeType,
        OpinionValence,
        IntentionType,
        DirectedMention,
        KnowledgeFact,
        Opinion,
        Intention,
        KnowledgeAsymmetryReport,
        CharacterKnowledgeAnalyzer,
    )
except ImportError:
    pass

try:
    from .emotional_coherence import (
        IncoherenceType,
        EmotionalIncoherence,
        EmotionalCoherenceChecker,
        get_emotional_coherence_checker,
        reset_emotional_coherence_checker,
    )
except ImportError:
    pass

try:
    from .vital_status import (
        VitalStatus,
        DeathEvent,
        PostMortemAppearance,
        VitalStatusReport,
        VitalStatusAnalyzer,
        analyze_vital_status,
    )
except ImportError:
    pass

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
