#!/usr/bin/env python3
"""
Script para descargar Python embebido/portable para Windows y macOS
Se usará como backend ejecutable sin PyInstaller
"""
import urllib.request
import zipfile
import tarfile
import subprocess
import shutil
import os
import sys
import platform
from pathlib import Path

PYTHON_VERSION = "3.12.7"

# URLs por plataforma
PYTHON_URLS = {
    "Windows": f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip",
    "Darwin": f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-macos11.pkg",
}

def download_windows_embed(target_dir: Path):
    """Descarga Python embebido para Windows"""
    url = PYTHON_URLS["Windows"]
    zip_path = target_dir / f"python-{PYTHON_VERSION}-embed.zip"
    
    print(f"Descargando Python {PYTHON_VERSION} embebido para Windows...")
    print(f"URL: {url}")
    
    # Descargar
    try:
        urllib.request.urlretrieve(url, zip_path)
        print(f"[OK] Descargado: {zip_path}")
    except Exception as e:
        print(f"[ERROR] Error descargando: {e}")
        return False
    
    # Extraer
    print(f"Extrayendo a {target_dir}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(target_dir)
        print(f"[OK] Extraido exitosamente")
        
        # Eliminar zip
        zip_path.unlink()
        
        # Configurar archivo _pth para habilitar site-packages
        python_major_minor = PYTHON_VERSION.rsplit('.', 1)[0].replace('.', '')
        pth_files = list(target_dir.glob("python*._pth"))
        if pth_files:
            pth_file = pth_files[0]
            print(f"Configurando {pth_file.name}...")
            
            content = pth_file.read_text()
            if "import site" not in content:
                # Uncomment or add "import site"
                content = content.replace("# import site", "import site")
                if "import site" not in content:
                    content += "\nimport site\n"
                pth_file.write_text(content)
                print("[OK] Habilitado import site para pip")
        
        # Verificar python.exe
        python_exe = target_dir / "python.exe"
        if python_exe.exists():
            print(f"[OK] Python Windows embebido listo: {python_exe}")
            return True
        else:
            print(f"[ERROR] No se encontro python.exe")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error extrayendo: {e}")
        return False

def download_macos_framework(target_dir: Path):
    """Descarga e instala Python Framework para macOS"""
    url = PYTHON_URLS["Darwin"]
    pkg_path = target_dir / f"python-{PYTHON_VERSION}-macos.pkg"
    
    print(f"Descargando Python {PYTHON_VERSION} para macOS...")
    print(f"URL: {url}")
    
    # Descargar
    try:
        urllib.request.urlretrieve(url, pkg_path)
        print(f"[OK] Descargado: {pkg_path}")
    except Exception as e:
        print(f"[ERROR] Error descargando: {e}")
        return False
    
    # Extraer Python.framework del .pkg usando installer
    print(f"Extrayendo Python.framework...")
    
    try:
        # Crear directorio temporal para extraer
        temp_dir = target_dir / "temp_extract"
        temp_dir.mkdir(exist_ok=True)
        
        # Usar xar para expandir el .pkg (alternativa a pkgutil)
        print("Extrayendo .pkg con xar...")
        subprocess.run([
            "xar", "-xf",
            str(pkg_path),
            "-C", str(temp_dir)
        ], check=True)
        
        # Buscar y extraer el Payload que contiene Python.framework
        payloads = list(temp_dir.glob("**/Payload"))
        if not payloads:
            # Intentar con nombre alternativo
            payloads = list(temp_dir.glob("**/*.pkg/Payload"))
        
        framework_extracted = False
        for payload in payloads:
            print(f"Extrayendo payload: {payload}")
            # Extraer con cpio
            result = subprocess.run(
                f"cd {temp_dir} && cat {payload.relative_to(temp_dir)} | gunzip -dc | cpio -i 2>/dev/null",
                shell=True,
                capture_output=True
            )
            
            # Buscar Python.framework
            framework_src = temp_dir / "Library" / "Frameworks" / "Python.framework"
            if framework_src.exists():
                framework_dst = target_dir / "Python.framework"
                if framework_dst.exists():
                    shutil.rmtree(framework_dst)
                shutil.move(str(framework_src), str(framework_dst))
                print(f"[OK] Python.framework extraido")
                framework_extracted = True
                break
        
        if framework_extracted:
            # Limpiar
            shutil.rmtree(temp_dir)
            pkg_path.unlink()
            
            # Crear symlink a python3
            framework_dst = target_dir / "Python.framework"
            python_bin = framework_dst / "Versions" / "Current" / "bin" / "python3"
            python_link = target_dir / "python3"
            if python_bin.exists():
                if python_link.exists():
                    python_link.unlink()
                python_link.symlink_to(python_bin)
                print(f"[OK] Python macOS listo: {python_link}")
                return True
            else:
                print(f"[ERROR] No se encontro python3 en framework")
                return False
        else:
            print(f"[ERROR] No se encontro Python.framework en ningún payload")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error extrayendo framework: {e}")
        print(f"  Nota: En macOS, puede ser necesario instalar manualmente:")
        print(f"  1. Instalar Python oficial desde python.org")
        print(f"  2. Copiar /Library/Frameworks/Python.framework a src-tauri/binaries/python-embed/")
        return False

def download_python_embed(target_dir: Path):
    """
    Descarga Python embebido para la plataforma actual
    
    Args:
        target_dir: Directorio donde extraer Python embebido
    """
    system = platform.system()
    
    if system not in PYTHON_URLS:
        print(f"[ERROR] Sistema operativo no soportado: {system}")
        print(f"  Soportados: {', '.join(PYTHON_URLS.keys())}")
        print(f"\n  Para Linux, considere usar Python del sistema")
        return False
    
    target_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*80}")
    print(f"Descargando Python {PYTHON_VERSION} para {system}")
    print(f"Destino: {target_dir}")
    print(f"{'='*80}\n")
    
    if system == "Windows":
        return download_windows_embed(target_dir)
    elif system == "Darwin":
        return download_macos_framework(target_dir)

def main():
    """Main entry point"""
    repo_root = Path(__file__).parent.parent
    target_dir = repo_root / "src-tauri" / "binaries" / "python-embed"
    
    success = download_python_embed(target_dir)
    
    if success:
        print(f"\n{'='*80}")
        print("[OK] Python embebido descargado exitosamente")
        print(f"{'='*80}")
        
        # Instrucciones post-instalación
        system = platform.system()
        if system == "Windows":
            print("\nProximos pasos:")
            print("1. cd src-tauri/binaries/python-embed")
            print("2. curl -o get-pip.py https://bootstrap.pypa.io/get-pip.py")
            print("3. .\\python.exe get-pip.py")
            print("4. .\\python.exe -m pip install --upgrade pip setuptools wheel")
            print("5. .\\python.exe -m pip install -r ../backend/requirements.txt")
        elif system == "Darwin":
            print("\nProximos pasos:")
            print("1. cd src-tauri/binaries/python-embed")
            print("2. curl -o get-pip.py https://bootstrap.pypa.io/get-pip.py")
            print("3. ./python3 get-pip.py")
            print("4. ./python3 -m pip install --upgrade pip setuptools wheel")
            print("5. ./python3 -m pip install -r ../backend/requirements.txt")
        
        return 0
    else:
        print(f"\n{'='*80}")
        print("[ERROR] Error descargando Python embebido")
        print(f"{'='*80}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
