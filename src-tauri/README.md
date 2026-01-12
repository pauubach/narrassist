# Narrative Assistant - Tauri App

Aplicación de escritorio cross-platform con Tauri 2.0, Vue 3, y backend Python.

## Arquitectura

```
┌─────────────────────────────────────┐
│   Tauri Window (Rust)               │
│  ┌──────────────────────────────┐   │
│  │  Vue 3 Frontend              │   │
│  │  - PrimeVue UI               │   │
│  │  - Pinia State               │   │
│  │  - Vue Router                │   │
│  └──────────────────────────────┘   │
│            ↕ HTTP (localhost:8008)  │
│  ┌──────────────────────────────┐   │
│  │  Python Backend (Sidecar)    │   │
│  │  - FastAPI Server            │   │
│  │  - narrative_assistant       │   │
│  │  - NLP Models (offline)      │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

## Requisitos

### Desarrollo

- **Rust** 1.70+ (con cargo)
- **Node.js** 18+ (con npm)
- **Python** 3.11+
- **Sistema operativo**: Windows, macOS, o Linux

### Instalación de Rust

```bash
# Windows
winget install Rustlang.Rustup

# macOS/Linux
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

Verificar:
```bash
cargo --version
rustc --version
```

## Setup

### 1. Preparar Backend

```bash
# Instalar paquete Python
pip install -e ".[dev]"

# Descargar modelos NLP
python scripts/download_models.py

# Build del backend para sidecar
cd api-server
python build.py
```

Esto genera `api-server/dist/narrative-assistant-server/`.

### 2. Copiar Backend a Tauri

```bash
# Windows (PowerShell)
Copy-Item -Recurse api-server\dist\narrative-assistant-server src-tauri\binaries\narrative-assistant-server-x86_64-pc-windows-msvc

# Windows (bash/WSL)
cp -r api-server/dist/narrative-assistant-server src-tauri/binaries/narrative-assistant-server-x86_64-pc-windows-msvc

# macOS
cp -r api-server/dist/narrative-assistant-server src-tauri/binaries/narrative-assistant-server-x86_64-apple-darwin

# Linux
cp -r api-server/dist/narrative-assistant-server src-tauri/binaries/narrative-assistant-server-x86_64-unknown-linux-gnu
```

**Nota**: El nombre del binario debe incluir el target triple de Rust.

### 3. Instalar Dependencias de Frontend

```bash
cd frontend
npm install
```

### 4. Instalar Tauri CLI

```bash
npm install -g @tauri-apps/cli
# o
cargo install tauri-cli
```

## Desarrollo

### Modo Dev (con hot-reload)

```bash
cd src-tauri
cargo tauri dev
```

Esto:
1. Inicia el frontend Vite en `localhost:5173`
2. Compila y ejecuta la app Tauri
3. Inicia el backend Python como sidecar
4. Hot-reload del frontend al editar código Vue

### Solo Frontend (sin Tauri)

```bash
cd frontend
npm run dev
```

Luego iniciar el backend manualmente:
```bash
cd api-server
python start_server.py
```

Navegar a http://localhost:5173

## Build de Producción

### Build Completo

```bash
cd src-tauri
cargo tauri build
```

Esto genera instaladores en `src-tauri/target/release/bundle/`:

- **Windows**: `.msi`, `.exe` (NSIS)
- **macOS**: `.app`, `.dmg`
- **Linux**: `.deb`, `.AppImage`

### Build Solo App (sin instalador)

```bash
cd src-tauri
cargo build --release
```

Ejecutable en `src-tauri/target/release/narrative-assistant.exe`

## Estructura de Archivos

```
src-tauri/
├── Cargo.toml              # Configuración de Rust
├── tauri.conf.json         # Configuración de Tauri
├── build.rs                # Build script
├── src/
│   └── main.rs             # Código Rust (sidecar lifecycle)
├── binaries/               # Backend Python empaquetado
│   └── narrative-assistant-server-{target}/
│       ├── narrative-assistant-server.exe
│       ├── models/         # NLP models (~2 GB)
│       └── _internal/      # Dependencies
├── icons/                  # Iconos de la app
│   ├── 32x32.png
│   ├── 128x128.png
│   ├── icon.icns           # macOS
│   └── icon.ico            # Windows
└── target/                 # Artefactos de build (gitignored)
```

## Comandos Tauri

```bash
# Desarrollo
cargo tauri dev

# Build de producción
cargo tauri build

# Información del sistema
cargo tauri info

# Actualizar dependencias
cargo update
```

## Sidecar Lifecycle

El backend Python se gestiona automáticamente:

1. **Al iniciar la app**: Se lanza el servidor FastAPI en puerto 8008
2. **Durante ejecución**: Logs del backend se muestran en consola
3. **Al cerrar la app**: El backend se detiene automáticamente

### Comandos Tauri personalizados

Desde el frontend, puedes controlar el backend:

```typescript
import { invoke } from '@tauri-apps/api/core'

// Iniciar backend
await invoke('start_backend_server')

// Detener backend
await invoke('stop_backend_server')

// Verificar health
const isHealthy = await invoke('check_backend_health')
```

## Configuración

### Puerto del Backend

Por defecto: `8008`

Para cambiar:
1. Modificar `api-server/main.py` (puerto del servidor)
2. Modificar `src-tauri/src/main.rs` (cliente HTTP)
3. Modificar `frontend/vite.config.ts` (proxy de desarrollo)

### CSP (Content Security Policy)

Configurado en `tauri.conf.json`:

```json
"security": {
  "csp": "default-src 'self'; connect-src 'self' http://localhost:8008; ..."
}
```

Permite:
- Recursos locales (`'self'`)
- Conexiones HTTP al backend (`localhost:8008`)
- Scripts y estilos inline (necesario para Vue + PrimeVue)

## Troubleshooting

### Error: "sidecar not found"

Verificar que el backend esté en `src-tauri/binaries/` con el nombre correcto:
```bash
ls src-tauri/binaries/
```

Debe incluir el target triple de Rust (ej: `narrative-assistant-server-x86_64-pc-windows-msvc`).

### Error: "Backend not starting"

1. Verificar que el backend funciona standalone:
   ```bash
   cd api-server/dist/narrative-assistant-server
   ./narrative-assistant-server.exe
   ```

2. Revisar logs de Tauri en consola

3. Verificar permisos de ejecución (Linux/macOS):
   ```bash
   chmod +x src-tauri/binaries/narrative-assistant-server-*/narrative-assistant-server
   ```

### Error: "Port 8008 already in use"

Matar el proceso que usa el puerto:

```bash
# Windows
netstat -ano | findstr :8008
taskkill /PID <PID> /F

# Linux/macOS
lsof -i :8008
kill <PID>
```

### Frontend no conecta con backend

1. Verificar que el backend esté corriendo:
   ```bash
   curl http://127.0.0.1:8008/api/health
   ```

2. Verificar CSP en `tauri.conf.json`

3. Revisar consola del navegador en DevTools

### Build falla en Windows

Puede requerir Visual Studio Build Tools:
- Descargar: https://visualstudio.microsoft.com/downloads/
- Instalar "Desktop development with C++"

## Iconos

Generar iconos desde una imagen PNG de alta resolución:

```bash
# Instalar herramienta
npm install -g @tauri-apps/cli

# Generar iconos
cargo tauri icon path/to/icon.png
```

Esto genera automáticamente todos los tamaños necesarios en `src-tauri/icons/`.

## Distribución

### Windows

- `.msi`: Instalador oficial de Windows
- `.exe` (NSIS): Instalador alternativo con opciones avanzadas

### macOS

- `.app`: Aplicación standalone
- `.dmg`: Imagen de disco para distribución

Requiere firma de código para distribución fuera de desarrollo.

### Linux

- `.deb`: Paquete Debian/Ubuntu
- `.AppImage`: Ejecutable portable (no requiere instalación)

## Recursos

- [Tauri Docs](https://tauri.app/)
- [Tauri 2.0 Guide](https://v2.tauri.app/start/)
- [Sidecar Pattern](https://tauri.app/v1/guides/building/sidecar/)
- [Vue 3 Docs](https://vuejs.org/)
- [PrimeVue Docs](https://primevue.org/)
