# Narrative Assistant - Setup Completo

Guía rápida para configurar y ejecutar Narrative Assistant (Backend + Frontend Desktop).

## Requisitos del Sistema

### Software Necesario

- **Python** 3.11 o superior (recomendado 3.12)
- **Node.js** 18 o superior
- **Rust** 1.70+ con cargo
- **Git** (opcional, para desarrollo)

### Instalación de Rust

```bash
# Windows
winget install Rustlang.Rustup

# macOS/Linux
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

Verificar instalación:
```bash
cargo --version
rustc --version
```

### Instalación de Node.js

- Windows: https://nodejs.org/ o `winget install OpenJS.NodeJS`
- macOS: `brew install node`
- Linux: `sudo apt install nodejs npm`

Verificar:
```bash
node --version
npm --version
```

---

## Setup Rápido (3 Pasos)

### 1. Preparar Backend Python

```bash
# Crear entorno virtual
python -m venv .venv

# Activar entorno
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS

# Instalar paquete
pip install -e ".[dev]"

# Descargar modelos NLP (~1.5 GB)
python scripts/download_models.py
```

### 2. Build Backend para Tauri

```bash
cd api-server
python build.py
cd ..
```

Esto genera `api-server/dist/narrative-assistant-server/` (~2-3 GB con modelos).

### 3. Setup Completo Automatizado

```bash
python scripts/setup_tauri.py
```

Este script:
- ✓ Verifica requisitos (Rust, Node, Python)
- ✓ Build del backend Python con PyInstaller
- ✓ Copia el backend a `src-tauri/binaries/`
- ✓ Instala dependencias del frontend (npm install)

---

## Modo Desarrollo

### Opción A: Tauri Dev (Recomendado)

```bash
cd src-tauri
cargo tauri dev
```

Esto inicia:
- Frontend Vue 3 en http://localhost:5173 (hot-reload)
- Backend Python como sidecar (puerto 8008)
- Ventana de Tauri con DevTools

### Opción B: Frontend Solo (sin Tauri)

```bash
# Terminal 1: Backend
cd api-server
python start_server.py

# Terminal 2: Frontend
cd frontend
npm run dev
```

Navegar a http://localhost:5173

---

## Build de Producción

### Build Completo (App + Instaladores)

```bash
cd src-tauri
cargo tauri build
```

Genera en `src-tauri/target/release/bundle/`:

- **Windows**: `.msi` (instalador oficial), `.exe` (NSIS)
- **macOS**: `.app` (aplicación), `.dmg` (imagen de disco)
- **Linux**: `.deb` (Debian/Ubuntu), `.AppImage` (portable)

### Build Solo App (sin instalador)

```bash
cd src-tauri
cargo build --release
```

Ejecutable en `src-tauri/target/release/narrative-assistant.exe`

---

## Verificación del Setup

### Check 1: Backend Funciona

```bash
cd api-server/dist/narrative-assistant-server
./narrative-assistant-server.exe  # Windows
./narrative-assistant-server       # Linux/macOS
```

Debe iniciar en http://127.0.0.1:8008

Probar:
```bash
curl http://127.0.0.1:8008/api/health
```

### Check 2: Frontend Funciona

```bash
cd frontend
npm run dev
```

Navegar a http://localhost:5173 - debe ver la página de inicio.

### Check 3: Tauri Funciona

```bash
cd src-tauri
cargo tauri dev
```

Debe abrir una ventana con la app.

---

## Estructura del Proyecto

```
tfm/
├── src/                           # Backend Python
│   └── narrative_assistant/       # Paquete principal
├── models/                        # Modelos NLP offline (~1.5 GB)
│   ├── spacy/
│   └── embeddings/
├── api-server/                    # FastAPI HTTP bridge
│   ├── main.py                    # Servidor FastAPI
│   ├── build.py                   # Script de build con PyInstaller
│   └── dist/                      # Backend empaquetado
├── frontend/                      # Vue 3 + TypeScript
│   ├── src/
│   │   ├── stores/                # Pinia stores
│   │   ├── views/                 # Páginas Vue
│   │   └── types/                 # TypeScript types
│   └── package.json
├── src-tauri/                     # Aplicación Tauri
│   ├── src/main.rs                # Rust app + sidecar lifecycle
│   ├── tauri.conf.json            # Configuración Tauri
│   ├── Cargo.toml                 # Dependencias Rust
│   └── binaries/                  # Backend para distribución
└── scripts/
    ├── setup_tauri.py             # Setup automatizado
    └── download_models.py         # Descarga de modelos NLP
```

---

## Troubleshooting

### Problema: "Cargo not found"

**Solución**: Reiniciar terminal después de instalar Rust. Verificar con `cargo --version`.

En WSL/bash, agregar al PATH:
```bash
export PATH="$HOME/.cargo/bin:$PATH"
```

### Problema: "Backend not starting in Tauri"

**Verificar**:
1. Backend funciona standalone: `cd api-server/dist/narrative-assistant-server && ./narrative-assistant-server.exe`
2. Backend está en `src-tauri/binaries/` con nombre correcto
3. Logs de Tauri en consola

**Nombre correcto del binario** (debe incluir target triple):
- Windows: `narrative-assistant-server-x86_64-pc-windows-msvc/`
- macOS Intel: `narrative-assistant-server-x86_64-apple-darwin/`
- macOS ARM: `narrative-assistant-server-aarch64-apple-darwin/`
- Linux: `narrative-assistant-server-x86_64-unknown-linux-gnu/`

Copiar manualmente si es necesario:
```bash
cp -r api-server/dist/narrative-assistant-server src-tauri/binaries/narrative-assistant-server-x86_64-pc-windows-msvc
```

### Problema: "Port 8008 already in use"

**Solución**: Matar proceso que usa el puerto:

```bash
# Windows
netstat -ano | findstr :8008
taskkill /PID <PID> /F

# Linux/macOS
lsof -i :8008
kill <PID>
```

### Problema: "Models not found"

**Solución**: Descargar modelos NLP:
```bash
python scripts/download_models.py
```

Verificar que existan:
```bash
ls models/spacy/es_core_news_lg
ls models/embeddings/paraphrase-multilingual-MiniLM-L12-v2
```

### Problema: "npm install fails"

**Solución**: Limpiar cache y reinstalar:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

### Problema: "PyInstaller build fails"

**Solución**: Instalar PyInstaller y dependencias:
```bash
pip install pyinstaller
pip install -e ".[dev]"
```

Verificar que `models/` exista antes de build.

---

## Comandos Útiles

### Backend

```bash
# Análisis de un documento
narrative-assistant analyze documento.docx

# Verificar entorno
narrative-assistant verify

# Info del sistema
narrative-assistant info
```

### Frontend

```bash
cd frontend
npm run dev      # Desarrollo
npm run build    # Build de producción
npm run preview  # Preview del build
```

### Tauri

```bash
cd src-tauri
cargo tauri dev     # Desarrollo
cargo tauri build   # Build de producción
cargo tauri info    # Info del sistema
```

---

## Próximos Pasos

Una vez completado el setup:

1. **Ejecutar en modo dev**: `cd src-tauri && cargo tauri dev`
2. **Crear un proyecto** desde la UI
3. **Analizar un documento** (DOCX, TXT, MD)
4. **Ver alertas** de inconsistencias detectadas
5. **Explorar entidades** extraídas del manuscrito
6. **Exportar fichas** de personajes y guía de estilo

---

## Documentación Adicional

- [CLAUDE.md](CLAUDE.md) - Instrucciones para desarrollo con Claude Code
- [PROJECT_STATUS.md](docs/PROJECT_STATUS.md) - Estado del proyecto y arquitectura
- [ROADMAP.md](docs/ROADMAP.md) - Trabajo pendiente y objetivos futuros
- [Frontend README](frontend/README.md) - Documentación del frontend Vue 3
- [API Server README](api-server/README.md) - Documentación del servidor FastAPI
- [Tauri README](src-tauri/README.md) - Documentación de la app Tauri

---

## Soporte

Para reportar problemas o solicitar ayuda:

1. Revisar esta guía y la sección de Troubleshooting
2. Verificar logs en consola (modo dev)
3. Consultar documentación específica de cada componente
4. Abrir un issue en el repositorio (si aplica)

---

**¡Listo para empezar!** 🚀

Ejecuta `python scripts/setup_tauri.py` para comenzar.
