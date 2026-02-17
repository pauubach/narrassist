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
import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional

logger = logging.getLogger(__name__)

# Lock para thread-safety
_client_lock = threading.Lock()
_client: Optional["LocalLLMClient"] = None

LLMBackend = Literal["ollama", "transformers", "none"]


# =============================================================================
# LLM Scheduler — prioriza chat interactivo sobre análisis batch
# =============================================================================

class LLMScheduler:
    """
    Coordina acceso al LLM entre análisis (batch) y chat (interactivo).

    Durante el análisis, el pipeline hace decenas de llamadas LLM en bucle
    (correferencias, temporal, perfiles). Si el usuario manda un mensaje al
    chat, el scheduler hace que el análisis ceda el turno al chat entre
    iteraciones, para que la respuesta interactiva sea rápida.

    Uso:
        # En el chat endpoint:
        with llm_scheduler.chat_priority():
            response = llm_client.complete(prompt, system)

        # En bucles de análisis (entre iteraciones LLM):
        for anaphor in anaphors:
            llm_scheduler.yield_to_chat()
            result = resolver.resolve(anaphor, candidates, context)
    """

    def __init__(self) -> None:
        self._chat_pending = threading.Event()
        self._chat_done = threading.Event()
        self._chat_done.set()  # Inicialmente no hay chat pendiente

    def yield_to_chat(self) -> None:
        """
        Llamar entre iteraciones LLM del análisis.

        Si hay un chat esperando, bloquea hasta que el chat termine.
        Si no hay chat pendiente, retorna inmediatamente (coste ~0).
        """
        if self._chat_pending.is_set():
            logger.debug("Análisis cede turno a chat interactivo")
            self._chat_done.wait(timeout=120)

    @contextmanager
    def chat_priority(self):
        """
        Context manager para llamadas LLM del chat interactivo.

        Señala al análisis que hay un chat esperando. El análisis cede
        el turno en su próximo yield_to_chat(). Después del chat,
        el análisis continúa automáticamente.
        """
        self._chat_done.clear()
        self._chat_pending.set()
        try:
            yield
        finally:
            self._chat_pending.clear()
            self._chat_done.set()

    @property
    def is_chat_pending(self) -> bool:
        """True si hay un chat esperando turno."""
        return self._chat_pending.is_set()


# Singleton global
_scheduler: LLMScheduler | None = None
_scheduler_lock = threading.Lock()


def get_llm_scheduler() -> LLMScheduler:
    """Obtiene el singleton del scheduler LLM."""
    global _scheduler
    if _scheduler is None:
        with _scheduler_lock:
            if _scheduler is None:
                _scheduler = LLMScheduler()
    return _scheduler


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
        self._ollama_num_gpu: int | None = None  # None = Ollama decide, 0 = CPU
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
        result = self._verify_ollama_model(manager)
        if result:
            self._ollama_num_gpu = self._determine_ollama_num_gpu()
        return result

    def _determine_ollama_num_gpu(self) -> int | None:
        """
        Determina el valor de num_gpu para solicitudes a Ollama.

        Comprueba si la GPU está bloqueada (CC < 6.0) o tiene poca VRAM
        (< 6 GB) para evitar crashes de Ollama por falta de memoria.

        Returns:
            0 para forzar CPU, None para dejar que Ollama decida (auto).
        """
        if self._config.force_cpu:
            logger.info("Ollama forzado a CPU por configuración (force_cpu=True)")
            return 0

        try:
            from ..core.device import get_blocked_gpu_info

            blocked = get_blocked_gpu_info()
            if blocked:
                logger.info(
                    f"GPU bloqueada ({blocked.get('name', '?')}, "
                    f"CC {blocked.get('compute_capability', '?')}). "
                    f"Ollama usará num_gpu=0 (CPU)."
                )
                return 0
        except Exception as e:
            logger.debug(f"Error comprobando GPU bloqueada: {e}")

        try:
            from ..core.device import DeviceType, get_device_detector

            detector = get_device_detector()
            device = detector.detect_best_device()
            if device.device_type == DeviceType.CUDA and device.is_low_vram:
                logger.info(
                    f"GPU {device.device_name} con VRAM limitada "
                    f"({device.memory_gb:.1f}GB). "
                    f"Ollama usará num_gpu=0 (CPU)."
                )
                return 0
        except Exception as e:
            logger.debug(f"Error detectando VRAM: {e}")

        return None

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
            from ..core.device import get_device_detector

            cuda = get_device_detector().detect_cuda()
            if cuda:
                has_gpu = True
                vram_gb = cuda.memory_gb or 0.0
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
        model_name: str | None = None,
    ) -> str | None:
        """
        Genera una respuesta usando el LLM local.

        Args:
            prompt: El prompt del usuario
            system: Mensaje de sistema opcional
            max_tokens: Override de max_tokens
            temperature: Override de temperature
            model_name: Override opcional del modelo Ollama a usar

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
                return self._complete_ollama(prompt, system, max_tokens, temperature, model_name)
            elif self._backend == "transformers":
                return self._complete_transformers(prompt, system, max_tokens, temperature)

        return None

    # Patrones de error de Ollama que indican fallo de VRAM/GPU
    _VRAM_ERROR_PATTERNS = (
        "llama runner process has terminated",
        "exit status 2",
        "graph_reserve",
        "compute buffer",
        "out of memory",
        "ggml_cuda",
        "failed to allocate",
    )

    def _is_ollama_vram_error(self, status_code: int, response_text: str) -> bool:
        """Detecta si el error de Ollama indica fallo de VRAM/GPU."""
        if status_code != 500:
            return False
        text_lower = response_text.lower()
        return any(p in text_lower for p in self._VRAM_ERROR_PATTERNS)

    def _send_ollama_request(
        self,
        messages: list[dict[str, str]],
        options: dict[str, Any],
        timeout_config: Any,
        model_name: str | None = None,
    ) -> tuple[str | None, int | None]:
        """
        Envía request a Ollama y retorna (content, status_code).

        Returns:
            - Éxito: (content_string, 200)
            - Error HTTP: (response_body, status_code)
            - Error de red: (error_message, None)
        """
        try:
            import httpx

            response = httpx.post(
                f"{self._config.ollama_host}/api/chat",
                json={
                    "model": model_name or self._config.ollama_model,
                    "messages": messages,
                    "stream": False,
                    "options": options,
                },
                timeout=timeout_config,
            )

            if response.status_code == 200:
                data = response.json()
                content = data.get("message", {}).get("content", "")
                return content, 200

            return response.text, response.status_code

        except Exception as e:
            logger.error(f"Error en llamada a Ollama: {e}")
            return str(e), None

    def _complete_ollama(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        model_name: str | None = None,
    ) -> str | None:
        """Genera respuesta usando Ollama con fallback a CPU si hay crash de VRAM."""
        try:
            import httpx
        except ImportError:
            logger.error("httpx no instalado, no se puede usar Ollama")
            return None

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        timeout_config = httpx.Timeout(
            connect=10.0,
            read=self._config.timeout,
            write=30.0,
            pool=10.0,
        )

        options: dict[str, Any] = {
            "num_predict": max_tokens if max_tokens is not None else self._config.max_tokens,
            "temperature": temperature if temperature is not None else self._config.temperature,
        }
        if self._ollama_num_gpu is not None:
            options["num_gpu"] = self._ollama_num_gpu

        # Primer intento
        content, status = self._send_ollama_request(
            messages, options, timeout_config, model_name=model_name
        )

        if status == 200 and content:
            return content

        # Detectar crash de VRAM → retry con CPU
        if (
            status is not None
            and self._is_ollama_vram_error(status, content or "")
            and options.get("num_gpu") != 0
        ):
            logger.warning(
                "Ollama falló por VRAM insuficiente. "
                "Reintentando con num_gpu=0 (CPU)..."
            )
            options["num_gpu"] = 0
            self._ollama_num_gpu = 0  # Persistir para futuras llamadas

            content, status = self._send_ollama_request(
                messages, options, timeout_config, model_name=model_name
            )
            if status == 200 and content:
                logger.info("Ollama respondió en modo CPU. Futuras llamadas usarán CPU.")
                return content

        if status is not None and status != 200:
            logger.error(
                f"Error de Ollama: {status} - {(content or '')[:200]}"
            )
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
                max_new_tokens=max_tokens if max_tokens is not None else self._config.max_tokens,
                temperature=temperature if temperature is not None else self._config.temperature,
                do_sample=True,
                pad_token_id=self._transformers_pipeline.tokenizer.eos_token_id,
            )

            generated_text = result[0]["generated_text"]
            # Extraer solo la respuesta del asistente
            if "<|assistant|>" in generated_text:
                response = generated_text.split("<|assistant|>")[-1].strip()
                return response  # type: ignore[no-any-return]

            return generated_text[len(full_prompt) :].strip()  # type: ignore[no-any-return]

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

            return json.loads(cleaned)  # type: ignore[no-any-return]

        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON: {e}")
            logger.debug(f"Respuesta recibida: {response[:500]}")
            return None

    def voting_query(
        self,
        task_name: str,
        prompt: str,
        system: str,
        parse_fn: Callable[[str], Any] | None = None,
        quality_level: Any | None = None,
        sensitivity: float = 5.0,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ):
        """
        Ejecuta una query con votación multi-modelo por roles.

        Obtiene la configuración de votación para la tarea, resuelve fallbacks
        con los modelos realmente disponibles, ejecuta cada slot secuencialmente,
        y consolida los resultados con pesos ponderados.

        Args:
            task_name: Nombre de la tarea (debe coincidir con AnalysisTask)
            prompt: Prompt para el LLM
            system: System prompt
            parse_fn: Función para parsear la respuesta cruda. Si None, devuelve texto.
            quality_level: QualityLevel override. Si None, usa el configurado en DB.
            sensitivity: Valor del slider de sensibilidad (1-10)
            max_tokens: Override de tokens máximos
            temperature: Override de temperatura

        Returns:
            VotingResult con consenso, confianza y detalles por modelo
        """
        from .config import (
            AnalysisTask,
            QualityLevel,
            VotingResult,
            get_voting_config,
        )

        # Resolver tarea
        try:
            task = AnalysisTask(task_name)
        except ValueError:
            logger.error(f"Tarea desconocida para votación: {task_name}")
            return VotingResult(
                consensus=None, confidence=0.0,
                models_used=[], roles_used=[],
            )

        # Nivel de calidad
        if quality_level is None:
            quality_level = QualityLevel.RAPIDA
        elif isinstance(quality_level, str):
            try:
                quality_level = QualityLevel(quality_level)
            except ValueError:
                quality_level = QualityLevel.RAPIDA

        # Obtener modelos disponibles
        available = self._get_available_ollama_models()

        # Resolver configuración de votación
        config = get_voting_config(task, available, quality_level, sensitivity)

        if not config.slots:
            logger.error(f"Votación {task_name}: sin modelos disponibles")
            return VotingResult(
                consensus=None, confidence=0.0,
                models_used=[], roles_used=[],
            )

        # Ejecutar cada slot
        per_model_results: dict[str, Any] = {}
        per_model_times: dict[str, float] = {}
        fallbacks_applied: list[str] = []
        models_used: list[str] = []
        roles_used = []

        # Detectar fallbacks
        from .config import QUALITY_MATRIX
        original_config = QUALITY_MATRIX.get(task)
        if original_config:
            original_models = {s.model_name for s in original_config.slot_for_level(quality_level)}
            for slot in config.slots:
                if slot.model_name not in original_models:
                    # Encontrar qué modelo original fue sustituido
                    for orig_slot in original_config.slot_for_level(quality_level):
                        if orig_slot.role == slot.role and orig_slot.model_name != slot.model_name:
                            fallbacks_applied.append(
                                f"{orig_slot.model_name}→{slot.model_name} ({slot.role.value})"
                            )

        for slot in config.slots:
            start = time.time()
            try:
                response = self.complete(
                    prompt=prompt,
                    system=system,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    model_name=slot.model_name,
                )
            except Exception as e:
                elapsed = time.time() - start
                logger.warning(
                    f"Votación {task_name}/{slot.model_name}: error en complete(): {e}"
                )
                per_model_times[slot.model_name] = elapsed
                continue
            elapsed = time.time() - start

            if response:
                try:
                    parsed = parse_fn(response) if parse_fn else response
                except Exception as e:
                    logger.warning(
                        f"Votación {task_name}/{slot.model_name}: error en parse_fn: {e}"
                    )
                    per_model_times[slot.model_name] = elapsed
                    continue
                per_model_results[slot.model_name] = parsed
                per_model_times[slot.model_name] = elapsed
                models_used.append(slot.model_name)
                roles_used.append(slot.role)
                logger.debug(
                    f"Votación {task_name}/{slot.model_name} "
                    f"({slot.role.value}, peso {slot.weight:.2f}): "
                    f"{elapsed:.1f}s"
                )
            else:
                logger.warning(
                    f"Votación {task_name}/{slot.model_name}: sin respuesta"
                )
                per_model_times[slot.model_name] = elapsed

        # Consolidar resultados
        consensus, confidence = self._compute_consensus(
            per_model_results, config.slots, config.min_confidence
        )

        result = VotingResult(
            consensus=consensus,
            confidence=confidence,
            models_used=models_used,
            roles_used=roles_used,
            per_model_results=per_model_results,
            per_model_times=per_model_times,
            fallbacks_applied=fallbacks_applied,
        )

        logger.info(
            f"Votación {task_name}: {len(models_used)} modelos, "
            f"confianza {confidence:.2f}, "
            f"fallbacks: {fallbacks_applied or 'ninguno'}"
        )

        return result

    def _get_available_ollama_models(self) -> set[str]:
        """Obtiene los modelos de Ollama realmente instalados."""
        try:
            import httpx

            host = self._config.ollama_host
            response = httpx.get(f"{host}/api/tags", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                models = set()
                for m in data.get("models", []):
                    name = m.get("name", "").split(":")[0]
                    if name:
                        models.add(name)
                return models
        except Exception as e:
            logger.debug(f"Error obteniendo modelos Ollama: {e}")

        # Fallback: devolver modelo configurado
        return {self._config.ollama_model}

    def _compute_consensus(
        self,
        results: dict[str, Any],
        slots: list,
        min_confidence: float,
    ) -> tuple[Any, float]:
        """
        Consolida resultados de votación ponderada.

        Para texto libre: selecciona el resultado del modelo con mayor peso.
        Para datos estructurados (dict): fusiona campos con pesos.

        Returns:
            (consensus_result, confidence)
        """
        if not results:
            return None, 0.0

        # Mapear modelo → peso
        weight_map = {s.model_name: s.weight for s in slots}

        # Si solo hay 1 resultado, usarlo directamente
        if len(results) == 1:
            model, result = next(iter(results.items()))
            confidence = weight_map.get(model, 0.5)
            return result, confidence

        # Múltiples resultados: usar el de mayor peso como base
        sorted_results = sorted(
            results.items(),
            key=lambda x: weight_map.get(x[0], 0),
            reverse=True,
        )

        best_model, best_result = sorted_results[0]
        total_weight = sum(weight_map.get(m, 0) for m in results)

        # Confianza: promedio ponderado (todos respondieron = alta confianza)
        expected_weight = sum(s.weight for s in slots)
        confidence = total_weight / expected_weight if expected_weight > 0 else 0.0

        return best_result, confidence


def _validate_ollama_host(host: str) -> str:
    """Valida que el host de Ollama sea seguro (A-12: solo localhost)."""
    import urllib.parse as urlparse

    try:
        parsed = urlparse.urlparse(host)
    except Exception:
        logger.warning(f"URL de host inválida: {host}, usando default")
        return "http://localhost:11434"

    if parsed.scheme not in ("http", "https"):
        logger.warning(f"Esquema no permitido: {parsed.scheme}, usando default")
        return "http://localhost:11434"

    allowed_hosts = {"localhost", "127.0.0.1", "::1", "[::1]"}
    hostname = (parsed.hostname or "").lower()
    if hostname not in allowed_hosts:
        logger.warning(
            f"Host no permitido en NA_OLLAMA_HOST: {hostname}. "
            "Solo localhost permitido por seguridad. Usando default."
        )
        return "http://localhost:11434"

    return host


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

    # A-12: Validar host de Ollama desde variable de entorno
    ollama_host = _validate_ollama_host(
        os.getenv("NA_OLLAMA_HOST", "http://localhost:11434")
    )

    config = LocalLLMConfig(
        backend=backend,  # type: ignore
        ollama_host=ollama_host,
        ollama_model=os.getenv("NA_OLLAMA_MODEL", "llama3.2"),
    )

    # A-04: Validar ruta del modelo desde variable de entorno
    if model_path_str := os.getenv("NA_LLM_MODEL_PATH"):
        model_path = Path(model_path_str).resolve()
        if model_path.is_absolute() and model_path.exists():
            config.transformers_model_path = model_path
        else:
            logger.warning(
                f"NA_LLM_MODEL_PATH inválido o no existe: {model_path_str}"
            )

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
