# Build and Deployment Guide - Narrative Assistant

> **Última actualización**: 2026-01-10
> **Versión**: 0.3.0

---

## Índice

1. [Requisitos del Sistema](#requisitos-del-sistema)
2. [Setup Inicial](#setup-inicial)
3. [Desarrollo Local](#desarrollo-local)
4. [Testing](#testing)
5. [Build de Producción](#build-de-producción)
6. [Deployment](#deployment)
7. [Troubleshooting](#troubleshooting)

---

## Requisitos del Sistema

### Software Requerido

- **Node.js** 18.x o superior ([Download](https://nodejs.org/))
- **Python** 3.11+ ([Download](https://www.python.org/))
- **Rust** 1.70+ para Tauri ([Download](https://www.rust-lang.org/))
- **Git** para control de versiones

### Espacio en Disco

- **Desarrollo**: ~3 GB
  - node_modules: ~500 MB
  - Python venv: ~800 MB
  - Modelos NLP: ~1 GB
  - Código fuente: ~50 MB
  - Build artifacts: ~300 MB

- **Producción**: ~2.5 GB
  - Aplicación empaquetada: ~2-2.5 GB (incluye modelos NLP)

---

## Setup Inicial

### 1. Clonar Repositorio

```bash
git clone <repository-url>
cd tfm
```

### 2. Setup Backend Python

```bash
# Crear entorno virtual
python3.11 -m venv .venv

# Activar entorno
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Instalar dependencias
pip install -e ".[dev]"

# Descargar modelos NLP (si no existen)
python scripts/download_models.py

# Verificar instalación
narrative-assistant verify
```

### 3. Setup Frontend

```bash
cd frontend

# Instalar dependencias
npm install

# Verificar instalación
npm run type-check
```

### 4. Setup Tauri

```bash
cd src-tauri

# Instalar dependencias Rust
cargo fetch

# Verificar instalación
cargo check
```

---

## Desarrollo Local

### Modo 1: Frontend Solo (sin Backend)

Útil para desarrollo rápido de UI sin necesidad del backend Python.

```bash
cd frontend
npm run dev

# Servidor en: http://localhost:5173
# Hot-reload habilitado
# Datos stub para testing
```

### Modo 2: Frontend + Backend (Completo)

Desarrollo completo con backend Python funcionando.

**Terminal 1 - Backend:**
```bash
# Activar venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS

# Iniciar servidor FastAPI
cd api-server
python main.py

# Servidor en: http://localhost:8008
# Hot-reload habilitado con --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev

# Servidor en: http://localhost:5173
# Se comunica con backend en :8008
```

### Modo 3: Aplicación Tauri Completa

Desarrollo con la aplicación de escritorio completa.

```bash
cd frontend
npm run tauri dev

# Inicia automáticamente:
# 1. Backend Python (sidecar)
# 2. Frontend Vite
# 3. Ventana Tauri
```

**Logs disponibles en:**
- Frontend: Consola del navegador (DevTools)
- Backend: Terminal donde se ejecuta
- Tauri: Terminal de `npm run tauri dev`

---

## Testing

### Tests Unitarios Backend

```bash
# Activar venv
.venv\Scripts\activate

# Ejecutar todos los tests
pytest

# Con coverage
pytest --cov=src/narrative_assistant

# Tests específicos
pytest tests/unit/test_ner.py
pytest tests/unit/test_attributes.py

# Verbose mode
pytest -v
```

**Resultados esperados:**
- 49 tests passing
- 11 tests skipped (alerts - pendiente actualización)
- ~2.5 minutos de ejecución

### Tests E2E Frontend

```bash
cd frontend

# Instalar Playwright browsers (primera vez)
npx playwright install

# Ejecutar tests E2E
npm run test:e2e

# Con UI interactivo
npm run test:e2e:ui

# Solo un navegador
npx playwright test --project=chromium

# Debug mode
npx playwright test --debug
```

**Tests disponibles:**
- `e2e/home.spec.ts` - Vista de inicio
- Más tests según se implementen

### Tests de Integración

```bash
# Backend + Frontend juntos
cd frontend
npm run test:integration

# Verifica:
# - Comunicación API
# - Flujos completos
# - Datos reales
```

---

## Build de Producción

### 1. Build Backend (PyInstaller)

Empaqueta el backend Python como ejecutable standalone.

```bash
cd api-server

# Build
python build.py

# Output: dist/narrative-assistant-backend/
# Tamaño: ~2-2.5 GB (incluye modelos)
```

**Contenido del bundle:**
- Ejecutable Python embebido
- Todas las dependencias
- Modelos NLP (spaCy, sentence-transformers)
- SQLite database

### 2. Build Frontend (Vite)

```bash
cd frontend

# Build optimizado
npm run build

# Output: dist/
# Tamaño: ~5-10 MB (minificado)
```

**Optimizaciones aplicadas:**
- Minificación
- Tree-shaking
- Code splitting
- Compresión gzip

### 3. Build Tauri App (Desktop)

Empaqueta todo en una aplicación de escritorio.

```bash
cd frontend

# Build para plataforma actual
npm run tauri build

# Outputs en: src-tauri/target/release/bundle/
```

**Plataformas soportadas:**

- **Windows**: `.msi` instalador
- **macOS**: `.dmg` disk image, `.app` bundle
- **Linux**: `.deb`, `.AppImage`

**Tamaños aproximados:**
- Windows .msi: ~2.5 GB
- macOS .dmg: ~2.5 GB
- Linux .deb: ~2.5 GB

---

## Deployment

### Local Installation

```bash
# Windows
cd src-tauri/target/release/bundle/msi
narrative-assistant_0.3.0_x64.msi

# macOS
open src-tauri/target/release/bundle/dmg/Narrative\ Assistant_0.3.0_x64.dmg

# Linux
sudo dpkg -i src-tauri/target/release/bundle/deb/narrative-assistant_0.3.0_amd64.deb
```

### Distribución

1. **Subir a releases de GitHub**
   ```bash
   gh release create v0.3.0 \
     src-tauri/target/release/bundle/msi/*.msi \
     src-tauri/target/release/bundle/dmg/*.dmg \
     src-tauri/target/release/bundle/deb/*.deb
   ```

2. **Auto-updates (opcional)**
   - Configurar en `tauri.conf.json`
   - Servidor de updates requerido

### Verificación Post-Deploy

```bash
# Verificar instalación
narrative-assistant verify

# Info del sistema
narrative-assistant info

# Test básico
narrative-assistant analyze tests/fixtures/sample.docx
```

---

## Troubleshooting

### Frontend

**Error: `Cannot find module 'vue'`**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Error: Puerto 5173 en uso**
```bash
# Cambiar puerto en vite.config.ts
server: {
  port: 3000
}
```

### Backend

**Error: Modelos NLP no encontrados**
```bash
python scripts/download_models.py
# O copiar modelos manualmente a models/
```

**Error: Puerto 8008 en uso**
```bash
# Cambiar puerto en api-server/main.py
uvicorn.run(app, host="0.0.0.0", port=8009)
```

### Tauri

**Error: `cargo not found`**
```bash
# Instalar Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

**Error: Build falla en Windows**
```bash
# Instalar Visual Studio Build Tools
# https://visualstudio.microsoft.com/downloads/
```

**Error: `WebView2 not found` (Windows)**
```bash
# Descargar WebView2 Runtime
# https://developer.microsoft.com/microsoft-edge/webview2/
```

### Tests

**Error: Tests fallan con timeout**
```bash
# Aumentar timeout en playwright.config.ts
timeout: 60 * 1000
```

**Error: Backend no responde en tests**
```bash
# Verificar que el backend está corriendo
curl http://localhost:8008/api/health
```

---

## Performance Optimization

### Frontend

1. **Lazy Loading**
   - Todas las rutas usan `() => import()`
   - Code splitting automático

2. **Virtual Scrolling**
   - Listas grandes usan PrimeVue VirtualScroller
   - Soporta 1000+ items sin lag

3. **Caching**
   - LocalStorage para configuración
   - Service worker (opcional)

### Backend

1. **Connection Pooling**
   - SQLite con WAL mode
   - Conexiones reutilizables

2. **Batch Processing**
   - NLP procesa en batches
   - GPU cuando disponible

3. **Caching**
   - Modelos NLP pre-cargados
   - Embeddings en memoria

---

## CI/CD (Futuro)

### GitHub Actions (Ejemplo)

```yaml
name: Build and Test

on: [push, pull_request]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: pytest

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: cd frontend && npm install
      - run: cd frontend && npm run test:e2e

  build:
    needs: [test-backend, test-frontend]
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - uses: actions-rs/toolchain@v1
      - run: cd frontend && npm install
      - run: cd frontend && npm run tauri build
      - uses: actions/upload-artifact@v3
        with:
          name: narrative-assistant-${{ matrix.os }}
          path: src-tauri/target/release/bundle/
```

---

## Contacto y Soporte

- **Repositorio**: [GitHub](https://github.com/...)
- **Issues**: [GitHub Issues](https://github.com/.../issues)
- **Documentación**: `docs/`

---

**Última actualización**: 2026-01-10 - Versión 0.3.0 con UI completa
