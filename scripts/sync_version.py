#!/usr/bin/env python3
"""
Sincroniza la versión desde VERSION a todos los archivos del proyecto.

Uso:
    python scripts/sync_version.py          # Lee VERSION y actualiza todo
    python scripts/sync_version.py 0.7.1    # Establece versión y actualiza todo
    python scripts/sync_version.py --check  # Verifica si todo está sincronizado
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"

# Archivos que contienen la versión
TARGETS = {
    "pyproject.toml": {
        "pattern": r'^version = ".*"',
        "replacement": 'version = "{version}"',
    },
    "frontend/package.json": {
        "json_key": "version",
    },
    "src-tauri/Cargo.toml": {
        "pattern": r'^version = ".*"',
        "replacement": 'version = "{version}"',
        "first_only": True,  # Solo la primera ocurrencia (package version, no deps)
    },
    "src-tauri/tauri.conf.json": {
        "json_key": "version",
    },
    "src-tauri/tauri.conf.dev.json": {
        "json_key": "version",
    },
    "api-server/deps.py": {
        "pattern": r'^BACKEND_VERSION = ".*"',
        "replacement": 'BACKEND_VERSION = "{version}"',
    },
    "src/narrative_assistant/__init__.py": {
        "pattern": r'^_FALLBACK_VERSION = ".*"',
        "replacement": '_FALLBACK_VERSION = "{version}"',
    },
}


def read_version() -> str:
    """Lee la versión del archivo VERSION."""
    return VERSION_FILE.read_text().strip()


def write_version(version: str) -> None:
    """Escribe la versión al archivo VERSION."""
    VERSION_FILE.write_text(version + "\n")


def sync_file(rel_path: str, config: dict, version: str, check_only: bool = False) -> bool:
    """Sincroniza la versión en un archivo. Retorna True si estaba sincronizado."""
    filepath = ROOT / rel_path

    if not filepath.exists():
        print(f"  SKIP  {rel_path} (no existe)")
        return True

    if "json_key" in config:
        return _sync_json(filepath, rel_path, config["json_key"], version, check_only)
    else:
        return _sync_text(filepath, rel_path, config, version, check_only)


def _sync_json(filepath: Path, rel_path: str, key: str, version: str, check_only: bool) -> bool:
    """Sincroniza versión en un archivo JSON."""
    data = json.loads(filepath.read_text(encoding="utf-8"))
    current = data.get(key, "")

    if current == version:
        print(f"  OK    {rel_path} ({current})")
        return True

    if check_only:
        print(f"  DESYNC {rel_path}: {current} != {version}")
        return False

    data[key] = version
    filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  FIXED {rel_path}: {current} -> {version}")
    return False


def _sync_text(filepath: Path, rel_path: str, config: dict, version: str, check_only: bool) -> bool:
    """Sincroniza versión en un archivo de texto via regex."""
    content = filepath.read_text(encoding="utf-8")
    pattern = config["pattern"]
    replacement = config["replacement"].format(version=version)
    first_only = config.get("first_only", False)

    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        print(f"  SKIP  {rel_path} (patrón no encontrado)")
        return True

    current_line = match.group(0)
    if current_line == replacement:
        # Extraer versión actual para mostrar
        ver_match = re.search(r'"([^"]+)"', current_line)
        current = ver_match.group(1) if ver_match else "?"
        print(f"  OK    {rel_path} ({current})")
        return True

    if check_only:
        ver_match = re.search(r'"([^"]+)"', current_line)
        current = ver_match.group(1) if ver_match else "?"
        print(f"  DESYNC {rel_path}: {current} != {version}")
        return False

    if first_only:
        new_content = content[:match.start()] + replacement + content[match.end():]
    else:
        new_content = re.sub(pattern, replacement, content, count=1, flags=re.MULTILINE)

    filepath.write_text(new_content, encoding="utf-8")
    ver_match = re.search(r'"([^"]+)"', current_line)
    current = ver_match.group(1) if ver_match else "?"
    print(f"  FIXED {rel_path}: {current} -> {version}")
    return False


def main():
    check_only = "--check" in sys.argv

    # Determinar versión
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        version = sys.argv[1]
        if not check_only:
            write_version(version)
            print(f"VERSION set to: {version}")
    else:
        version = read_version()
        print(f"VERSION: {version}")

    print()
    all_synced = True
    for rel_path, config in TARGETS.items():
        synced = sync_file(rel_path, config, version, check_only)
        if not synced:
            all_synced = False

    print()
    if check_only:
        if all_synced:
            print("All files are in sync.")
        else:
            print("Some files are out of sync! Run: python scripts/sync_version.py")
            sys.exit(1)
    else:
        print(f"All files synced to {version}")


if __name__ == "__main__":
    main()
