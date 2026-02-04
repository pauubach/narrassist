#!/usr/bin/env python3
"""
Script de setup completo para Tauri + Vue 3 + Backend Python.

Automatiza:
1. Verificación de requisitos (Rust, Node, Python)
2. Instalación de dependencias
3. Build del backend
4. Copia del backend a binaries/
5. Setup del frontend

Uso:
    python scripts/setup_tauri.py
    python scripts/setup_tauri.py --skip-backend  # Solo frontend
    python scripts/setup_tauri.py --dev           # Solo checks, no builds
"""

import sys
import shutil
import subprocess
import platform
import logging
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Rutas del proyecto
PROJECT_ROOT = Path(__file__).parent.parent
API_SERVER_DIR = PROJECT_ROOT / "api-server"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
TAURI_DIR = PROJECT_ROOT / "src-tauri"
BINARIES_DIR = TAURI_DIR / "binaries"

def get_target_triple() -> str:
    """Obtiene el target triple de Rust según el sistema operativo."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "windows":
        return "x86_64-pc-windows-msvc"
    elif system == "darwin":
        if machine == "arm64":
            return "aarch64-apple-darwin"
        return "x86_64-apple-darwin"
    elif system == "linux":
        return "x86_64-unknown-linux-gnu"
    else:
        raise RuntimeError(f"Unsupported platform: {system}")

def check_command(cmd: str, version_flag: str = "--version") -> Optional[str]:
    """Verifica si un comando está disponible y devuelve su versión."""
    try:
        result = subprocess.run(
            [cmd, version_flag],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def verify_requirements() -> bool:
    """Verifica que todos los requisitos estén instalados."""
    logger.info("Verificando requisitos...")

    required = {
        "Python": ("python", "--version"),
        "Node.js": ("node", "--version"),
        "npm": ("npm", "--version"),
        "Rust": ("rustc", "--version"),
        "Cargo": ("cargo", "--version"),
    }

    all_ok = True
    for name, (cmd, flag) in required.items():
        version = check_command(cmd, flag)
        if version:
            logger.info(f"✓ {name}: {version}")
        else:
            logger.error(f"✗ {name} no encontrado")
            all_ok = False

    return all_ok

def build_backend() -> bool:
    """Build del backend Python con PyInstaller."""
    logger.info("=" * 60)
    logger.info("Building backend Python...")
    logger.info("=" * 60)

    try:
        # Verificar que exista build.py
        build_script = API_SERVER_DIR / "build.py"
        if not build_script.exists():
            logger.error(f"Build script not found: {build_script}")
            return False

        # Ejecutar build
        result = subprocess.run(
            [sys.executable, str(build_script)],
            cwd=API_SERVER_DIR,
            check=True,
        )

        logger.info("✓ Backend build completado")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Backend build falló: {e}")
        return False

def copy_backend_to_binaries() -> bool:
    """Copia el backend empaquetado a src-tauri/binaries/."""
    logger.info("Copiando backend a binaries...")

    source_dir = API_SERVER_DIR / "dist" / "narrative-assistant-server"
    if not source_dir.exists():
        logger.error(f"Backend build not found: {source_dir}")
        logger.error("Ejecuta primero: cd api-server && python build.py")
        return False

    # Obtener target triple
    target = get_target_triple()
    dest_dir = BINARIES_DIR / f"narrative-assistant-server-{target}"

    # Crear directorio binaries si no existe
    BINARIES_DIR.mkdir(exist_ok=True)

    # Eliminar destino anterior si existe
    if dest_dir.exists():
        logger.info(f"Eliminando build anterior: {dest_dir}")
        shutil.rmtree(dest_dir)

    # Copiar
    logger.info(f"Copiando {source_dir} -> {dest_dir}")
    shutil.copytree(source_dir, dest_dir)

    # Verificar ejecutable
    exe_name = "narrative-assistant-server.exe" if platform.system() == "Windows" else "narrative-assistant-server"
    exe_path = dest_dir / exe_name

    if not exe_path.exists():
        logger.error(f"Ejecutable no encontrado: {exe_path}")
        return False

    # Dar permisos de ejecución en Unix
    if platform.system() != "Windows":
        import stat
        exe_path.chmod(exe_path.stat().st_mode | stat.S_IEXEC)

    logger.info(f"✓ Backend copiado: {dest_dir}")
    logger.info(f"  Ejecutable: {exe_path}")
    logger.info(f"  Tamaño: {exe_path.stat().st_size / (1024 * 1024):.1f} MB")

    return True

def install_frontend_deps() -> bool:
    """Instala dependencias del frontend con npm."""
    logger.info("Instalando dependencias del frontend...")

    try:
        result = subprocess.run(
            ["npm", "install"],
            cwd=FRONTEND_DIR,
            check=True,
        )

        logger.info("✓ Dependencias del frontend instaladas")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"✗ npm install falló: {e}")
        return False

def main():
    """Función principal."""
    import argparse

    parser = argparse.ArgumentParser(description="Setup completo de Tauri + Vue 3 + Backend Python")
    parser.add_argument("--skip-backend", action="store_true", help="Omitir build del backend")
    parser.add_argument("--dev", action="store_true", help="Solo verificar requisitos (no builds)")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Narrative Assistant - Tauri Setup")
    logger.info("=" * 60)

    # 1. Verificar requisitos
    if not verify_requirements():
        logger.error("✗ Faltan requisitos. Instala las herramientas necesarias.")
        logger.error("")
        logger.error("Instalación:")
        logger.error("  - Rust: https://rustup.rs/")
        logger.error("  - Node.js: https://nodejs.org/")
        logger.error("  - Python: https://www.python.org/")
        return 1

    if args.dev:
        logger.info("✓ Todos los requisitos están instalados")
        return 0

    # 2. Build del backend (opcional)
    if not args.skip_backend:
        logger.info("")
        if not build_backend():
            logger.error("✗ Backend build falló")
            return 1

        # 3. Copiar backend a binaries
        logger.info("")
        if not copy_backend_to_binaries():
            logger.error("✗ Fallo al copiar backend a binaries")
            return 1
    else:
        logger.info("⊘ Backend build omitido (--skip-backend)")

    # 4. Instalar dependencias del frontend
    logger.info("")
    if not install_frontend_deps():
        logger.error("✗ Fallo al instalar dependencias del frontend")
        return 1

    # 5. Resumen
    logger.info("")
    logger.info("=" * 60)
    logger.info("✓✓✓ SETUP COMPLETADO ✓✓✓")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Siguiente paso:")
    logger.info("  cd src-tauri")
    logger.info("  cargo tauri dev")
    logger.info("")
    logger.info("O para build de producción:")
    logger.info("  cd src-tauri")
    logger.info("  cargo tauri build")

    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.warning("\nSetup cancelado por usuario")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error inesperado: {e}", exc_info=True)
        sys.exit(1)
