#!/usr/bin/env python3
"""
Firmar binarios Mach-O embebidos con ad-hoc signing.

Uso:
    python scripts/sign_macos_binaries.py <dir1> [<dir2> ...]

Si no se pasan directorios, firma por defecto:
    - src-tauri/binaries/python-embed
    - src-tauri/binaries/java-jre
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path


MACHO_SUFFIXES = {".so", ".dylib", ".jnilib"}
MACHO_MAGICS = {
    b"\xfe\xed\xfa\xce",
    b"\xfe\xed\xfa\xcf",
    b"\xce\xfa\xed\xfe",
    b"\xcf\xfa\xed\xfe",
    b"\xca\xfe\xba\xbe",
    b"\xbe\xba\xfe\xca",
    b"\xca\xfe\xba\xbf",
    b"\xbf\xba\xfe\xca",
}


def sign_binary(binary_path: Path) -> bool:
    """Firma un binario con ad-hoc signing."""
    try:
        result = subprocess.run(
            ["codesign", "--force", "--sign", "-", str(binary_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def is_signable_binary(path: Path) -> bool:
    """Detecta si un fichero debe firmarse."""
    if not path.is_file():
        return False
    if path.suffix.lower() in MACHO_SUFFIXES:
        return True
    try:
        mode = path.stat().st_mode
        if not (mode & stat.S_IXUSR):
            return False
        with path.open("rb") as handle:
            return handle.read(4) in MACHO_MAGICS
    except OSError:
        return False


def collect_signable_binaries(root: Path) -> list[Path]:
    """Recopilar binarios firmables bajo un directorio."""
    return sorted(path for path in root.rglob("*") if is_signable_binary(path))


def sign_all_binaries(root: Path) -> int:
    """Firma todos los binarios firmables bajo `root`."""
    if not root.exists():
        print(f"[ERROR] Directorio no encontrado: {root}")
        return 0

    binaries = collect_signable_binaries(root)
    print(f"\n{'=' * 80}")
    print(f"Firmando binarios en {root}")
    print(f"{'=' * 80}\n")
    print(f"Total binarios a firmar: {len(binaries)}\n")

    signed_count = 0
    failed_count = 0

    for binary in binaries:
        if sign_binary(binary):
            signed_count += 1
        else:
            failed_count += 1
            print(f"[WARN] Fallo al firmar: {binary}")

    print(f"\nFirmados: {signed_count}")
    if failed_count > 0:
        print(f"Fallos: {failed_count}")
    print(f"\n{'=' * 80}")
    print(f"Firma completada para {root}")
    print(f"{'=' * 80}\n")
    return signed_count


def default_targets(repo_root: Path) -> list[Path]:
    """Directorios por defecto a firmar."""
    return [
        repo_root / "src-tauri" / "binaries" / "python-embed",
        repo_root / "src-tauri" / "binaries" / "java-jre",
    ]


def main() -> int:
    repo_root = Path(__file__).parent.parent
    targets = [Path(arg) for arg in sys.argv[1:]] or default_targets(repo_root)

    total_signed = 0
    for target in targets:
        if target.exists():
            total_signed += sign_all_binaries(target)
        else:
            print(f"[SKIP] No existe {target}")

    return 0 if total_signed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
