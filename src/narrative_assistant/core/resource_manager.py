"""
Gestor de recursos del sistema.

Detecta capacidades de la máquina y optimiza el uso de recursos:
- CPU cores y carga actual
- RAM disponible
- GPU VRAM
- Recomendaciones de paralelismo
- Control de tareas pesadas concurrentes
"""

import logging
import os
import platform
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Intentar importar psutil para monitoreo avanzado
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil no disponible - monitoreo de recursos limitado")


class ResourceTier(Enum):
    """Clasificación de capacidad del sistema."""

    LOW = "low"  # <4 cores, <8GB RAM, no GPU
    MEDIUM = "medium"  # 4-8 cores, 8-16GB RAM, GPU opcional
    HIGH = "high"  # >8 cores, >16GB RAM, GPU con >6GB VRAM


class TaskPriority(Enum):
    """Prioridad de tareas para scheduling."""

    CRITICAL = 1  # NER, parsing básico
    HIGH = 2  # Correferencias, embeddings
    NORMAL = 3  # Análisis de calidad
    LOW = 4  # Redundancia semántica, exportaciones


@dataclass
class SystemCapabilities:
    """Capacidades detectadas del sistema."""

    # CPU
    cpu_cores_logical: int = 1
    cpu_cores_physical: int = 1
    cpu_percent: float = 0.0  # Uso actual

    # RAM
    ram_total_mb: int = 0
    ram_available_mb: int = 0
    ram_percent_used: float = 0.0

    # GPU
    gpu_available: bool = False
    gpu_name: str = ""
    gpu_vram_total_mb: int = 0
    gpu_vram_available_mb: int = 0
    gpu_is_low_vram: bool = True  # <6GB

    # Clasificación
    tier: ResourceTier = ResourceTier.LOW

    # Timestamp
    detected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Serializa a diccionario."""
        return {
            "cpu_cores_logical": self.cpu_cores_logical,
            "cpu_cores_physical": self.cpu_cores_physical,
            "cpu_percent": self.cpu_percent,
            "ram_total_mb": self.ram_total_mb,
            "ram_available_mb": self.ram_available_mb,
            "ram_percent_used": self.ram_percent_used,
            "gpu_available": self.gpu_available,
            "gpu_name": self.gpu_name,
            "gpu_vram_total_mb": self.gpu_vram_total_mb,
            "gpu_vram_available_mb": self.gpu_vram_available_mb,
            "gpu_is_low_vram": self.gpu_is_low_vram,
            "tier": self.tier.value,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class ResourceRecommendation:
    """Recomendaciones de uso de recursos."""

    max_workers: int = 2
    batch_size_embeddings: int = 16
    batch_size_nlp: int = 100
    use_gpu_for_embeddings: bool = False
    use_gpu_for_spacy: bool = False
    enable_semantic_redundancy: bool = True
    max_concurrent_heavy_tasks: int = 1
    chunk_large_documents: bool = False
    document_chunk_size: int = 50000  # caracteres

    def to_dict(self) -> dict:
        """Serializa a diccionario."""
        return {
            "max_workers": self.max_workers,
            "batch_size_embeddings": self.batch_size_embeddings,
            "batch_size_nlp": self.batch_size_nlp,
            "use_gpu_for_embeddings": self.use_gpu_for_embeddings,
            "use_gpu_for_spacy": self.use_gpu_for_spacy,
            "enable_semantic_redundancy": self.enable_semantic_redundancy,
            "max_concurrent_heavy_tasks": self.max_concurrent_heavy_tasks,
            "chunk_large_documents": self.chunk_large_documents,
            "document_chunk_size": self.document_chunk_size,
        }


class HeavyTaskSemaphore:
    """
    Semáforo para controlar tareas pesadas concurrentes.

    Evita que múltiples análisis que consumen mucha memoria
    corran simultáneamente.
    """

    def __init__(self, max_concurrent: int = 1):
        self.max_concurrent = max_concurrent
        self._semaphore = threading.Semaphore(max_concurrent)
        self._active_tasks: list[str] = []
        self._lock = threading.Lock()

    def acquire(self, task_name: str, timeout: float | None = None) -> bool:
        """
        Intenta adquirir el semáforo para una tarea pesada.

        Args:
            task_name: Nombre de la tarea
            timeout: Tiempo máximo de espera (None = infinito)

        Returns:
            True si se adquirió, False si timeout
        """
        acquired = self._semaphore.acquire(timeout=timeout)
        if acquired:
            with self._lock:
                self._active_tasks.append(task_name)
            logger.debug(f"Tarea pesada iniciada: {task_name}")
        else:
            logger.warning(f"Timeout esperando recursos para: {task_name}")
        return acquired

    def release(self, task_name: str) -> None:
        """Libera el semáforo después de completar una tarea."""
        with self._lock:
            if task_name in self._active_tasks:
                self._active_tasks.remove(task_name)
        self._semaphore.release()
        logger.debug(f"Tarea pesada completada: {task_name}")

    @property
    def active_tasks(self) -> list[str]:
        """Retorna lista de tareas activas."""
        with self._lock:
            return self._active_tasks.copy()

    @property
    def available_slots(self) -> int:
        """Retorna slots disponibles."""
        with self._lock:
            return self.max_concurrent - len(self._active_tasks)


class ResourceManager:
    """
    Gestor singleton de recursos del sistema.

    Detecta capacidades de la máquina y proporciona recomendaciones
    para optimizar el uso de recursos durante el análisis.
    """

    _instance: Optional["ResourceManager"] = None
    _lock = threading.Lock()

    # Tareas consideradas "pesadas" (alto consumo de memoria)
    HEAVY_TASKS = {
        "semantic_redundancy",
        "embeddings_full",
        "coreference_resolution",
        "llm_analysis",
        "spacy_full_pipeline",
    }

    def __new__(cls) -> "ResourceManager":
        """Singleton thread-safe."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._capabilities: SystemCapabilities | None = None
        self._recommendation: ResourceRecommendation | None = None
        self._heavy_task_semaphore: HeavyTaskSemaphore | None = None
        self._initialized = True

        # Detectar capacidades al inicializar
        self.refresh_capabilities()

    def refresh_capabilities(self) -> SystemCapabilities:
        """Detecta y actualiza las capacidades del sistema."""
        caps = SystemCapabilities()

        # CPU
        caps.cpu_cores_logical = os.cpu_count() or 1
        caps.cpu_cores_physical = self._get_physical_cores()

        if PSUTIL_AVAILABLE:
            caps.cpu_percent = psutil.cpu_percent(interval=0.1)

        # RAM
        if PSUTIL_AVAILABLE:
            mem = psutil.virtual_memory()
            caps.ram_total_mb = mem.total // (1024 * 1024)
            caps.ram_available_mb = mem.available // (1024 * 1024)
            caps.ram_percent_used = mem.percent
        else:
            # Fallback: estimar basado en plataforma
            caps.ram_total_mb = self._estimate_ram()
            caps.ram_available_mb = caps.ram_total_mb // 2  # Asumir 50% disponible

        # GPU
        self._detect_gpu(caps)

        # Clasificación
        caps.tier = self._classify_tier(caps)

        self._capabilities = caps
        self._recommendation = self._generate_recommendation(caps)

        # Actualizar semáforo de tareas pesadas
        self._heavy_task_semaphore = HeavyTaskSemaphore(
            max_concurrent=self._recommendation.max_concurrent_heavy_tasks
        )

        logger.info(
            f"Sistema detectado: {caps.tier.value} - "
            f"CPU: {caps.cpu_cores_physical}c/{caps.cpu_cores_logical}t, "
            f"RAM: {caps.ram_available_mb}MB/{caps.ram_total_mb}MB, "
            f"GPU: {caps.gpu_name or 'N/A'}"
        )

        return caps

    def _get_physical_cores(self) -> int:
        """Obtiene número de cores físicos."""
        if PSUTIL_AVAILABLE:
            try:
                return psutil.cpu_count(logical=False) or 1
            except Exception:
                pass

        # Fallback: asumir hyperthreading (logical / 2)
        logical = os.cpu_count() or 2
        return max(1, logical // 2)

    def _estimate_ram(self) -> int:
        """Estima RAM total cuando psutil no está disponible."""
        # Valores por defecto conservadores según plataforma
        system = platform.system().lower()
        if system == "darwin" or system == "windows":  # macOS
            return 8192  # 8GB típico
        else:  # Linux
            try:
                with open("/proc/meminfo") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            # MemTotal: 16384000 kB
                            kb = int(line.split()[1])
                            return kb // 1024
            except Exception:
                pass
            return 4096  # 4GB conservador

    def _detect_gpu(self, caps: SystemCapabilities) -> None:
        """Detecta GPU y VRAM."""
        try:
            import torch

            if torch.cuda.is_available():
                caps.gpu_available = True
                device = torch.cuda.current_device()
                caps.gpu_name = torch.cuda.get_device_name(device)
                props = torch.cuda.get_device_properties(device)
                caps.gpu_vram_total_mb = props.total_memory // (1024 * 1024)

                # VRAM disponible
                free_mem = torch.cuda.mem_get_info()[0]
                caps.gpu_vram_available_mb = free_mem // (1024 * 1024)

                caps.gpu_is_low_vram = caps.gpu_vram_total_mb < 6144  # <6GB

            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                # Apple Silicon
                caps.gpu_available = True
                caps.gpu_name = "Apple Silicon (MPS)"
                caps.gpu_vram_total_mb = 8192  # Asumido, MPS usa RAM unificada
                caps.gpu_vram_available_mb = caps.ram_available_mb // 2
                caps.gpu_is_low_vram = False  # MPS maneja memoria dinámicamente

        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Error detectando GPU: {e}")

    def _classify_tier(self, caps: SystemCapabilities) -> ResourceTier:
        """Clasifica el sistema en un tier de capacidad."""
        # HIGH: >8 cores, >16GB RAM, GPU con >6GB VRAM
        if (
            caps.cpu_cores_physical >= 8
            and caps.ram_total_mb >= 16384
            and caps.gpu_available
            and not caps.gpu_is_low_vram
        ):
            return ResourceTier.HIGH

        # MEDIUM: 4-8 cores, 8-16GB RAM
        if caps.cpu_cores_physical >= 4 and caps.ram_total_mb >= 8192:
            return ResourceTier.MEDIUM

        # LOW: resto
        return ResourceTier.LOW

    def _generate_recommendation(self, caps: SystemCapabilities) -> ResourceRecommendation:
        """Genera recomendaciones basadas en capacidades."""
        rec = ResourceRecommendation()

        # Workers basados en cores y RAM disponible
        # Usar min(cores físicos - 1, RAM disponible / 2GB)
        cores_based = max(1, caps.cpu_cores_physical - 1)
        ram_based = max(1, caps.ram_available_mb // 2048)  # 2GB por worker
        rec.max_workers = min(cores_based, ram_based, 8)  # Máximo 8

        # GPU para embeddings
        if caps.gpu_available and not caps.gpu_is_low_vram:
            rec.use_gpu_for_embeddings = True
            rec.batch_size_embeddings = 64
        elif caps.gpu_available:
            # GPU con poca VRAM: usar para spaCy pero no embeddings
            rec.use_gpu_for_embeddings = False
            rec.use_gpu_for_spacy = True
            rec.batch_size_embeddings = 32
        else:
            rec.batch_size_embeddings = 16

        # Tareas pesadas concurrentes
        if caps.tier == ResourceTier.HIGH:
            rec.max_concurrent_heavy_tasks = 2
        elif caps.tier == ResourceTier.MEDIUM:
            rec.max_concurrent_heavy_tasks = 1
        else:
            rec.max_concurrent_heavy_tasks = 1

        # Redundancia semántica: siempre habilitada pero ajustada
        rec.enable_semantic_redundancy = True

        # Chunking para documentos grandes
        if caps.ram_available_mb < 4096:
            rec.chunk_large_documents = True
            rec.document_chunk_size = 30000
        elif caps.ram_available_mb < 8192:
            rec.document_chunk_size = 50000
        else:
            rec.document_chunk_size = 100000

        # Batch NLP basado en RAM
        if caps.ram_available_mb >= 8192:
            rec.batch_size_nlp = 200
        elif caps.ram_available_mb >= 4096:
            rec.batch_size_nlp = 100
        else:
            rec.batch_size_nlp = 50

        logger.debug(f"Recomendaciones generadas: {rec.to_dict()}")
        return rec

    @property
    def capabilities(self) -> SystemCapabilities:
        """Retorna capacidades detectadas."""
        if self._capabilities is None:
            self.refresh_capabilities()
        return self._capabilities

    @property
    def recommendation(self) -> ResourceRecommendation:
        """Retorna recomendaciones actuales."""
        if self._recommendation is None:
            self.refresh_capabilities()
        return self._recommendation

    @property
    def heavy_task_semaphore(self) -> HeavyTaskSemaphore:
        """Retorna semáforo para tareas pesadas."""
        if self._heavy_task_semaphore is None:
            self.refresh_capabilities()
        return self._heavy_task_semaphore

    def is_system_under_pressure(self) -> bool:
        """Verifica si el sistema está bajo presión de recursos."""
        if not PSUTIL_AVAILABLE:
            return False

        try:
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()

            # Presión si CPU > 80% o RAM > 85%
            return cpu > 80 or mem.percent > 85
        except Exception:
            return False

    def get_available_workers(self) -> int:
        """
        Retorna número de workers recomendados basado en estado actual.

        Reduce workers si el sistema está bajo presión.
        """
        base = self.recommendation.max_workers

        if self.is_system_under_pressure():
            return max(1, base // 2)

        return base

    def can_run_heavy_task(self, task_name: str) -> bool:
        """Verifica si se puede ejecutar una tarea pesada."""
        if task_name not in self.HEAVY_TASKS:
            return True

        return self.heavy_task_semaphore.available_slots > 0

    def run_heavy_task(
        self,
        task_name: str,
        func: Callable[..., Any],
        *args,
        timeout: float | None = None,
        **kwargs,
    ) -> Any:
        """
        Ejecuta una tarea pesada con control de recursos.

        Args:
            task_name: Nombre de la tarea
            func: Función a ejecutar
            *args: Argumentos posicionales
            timeout: Tiempo máximo de espera para adquirir recursos
            **kwargs: Argumentos nombrados

        Returns:
            Resultado de la función

        Raises:
            TimeoutError: Si no se pueden adquirir recursos en el timeout
        """
        if task_name in self.HEAVY_TASKS:
            if not self.heavy_task_semaphore.acquire(task_name, timeout=timeout):
                raise TimeoutError(
                    f"No se pudieron adquirir recursos para '{task_name}' en {timeout}s. "
                    f"Tareas activas: {self.heavy_task_semaphore.active_tasks}"
                )
            try:
                return func(*args, **kwargs)
            finally:
                self.heavy_task_semaphore.release(task_name)
        else:
            return func(*args, **kwargs)

    def get_status(self) -> dict:
        """Retorna estado actual del sistema y recursos."""
        caps = self.capabilities
        rec = self.recommendation

        # Actualizar métricas en tiempo real si psutil disponible
        current_cpu = 0.0
        current_ram_available = caps.ram_available_mb
        current_ram_percent = caps.ram_percent_used

        if PSUTIL_AVAILABLE:
            try:
                current_cpu = psutil.cpu_percent(interval=0.1)
                mem = psutil.virtual_memory()
                current_ram_available = mem.available // (1024 * 1024)
                current_ram_percent = mem.percent
            except Exception:
                pass

        return {
            "capabilities": caps.to_dict(),
            "recommendation": rec.to_dict(),
            "current_state": {
                "cpu_percent": current_cpu,
                "ram_available_mb": current_ram_available,
                "ram_percent_used": current_ram_percent,
                "system_under_pressure": self.is_system_under_pressure(),
                "available_workers": self.get_available_workers(),
                "heavy_tasks_active": self.heavy_task_semaphore.active_tasks,
                "heavy_tasks_slots_available": self.heavy_task_semaphore.available_slots,
            },
        }


# Singleton accessor
_resource_manager: ResourceManager | None = None
_manager_lock = threading.Lock()


def get_resource_manager() -> ResourceManager:
    """
    Obtiene la instancia singleton del gestor de recursos.

    Thread-safe con double-checked locking.
    """
    global _resource_manager

    if _resource_manager is None:
        with _manager_lock:
            if _resource_manager is None:
                _resource_manager = ResourceManager()
                logger.debug("ResourceManager singleton inicializado")

    return _resource_manager
