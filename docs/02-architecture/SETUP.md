# Guía de Setup - Narrative Assistant

Esta guía te permite configurar el entorno de desarrollo en cualquier ordenador.

## Requisitos Previos

### Sistema Operativo
- **macOS** 12.3+ (para Apple Silicon GPU)
- **Linux** (Ubuntu 20.04+, Fedora 35+)
- **Windows** 10/11 con WSL2 (recomendado) o nativo

### Software Base
- **Python** 3.11 o 3.12 (recomendado: 3.11)
- **Git** 2.30+
- **pip** 23.0+

### Opcional (para GPU)
- **CUDA** 12.x (NVIDIA GPUs)
- **PyTorch** con soporte MPS (Apple Silicon)

---

## Instalación Rápida

### 1. Clonar el repositorio

```bash
git clone <url-del-repo> tfm
cd tfm
```

### 2. Crear entorno virtual

```bash
# Con venv (recomendado)
python3.11 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# o en Windows: .venv\Scripts\activate

# Alternativa con conda
conda create -n narrative-assistant python=3.11
conda activate narrative-assistant
```

### 3. Instalar dependencias

```bash
# Dependencias base
pip install -e ".[dev]"

# O instalación completa con todas las opciones
pip install -e ".[dev,gpu,docs]"
```

### 4. Descargar modelo spaCy

```bash
python -m spacy download es_core_news_lg
```

### 5. Verificar instalación

```bash
python scripts/verify_environment.py
```

---

## Configuración por Plataforma

### macOS (Apple Silicon)

```bash
# PyTorch con MPS (GPU Apple Silicon)
pip install torch torchvision torchaudio

# Verificar MPS
python -c "import torch; print(f'MPS disponible: {torch.backends.mps.is_available()}')"
```

### Linux con NVIDIA GPU

```bash
# PyTorch con CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# CuPy para spaCy GPU (opcional, mejora ~1.5x)
pip install cupy-cuda12x

# Verificar CUDA
python -c "import torch; print(f'CUDA disponible: {torch.cuda.is_available()}')"
```

### Windows / CPU-only

```bash
# PyTorch CPU
pip install torch torchvision torchaudio

# La aplicación detectará automáticamente y usará CPU
```

---

## Variables de Entorno

Crear archivo `.env` en la raíz del proyecto (no se commitea):

```bash
# Configuración de dispositivo
NA_DEVICE=auto          # auto | cuda | mps | cpu
NA_SPACY_GPU=true       # true | false
NA_EMBEDDINGS_GPU=true  # true | false

# Batch sizes (ajustar según VRAM)
NA_BATCH_SIZE_GPU=64    # Reducir si hay OOM
NA_BATCH_SIZE_CPU=16

# Logging
NA_LOG_LEVEL=INFO       # DEBUG | INFO | WARNING | ERROR

# Directorio de datos (opcional)
NA_DATA_DIR=~/.narrative_assistant
```

---

## Estructura del Proyecto

```
tfm/
├── src/narrative_assistant/
│   ├── core/           # Configuración, errores, dispositivos
│   │   ├── config.py   # Sistema de configuración centralizado
│   │   ├── device.py   # Detección GPU (CUDA/MPS/CPU)
│   │   ├── errors.py   # Jerarquía de errores
│   │   └── result.py   # Result pattern para éxitos parciales
│   │
│   ├── persistence/    # Base de datos y estado
│   │   ├── database.py           # SQLite con WAL mode
│   │   ├── project.py            # Gestión de proyectos
│   │   ├── document_fingerprint.py  # Detección de documentos similares
│   │   ├── session.py            # Sesiones de trabajo
│   │   └── history.py            # Historial de cambios
│   │
│   ├── parsers/        # Lectura de documentos
│   │   ├── base.py              # Clases base, detección de formato
│   │   ├── docx_parser.py       # Microsoft Word
│   │   ├── txt_parser.py        # Texto plano / Markdown
│   │   └── sanitization.py      # Validación de inputs
│   │
│   └── nlp/            # Procesamiento de lenguaje
│       ├── spacy_gpu.py    # Configuración spaCy + GPU
│       ├── embeddings.py   # sentence-transformers
│       └── chunking.py     # División de documentos grandes
│
├── docs/               # Documentación
│   └── 02-architecture/
│
├── tests/              # Tests (próximamente)
├── scripts/            # Scripts de utilidad
└── pyproject.toml      # Configuración del proyecto
```

---

## Comandos Útiles

### Desarrollo

```bash
# Activar entorno
source .venv/bin/activate

# Verificar entorno
python scripts/verify_environment.py

# Ejecutar tests (cuando estén implementados)
pytest

# Formatear código
black src/
isort src/

# Linting
ruff check src/
mypy src/
```

### Base de Datos

```bash
# La DB se crea automáticamente en ~/.narrative_assistant/
# Para reset:
rm -rf ~/.narrative_assistant/narrative_assistant.db*
```

---

## Solución de Problemas

### Error: "spaCy model not found"

```bash
python -m spacy download es_core_news_lg
```

### Error: "CUDA out of memory"

Reducir batch size en `.env`:
```bash
NA_BATCH_SIZE_GPU=32  # o 16
```

O forzar CPU:
```bash
NA_DEVICE=cpu
```

### Error: "MPS not available" (macOS)

- Verificar macOS 12.3+
- Verificar Apple Silicon (no Intel)
- Actualizar PyTorch: `pip install --upgrade torch`

### Error: "Permission denied" en Windows

- Usar PowerShell como Administrador
- O usar WSL2 (recomendado)

---

## Continuación del Trabajo

Si clonas en otro ordenador:

1. Seguir pasos de instalación
2. La base de datos es local (no se sincroniza)
3. Los documentos analizados deben cargarse de nuevo
4. El fingerprinting detectará documentos similares

---

## Contacto

Para problemas específicos del TFM, consultar la documentación en `docs/` o contactar al autor.
