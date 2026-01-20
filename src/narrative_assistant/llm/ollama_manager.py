"""
Gestión de instalación bajo demanda de Ollama.

Este módulo proporciona:
1. Detección de Ollama instalado
2. Instalación automática bajo demanda (Windows, macOS, Linux)
3. Gestión del servicio (iniciar/verificar)
4. Gestión de modelos (descargar/listar)
5. Persistencia de modelos descargados

IMPORTANTE: Las descargas solo ocurren cuando el usuario las solicita explícitamente.
"""

import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Lock para thread-safety
_manager_lock = threading.Lock()
_manager: Optional["OllamaManager"] = None


class OllamaStatus(Enum):
    """Estado de Ollama."""

    NOT_INSTALLED = "not_installed"
    INSTALLED_NOT_RUNNING = "installed_not_running"
    RUNNING = "running"
    STARTING = "starting"
    ERROR = "error"


class InstallationPlatform(Enum):
    """Plataforma de instalación."""

    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    UNKNOWN = "unknown"


@dataclass
class OllamaModel:
    """Información de un modelo de Ollama."""

    name: str
    display_name: str
    size_gb: float
    description: str
    is_downloaded: bool = False
    is_default: bool = False


@dataclass
class DownloadProgress:
    """Progreso de descarga."""

    current_bytes: int = 0
    total_bytes: int = 0
    percentage: float = 0.0
    status: str = "pending"
    error: Optional[str] = None

    @property
    def is_complete(self) -> bool:
        """Verifica si la descarga está completa."""
        return self.status == "complete"

    @property
    def is_error(self) -> bool:
        """Verifica si hay error."""
        return self.status == "error"


@dataclass
class OllamaConfig:
    """Configuración del gestor de Ollama."""

    # URL del servidor Ollama
    host: str = "http://localhost:11434"

    # Timeout para operaciones de red (segundos)
    network_timeout: float = 30.0

    # Timeout para inicio del servicio (segundos)
    service_start_timeout: float = 60.0

    # Reintentos para operaciones de red
    network_retries: int = 3

    # Retraso entre reintentos (segundos)
    retry_delay: float = 2.0

    # Directorio para persistir estado
    state_dir: Optional[Path] = None

    # Forzar modo CPU
    force_cpu: bool = False


# Modelos disponibles
AVAILABLE_MODELS = [
    OllamaModel(
        name="llama3.2",
        display_name="Llama 3.2 (3B)",
        size_gb=2.0,
        description="Modelo rapido, buena calidad general. Funciona bien en CPU.",
        is_default=True,
    ),
    OllamaModel(
        name="qwen2.5",
        display_name="Qwen 2.5 (7B)",
        size_gb=4.4,
        description="Excelente para textos en espanol. Requiere mas recursos.",
    ),
    OllamaModel(
        name="mistral",
        display_name="Mistral (7B)",
        size_gb=4.1,
        description="Mayor calidad de razonamiento. Requiere mas recursos.",
    ),
    OllamaModel(
        name="gemma2",
        display_name="Gemma 2 (9B)",
        size_gb=5.4,
        description="Alta calidad, el mas lento. Requiere GPU o mucha RAM.",
    ),
]

# URLs de descarga de Ollama
OLLAMA_DOWNLOAD_URLS = {
    InstallationPlatform.WINDOWS: "https://ollama.com/download/OllamaSetup.exe",
    InstallationPlatform.MACOS: "https://ollama.com/download/Ollama-darwin.zip",
    InstallationPlatform.LINUX: "https://ollama.com/install.sh",
}


class OllamaManager:
    """
    Gestor de instalación y configuración de Ollama bajo demanda.

    Thread-safe. Proporciona:
    - Detección de instalación
    - Instalación automática
    - Gestión del servicio
    - Gestión de modelos
    - Persistencia de estado
    """

    def __init__(self, config: Optional[OllamaConfig] = None):
        """
        Inicializa el gestor.

        Args:
            config: Configuración opcional
        """
        self._config = config or OllamaConfig()
        self._lock = threading.Lock()
        self._status = OllamaStatus.NOT_INSTALLED
        self._downloaded_models: set[str] = set()
        self._platform = self._detect_platform()
        self._state_file: Optional[Path] = None

        # Configurar directorio de estado
        self._setup_state_dir()

        # Cargar estado persistido
        self._load_state()

        # Verificar estado inicial
        self._update_status()

    def _detect_platform(self) -> InstallationPlatform:
        """Detecta la plataforma actual."""
        system = platform.system().lower()
        if system == "windows":
            return InstallationPlatform.WINDOWS
        elif system == "darwin":
            return InstallationPlatform.MACOS
        elif system == "linux":
            return InstallationPlatform.LINUX
        return InstallationPlatform.UNKNOWN

    def _setup_state_dir(self) -> None:
        """Configura el directorio de estado."""
        if self._config.state_dir:
            state_dir = self._config.state_dir
        else:
            # Usar directorio de datos de la aplicacion
            try:
                from narrative_assistant.core.config import get_config
                app_config = get_config()
                state_dir = app_config.data_dir
            except Exception:
                state_dir = Path.home() / ".narrative_assistant"

        state_dir.mkdir(parents=True, exist_ok=True)
        self._state_file = state_dir / "ollama_state.json"

    def _load_state(self) -> None:
        """Carga el estado persistido."""
        if not self._state_file or not self._state_file.exists():
            return

        try:
            with open(self._state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._downloaded_models = set(data.get("downloaded_models", []))
            logger.debug(f"Estado cargado: {len(self._downloaded_models)} modelos registrados")
        except Exception as e:
            logger.debug(f"Error cargando estado: {e}")

    def _save_state(self) -> None:
        """Guarda el estado a disco."""
        if not self._state_file:
            return

        try:
            data = {
                "downloaded_models": list(self._downloaded_models),
                "platform": self._platform.value,
            }
            with open(self._state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.debug("Estado guardado")
        except Exception as e:
            logger.debug(f"Error guardando estado: {e}")

    def _update_status(self) -> None:
        """Actualiza el estado de Ollama."""
        if not self.is_installed:
            self._status = OllamaStatus.NOT_INSTALLED
        elif self.is_running:
            self._status = OllamaStatus.RUNNING
            # Actualizar lista de modelos descargados
            self._refresh_downloaded_models()
        else:
            self._status = OllamaStatus.INSTALLED_NOT_RUNNING

    @property
    def status(self) -> OllamaStatus:
        """Obtiene el estado actual de Ollama."""
        with self._lock:
            self._update_status()
            return self._status

    @property
    def is_installed(self) -> bool:
        """Verifica si Ollama esta instalado."""
        # Primero verificar en PATH
        if shutil.which("ollama") is not None:
            return True

        # En Windows, verificar rutas comunes de instalacion
        if self._platform == InstallationPlatform.WINDOWS:
            common_paths = [
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
                Path(os.environ.get("PROGRAMFILES", "")) / "Ollama" / "ollama.exe",
            ]
            for path in common_paths:
                if path.exists():
                    return True

        return False

    def _get_ollama_executable(self) -> str:
        """Obtiene la ruta del ejecutable de Ollama."""
        # Primero verificar en PATH
        which_result = shutil.which("ollama")
        if which_result:
            return which_result

        # En Windows, buscar en rutas comunes
        if self._platform == InstallationPlatform.WINDOWS:
            common_paths = [
                Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
                Path(os.environ.get("PROGRAMFILES", "")) / "Ollama" / "ollama.exe",
            ]
            for path in common_paths:
                if path.exists():
                    return str(path)

        return "ollama"  # Fallback al comando simple

    @property
    def is_running(self) -> bool:
        """Verifica si el servidor Ollama esta corriendo."""
        try:
            import httpx
            response = httpx.get(
                f"{self._config.host}/api/tags",
                timeout=self._config.network_timeout
            )
            return response.status_code == 200
        except ImportError:
            # Fallback a urllib si httpx no esta disponible
            try:
                req = urllib.request.Request(f"{self._config.host}/api/tags")
                with urllib.request.urlopen(req, timeout=self._config.network_timeout) as resp:
                    return resp.status == 200
            except Exception:
                return False
        except Exception:
            return False

    @property
    def platform(self) -> InstallationPlatform:
        """Obtiene la plataforma actual."""
        return self._platform

    @property
    def downloaded_models(self) -> list[str]:
        """Lista de modelos descargados."""
        return list(self._downloaded_models)

    @property
    def available_models(self) -> list[OllamaModel]:
        """Lista de modelos disponibles con estado de descarga."""
        models = []
        for model in AVAILABLE_MODELS:
            model_copy = OllamaModel(
                name=model.name,
                display_name=model.display_name,
                size_gb=model.size_gb,
                description=model.description,
                is_downloaded=model.name in self._downloaded_models,
                is_default=model.is_default,
            )
            models.append(model_copy)
        return models

    def _refresh_downloaded_models(self) -> None:
        """Actualiza la lista de modelos descargados desde Ollama."""
        if not self.is_running:
            return

        try:
            import httpx
            response = httpx.get(
                f"{self._config.host}/api/tags",
                timeout=self._config.network_timeout
            )
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                # Extraer nombres base (sin tag de version)
                downloaded = set()
                for m in models:
                    name = m.get("name", "")
                    base_name = name.split(":")[0]
                    if base_name:
                        downloaded.add(base_name)

                self._downloaded_models = downloaded
                self._save_state()
        except Exception as e:
            logger.debug(f"Error actualizando lista de modelos: {e}")

    def get_version(self) -> Optional[str]:
        """Obtiene la version de Ollama instalada."""
        if not self.is_installed:
            return None

        try:
            ollama_exe = self._get_ollama_executable()
            result = subprocess.run(
                [ollama_exe, "--version"],
                capture_output=True,
                text=True,
                timeout=10.0
            )
            if result.returncode == 0:
                # Parsear version del output
                output = result.stdout.strip()
                # Formato tipico: "ollama version 0.1.xx"
                if "version" in output.lower():
                    parts = output.split()
                    for i, part in enumerate(parts):
                        if part.lower() == "version" and i + 1 < len(parts):
                            return parts[i + 1]
                return output
        except Exception as e:
            logger.debug(f"Error obteniendo version: {e}")

        return None

    def check_installation_requirements(self) -> tuple[bool, str]:
        """
        Verifica si se puede instalar Ollama.

        Returns:
            Tupla (puede_instalar, mensaje)
        """
        if self._platform == InstallationPlatform.UNKNOWN:
            return False, "Plataforma no soportada para instalacion automatica"

        if self._platform == InstallationPlatform.LINUX:
            # Verificar que curl esta disponible
            if not shutil.which("curl"):
                return False, "Se requiere 'curl' para instalar en Linux"

        return True, "Listo para instalar"

    def install_ollama(
        self,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
        silent: bool = False,
    ) -> tuple[bool, str]:
        """
        Instala Ollama en el sistema.

        Args:
            progress_callback: Callback para reportar progreso
            silent: Si True, intenta instalacion silenciosa (Windows)

        Returns:
            Tupla (exito, mensaje)
        """
        with self._lock:
            if self.is_installed:
                return True, "Ollama ya esta instalado"

            can_install, msg = self.check_installation_requirements()
            if not can_install:
                return False, msg

            logger.info(f"Instalando Ollama en {self._platform.value}...")

            try:
                if self._platform == InstallationPlatform.WINDOWS:
                    return self._install_windows(progress_callback, silent)
                elif self._platform == InstallationPlatform.MACOS:
                    return self._install_macos(progress_callback)
                elif self._platform == InstallationPlatform.LINUX:
                    return self._install_linux(progress_callback)
                else:
                    return False, "Plataforma no soportada"
            except Exception as e:
                logger.error(f"Error instalando Ollama: {e}")
                return False, f"Error de instalacion: {e}"

    def _install_windows(
        self,
        progress_callback: Optional[Callable[[DownloadProgress], None]],
        silent: bool,
    ) -> tuple[bool, str]:
        """Instala Ollama en Windows."""
        # Descargar instalador
        installer_path = Path(tempfile.gettempdir()) / "OllamaSetup.exe"

        download_url = OLLAMA_DOWNLOAD_URLS[InstallationPlatform.WINDOWS]
        success = self._download_file(download_url, installer_path, progress_callback)

        if not success:
            return False, "Error descargando instalador"

        # Ejecutar instalador
        try:
            if silent:
                # Intentar instalacion silenciosa
                result = subprocess.run(
                    [str(installer_path), "/S"],
                    capture_output=True,
                    timeout=300.0  # 5 minutos
                )
                if result.returncode != 0:
                    # Fallback a instalacion interactiva
                    subprocess.run([str(installer_path)], check=True)
            else:
                subprocess.run([str(installer_path)], check=True)

            # Esperar a que se registre en PATH
            time.sleep(2)

            # Verificar instalacion
            if self.is_installed:
                logger.info("Ollama instalado correctamente")
                return True, "Ollama instalado correctamente"
            else:
                return False, "Instalacion completa pero 'ollama' no esta en PATH. Reinicia la terminal."

        except subprocess.TimeoutExpired:
            return False, "Timeout durante la instalacion"
        except subprocess.CalledProcessError as e:
            return False, f"Error ejecutando instalador: {e}"
        finally:
            # Limpiar instalador
            try:
                installer_path.unlink()
            except Exception:
                pass

    def _install_macos(
        self,
        progress_callback: Optional[Callable[[DownloadProgress], None]],
    ) -> tuple[bool, str]:
        """Instala Ollama en macOS."""
        # Intentar con Homebrew primero
        if shutil.which("brew"):
            try:
                logger.info("Instalando via Homebrew...")
                result = subprocess.run(
                    ["brew", "install", "ollama"],
                    capture_output=True,
                    text=True,
                    timeout=600.0  # 10 minutos
                )
                if result.returncode == 0:
                    return True, "Ollama instalado via Homebrew"
            except Exception as e:
                logger.debug(f"Homebrew fallo: {e}")

        # Fallback: descarga directa
        download_url = OLLAMA_DOWNLOAD_URLS[InstallationPlatform.MACOS]
        zip_path = Path(tempfile.gettempdir()) / "Ollama-darwin.zip"

        success = self._download_file(download_url, zip_path, progress_callback)
        if not success:
            return False, "Error descargando Ollama"

        try:
            # Extraer y mover a Applications
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tempfile.gettempdir())

            # Mover a /Applications
            app_source = Path(tempfile.gettempdir()) / "Ollama.app"
            app_dest = Path("/Applications/Ollama.app")

            if app_dest.exists():
                shutil.rmtree(app_dest)
            shutil.move(str(app_source), str(app_dest))

            return True, "Ollama instalado en /Applications. Ejecuta la app para completar."

        except Exception as e:
            return False, f"Error instalando: {e}"
        finally:
            try:
                zip_path.unlink()
            except Exception:
                pass

    def _install_linux(
        self,
        progress_callback: Optional[Callable[[DownloadProgress], None]],
    ) -> tuple[bool, str]:
        """Instala Ollama en Linux usando el script oficial."""
        try:
            # Descargar script
            if progress_callback:
                progress_callback(DownloadProgress(status="downloading"))

            result = subprocess.run(
                ["curl", "-fsSL", "https://ollama.com/install.sh"],
                capture_output=True,
                text=True,
                timeout=60.0
            )

            if result.returncode != 0:
                return False, f"Error descargando script: {result.stderr}"

            install_script = result.stdout

            # Ejecutar script
            if progress_callback:
                progress_callback(DownloadProgress(status="installing"))

            process = subprocess.Popen(
                ["sh"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            stdout, _ = process.communicate(input=install_script, timeout=600.0)

            if process.returncode == 0:
                if progress_callback:
                    progress_callback(DownloadProgress(status="complete", percentage=100.0))
                return True, "Ollama instalado correctamente"
            else:
                return False, f"Error en script de instalacion: {stdout}"

        except subprocess.TimeoutExpired:
            return False, "Timeout durante la instalacion"
        except Exception as e:
            return False, f"Error: {e}"

    def _download_file(
        self,
        url: str,
        dest: Path,
        progress_callback: Optional[Callable[[DownloadProgress], None]],
    ) -> bool:
        """Descarga un archivo con reporte de progreso."""
        progress = DownloadProgress(status="downloading")

        def report_hook(block_num: int, block_size: int, total_size: int) -> None:
            progress.current_bytes = block_num * block_size
            progress.total_bytes = total_size
            if total_size > 0:
                progress.percentage = min(100.0, progress.current_bytes * 100.0 / total_size)
            if progress_callback:
                progress_callback(progress)

        for attempt in range(self._config.network_retries):
            try:
                urllib.request.urlretrieve(url, dest, report_hook)
                progress.status = "complete"
                progress.percentage = 100.0
                if progress_callback:
                    progress_callback(progress)
                return True
            except Exception as e:
                logger.debug(f"Intento {attempt + 1} fallido: {e}")
                if attempt < self._config.network_retries - 1:
                    time.sleep(self._config.retry_delay)

        progress.status = "error"
        progress.error = "Descarga fallida despues de varios intentos"
        if progress_callback:
            progress_callback(progress)
        return False

    def start_service(self, force_cpu: bool = False) -> tuple[bool, str]:
        """
        Inicia el servicio de Ollama.

        Args:
            force_cpu: Si True, fuerza modo CPU (util en Windows con GPUs viejas)

        Returns:
            Tupla (exito, mensaje)
        """
        with self._lock:
            if not self.is_installed:
                return False, "Ollama no esta instalado"

            if self.is_running:
                return True, "Ollama ya esta corriendo"

            self._status = OllamaStatus.STARTING

            try:
                env = os.environ.copy()

                # Configurar modo CPU si se solicita
                if force_cpu or self._config.force_cpu:
                    env["CUDA_VISIBLE_DEVICES"] = "-1"
                    env["OLLAMA_GPU_OVERHEAD"] = "0"
                    env["OLLAMA_GPU_LAYERS"] = "0"
                    env["OLLAMA_NUM_GPU"] = "0"

                # Obtener ruta del ejecutable
                ollama_exe = self._get_ollama_executable()
                logger.info(f"Iniciando Ollama: {ollama_exe}")

                if self._platform == InstallationPlatform.WINDOWS:
                    # Windows: iniciar en segundo plano
                    subprocess.Popen(
                        [ollama_exe, "serve"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        env=env,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                else:
                    # Linux/macOS: iniciar en nueva sesion
                    subprocess.Popen(
                        [ollama_exe, "serve"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        env=env,
                        start_new_session=True
                    )

                # Esperar a que inicie
                start_time = time.time()
                while time.time() - start_time < self._config.service_start_timeout:
                    time.sleep(1)
                    if self.is_running:
                        self._status = OllamaStatus.RUNNING
                        self._refresh_downloaded_models()
                        logger.info("Servicio Ollama iniciado")
                        return True, "Servicio iniciado correctamente"

                self._status = OllamaStatus.ERROR
                return False, f"Timeout esperando que Ollama inicie ({self._config.service_start_timeout}s)"

            except FileNotFoundError:
                self._status = OllamaStatus.NOT_INSTALLED
                return False, "Comando 'ollama' no encontrado"
            except Exception as e:
                self._status = OllamaStatus.ERROR
                return False, f"Error iniciando servicio: {e}"

    def ensure_running(self, force_cpu: bool = False) -> tuple[bool, str]:
        """
        Asegura que Ollama este corriendo.

        Si no esta instalado, retorna False.
        Si esta instalado pero no corriendo, intenta iniciarlo.

        Args:
            force_cpu: Si True, fuerza modo CPU

        Returns:
            Tupla (exito, mensaje)
        """
        if not self.is_installed:
            return False, "Ollama no esta instalado"

        if self.is_running:
            return True, "Ollama esta corriendo"

        return self.start_service(force_cpu)

    def download_model(
        self,
        model_name: str,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
    ) -> tuple[bool, str]:
        """
        Descarga un modelo de Ollama.

        Args:
            model_name: Nombre del modelo (ej: "llama3.2")
            progress_callback: Callback para reportar progreso

        Returns:
            Tupla (exito, mensaje)
        """
        # Verificar que el modelo es valido
        valid_models = [m.name for m in AVAILABLE_MODELS]
        if model_name not in valid_models:
            return False, f"Modelo desconocido: {model_name}. Disponibles: {valid_models}"

        # Asegurar que Ollama esta corriendo
        success, msg = self.ensure_running()
        if not success:
            return False, f"No se puede descargar: {msg}"

        # Verificar si ya esta descargado
        if model_name in self._downloaded_models:
            return True, f"Modelo {model_name} ya esta descargado"

        logger.info(f"Descargando modelo {model_name}...")
        progress = DownloadProgress(status="downloading")

        try:
            ollama_exe = self._get_ollama_executable()
            process = subprocess.Popen(
                [ollama_exe, "pull", model_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            for line in process.stdout:
                line = line.strip()
                logger.debug(f"ollama pull: {line}")

                # Parsear progreso si es posible
                if "%" in line:
                    try:
                        # Formato tipico: "pulling... 45%"
                        parts = line.split()
                        for part in parts:
                            if "%" in part:
                                pct = float(part.replace("%", ""))
                                progress.percentage = pct
                                if progress_callback:
                                    progress_callback(progress)
                                break
                    except Exception:
                        pass

            process.wait()

            if process.returncode == 0:
                self._downloaded_models.add(model_name)
                self._save_state()
                progress.status = "complete"
                progress.percentage = 100.0
                if progress_callback:
                    progress_callback(progress)
                logger.info(f"Modelo {model_name} descargado correctamente")
                return True, f"Modelo {model_name} descargado"
            else:
                progress.status = "error"
                progress.error = "Error en ollama pull"
                if progress_callback:
                    progress_callback(progress)
                return False, "Error descargando modelo"

        except Exception as e:
            progress.status = "error"
            progress.error = str(e)
            if progress_callback:
                progress_callback(progress)
            return False, f"Error: {e}"

    def is_model_available(self, model_name: str) -> bool:
        """Verifica si un modelo esta disponible para usar."""
        self._refresh_downloaded_models()
        return model_name in self._downloaded_models

    def delete_model(self, model_name: str) -> tuple[bool, str]:
        """
        Elimina un modelo descargado.

        Args:
            model_name: Nombre del modelo

        Returns:
            Tupla (exito, mensaje)
        """
        if not self.is_running:
            return False, "Ollama no esta corriendo"

        try:
            ollama_exe = self._get_ollama_executable()
            result = subprocess.run(
                [ollama_exe, "rm", model_name],
                capture_output=True,
                text=True,
                timeout=60.0
            )

            if result.returncode == 0:
                self._downloaded_models.discard(model_name)
                self._save_state()
                return True, f"Modelo {model_name} eliminado"
            else:
                return False, f"Error eliminando modelo: {result.stderr}"

        except Exception as e:
            return False, f"Error: {e}"

    def get_model_info(self, model_name: str) -> Optional[OllamaModel]:
        """Obtiene informacion de un modelo."""
        for model in AVAILABLE_MODELS:
            if model.name == model_name:
                return OllamaModel(
                    name=model.name,
                    display_name=model.display_name,
                    size_gb=model.size_gb,
                    description=model.description,
                    is_downloaded=model_name in self._downloaded_models,
                    is_default=model.is_default,
                )
        return None


def get_ollama_manager(config: Optional[OllamaConfig] = None) -> OllamaManager:
    """
    Obtiene el gestor de Ollama singleton (thread-safe).

    Args:
        config: Configuracion opcional (solo se usa en la primera llamada)

    Returns:
        Instancia del gestor
    """
    global _manager

    if _manager is None:
        with _manager_lock:
            # Double-checked locking
            if _manager is None:
                _manager = OllamaManager(config)

    return _manager


def reset_ollama_manager() -> None:
    """Resetea el gestor singleton (para testing)."""
    global _manager
    with _manager_lock:
        _manager = None


# Funciones de conveniencia

def is_ollama_available() -> bool:
    """Verifica si Ollama esta instalado y corriendo."""
    manager = get_ollama_manager()
    return manager.is_running


def ensure_ollama_ready(
    install_if_missing: bool = False,
    start_if_stopped: bool = True,
    force_cpu: bool = False,
) -> tuple[bool, str]:
    """
    Asegura que Ollama este listo para usar.

    Args:
        install_if_missing: Si True, instala Ollama si no esta
        start_if_stopped: Si True, inicia el servicio si esta detenido
        force_cpu: Si True, fuerza modo CPU

    Returns:
        Tupla (exito, mensaje)
    """
    manager = get_ollama_manager()

    # Verificar instalacion
    if not manager.is_installed:
        if install_if_missing:
            success, msg = manager.install_ollama()
            if not success:
                return False, msg
        else:
            return False, "Ollama no esta instalado"

    # Verificar servicio
    if not manager.is_running:
        if start_if_stopped:
            success, msg = manager.start_service(force_cpu)
            if not success:
                return False, msg
        else:
            return False, "El servicio Ollama no esta corriendo"

    return True, "Ollama listo"


def get_available_llm_models() -> list[OllamaModel]:
    """Obtiene la lista de modelos LLM disponibles."""
    manager = get_ollama_manager()
    return manager.available_models


def download_llm_model(
    model_name: str,
    progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
) -> tuple[bool, str]:
    """
    Descarga un modelo LLM.

    Args:
        model_name: Nombre del modelo
        progress_callback: Callback de progreso

    Returns:
        Tupla (exito, mensaje)
    """
    manager = get_ollama_manager()
    return manager.download_model(model_name, progress_callback)
