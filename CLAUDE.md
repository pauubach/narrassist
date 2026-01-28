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
- ✅ Realizar búsquedas web (WebSearch) con cualquier query para investigar metodologías, papers, documentación, etc.

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

**Flujo de trabajo**:
- Completar las tareas de forma secuencial, no dejar trabajo a medias
- Si el usuario interrumpe con nuevas instrucciones, procesarlas en orden
- Siempre commitear cambios completos antes de pasar a otra tarea

---

## Setup Rapido (Nueva Maquina)

Los modelos NLP se descargan automaticamente la primera vez que se necesitan.

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

# 4. Descargar modelos NLP (opcional, se descargan automaticamente al usar)
python scripts/download_models.py

# 5. Verificar
python scripts/verify_environment.py
# o
narrative-assistant verify
```

**Modelos NLP**: Se descargan bajo demanda la primera vez que se usan y se guardan en `~/.narrative_assistant/models/`.
**Ollama**: Se instala y configura con `setup_ollama.py` - descarga modelos LLM locales automaticamente.

---

## Proyecto

**Asistente de Corrección Narrativa** - Herramienta de asistencia a escritores, editores y correctores profesionales para detectar inconsistencias en cualquier tipo de manuscrito: novelas, memorias, libros de autoayuda, cocina, ensayos, manuales técnicos y más.

### Stack Tecnológico
- **Python** 3.11+
- **NLP**: spaCy (es_core_news_lg), sentence-transformers
- **LLM Local**: Ollama (llama3.2, mistral, qwen2.5)
- **GPU**: PyTorch (CUDA/MPS/CPU auto-detect)
- **DB**: SQLite con WAL mode
- **Formatos**: DOCX (prioritario), TXT, MD, PDF, EPUB

### Requisito de Red
- **Primera ejecucion**: Descarga automatica de modelos NLP (~1 GB)
- **Sistema de licencias**: Verificacion online
- **Ollama**: Descarga inicial de modelos LLM
- **Uso posterior**: 100% offline desde `~/.narrative_assistant/models/` y Ollama local

---

## Modelos NLP (Descarga Bajo Demanda)

Los modelos NLP se descargan automaticamente la primera vez que se necesitan y se almacenan en el directorio del usuario para uso offline posterior.

### Ubicacion de modelos
```
~/.narrative_assistant/
└── models/
    ├── spacy/
    │   └── es_core_news_lg/     # Modelo spaCy espanol (~500 MB)
    └── embeddings/
        └── paraphrase-multilingual-MiniLM-L12-v2/  # sentence-transformers (~500 MB)
```

### Comportamiento de descarga
1. **Primera ejecucion**: Si el modelo no existe, se descarga automaticamente de HuggingFace/spaCy
2. **Cache local**: Los modelos se guardan en `~/.narrative_assistant/models/`
3. **Uso offline**: Las ejecuciones posteriores usan el cache local (sin internet)
4. **Sin red y sin cache**: Falla con mensaje claro indicando como descargar

### Descargar modelos manualmente
```bash
# Descargar todos los modelos
python scripts/download_models.py

# Descargar solo spaCy
python scripts/download_models.py --spacy

# Descargar solo embeddings
python scripts/download_models.py --embeddings

# Forzar re-descarga
python scripts/download_models.py --force

# Ver estado de modelos
python scripts/download_models.py --status
```

### Orden de busqueda de modelos
1. Ruta explicita via `NA_SPACY_MODEL_PATH` / `NA_EMBEDDINGS_MODEL_PATH`
2. `~/.narrative_assistant/models/` (cache del usuario) - **DEFAULT**
3. Descarga automatica si hay conexion a internet

### Variables de entorno para modelos
```bash
# Directorio alternativo para modelos (default: ~/.narrative_assistant/models/)
NA_MODELS_DIR=/path/to/custom/models

# Rutas explicitas (override completo)
NA_SPACY_MODEL_PATH=/path/to/spacy/model
NA_EMBEDDINGS_MODEL_PATH=/path/to/embeddings/model
```

### Deshabilitar descarga automatica
Si prefieres control manual sobre las descargas:
```python
# En codigo
nlp = load_spacy_model(auto_download=False)
model = EmbeddingsModel(auto_download=False)
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

# Windows con GPU vieja o poca VRAM - forzar CPU:
scripts\start_ollama_cpu.bat  # Inicia minimizado en modo CPU
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
│   ├── config.py   # Configuracion centralizada (GPUConfig, NLPConfig, etc.)
│   ├── device.py   # Deteccion GPU (CUDA, MPS, CPU)
│   ├── errors.py   # Jerarquia de errores (NarrativeError, severity levels)
│   ├── model_manager.py  # Gestion de modelos NLP (descarga bajo demanda)
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
    ├── chunking.py     # TextChunker para docs grandes
    ├── ner.py          # NERExtractor - extracción de entidades
    └── coreference_resolver.py  # Sistema de correferencias multi-método
```

### Sistema de Correferencias (Votación Multi-Método)

El sistema usa **4 métodos independientes** con votación ponderada:

| Método | Peso | Descripción |
|--------|------|-------------|
| `embeddings` | 30% | Similitud semántica (sentence-transformers) |
| `llm` | 35% | LLM local (Ollama: llama3.2, mistral, qwen2.5) |
| `morpho` | 20% | Análisis morfosintáctico (spaCy) |
| `heuristics` | 15% | Heurísticas narrativas (proximidad, patrones) |

**Uso**:
```python
from narrative_assistant.nlp.coreference_resolver import resolve_coreferences_voting

result = resolve_coreferences_voting(text, chapters=chapters_data)
# result.chains -> cadenas de correferencia
# result.unresolved -> menciones sin resolver
```

**Documentación completa**: [docs/COREFERENCE_RESOLUTION.md](docs/COREFERENCE_RESOLUTION.md)

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
| `NA_MODELS_DIR` | path | ~/.narrative_assistant/models | Directorio de modelos |
| `NA_SPACY_MODEL_PATH` | path | (auto) | Ruta explicita modelo spaCy |
| `NA_EMBEDDINGS_MODEL_PATH` | path | (auto) | Ruta explicita modelo embeddings |

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
Los modelos se descargan automaticamente. Si falla:
```bash
# Verificar estado de modelos
python scripts/download_models.py --status

# Descargar manualmente
python scripts/download_models.py

# Verificar directorio de cache
ls -la ~/.narrative_assistant/models/
```

### Sin conexion a internet
Si no hay conexion y el modelo no esta en cache:
```bash
# El sistema mostrara un error claro indicando:
# - Que modelo falta
# - Como descargarlo manualmente
# - Que se necesita conexion a internet para la primera descarga
```

### Import errors
Verificar que el paquete está instalado en modo editable:
```bash
pip install -e .
```

---

## Seguridad - Aislamiento de Manuscritos

**CRITICO**: Los manuscritos NUNCA deben salir de la maquina del usuario.

### Reglas de seguridad obligatorias

1. **Acceso a internet limitado**:
   - Verificacion de licencias
   - Descarga inicial de modelos NLP (solo a HuggingFace/spaCy)
   - Descarga inicial de modelos Ollama
2. **Despues de primera descarga**: 100% offline
3. **Sin telemetria** ni analytics de ningun tipo
4. **Sin auto-updates** de modelos o dependencias

### Descarga de modelos - Seguridad

La descarga de modelos es la UNICA excepcion al modo offline:
- Solo se conecta a HuggingFace Hub y repositorios de spaCy
- Solo descarga modelos conocidos y verificados
- Los manuscritos NUNCA se envian a internet
- Despues de la descarga inicial, todo funciona offline

### Al generar codigo - PROHIBIDO:
- Enviar datos de manuscritos a servicios externos
- Analytics, telemetria, logging remoto
- Conexiones de red durante el analisis de documentos

### Al generar codigo - PERMITIDO:
- Descarga de modelos NLP via ModelManager
- Verificacion de licencias
- Conexion a Ollama local (localhost)

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
