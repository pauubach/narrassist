"""
Módulo de detección y gestión de dispositivos de cómputo (CPU/GPU).

Soporta:
- NVIDIA CUDA (Linux/Windows)
- Apple Metal (MPS) en Apple Silicon
- Fallback automático a CPU

Incluye gestión defensiva de memoria GPU para evitar crashes en sistemas
con VRAM limitada (< 6GB).

IMPORTANTE: Este módulo bloquea GPUs inseguras (CC < 6.0) a nivel de
entorno (CUDA_VISIBLE_DEVICES) ANTES de que PyTorch pueda inicializar
CUDA. Esto previene BSOD en GPUs pre-Pascal (Maxwell, Kepler).
"""

import gc
import logging
import os
import platform
import subprocess
import threading
from dataclasses import dataclass
from enum import Enum, auto

logger = logging.getLogger(__name__)

# Umbral de VRAM para considerar GPU "segura" para uso intensivo
MIN_SAFE_VRAM_GB = 6.0

# Compute Capability mínima para usar CUDA sin riesgo de BSOD/crash
# GPUs con CC < 6.0 (pre-Pascal) tienen drivers inestables con PyTorch moderno
MIN_SAFE_COMPUTE_CAPABILITY = 6.0


# Info sobre GPU bloqueada (si aplica) — se llena en _block_unsafe_gpu()
_blocked_gpu_info: dict | None = None


def get_blocked_gpu_info() -> dict | None:
    """Retorna info de la GPU bloqueada, o None si no se bloqueó ninguna."""
    return _blocked_gpu_info


def _block_unsafe_gpu() -> None:
    """
    Bloquea GPUs inseguras ANTES de que PyTorch/CuPy las vean.

    Usa nvidia-smi (no requiere PyTorch) para detectar la Compute Capability.
    Si la GPU tiene CC < 6.0 (pre-Pascal: Maxwell, Kepler, Fermi), establece
    CUDA_VISIBLE_DEVICES="" para que torch.cuda.is_available() retorne False
    en TODOS los módulos, cerrando cualquier bypass.

    Esto previene BSODs causados por drivers inestables en GPUs antiguas
    con versiones modernas de PyTorch/CUDA.
    """
    global _blocked_gpu_info

    # Si el usuario ya forzó CPU, no hacer nada
    if os.environ.get("NA_DEVICE", "").lower() == "cpu":
        return

    # Si ya se deshabilitó CUDA externamente, no hacer nada
    cuda_visible = os.environ.get("CUDA_VISIBLE_DEVICES")
    if cuda_visible is not None and cuda_visible.strip() in ("", "-1"):
        return

    try:
        # Obtener CC y nombre de la GPU
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=compute_cap,name", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return  # nvidia-smi no disponible o falló

        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            try:
                cc = float(parts[0])
            except (ValueError, IndexError):
                continue

            gpu_name = parts[1] if len(parts) > 1 else "GPU NVIDIA"

            if cc < MIN_SAFE_COMPUTE_CAPABILITY:
                os.environ["CUDA_VISIBLE_DEVICES"] = ""
                _blocked_gpu_info = {
                    "name": gpu_name,
                    "compute_capability": cc,
                    "min_required": MIN_SAFE_COMPUTE_CAPABILITY,
                }
                # Usar print porque logger puede no estar configurado aún
                print(
                    f"[device] {gpu_name} (Compute Capability {cc}) detectada. "
                    f"Mínimo requerido: {MIN_SAFE_COMPUTE_CAPABILITY}. "
                    f"CUDA deshabilitado para prevenir BSOD. Usando CPU."
                )
                return
    except FileNotFoundError:
        pass  # nvidia-smi no instalado → no hay GPU NVIDIA
    except Exception:
        pass  # Cualquier error → no bloquear, dejar que el detector decida


# CRÍTICO: Ejecutar ANTES de cualquier import de torch/cupy
_block_unsafe_gpu()

# Lock para thread-safety en singleton
_detector_lock = threading.Lock()


class DeviceType(Enum):
    """Tipos de dispositivo soportados."""

    CPU = auto()
    CUDA = auto()  # NVIDIA GPU
    MPS = auto()  # Apple Silicon GPU


@dataclass
class DeviceInfo:
    """Información del dispositivo seleccionado."""

    device_type: DeviceType
    device_name: str
    device_id: int  # Para CUDA multi-GPU, -1 para CPU
    memory_gb: float | None  # Memoria disponible si se puede detectar
    is_available: bool

    def __str__(self) -> str:
        mem_str = f", {self.memory_gb:.1f}GB" if self.memory_gb else ""
        return f"{self.device_type.name}: {self.device_name}{mem_str}"

    @property
    def is_low_vram(self) -> bool:
        """
        Indica si el dispositivo tiene VRAM limitada.

        GPUs con < 6GB de VRAM pueden tener problemas al ejecutar
        múltiples modelos (Ollama + embeddings + spaCy) simultáneamente.
        """
        if self.device_type == DeviceType.CPU:
            return False  # CPU no tiene VRAM
        if self.memory_gb is None:
            return True  # Asumir low VRAM si no podemos detectar
        return self.memory_gb < MIN_SAFE_VRAM_GB


class DeviceDetector:
    """
    Detecta y selecciona el mejor dispositivo disponible.

    Orden de preferencia:
    1. CUDA (si disponible y no deshabilitado)
    2. MPS (Apple Silicon, si disponible)
    3. CPU (siempre disponible)
    """

    def __init__(self):
        self._detected_device: DeviceInfo | None = None
        self._torch_available: bool = False
        self._cupy_available: bool = False

    def detect_cuda(self) -> DeviceInfo | None:
        """
        Detecta GPU NVIDIA con CUDA.

        Rechaza GPUs con Compute Capability < MIN_SAFE_COMPUTE_CAPABILITY
        para evitar BSOD/crashes con drivers antiguos (pre-Pascal: Kepler, Maxwell).
        """
        try:
            import torch

            self._torch_available = True

            if torch.cuda.is_available():
                device_id = 0  # Usar primera GPU por defecto
                props = torch.cuda.get_device_properties(device_id)
                device_name = props.name
                memory_gb = props.total_memory / (1024**3)
                cc = float(f"{props.major}.{props.minor}")

                logger.info(
                    f"CUDA detectada: {device_name} "
                    f"(CC {cc}, {memory_gb:.1f} GB VRAM)"
                )

                # Rechazar GPUs con Compute Capability antigua
                if cc < MIN_SAFE_COMPUTE_CAPABILITY:
                    logger.warning(
                        f"GPU {device_name} tiene Compute Capability {cc} "
                        f"(mínimo requerido: {MIN_SAFE_COMPUTE_CAPABILITY}). "
                        f"Usando CPU para evitar inestabilidad de driver. "
                        f"Para forzar GPU: NA_DEVICE=cuda"
                    )
                    return None

                return DeviceInfo(
                    device_type=DeviceType.CUDA,
                    device_name=device_name,
                    device_id=device_id,
                    memory_gb=memory_gb,
                    is_available=True,
                )
        except ImportError:
            logger.debug("PyTorch no instalado, CUDA no disponible")
        except Exception as e:
            logger.warning(f"Error detectando CUDA: {e}")

        return None

    def detect_mps(self) -> DeviceInfo | None:
        """Detecta GPU Apple Silicon (Metal Performance Shaders)."""
        try:
            import torch

            self._torch_available = True

            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                logger.info("Apple MPS disponible (Apple Silicon GPU)")
                return DeviceInfo(
                    device_type=DeviceType.MPS,
                    device_name="Apple Silicon GPU",
                    device_id=0,
                    memory_gb=None,  # Compartida con sistema
                    is_available=True,
                )
        except ImportError:
            logger.debug("PyTorch no instalado, MPS no disponible")
        except Exception as e:
            logger.warning(f"Error detectando MPS: {e}")

        return None

    def detect_cupy(self) -> bool:
        """Verifica si CuPy está disponible (para spaCy GPU)."""
        try:
            import cupy

            cupy.cuda.runtime.getDeviceCount()
            self._cupy_available = True
            logger.info("CuPy disponible para spaCy GPU")
            return True
        except ImportError:
            logger.debug("CuPy no instalado")
        except Exception as e:
            logger.warning(f"CuPy instalado pero CUDA no funcional: {e}")

        return False

    def get_cpu_info(self) -> DeviceInfo:
        """Retorna información del CPU como fallback."""
        cpu_name = platform.processor() or "CPU"

        return DeviceInfo(
            device_type=DeviceType.CPU,
            device_name=cpu_name,
            device_id=-1,
            memory_gb=None,
            is_available=True,
        )

    def detect_best_device(self, prefer: str = "auto") -> DeviceInfo:
        """
        Detecta el mejor dispositivo disponible.

        Args:
            prefer: Preferencia de dispositivo
                - "auto": Detectar automáticamente (GPU si disponible)
                - "cuda": Forzar CUDA (error si no disponible)
                - "mps": Forzar MPS (error si no disponible)
                - "cpu": Forzar CPU

        Returns:
            DeviceInfo con el dispositivo seleccionado

        Raises:
            RuntimeError: Si se fuerza un dispositivo no disponible
        """
        # Forzar CPU
        if prefer == "cpu":
            device = self.get_cpu_info()
            logger.info(f"Usando CPU (forzado): {device.device_name}")
            self._detected_device = device
            return device

        # Forzar CUDA
        if prefer == "cuda":
            device = self.detect_cuda()
            if device is None:
                raise RuntimeError(
                    "CUDA solicitado pero no disponible. "
                    "Instale PyTorch con CUDA: pip install torch --index-url https://download.pytorch.org/whl/cu121"
                )
            self._detected_device = device
            return device

        # Forzar MPS
        if prefer == "mps":
            device = self.detect_mps()
            if device is None:
                raise RuntimeError(
                    "MPS solicitado pero no disponible. Requiere macOS 12.3+ y Apple Silicon."
                )
            self._detected_device = device
            return device

        # Auto-detectar (prefer == "auto")
        # 1. Intentar CUDA
        cuda_device = self.detect_cuda()
        if cuda_device:
            self._detected_device = cuda_device
            return cuda_device

        # 2. Intentar MPS
        mps_device = self.detect_mps()
        if mps_device:
            self._detected_device = mps_device
            return mps_device

        # 3. Fallback a CPU
        cpu_device = self.get_cpu_info()
        logger.info(f"GPU no disponible, usando CPU: {cpu_device.device_name}")
        self._detected_device = cpu_device
        return cpu_device

    @property
    def current_device(self) -> DeviceInfo | None:
        """Dispositivo detectado actualmente."""
        return self._detected_device

    def get_torch_device(self) -> str:
        """
        Retorna string de dispositivo para PyTorch.

        Returns:
            "cuda", "mps", o "cpu"
        """
        if self._detected_device is None:
            self.detect_best_device()

        device_map = {
            DeviceType.CUDA: "cuda",
            DeviceType.MPS: "mps",
            DeviceType.CPU: "cpu",
        }
        return device_map[self._detected_device.device_type]

    def has_cupy_for_spacy(self) -> bool:
        """Indica si CuPy está disponible para spaCy."""
        if not hasattr(self, "_cupy_checked"):
            self._cupy_checked = self.detect_cupy()
        return self._cupy_available


# Singleton global
_device_detector: DeviceDetector | None = None


def get_device_detector() -> DeviceDetector:
    """Obtiene el detector de dispositivos singleton (thread-safe)."""
    global _device_detector
    if _device_detector is None:
        with _detector_lock:
            # Double-checked locking
            if _device_detector is None:
                _device_detector = DeviceDetector()
    return _device_detector


def reset_device_detector() -> None:
    """Resetea el detector singleton (thread-safe, para testing)."""
    global _device_detector
    with _detector_lock:
        _device_detector = None


def get_device(prefer: str = "auto") -> DeviceInfo:
    """
    Atajo para obtener el mejor dispositivo.

    Args:
        prefer: "auto", "cuda", "mps", o "cpu"

    Returns:
        DeviceInfo del dispositivo seleccionado
    """
    return get_device_detector().detect_best_device(prefer)


def get_torch_device_string(prefer: str = "auto") -> str:
    """
    Atajo para obtener string de dispositivo PyTorch.

    Args:
        prefer: "auto", "cuda", "mps", o "cpu"

    Returns:
        "cuda", "mps", o "cpu"
    """
    get_device(prefer)  # Asegurar detección
    return get_device_detector().get_torch_device()


def clear_gpu_memory() -> None:
    """
    Libera memoria GPU agresivamente.

    IMPORTANTE: Llamar esta función después de operaciones intensivas
    (embeddings, LLM, etc.) en sistemas con VRAM limitada para evitar
    saturación y posibles crashes/BSOD.
    """
    # Recolector de basura de Python primero
    gc.collect()

    # Limpiar caché CUDA si está disponible
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()  # Esperar a que termine todo
            logger.debug("GPU memory cache cleared (CUDA)")
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Error clearing CUDA memory: {e}")


def get_gpu_memory_usage() -> tuple[float, float] | None:
    """
    Obtiene uso actual de memoria GPU.

    Returns:
        Tuple (used_gb, total_gb) o None si no hay GPU
    """
    try:
        import torch

        if torch.cuda.is_available():
            device = torch.cuda.current_device()
            used = torch.cuda.memory_allocated(device) / (1024**3)
            total = torch.cuda.get_device_properties(device).total_memory / (1024**3)
            return (used, total)
    except Exception:
        pass
    return None


def is_gpu_memory_low(threshold_fraction: float = 0.85) -> bool:
    """
    Verifica si la GPU está cerca del límite de memoria.

    Args:
        threshold_fraction: Fracción de memoria usada para considerar "low" (default: 85%)

    Returns:
        True si la memoria está por encima del umbral
    """
    usage = get_gpu_memory_usage()
    if usage is None:
        return False
    used, total = usage
    return (used / total) > threshold_fraction


def get_safe_batch_size(default: int, device_info: DeviceInfo | None = None) -> int:
    """
    Obtiene un batch size seguro basado en la VRAM disponible.

    En sistemas con VRAM limitada (< 6GB), reduce el batch size para
    evitar saturación de memoria.

    Args:
        default: Batch size por defecto
        device_info: Info del dispositivo (auto-detecta si None)

    Returns:
        Batch size ajustado
    """
    if device_info is None:
        detector = get_device_detector()
        device_info = detector.current_device
        if device_info is None:
            return default

    # En CPU no hay restricción de VRAM
    if device_info.device_type == DeviceType.CPU:
        return default

    # Ajustar según VRAM
    if device_info.memory_gb:
        if device_info.memory_gb < 4:
            return max(4, default // 8)  # Muy poca VRAM
        elif device_info.memory_gb < 6:
            return max(8, default // 4)  # Poca VRAM (como Quadro M3000M)
        elif device_info.memory_gb < 8:
            return max(16, default // 2)  # VRAM media

    return default
