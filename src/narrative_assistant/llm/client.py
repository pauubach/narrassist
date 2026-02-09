"""
Cliente para LLM local.

Este módulo proporciona un cliente thread-safe para interactuar con modelos
LLM locales. Soporta:
1. Ollama (servidor local con modelos como Llama, Mistral, etc.)
2. Transformers (modelos HuggingFace descargados localmente)

IMPORTANTE: Este módulo funciona 100% offline. No requiere acceso a internet
una vez que los modelos están descargados.

Instalación bajo demanda:
- Ollama se instala solo cuando el usuario intenta usar funcionalidades LLM
- Los modelos se descargan cuando el usuario los selecciona en Settings
"""

import json
import logging
import os
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional

logger = logging.getLogger(__name__)

# Lock para thread-safety
_client_lock = threading.Lock()
_client: Optional["LocalLLMClient"] = None

LLMBackend = Literal["ollama", "transformers", "none"]

# Callback para solicitar instalación de Ollama
_installation_prompt_callback: Callable[[], bool] | None = None


@dataclass
class LocalLLMConfig:
    """Configuración del cliente LLM local."""

    # Backend a usar: ollama, transformers, none
    backend: LLMBackend = "ollama"

    # Ollama config
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"  # Modelo por defecto (3B params, funciona en CPU)

    # Transformers config (modelos locales)
    transformers_model_path: Path | None = None
    transformers_model_name: str = "meta-llama/Llama-3.2-3B-Instruct"

    # Parámetros de generación
    max_tokens: int = 2048
    temperature: float = 0.3  # Bajo para análisis consistente
    timeout: int = 600  # 10 minutos - modelos locales en CPU son MUY lentos

    # Instalación bajo demanda
    auto_install_ollama: bool = False  # Si True, instala Ollama automáticamente
    auto_start_service: bool = True  # Si True, inicia el servicio automáticamente
    force_cpu: bool = False  # Si True, fuerza modo CPU para Ollama

    # S5-01: Preferencia de modelo para español
    prefer_spanish_model: bool = True  # Prefiere Qwen 2.5 para textos en español

    # S5-05: Cuantización
    quantization: str = "Q4_K_M"  # Q4_K_M (default), Q6_K (calidad), Q8_0 (máxima)


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
        self._warned_unavailable = False  # Para evitar warnings repetidos
        self._initialize_backend()

    def _initialize_backend(self) -> None:
        """Inicializa el backend de LLM."""
        # Intentar Ollama primero
        if self._config.backend in ("ollama", "auto") and self._try_init_ollama():
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
        """
        Intenta inicializar Ollama.

        Comportamiento bajo demanda:
        1. Verifica si Ollama está instalado
        2. Si no está instalado y hay callback de instalación, lo invoca
        3. Si está instalado pero no corriendo, intenta iniciarlo
        4. Verifica que el modelo esté disponible
        """
        from .ollama_manager import OllamaStatus, get_ollama_manager

        manager = get_ollama_manager()
        status = manager.status

        # Caso 1: Ollama no instalado
        if status == OllamaStatus.NOT_INSTALLED:
            if self._config.auto_install_ollama:
                logger.info("Instalando Ollama automáticamente...")
                success, msg = manager.install_ollama(silent=True)
                if not success:
                    logger.warning(f"No se pudo instalar Ollama: {msg}")
                    return False
            elif _installation_prompt_callback:
                # Preguntar al usuario si quiere instalar
                if _installation_prompt_callback():
                    success, msg = manager.install_ollama()
                    if not success:
                        logger.warning(f"No se pudo instalar Ollama: {msg}")
                        return False
                else:
                    logger.info("Usuario rechazó la instalación de Ollama")
                    return False
            else:
                logger.debug("Ollama no instalado, instalación bajo demanda deshabilitada")
                return False

        # Caso 2: Ollama instalado pero no corriendo
        if not manager.is_running:
            if self._config.auto_start_service:
                logger.info("Iniciando servicio Ollama...")
                success, msg = manager.start_service(force_cpu=self._config.force_cpu)
                if not success:
                    logger.warning(f"No se pudo iniciar Ollama: {msg}")
                    return False
            else:
                logger.debug("Ollama no está corriendo, inicio automático deshabilitado")
                return False

        # Caso 3: Ollama corriendo, verificar modelo
        return self._verify_ollama_model(manager)

    def _verify_ollama_model(self, manager: Any) -> bool:
        """Verifica que el modelo configurado esté disponible."""
        try:
            import httpx

            response = httpx.get(f"{self._config.ollama_host}/api/tags", timeout=5.0)

            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]

                # Verificar que el modelo está disponible
                model_available = any(self._config.ollama_model in m for m in models)

                if model_available:
                    self._backend = "ollama"
                    logger.info(f"Ollama inicializado con modelo: {self._config.ollama_model}")
                    return True
                else:
                    logger.warning(
                        f"Modelo {self._config.ollama_model} no encontrado en Ollama. "
                        f"Modelos disponibles: {models}"
                    )
                    # Seleccionar el mejor modelo disponible según el hardware
                    if models:
                        best_model = self._select_best_available_model(models)
                        self._config.ollama_model = best_model
                        self._backend = "ollama"
                        logger.info(
                            f"Usando modelo óptimo para tu hardware: {self._config.ollama_model}"
                        )
                        return True
                    else:
                        logger.warning("No hay modelos descargados en Ollama")
                        return False

        except ImportError:
            logger.debug("httpx no instalado, no se puede usar Ollama")
        except Exception as e:
            logger.debug(f"Ollama no disponible: {e}")

        return False

    def _select_best_available_model(self, available_models: list[str]) -> str:
        """
        Selecciona el mejor modelo disponible según hardware y preferencias.

        Estrategia de selección (S5-01 + S5-02):
        - Si prefer_spanish_model=True: Qwen 2.5 como primera opción
        - GPU con alta VRAM (>8GB): qwen2.5 > mistral > gemma2 > llama3.2
        - GPU con VRAM media (4-8GB): qwen2.5 > llama3.2 > mistral
        - CPU o poca VRAM: llama3.2 (3B es rápido en CPU)
        """
        # Detectar capacidades de hardware
        has_gpu = False
        has_high_vram = False
        vram_gb = 0.0

        try:
            from ..core.device import get_gpu_device

            gpu = get_gpu_device()
            if gpu:
                has_gpu = True
                vram_gb = gpu.total_memory_gb or 0.0
                if vram_gb > 8:
                    has_high_vram = True
        except Exception:
            pass

        # Normalizar nombres de modelos (quitar tags como :latest)
        normalized = [m.split(":")[0] for m in available_models]

        # S5-01: Preferir Qwen 2.5 para español si hay hardware suficiente
        prefer_qwen = self._config.prefer_spanish_model and (has_gpu or vram_gb >= 4)

        # S5-02: Definir orden de preferencia según hardware
        if has_high_vram:
            if prefer_qwen:
                preference_order = ["qwen2.5", "mistral", "gemma2", "llama3.2"]
            else:
                preference_order = ["mistral", "qwen2.5", "gemma2", "llama3.2"]
        elif has_gpu:
            if prefer_qwen:
                preference_order = ["qwen2.5", "llama3.2", "mistral"]
            else:
                preference_order = ["llama3.2", "qwen2.5", "mistral"]
        else:
            # CPU: llama3.2 (3B) es la mejor opción para velocidad
            preference_order = ["llama3.2", "phi3", "gemma2:2b", "qwen2.5"]

        # Buscar el primer modelo disponible según preferencia
        for preferred in preference_order:
            for model in normalized:
                if preferred in model:
                    idx = normalized.index(model)
                    selected = available_models[idx].split(":")[0]
                    logger.info(
                        f"Modelo seleccionado: {selected} "
                        f"(GPU: {has_gpu}, VRAM: {vram_gb:.1f}GB, "
                        f"prefer_spanish: {prefer_qwen})"
                    )
                    return selected

        # Si no hay coincidencia, usar el primero
        return available_models[0].split(":")[0]

    def _try_init_transformers(self) -> bool:
        """Intenta inicializar Transformers con modelo local."""
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

            model_path = self._config.transformers_model_path
            if model_path is None:
                # Buscar en directorio de modelos del proyecto
                from narrative_assistant.core.config import get_config

                config = get_config()
                if config.models_dir:
                    model_path = (
                        config.models_dir
                        / "llm"
                        / self._config.transformers_model_name.replace("/", "_")
                    )

            if model_path and model_path.exists():
                logger.info(f"Cargando modelo local desde: {model_path}")

                # Detectar dispositivo via DeviceDetector centralizado
                from narrative_assistant.core.device import get_torch_device_string

                device = get_torch_device_string()

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
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str | None:
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
            if not self._warned_unavailable:
                logger.warning("LLM local no disponible - los análisis con LLM se omitirán")
                self._warned_unavailable = True
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
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str | None:
        """Genera respuesta usando Ollama."""
        try:
            import httpx

            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            # Timeout alto para CPU sin GPU - puede tardar varios minutos
            timeout_config = httpx.Timeout(
                connect=10.0,  # 10s para conectar
                read=self._config.timeout,  # 10 min para leer respuesta
                write=30.0,  # 30s para enviar request
                pool=10.0,  # 10s para obtener conexión del pool
            )

            response = httpx.post(
                f"{self._config.ollama_host}/api/chat",
                json={
                    "model": self._config.ollama_model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens or self._config.max_tokens,
                        "temperature": temperature or self._config.temperature,
                    },
                },
                timeout=timeout_config,
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
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str | None:
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

            return generated_text[len(full_prompt) :].strip()

        except Exception as e:
            logger.error(f"Error en Transformers: {e}")
            return None

    def analyze_json(
        self,
        prompt: str,
        system: str | None = None,
        schema_hint: str | None = None,
    ) -> dict | None:
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
            (system or "")
            + "\n\nResponde SIEMPRE en formato JSON válido. Sin markdown, sin explicaciones adicionales, solo el JSON."
        )

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


def get_llm_client() -> LocalLLMClient | None:
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
                    logger.info("LLM deshabilitado. Configure NA_LLM_BACKEND para habilitar.")

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


def set_installation_prompt_callback(callback: Callable[[], bool] | None) -> None:
    """
    Establece un callback para solicitar instalación de Ollama al usuario.

    El callback debe retornar True si el usuario acepta la instalación,
    False si la rechaza.

    Args:
        callback: Función que retorna bool, o None para desactivar
    """
    global _installation_prompt_callback
    _installation_prompt_callback = callback


def get_ollama_status() -> dict[str, Any]:
    """
    Obtiene información del estado de Ollama.

    Returns:
        Diccionario con:
        - installed: bool
        - running: bool
        - version: str o None
        - models: lista de modelos descargados
        - available_models: lista de modelos disponibles para descargar
    """
    from .ollama_manager import get_ollama_manager

    manager = get_ollama_manager()

    return {
        "installed": manager.is_installed,
        "running": manager.is_running,
        "version": manager.get_version(),
        "models": manager.downloaded_models,
        "available_models": [
            {
                "name": m.name,
                "display_name": m.display_name,
                "size_gb": m.size_gb,
                "description": m.description,
                "is_downloaded": m.is_downloaded,
                "is_default": m.is_default,
            }
            for m in manager.available_models
        ],
    }


def install_ollama_if_needed(
    force: bool = False,
    progress_callback: Callable[[Any], None] | None = None,
) -> tuple[bool, str]:
    """
    Instala Ollama si no está instalado.

    Args:
        force: Si True, reinstala aunque ya esté instalado
        progress_callback: Callback para reportar progreso

    Returns:
        Tupla (éxito, mensaje)
    """
    from .ollama_manager import get_ollama_manager

    manager = get_ollama_manager()

    if manager.is_installed and not force:
        return True, "Ollama ya está instalado"

    return manager.install_ollama(progress_callback=progress_callback)


def download_ollama_model(
    model_name: str,
    progress_callback: Callable[[Any], None] | None = None,
) -> tuple[bool, str]:
    """
    Descarga un modelo de Ollama.

    Args:
        model_name: Nombre del modelo (llama3.2, qwen2.5, mistral, gemma2)
        progress_callback: Callback para reportar progreso

    Returns:
        Tupla (éxito, mensaje)
    """
    from .ollama_manager import get_ollama_manager

    manager = get_ollama_manager()

    # Asegurar que Ollama está corriendo
    if not manager.is_running:
        success, msg = manager.ensure_running()
        if not success:
            return False, f"No se puede descargar: {msg}"

    return manager.download_model(model_name, progress_callback)


def ensure_llm_ready(
    install_if_missing: bool = False,
    download_default_model: bool = False,
) -> tuple[bool, str]:
    """
    Asegura que el sistema LLM esté listo para usar.

    Esta función es el punto de entrada principal para verificar y preparar
    el sistema LLM antes de usarlo.

    Args:
        install_if_missing: Si True, instala Ollama si no está
        download_default_model: Si True, descarga el modelo por defecto si no hay ninguno

    Returns:
        Tupla (éxito, mensaje)
    """
    from .ollama_manager import get_ollama_manager

    manager = get_ollama_manager()

    # Verificar instalación
    if not manager.is_installed:
        if install_if_missing:
            success, msg = manager.install_ollama()
            if not success:
                return False, f"Error instalando Ollama: {msg}"
        else:
            return (
                False,
                "Ollama no está instalado. Usa install_ollama_if_needed() para instalarlo.",
            )

    # Verificar servicio
    if not manager.is_running:
        success, msg = manager.start_service()
        if not success:
            return False, f"Error iniciando servicio: {msg}"

    # Verificar modelos
    if not manager.downloaded_models:
        if download_default_model:
            success, msg = manager.download_model("llama3.2")
            if not success:
                return False, f"Error descargando modelo: {msg}"
        else:
            return (
                False,
                "No hay modelos descargados. Usa download_ollama_model() para descargar uno.",
            )

    return True, "Sistema LLM listo"
