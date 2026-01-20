#!/usr/bin/env python3
"""
Script para construir el sidecar de Narrative Assistant con PyInstaller.

Este script empaqueta el servidor FastAPI como un ejecutable standalone
que puede ser usado como sidecar de Tauri.

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


def build_sidecar(project_root: Path, debug: bool = False) -> Path:
    """Construye el sidecar con PyInstaller."""
    target_triple = get_target_triple()
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
    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", f"narrative-assistant-server-{target_triple}",
        "--distpath", str(output_dir),
        "--workpath", str(project_root / "build" / "pyinstaller"),
        "--specpath", str(project_root / "build"),
        # Incluir el paquete narrative_assistant
        "--paths", str(project_root / "src"),
        # Ocultos imports necesarios
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "narrative_assistant",
        "--hidden-import", "narrative_assistant.core",
        "--hidden-import", "narrative_assistant.persistence",
        "--hidden-import", "narrative_assistant.parsers",
        "--hidden-import", "narrative_assistant.nlp",
        "--hidden-import", "narrative_assistant.entities",
        "--hidden-import", "narrative_assistant.alerts",
        "--hidden-import", "spacy",
        "--hidden-import", "sentence_transformers",
        # Excluir modulos no necesarios para reducir tamano
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "PIL",
        "--exclude-module", "notebook",
        "--exclude-module", "jupyter",
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
    print(f"Comando: {' '.join(pyinstaller_args[:10])}...")

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
        print(f"Sidecar construido: {output_path}")
        print(f"Tamano: {output_path.stat().st_size / 1024 / 1024:.1f} MB")
        return output_path
    else:
        raise RuntimeError(f"No se genero el ejecutable en {output_path}")


def update_tauri_config(project_root: Path):
    """Actualiza tauri.conf.json para incluir el sidecar."""
    import json

    config_path = project_root / "src-tauri" / "tauri.conf.json"
    if not config_path.exists():
        print("No se encontro tauri.conf.json")
        return

    with open(config_path) as f:
        config = json.load(f)

    # Agregar externalBin si no existe
    if "bundle" not in config:
        config["bundle"] = {}

    config["bundle"]["externalBin"] = ["binaries/narrative-assistant-server"]

    # Agregar scope de shell si no existe
    if "plugins" not in config:
        config["plugins"] = {}
    if "shell" not in config["plugins"]:
        config["plugins"]["shell"] = {}

    config["plugins"]["shell"]["scope"] = [
        {
            "name": "binaries/narrative-assistant-server",
            "sidecar": True
        }
    ]

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"Actualizado {config_path}")


def main():
    parser = argparse.ArgumentParser(description="Construir sidecar de Narrative Assistant")
    parser.add_argument("--debug", action="store_true", help="Build con simbolos de debug")
    parser.add_argument("--clean", action="store_true", help="Limpiar builds anteriores")
    parser.add_argument("--update-config", action="store_true", help="Actualizar tauri.conf.json")
    args = parser.parse_args()

    # Encontrar raiz del proyecto
    project_root = Path(__file__).parent.parent
    if not (project_root / "src-tauri").exists():
        raise RuntimeError("No se encontro src-tauri. Ejecutar desde la raiz del proyecto.")

    print(f"Proyecto: {project_root}")
    print(f"Target: {get_target_triple()}")

    if args.clean:
        clean_build_dirs(project_root)

    try:
        output_path = build_sidecar(project_root, debug=args.debug)

        if args.update_config:
            update_tauri_config(project_root)

        print("\n[OK] Build completado exitosamente")
        print(f"Ejecutable: {output_path}")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
