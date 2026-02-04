# Estado Soporte Multi-Plataforma

> **Versión**: v0.3.0  
> **Fecha**: 2026-01-26  
> **Estado**: ✅ Windows funcional | 🧪 macOS implementado (pendiente test) | 🚧 Linux planificado

---

## Resumen

La solución de **Python embebido** ahora soporta **Windows y macOS**, permitiendo que la aplicación funcione en máquinas **sin Python instalado**.

---

## ✅ Windows (Verificado)

### Componentes
- **Python embebido**: `python-3.12.7-embed-amd64.zip` (~20MB)
- **Launcher**: [start-backend.bat](src-tauri/binaries/start-backend.bat)
- **Backend**: Scripts Python (~3.5MB)

### Estado
- ✅ Python embebido descarga correctamente
- ✅ Configuración `_pth` para pip funciona
- ✅ Backend inicia y responde en `localhost:8008`
- ✅ API `/api/models/status` responde correctamente
- ✅ Sin conflictos numpy/PyInstaller

### Verificado en sesión
```
[2026-01-26] Backend started successfully
INFO:     Uvicorn running on http://127.0.0.1:8008
HTTP/1.1 200 OK - /api/models/status
```

---

## 🧪 macOS (Implementado - Pendiente Test)

### Componentes
- **Python Framework**: `python-3.12.7-macos11.pkg` → `Python.framework` (~30-40MB)
- **Launcher**: [start-backend.sh](src-tauri/binaries/start-backend.sh)
- **Backend**: Mismo bundle de scripts

### Implementación
- ✅ [download_python_embed.py](scripts/download_python_embed.py) soporta macOS
  - Descarga `.pkg` oficial de python.org
  - Extrae `Python.framework` usando `pkgutil --expand` + `cpio`
  - Crea symlink `python3` → `Python.framework/Versions/Current/bin/python3`
- ✅ [start-backend.sh](src-tauri/binaries/start-backend.sh) con detección OS
  - Detecta `darwin` vs `linux-gnu`
  - Busca Python en framework o link
  - Configura `PYTHONPATH` y ejecuta `main.py`
- ✅ [tauri.conf.json](src-tauri/tauri.conf.json) multi-plataforma
  - `externalBin: "binaries/start-backend"` (Tauri añade `.bat` o `.sh`)
  - `resources: ["binaries/start-backend.sh"]` (permisos exec)
- ✅ [build_app_with_python_embed.py](scripts/build_app_with_python_embed.py) detecta plataforma
  - `get_python_embed_executable()` devuelve path correcto por OS
  - Instrucciones específicas por plataforma en output

### Pendiente
- 🧪 Probar en hardware macOS real
- 🧪 Verificar extracción `.pkg` → `Python.framework`
- 🧪 Validar permisos de ejecución `start-backend.sh`
- 🧪 Confirmar Tauri `externalBin` en macOS

---

## 🚧 Linux (Planificado)

### Opciones consideradas
1. **Python portable** (ej. AppImage embebido)
2. **Dependencia de paquete** (`python3` en `.deb`)

### Estado
- 🚧 `download_python_embed.py` tiene stub para Linux
- 🚧 `start-backend.sh` soporta `linux-gnu` con fallback a system Python
- 🚧 Decisión pendiente sobre estrategia (portable vs dependency)

---

## Tamaños de Instalador

| Plataforma | Tamaño Estimado | Componentes |
|------------|-----------------|-------------|
| **Windows** | ~40-50 MB | Python embed 20MB + Backend 3.5MB + Tauri runtime |
| **macOS** | ~60-70 MB | Python.framework 30-40MB + Backend 3.5MB + Tauri runtime |
| **Linux** | TBD | Depende de estrategia elegida |

**Nota**: Primera ejecución descarga modelos NLP (~900MB). Después funciona 100% offline.

---

## Documentación

| Archivo | Descripción |
|---------|-------------|
| [PYTHON_EMBED.md](docs/PYTHON_EMBED.md) | Documentación técnica completa (arquitectura, proceso, configuración) |
| [README.md](README.md) | Actualizado con info multi-plataforma |
| [BUILD_AND_DEPLOY.md](docs/BUILD_AND_DEPLOY.md) | Construcción de instaladores |

---

## Próximos Pasos

### v0.3.1 (Testing + CI/CD)
- [x] Probar implementación macOS en hardware real (validado v0.4.35)
- [x] GitHub Actions workflow para builds multi-plataforma
- [ ] Validar instaladores en sistemas limpios (sin Python)

### v0.4.0 (Producción)
- [ ] Code signing (Windows EV cert, Apple Developer)
- [ ] Definir estrategia Linux
- [ ] Auto-update mechanism
- [ ] Telemetría opcional post-instalación

---

## Comandos Útiles

### Build local Windows
```powershell
python scripts/build_app_with_python_embed.py
```

### Build local macOS
```bash
python3 scripts/build_app_with_python_embed.py
```

### Verificar Python embebido (Windows)
```powershell
.\src-tauri\binaries\python-embed\python.exe --version
.\src-tauri\binaries\start-backend.bat
```

### Verificar Python embebido (macOS)
```bash
./src-tauri/binaries/python-embed/python3 --version
./src-tauri/binaries/start-backend.sh
```

---

## Referencias Técnicas

### Python Embebido Windows
- Fuente: https://www.python.org/ftp/python/3.12.7/python-3.12.7-embed-amd64.zip
- Docs: https://docs.python.org/3/using/windows.html#embedded-distribution

### Python macOS Framework
- Fuente: https://www.python.org/ftp/python/3.12.7/python-3.12.7-macos11.pkg
- Docs: https://docs.python.org/3/using/mac.html

### Tauri External Binaries
- Docs: https://v2.tauri.app/reference/config/#externalbinconfig

---

*Última actualización: 2026-01-26 por implementación multi-plataforma v0.3.0*
