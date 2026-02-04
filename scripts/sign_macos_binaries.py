#!/usr/bin/env python3
"""
Script para firmar todos los binarios (.so, .dylib) en el Python Framework embebido.
Debe ejecutarse DESPUÉS de instalar los paquetes pip.
"""
import subprocess
import sys
from pathlib import Path


def sign_binary(binary_path: Path) -> bool:
    """Firma un binario con ad-hoc signing"""
    try:
        result = subprocess.run(
            ["codesign", "--force", "--sign", "-", str(binary_path)],
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0
    except Exception:
        return False


def sign_all_binaries(framework_dir: Path) -> int:
    """
    Firma todos los .so y .dylib en el Python Framework.
    
    Args:
        framework_dir: Ruta al directorio que contiene Python.framework
        
    Returns:
        Número de binarios firmados
    """
    python_framework = framework_dir / "Python.framework"
    if not python_framework.exists():
        print(f"❌ Python.framework no encontrado en {framework_dir}")
        return 0
    
    print(f"\n{'='*80}")
    print(f"🔏 Firmando binarios en {framework_dir}")
    print(f"{'='*80}\n")
    
    # Encontrar todos los binarios
    so_files = list(python_framework.rglob("*.so"))
    dylib_files = list(python_framework.rglob("*.dylib"))
    
    all_binaries = so_files + dylib_files
    
    print(f"📦 Encontrados {len(so_files)} archivos .so")
    print(f"📦 Encontrados {len(dylib_files)} archivos .dylib")
    print(f"📦 Total: {len(all_binaries)} binarios a firmar\n")
    
    signed_count = 0
    failed_count = 0
    
    for binary in all_binaries:
        if sign_binary(binary):
            signed_count += 1
        else:
            failed_count += 1
            print(f"  ⚠️  Fallo al firmar: {binary.name}")
    
    print(f"\n✅ Firmados: {signed_count}")
    if failed_count > 0:
        print(f"⚠️  Fallos: {failed_count}")
    
    # También firmar python3.bin en la raíz si existe (el wrapper shell python3 no necesita firma)
    python3_bin = framework_dir / "python3.bin"
    if python3_bin.exists():
        if sign_binary(python3_bin):
            print(f"✅ python3.bin firmado")
            signed_count += 1
    
    # Fallback: si aún existe python3 como binario (no shell script)
    python3_root = framework_dir / "python3"
    if python3_root.exists() and not python3_root.is_symlink():
        # Verificar si es binario o shell script
        with open(python3_root, 'rb') as f:
            magic = f.read(4)
        if magic != b'#!/b':  # No es shell script
            if sign_binary(python3_root):
                print(f"✅ python3 en raíz firmado")
                signed_count += 1
    
    print(f"\n{'='*80}")
    print(f"✅ Firma completada: {signed_count} binarios")
    print(f"{'='*80}\n")
    
    return signed_count


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
        return 1
    
    signed = sign_all_binaries(target_dir)
    return 0 if signed > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
