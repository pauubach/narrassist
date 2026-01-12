# Fase 0: Fundamentos (Setup)

[← Volver a Roadmap](./README.md) | [← Índice principal](../../README.md)

---

## Objetivo

Establecer la infraestructura base necesaria para el desarrollo del sistema.

**Prioridad**: P0 (CRÍTICO)
**Duración estimada**: 7-12 horas

---

## STEPs de esta Fase

| STEP | Nombre | Complejidad | Horas |
|------|--------|-------------|-------|
| [0.1](../../steps/phase-0/step-0.1-environment.md) | Configuración del Entorno | S | 2-4h |
| [0.2](../../steps/phase-0/step-0.2-project-structure.md) | Estructura del Proyecto | S | 1-2h |
| [0.3](../../steps/phase-0/step-0.3-database-schema.md) | Schema de Base de Datos | M | 4-6h |

---

## STEP 0.1: Configuración del Entorno

### Prerequisitos
- Python 3.11+ instalado
- pip/uv disponible
- 16GB RAM mínimo

### Outputs esperados
- `pyproject.toml` con dependencias
- Modelo spaCy descargado (`es_core_news_lg`)
- Script de verificación de entorno
- Benchmark de memoria con documento de 100k palabras

### Dependencias a instalar

```toml
[project]
name = "narrative-assistant"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    "spacy>=3.7.0",
    "coreferee>=1.4.0",
    "sentence-transformers>=2.2.0",
    "python-docx>=1.1.0",
    "sqlite-utils>=3.35",
    "rich>=13.0.0",  # Para CLI bonita
    "typer>=0.9.0",  # Para CLI
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "ruff>=0.1.0"]
```

### Comandos post-instalación

```bash
python -m spacy download es_core_news_lg
python -m coreferee install es
```

### Criterio de DONE

```python
import spacy
nlp = spacy.load("es_core_news_lg")
doc = nlp("Juan tiene ojos verdes.")
assert any(ent.label_ == "PER" for ent in doc.ents)
print("✅ Entorno configurado correctamente")
```

---

## STEP 0.2: Estructura del Proyecto

### Prerequisitos
- STEP 0.1 completado

### Outputs esperados
- Estructura de directorios creada
- `__init__.py` en cada módulo
- `.gitignore` configurado
- `README.md` básico

### Estructura de directorios

```
narrative-assistant/
├── pyproject.toml
├── README.md
├── .gitignore
├── src/
│   └── narrative_assistant/
│       ├── __init__.py
│       ├── cli.py                    # Interfaz de línea de comandos
│       ├── config.py                 # Configuración y constantes
│       │
│       ├── db/                       # Capa de datos
│       │   ├── __init__.py
│       │   ├── schema.sql            # DDL de SQLite
│       │   ├── models.py             # Dataclasses
│       │   └── repository.py         # CRUD operations
│       │
│       ├── parsers/                  # Importación de documentos
│       │   ├── __init__.py
│       │   ├── docx_parser.py
│       │   └── structure_detector.py # Capítulos/escenas
│       │
│       ├── nlp/                      # Pipeline NLP
│       │   ├── __init__.py
│       │   ├── pipeline.py           # Orquestador
│       │   ├── ner.py                # Extracción de entidades
│       │   ├── coref.py              # Correferencia
│       │   ├── dialogue.py           # Detección de diálogos
│       │   ├── speaker.py            # Atribución de hablante
│       │   ├── temporal.py           # Marcadores temporales
│       │   └── attributes.py         # Extracción de atributos
│       │
│       ├── analysis/                 # Detectores de inconsistencias
│       │   ├── __init__.py
│       │   ├── name_variants.py      # Grafías inconsistentes
│       │   ├── attribute_consistency.py
│       │   ├── repetitions.py        # Léxicas y semánticas
│       │   ├── timeline.py           # Inconsistencias temporales
│       │   ├── voice_profiles.py     # Perfiles de voz
│       │   ├── register.py           # Cambios de registro
│       │   └── focalization.py       # Verificación de POV
│       │
│       ├── alerts/                   # Sistema de alertas
│       │   ├── __init__.py
│       │   ├── engine.py             # Motor de alertas
│       │   ├── confidence.py         # Cálculo de confianza
│       │   └── types.py              # Tipos de alerta
│       │
│       └── export/                   # Generación de outputs
│           ├── __init__.py
│           ├── character_sheet.py
│           ├── style_guide.py
│           └── report.py
│
├── tests/
│   ├── __init__.py
│   ├── fixtures/                     # Documentos de prueba
│   │   ├── sample_novel.docx
│   │   └── known_errors.json
│   ├── test_parsers.py
│   ├── test_nlp.py
│   └── test_analysis.py
│
└── data/
    └── .gitkeep                      # Proyectos del usuario (no en git)
```

### Criterio de DONE

```bash
tree src/
# Debe mostrar la estructura completa
```

---

## STEP 0.3: Schema de Base de Datos

### Prerequisitos
- STEP 0.2 completado

### Outputs esperados
- `src/narrative_assistant/db/schema.sql`
- `src/narrative_assistant/db/models.py` (dataclasses)
- Tests de migración

### Contenido del schema

Ver [Schema de Base de Datos](../02-architecture/database-schema.md) para el DDL completo.

**Tablas principales**:
- `project` - Proyecto y configuración
- `chapter` - Capítulos del documento
- `scene` - Escenas dentro de capítulos
- `entity` - Entidades detectadas
- `text_reference` - Referencias al texto
- `attribute` - Atributos de entidades
- `dialogue` - Diálogos detectados
- `voice_profile` - Perfiles de voz
- `event` - Eventos temporales
- `alert` - Alertas generadas
- `note` - Notas del corrector

### Criterio de DONE

```python
# Test de inserción y consulta
from narrative_assistant.db import create_project, get_entities
project_id = create_project("Test Novel", "es")
entities = get_entities(project_id)
assert entities == []  # Vacío inicialmente
```

---

## Correcciones Críticas Pre-implementación

Antes de comenzar, aplicar estas correcciones basadas en el análisis de expertos:

```yaml
CORRECCIONES_CRITICAS:
  NER:
    modelo_correcto: "es_core_news_lg"  # NO es_dep_news_trf (no existe con NER)
    f1_esperado_ficcion: "60-70%"  # NO 75-80%
    solucion: "Gazetteers dinámicos + validación manual obligatoria"

  Correferencia:
    f1_esperado_ficcion: "45-55%"  # NO 65%
    limitacion_critica: "Pro-drop hace ~40-50% de sujetos invisibles"
    solucion: "Fusión manual OBLIGATORIA, no opcional"

  Focalizacion:
    viabilidad_real: "BAJA"  # NO MEDIA-BAJA
    tasa_error: ">50% en español por pro-drop"
    solucion: "Solo verificar sujetos EXPLÍCITOS; resto = confianza MUY BAJA"

  Memoria:
    riesgo: "16GB puede no ser suficiente con spaCy + embeddings + LLM"
    validacion: "Benchmark obligatorio en STEP 0.1"
```

---

## Siguiente Paso

Completada la Fase 0, continuar con [Fase 1: MVP](./phase-1-mvp.md).
