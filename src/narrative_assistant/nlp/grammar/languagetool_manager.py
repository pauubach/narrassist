"""
Gestor de LanguageTool - Inicio y detención automática del servidor.

Este módulo gestiona el ciclo de vida del servidor LanguageTool:
- Inicio automático cuando se activa en Settings
- Detención al cerrar la aplicación o desactivar
- Verificación de estado y reconexión

El servidor se inicia como subproceso y consume ~500MB RAM.
"""

import logging
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional
import platform

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
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._starting = False

        # Rutas
        self._project_root = self._find_project_root()
        self._lt_dir = self._project_root / "tools" / "languagetool" if self._project_root else None
        self._java_dir = self._project_root / "tools" / "java" if self._project_root else None

    def _find_project_root(self) -> Optional[Path]:
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

    def _get_java_command(self) -> Optional[str]:
        """Obtener comando de Java (sistema o local)."""
        system = platform.system()

        # 1. Verificar Java del sistema
        try:
            result = subprocess.run(
                ["java", "-version"],
                capture_output=True,
                timeout=5
            )
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
                return str(java_exe)

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
                logger.warning("LanguageTool no está instalado. Ejecutar: python scripts/setup_languagetool.py")
                return False

            # Verificar Java
            java_cmd = self._get_java_command()
            if not java_cmd:
                logger.warning("Java no encontrado. Instalar Java o ejecutar: python scripts/setup_languagetool.py")
                return False

            self._starting = True

        try:
            jar_file = self._lt_dir / "languagetool-server.jar"

            # Comando para iniciar
            cmd = [
                java_cmd,
                "-Xmx512m",
                "-cp", str(jar_file),
                "org.languagetool.server.HTTPServer",
                "--port", str(self.port),
                "--allow-origin", "*"
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
_manager: Optional[LanguageToolManager] = None
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
