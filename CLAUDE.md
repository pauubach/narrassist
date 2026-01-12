# Claude Code Instructions - Narrative Assistant (TFM)

## 🔑 Permisos y Autorización

**Claude tiene PERMISO COMPLETO para**:
- ✅ Buscar, leer y analizar cualquier archivo del proyecto
- ✅ Ejecutar código, scripts, tests
- ✅ Instalar dependencias y paquetes
- ✅ Modificar, crear y eliminar archivos
- ✅ Ejecutar comandos de sistema (git, npm, pip, etc.)
- ✅ Revisar bases de datos y logs
- ✅ Hacer cambios arquitectónicos cuando sea necesario
- ✅ Refactorizar código sin preguntar previamente
- ✅ Eliminar código muerto o duplicado
- ✅ Crear y modificar tests

**NO es necesario pedir permiso antes de**:
- Revisar o explorar el código
- Ejecutar tests o análisis
- Hacer búsquedas exhaustivas
- Instalar herramientas necesarias
- Corregir bugs evidentes
- Mejorar logging o debugging

**Solo preguntar cuando**:
- Hay múltiples enfoques arquitectónicos válidos con trade-offs importantes
- Se va a eliminar funcionalidad existente (no código muerto)
- Se necesita aclarar requisitos del usuario

---

## Setup Rápido (Nueva Máquina)

**IMPORTANTE**: Solo copiar la carpeta del proyecto. Los modelos están incluidos localmente.

```bash
# 1. Crear entorno virtual
cd tfm
python3.11 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 2. Instalar dependencias
pip install -e ".[dev]"

# 3. Instalar/Configurar Ollama para LLM local
python scripts/setup_ollama.py

# 4. Verificar (NO requiere internet)
python scripts/verify_environment.py
# o
narrative-assistant verify
```

**No se necesita `spacy download`** - el modelo está en `models/spacy/`.
**Ollama se instala y configura con** `setup_ollama.py` - descarga modelos locales automáticamente.

---

## Proyecto

**Asistente de Corrección Narrativa** - Herramienta de asistencia a correctores literarios profesionales para detectar inconsistencias en manuscritos de ficción.

### Stack Tecnológico
- **Python** 3.11+
- **NLP**: spaCy (es_core_news_lg), sentence-transformers
- **LLM Local**: Ollama (llama3.2, mistral, qwen2.5)
- **GPU**: PyTorch (CUDA/MPS/CPU auto-detect)
- **DB**: SQLite con WAL mode
- **Formatos**: DOCX (prioritario), TXT, MD, PDF, EPUB

### Requisito de Red
- **Único acceso a internet**: Sistema de licencias (verificación) e instalación inicial de Ollama
- **Modelos NLP y LLM**: 100% offline desde `models/` y Ollama local

---

## Modelos Locales

Los modelos se almacenan en el proyecto para funcionamiento offline:

```
tfm/
├── models/
│   ├── spacy/
│   │   └── es_core_news_lg/     # Modelo spaCy español (~500 MB)
│   └── embeddings/
│       └── paraphrase-multilingual-MiniLM-L12-v2/  # sentence-transformers (~500 MB)
```

### Primera vez: Descargar modelos
Si `models/` no existe (primera instalación o proyecto nuevo):
```bash
python scripts/download_models.py
```
Esto descarga los modelos (~1 GB total) y los guarda en `models/`.

### Configuración automática
El sistema busca modelos en este orden:
1. `./models/` (proyecto local) - **PREFERIDO**
2. `~/.narrative_assistant/models/` (usuario)
3. Cache de HuggingFace/spaCy (requiere internet)

### Variables de entorno para modelos locales
```bash
# Opcional - por defecto usa ./models/
NA_SPACY_MODEL_PATH=./models/spacy/es_core_news_lg
NA_EMBEDDINGS_MODEL_PATH=./models/embeddings/paraphrase-multilingual-MiniLM-L12-v2
```

---

## Ollama / LLM Local

Ollama proporciona análisis semántico avanzado mediante modelos LLM que corren 100% localmente.

### Instalación
```bash
# Automática (recomendado)
python scripts/setup_ollama.py

# Manual - Windows
# Descargar desde https://ollama.com/download

# Manual - Linux
curl -fsSL https://ollama.com/install.sh | sh

# Manual - macOS
brew install ollama
```

### Modelos disponibles

| Modelo | Tamaño | Velocidad | Calidad | Notas |
|--------|--------|-----------|---------|-------|
| `llama3.2` | 3B | Rápido | Buena | **Default**, funciona en CPU |
| `mistral` | 7B | Media | Alta | Mejor razonamiento |
| `qwen2.5` | 7B | Media | Alta | Excelente para español |
| `gemma2` | 9B | Lento | Muy alta | Requiere más recursos |

### Descargar modelos
```bash
ollama pull llama3.2     # Recomendado (~2 GB)
ollama pull qwen2.5      # Opcional, mejor español (~4 GB)
ollama pull mistral      # Opcional, mayor calidad (~4 GB)
```

### Iniciar servicio
```bash
ollama serve  # Corre en localhost:11434
```

### Sistema Multi-Modelo (Votación)
El análisis de comportamiento de personajes puede usar múltiples métodos:

1. **Modelos LLM** (llama3.2, mistral, qwen2.5, gemma2)
2. **Reglas y heurísticas** (rule_based) - Siempre disponible
3. **Embeddings semánticos** (embeddings) - Similitud vectorial

Configuración en Settings:
- **Métodos habilitados**: Selección múltiple de métodos
- **Confianza mínima**: Umbral para mostrar expectativas
- **Consenso mínimo**: Porcentaje de métodos que deben coincidir

### Variables de entorno LLM
```bash
NA_LLM_BACKEND=ollama              # Backend: ollama, transformers, none
NA_OLLAMA_HOST=http://localhost:11434  # URL del servidor Ollama
NA_OLLAMA_MODEL=llama3.2           # Modelo por defecto
```

---

## Convenciones de Código

### Python
- **Estilo**: PEP 8, Black formatter, isort
- **Type hints**: Obligatorios en funciones públicas
- **Docstrings**: Google style en español
- **Imports**: Relativos dentro del paquete (`from ..core.config import ...`)

### Patrones Arquitectónicos

#### Result Pattern
Para operaciones que pueden tener éxitos parciales:
```python
from narrative_assistant.core import Result

def process(data) -> Result[OutputType]:
    if error_condition:
        return Result.failure(SomeError(...))
    return Result.success(output)
```

#### Singleton Thread-Safe
Todos los singletons usan double-checked locking:
```python
import threading

_lock = threading.Lock()
_instance = None

def get_instance():
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = create_instance()
    return _instance
```

#### Validación de Archivos
Los parsers SIEMPRE validan antes de abrir:
```python
def parse(self, path: Path) -> Result[RawDocument]:
    validation = self.validate_file(path)  # Path traversal, size, extension
    if validation.is_failure:
        return validation
    # ... continuar
```

---

## Estructura de Módulos

```
src/narrative_assistant/
├── core/           # Infraestructura base
│   ├── config.py   # Configuración centralizada (GPUConfig, NLPConfig, etc.)
│   ├── device.py   # Detección GPU (CUDA, MPS, CPU)
│   ├── errors.py   # Jerarquía de errores (NarrativeError, severity levels)
│   └── result.py   # Result[T] pattern
│
├── persistence/    # Estado y base de datos
│   ├── database.py           # SQLite, transacciones
│   ├── project.py            # Proyecto = un manuscrito
│   ├── document_fingerprint.py  # SHA-256 + n-gram Jaccard
│   ├── session.py            # Sesión de trabajo del revisor
│   └── history.py            # Historial de cambios (undo/redo)
│
├── parsers/        # Lectura de documentos
│   ├── base.py              # DocumentParser ABC, RawDocument
│   ├── docx_parser.py       # Word (.docx)
│   ├── txt_parser.py        # Texto plano + Markdown
│   └── sanitization.py      # InputSanitizer, validate_file_path
│
└── nlp/            # Procesamiento NLP
    ├── spacy_gpu.py    # setup_spacy_gpu(), load_spacy_model()
    ├── embeddings.py   # EmbeddingsModel con fallback OOM
    └── chunking.py     # TextChunker para docs grandes
```

---

## Comandos de Desarrollo

```bash
# Verificar entorno (offline)
narrative-assistant verify

# Info del sistema
narrative-assistant info

# Analizar documento
narrative-assistant analyze documento.docx

# Tests
pytest -v

# Formateo
black src/ && isort src/

# Type checking
mypy src/
```

---

## Variables de Entorno

| Variable | Valores | Default | Descripción |
|----------|---------|---------|-------------|
| `NA_DEVICE` | auto, cuda, mps, cpu | auto | Dispositivo preferido |
| `NA_SPACY_GPU` | true, false | true | Habilitar GPU para spaCy |
| `NA_EMBEDDINGS_GPU` | true, false | true | Habilitar GPU para embeddings |
| `NA_BATCH_SIZE_GPU` | int | 64 | Batch size en GPU |
| `NA_BATCH_SIZE_CPU` | int | 16 | Batch size en CPU |
| `NA_LOG_LEVEL` | DEBUG, INFO, WARNING, ERROR | INFO | Nivel de logging |
| `NA_DATA_DIR` | path | ~/.narrative_assistant | Directorio de datos |
| `NA_SPACY_MODEL_PATH` | path | ./models/spacy/es_core_news_lg | Modelo spaCy local |
| `NA_EMBEDDINGS_MODEL_PATH` | path | ./models/embeddings/... | Modelo embeddings local |

---

## Errores Comunes y Soluciones

### GPU OOM
El sistema tiene fallback automático a CPU con batch reducido. Si persiste:
```bash
export NA_BATCH_SIZE_GPU=32  # Reducir
# o
export NA_DEVICE=cpu  # Forzar CPU
```

### Modelo no encontrado
Verificar que `models/` esté copiado con el proyecto:
```bash
ls -la models/spacy/es_core_news_lg/
ls -la models/embeddings/
```

### Import errors
Verificar que el paquete está instalado en modo editable:
```bash
pip install -e .
```

---

## Seguridad - Aislamiento de Manuscritos

**CRÍTICO**: Los manuscritos NUNCA deben salir de la máquina del usuario.

### Reglas de seguridad obligatorias

1. **Sin acceso a internet** excepto verificación de licencias
2. **Modelos NLP solo locales** - fallar si no están en `models/`
3. **Sin telemetría** ni analytics de ningún tipo
4. **Sin auto-updates** de modelos o dependencias

### Variables de entorno forzadas
```python
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
```

### Al generar código - PROHIBIDO:
- ❌ `requests`, `urllib`, `httpx`, `aiohttp`
- ❌ Cualquier llamada HTTP/HTTPS (excepto licencias)
- ❌ Enviar datos a servicios externos
- ❌ Descargas automáticas de modelos
- ❌ Analytics, telemetría, logging remoto

Ver: [docs/02-architecture/SECURITY.md](docs/02-architecture/SECURITY.md)

---

## Notas para Claude

1. **Idioma**: El código está en inglés, docstrings y comentarios en español
2. **Tests**: Aún no implementados, priorizar implementación
3. **UI**: Vue 3 + PrimeVue (frontend), FastAPI (api-server)
4. **LLM Integration**: Ollama para análisis semántico local (100% offline)
5. **Offline**: Todos los modelos (NLP y LLM) son locales, no requieren internet

### Al generar código:
- Usar type hints siempre
- Seguir Result pattern para operaciones fallibles
- Validar inputs (especialmente paths de archivos)
- Añadir logging apropiado
- Considerar thread-safety en singletons
- **NO añadir código que requiera internet** (excepto licencias)
- **Verificar que no hay filtraciones de datos**
