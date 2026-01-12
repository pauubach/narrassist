"""
Módulo de detección y gestión de dispositivos de cómputo (CPU/GPU).

Soporta:
- NVIDIA CUDA (Linux/Windows)
- Apple Metal (MPS) en Apple Silicon
- Fallback automático a CPU
"""

import logging
import platform
import threading
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

logger = logging.getLogger(__name__)

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
    memory_gb: Optional[float]  # Memoria disponible si se puede detectar
    is_available: bool

    def __str__(self) -> str:
        mem_str = f", {self.memory_gb:.1f}GB" if self.memory_gb else ""
        return f"{self.device_type.name}: {self.device_name}{mem_str}"


class DeviceDetector:
    """
    Detecta y selecciona el mejor dispositivo disponible.

    Orden de preferencia:
    1. CUDA (si disponible y no deshabilitado)
    2. MPS (Apple Silicon, si disponible)
    3. CPU (siempre disponible)
    """

    def __init__(self):
        self._detected_device: Optional[DeviceInfo] = None
        self._torch_available: bool = False
        self._cupy_available: bool = False

    def detect_cuda(self) -> Optional[DeviceInfo]:
        """Detecta GPU NVIDIA con CUDA."""
        try:
            import torch

            self._torch_available = True

            if torch.cuda.is_available():
                device_id = 0  # Usar primera GPU por defecto
                device_name = torch.cuda.get_device_name(device_id)
                memory_gb = torch.cuda.get_device_properties(device_id).total_memory / (
                    1024**3
                )

                logger.info(f"CUDA disponible: {device_name} ({memory_gb:.1f} GB)")
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

    def detect_mps(self) -> Optional[DeviceInfo]:
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
                    "MPS solicitado pero no disponible. "
                    "Requiere macOS 12.3+ y Apple Silicon."
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
    def current_device(self) -> Optional[DeviceInfo]:
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
_device_detector: Optional[DeviceDetector] = None


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
