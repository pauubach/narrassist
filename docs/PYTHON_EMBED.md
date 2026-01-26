# Python Embebido - Narrative Assistant

> **Estado**: ✅ Funcional (v0.3.0+)
> **Última actualización**: 2026-01-26

---

## Resumen

Desde v0.3.0, Narrative Assistant utiliza **Python embebido** en lugar de PyInstaller para el backend. Esta solución resuelve incompatibilidades críticas con numpy y asegura que la aplicación funcione en máquinas **sin Python instalado**.

---

## ¿Por Qué Python Embebido?

### Problema con PyInstaller

```
PyInstaller (frozen) + narrative_assistant + numpy (pip --user)
= ImportError: you should not try to import numpy from its source directory
```

**Causas**:
- PyInstaller congela los imports en tiempo de build
- numpy instalado después (pip --user) causa conflicto de paths
- Ninguna workaround (chdir, _MEI cleanup) funciona de forma confiable

### Solución: Python Embebido

| Approach | Tamaño | Funciona sin Python | Conflictos |
|----------|--------|---------------------|------------|
| PyInstaller sidecar | ~66MB | ❌ No | ✅ Con numpy lazy |
| **Python embebido** | **~40-70MB** | **✅ Sí** | **❌ Ninguno** |

---

## Arquitectura

```
narrative-assistant.exe (Tauri)
├── Frontend: Vue 3 + TypeScript
└── Backend: Python embebido
    ├── src-tauri/binaries/python-embed/    (~20MB)
    │   ├── python.exe (3.12.7)
    │   ├── python312.dll
    │   ├── DLLs/
    │   ├── Lib/ (standard library)
    │   └── python312._pth (import site enabled)
    │
    ├── src-tauri/binaries/backend/          (~3.5MB)
    │   ├── api-server/main.py
    │   ├── src/narrative_assistant/
    │   └── requirements.txt
    │
    └── start-backend.bat
        └── python-embed\python.exe backend\api-server\main.py
```

---

## Componentes

### 1. Python Embebido (3.12.7)

**Fuente**: [python.org/ftp/python/3.12.7/python-3.12.7-embed-amd64.zip](https://www.python.org/ftp/python/3.12.7/python-3.12.7-embed-amd64.zip)

**Ubicación**: `src-tauri/binaries/python-embed/`

**Características**:
- Versión mínima de Python sin instalación
- ~20MB comprimido
- Incluye standard library
- Sin registry entries, completamente portable
- `python312._pth` modificado para activar `import site` (habilita pip)

**Instalación de pip**:
```bash
.\python.exe -m ensurepip
.\python.exe -m pip install --upgrade pip setuptools wheel
```

### 2. Backend Bundle

**Script**: `scripts/build_backend_bundle.py`

**Contenido**:
- `api-server/` completo (main.py + dependencias)
- `src/narrative_assistant/` completo
- `requirements.txt` (FastAPI, uvicorn, pydantic, etc.)

**Generación**:
```bash
python scripts/build_backend_bundle.py
```

**Salida**: `src-tauri/binaries/backend/` (~3.5MB)

### 3. Launcher

**Script**: `src-tauri/binaries/start-backend.bat` (Windows)

**Código**:
```batch
@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EMBED=%SCRIPT_DIR%python-embed\python.exe"
set "BACKEND_DIR=%SCRIPT_DIR%backend"
set "MAIN_PY=%BACKEND_DIR%\api-server\main.py"

cd /d "%BACKEND_DIR%\api-server"
set "PYTHONPATH=%BACKEND_DIR%;%BACKEND_DIR%\api-server;%PYTHONPATH%"

"%PYTHON_EMBED%" "%MAIN_PY%"
endlocal
```

**Funcionalidad**:
- Cambia al directorio del backend
- Establece PYTHONPATH correctamente
- Ejecuta main.py con Python embebido
- No usa launcher intermedio (exec directo)

---

## Configuración de Tauri

**Archivo**: `src-tauri/tauri.conf.json`

```json
{
  "bundle": {
    "externalBin": [
      "binaries/start-backend.bat"
    ],
    "resources": [
      "binaries/python-embed/**",
      "binaries/backend/**"
    ]
  }
}
```

**Comportamiento**:
- `externalBin`: Tauri ejecuta start-backend.bat al iniciar app
- `resources`: Incluye Python embebido + backend en instalador
- Backend se ejecuta como proceso separado
- Comunicación: HTTP localhost:8008

---

## Proceso de Build

### Desarrollo Local

```bash
# 1. Download Python embebido (una vez)
python scripts/download_python_embed.py

# 2. Build backend bundle
python scripts/build_backend_bundle.py

# 3. Ejecutar app Tauri
npm run tauri dev
```

### Build de Producción

**Script automático**:
```bash
python scripts/build_app_with_python_embed.py
```

**Pasos manuales**:
```bash
# 1. Python embebido (si no existe)
python scripts/download_python_embed.py

# 2. Backend bundle
python scripts/build_backend_bundle.py

# 3. Frontend
cd frontend
npm install
npm run build

# 4. Tauri instalador
cd ..
npm run tauri build
```

**Salida**:
- Windows: `src-tauri/target/release/bundle/nsis/Narrative Assistant_0.3.0_x64-setup.exe`
- macOS: `src-tauri/target/release/bundle/dmg/Narrative Assistant_0.3.0_x64.dmg`
- Linux: `src-tauri/target/release/bundle/deb/narrative-assistant_0.3.0_amd64.deb`

---

## Instalación de Dependencias NLP

### Lazy Loading (Usuario Final)

**Primera ejecución**:
1. App detecta dependencias faltantes: numpy, spacy, sentence-transformers
2. Usuario hace clic en "Instalar Dependencias"
3. App ejecuta:
   ```python
   python_embed\python.exe -m pip install --user numpy spacy sentence-transformers torch
   ```
4. Dependencias se instalan en: `%APPDATA%\Roaming\Python\Python312\site-packages`
5. App carga módulos automáticamente

**Tamaño adicional**:
- numpy: ~20MB
- spacy: ~50MB
- sentence-transformers + torch: ~800MB (incluye modelo)

**Total instalación completa**: ~40MB (app) + ~900MB (NLP) = ~940MB

### Build Previo (GitHub Actions)

**Instalador con dependencias pre-instaladas**:
```bash
# En el build, instalar en Python embebido
cd src-tauri/binaries
.\python-embed\python.exe -m pip install numpy spacy sentence-transformers torch

# Resultado: dependencias en python-embed\Lib\site-packages
```

**Ventajas**:
- Usuario no necesita instalar nada
- Primera ejecución inmediata

**Desventajas**:
- Instalador más grande (~1GB)
- No recomendado para GitHub free tier

---

## Detección de Python Embebido

**Código** (`api-server/main.py`, línea 102):
```python
# Detectar Python embebido
using_embedded_python = 'python-embed' in sys.executable.lower()

if using_embedded_python:
    _write_debug("Detected embedded Python - skipping Anaconda detection")
    # No buscar Anaconda cuando usamos Python embebido
else:
    # Búsqueda normal de Anaconda en paths conocidos
    ...
```

**Comportamiento**:
- Python embebido: skip Anaconda detection, usar solo pip --user
- Python sistema: detectar Anaconda si está disponible

---

## Compatibilidad Multi-Plataforma

### Windows ✅

- **Python**: [python-3.12.7-embed-amd64.zip](https://www.python.org/ftp/python/3.12.7/python-3.12.7-embed-amd64.zip)
- **Launcher**: `start-backend.bat`
- **Tamaño**: ~20MB

### macOS 🚧

- **Python**: [Python-3.12.7-macos.pkg](https://www.python.org/ftp/python/3.12.7/python-3.12.7-macos11.pkg) o Python Framework
- **Launcher**: `start-backend.sh`
- **Instalación**: extraer framework de .pkg, incluir en bundle

### Linux 🚧

- **Approach 1**: Python portable (pyenv portable, AppImage Python)
- **Approach 2**: Depender de Python sistema (añadir a dependencies en .deb/.rpm)
- **Launcher**: `start-backend.sh`

---

## GitHub Actions (Planificado)

**Workflow**: `.github/workflows/build.yml`

```yaml
name: Build Multi-Platform

on:
  push:
    tags: [ 'v*' ]

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node
        uses: actions/setup-node@v4
      - name: Setup Python
        uses: actions/setup-python@v5
      - name: Download Python Embed
        run: python scripts/download_python_embed.py
      - name: Build Backend Bundle
        run: python scripts/build_backend_bundle.py
      - name: Build Frontend
        run: cd frontend && npm install && npm run build
      - name: Build Tauri
        run: npm run tauri build
      - name: Upload Artifacts
        uses: actions/upload-artifact@v4
        with:
          name: windows-installer
          path: src-tauri/target/release/bundle/nsis/*.exe

  build-macos:
    # Similar para macOS

  build-linux:
    # Similar para Linux
```

---

## Troubleshooting

### Backend no arranca

**Síntoma**: App inicia pero backend no responde en localhost:8008

**Debug**:
1. Verificar logs:
   ```
   %LOCALAPPDATA%\Narrative Assistant\backend-debug.log
   %LOCALAPPDATA%\Narrative Assistant\early-debug.txt
   ```

2. Ejecutar backend manualmente:
   ```bash
   cd src-tauri\binaries
   .\python-embed\python.exe .\backend\api-server\main.py
   ```

3. Verificar Python embebido:
   ```bash
   .\python-embed\python.exe --version
   # Debe mostrar: Python 3.12.7
   ```

### Dependencias no se encuentran

**Síntoma**: `ModuleNotFoundError: No module named 'numpy'`

**Solución**:
1. Instalar dependencias manualmente:
   ```bash
   .\python-embed\python.exe -m pip install --user numpy spacy sentence-transformers torch
   ```

2. Verificar site-packages del usuario:
   ```bash
   dir %APPDATA%\Roaming\Python\Python312\site-packages
   ```

3. Reiniciar aplicación

### uvicorn no se inicia

**Síntoma**: Backend arranca pero no bind a puerto 8008

**Causas comunes**:
- Puerto 8008 en uso por otro proceso
- `reload=True` en uvicorn.run() (incompatible con embedded)
- Falta uvicorn en requirements.txt

**Solución**:
```python
# main.py - usar reload=False
uvicorn.run(
    app,  # Instancia directa, no "main:app" string
    host="127.0.0.1",
    port=8008,
    reload=False,  # CRÍTICO para Python embebido
    log_level="info"
)
```

---

## Comparación con PyInstaller

| Aspecto | PyInstaller | Python Embebido |
|---------|-------------|-----------------|
| Tamaño base | ~66MB | ~23MB |
| Tamaño con deps | ~66MB | ~900MB |
| Funciona sin Python | ❌ No | ✅ Sí |
| Conflictos numpy | ✅ Sí | ❌ No |
| Compilación | Lenta (5min) | Rápida (30s) |
| Debugging | Difícil | Fácil (código Python visible) |
| Actualizaciones | Rebuild completo | Solo backend bundle |
| Multi-plataforma | Complejo | Relativamente simple |

---

## Roadmap

### v0.3.0 (Actual)
- ✅ Windows con Python embebido funcional
- ✅ Lazy loading de dependencias NLP
- ✅ Script de build automatizado

### v0.3.1 (Próximo)
- 🚧 macOS con Python Framework
- 🚧 Linux con Python portable
- 🚧 GitHub Actions para builds multi-plataforma

### v0.4.0 (Futuro)
- 📅 Instalador con dependencias pre-instaladas (opcional)
- 📅 Auto-updater para backend bundle
- 📅 Firma de código (Windows + macOS)

---

## Referencias

- [Python Embeddable Package (Windows)](https://docs.python.org/3/using/windows.html#embedded-distribution)
- [Tauri External Binaries](https://tauri.app/v1/guides/building/external-binaries/)
- [pip documentation](https://pip.pypa.io/en/stable/)

---

*Documento creado: 2026-01-26*
*Última actualización: 2026-01-26*
