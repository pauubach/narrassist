#!/usr/bin/env python3
"""
Script de build para empaquetar el servidor FastAPI con PyInstaller.

Genera un ejecutable standalone con todos los modelos NLP incluidos.

Uso:
    python build.py                    # Build estándar (carpeta)
    python build.py --onefile          # Build ejecutable único
    python build.py --clean            # Limpiar build anterior
"""

import sys
import shutil
import subprocess
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Rutas
API_SERVER_DIR = Path(__file__).parent
PROJECT_ROOT = API_SERVER_DIR.parent
DIST_DIR = API_SERVER_DIR / "dist"
BUILD_DIR = API_SERVER_DIR / "build"
SPEC_FILE = API_SERVER_DIR / "build_bundle.spec"

def clean_build():
    """Limpia directorios de build anteriores."""
    logger.info("Limpiando builds anteriores...")

    if DIST_DIR.exists():
        logger.info(f"Eliminando {DIST_DIR}")
        shutil.rmtree(DIST_DIR)

    if BUILD_DIR.exists():
        logger.info(f"Eliminando {BUILD_DIR}")
        shutil.rmtree(BUILD_DIR)

    logger.info("✓ Limpieza completada")

def verify_models():
    """Verifica que los modelos NLP estén presentes."""
    logger.info("Verificando modelos NLP...")

    models_dir = PROJECT_ROOT / "models"
    spacy_model = models_dir / "spacy" / "es_core_news_lg"
    embeddings_model = models_dir / "embeddings" / "paraphrase-multilingual-MiniLM-L12-v2"

    if not spacy_model.exists():
        logger.error(f"✗ Modelo spaCy no encontrado: {spacy_model}")
        logger.error("Ejecuta: python scripts/download_models.py")
        return False

    if not embeddings_model.exists():
        logger.error(f"✗ Modelo embeddings no encontrado: {embeddings_model}")
        logger.error("Ejecuta: python scripts/download_models.py")
        return False

    logger.info(f"✓ Modelo spaCy: {spacy_model}")
    logger.info(f"✓ Modelo embeddings: {embeddings_model}")
    return True

def install_pyinstaller():
    """Verifica e instala PyInstaller si es necesario."""
    try:
        import PyInstaller
        logger.info(f"✓ PyInstaller ya instalado (v{PyInstaller.__version__})")
        return True
    except ImportError:
        logger.warning("PyInstaller no encontrado, instalando...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "pyinstaller"],
                check=True,
            )
            logger.info("✓ PyInstaller instalado correctamente")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"✗ Error instalando PyInstaller: {e}")
            return False

def run_pyinstaller(onefile: bool = False):
    """Ejecuta PyInstaller con el spec file."""
    logger.info("=" * 60)
    logger.info("Iniciando build con PyInstaller...")
    logger.info(f"Modo: {'ONEFILE' if onefile else 'FOLDER'}")
    logger.info("=" * 60)

    # Modificar spec si es onefile (o usar archivo diferente)
    # Por ahora usamos el spec como está (modo carpeta)

    cmd = [
        "pyinstaller",
        str(SPEC_FILE),
        "--clean",
        "--noconfirm",
    ]

    if onefile:
        logger.warning("Modo --onefile requiere modificar el spec file manualmente")
        logger.warning("Por ahora se usará el modo carpeta (recomendado para Tauri)")

    try:
        result = subprocess.run(cmd, cwd=API_SERVER_DIR, check=True)
        logger.info("=" * 60)
        logger.info("✓ Build completado exitosamente")
        logger.info("=" * 60)

        # Mostrar ubicación del ejecutable
        exe_path = DIST_DIR / "narrative-assistant-server" / "narrative-assistant-server.exe"
        if exe_path.exists():
            logger.info(f"Ejecutable: {exe_path}")
            logger.info(f"Tamaño: {exe_path.stat().st_size / (1024 * 1024):.1f} MB")
        else:
            logger.warning("No se encontró el ejecutable en la ubicación esperada")

        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"✗ Error durante el build: {e}")
        return False

def main():
    """Función principal."""
    import argparse

    parser = argparse.ArgumentParser(description="Build del servidor FastAPI con PyInstaller")
    parser.add_argument("--onefile", action="store_true", help="Crear ejecutable único")
    parser.add_argument("--clean", action="store_true", help="Solo limpiar builds anteriores")
    args = parser.parse_args()

    # Limpiar siempre antes de build
    clean_build()

    if args.clean:
        logger.info("Limpieza completada. Saliendo.")
        return 0

    # Verificar modelos
    if not verify_models():
        logger.error("✗ Modelos no encontrados. Build cancelado.")
        return 1

    # Verificar/instalar PyInstaller
    if not install_pyinstaller():
        logger.error("✗ No se pudo instalar PyInstaller. Build cancelado.")
        return 1

    # Ejecutar build
    if not run_pyinstaller(onefile=args.onefile):
        logger.error("✗ Build fallido")
        return 1

    logger.info("=" * 60)
    logger.info("✓✓✓ BUILD COMPLETADO ✓✓✓")
    logger.info("=" * 60)
    logger.info(f"Distribución: {DIST_DIR / 'narrative-assistant-server'}")
    logger.info("")
    logger.info("Siguiente paso: Configurar Tauri sidecar")

    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.warning("\nBuild cancelado por usuario")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error inesperado: {e}", exc_info=True)
        sys.exit(1)
