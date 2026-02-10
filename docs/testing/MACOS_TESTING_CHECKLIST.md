# Checklist de Testing macOS

> **Propósito**: Validar la implementación de Python embebido en macOS  
> **Prerequisitos**: Mac con macOS 11+ (Big Sur o superior)  
> **Estado**: 🧪 Pendiente ejecución

---

## Pre-Test Setup

### 1. Preparar entorno limpio
- [ ] Máquina macOS **sin** Python instalado (o desactivar temporalmente)
- [ ] Verificar ausencia de Python: `which python3` → debe fallar o mostrar system Python
- [ ] Clonar repositorio: `git clone <url> tfm && cd tfm`

### 2. Descargar Python embebido
```bash
python3 scripts/download_python_embed.py
```

**Verificaciones**:
- [ ] Script detecta plataforma como `Darwin`
- [ ] Descarga `python-3.12.7-macos11.pkg` (~30-40MB)
- [ ] Extrae `Python.framework` correctamente
- [ ] Estructura creada en `src-tauri/binaries/python-embed/`:
  - [ ] `Python.framework/` existe
  - [ ] `Python.framework/Versions/Current/` es symlink válido
  - [ ] `Python.framework/Versions/3.12/bin/python3` existe y es ejecutable
  - [ ] `python3` symlink creado en raíz

**Comandos de verificación**:
```bash
ls -la src-tauri/binaries/python-embed/
file src-tauri/binaries/python-embed/python3
./src-tauri/binaries/python-embed/python3 --version
# Debe mostrar: Python 3.12.7
```

---

## Test 1: Python Embebido Standalone

### Verificar ejecutable Python
```bash
cd src-tauri/binaries/python-embed/
./python3 --version
./python3 -c "import sys; print(sys.executable)"
./python3 -c "import sys; print(sys.path)"
```

**Esperado**:
- [ ] Versión: `Python 3.12.7`
- [ ] Executable path apunta a `Python.framework/...`
- [ ] sys.path incluye framework `lib/python3.12`

### Instalar pip
```bash
./python3 -m ensurepip
./python3 -m pip install --upgrade pip setuptools wheel
```

**Verificaciones**:
- [ ] pip se instala sin errores
- [ ] `./python3 -m pip list` muestra pip, setuptools, wheel

### Probar instalación de paquetes
```bash
./python3 -m pip install requests
./python3 -c "import requests; print(requests.__version__)"
```

**Esperado**:
- [ ] Instalación exitosa
- [ ] Import funciona

---

## Test 2: Backend Bundle

### Construir backend bundle
```bash
cd /ruta/a/tfm
python3 scripts/build_backend_bundle.py
```

**Verificaciones**:
- [ ] Script se ejecuta sin errores
- [ ] Directorio `src-tauri/binaries/backend/` creado con:
  - [ ] `api-server/main.py`
  - [ ] `src/narrative_assistant/`
  - [ ] `requirements.txt`

### Instalar dependencias backend
```bash
cd src-tauri/binaries/python-embed/
./python3 -m pip install -r ../backend/requirements.txt
```

**Verificaciones**:
- [ ] Todas las dependencias se instalan sin conflictos
- [ ] No hay errores de compilación (numpy, uvicorn, etc.)

---

## Test 3: Launcher Script

### Verificar permisos
```bash
chmod +x src-tauri/binaries/start-backend.sh
ls -l src-tauri/binaries/start-backend.sh
# Debe mostrar: -rwxr-xr-x
```

### Ejecutar launcher
```bash
cd src-tauri/binaries/
./start-backend.sh
```

**Verificaciones**:
- [ ] Script detecta `OSTYPE=darwin*`
- [ ] Encuentra Python en `python3` symlink o `Python.framework/.../python3`
- [ ] Backend inicia sin errores
- [ ] Mensaje: `INFO:     Uvicorn running on http://127.0.0.1:8008`
- [ ] Proceso no termina inmediatamente

### Probar API (en otra terminal)
```bash
curl http://localhost:8008/api/health
curl http://localhost:8008/api/models/status
```

**Esperado**:
- [ ] `/api/health` devuelve JSON con `{"status": "ok"}`
- [ ] `/api/models/status` devuelve JSON con info de modelos
- [ ] Respuestas HTTP 200

### Detener backend
```bash
# Ctrl+C en terminal del launcher
```

**Verificaciones**:
- [ ] Proceso termina limpiamente
- [ ] No quedan procesos zombie (`ps aux | grep python`)

---

## Test 4: Build Completo con Tauri

### Ejecutar build script
```bash
python3 scripts/build_app_with_python_embed.py
```

**Verificaciones**:
- [ ] Script detecta plataforma `Darwin`
- [ ] Paso 1: Download Python - detecta existente o descarga
- [ ] Paso 2: Install pip - verifica instalación
- [ ] Paso 3: Build backend bundle - copia archivos
- [ ] Paso 4: Build frontend - `cd frontend && npm install && npm run build`
- [ ] Paso 5: Build Tauri - `cd src-tauri && cargo tauri build`
- [ ] Mensaje final con path al `.dmg`

### Verificar instalador
```bash
ls -lh src-tauri/target/release/bundle/dmg/
# Debe existir: Narrative-Assistant_x.x.x_aarch64.dmg o _x86_64.dmg
```

**Verificaciones**:
- [ ] Archivo `.dmg` existe
- [ ] Tamaño aproximado: 60-70 MB
- [ ] No hay errores en logs de Tauri build

---

## Test 5: Instalación y Ejecución

### Instalar desde DMG
```bash
# Montar DMG (doble click o hdiutil)
# Arrastrar "Narrative Assistant.app" a Aplicaciones
open /Applications/Narrative\ Assistant.app
```

**Verificaciones**:
- [ ] App se instala en `/Applications/`
- [ ] App arranca sin warnings de Gatekeeper (si sin firmar, necesita "Abrir de todas formas")
- [ ] Frontend carga correctamente
- [ ] Backend inicia automáticamente

### Verificar logs backend
```bash
# Logs de Console.app filtrar por "Narrative Assistant"
# O verificar Activity Monitor → buscar proceso python
```

**Verificaciones**:
- [ ] Backend process existe (nombre: `python3` o `Python`)
- [ ] Command line muestra path correcto a `main.py` en bundle de app
- [ ] No hay errores en Console.app

### Probar funcionalidad básica
- [ ] Abrir la app
- [ ] Frontend muestra interfaz correctamente
- [ ] Verificar `/api/health` desde frontend (DevTools → Network)
- [ ] Intentar cargar un documento de prueba
- [ ] Backend responde correctamente

### Cerrar y verificar cleanup
```bash
# Cerrar app normalmente
# Verificar que proceso backend termina
ps aux | grep python
# No debe mostrar procesos relacionados
```

---

## Test 6: Sistema Limpio (Sin Python del Sistema)

### Setup
- [ ] Desinstalar Python del sistema (o renombrar `/usr/bin/python3`)
- [ ] Verificar: `which python3` → no encontrado

### Re-test
- [ ] App instalada sigue funcionando
- [ ] Backend inicia correctamente
- [ ] No hay errores sobre Python no encontrado

**Resultado esperado**: App funciona **independientemente** del Python del sistema.

---

## Troubleshooting

### Problema: "Python embebido no encontrado"
**Diagnóstico**:
```bash
ls -la src-tauri/binaries/python-embed/
file src-tauri/binaries/python-embed/python3
```

**Soluciones**:
- Verificar que symlink `python3` apunta correctamente a framework
- Re-ejecutar `download_python_embed.py`

### Problema: "Permission denied" al ejecutar start-backend.sh
**Solución**:
```bash
chmod +x src-tauri/binaries/start-backend.sh
```

### Problema: Backend no inicia (port already in use)
**Diagnóstico**:
```bash
lsof -i :8008
```

**Solución**:
```bash
kill <PID>
```

### Problema: "numpy ImportError" en macOS
**Diagnóstico**:
```bash
./src-tauri/binaries/python-embed/python3 -c "import numpy; print(numpy.__version__)"
```

**Solución**:
- Re-instalar numpy: `pip install --force-reinstall numpy`
- Verificar architecture (x86_64 vs arm64)

### Problema: Gatekeeper bloquea app sin firmar
**Solución (temporal para desarrollo)**:
```bash
xattr -cr /Applications/Narrative\ Assistant.app
```

---

## Criterios de Éxito

✅ **Test Exitoso** si:
1. Python embebido se descarga y extrae correctamente
2. Backend inicia con launcher script
3. API responde en localhost:8008
4. Build Tauri genera `.dmg` válido
5. App instalada funciona sin Python del sistema
6. No hay conflictos numpy/PyInstaller
7. Cleanup correcto al cerrar app

---

## Reportar Resultados

Al completar testing, actualizar:
1. [MULTI_PLATFORM_STATUS.md](MULTI_PLATFORM_STATUS.md) - cambiar macOS de 🧪 a ✅ o documentar issues
2. [PYTHON_EMBED.md](docs/PYTHON_EMBED.md) - sección "Estado por Plataforma"
3. [CHANGELOG.md](docs/CHANGELOG.md) - registrar validación macOS

**Template de reporte**:
```
## macOS Testing - [Fecha]

**Hardware**: MacBook [modelo], [chip M1/Intel]
**OS**: macOS [versión]

### Resultados:
- [ ] Python embebido: ✅/❌ [detalles]
- [ ] Backend bundle: ✅/❌ [detalles]
- [ ] Launcher script: ✅/❌ [detalles]
- [ ] Tauri build: ✅/❌ [detalles]
- [ ] Instalación: ✅/❌ [detalles]
- [ ] Sistema limpio: ✅/❌ [detalles]

### Issues encontrados:
1. [Descripción]
   - Error: [mensaje]
   - Solución: [pasos]

### Conclusión:
[PASSED/FAILED] - [resumen]
```

---

*Checklist v0.3.0 - 2026-01-26*
