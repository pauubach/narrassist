"""
Manager para llama.cpp (llama-server).

Este módulo proporciona gestión del servidor llama.cpp como alternativa
ligera a Ollama. Características:

- Binario portable (~50MB vs ~500MB de Ollama)
- Mejor rendimiento en CPU (~150 tok/s vs ~30 tok/s)
- API compatible con OpenAI
- 100% offline

IMPORTANTE: Los binarios de llama.cpp se descargan automáticamente
la primera vez que se necesitan.
"""

import logging
import os
import platform
import shutil
import signal
import subprocess
import threading
import time
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Lock para thread-safety
_manager_lock = threading.Lock()
_manager: "LlamaCppManager | None" = None


class LlamaCppStatus(Enum):
    """Estados posibles de llama.cpp."""

    NOT_INSTALLED = "not_installed"  # Binario no descargado
    INSTALLED = "installed"  # Binario presente pero servidor no corriendo
    RUNNING = "running"  # Servidor activo
    ERROR = "error"  # Error de estado


@dataclass
class LlamaCppModelInfo:
    """Información de un modelo GGUF."""

    name: str
    display_name: str
    filename: str  # Nombre del archivo GGUF
    size_gb: float
    description: str
    url: str  # URL de descarga (HuggingFace)
    is_downloaded: bool = False
    is_default: bool = False


# Modelos GGUF recomendados (cuantizados Q4_K_M para balance calidad/velocidad)
AVAILABLE_MODELS = [
    LlamaCppModelInfo(
        name="llama-3.2-3b",
        display_name="Llama 3.2 3B (Recomendado)",
        filename="Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        size_gb=2.0,
        description="Modelo rápido, funciona bien en CPU. Ideal para empezar.",
        url="https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        is_default=True,
    ),
    LlamaCppModelInfo(
        name="qwen2.5-7b",
        display_name="Qwen 2.5 7B (Mejor español)",
        filename="Qwen2.5-7B-Instruct-Q4_K_M.gguf",
        size_gb=4.4,
        description="Excelente para español. Requiere GPU o CPU potente.",
        url="https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf",
    ),
    LlamaCppModelInfo(
        name="mistral-7b",
        display_name="Mistral 7B (Alta calidad)",
        filename="Mistral-7B-Instruct-v0.3-Q4_K_M.gguf",
        size_gb=4.1,
        description="Alta calidad de razonamiento. Requiere GPU o CPU potente.",
        url="https://huggingface.co/bartowski/Mistral-7B-Instruct-v0.3-GGUF/resolve/main/Mistral-7B-Instruct-v0.3-Q4_K_M.gguf",
    ),
]


class LlamaCppManager:
    """
    Manager para el servidor llama.cpp.

    Gestiona la descarga, instalación e inicio del servidor llama-server.
    """

    def __init__(self) -> None:
        """Inicializa el manager."""
        self._process: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._port = 8081  # Puerto para llama-server (diferente de Ollama 11434)
        self._current_model: str | None = None

        # Directorio base para llama.cpp
        self._base_dir = self._get_base_dir()
        self._binary_dir = self._base_dir / "bin"
        self._models_dir = self._base_dir / "models"

        # Crear directorios si no existen
        self._binary_dir.mkdir(parents=True, exist_ok=True)
        self._models_dir.mkdir(parents=True, exist_ok=True)

    def _get_base_dir(self) -> Path:
        """Obtiene el directorio base para llama.cpp."""
        # Primero verificar si estamos en modo embebido
        if os.environ.get("NA_EMBEDDED") == "1":
            # En modo embebido, usar el directorio de recursos de la app
            # El binario viene pre-bundled
            resource_dir = os.environ.get("NA_RESOURCE_DIR")
            if resource_dir:
                return Path(resource_dir) / "llama.cpp"

        # En desarrollo o si no hay recurso embebido, usar directorio de usuario
        data_dir = Path(os.environ.get("NA_DATA_DIR", Path.home() / ".narrative_assistant"))
        return data_dir / "llama.cpp"

    @property
    def binary_path(self) -> Path:
        """Ruta al binario llama-server."""
        system = platform.system().lower()

        if system == "windows":
            return self._binary_dir / "llama-server.exe"
        else:
            return self._binary_dir / "llama-server"

    @property
    def is_installed(self) -> bool:
        """Verifica si el binario está instalado."""
        return self.binary_path.exists()

    @property
    def is_running(self) -> bool:
        """Verifica si el servidor está corriendo (thread-safe)."""
        with self._lock:
            if self._process is None:
                return False
            # Verificar si el proceso sigue vivo
            return self._process.poll() is None

    @property
    def status(self) -> LlamaCppStatus:
        """Obtiene el estado actual."""
        if not self.is_installed:
            return LlamaCppStatus.NOT_INSTALLED
        if self.is_running:
            return LlamaCppStatus.RUNNING
        return LlamaCppStatus.INSTALLED

    @property
    def host(self) -> str:
        """URL del servidor."""
        return f"http://localhost:{self._port}"

    @property
    def available_models(self) -> list[LlamaCppModelInfo]:
        """Lista de modelos disponibles con estado de descarga (sin mutar global)."""
        models = []
        for model in AVAILABLE_MODELS:
            model_path = self._models_dir / model.filename
            # Crear copia con is_downloaded actualizado (no muta AVAILABLE_MODELS)
            models.append(replace(model, is_downloaded=model_path.exists()))
        return models

    @property
    def downloaded_models(self) -> list[str]:
        """Lista de nombres de modelos descargados."""
        return [m.name for m in self.available_models if m.is_downloaded]

    def get_model_path(self, model_name: str) -> Path | None:
        """
        Obtiene la ruta a un modelo por nombre.

        Valida que el path esté dentro del directorio de modelos
        por seguridad (previene path traversal).
        """
        for model in AVAILABLE_MODELS:
            if model.name == model_name:
                path = self._models_dir / model.filename
                # Validación de seguridad: el path debe estar dentro de models_dir
                try:
                    resolved_path = path.resolve()
                    resolved_models_dir = self._models_dir.resolve()
                    if not str(resolved_path).startswith(str(resolved_models_dir)):
                        logger.error(f"Path de modelo fuera del directorio permitido: {path}")
                        return None
                except Exception as e:
                    logger.error(f"Error validando path de modelo: {e}")
                    return None
                return resolved_path if resolved_path.exists() else None
        return None

    def install_binary(
        self,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> tuple[bool, str]:
        """
        Descarga e instala el binario llama-server.

        Args:
            progress_callback: Callback para reportar progreso

        Returns:
            Tupla (éxito, mensaje)
        """
        system = platform.system().lower()
        machine = platform.machine().lower()

        # Determinar la URL de descarga según plataforma
        # Usamos releases pre-compilados de llama.cpp
        base_url = "https://github.com/ggerganov/llama.cpp/releases/latest/download"

        if system == "darwin":
            if machine in ("arm64", "aarch64"):
                filename = "llama-server-macos-arm64"
            else:
                filename = "llama-server-macos-x64"
        elif system == "windows":
            filename = "llama-server-win-x64.exe"
        elif system == "linux":
            if machine in ("arm64", "aarch64"):
                filename = "llama-server-linux-arm64"
            else:
                filename = "llama-server-linux-x64"
        else:
            return False, f"Sistema no soportado: {system}"

        url = f"{base_url}/{filename}"

        try:
            import httpx

            if progress_callback:
                progress_callback(
                    {"status": "downloading", "message": "Descargando llama-server...", "progress": 0}
                )

            # Descargar con progreso
            with httpx.stream("GET", url, follow_redirects=True, timeout=300.0) as response:
                response.raise_for_status()

                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0

                binary_path = self.binary_path
                with open(binary_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback and total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            progress_callback(
                                {
                                    "status": "downloading",
                                    "message": f"Descargando llama-server... {progress}%",
                                    "progress": progress,
                                }
                            )

            # Hacer ejecutable en Unix
            if system != "windows":
                os.chmod(binary_path, 0o755)

            if progress_callback:
                progress_callback({"status": "complete", "message": "llama-server instalado", "progress": 100})

            logger.info(f"llama-server instalado en: {binary_path}")
            return True, "llama-server instalado correctamente"

        except httpx.HTTPStatusError as e:
            msg = f"Error descargando llama-server: HTTP {e.response.status_code}"
            logger.error(msg)
            return False, msg
        except Exception as e:
            msg = f"Error instalando llama-server: {e}"
            logger.error(msg)
            return False, msg

    def download_model(
        self,
        model_name: str,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> tuple[bool, str]:
        """
        Descarga un modelo GGUF.

        Args:
            model_name: Nombre del modelo (llama-3.2-3b, qwen2.5-7b, mistral-7b)
            progress_callback: Callback para reportar progreso

        Returns:
            Tupla (éxito, mensaje)
        """
        model_info = None
        for m in AVAILABLE_MODELS:
            if m.name == model_name:
                model_info = m
                break

        if not model_info:
            return False, f"Modelo no encontrado: {model_name}"

        model_path = self._models_dir / model_info.filename

        if model_path.exists():
            return True, f"Modelo {model_name} ya está descargado"

        try:
            import httpx

            if progress_callback:
                progress_callback(
                    {
                        "status": "downloading",
                        "message": f"Descargando {model_info.display_name}...",
                        "progress": 0,
                    }
                )

            # Descargar con progreso
            with httpx.stream("GET", model_info.url, follow_redirects=True, timeout=3600.0) as response:
                response.raise_for_status()

                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0

                # Descargar a archivo temporal primero
                temp_path = model_path.with_suffix(".tmp")
                with open(temp_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=65536):
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress_callback and total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            size_mb = downloaded / (1024 * 1024)
                            total_mb = total_size / (1024 * 1024)
                            progress_callback(
                                {
                                    "status": "downloading",
                                    "message": f"Descargando {model_info.display_name}... {size_mb:.0f}/{total_mb:.0f} MB",
                                    "progress": progress,
                                }
                            )

                # Verificar integridad: tamaño de archivo
                actual_size = temp_path.stat().st_size
                if total_size > 0 and actual_size != total_size:
                    temp_path.unlink()  # Eliminar archivo corrupto
                    msg = f"Descarga incompleta: {actual_size}/{total_size} bytes"
                    logger.error(msg)
                    if progress_callback:
                        progress_callback({"status": "error", "message": msg, "progress": 0})
                    return False, msg

                # Mover a ubicación final
                shutil.move(str(temp_path), str(model_path))

            if progress_callback:
                progress_callback(
                    {"status": "complete", "message": f"{model_info.display_name} descargado", "progress": 100}
                )

            logger.info(f"Modelo descargado: {model_path}")
            return True, f"Modelo {model_name} descargado correctamente"

        except httpx.HTTPStatusError as e:
            msg = f"Error descargando modelo: HTTP {e.response.status_code}"
            logger.error(msg)
            return False, msg
        except Exception as e:
            msg = f"Error descargando modelo: {e}"
            logger.error(msg)
            return False, msg

    def start_server(
        self,
        model_name: str | None = None,
        n_gpu_layers: int = -1,  # -1 = auto (all layers to GPU if available)
        n_ctx: int = 4096,  # Contexto de 4K tokens
    ) -> tuple[bool, str]:
        """
        Inicia el servidor llama-server.

        Args:
            model_name: Nombre del modelo a cargar (usa el default si None)
            n_gpu_layers: Capas a cargar en GPU (-1 = auto)
            n_ctx: Tamaño del contexto

        Returns:
            Tupla (éxito, mensaje)
        """
        with self._lock:
            if self.is_running:
                return True, "Servidor ya está corriendo"

            if not self.is_installed:
                return False, "llama-server no está instalado"

            # Encontrar modelo
            if model_name is None:
                # Usar el primero descargado o el default
                for m in AVAILABLE_MODELS:
                    if (self._models_dir / m.filename).exists():
                        model_name = m.name
                        break

            if model_name is None:
                return False, "No hay modelos descargados"

            model_path = self.get_model_path(model_name)
            if model_path is None:
                return False, f"Modelo {model_name} no encontrado"

            # Construir comando
            cmd = [
                str(self.binary_path),
                "--model",
                str(model_path),
                "--port",
                str(self._port),
                "--host",
                "127.0.0.1",
                "--ctx-size",
                str(n_ctx),
            ]

            # GPU layers
            if n_gpu_layers != 0:
                cmd.extend(["--n-gpu-layers", str(n_gpu_layers)])

            # Logging mínimo
            cmd.extend(["--log-disable"])

            try:
                # Iniciar proceso
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    # No crear ventana de consola en Windows
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if platform.system() == "Windows" else 0,
                )

                self._current_model = model_name

                # Esperar a que el servidor esté listo
                if self._wait_for_ready(timeout=60):
                    logger.info(f"llama-server iniciado con modelo {model_name}")
                    return True, f"Servidor iniciado con {model_name}"
                else:
                    self.stop_server()
                    return False, "Servidor no respondió a tiempo"

            except Exception as e:
                msg = f"Error iniciando servidor: {e}"
                logger.error(msg)
                return False, msg

    def _wait_for_ready(self, timeout: int = 60) -> bool:
        """Espera a que el servidor esté listo."""
        import httpx

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = httpx.get(f"{self.host}/health", timeout=2.0)
                if response.status_code == 200:
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    def stop_server(self) -> tuple[bool, str]:
        """Detiene el servidor."""
        with self._lock:
            if self._process is None:
                return True, "Servidor no estaba corriendo"

            try:
                # Intentar terminar gracefully
                if platform.system() == "Windows":
                    self._process.terminate()
                else:
                    self._process.send_signal(signal.SIGTERM)

                # Esperar hasta 5 segundos
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait()

                self._process = None
                self._current_model = None

                logger.info("llama-server detenido")
                return True, "Servidor detenido"

            except Exception as e:
                msg = f"Error deteniendo servidor: {e}"
                logger.error(msg)
                return False, msg

    def ensure_running(self, model_name: str | None = None) -> tuple[bool, str]:
        """
        Asegura que el servidor esté corriendo.

        Si no está instalado, lo instala.
        Si no hay modelos, descarga el default.
        Si no está corriendo, lo inicia.
        """
        # Verificar instalación
        if not self.is_installed:
            success, msg = self.install_binary()
            if not success:
                return False, msg

        # Verificar modelos
        if not self.downloaded_models:
            # Descargar modelo default
            default_model = next((m for m in AVAILABLE_MODELS if m.is_default), AVAILABLE_MODELS[0])
            success, msg = self.download_model(default_model.name)
            if not success:
                return False, msg
            model_name = default_model.name

        # Verificar servidor
        if not self.is_running:
            return self.start_server(model_name)

        return True, "llama.cpp listo"


def get_llamacpp_manager() -> LlamaCppManager:
    """
    Obtiene el manager singleton (thread-safe).

    Returns:
        Manager de llama.cpp
    """
    global _manager

    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = LlamaCppManager()

    return _manager
