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

import contextlib
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

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
    STOPPED = "stopped"
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
    min_ram_gb: float = 4.0  # RAM mínima recomendada
    is_core: bool = False  # Modelo principal (vs fallback)
    is_legacy: bool = False  # Modelo reemplazado por uno mejor
    benchmark_toks: float | None = None  # tok/s medido (post-descarga)


@dataclass
class DownloadProgress:
    """Progreso de descarga."""

    current_bytes: int = 0
    total_bytes: int = 0
    percentage: float = 0.0
    status: str = "pending"
    error: str | None = None

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
    state_dir: Path | None = None

    # Forzar modo CPU
    force_cpu: bool = False


# Modelos disponibles — core (votación), fallback y legacy
AVAILABLE_MODELS = [
    # === Modelos Core (votación por roles) ===
    OllamaModel(
        name="qwen3",
        display_name="Qwen 3 (14B)",
        size_gb=8.5,
        description="Motor de idioma: comprension profunda del espanol y razonamiento.",
        is_core=True,
        min_ram_gb=12.0,
    ),
    OllamaModel(
        name="hermes3",
        display_name="Hermes 3 (8B)",
        size_gb=4.7,
        description="Motor de personajes: analisis narrativo, voz y estilo literario.",
        is_core=True,
        min_ram_gb=8.0,
    ),
    OllamaModel(
        name="deepseek-r1",
        display_name="DeepSeek-R1 (7B)",
        size_gb=4.4,
        description="Motor de razonamiento: logica temporal, causal y deductiva.",
        is_core=True,
        min_ram_gb=8.0,
    ),
    # === Modelos Fallback ===
    OllamaModel(
        name="llama3.2",
        display_name="Llama 3.2 (3B)",
        size_gb=2.0,
        description="Modelo ligero universal. Funciona bien en CPU.",
        is_default=True,
        min_ram_gb=4.0,
    ),
    OllamaModel(
        name="qwen2.5",
        display_name="Qwen 2.5 (7B)",
        size_gb=4.4,
        description="Alternativa para espanol cuando Qwen 3 no cabe en memoria.",
        min_ram_gb=8.0,
    ),
    OllamaModel(
        name="gemma2",
        display_name="Gemma 2 (9B)",
        size_gb=5.4,
        description="Alternativa narrativa. Requiere GPU o mucha RAM.",
        min_ram_gb=10.0,
    ),
    # === Legacy (reemplazado por Hermes 3) ===
    OllamaModel(
        name="mistral",
        display_name="Mistral (7B)",
        size_gb=4.1,
        description="Reemplazado por Hermes 3. Disponible como fallback de razonamiento.",
        is_legacy=True,
        min_ram_gb=8.0,
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

    def __init__(self, config: OllamaConfig | None = None):
        """
        Inicializa el gestor.

        Args:
            config: Configuración opcional
        """
        self._config = config or OllamaConfig()

        # A-12: Validar URL del host (solo localhost permitido por seguridad)
        self._validate_host_url(self._config.host)

        self._lock = threading.Lock()
        self._status = OllamaStatus.NOT_INSTALLED
        self._downloaded_models: set[str] = set()
        self._platform = self._detect_platform()
        self._state_file: Path | None = None
        self._download_progress: DownloadProgress | None = None
        self._downloading_model: str | None = None

        # Configurar directorio de estado
        self._setup_state_dir()

        # Cargar estado persistido
        self._load_state()

        # Verificar estado inicial
        self._update_status()

    @staticmethod
    def _validate_host_url(host: str) -> None:
        """Valida que la URL del host sea segura (A-12: solo localhost)."""
        import urllib.parse as urlparse

        try:
            parsed = urlparse.urlparse(host)
        except Exception:
            raise ValueError(f"URL de host inválida: {host}")

        # Solo permitir esquemas http/https
        if parsed.scheme not in ("http", "https"):
            raise ValueError(
                f"Esquema no permitido en host Ollama: {parsed.scheme}. "
                "Solo http/https están permitidos."
            )

        # Solo permitir conexiones a localhost (seguridad: manuscritos no salen)
        allowed_hosts = {"localhost", "127.0.0.1", "::1", "[::1]"}
        hostname = (parsed.hostname or "").lower()
        if hostname not in allowed_hosts:
            raise ValueError(
                f"Host no permitido: {hostname}. "
                "Ollama solo puede conectar a localhost por seguridad."
            )

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
        """Configura el directorio de estado (A-04: validación con pathlib)."""
        if self._config.state_dir:
            state_dir = Path(self._config.state_dir).resolve()
        else:
            # Usar directorio de datos de la aplicacion
            try:
                from narrative_assistant.core.config import get_config

                app_config = get_config()
                state_dir = Path(app_config.data_dir).resolve()
            except Exception:
                state_dir = Path.home() / ".narrative_assistant"

        # Validar que la ruta es absoluta y no contiene componentes sospechosos
        if not state_dir.is_absolute():
            logger.warning(f"state_dir no es absoluto, usando default: {state_dir}")
            state_dir = Path.home() / ".narrative_assistant"

        state_dir.mkdir(parents=True, exist_ok=True)
        self._state_file = state_dir / "ollama_state.json"

    def _load_state(self) -> None:
        """Carga el estado persistido."""
        if not self._state_file or not self._state_file.exists():
            return

        try:
            with open(self._state_file, encoding="utf-8") as f:
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

    def _get_windows_common_paths(self) -> list[Path]:
        """Rutas comunes de instalación de Ollama en Windows (A-04: centralizado)."""
        paths: list[Path] = []
        for env_var in ("LOCALAPPDATA", "PROGRAMFILES"):
            raw = os.environ.get(env_var, "")
            if not raw:
                continue
            # Validar que el directorio base existe antes de construir la ruta
            base = Path(raw)
            if base.is_absolute() and base.is_dir():
                paths.append(base / "Programs" / "Ollama" / "ollama.exe")
        return paths

    @property
    def is_installed(self) -> bool:
        """Verifica si Ollama esta instalado."""
        # Primero verificar en PATH
        if shutil.which("ollama") is not None:
            return True

        # En Windows, verificar rutas comunes de instalacion
        if self._platform == InstallationPlatform.WINDOWS:
            for path in self._get_windows_common_paths():
                if path.exists():
                    return True

        return False

    def _get_ollama_executable(self) -> str:
        """Obtiene la ruta del ejecutable de Ollama."""
        # Primero verificar en PATH
        which_result = shutil.which("ollama")
        if which_result:
            return which_result

        # En Windows, buscar en rutas comunes (A-04: reutiliza método centralizado)
        if self._platform == InstallationPlatform.WINDOWS:
            for path in self._get_windows_common_paths():
                if path.exists():
                    return str(path)

        return "ollama"  # Fallback al comando simple

    @property
    def is_running(self) -> bool:
        """Verifica si el servidor Ollama esta corriendo."""
        try:
            import httpx

            response = httpx.get(
                f"{self._config.host}/api/tags", timeout=self._config.network_timeout
            )
            return bool(response.status_code == 200)
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
                f"{self._config.host}/api/tags", timeout=self._config.network_timeout
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

    def _subprocess_kwargs(self) -> dict:
        """Kwargs comunes para subprocess en Windows (ocultar ventana de consola)."""
        if self._platform == InstallationPlatform.WINDOWS and hasattr(subprocess, "CREATE_NO_WINDOW"):
            return {"creationflags": subprocess.CREATE_NO_WINDOW}
        return {}
        return {}

    @property
    def download_progress(self) -> DownloadProgress | None:
        """Progreso de descarga actual (None si no hay descarga en curso)."""
        return self._download_progress

    @property
    def downloading_model(self) -> str | None:
        """Nombre del modelo que se está descargando (None si no hay descarga)."""
        return self._downloading_model

    @property
    def is_downloading(self) -> bool:
        """True si hay una descarga en curso."""
        return self._download_progress is not None and self._download_progress.status == "downloading"

    def start_download_async(self, model_name: str) -> bool:
        """Inicia descarga de modelo en un hilo de fondo.

        Returns:
            True si la descarga se inició, False si ya hay una en curso.
        """
        if self.is_downloading:
            return False

        self._download_progress = DownloadProgress(status="downloading")
        self._downloading_model = model_name

        def _progress_cb(progress: DownloadProgress) -> None:
            self._download_progress = progress

        def _run() -> None:
            try:
                success, msg = self.download_model(model_name, progress_callback=_progress_cb)
                if success:
                    self._download_progress = DownloadProgress(
                        status="complete", percentage=100.0
                    )
                elif not self._download_progress or self._download_progress.status != "error":
                    self._download_progress = DownloadProgress(
                        status="error", error=msg
                    )
            except Exception as e:
                self._download_progress = DownloadProgress(
                    status="error", error=str(e)
                )
            finally:
                self._downloading_model = None

        thread = threading.Thread(target=_run, daemon=True, name="ollama-pull")
        thread.start()
        return True

    def get_version(self) -> str | None:
        """Obtiene la version de Ollama instalada."""
        if not self.is_installed:
            return None

        try:
            ollama_exe = self._get_ollama_executable()
            result = subprocess.run(
                [ollama_exe, "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10.0,
                **self._subprocess_kwargs(),
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
        progress_callback: Callable[[DownloadProgress], None] | None = None,
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
        progress_callback: Callable[[DownloadProgress], None] | None,
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
                    timeout=300.0,  # 5 minutos
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
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
                return (
                    False,
                    "Instalacion completa pero 'ollama' no esta en PATH. Reinicia la terminal.",
                )

        except subprocess.TimeoutExpired:
            return False, "Timeout durante la instalacion"
        except subprocess.CalledProcessError as e:
            return False, f"Error ejecutando instalador: {e}"
        finally:
            # Limpiar instalador
            with contextlib.suppress(Exception):
                installer_path.unlink()

    def _install_macos(
        self,
        progress_callback: Callable[[DownloadProgress], None] | None,
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
                    encoding="utf-8",
                    errors="replace",
                    timeout=600.0,  # 10 minutos
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

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
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
            with contextlib.suppress(Exception):
                zip_path.unlink()

    def _install_linux(
        self,
        progress_callback: Callable[[DownloadProgress], None] | None,
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
                encoding="utf-8",
                errors="replace",
                timeout=60.0,
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
                text=True,
                encoding="utf-8",
                errors="replace",
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
        progress_callback: Callable[[DownloadProgress], None] | None,
    ) -> bool:
        """Descarga un archivo con reporte de progreso."""
        import ssl

        progress = DownloadProgress(status="downloading")

        # Crear contexto SSL con certifi para entornos embebidos
        try:
            import certifi

            ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            try:
                ssl_ctx = ssl.create_default_context()
            except Exception:
                ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE

        for attempt in range(self._config.network_retries):
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                req = urllib.request.Request(url, headers=headers)

                with urllib.request.urlopen(req, timeout=300, context=ssl_ctx) as response:
                    total_size = int(response.headers.get("Content-Length", 0))
                    progress.total_bytes = total_size
                    block_size = 8192
                    downloaded = 0

                    with open(dest, "wb") as f:
                        while True:
                            chunk = response.read(block_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)

                            progress.current_bytes = downloaded
                            if total_size > 0:
                                progress.percentage = min(100.0, downloaded * 100.0 / total_size)
                            if progress_callback:
                                progress_callback(progress)

                progress.status = "complete"
                progress.percentage = 100.0
                if progress_callback:
                    progress_callback(progress)
                return True

            except Exception as e:
                logger.debug(f"Intento {attempt + 1} fallido: {e}")
                if dest.exists():
                    dest.unlink()
                if attempt < self._config.network_retries - 1:
                    time.sleep(self._config.retry_delay)

        progress.status = "error"
        progress.error = "Descarga fallida despues de varios intentos"
        if progress_callback:
            progress_callback(progress)
        return False

    def _should_force_cpu(self) -> bool:
        """Detecta si la GPU fue bloqueada por seguridad (CC < 6.0 → BSOD risk)."""
        try:
            from narrative_assistant.core.device import get_blocked_gpu_info
            blocked = get_blocked_gpu_info()
            if blocked:
                logger.info(
                    f"GPU bloqueada detectada ({blocked.get('name', '?')}, "
                    f"CC {blocked.get('compute_capability', '?')}). "
                    f"Forzando Ollama en modo CPU."
                )
                return True
        except Exception:
            pass
        return False

    def start_service(self, force_cpu: bool = False) -> tuple[bool, str]:
        """
        Inicia el servicio de Ollama.

        Args:
            force_cpu: Si True, fuerza modo CPU (util en Windows con GPUs viejas)

        Returns:
            Tupla (exito, mensaje)
        """
        # Auto-detectar GPU bloqueada (prevención BSOD en Maxwell/Kepler)
        if not force_cpu:
            force_cpu = self._should_force_cpu()

        with self._lock:
            if not self.is_installed:
                return False, "Ollama no esta instalado"

            if self.is_running:
                # Si Ollama ya está corriendo pero necesitamos CPU mode,
                # verificar si debemos reiniciar
                if force_cpu:
                    return self._restart_in_cpu_mode()
                return True, "Ollama ya esta corriendo"

            self._status = OllamaStatus.STARTING

            try:
                env = os.environ.copy()

                # Configurar modo CPU si se solicita o GPU bloqueada
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
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )
                else:
                    # Linux/macOS: iniciar en nueva sesion
                    subprocess.Popen(
                        [ollama_exe, "serve"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        env=env,
                        start_new_session=True,
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
                return (
                    False,
                    f"Timeout esperando que Ollama inicie ({self._config.service_start_timeout}s)",
                )

            except FileNotFoundError:
                self._status = OllamaStatus.NOT_INSTALLED
                return False, "Comando 'ollama' no encontrado"
            except Exception as e:
                self._status = OllamaStatus.ERROR
                return False, f"Error iniciando servicio: {e}"

    def _restart_in_cpu_mode(self) -> tuple[bool, str]:
        """Reinicia Ollama en modo CPU si está corriendo con GPU bloqueada."""
        logger.warning("Ollama corriendo con GPU potencialmente insegura. Intentando reiniciar en modo CPU...")
        try:
            # Intentar detener Ollama via taskkill (Windows) o kill (Unix)
            import subprocess as sp
            if self._platform == InstallationPlatform.WINDOWS:
                sp.run(["taskkill", "/IM", "ollama.exe", "/F"],
                       capture_output=True, timeout=10)
                # También matar ollama_llama_server si existe
                sp.run(["taskkill", "/IM", "ollama_llama_server.exe", "/F"],
                       capture_output=True, timeout=10)
            else:
                sp.run(["pkill", "-f", "ollama serve"],
                       capture_output=True, timeout=10)

            # Esperar a que se detenga
            for _ in range(10):
                if not self.is_running:
                    break
                time.sleep(1)
        except Exception as e:
            logger.warning(f"Error deteniendo Ollama: {e}")

        if self.is_running:
            logger.warning("No se pudo detener Ollama. Continuando con la instancia existente (riesgo BSOD).")
            return True, "Ollama corriendo (no se pudo reiniciar en CPU)"

        # Reiniciar con force_cpu
        self._config.force_cpu = True
        self._status = OllamaStatus.STOPPED
        return self.start_service(force_cpu=True)

    def ensure_running(self, force_cpu: bool = False) -> tuple[bool, str]:
        """
        Asegura que Ollama este corriendo.

        Si no esta instalado, retorna False.
        Si esta instalado pero no corriendo, intenta iniciarlo.
        Si GPU bloqueada, reinicia en modo CPU si es necesario.

        Args:
            force_cpu: Si True, fuerza modo CPU

        Returns:
            Tupla (exito, mensaje)
        """
        if not self.is_installed:
            return False, "Ollama no esta instalado"

        # Auto-detectar GPU bloqueada
        if not force_cpu:
            force_cpu = self._should_force_cpu()

        if self.is_running:
            if force_cpu:
                return self._restart_in_cpu_mode()
            return True, "Ollama esta corriendo"

        return self.start_service(force_cpu)

    def download_model(
        self,
        model_name: str,
        progress_callback: Callable[[DownloadProgress], None] | None = None,
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
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                **self._subprocess_kwargs(),
            )

            # Regex para extraer porcentaje de líneas con ANSI escapes
            _ansi_re = re.compile(r"\x1b\[[^a-zA-Z]*[a-zA-Z]|\[[\d;?]*[a-zA-Z]")
            last_error_line = ""

            if process.stdout is not None:
                for line in process.stdout:
                    # Limpiar ANSI escapes y caracteres de control
                    clean = _ansi_re.sub("", line).strip()
                    clean = "".join(c for c in clean if c.isprintable() or c in " \t")
                    clean = clean.strip()

                    if not clean:
                        continue

                    logger.debug(f"ollama pull: {clean}")

                    # Capturar líneas de error para mensajes útiles
                    if clean.lower().startswith("error"):
                        last_error_line = clean

                # Parsear progreso: Ollama emite "pulling xxx:  45% ▕...▏ 1.2 GB/2.0 GB"
                pct_match = re.search(r"(\d+)%", clean)
                if pct_match:
                    try:
                        pct = float(pct_match.group(1))
                        progress.percentage = pct
                        if progress_callback:
                            progress_callback(progress)
                    except ValueError:
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

                # Micro-benchmark automático post-descarga
                try:
                    toks = self.benchmark_model(model_name)
                    if toks:
                        logger.info(f"Benchmark post-descarga {model_name}: {toks:.1f} tok/s")
                except Exception as e:
                    logger.debug(f"Benchmark post-descarga {model_name} omitido: {e}")

                return True, f"Modelo {model_name} descargado"
            else:
                # Construir mensaje de error descriptivo
                if last_error_line:
                    error_msg = last_error_line
                else:
                    error_msg = f"ollama pull {model_name} falló (código {process.returncode})"

                # Detectar causas comunes y dar mensajes accionables
                error_lower = error_msg.lower()
                if "id_ed25519" in error_lower or "no puede encontrar" in error_lower:
                    error_msg = (
                        "Ollama necesita reiniciarse. "
                        "Cierra Ollama desde la bandeja del sistema y vuelve a abrirlo."
                    )
                elif "connection" in error_lower or "timeout" in error_lower:
                    error_msg = (
                        f"Error de conexión descargando {model_name}. "
                        "Verifica tu conexión a internet."
                    )
                elif "no space" in error_lower or "disk" in error_lower:
                    model_info = self.get_model_info(model_name)
                    size = f" (~{model_info.size_gb} GB)" if model_info else ""
                    error_msg = f"Espacio en disco insuficiente para {model_name}{size}."

                logger.error(f"ollama pull falló: {error_msg}")
                progress.status = "error"
                progress.error = error_msg
                if progress_callback:
                    progress_callback(progress)
                return False, error_msg

        except FileNotFoundError:
            error_msg = (
                "Comando 'ollama' no encontrado. "
                "Instala Ollama desde ollama.com/download"
            )
            progress.status = "error"
            progress.error = error_msg
            if progress_callback:
                progress_callback(progress)
            return False, error_msg

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
                encoding="utf-8",
                errors="replace",
                timeout=60.0,
                **self._subprocess_kwargs(),
            )

            if result.returncode == 0:
                self._downloaded_models.discard(model_name)
                self._save_state()
                return True, f"Modelo {model_name} eliminado"
            else:
                return False, f"Error eliminando modelo: {result.stderr}"

        except Exception as e:
            return False, f"Error: {e}"

    def get_model_info(self, model_name: str) -> OllamaModel | None:
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
                    min_ram_gb=model.min_ram_gb,
                    is_core=model.is_core,
                    is_legacy=model.is_legacy,
                    benchmark_toks=model.benchmark_toks,
                )
        return None

    def benchmark_model(self, model_name: str) -> float | None:
        """
        Ejecuta un micro-benchmark de un modelo (~30 tokens).

        Mide tok/s real en el hardware actual. Se ejecuta automáticamente
        después de descargar un modelo.

        Args:
            model_name: Nombre del modelo a benchmarkear

        Returns:
            tok/s medido, o None si falla
        """
        if not self.is_running:
            logger.warning(f"Benchmark de {model_name}: Ollama no corriendo")
            return None

        try:
            import httpx

            host = self._config.host
            start = time.time()

            response = httpx.post(
                f"{host}/api/chat",
                json={
                    "model": model_name,
                    "messages": [
                        {"role": "user", "content": "Cuenta del 1 al 10."}
                    ],
                    "stream": False,
                    "options": {"num_predict": 30},
                },
                timeout=120.0,
            )

            elapsed = time.time() - start

            if response.status_code == 200:
                data = response.json()
                # Ollama devuelve eval_count y eval_duration en nanoseconds
                eval_count = data.get("eval_count", 0)
                eval_duration_ns = data.get("eval_duration", 0)

                if eval_count > 0 and eval_duration_ns > 0:
                    toks = eval_count / (eval_duration_ns / 1e9)
                elif elapsed > 0:
                    # Fallback: estimar por tokens generados / tiempo total
                    content = data.get("message", {}).get("content", "")
                    estimated_tokens = len(content.split()) * 1.3
                    toks = estimated_tokens / elapsed
                else:
                    return None

                logger.info(
                    f"Benchmark {model_name}: {toks:.1f} tok/s "
                    f"({eval_count} tokens en {elapsed:.1f}s)"
                )

                # Actualizar en el catálogo
                for model in AVAILABLE_MODELS:
                    if model.name == model_name:
                        model.benchmark_toks = toks
                        break

                return float(toks)

            logger.warning(f"Benchmark {model_name}: HTTP {response.status_code}")
            return None

        except Exception as e:
            logger.warning(f"Benchmark {model_name} falló: {e}")
            return None


def get_ollama_manager(config: OllamaConfig | None = None) -> OllamaManager:
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
    progress_callback: Callable[[DownloadProgress], None] | None = None,
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
