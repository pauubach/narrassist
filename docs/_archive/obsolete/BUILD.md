# Build del Backend para Tauri

Guía para empaquetar el backend Python como ejecutable standalone para uso como Tauri sidecar.

## Requisitos

- Python 3.11+
- PyInstaller
- Modelos NLP en `models/` (ejecutar `python scripts/download_models.py` si no existen)

## Build Rápido

```bash
cd api-server
python build.py
```

Esto genera:
- `dist/narrative-assistant-server/` - Carpeta con ejecutable y dependencias
- `dist/narrative-assistant-server/narrative-assistant-server.exe` - Ejecutable principal

## Opciones de Build

### Build estándar (carpeta - RECOMENDADO)

```bash
python build.py
```

**Ventajas**:
- Inicio rápido
- Fácil debugging
- Recomendado para Tauri sidecar

**Tamaño**: ~2-3 GB (incluye modelos NLP)

### Build ejecutable único (onefile)

```bash
python build.py --onefile
```

**Desventajas**:
- Inicio más lento (descomprime a temp cada vez)
- Más difícil de debuggear
- No recomendado para Tauri

### Limpiar builds

```bash
python build.py --clean
```

## Verificación Manual

### 1. Verificar modelos

```bash
python -c "from pathlib import Path; print(Path('../models/spacy/es_core_news_lg').exists())"
```

Debe devolver `True`.

### 2. Build con PyInstaller

```bash
pyinstaller build_bundle.spec --clean --noconfirm
```

### 3. Probar ejecutable

```bash
cd dist/narrative-assistant-server
./narrative-assistant-server.exe
```

Debe iniciar el servidor en http://127.0.0.1:8008

### 4. Probar endpoints

```bash
curl http://127.0.0.1:8008/api/health
```

Respuesta esperada:
```json
{
  "status": "ok",
  "version": "0.1.0",
  "backend_loaded": true,
  "timestamp": "2024-01-10T12:00:00"
}
```

## Estructura del Build

```
dist/
└── narrative-assistant-server/
    ├── narrative-assistant-server.exe    # Ejecutable principal
    ├── models/                           # Modelos NLP (~2 GB)
    │   ├── spacy/
    │   │   └── es_core_news_lg/
    │   └── embeddings/
    │       └── paraphrase-multilingual-MiniLM-L12-v2/
    ├── _internal/                        # Dependencias Python
    │   ├── torch/
    │   ├── spacy/
    │   ├── transformers/
    │   └── ...
    └── ... (otros archivos de PyInstaller)
```

## Configuración para Tauri

Una vez generado el build, copiar la carpeta a Tauri:

```bash
# Windows
cp -r dist/narrative-assistant-server src-tauri/binaries/narrative-assistant-server-x86_64-pc-windows-msvc

# macOS
cp -r dist/narrative-assistant-server src-tauri/binaries/narrative-assistant-server-x86_64-apple-darwin

# Linux
cp -r dist/narrative-assistant-server src-tauri/binaries/narrative-assistant-server-x86_64-unknown-linux-gnu
```

Ver [Tauri Sidecar Documentation](https://tauri.app/v1/guides/building/sidecar/) para más detalles.

## Troubleshooting

### Error: "Modelo spaCy no encontrado"

```bash
cd ..
python scripts/download_models.py
```

### Error: "PyInstaller no encontrado"

```bash
pip install pyinstaller
```

### Error: "Import error en el ejecutable"

Verificar que todos los módulos estén en `hiddenimports` en `build_bundle.spec`.

Agregar el módulo faltante:

```python
hiddenimports=[
    ...
    'tu_modulo_faltante',
],
```

### Build muy grande

El tamaño es normal debido a:
- Modelos NLP: ~1.5 GB
- PyTorch: ~500 MB
- Dependencias: ~500 MB

Para reducir (avanzado):
- Excluir PyTorch si no se usa GPU
- Usar versión CPU-only de PyTorch
- Comprimir con UPX (ya habilitado en spec)

### Ejecutable inicia lento

Esto es normal en modo onefile. Usar modo carpeta (COLLECT) para mejor rendimiento.

## Automatización

Para CI/CD, el proceso completo:

```bash
# 1. Instalar dependencias
pip install -e ".[dev]"
pip install pyinstaller

# 2. Descargar modelos (si no existen)
python scripts/download_models.py

# 3. Build
cd api-server
python build.py

# 4. Verificar
cd dist/narrative-assistant-server
./narrative-assistant-server.exe &
sleep 5
curl http://127.0.0.1:8008/api/health
killall narrative-assistant-server.exe
```
