# Arquitectura de Alto Nivel

[← Volver al índice principal](../../README.md)

---

## Diagrama de Capas

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CAPA DE PRESENTACIÓN                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  CLI (Fase 1)  │  Tauri + Vue 3 (Fase 2+, opcional)             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────┤
│                           CAPA DE APLICACIÓN                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Análisis de    │  Motor de    │  Generador de  │  Exportador  │   │
│  │  Estructura     │  Alertas     │  Fichas        │  de Estilo   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────┤
│                           CAPA DE DOMINIO                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Entidades  │  Atributos  │  Diálogos  │  Timeline  │  Alertas  │   │
│  │  + Coref    │  + Consist. │  + Voz     │  + Eventos │  + Resol. │   │
│  └─────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────┤
│                           CAPA DE NLP                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  spaCy (NER)  │  Coreferee  │  Embeddings  │  LLM (opcional)   │   │
│  │  es_core_news │  (coref)    │  MiniLM      │  Llama/Qwen       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────┤
│                           CAPA DE DATOS                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  SQLite  │  Cache  │  Exportación (JSON/MD/PDF/DOCX)            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Flujo de Datos Principal

```
INPUT                    PROCESAMIENTO                    OUTPUT
─────                    ─────────────                    ──────

.docx  ──► Parser DOCX ──► Estructura ──► NER + Coref ──► Entidades
                               │              │              │
                               │              ▼              │
                               │         Atributos ◄────────┘
                               │              │
                               ▼              ▼
                          Timeline ◄──── Alertas ──► Panel/CLI
                               │              │
                               ▼              ▼
                          Exportación    Hoja de Estilo
```

---

## Stack Tecnológico

### Core

| Componente | Tecnología | Versión | Propósito |
|------------|------------|---------|-----------|
| Lenguaje | Python | 3.11+ | Backend, NLP |
| NLP Base | spaCy | 3.x | Tokenización, POS, NER |
| Modelo NER | es_core_news_lg | - | Entidades nombradas español |
| Correferencia | Coreferee | 1.4+ | Resolución de pronombres |
| Embeddings | sentence-transformers | - | Similitud semántica |
| Modelo Emb. | paraphrase-multilingual-MiniLM | - | Embeddings multilingües |
| Base de datos | SQLite | 3.x | Persistencia local |
| Parser DOCX | python-docx | - | Lectura de manuscritos |

### Opcional (LLM)

| Componente | Tecnología | Propósito |
|------------|------------|-----------|
| LLM local | Llama 3.1 8B / Qwen2.5 7B | Desambiguación de coref |
| Framework | llama.cpp / Ollama | Inferencia local |

### UI (Post-MVP)

| Componente | Tecnología | Propósito |
|------------|------------|-----------|
| Desktop | Tauri | App nativa |
| Frontend | Vue 3 | Interfaz web |
| Comunicación | IPC (Tauri commands) | Python ↔ Frontend |

---

## Estructura del Proyecto

```
narrative-assistant/
├── src/
│   └── narrative_assistant/
│       ├── __init__.py
│       ├── cli.py                    # Interfaz de línea de comandos
│       ├── parsers/
│       │   ├── __init__.py
│       │   └── docx_parser.py        # Parser de DOCX
│       ├── nlp/
│       │   ├── __init__.py
│       │   ├── ner_pipeline.py       # Pipeline NER
│       │   ├── coreference.py        # Resolución de correferencias
│       │   └── embeddings.py         # Similitud semántica
│       ├── analysis/
│       │   ├── __init__.py
│       │   ├── structure.py          # Detección de capítulos/escenas
│       │   ├── dialogue.py           # Detección de diálogos
│       │   ├── attributes.py         # Extracción de atributos
│       │   ├── timeline.py           # Marcadores temporales
│       │   ├── voice.py              # Perfiles de voz
│       │   └── repetitions.py        # Repeticiones léxicas/semánticas
│       ├── alerts/
│       │   ├── __init__.py
│       │   ├── engine.py             # Motor de alertas
│       │   ├── consistency.py        # Inconsistencias de atributos
│       │   ├── names.py              # Variantes de grafía
│       │   └── focalization.py       # Verificación de POV
│       ├── export/
│       │   ├── __init__.py
│       │   ├── style_sheet.py        # Hoja de estilo
│       │   └── character_sheets.py   # Fichas de personajes
│       └── db/
│           ├── __init__.py
│           ├── models.py             # Modelos ORM
│           └── schema.sql            # Schema SQLite
├── tests/
│   ├── fixtures/                     # Documentos de prueba
│   └── ...
├── pyproject.toml
└── README.md
```

---

## Principios de Arquitectura

### 1. Offline First
Todo el procesamiento ocurre localmente. No hay llamadas a APIs externas. El manuscrito nunca sale del equipo.

### 2. Trabajo Inmediato (Progressive Analysis)
**El usuario puede trabajar desde el primer momento.** No esperar a que termine todo el análisis. Los hallazgos se muestran en cuanto se detectan.

### 3. Trazabilidad Universal
Cada dato almacenado tiene referencia a su posición en el texto original (capítulo, página, carácter). Historial completo de estados de alertas.

### 4. Análisis Incremental
Cuando se reimporta un documento modificado, **solo se analizan los cambios**. Las decisiones previas (alertas ignoradas/resueltas) se mantienen.

### 5. Híbrido por Diseño
Automatización + validación humana. El sistema propone, el corrector decide.

### 6. Modular
Cada componente puede evolucionar independientemente. NER puede mejorarse sin afectar timeline.

### 7. Extensible
Nuevas heurísticas pueden añadirse sin modificar el core. Ver [Puntos de Extensión](./extension-points.md).

---

## Documentos de esta Sección

| Documento | Descripción |
|-----------|-------------|
| **[Procesamiento de Documentos](./document-processing.md)** | **Parsers, formatos soportados, normalizacion, pipeline completo** |
| [Modelo de Datos](./data-model.md) | Entidades, atributos, alertas |
| [Schema BD](./database-schema.md) | Schema SQLite completo |
| [Enums de Referencia](./enums-reference.md) | Valores canónicos para todos los enums |
| [Puntos de Extensión](./extension-points.md) | Cómo añadir nuevas heurísticas |
| **[Análisis Progresivo](./progressive-analysis.md)** | **UX en tiempo real, barra de estado, eventos** |
| **[Sistema de Historial](./history-system.md)** | **Estados de alertas, versiones, análisis incremental** |
| **[Sincronización de Posiciones](./position-synchronization.md)** | **Manejo de cambios en documento, anclas resilientes** |

---

## Siguiente Paso

Ver [Análisis Progresivo](./progressive-analysis.md) para entender cómo funciona la experiencia en tiempo real.
