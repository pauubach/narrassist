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
- extraction: Pipeline unificado de extracción de atributos (recomendado)
- orthography: Corrección ortográfica
- grammar: Corrección gramatical
- sentiment: Análisis de sentimiento y emociones
- title_preprocessor: Preprocesamiento de títulos para spaCy
- spacy_title_integration: Integración de títulos con pipelines de análisis

NOTE: All imports are wrapped in try/except because NLP dependencies
(numpy, spacy, sentence-transformers, torch) may not be available in
embedded Python (production mode). The server starts in limited mode
and NLP features become available after the user installs dependencies.
"""

import logging as _logging

_logger = _logging.getLogger(__name__)

# All NLP submodules depend on heavy libraries. Wrap each in try/except
# so the package can be partially imported even without full NLP stack.

try:
    from .spacy_gpu import (
        get_spacy_gpu_status,
        load_spacy_model,
        reset_gpu_config,
        setup_spacy_gpu,
    )
except ImportError as _e:
    _logger.debug(f"spacy_gpu not available: {_e}")

try:
    from .embeddings import (
        EmbeddingsModel,
        encode_texts,
        get_embeddings_model,
        reset_embeddings_model,
    )
except ImportError as _e:
    _logger.debug(f"embeddings not available: {_e}")

try:
    from .chunking import (
        TextChunk,
        TextChunker,
        chunk_for_embeddings,
        chunk_for_spacy,
    )
except ImportError as _e:
    _logger.debug(f"chunking not available: {_e}")

try:
    from .ner import (
        EntityLabel,
        ExtractedEntity,
        NERExtractor,
        NERResult,
        extract_entities,
        get_ner_extractor,
        reset_ner_extractor,
    )
except ImportError as _e:
    _logger.debug(f"ner not available: {_e}")

try:
    from .dialogue import (
        DialogueResult,
        DialogueSpan,
        DialogueType,
        detect_dialogues,
        get_dialogue_density,
    )
except ImportError as _e:
    _logger.debug(f"dialogue not available: {_e}")

try:
    from .coref import (
        CoreferenceChain,
        CoreferenceResolver,
        CoreferenceResult,
        GrammaticalGender,
        GrammaticalNumber,
        Mention,
        MentionType,
        get_coref_resolver,
        reset_coref_resolver,
        resolve_coreferences,
    )
except ImportError as _e:
    _logger.debug(f"coref not available: {_e}")

try:
    from .attributes import (
        AttributeCategory,
        AttributeExtractionResult,
        AttributeExtractor,
        AttributeKey,
        ExtractedAttribute,
        extract_attributes,
        get_attribute_extractor,
        reset_attribute_extractor,
    )
except ImportError as _e:
    _logger.debug(f"attributes not available: {_e}")

# Unified extraction pipeline (recommended for new code)
try:
    from .extraction import (
        AttributeExtractionPipeline,
        PipelineConfig,
        get_extraction_pipeline,
        reset_extraction_pipeline,
    )
except ImportError as _e:
    _logger.debug(f"extraction not available: {_e}")

try:
    from .orthography import (
        SpellingChecker,
        SpellingErrorType,
        SpellingIssue,
        SpellingReport,
        SpellingSeverity,
        get_spelling_checker,
        reset_spelling_checker,
    )
except ImportError as _e:
    _logger.debug(f"orthography not available: {_e}")

try:
    from .grammar import (
        GrammarChecker,
        GrammarErrorType,
        GrammarIssue,
        GrammarReport,
        GrammarSeverity,
        get_grammar_checker,
        reset_grammar_checker,
    )
except ImportError as _e:
    _logger.debug(f"grammar not available: {_e}")

try:
    from .sentiment import (
        DeclaredEmotionalState,
        Emotion,
        EmotionalInconsistency,
        EmotionalState,
        Sentiment,
        SentimentAnalyzer,
        get_sentiment_analyzer,
    )
except ImportError as _e:
    _logger.debug(f"sentiment not available: {_e}")

try:
    from .title_preprocessor import (
        ProcessedDocument,
        ProcessedParagraph,
        TitleDetector,
        TitlePreprocessor,
        TitleType,
        is_title,
        preprocess_text_for_spacy,
        split_by_titles,
    )
except ImportError as _e:
    _logger.debug(f"title_preprocessor not available: {_e}")

try:
    from .spacy_title_integration import (
        TitleAwareAnalysisResult,
        TitleAwareDoc,
        analyze_paragraphs_separately,
        analyze_with_title_handling,
        debug_parsing,
        extract_dependencies_by_title,
        extract_entities_by_title,
        get_parsing_quality_metrics,
    )
except ImportError as _e:
    _logger.debug(f"spacy_title_integration not available: {_e}")

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
    # Attributes (legacy)
    "AttributeCategory",
    "AttributeKey",
    "ExtractedAttribute",
    "AttributeExtractionResult",
    "AttributeExtractor",
    "get_attribute_extractor",
    "reset_attribute_extractor",
    "extract_attributes",
    # Extraction Pipeline (recommended)
    "AttributeExtractionPipeline",
    "PipelineConfig",
    "get_extraction_pipeline",
    "reset_extraction_pipeline",
    # Orthography
    "SpellingIssue",
    "SpellingReport",
    "SpellingErrorType",
    "SpellingSeverity",
    "SpellingChecker",
    "get_spelling_checker",
    "reset_spelling_checker",
    # Grammar
    "GrammarIssue",
    "GrammarReport",
    "GrammarErrorType",
    "GrammarSeverity",
    "GrammarChecker",
    "get_grammar_checker",
    "reset_grammar_checker",
    # Sentiment
    "Sentiment",
    "Emotion",
    "EmotionalState",
    "DeclaredEmotionalState",
    "EmotionalInconsistency",
    "SentimentAnalyzer",
    "get_sentiment_analyzer",
    # Title Preprocessing
    "TitleType",
    "ProcessedParagraph",
    "ProcessedDocument",
    "TitleDetector",
    "TitlePreprocessor",
    "is_title",
    "preprocess_text_for_spacy",
    "split_by_titles",
    # Title Integration
    "TitleAwareDoc",
    "TitleAwareAnalysisResult",
    "analyze_with_title_handling",
    "analyze_paragraphs_separately",
    "extract_entities_by_title",
    "extract_dependencies_by_title",
    "get_parsing_quality_metrics",
    "debug_parsing",
]
