#!/usr/bin/env python3
"""
Script para preparar y construir la aplicación con Python embebido
"""
import subprocess
import sys
from pathlib import Path

def run_command(cmd, cwd=None, description=""):
    """Ejecuta un comando y muestra el resultado"""
    if description:
        print(f"\n{'='*80}")
        print(f"{description}")
        print(f"{'='*80}\n")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            check=True,
            capture_output=False,
            text=True
        )
        print(f"✓ {description} completado exitosamente\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ ERROR en {description}")
        print(f"  Código de salida: {e.returncode}")
        return False

def main():
    repo_root = Path(__file__).parent.parent
    
    print(f"""
================================================================================
🚀 Building Narrative Assistant with Embedded Python
================================================================================
Root: {repo_root}
""")
    
    # 1. Download Python embebido si no está
    python_embed_dir = repo_root / "src-tauri" / "binaries" / "python-embed"
    if not python_embed_dir.exists() or not (python_embed_dir / "python.exe").exists():
        if not run_command(
            "python scripts/download_python_embed.py",
            cwd=repo_root,
            description="Step 1/4: Downloading Python embebido"
        ):
            return False
    else:
        print("\n✓ Python embebido already exists, skipping download\n")
    
    # 2. Build backend bundle
    if not run_command(
        "python scripts/build_backend_bundle.py",
        cwd=repo_root,
        description="Step 2/4: Building backend bundle"
    ):
        return False
    
    # 3. Build frontend
    if not run_command(
        "npm install && npm run build",
        cwd=repo_root / "frontend",
        description="Step 3/4: Building frontend"
    ):
        return False
    
    # 4. Build Tauri app
    if not run_command(
        "npm run tauri build",
        cwd=repo_root,
        description="Step 4/4: Building Tauri installer"
    ):
        return False
    
    print(f"""
================================================================================
✓ Build completed successfully!
================================================================================

Installer location:
  {repo_root / "src-tauri" / "target" / "release" / "bundle"}

You can now test the installer on a machine WITHOUT Python installed!
""")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
