"""
LLM Integration module - Integración con modelos LLM locales para análisis semántico avanzado.

Este módulo proporciona capacidades de análisis que requieren comprensión
semántica profunda, como:
- Inferencia de expectativas comportamentales
- Análisis de motivaciones de personajes
- Detección de inconsistencias complejas
- Generación de sugerencias de corrección

IMPORTANTE: Este módulo funciona 100% OFFLINE una vez configurado.
Usa modelos locales a través de (en orden de prioridad):
1. llama.cpp - Servidor ligero (~50MB), más rápido (~150 tok/s)
2. Ollama - Servidor local con modelos como Llama, Mistral
3. Transformers - Modelos HuggingFace descargados localmente

Instalación bajo demanda:
- Los binarios y modelos se descargan cuando el usuario los selecciona
- Ver llamacpp_manager.py y ollama_manager.py para la gestión de instalación
"""

from .client import (
    # Cliente
    LocalLLMClient,
    LocalLLMConfig,
    download_ollama_model,
    ensure_llm_ready,
    # Alias deprecated
    get_claude_client,
    # Funciones - cliente
    get_llm_client,
    get_ollama_status,
    install_ollama_if_needed,
    is_llm_available,
    reset_client,
    # Funciones - instalación bajo demanda
    set_installation_prompt_callback,
)
from .expectation_inference import (
    # Tipos
    BehavioralExpectation,
    CharacterBehaviorProfile,
    # Clase principal
    ExpectationInferenceEngine,
    ExpectationType,
    ExpectationViolation,
    detect_expectation_violations,
    # Funciones de conveniencia
    infer_expectations,
)
from .llamacpp_manager import (
    # Constantes
    AVAILABLE_MODELS as LLAMACPP_MODELS,
    # Gestor principal
    LlamaCppManager,
    LlamaCppModelInfo,
    # Tipos
    LlamaCppStatus,
    # Funciones singleton
    get_llamacpp_manager,
)
from .ollama_manager import (
    # Constantes
    AVAILABLE_MODELS,
    DownloadProgress,
    InstallationPlatform,
    OllamaConfig,
    # Gestor principal
    OllamaManager,
    OllamaModel,
    # Tipos
    OllamaStatus,
    download_llm_model,
    ensure_ollama_ready,
    get_available_llm_models,
    # Funciones singleton
    get_ollama_manager,
    # Funciones de conveniencia
    is_ollama_available,
    reset_ollama_manager,
)

__all__ = [
    # Tipos - Expectation
    "BehavioralExpectation",
    "ExpectationType",
    "ExpectationViolation",
    "CharacterBehaviorProfile",
    # Clase principal - Expectation
    "ExpectationInferenceEngine",
    # Funciones - Expectation
    "infer_expectations",
    "detect_expectation_violations",
    # Cliente LLM
    "LocalLLMClient",
    "LocalLLMConfig",
    # Funciones - Client
    "get_llm_client",
    "is_llm_available",
    "reset_client",
    # Funciones - Instalación bajo demanda
    "set_installation_prompt_callback",
    "get_ollama_status",
    "install_ollama_if_needed",
    "download_ollama_model",
    "ensure_llm_ready",
    # Gestor llama.cpp (ligero, rápido)
    "LlamaCppManager",
    "LlamaCppStatus",
    "LlamaCppModelInfo",
    "LLAMACPP_MODELS",
    "get_llamacpp_manager",
    # Gestor Ollama
    "OllamaManager",
    "OllamaConfig",
    "OllamaStatus",
    "OllamaModel",
    "DownloadProgress",
    "InstallationPlatform",
    "AVAILABLE_MODELS",
    "get_ollama_manager",
    "reset_ollama_manager",
    "is_ollama_available",
    "ensure_ollama_ready",
    "get_available_llm_models",
    "download_llm_model",
    # Deprecated
    "get_claude_client",
]
