"""
NLP module - Procesamiento de lenguaje natural con soporte GPU.

Componentes:
- spacy_gpu: Configuración de spaCy con GPU
- embeddings: Embeddings semánticos con sentence-transformers
- ner: Extracción de entidades nombradas
- chunking: Segmentación de texto para procesamiento
- dialogue: Detección de diálogos
- coref: Resolución de correferencias
- attributes: Extracción de atributos de entidades
"""

from .spacy_gpu import (
    setup_spacy_gpu,
    load_spacy_model,
    get_spacy_gpu_status,
    reset_gpu_config,
)
from .embeddings import (
    EmbeddingsModel,
    get_embeddings_model,
    encode_texts,
    reset_embeddings_model,
)
from .chunking import (
    TextChunk,
    TextChunker,
    chunk_for_embeddings,
    chunk_for_spacy,
)
from .ner import (
    EntityLabel,
    ExtractedEntity,
    NERResult,
    NERExtractor,
    get_ner_extractor,
    reset_ner_extractor,
    extract_entities,
)
from .dialogue import (
    DialogueType,
    DialogueSpan,
    DialogueResult,
    detect_dialogues,
    get_dialogue_density,
)
from .coref import (
    MentionType,
    GrammaticalGender,
    GrammaticalNumber,
    Mention,
    CoreferenceChain,
    CoreferenceResult,
    CoreferenceResolver,
    get_coref_resolver,
    reset_coref_resolver,
    resolve_coreferences,
)
from .attributes import (
    AttributeCategory,
    AttributeKey,
    ExtractedAttribute,
    AttributeExtractionResult,
    AttributeExtractor,
    get_attribute_extractor,
    reset_attribute_extractor,
    extract_attributes,
)

__all__ = [
    # spaCy
    "setup_spacy_gpu",
    "load_spacy_model",
    "get_spacy_gpu_status",
    "reset_gpu_config",
    # Embeddings
    "EmbeddingsModel",
    "get_embeddings_model",
    "encode_texts",
    "reset_embeddings_model",
    # Chunking
    "TextChunk",
    "TextChunker",
    "chunk_for_embeddings",
    "chunk_for_spacy",
    # NER
    "EntityLabel",
    "ExtractedEntity",
    "NERResult",
    "NERExtractor",
    "get_ner_extractor",
    "reset_ner_extractor",
    "extract_entities",
    # Dialogue
    "DialogueType",
    "DialogueSpan",
    "DialogueResult",
    "detect_dialogues",
    "get_dialogue_density",
    # Coreference
    "MentionType",
    "GrammaticalGender",
    "GrammaticalNumber",
    "Mention",
    "CoreferenceChain",
    "CoreferenceResult",
    "CoreferenceResolver",
    "get_coref_resolver",
    "reset_coref_resolver",
    "resolve_coreferences",
    # Attributes
    "AttributeCategory",
    "AttributeKey",
    "ExtractedAttribute",
    "AttributeExtractionResult",
    "AttributeExtractor",
    "get_attribute_extractor",
    "reset_attribute_extractor",
    "extract_attributes",
]
