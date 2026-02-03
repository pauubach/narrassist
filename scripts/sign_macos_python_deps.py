#!/usr/bin/env python3
"""
Script para firmar módulos .so y .dylib instalados en Python embebido en macOS.
Esto es necesario porque macOS AMFI (Apple Mobile File Integrity) mata procesos
que cargan código no firmado.

Ejecutar después de instalar dependencias con pip.
"""
import subprocess
import sys
from pathlib import Path


def codesign_file(file_path: Path) -> bool:
    """Firma un archivo con ad-hoc signature"""
    try:
        result = subprocess.run(
            ["codesign", "--force", "--sign", "-", str(file_path)],
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0
    except Exception:
        return False


def sign_python_embed_dependencies(target_dir: Path) -> bool:
    """
    Firma todos los .so y .dylib en un Python embebido
    
    Args:
        target_dir: Directorio que contiene Python.framework
    """
    python_framework = target_dir / "Python.framework"
    if not python_framework.exists():
        print(f"❌ Python.framework no encontrado en {target_dir}")
        return False

    print(f"\n{'='*80}")
    print(f"🔏 Firmando módulos en {target_dir}")
    print(f"{'='*80}\n")

    # Encontrar todos los .so
    so_files = list(python_framework.rglob("*.so"))
    print(f"📦 Encontrados {len(so_files)} archivos .so")
    
    signed_so = 0
    failed_so = 0
    for so_file in so_files:
        if codesign_file(so_file):
            signed_so += 1
        else:
            failed_so += 1
            print(f"  ⚠️  Error firmando: {so_file.name}")
    
    print(f"  ✅ Firmados: {signed_so}, ⚠️ Fallidos: {failed_so}")

    # Encontrar todos los .dylib
    dylib_files = list(python_framework.rglob("*.dylib"))
    print(f"\n📦 Encontrados {len(dylib_files)} archivos .dylib")
    
    signed_dylib = 0
    failed_dylib = 0
    for dylib_file in dylib_files:
        if codesign_file(dylib_file):
            signed_dylib += 1
        else:
            failed_dylib += 1
            print(f"  ⚠️  Error firmando: {dylib_file.name}")
    
    print(f"  ✅ Firmados: {signed_dylib}, ⚠️ Fallidos: {failed_dylib}")

    # Firmar también python3.bin si existe
    python3_bin = target_dir / "python3.bin"
    if python3_bin.exists():
        if codesign_file(python3_bin):
            print(f"\n✅ python3.bin firmado")
        else:
            print(f"\n⚠️  Error firmando python3.bin")

    print(f"\n{'='*80}")
    print(f"✅ Firma completada")
    print(f"   Total: {signed_so + signed_dylib} archivos firmados")
    print(f"{'='*80}\n")

    return failed_so == 0 and failed_dylib == 0


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        target_dir = Path(sys.argv[1])
    else:
        # Default: src-tauri/binaries/python-embed
        repo_root = Path(__file__).parent.parent
        target_dir = repo_root / "src-tauri" / "binaries" / "python-embed"

    if not target_dir.exists():
        print(f"❌ Directorio no encontrado: {target_dir}")
        print(f"\nUso: python {sys.argv[0]} [directorio_python_embed]")
        return 1

    success = sign_python_embed_dependencies(target_dir)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
