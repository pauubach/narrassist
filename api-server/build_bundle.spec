# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file para empaquetar el servidor FastAPI + backend narrative_assistant.

Uso:
    pyinstaller build_bundle.spec

Genera:
    dist/narrative-assistant-server/ (carpeta con ejecutable y dependencias)
    dist/narrative-assistant-server.exe (ejecutable único - opcional)
"""

import sys
from pathlib import Path

# Rutas del proyecto
project_root = Path.cwd().parent
src_path = project_root / "src"
models_path = project_root / "models"

block_cipher = None

# ============================================================================
# Análisis de dependencias
# ============================================================================

a = Analysis(
    ['start_server.py'],
    pathex=[str(project_root / 'api-server'), str(src_path)],
    binaries=[],
    datas=[
        # Incluir modelos NLP (CRÍTICO para funcionamiento offline)
        (str(models_path / 'spacy' / 'es_core_news_lg'), 'models/spacy/es_core_news_lg'),
        (str(models_path / 'embeddings' / 'paraphrase-multilingual-MiniLM-L12-v2'), 'models/embeddings/paraphrase-multilingual-MiniLM-L12-v2'),

        # Incluir archivos de configuración si existen
        # (str(project_root / 'config.yaml'), '.'),
    ],
    hiddenimports=[
        # FastAPI y dependencias
        'fastapi',
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'pydantic',
        'starlette',

        # Backend narrative_assistant
        'narrative_assistant',
        'narrative_assistant.core',
        'narrative_assistant.persistence',
        'narrative_assistant.parsers',
        'narrative_assistant.nlp',
        'narrative_assistant.entities',
        'narrative_assistant.alerts',
        'narrative_assistant.exporters',

        # NLP
        'spacy',
        'sentence_transformers',
        'torch',
        'transformers',

        # Utilidades
        'docx',
        'markdown',
        'pypdf',
        'ebooklib',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Excluir módulos innecesarios para reducir tamaño
        'matplotlib',
        'IPython',
        'notebook',
        'PIL',  # Pillow (a menos que se use)
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ============================================================================
# Crear PYZ (archivo Python comprimido)
# ============================================================================

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ============================================================================
# Ejecutable
# ============================================================================

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='narrative-assistant-server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # True para ver logs, False para sin consola
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Añadir icono si se desea
)

# ============================================================================
# Colección de archivos (modo carpeta)
# ============================================================================

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='narrative-assistant-server',
)

# ============================================================================
# Ejecutable único (opcional - comentar si no se desea)
# ============================================================================

# NOTA: El modo --onefile puede tardar más en iniciar porque
# descomprime todo a un directorio temporal cada vez.
# Para Tauri, se recomienda usar el modo carpeta (COLLECT) anterior.

# exe_onefile = EXE(
#     pyz,
#     a.scripts,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     [],
#     name='narrative-assistant-server',
#     debug=False,
#     bootloader_ignore_signals=False,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     runtime_tmpdir=None,
#     console=True,
#     disable_windowed_traceback=False,
#     argv_emulation=False,
#     target_arch=None,
#     codesign_identity=None,
#     entitlements_file=None,
# )
