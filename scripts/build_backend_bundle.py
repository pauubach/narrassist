#!/usr/bin/env python3
"""
Build backend bundle for embedded Python
NO usa PyInstaller - copia scripts directamente
"""
import shutil
import sys
from pathlib import Path

def build_backend_bundle():
    """Copia el backend como bundle de scripts Python"""
    
    repo_root = Path(__file__).parent.parent
    backend_source = repo_root / "api-server"
    src_source = repo_root / "src"
    target_dir = repo_root / "src-tauri" / "binaries" / "backend"
    
    print("=" * 80)
    print("Building Backend Bundle")
    print("=" * 80)
    print(f"Source: {backend_source}")
    print(f"Target: {target_dir}")
    print()
    
    # Limpiar directorio destino
    if target_dir.exists():
        print(f"Limpiando {target_dir}...")
        shutil.rmtree(target_dir)
    
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Copiar api-server
    print("Copiando api-server/...")
    shutil.copytree(backend_source, target_dir / "api-server", 
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))
    
    # Copiar src/narrative_assistant
    print("Copiando src/narrative_assistant/...")
    shutil.copytree(src_source / "narrative_assistant", target_dir / "narrative_assistant",
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))
    
    # Crear launcher script
    launcher_script = target_dir / "start_backend.py"
    launcher_content = '''#!/usr/bin/env python3
"""
Launcher para el backend con Python embebido
"""
import sys
import os
from pathlib import Path

# Añadir el directorio actual al path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir / "api-server"))

# Importar y ejecutar main
if __name__ == "__main__":
    # Cambiar al directorio del backend
    os.chdir(backend_dir / "api-server")
    
    # Importar y ejecutar
    import main
'''
    launcher_script.write_text(launcher_content, encoding='utf-8')
    print(f"[OK] Creado launcher: {launcher_script.name}")
    
    # Crear requirements.txt (dependencias base sin NLP)
    requirements = target_dir / "requirements.txt"
    requirements_content = """# Backend dependencies (base, sin NLP)
fastapi==0.115.12
uvicorn[standard]==0.34.0
pydantic==2.10.4
python-multipart==0.0.20
python-dateutil==2.9.0.post0
ebooklib==0.18
pypdfium2==4.30.1
python-docx==1.1.2
pdfminer.six==20240706
olefile==0.47
charset-normalizer==3.4.0
"""
    requirements.write_text(requirements_content, encoding='utf-8')
    print(f"[OK] Creado requirements.txt")

    # Crear requirements-nlp.txt (NLP con versiones pinned para compatibilidad)
    requirements_nlp = target_dir / "requirements-nlp.txt"
    requirements_nlp_content = """# NLP dependencies with pinned versions for compatibility
# These versions have been tested together and are known to work
# DO NOT upgrade torch to 2.10+ without also upgrading numpy to 2.x

# PyTorch CPU-only (compatible with numpy 1.x)
# Using CPU version to minimize bundle size
--index-url https://download.pytorch.org/whl/cpu
torch==2.5.1

# Switch back to PyPI for remaining packages
--index-url https://pypi.org/simple

# NumPy 1.x (required for compatibility with thinc wheels)
numpy>=1.24.0,<2.0.0

# spaCy and thinc (compatible versions)
spacy>=3.7.0,<3.8.0
thinc>=8.2.0,<8.3.0

# Sentence transformers for embeddings
sentence-transformers>=2.2.0,<3.0.0
"""
    requirements_nlp.write_text(requirements_nlp_content, encoding='utf-8')
    print(f"[OK] Creado requirements-nlp.txt")
    
    # Calcular tamaño
    total_size = sum(f.stat().st_size for f in target_dir.rglob('*') if f.is_file())
    size_mb = total_size / (1024 * 1024)
    
    print()
    print("=" * 80)
    print(f"[OK] Backend bundle creado exitosamente")
    print(f"  Tamaño: {size_mb:.1f} MB")
    print(f"  Ubicación: {target_dir}")
    print("=" * 80)
    
    return 0

if __name__ == "__main__":
    sys.exit(build_backend_bundle())
