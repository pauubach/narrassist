"""
Cliente para LLM local.

Este módulo proporciona un cliente thread-safe para interactuar con modelos
LLM locales. Soporta:
1. Ollama (servidor local con modelos como Llama, Mistral, etc.)
2. Transformers (modelos HuggingFace descargados localmente)

IMPORTANTE: Este módulo funciona 100% offline. No requiere acceso a internet.
"""

import json
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional

logger = logging.getLogger(__name__)

# Lock para thread-safety
_client_lock = threading.Lock()
_client: Optional["LocalLLMClient"] = None

LLMBackend = Literal["ollama", "transformers", "none"]


@dataclass
class LocalLLMConfig:
    """Configuración del cliente LLM local."""

    # Backend a usar: ollama, transformers, none
    backend: LLMBackend = "ollama"

    # Ollama config
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"  # Modelo por defecto (3B params, funciona en CPU)

    # Transformers config (modelos locales)
    transformers_model_path: Optional[Path] = None
    transformers_model_name: str = "meta-llama/Llama-3.2-3B-Instruct"

    # Parámetros de generación
    max_tokens: int = 2048
    temperature: float = 0.3  # Bajo para análisis consistente
    timeout: int = 120  # Segundos (modelos locales son más lentos)


class LocalLLMClient:
    """
    Cliente para interactuar con LLM local.

    Características:
    - 100% Offline - No requiere internet
    - Thread-safe
    - Soporte para Ollama y Transformers
    - Caché de resultados (opcional)
    """

    def __init__(self, config: LocalLLMConfig):
        """
        Inicializa el cliente.

        Args:
            config: Configuración del cliente
        """
        self._config = config
        self._backend: LLMBackend = "none"
        self._ollama_client: Any = None
        self._transformers_pipeline: Any = None
        self._lock = threading.Lock()
        self._initialize_backend()

    def _initialize_backend(self) -> None:
        """Inicializa el backend de LLM."""
        # Intentar Ollama primero
        if self._config.backend in ("ollama", "auto"):
            if self._try_init_ollama():
                return

        # Fallback a Transformers
        if self._config.backend in ("transformers", "auto"):
            if self._try_init_transformers():
                return

        logger.warning(
            "No se pudo inicializar ningún backend LLM. "
            "Instala Ollama o configura un modelo de Transformers local."
        )
        self._backend = "none"

    def _try_init_ollama(self) -> bool:
        """Intenta inicializar Ollama."""
        try:
            import httpx

            # Verificar que Ollama está corriendo
            response = httpx.get(
                f"{self._config.ollama_host}/api/tags",
                timeout=5.0
            )

            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]

                # Verificar que el modelo está disponible
                model_available = any(
                    self._config.ollama_model in m for m in models
                )

                if model_available:
                    self._backend = "ollama"
                    logger.info(
                        f"Ollama inicializado con modelo: {self._config.ollama_model}"
                    )
                    return True
                else:
                    logger.warning(
                        f"Modelo {self._config.ollama_model} no encontrado en Ollama. "
                        f"Modelos disponibles: {models}"
                    )
                    # Intentar con el primer modelo disponible
                    if models:
                        self._config.ollama_model = models[0].split(":")[0]
                        self._backend = "ollama"
                        logger.info(f"Usando modelo alternativo: {self._config.ollama_model}")
                        return True

        except ImportError:
            logger.debug("httpx no instalado, no se puede usar Ollama")
        except Exception as e:
            logger.debug(f"Ollama no disponible: {e}")

        return False

    def _try_init_transformers(self) -> bool:
        """Intenta inicializar Transformers con modelo local."""
        try:
            from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
            import torch

            model_path = self._config.transformers_model_path
            if model_path is None:
                # Buscar en directorio de modelos del proyecto
                from narrative_assistant.core.config import get_config
                config = get_config()
                if config.models_dir:
                    model_path = config.models_dir / "llm" / self._config.transformers_model_name.replace("/", "_")

            if model_path and model_path.exists():
                logger.info(f"Cargando modelo local desde: {model_path}")

                # Detectar dispositivo
                if torch.cuda.is_available():
                    device = "cuda"
                elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    device = "mps"
                else:
                    device = "cpu"

                self._transformers_pipeline = pipeline(
                    "text-generation",
                    model=str(model_path),
                    device=device,
                    torch_dtype=torch.float16 if device != "cpu" else torch.float32,
                )
                self._backend = "transformers"
                logger.info(f"Transformers inicializado en {device}")
                return True
            else:
                logger.debug(f"Modelo no encontrado en: {model_path}")

        except ImportError:
            logger.debug("transformers no instalado")
        except Exception as e:
            logger.debug(f"Error inicializando Transformers: {e}")

        return False

    @property
    def is_available(self) -> bool:
        """Verifica si el cliente está disponible."""
        return self._backend != "none"

    @property
    def backend_name(self) -> str:
        """Nombre del backend en uso."""
        return self._backend

    @property
    def model_name(self) -> str:
        """Nombre del modelo en uso."""
        if self._backend == "ollama":
            return self._config.ollama_model
        elif self._backend == "transformers":
            return self._config.transformers_model_name
        return "none"

    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Optional[str]:
        """
        Genera una respuesta usando el LLM local.

        Args:
            prompt: El prompt del usuario
            system: Mensaje de sistema opcional
            max_tokens: Override de max_tokens
            temperature: Override de temperature

        Returns:
            Respuesta generada o None si hay error
        """
        if not self.is_available:
            logger.warning("LLM local no disponible")
            return None

        with self._lock:
            if self._backend == "ollama":
                return self._complete_ollama(prompt, system, max_tokens, temperature)
            elif self._backend == "transformers":
                return self._complete_transformers(prompt, system, max_tokens, temperature)

        return None

    def _complete_ollama(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Optional[str]:
        """Genera respuesta usando Ollama."""
        try:
            import httpx

            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = httpx.post(
                f"{self._config.ollama_host}/api/chat",
                json={
                    "model": self._config.ollama_model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens or self._config.max_tokens,
                        "temperature": temperature or self._config.temperature,
                    }
                },
                timeout=self._config.timeout,
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("message", {}).get("content", "")

            logger.error(f"Error de Ollama: {response.status_code} - {response.text}")
            return None

        except Exception as e:
            logger.error(f"Error en llamada a Ollama: {e}")
            return None

    def _complete_transformers(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Optional[str]:
        """Genera respuesta usando Transformers."""
        try:
            # Construir prompt con sistema si existe
            full_prompt = ""
            if system:
                full_prompt = f"<|system|>\n{system}\n<|user|>\n{prompt}\n<|assistant|>\n"
            else:
                full_prompt = f"<|user|>\n{prompt}\n<|assistant|>\n"

            result = self._transformers_pipeline(
                full_prompt,
                max_new_tokens=max_tokens or self._config.max_tokens,
                temperature=temperature or self._config.temperature,
                do_sample=True,
                pad_token_id=self._transformers_pipeline.tokenizer.eos_token_id,
            )

            generated_text = result[0]["generated_text"]
            # Extraer solo la respuesta del asistente
            if "<|assistant|>" in generated_text:
                response = generated_text.split("<|assistant|>")[-1].strip()
                return response

            return generated_text[len(full_prompt):].strip()

        except Exception as e:
            logger.error(f"Error en Transformers: {e}")
            return None

    def analyze_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        schema_hint: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Genera una respuesta estructurada en JSON.

        Args:
            prompt: El prompt del usuario
            system: Mensaje de sistema opcional
            schema_hint: Descripción del esquema JSON esperado

        Returns:
            Diccionario parseado o None si hay error
        """
        json_system = (
            system or ""
        ) + "\n\nResponde SIEMPRE en formato JSON válido. Sin markdown, sin explicaciones adicionales, solo el JSON."

        if schema_hint:
            json_system += f"\n\nEsquema esperado: {schema_hint}"

        response = self.complete(prompt, system=json_system)

        if not response:
            return None

        try:
            # Limpiar respuesta si viene con markdown
            cleaned = response.strip()
            if cleaned.startswith("```"):
                # Remover bloques de código
                lines = cleaned.split("\n")
                lines = [l for l in lines if not l.startswith("```")]
                cleaned = "\n".join(lines)

            # Encontrar el JSON en la respuesta
            start_idx = cleaned.find("{")
            end_idx = cleaned.rfind("}") + 1

            if start_idx != -1 and end_idx > start_idx:
                cleaned = cleaned[start_idx:end_idx]

            return json.loads(cleaned)

        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON: {e}")
            logger.debug(f"Respuesta recibida: {response[:500]}")
            return None


def _load_config() -> LocalLLMConfig:
    """
    Carga la configuración del LLM local.

    Lee de variables de entorno:
    - NA_LLM_BACKEND: ollama, transformers, auto
    - NA_OLLAMA_HOST: URL del servidor Ollama
    - NA_OLLAMA_MODEL: Modelo de Ollama a usar
    - NA_LLM_MODEL_PATH: Ruta al modelo local de Transformers
    """
    backend = os.getenv("NA_LLM_BACKEND", "ollama")
    if backend not in ("ollama", "transformers", "auto", "none"):
        backend = "ollama"

    config = LocalLLMConfig(
        backend=backend,  # type: ignore
        ollama_host=os.getenv("NA_OLLAMA_HOST", "http://localhost:11434"),
        ollama_model=os.getenv("NA_OLLAMA_MODEL", "llama3.2"),
    )

    if model_path := os.getenv("NA_LLM_MODEL_PATH"):
        config.transformers_model_path = Path(model_path)

    return config


def get_llm_client() -> Optional[LocalLLMClient]:
    """
    Obtiene el cliente LLM singleton (thread-safe).

    Returns:
        Cliente LLM o None si no hay backend disponible
    """
    global _client

    if _client is None:
        with _client_lock:
            # Double-checked locking
            if _client is None:
                config = _load_config()
                if config.backend != "none":
                    _client = LocalLLMClient(config)
                else:
                    logger.info(
                        "LLM deshabilitado. Configure NA_LLM_BACKEND para habilitar."
                    )

    return _client


def is_llm_available() -> bool:
    """Verifica si las funcionalidades LLM están disponibles."""
    client = get_llm_client()
    return client is not None and client.is_available


def reset_client() -> None:
    """Resetea el cliente singleton (para testing)."""
    global _client
    with _client_lock:
        _client = None


# Alias para compatibilidad
get_claude_client = get_llm_client  # Deprecated, usar get_llm_client
