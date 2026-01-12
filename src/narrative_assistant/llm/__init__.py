"""
LLM Integration module - Integración con modelos LLM locales para análisis semántico avanzado.

Este módulo proporciona capacidades de análisis que requieren comprensión
semántica profunda, como:
- Inferencia de expectativas comportamentales
- Análisis de motivaciones de personajes
- Detección de inconsistencias complejas
- Generación de sugerencias de corrección

IMPORTANTE: Este módulo funciona 100% OFFLINE.
Usa modelos locales a través de:
1. Ollama (recomendado) - Servidor local con modelos como Llama, Mistral
2. Transformers - Modelos HuggingFace descargados localmente
"""

from .expectation_inference import (
    # Tipos
    BehavioralExpectation,
    ExpectationType,
    ExpectationViolation,
    CharacterBehaviorProfile,
    # Clase principal
    ExpectationInferenceEngine,
    # Funciones de conveniencia
    infer_expectations,
    detect_expectation_violations,
)

from .client import (
    # Cliente
    LocalLLMClient,
    LocalLLMConfig,
    # Funciones
    get_llm_client,
    is_llm_available,
    # Alias deprecated
    get_claude_client,
)

__all__ = [
    # Tipos
    "BehavioralExpectation",
    "ExpectationType",
    "ExpectationViolation",
    "CharacterBehaviorProfile",
    # Clase principal
    "ExpectationInferenceEngine",
    # Funciones - Expectation
    "infer_expectations",
    "detect_expectation_violations",
    # Cliente
    "LocalLLMClient",
    "LocalLLMConfig",
    # Funciones - Client
    "get_llm_client",
    "is_llm_available",
    # Deprecated
    "get_claude_client",
]
