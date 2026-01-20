#!/usr/bin/env python3
"""
Script para construir el sidecar de Narrative Assistant con PyInstaller.

Este script empaqueta el servidor FastAPI como un ejecutable standalone
que puede ser usado como sidecar de Tauri.

NOTA: El sidecar se construye SIN las dependencias NLP pesadas (spacy, torch, etc.)
Los modelos NLP se descargan automáticamente al primer inicio de la aplicación.

Uso:
    python scripts/build_sidecar.py [--debug] [--clean]

Opciones:
    --debug     Incluir simbolos de depuracion
    --clean     Limpiar builds anteriores antes de construir
"""

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def get_target_triple() -> str:
    """Obtiene el target triple para la plataforma actual."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "windows":
        if machine in ("amd64", "x86_64"):
            return "x86_64-pc-windows-msvc"
        elif machine in ("arm64", "aarch64"):
            return "aarch64-pc-windows-msvc"
        else:
            return "i686-pc-windows-msvc"
    elif system == "darwin":
        if machine in ("arm64", "aarch64"):
            return "aarch64-apple-darwin"
        else:
            return "x86_64-apple-darwin"
    elif system == "linux":
        if machine in ("amd64", "x86_64"):
            return "x86_64-unknown-linux-gnu"
        elif machine in ("arm64", "aarch64"):
            return "aarch64-unknown-linux-gnu"
        else:
            return "i686-unknown-linux-gnu"
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


def clean_build_dirs(project_root: Path):
    """Limpia directorios de builds anteriores."""
    dirs_to_clean = [
        project_root / "build",
        project_root / "dist",
        project_root / "api-server" / "build",
        project_root / "api-server" / "dist",
    ]

    for dir_path in dirs_to_clean:
        if dir_path.exists():
            print(f"Limpiando {dir_path}...")
            shutil.rmtree(dir_path)


def build_sidecar(project_root: Path, debug: bool = False, target: str | None = None) -> Path:
    """Construye el sidecar con PyInstaller."""
    target_triple = target or get_target_triple()
    system = platform.system().lower()

    # Nombre del ejecutable
    exe_name = f"narrative-assistant-server-{target_triple}"
    if system == "windows":
        exe_name += ".exe"

    # Directorio de salida para Tauri
    output_dir = project_root / "src-tauri" / "binaries"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Archivo principal
    main_script = project_root / "api-server" / "main.py"
    if not main_script.exists():
        raise FileNotFoundError(f"No se encontro {main_script}")

    # Construir comando PyInstaller
    # IMPORTANTE: Excluimos las dependencias pesadas de NLP
    # Los modelos se descargan al primer inicio
    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", f"narrative-assistant-server-{target_triple}",
        "--distpath", str(output_dir),
        "--workpath", str(project_root / "build" / "pyinstaller"),
        "--specpath", str(project_root / "build"),
        # Incluir el paquete narrative_assistant
        "--paths", str(project_root / "src"),
        # Hidden imports para FastAPI/uvicorn
        "--hidden-import", "uvicorn",
        "--hidden-import", "uvicorn.main",
        "--hidden-import", "uvicorn.config",
        "--hidden-import", "uvicorn.server",
        "--hidden-import", "fastapi",
        "--hidden-import", "starlette",
        "--hidden-import", "starlette.routing",
        "--hidden-import", "starlette.responses",
        "--hidden-import", "starlette.middleware",
        "--hidden-import", "starlette.middleware.cors",
        "--hidden-import", "pydantic",
        "--hidden-import", "pydantic_core",
        "--hidden-import", "anyio",
        "--hidden-import", "anyio._backends",
        "--hidden-import", "anyio._backends._asyncio",
        "--hidden-import", "httptools",
        "--hidden-import", "websockets",
        "--hidden-import", "watchfiles",
        # Hidden imports para narrative_assistant (core only)
        "--hidden-import", "narrative_assistant",
        "--hidden-import", "narrative_assistant.core",
        "--hidden-import", "narrative_assistant.core.config",
        "--hidden-import", "narrative_assistant.core.errors",
        "--hidden-import", "narrative_assistant.persistence",
        "--hidden-import", "narrative_assistant.persistence.database",
        "--hidden-import", "narrative_assistant.persistence.project",
        "--hidden-import", "narrative_assistant.persistence.chapter",
        "--hidden-import", "narrative_assistant.entities",
        "--hidden-import", "narrative_assistant.entities.repository",
        "--hidden-import", "narrative_assistant.entities.models",
        "--hidden-import", "narrative_assistant.alerts",
        "--hidden-import", "narrative_assistant.alerts.repository",
        "--hidden-import", "narrative_assistant.alerts.models",
        "--hidden-import", "narrative_assistant.parsers",
        "--hidden-import", "narrative_assistant.parsers.base",
        "--hidden-import", "narrative_assistant.parsers.docx_parser",
        # Python-docx for document parsing
        "--hidden-import", "docx",
        "--hidden-import", "lxml",
        # SQLite
        "--hidden-import", "sqlite3",
        # Excluir modulos pesados que NO necesitamos en el sidecar
        # Los modelos NLP se cargan dinámicamente cuando se necesitan
        "--exclude-module", "torch",
        "--exclude-module", "torchvision",
        "--exclude-module", "torchaudio",
        "--exclude-module", "nvidia",
        "--exclude-module", "triton",
        "--exclude-module", "tensorboard",
        "--exclude-module", "tensorflow",
        "--exclude-module", "keras",
        "--exclude-module", "spacy",
        "--exclude-module", "thinc",
        "--exclude-module", "sentence_transformers",
        "--exclude-module", "transformers",
        "--exclude-module", "huggingface_hub",
        "--exclude-module", "tokenizers",
        "--exclude-module", "safetensors",
        "--exclude-module", "scipy",
        "--exclude-module", "sklearn",
        "--exclude-module", "scikit-learn",
        "--exclude-module", "numpy",  # Se incluirá solo si es necesario
        "--exclude-module", "pandas",
        "--exclude-module", "matplotlib",
        "--exclude-module", "PIL",
        "--exclude-module", "cv2",
        "--exclude-module", "opencv",
        "--exclude-module", "tkinter",
        "--exclude-module", "notebook",
        "--exclude-module", "jupyter",
        "--exclude-module", "IPython",
        "--exclude-module", "pytest",
        "--exclude-module", "test",
        "--exclude-module", "tests",
        "--exclude-module", "sympy",
        "--exclude-module", "networkx",
        # Consola oculta en Windows release
        *(["--noconsole"] if system == "windows" and not debug else []),
        # Debug
        *(["--debug", "all"] if debug else []),
        # Script principal
        str(main_script),
    ]

    # Filtrar argumentos vacios
    pyinstaller_args = [arg for arg in pyinstaller_args if arg]

    print(f"Construyendo sidecar para {target_triple}...")
    print(f"Comando: {' '.join(pyinstaller_args[:15])}...")
    print("")
    print("NOTA: Excluyendo dependencias NLP pesadas (torch, spacy, transformers)")
    print("      Los modelos se descargaran al primer inicio de la aplicacion.")
    print("")

    result = subprocess.run(pyinstaller_args, cwd=project_root)

    if result.returncode != 0:
        raise RuntimeError("PyInstaller fallo")

    output_path = output_dir / exe_name
    if not output_path.exists():
        # Buscar el archivo generado
        for f in output_dir.iterdir():
            if f.name.startswith("narrative-assistant-server"):
                if f.name != exe_name:
                    # Renombrar al nombre correcto
                    f.rename(output_path)
                    break

    if output_path.exists():
        size_mb = output_path.stat().st_size / 1024 / 1024
        print(f"\nSidecar construido: {output_path}")
        print(f"Tamano: {size_mb:.1f} MB")

        if size_mb > 100:
            print(f"\nADVERTENCIA: El ejecutable es grande ({size_mb:.0f} MB).")
            print("Considera revisar las exclusiones si es demasiado grande.")

        return output_path
    else:
        raise RuntimeError(f"No se genero el ejecutable en {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Construir sidecar de Narrative Assistant")
    parser.add_argument("--debug", action="store_true", help="Build con simbolos de debug")
    parser.add_argument("--clean", action="store_true", help="Limpiar builds anteriores")
    parser.add_argument("--target", type=str, help="Target triple (ej: x86_64-apple-darwin)")
    args = parser.parse_args()

    # Encontrar raiz del proyecto
    project_root = Path(__file__).parent.parent
    if not (project_root / "src-tauri").exists():
        raise RuntimeError("No se encontro src-tauri. Ejecutar desde la raiz del proyecto.")

    target = args.target or get_target_triple()
    print(f"Proyecto: {project_root}")
    print(f"Target: {target}")

    if args.clean:
        clean_build_dirs(project_root)

    try:
        output_path = build_sidecar(project_root, debug=args.debug, target=args.target)

        print("\n[OK] Build completado exitosamente")
        print(f"Ejecutable: {output_path}")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
