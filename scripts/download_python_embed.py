#!/usr/bin/env python3
"""
Script para descargar Python embebido para Windows
Se usará como backend ejecutable sin PyInstaller
"""
import urllib.request
import zipfile
import os
import sys
from pathlib import Path

PYTHON_VERSION = "3.12.7"
PYTHON_EMBED_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip"

def download_python_embed(target_dir: Path):
    """
    Descarga Python embebido para Windows y lo extrae
    
    Args:
        target_dir: Directorio donde extraer Python embebido
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    zip_path = target_dir / f"python-{PYTHON_VERSION}-embed.zip"
    
    print(f"Descargando Python {PYTHON_VERSION} embebido...")
    print(f"URL: {PYTHON_EMBED_URL}")
    
    # Descargar
    try:
        urllib.request.urlretrieve(PYTHON_EMBED_URL, zip_path)
        print(f"✓ Descargado: {zip_path}")
    except Exception as e:
        print(f"✗ Error descargando: {e}")
        return False
    
    # Extraer
    print(f"Extrayendo a {target_dir}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(target_dir)
        print(f"✓ Extraído exitosamente")
        
        # Eliminar zip
        zip_path.unlink()
        
        # Crear archivo _pth para configurar paths
        python_major_minor = PYTHON_VERSION.rsplit('.', 1)[0].replace('.', '')
        pth_file = target_dir / f"python{python_major_minor}._pth"
        if not pth_file.exists():
            # Buscar el archivo .pth existente
            pth_files = list(target_dir.glob("python*._pth"))
            if pth_files:
                pth_file = pth_files[0]
                print(f"Encontrado archivo PTH: {pth_file.name}")
                
                # Modificar para incluir site-packages
                content = pth_file.read_text()
                if "import site" not in content:
                    content += "\nimport site\n"
                    pth_file.write_text(content)
                    print("✓ Configurado import site")
        
        # Verificar que python.exe existe
        python_exe = target_dir / "python.exe"
        if python_exe.exists():
            print(f"✓ Python embebido listo: {python_exe}")
            return True
        else:
            print(f"✗ No se encontró python.exe en {target_dir}")
            return False
            
    except Exception as e:
        print(f"✗ Error extrayendo: {e}")
        return False

def main():
    """Main entry point"""
    repo_root = Path(__file__).parent.parent
    target_dir = repo_root / "src-tauri" / "binaries" / "python-embed"
    
    print("=" * 80)
    print("Descargando Python Embebido para Windows")
    print("=" * 80)
    print(f"Versión: {PYTHON_VERSION}")
    print(f"Destino: {target_dir}")
    print()
    
    if download_python_embed(target_dir):
        print()
        print("=" * 80)
        print("✓ Python embebido descargado exitosamente")
        print("=" * 80)
        return 0
    else:
        print()
        print("=" * 80)
        print("✗ Error descargando Python embebido")
        print("=" * 80)
        return 1

if __name__ == "__main__":
    sys.exit(main())
