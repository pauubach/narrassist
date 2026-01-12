# Estado del Proyecto - Narrative Assistant

## Resumen

**Narrative Assistant** es una herramienta de asistencia a correctores literarios profesionales para detectar inconsistencias en manuscritos de ficción.

**Estado actual**: En desarrollo activo - MVP funcional con UI

---

## Componentes Implementados

### Backend (Python)

#### Core (`src/narrative_assistant/core/`)
- [x] `config.py` - Configuración centralizada
- [x] `device.py` - Detección automática GPU (CUDA/MPS/CPU)
- [x] `errors.py` - Jerarquía de errores con severidad
- [x] `result.py` - Result pattern para operaciones fallibles

#### Parsers (`src/narrative_assistant/parsers/`)
- [x] `docx_parser.py` - Parser para Word (.docx)
- [x] `txt_parser.py` - Parser para texto plano y Markdown
- [x] `sanitization.py` - Validación y sanitización de archivos

#### NLP (`src/narrative_assistant/nlp/`)
- [x] `spacy_gpu.py` - Integración spaCy con GPU
- [x] `embeddings.py` - Modelo de embeddings con fallback OOM
- [x] `chunking.py` - Chunking para documentos grandes

#### LLM Local (`src/narrative_assistant/llm/`)
- [x] `client.py` - Cliente Ollama/Transformers thread-safe
- [x] `expectation_inference.py` - Motor de inferencia de expectativas
- [x] Sistema multi-modelo con votación

#### Persistencia (`src/narrative_assistant/persistence/`)
- [x] `database.py` - SQLite con WAL mode
- [x] `project.py` - Gestión de proyectos
- [x] `chapter.py` - Repositorio de capítulos
- [x] `document_fingerprint.py` - Detección de cambios

#### Entidades (`src/narrative_assistant/entities/`)
- [x] `entity.py` - Modelo de entidades narrativas
- [x] `repository.py` - Repositorio de entidades
- [x] `extractor.py` - Extracción NER con spaCy

### Frontend (Vue 3 + PrimeVue)

#### Vistas (`frontend/src/views/`)
- [x] `DashboardView.vue` - Panel principal
- [x] `ProjectsView.vue` - Lista de proyectos
- [x] `AnalysisView.vue` - Análisis de documento
- [x] `CharactersView.vue` - Gestión de personajes
- [x] `TimelineView.vue` - Línea temporal
- [x] `SettingsView.vue` - Configuración (incluye LLM)

#### Componentes (`frontend/src/components/`)
- [x] `EntityCard.vue` - Tarjeta de entidad
- [x] `RelationshipGraph.vue` - Grafo de relaciones (vis-network)
- [x] `BehaviorExpectations.vue` - Expectativas comportamentales
- [x] `TimelineVisualization.vue` - Visualización temporal

### API Server (FastAPI)
- [x] `api-server/main.py` - Servidor FastAPI completo
- [x] Endpoints para proyectos, capítulos, entidades
- [x] Endpoints LLM para análisis de comportamiento
- [x] CORS configurado para desarrollo

---

## Funcionalidades LLM

### Integración con Ollama
- **Backend**: Ollama corriendo localmente (localhost:11434)
- **Modelos soportados**: llama3.2, mistral, qwen2.5, gemma2
- **100% offline**: Una vez instalados, no requieren internet

### Sistema Multi-Modelo
```
Métodos de Inferencia:
├── LLM (Ollama)
│   ├── llama3.2 (3B) - Rápido, buena calidad
│   ├── mistral (7B) - Mayor calidad
│   ├── qwen2.5 (7B) - Excelente para español
│   └── gemma2 (9B) - Muy alta calidad
├── rule_based - Reglas y heurísticas
└── embeddings - Similitud semántica
```

### Configuración en UI
- Selección múltiple de métodos de inferencia
- Umbral de confianza mínima (20-90%)
- Consenso mínimo para violaciones (30-100%)
- Opción de priorizar velocidad

---

## Scripts de Instalación

| Script | Descripción |
|--------|-------------|
| `scripts/setup_ollama.py` | Instala Ollama y descarga modelos |
| `scripts/download_models.py` | Descarga modelos NLP (spaCy, embeddings) |
| `scripts/verify_environment.py` | Verifica instalación completa |

---

## Pendiente

### Alta Prioridad
- [ ] Tests unitarios y de integración
- [ ] Detección de violaciones de comportamiento
- [ ] Historial de cambios (undo/redo)

### Media Prioridad
- [ ] Sistema de licencias
- [ ] Exportación de informes
- [ ] Soporte PDF y EPUB

### Baja Prioridad
- [ ] Empaquetado con Tauri (desktop app)
- [ ] Temas de color personalizados
- [ ] Backup automático

---

## Estructura de Directorios

```
tfm/
├── src/narrative_assistant/    # Backend Python
│   ├── core/                   # Infraestructura
│   ├── parsers/                # Lectura de documentos
│   ├── nlp/                    # Procesamiento NLP
│   ├── llm/                    # Integración LLM local
│   ├── entities/               # Entidades narrativas
│   └── persistence/            # Base de datos
├── frontend/                   # Vue 3 + PrimeVue
│   ├── src/views/              # Vistas principales
│   ├── src/components/         # Componentes reutilizables
│   └── src/stores/             # Estado (Pinia)
├── api-server/                 # FastAPI server
├── models/                     # Modelos NLP locales
│   ├── spacy/                  # es_core_news_lg
│   └── embeddings/             # sentence-transformers
└── scripts/                    # Scripts de utilidad
```

---

## Comandos Rápidos

```bash
# Backend
pip install -e ".[dev]"
python scripts/setup_ollama.py

# Frontend
cd frontend && npm install && npm run dev

# API Server
cd api-server && python main.py

# Ollama
ollama serve
ollama pull llama3.2
```

---

## Última Actualización

**Fecha**: Enero 2026

**Cambios recientes**:
- Integración completa con Ollama para LLM local
- Sistema multi-modelo con votación
- UI de configuración para métodos de inferencia
- Visualización de votos por expectativa
- Script de instalación automática de Ollama
