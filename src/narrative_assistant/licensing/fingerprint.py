"""
Sistema de fingerprinting de hardware para vinculacion de dispositivos.

Genera un identificador unico y estable basado en caracteristicas
del hardware del sistema, permitiendo vincular licencias a maquinas
especificas.

Caracteristicas consideradas:
- CPU: modelo, numero de nucleos
- Memoria: cantidad total
- Disco: identificador del disco principal
- Sistema: hostname, MAC address (parcial)
- Plataforma: OS y arquitectura

SEGURIDAD: El fingerprint es un hash one-way, no permite reconstruir
la informacion original del hardware.
"""

import hashlib
import logging
import platform
import socket
import subprocess
import sys
import uuid
from dataclasses import dataclass
from typing import Optional

from ..core.result import Result
from ..core.errors import NarrativeError, ErrorSeverity

logger = logging.getLogger(__name__)


@dataclass
class HardwareInfo:
    """
    Informacion de hardware recolectada para el fingerprint.

    Attributes:
        cpu_model: Modelo del procesador
        cpu_cores: Numero de nucleos fisicos
        cpu_threads: Numero de threads
        memory_total_gb: Memoria RAM total en GB
        disk_serial: Serial del disco principal (parcial)
        mac_address: MAC address (parcial, ultimos 6 chars)
        hostname: Nombre del equipo
        os_name: Nombre del sistema operativo
        os_version: Version del sistema operativo
        architecture: Arquitectura (x64, arm64, etc.)
        machine_id: ID unico de la maquina (si disponible)
    """

    cpu_model: str = ""
    cpu_cores: int = 0
    cpu_threads: int = 0
    memory_total_gb: float = 0.0
    disk_serial: str = ""
    mac_address: str = ""
    hostname: str = ""
    os_name: str = ""
    os_version: str = ""
    architecture: str = ""
    machine_id: str = ""

    def to_fingerprint_string(self) -> str:
        """
        Genera string para hashing.

        Usa solo componentes estables que no cambian frecuentemente.
        """
        # Componentes mas estables (peso mayor)
        stable_parts = [
            self.cpu_model,
            str(self.cpu_cores),
            self.disk_serial,
            self.machine_id,
        ]

        # Componentes semi-estables
        semi_stable_parts = [
            self.mac_address,
            self.architecture,
            self.os_name,
        ]

        # Combinar con separador unico
        fingerprint_data = "|".join(stable_parts + semi_stable_parts)
        return fingerprint_data

    @property
    def device_name(self) -> str:
        """Nombre amigable del dispositivo."""
        return f"{self.hostname} ({self.os_name})"

    @property
    def os_info(self) -> str:
        """Informacion del sistema operativo."""
        return f"{self.os_name} {self.os_version} ({self.architecture})"


class HardwareDetector:
    """Detecta informacion del hardware del sistema."""

    def __init__(self):
        self._cached_info: Optional[HardwareInfo] = None

    def detect(self) -> HardwareInfo:
        """
        Detecta y retorna informacion del hardware.

        Returns:
            HardwareInfo con datos del sistema actual
        """
        if self._cached_info is not None:
            return self._cached_info

        info = HardwareInfo()

        # Informacion basica de plataforma
        info.os_name = platform.system()
        info.os_version = platform.release()
        info.architecture = platform.machine()
        info.hostname = socket.gethostname()

        # CPU
        info.cpu_model = self._get_cpu_model()
        info.cpu_cores = self._get_cpu_cores()
        info.cpu_threads = self._get_cpu_threads()

        # Memoria
        info.memory_total_gb = self._get_memory_total()

        # Disco
        info.disk_serial = self._get_disk_serial()

        # MAC Address (parcial para privacidad)
        info.mac_address = self._get_mac_address()

        # Machine ID
        info.machine_id = self._get_machine_id()

        self._cached_info = info
        return info

    def _get_cpu_model(self) -> str:
        """Obtiene el modelo del CPU."""
        try:
            if sys.platform == "win32":
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
                )
                value, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                return value.strip()
            elif sys.platform == "darwin":
                result = subprocess.run(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return result.stdout.strip()
            else:  # Linux
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if "model name" in line:
                            return line.split(":")[1].strip()
        except Exception as e:
            logger.debug(f"No se pudo obtener modelo CPU: {e}")
        return platform.processor() or "Unknown"

    def _get_cpu_cores(self) -> int:
        """Obtiene el numero de nucleos fisicos."""
        try:
            import os
            # Nucleos fisicos, no threads
            if hasattr(os, "cpu_count"):
                return os.cpu_count() // 2 or 1
        except Exception as e:
            logger.debug(f"No se pudo obtener nucleos CPU: {e}")
        return 1

    def _get_cpu_threads(self) -> int:
        """Obtiene el numero de threads."""
        try:
            import os
            return os.cpu_count() or 1
        except Exception as e:
            logger.debug(f"No se pudo obtener threads CPU: {e}")
        return 1

    def _get_memory_total(self) -> float:
        """Obtiene la memoria RAM total en GB."""
        try:
            if sys.platform == "win32":
                import ctypes
                kernel32 = ctypes.windll.kernel32
                c_ulong = ctypes.c_ulong
                class MEMORYSTATUS(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", c_ulong),
                        ("dwMemoryLoad", c_ulong),
                        ("dwTotalPhys", c_ulong),
                        ("dwAvailPhys", c_ulong),
                        ("dwTotalPageFile", c_ulong),
                        ("dwAvailPageFile", c_ulong),
                        ("dwTotalVirtual", c_ulong),
                        ("dwAvailVirtual", c_ulong),
                    ]
                mem_status = MEMORYSTATUS()
                mem_status.dwLength = ctypes.sizeof(MEMORYSTATUS)
                kernel32.GlobalMemoryStatus(ctypes.byref(mem_status))
                return round(mem_status.dwTotalPhys / (1024**3), 1)
            elif sys.platform == "darwin":
                result = subprocess.run(
                    ["sysctl", "-n", "hw.memsize"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return round(int(result.stdout.strip()) / (1024**3), 1)
            else:  # Linux
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if "MemTotal" in line:
                            kb = int(line.split()[1])
                            return round(kb / (1024**2), 1)
        except Exception as e:
            logger.debug(f"No se pudo obtener memoria total: {e}")
        return 0.0

    def _get_disk_serial(self) -> str:
        """
        Obtiene identificador del disco principal (parcial).

        Retorna solo los ultimos 8 caracteres para privacidad.
        """
        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    ["wmic", "diskdrive", "get", "serialnumber"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:
                    serial = lines[1].strip()
                    return serial[-8:] if len(serial) > 8 else serial
            elif sys.platform == "darwin":
                result = subprocess.run(
                    ["system_profiler", "SPStorageDataType"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                for line in result.stdout.split("\n"):
                    if "BSD Name" in line or "Volume UUID" in line:
                        parts = line.split(":")
                        if len(parts) > 1:
                            value = parts[1].strip()
                            return value[-8:] if len(value) > 8 else value
            else:  # Linux
                # Intentar con lsblk
                result = subprocess.run(
                    ["lsblk", "-d", "-o", "SERIAL", "-n"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                serial = result.stdout.strip().split("\n")[0]
                if serial:
                    return serial[-8:] if len(serial) > 8 else serial
        except Exception as e:
            logger.debug(f"No se pudo obtener serial del disco: {e}")
        return ""

    def _get_mac_address(self) -> str:
        """
        Obtiene la MAC address (parcial para privacidad).

        Retorna solo los ultimos 6 caracteres.
        """
        try:
            mac = uuid.getnode()
            mac_str = ":".join(f"{(mac >> i) & 0xff:02x}" for i in range(0, 48, 8))
            # Solo ultimos 6 caracteres (2 octetos)
            return mac_str[-8:].replace(":", "")
        except Exception as e:
            logger.debug(f"No se pudo obtener MAC address: {e}")
        return ""

    def _get_machine_id(self) -> str:
        """
        Obtiene el ID unico de la maquina.

        En Windows: ProductId del registro
        En Linux: /etc/machine-id
        En macOS: IOPlatformUUID
        """
        try:
            if sys.platform == "win32":
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
                )
                value, _ = winreg.QueryValueEx(key, "ProductId")
                return value
            elif sys.platform == "darwin":
                result = subprocess.run(
                    ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                for line in result.stdout.split("\n"):
                    if "IOPlatformUUID" in line:
                        # Formato: "IOPlatformUUID" = "XXXX-XXXX-..."
                        parts = line.split('"')
                        if len(parts) >= 4:
                            return parts[3]
            else:  # Linux
                try:
                    with open("/etc/machine-id", "r") as f:
                        return f.read().strip()
                except FileNotFoundError:
                    with open("/var/lib/dbus/machine-id", "r") as f:
                        return f.read().strip()
        except Exception as e:
            logger.debug(f"No se pudo obtener machine ID: {e}")
        return ""


class FingerprintGenerator:
    """
    Genera fingerprints de hardware.

    El fingerprint es un hash SHA-256 de caracteristicas del hardware,
    disenado para ser:
    - Unico: diferente para cada maquina
    - Estable: no cambia con actualizaciones menores
    - Privado: no permite reconstruir info del hardware
    """

    # Salt para el hash (no secreto, solo para evitar ataques de diccionario)
    SALT = "narrative_assistant_v1_"

    def __init__(self):
        self._detector = HardwareDetector()

    def generate(self) -> tuple[str, HardwareInfo]:
        """
        Genera fingerprint del hardware actual.

        Returns:
            Tupla de (fingerprint_hash, hardware_info)
        """
        info = self._detector.detect()
        fingerprint_data = self.SALT + info.to_fingerprint_string()

        # Hash SHA-256
        fingerprint_hash = hashlib.sha256(
            fingerprint_data.encode("utf-8")
        ).hexdigest()

        logger.debug(f"Fingerprint generado: {fingerprint_hash[:16]}...")

        return fingerprint_hash, info

    def generate_short(self) -> str:
        """
        Genera fingerprint corto (primeros 32 caracteres).

        Util para display y comparaciones rapidas.
        """
        full_hash, _ = self.generate()
        return full_hash[:32]


# =============================================================================
# Funciones publicas
# =============================================================================


def get_hardware_fingerprint() -> Result[str]:
    """
    Obtiene el fingerprint de hardware del dispositivo actual.

    Returns:
        Result con el fingerprint o error si falla la deteccion
    """
    try:
        generator = FingerprintGenerator()
        fingerprint, info = generator.generate()

        logger.info(
            f"Hardware fingerprint generado para {info.device_name}: "
            f"{fingerprint[:16]}..."
        )

        return Result.success(fingerprint)

    except Exception as e:
        error = NarrativeError(
            message=f"Error generating hardware fingerprint: {e}",
            severity=ErrorSeverity.FATAL,
            user_message=(
                "No se pudo identificar el hardware del dispositivo. "
                "Esto puede ocurrir en entornos virtualizados o contenedores."
            ),
            context={"error": str(e)},
        )
        return Result.failure(error)


def get_hardware_info() -> Result[HardwareInfo]:
    """
    Obtiene informacion detallada del hardware.

    Returns:
        Result con HardwareInfo o error si falla la deteccion
    """
    try:
        detector = HardwareDetector()
        info = detector.detect()
        return Result.success(info)

    except Exception as e:
        error = NarrativeError(
            message=f"Error detecting hardware info: {e}",
            severity=ErrorSeverity.RECOVERABLE,
            user_message="No se pudo obtener toda la informacion del hardware.",
            context={"error": str(e)},
        )
        return Result.failure(error)


def verify_fingerprint(expected: str) -> Result[bool]:
    """
    Verifica si el fingerprint actual coincide con el esperado.

    Args:
        expected: Fingerprint esperado

    Returns:
        Result con True si coincide, False si no, o error
    """
    result = get_hardware_fingerprint()
    if result.is_failure:
        return result

    current = result.value
    matches = current == expected

    if not matches:
        logger.warning(
            f"Fingerprint mismatch: expected {expected[:16]}..., "
            f"got {current[:16]}..."
        )

    return Result.success(matches)


def get_device_display_info() -> dict:
    """
    Obtiene informacion del dispositivo para mostrar al usuario.

    Returns:
        Dict con nombre, OS info, y fingerprint parcial
    """
    try:
        generator = FingerprintGenerator()
        fingerprint, info = generator.generate()

        return {
            "device_name": info.device_name,
            "os_info": info.os_info,
            "fingerprint_short": fingerprint[:16] + "...",
            "cpu": info.cpu_model,
            "memory_gb": info.memory_total_gb,
        }
    except Exception as e:
        logger.warning(f"No se pudo obtener info del dispositivo: {e}")
        return {
            "device_name": socket.gethostname(),
            "os_info": f"{platform.system()} {platform.release()}",
            "fingerprint_short": "Error",
            "cpu": "Unknown",
            "memory_gb": 0,
        }
