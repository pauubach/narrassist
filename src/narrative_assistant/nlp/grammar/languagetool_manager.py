"""
Gestor de LanguageTool - Inicio, detención e instalación automática.

Este módulo gestiona el ciclo de vida del servidor LanguageTool:
- Instalación automática de Java + LanguageTool desde la UI
- Inicio automático cuando se activa en Settings
- Detención al cerrar la aplicación o desactivar
- Verificación de estado y reconexión

El servidor se inicia como subproceso y consume ~256MB RAM (heap limitado).
"""

import contextlib
import logging
import os
import platform
import shutil
import stat
import subprocess
import threading
import time
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Configuración
DEFAULT_PORT = 8081
STARTUP_TIMEOUT = 30  # segundos para esperar que inicie
CHECK_INTERVAL = 1  # segundos entre checks de disponibilidad


class LanguageToolManager:
    """
    Gestor del servidor LanguageTool.

    Maneja el inicio y detención del servidor Java de LanguageTool
    como un subproceso gestionado.
    """

    def __init__(self, port: int = DEFAULT_PORT):
        """
        Inicializar gestor.

        Args:
            port: Puerto para el servidor (default: 8081)
        """
        self.port = port
        self._process: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._starting = False

        # Rutas - usar directorio de datos en producción, tools/ en desarrollo
        self._tools_base = self._get_tools_base_dir()
        self._lt_dir = self._tools_base / "languagetool" if self._tools_base else None
        self._java_dir = self._tools_base / "java" if self._tools_base else None

    def _get_tools_base_dir(self) -> Path | None:
        """
        Obtener directorio base para tools (Java, LanguageTool).

        - Producción (NA_EMBEDDED=1): %LOCALAPPDATA%/Narrative Assistant/tools
        - Desarrollo: <project_root>/tools
        """
        is_embedded = os.environ.get("NA_EMBEDDED") == "1"

        if is_embedded:
            # Modo producción - usar directorio de datos del sistema
            system = platform.system()
            if system == "Windows":
                localappdata = os.environ.get("LOCALAPPDATA", "")
                if localappdata:
                    tools_dir = Path(localappdata) / "Narrative Assistant" / "tools"
                    tools_dir.mkdir(parents=True, exist_ok=True)
                    return tools_dir
            elif system == "Darwin":
                tools_dir = (
                    Path.home()
                    / "Library"
                    / "Application Support"
                    / "Narrative Assistant"
                    / "tools"
                )
                tools_dir.mkdir(parents=True, exist_ok=True)
                return tools_dir
            else:
                # Linux
                xdg_data = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
                tools_dir = Path(xdg_data) / "narrative-assistant" / "tools"
                tools_dir.mkdir(parents=True, exist_ok=True)
                return tools_dir

        # Modo desarrollo - buscar raíz del proyecto
        project_root = self._find_project_root()
        if project_root:
            tools_dir = project_root / "tools"
            tools_dir.mkdir(parents=True, exist_ok=True)
            return tools_dir

        return None

    def _find_project_root(self) -> Path | None:
        """Encontrar raíz del proyecto buscando CLAUDE.md o pyproject.toml."""
        current = Path(__file__).resolve()

        # Subir hasta encontrar el directorio raíz del proyecto
        for parent in [current] + list(current.parents):
            if (parent / "CLAUDE.md").exists() or (parent / "pyproject.toml").exists():
                return parent

        # Fallback: buscar desde el directorio de trabajo
        cwd = Path.cwd()
        for parent in [cwd] + list(cwd.parents):
            if (parent / "tools" / "languagetool").exists():
                return parent

        return None

    @property
    def is_installed(self) -> bool:
        """Verificar si LanguageTool está instalado."""
        if not self._lt_dir:
            return False
        jar_file = self._lt_dir / "languagetool-server.jar"
        return jar_file.exists()

    @property
    def is_running(self) -> bool:
        """Verificar si el servidor está corriendo (proceso o externo)."""
        # Primero verificar nuestro proceso
        if self._process is not None:
            if self._process.poll() is None:
                return True
            else:
                # Proceso terminó
                self._process = None

        # Verificar si hay algo escuchando en el puerto
        return self._check_server_responding()

    def _check_server_responding(self) -> bool:
        """Verificar si el servidor responde en el puerto."""
        try:
            import urllib.request

            url = f"http://localhost:{self.port}/v2/languages"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2) as response:
                return response.status == 200
        except Exception:
            return False

    def _get_java_command(self) -> str | None:
        """Obtener comando de Java (sistema o local)."""
        system = platform.system()

        # 1. Verificar Java del sistema
        try:
            result = subprocess.run(["java", "-version"], capture_output=True, timeout=5)
            if result.returncode == 0:
                return "java"
        except Exception:
            pass

        # 2. Verificar Java local
        if self._java_dir:
            if system == "Windows":
                java_exe = self._java_dir / "bin" / "java.exe"
            else:
                java_exe = self._java_dir / "bin" / "java"

            if java_exe.exists():
                # Verificar que es ejecutable (arquitectura correcta)
                try:
                    result = subprocess.run(
                        [str(java_exe), "-version"], capture_output=True, timeout=5
                    )
                    if result.returncode == 0:
                        return str(java_exe)
                    else:
                        logger.warning(
                            "Java local existe pero no es ejecutable (¿arquitectura incorrecta?)"
                        )
                except Exception as e:
                    logger.warning(f"Java local no funciona: {e}")

        return None

    def start(self, wait: bool = True) -> bool:
        """
        Iniciar servidor LanguageTool.

        Args:
            wait: Si True, espera a que el servidor esté listo

        Returns:
            True si se inició correctamente o ya estaba corriendo
        """
        with self._lock:
            # Ya corriendo?
            if self.is_running:
                logger.info("LanguageTool ya está corriendo")
                return True

            # Ya iniciando?
            if self._starting:
                logger.info("LanguageTool ya se está iniciando")
                return False

            # Verificar instalación
            if not self.is_installed:
                logger.warning(
                    "LanguageTool no está instalado. Ejecutar: python scripts/setup_languagetool.py"
                )
                return False

            # Verificar Java
            java_cmd = self._get_java_command()
            if not java_cmd:
                logger.warning(
                    "Java no encontrado. Instalar Java o ejecutar: python scripts/setup_languagetool.py"
                )
                return False

            self._starting = True

        try:
            jar_file = self._lt_dir / "languagetool-server.jar"

            # Comando para iniciar
            cmd = [
                java_cmd,
                "-Xmx256m",
                "-cp",
                str(jar_file),
                "org.languagetool.server.HTTPServer",
                "--port",
                str(self.port),
                "--allow-origin",
                "*",
            ]

            logger.info(f"Iniciando LanguageTool en puerto {self.port}...")

            # Iniciar proceso
            # En Windows, usar CREATE_NO_WINDOW para no mostrar ventana
            kwargs = {
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "cwd": str(self._lt_dir),
            }

            if platform.system() == "Windows":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            self._process = subprocess.Popen(cmd, **kwargs)

            if wait:
                # Esperar a que esté listo
                start_time = time.time()
                while time.time() - start_time < STARTUP_TIMEOUT:
                    if self._check_server_responding():
                        logger.info(f"LanguageTool iniciado correctamente (puerto {self.port})")
                        return True

                    # Verificar que el proceso sigue vivo
                    if self._process.poll() is not None:
                        logger.error("LanguageTool terminó inesperadamente")
                        self._process = None
                        return False

                    time.sleep(CHECK_INTERVAL)

                # Timeout
                logger.warning(f"Timeout esperando LanguageTool ({STARTUP_TIMEOUT}s)")
                return False

            return True

        except Exception as e:
            logger.error(f"Error iniciando LanguageTool: {e}")
            return False
        finally:
            with self._lock:
                self._starting = False

    def stop(self) -> bool:
        """
        Detener servidor LanguageTool (solo si lo iniciamos nosotros).

        Returns:
            True si se detuvo correctamente
        """
        with self._lock:
            if self._process is None:
                logger.debug("No hay proceso LanguageTool que detener")
                return True

            try:
                logger.info("Deteniendo LanguageTool...")

                # Terminar gracefully
                self._process.terminate()

                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Forzar
                    self._process.kill()
                    self._process.wait(timeout=2)

                self._process = None
                logger.info("LanguageTool detenido")
                return True

            except Exception as e:
                logger.error(f"Error deteniendo LanguageTool: {e}")
                self._process = None
                return False

    def restart(self) -> bool:
        """Reiniciar servidor."""
        self.stop()
        time.sleep(1)
        return self.start()

    def ensure_running(self) -> bool:
        """
        Asegurar que el servidor está corriendo.

        Inicia el servidor si no está corriendo.
        Útil para llamar antes de cada análisis.

        Returns:
            True si el servidor está disponible
        """
        if self.is_running:
            return True
        return self.start()


# Singleton
_manager: LanguageToolManager | None = None
_manager_lock = threading.Lock()


def get_languagetool_manager() -> LanguageToolManager:
    """Obtener instancia singleton del gestor."""
    global _manager

    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = LanguageToolManager()

    return _manager


def ensure_languagetool_running() -> bool:
    """
    Asegurar que LanguageTool está corriendo.

    Función de conveniencia para iniciar el servidor si no está activo.

    Returns:
        True si el servidor está disponible
    """
    return get_languagetool_manager().ensure_running()


def stop_languagetool() -> bool:
    """
    Detener servidor LanguageTool si lo iniciamos nosotros.

    Returns:
        True si se detuvo correctamente
    """
    return get_languagetool_manager().stop()


def is_languagetool_installed() -> bool:
    """Verificar si LanguageTool está instalado."""
    return get_languagetool_manager().is_installed


# =============================================================================
# Instalador de LanguageTool + Java
# =============================================================================

# Configuración de instalación
LT_VERSION = "6.4"
LT_URLS = [
    f"https://github.com/languagetool-org/languagetool/releases/download/v{LT_VERSION}/LanguageTool-{LT_VERSION}.zip",
    f"https://languagetool.org/download/LanguageTool-{LT_VERSION}.zip",
    f"https://www.languagetool.org/download/LanguageTool-{LT_VERSION}.zip",
]

JAVA_VERSION = "21"
# URLs para diferentes plataformas y arquitecturas
# macOS tiene versiones separadas para Intel (x64) y Apple Silicon (aarch64)
JAVA_URLS = {
    "Windows": {
        "x64": "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jre_x64_windows_hotspot_21.0.2_13.zip",
    },
    "Linux": {
        "x64": "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jre_x64_linux_hotspot_21.0.2_13.tar.gz",
        "aarch64": "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jre_aarch64_linux_hotspot_21.0.2_13.tar.gz",
    },
    "Darwin": {
        "x64": "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jre_x64_mac_hotspot_21.0.2_13.tar.gz",
        "aarch64": "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.2%2B13/OpenJDK21U-jre_aarch64_mac_hotspot_21.0.2_13.tar.gz",
    },
}


def _get_machine_arch() -> str:
    """
    Obtener la arquitectura de la máquina de forma normalizada.

    Returns:
        'x64' para Intel/AMD64, 'aarch64' para ARM64/Apple Silicon
    """
    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        return "aarch64"
    elif machine in ("x86_64", "amd64", "x64"):
        return "x64"
    else:
        # Default a x64 para compatibilidad
        return "x64"


@dataclass
class InstallProgress:
    """Progreso de la instalación de LanguageTool."""

    phase: str = "pending"
    phase_label: str = ""
    percentage: float = 0.0
    detail: str = ""
    error: str | None = None


class LanguageToolInstaller:
    """
    Instalador de LanguageTool + Java portable.

    Reutiliza la lógica de scripts/setup_languagetool.py con progress callbacks
    para integración con la UI.
    """

    def __init__(
        self,
        progress_callback: Callable[[InstallProgress], None] | None = None,
    ):
        self._callback = progress_callback
        self._progress = InstallProgress()
        self._last_logged_pct = -1.0  # throttle: solo loguear al cambiar >=1%

        # Rutas - reutilizar la lógica del manager
        mgr = get_languagetool_manager()
        self._tools_dir = mgr._tools_base
        self._lt_dir = mgr._lt_dir
        self._java_dir = mgr._java_dir

    def _report(
        self,
        phase: str,
        label: str,
        percentage: float,
        detail: str = "",
    ) -> None:
        """Reportar progreso al callback."""
        self._progress = InstallProgress(
            phase=phase,
            phase_label=label,
            percentage=percentage,
            detail=detail,
        )
        if self._callback:
            self._callback(self._progress)
        # Throttle log: solo cada 1% para evitar 28K líneas en un download de 235MB
        rounded = int(percentage)
        if rounded != int(self._last_logged_pct):
            self._last_logged_pct = percentage
            logger.info(f"LT Install [{percentage:.0f}%] {label}: {detail}")

    def _report_error(self, error: str) -> None:
        """Reportar error."""
        self._progress = InstallProgress(
            phase="error",
            phase_label="Error",
            percentage=self._progress.percentage,
            error=error,
        )
        if self._callback:
            self._callback(self._progress)
        logger.error(f"LT Install error: {error}")

    def install(self) -> tuple[bool, str]:
        """
        Ejecutar instalación completa. Bloqueante — llamar desde hilo background.

        Returns:
            Tupla (éxito, mensaje)
        """
        if not self._tools_dir:
            msg = "No se pudo determinar el directorio de instalación"
            self._report_error(msg)
            return False, msg

        try:
            # Fase 1: Verificar Java (0-5%)
            self._report("checking_java", "Verificando Java", 0, "Buscando Java en el sistema...")

            has_system_java = self._check_system_java()
            has_local_java = self._check_local_java()

            if has_system_java or has_local_java:
                self._report("checking_java", "Verificando Java", 5, "Java encontrado")
            else:
                # Fase 2: Instalar Java (5-40%)
                self._report(
                    "installing_java", "Instalando Java", 5, "Descargando OpenJDK Temurin..."
                )
                success = self._install_java()
                if not success:
                    msg = "Error instalando Java"
                    self._report_error(msg)
                    return False, msg

            # Fase 3: Descargar LanguageTool (40-75%)
            self._report(
                "downloading_lt", "Descargando LanguageTool", 40, f"LanguageTool {LT_VERSION}..."
            )
            zip_path = self._download_languagetool()
            if zip_path is None:
                msg = "Error descargando LanguageTool"
                self._report_error(msg)
                return False, msg

            # Fase 4: Extraer (75-85%)
            self._report(
                "extracting_lt", "Extrayendo LanguageTool", 75, "Descomprimiendo archivos..."
            )
            success = self._extract_languagetool(zip_path)
            if not success:
                msg = "Error extrayendo LanguageTool"
                self._report_error(msg)
                return False, msg

            # Fase 5: Crear scripts de inicio (85-90%)
            self._report(
                "creating_scripts", "Configurando scripts", 85, "Creando scripts de inicio..."
            )
            self._create_start_scripts()

            # Fase 6: Verificar (90-95%)
            self._report("verifying", "Verificando instalación", 90, "Comprobando archivos...")
            jar_file = self._lt_dir / "languagetool-server.jar"
            if not jar_file.exists():
                msg = "No se encontró languagetool-server.jar después de la instalación"
                self._report_error(msg)
                return False, msg

            # Fase 7: Completar (95-100%)
            # NO arrancar el servidor automáticamente: consume ~512MB RAM
            # y combinado con Python backend + Ollama puede causar OOM.
            # El usuario puede iniciarlo manualmente desde Settings.
            mgr = get_languagetool_manager()
            # Refrescar rutas del manager por si acaba de instalarse
            mgr._lt_dir = self._lt_dir
            mgr._java_dir = self._java_dir

            self._report(
                "completed",
                "Instalación completada",
                100,
                "LanguageTool instalado. Puedes iniciarlo desde Ajustes.",
            )

            return True, "LanguageTool instalado correctamente"

        except Exception as e:
            msg = f"Error durante la instalación: {e}"
            self._report_error(msg)
            logger.exception("Error instalando LanguageTool")
            return False, msg

    # -------------------------------------------------------------------------
    # Métodos privados de instalación (adaptados de setup_languagetool.py)
    # -------------------------------------------------------------------------

    def _check_system_java(self) -> bool:
        """Verificar si Java está en el sistema."""
        try:
            result = subprocess.run(
                ["java", "-version"],
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _check_local_java(self) -> bool:
        """Verificar si Java está instalado localmente en tools/java."""
        if not self._java_dir:
            return False
        system = platform.system()
        java_exe = self._java_dir / "bin" / ("java.exe" if system == "Windows" else "java")
        if not java_exe.exists():
            return False
        try:
            result = subprocess.run(
                [str(java_exe), "-version"],
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _download_file(
        self,
        url: str,
        dest: Path,
        phase: str,
        label: str,
        pct_start: float,
        pct_end: float,
    ) -> bool:
        """Descargar archivo con progreso reportado al callback."""
        try:
            import ssl

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/octet-stream,*/*",
            }
            req = urllib.request.Request(url, headers=headers)

            # Crear contexto SSL con certifi para entornos embebidos
            try:
                import certifi

                ssl_ctx = ssl.create_default_context(cafile=certifi.where())
            except ImportError:
                # certifi no disponible, usar certificados del sistema
                try:
                    ssl_ctx = ssl.create_default_context()
                except Exception:
                    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                    ssl_ctx.check_hostname = False
                    ssl_ctx.verify_mode = ssl.CERT_NONE
                    logger.warning("Usando SSL sin verificación de certificados")

            with urllib.request.urlopen(req, timeout=300, context=ssl_ctx) as response:
                total_size = int(response.headers.get("Content-Length", 0))
                block_size = 8192
                downloaded = 0

                with open(dest, "wb") as f:
                    while True:
                        chunk = response.read(block_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            frac = downloaded / total_size
                            pct = pct_start + frac * (pct_end - pct_start)
                            mb_dl = downloaded / (1024 * 1024)
                            mb_total = total_size / (1024 * 1024)
                            self._report(
                                phase,
                                label,
                                pct,
                                f"{mb_dl:.0f}/{mb_total:.0f} MB",
                            )

            return True

        except urllib.error.URLError as e:
            reason = str(getattr(e, "reason", e))
            logger.warning(f"Error de red descargando {url}: {reason}")
            self._report(phase, label, pct_start, f"Error de red: {reason}")
            if dest.exists():
                dest.unlink()
            return False
        except Exception as e:
            logger.warning(f"Error descargando {url}: {e}")
            self._report(phase, label, pct_start, f"Error: {e}")
            if dest.exists():
                dest.unlink()
            return False

    def _install_java(self) -> bool:
        """Descargar e instalar Java portable."""
        system = platform.system()
        if system not in JAVA_URLS:
            logger.error(f"Sistema no soportado para Java: {system}")
            return False

        arch = _get_machine_arch()
        arch_urls = JAVA_URLS[system]

        if arch not in arch_urls:
            # Fallback a x64 si la arquitectura no está soportada
            logger.warning(f"Arquitectura {arch} no disponible para {system}, usando x64")
            arch = "x64"

        java_url = arch_urls[arch]
        logger.info(f"Descargando Java para {system}/{arch}")
        self._tools_dir.mkdir(parents=True, exist_ok=True)

        archive_name = (
            f"java-{JAVA_VERSION}-{arch}.zip"
            if system == "Windows"
            else f"java-{JAVA_VERSION}-{arch}.tar.gz"
        )
        archive_path = self._tools_dir / archive_name

        # Descargar (5-30%)
        if not archive_path.exists():
            success = self._download_file(
                java_url,
                archive_path,
                "installing_java",
                "Descargando Java",
                5,
                30,
            )
            if not success:
                return False
        else:
            self._report("installing_java", "Instalando Java", 30, "Archivo Java ya descargado")

        # Extraer (30-40%)
        self._report("installing_java", "Instalando Java", 30, "Extrayendo Java...")

        if self._java_dir and self._java_dir.exists():
            shutil.rmtree(self._java_dir, onerror=self._remove_readonly)

        try:
            if system == "Windows":
                with zipfile.ZipFile(archive_path, "r") as zf:
                    zf.extractall(self._tools_dir)
            else:
                import tarfile

                with tarfile.open(archive_path, "r:gz") as tf:
                    tf.extractall(self._tools_dir)

            # Encontrar directorio extraído
            extracted_dirs = [
                d for d in self._tools_dir.iterdir() if d.is_dir() and d.name.startswith("jdk-")
            ]
            if not extracted_dirs:
                logger.error("No se encontró directorio Java extraído")
                return False

            extracted_dir = extracted_dirs[0]

            # macOS: contenido en Contents/Home
            if system == "Darwin":
                contents_home = extracted_dir / "Contents" / "Home"
                if contents_home.exists():
                    shutil.move(str(contents_home), str(self._java_dir))
                    shutil.rmtree(extracted_dir)
                else:
                    extracted_dir.rename(self._java_dir)
            else:
                extracted_dir.rename(self._java_dir)

            # Hacer ejecutable en Unix
            if system != "Windows":
                java_exe = self._java_dir / "bin" / "java"
                if java_exe.exists():
                    java_exe.chmod(0o755)

            self._report("installing_java", "Instalando Java", 40, "Java instalado")
            return True

        except Exception as e:
            logger.error(f"Error extrayendo Java: {e}")
            return False

    def _download_languagetool(self) -> Path | None:
        """Descargar LanguageTool probando múltiples mirrors."""
        self._tools_dir.mkdir(parents=True, exist_ok=True)
        zip_path = self._tools_dir / f"LanguageTool-{LT_VERSION}.zip"

        if zip_path.exists():
            self._report("downloading_lt", "Descargando LanguageTool", 75, "Archivo ya descargado")
            return zip_path

        for i, url in enumerate(LT_URLS):
            self._report(
                "downloading_lt",
                "Descargando LanguageTool",
                40 + i * 2,
                f"Intentando mirror {i + 1}/{len(LT_URLS)}...",
            )
            success = self._download_file(
                url,
                zip_path,
                "downloading_lt",
                "Descargando LanguageTool",
                42 + i * 2,
                75,
            )
            if success:
                return zip_path
            # Eliminar archivo parcial
            if zip_path.exists():
                zip_path.unlink()

        return None

    def _extract_languagetool(self, zip_path: Path) -> bool:
        """Extraer LanguageTool del zip."""
        try:
            # Limpiar instalación anterior
            if self._lt_dir and self._lt_dir.exists():
                shutil.rmtree(self._lt_dir, onerror=self._remove_readonly)

            extract_dir = self._tools_dir / f"LanguageTool-{LT_VERSION}"
            if extract_dir.exists():
                shutil.rmtree(extract_dir, onerror=self._remove_readonly)

            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(self._tools_dir)

            # Buscar directorio extraído
            if not extract_dir.exists():
                for d in self._tools_dir.iterdir():
                    if d.is_dir() and d.name.startswith("LanguageTool"):
                        extract_dir = d
                        break

            if extract_dir.exists():
                shutil.move(str(extract_dir), str(self._lt_dir))
                return True
            else:
                logger.error("No se encontró directorio LanguageTool extraído")
                return False

        except Exception as e:
            logger.error(f"Error extrayendo LanguageTool: {e}")
            return False

    def _create_start_scripts(self) -> None:
        """Crear scripts de inicio."""
        if not self._lt_dir:
            return

        system = platform.system()
        has_system_java = self._check_system_java()

        # Windows batch
        if system == "Windows":
            java_cmd = "java" if has_system_java else "%~dp0..\\java\\bin\\java.exe"
        else:
            java_cmd = "java" if has_system_java else '"$(dirname "$0")/../java/bin/java"'

        if system == "Windows":
            bat = self._lt_dir / "start_lt.bat"
            bat.write_text(
                f'@echo off\ncd /d "%~dp0"\n"{java_cmd}" -Xmx256m -cp languagetool-server.jar '
                f'org.languagetool.server.HTTPServer --port {DEFAULT_PORT} --allow-origin "*"\n',
                encoding="utf-8",
            )

        sh = self._lt_dir / "start_lt.sh"
        sh_java = "java" if has_system_java else '"$(dirname "$0")/../java/bin/java"'
        sh.write_text(
            f'#!/bin/bash\ncd "$(dirname "$0")"\n{sh_java} -Xmx256m -cp languagetool-server.jar '
            f'org.languagetool.server.HTTPServer --port {DEFAULT_PORT} --allow-origin "*"\n',
            encoding="utf-8",
        )
        with contextlib.suppress(Exception):
            sh.chmod(0o755)

    @staticmethod
    def _remove_readonly(func, path, _excinfo) -> None:
        """Callback para shutil.rmtree: quitar readonly en Windows."""
        os.chmod(path, stat.S_IWRITE)
        func(path)


# Estado global de instalación (thread-safe)
_install_progress: InstallProgress | None = None
_installing: bool = False
_install_lock = threading.Lock()


def get_install_progress() -> InstallProgress | None:
    """Obtener progreso actual de la instalación."""
    return _install_progress


def is_lt_installing() -> bool:
    """Verificar si hay una instalación en curso."""
    return _installing


def start_lt_installation(
    callback: Callable[[InstallProgress], None] | None = None,
) -> tuple[bool, str]:
    """
    Iniciar instalación de LanguageTool en background.

    Args:
        callback: Función opcional para recibir progreso

    Returns:
        Tupla (éxito al iniciar, mensaje)
    """
    global _installing, _install_progress

    with _install_lock:
        if _installing:
            return False, "Ya hay una instalación en curso"
        _installing = True
        _install_progress = InstallProgress(
            phase="starting", phase_label="Iniciando...", percentage=0
        )

    def _progress_cb(progress: InstallProgress) -> None:
        global _install_progress
        _install_progress = progress
        if callback:
            callback(progress)

    def _run() -> None:
        global _installing
        try:
            installer = LanguageToolInstaller(progress_callback=_progress_cb)
            installer.install()
        except Exception as e:
            logger.exception("Error en hilo de instalación de LanguageTool")
            _progress_cb(
                InstallProgress(
                    phase="error",
                    phase_label="Error",
                    error=str(e),
                )
            )
        finally:
            _installing = False

    thread = threading.Thread(target=_run, daemon=True, name="lt-installer")
    thread.start()
    return True, "Instalación iniciada"
