#!/usr/bin/env python3
"""
Script para preparar y construir la aplicación con Python embebido
Soporta Windows y macOS
"""
import subprocess
import sys
import platform
from pathlib import Path

def run_command(cmd, cwd=None, description="", shell=True):
    """Ejecuta un comando y muestra el resultado"""
    if description:
        print(f"\n{'='*80}")
        print(f"{description}")
        print(f"{'='*80}\n")
    
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
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

def get_python_embed_executable(repo_root: Path):
    """Retorna el path al ejecutable de Python embebido según la plataforma"""
    python_embed_dir = repo_root / "src-tauri" / "binaries" / "python-embed"
    system = platform.system()
    
    if system == "Windows":
        return python_embed_dir / "python.exe"
    elif system == "Darwin":  # macOS
        # Buscar python3 link o en framework
        python3_link = python_embed_dir / "python3"
        if python3_link.exists():
            return python3_link
        python3_framework = python_embed_dir / "Python.framework" / "Versions" / "Current" / "bin" / "python3"
        if python3_framework.exists():
            return python3_framework
    
    return None

def main():
    """Main entry point"""
    repo_root = Path(__file__).parent.parent
    system = platform.system()
    
    print(f"""
================================================================================
🚀 Building Narrative Assistant with Embedded Python
================================================================================
Platform: {system}
Root: {repo_root}
""")
    
    # 1. Download Python embebido si no está
    python_embed_dir = repo_root / "src-tauri" / "binaries" / "python-embed"
    python_exe = get_python_embed_executable(repo_root)
    
    if not python_exe or not python_exe.exists():
        if not run_command(
            f"{sys.executable} scripts/download_python_embed.py",
            cwd=repo_root,
            description="Step 1/5: Downloading Python embebido"
        ):
            return False
        
        # Recheck
        python_exe = get_python_embed_executable(repo_root)
        if not python_exe or not python_exe.exists():
            print(f"✗ Python embebido no encontrado después de descarga")
            return False
    else:
        print(f"\n✓ Python embebido already exists: {python_exe}\n")
    
    # 2. Instalar pip si no está (solo primera vez)
    pip_check = f'"{python_exe}" -m pip --version'
    result = subprocess.run(pip_check, shell=True, capture_output=True)
    if result.returncode != 0:
        if not run_command(
            f'"{python_exe}" -m ensurepip',
            cwd=repo_root,
            description="Step 2/5: Installing pip"
        ):
            print("⚠️ Warning: pip installation failed, continuing...")
    else:
        print("\n✓ pip already installed\n")
    
    # 3. Build backend bundle
    if not run_command(
        f"{sys.executable} scripts/build_backend_bundle.py",
        cwd=repo_root,
        description="Step 3/5: Building backend bundle"
    ):
        return False
    
    # 4. Build frontend
    if not run_command(
        "npm install && npm run build",
        cwd=repo_root / "frontend",
        description="Step 4/5: Building frontend"
    ):
        return False
    
    # 5. Build Tauri app
    if not run_command(
        "npm run tauri build",
        cwd=repo_root,
        description="Step 5/5: Building Tauri installer"
    ):
        return False
    
    print(f"""
================================================================================
✓ Build completed successfully for {system}!
================================================================================

Installer location:
  {repo_root / "src-tauri" / "target" / "release" / "bundle"}

You can now test the installer on a machine WITHOUT Python installed!
""")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
