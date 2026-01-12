# -*- coding: utf-8 -*-
"""
Extractores individuales para el pipeline híbrido.

Cada extractor implementa BaseExtractor y se especializa en un método:
- RegexExtractor: Patrones regex de alta precisión
- DependencyExtractor: Análisis de dependencias con spaCy
- EmbeddingsExtractor: Clasificación semántica con sentence-transformers
- LLMExtractor: Refinamiento con LLM local (Ollama)
"""

from .regex_extractor import RegexExtractor
from .dependency_extractor import DependencyExtractor
from .embeddings_extractor import EmbeddingsExtractor

# LLMExtractor se importa condicionalmente (requiere ollama)
try:
    from .llm_extractor import LLMExtractor
    __all__ = [
        "RegexExtractor",
        "DependencyExtractor",
        "EmbeddingsExtractor",
        "LLMExtractor",
    ]
except ImportError:
    __all__ = [
        "RegexExtractor",
        "DependencyExtractor",
        "EmbeddingsExtractor",
    ]
