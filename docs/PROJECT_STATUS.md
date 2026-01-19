# Estado del Proyecto - Narrative Assistant

> **Última actualización**: 2026-01-19 (Audit completo - MVP listo)
> **Versión**: 1.0.0-rc1 (Release Candidate - P0/P1/P2 completados)

---

## Resumen Ejecutivo

**Narrative Assistant** es una herramienta NLP 100% offline para editores literarios. Analiza manuscritos detectando inconsistencias narrativas, entidades, atributos, relaciones, timeline y problemas de estilo.

### Stack Tecnológico

| Capa | Tecnología |
|------|------------|
| **Backend** | Python 3.11+, spaCy 3.8, sentence-transformers, PyTorch, SQLite |
| **LLM Local** | Ollama (llama3.2, mistral, qwen2.5) - 100% offline |
| **Frontend** | Vue 3.4, TypeScript 5.3, PrimeVue, Pinia, Vite |
| **Desktop** | Tauri 2.0, Rust |
| **API Bridge** | FastAPI, Uvicorn (33 endpoints) |

---

## Estado de Implementación por Fases

### FASES BACKEND (0-9) - ✅ COMPLETADO

#### Phase 0: Fundamentos ✅
| Step | Estado | Módulo |
|------|--------|--------|
| 0.1 Environment | ✅ | `pyproject.toml`, dependencias |
| 0.2 Project Structure | ✅ | Estructura de directorios |
| 0.3 Database Schema | ✅ | `persistence/database.py` |

#### Phase 1: Infraestructura ✅
| Step | Estado | Módulo |
|------|--------|--------|
| 1.1 DOCX Parser | ✅ | `parsers/docx_parser.py` |
| 1.2 TXT Parser | ✅ | `parsers/txt_parser.py` |
| 1.3 Structure Detector | ✅ | `parsers/structure_detector.py` |
| 1.4 Input Sanitization | ✅ | `parsers/sanitization.py` |

#### Phase 2: Core ✅
| Step | Estado | Módulo |
|------|--------|--------|
| 2.1 Error Handling | ✅ | `core/errors.py` |
| 2.2 Result Pattern | ✅ | `core/result.py` |
| 2.3 Configuration | ✅ | `core/config.py` |
| 2.4 Device Detection | ✅ | `core/device.py` |

#### Phase 3: Persistencia ✅
| Step | Estado | Módulo |
|------|--------|--------|
| 3.1 Database | ✅ | `persistence/database.py` |
| 3.2 Projects | ✅ | `persistence/project.py` |
| 3.3 Sessions | ✅ | `persistence/session.py` |
| 3.4 History | ✅ | `persistence/history.py` |
| 3.5 Fingerprinting | ✅ | `persistence/document_fingerprint.py` |
| 3.6 Chapters | ✅ | `persistence/chapter.py` |

#### Phase 4: Entidades ✅
| Step | Estado | Módulo |
|------|--------|--------|
| 4.1 Entity Models | ✅ | `entities/models.py` (18 tipos) |
| 4.2 Entity Repository | ✅ | `entities/repository.py` |
| 4.3 Entity Fusion | ✅ | `entities/fusion.py` |
| 4.4 Semantic Fusion | ✅ | `entities/semantic_fusion.py` |

#### Phase 5: NLP Core ✅
| Step | Estado | Módulo |
|------|--------|--------|
| 5.1 spaCy Integration | ✅ | `nlp/spacy_gpu.py` |
| 5.2 Embeddings | ✅ | `nlp/embeddings.py` |
| 5.3 NER Extractor | ✅ | `nlp/ner.py` |
| 5.4 Dialogue Parser | ✅ | `nlp/dialogue.py` |
| 5.5 Coreference Legacy | ✅ | `nlp/coref.py` |
| 5.6 Coreference Resolver | ✅ | `nlp/coreference_resolver.py` (4 métodos votación) |
| 5.7 Attributes | ✅ | `nlp/attributes.py` (40+ patrones) |
| 5.8 AI Attributes | ✅ | `nlp/ai_attribute_extractor.py` |
| 5.9 Attribute Consolidation | ✅ | `nlp/attribute_consolidation.py` |
| 5.10 Sentiment | ✅ | `nlp/sentiment.py` |
| 5.11 Chunking | ✅ | `nlp/chunking.py` |

#### Phase 6: Análisis de Calidad ✅
| Step | Estado | Módulo |
|------|--------|--------|
| 6.1 Attribute Consistency | ✅ | `analysis/attribute_consistency.py` |
| 6.2 Orthography | ✅ | `nlp/orthography/` (3 archivos) |
| 6.3 Grammar | ✅ | `nlp/grammar/` (5 archivos) + LanguageTool |
| 6.4 Repetitions | ✅ | `nlp/style/repetition_detector.py` |
| 6.5 Coherence | ✅ | `nlp/style/coherence_detector.py` |
| 6.6 Extraction Pipeline | ✅ | `nlp/extraction/` (6 archivos) |

#### Phase 7: Análisis Narrativo Avanzado ✅
| Step | Estado | Módulo |
|------|--------|--------|
| 7.1 Voice Profiles | ✅ | `voice/profiles.py` |
| 7.2 Voice Deviations | ✅ | `voice/deviations.py` |
| 7.3 Register Analysis | ✅ | `voice/register.py` |
| 7.4 Speaker Attribution | ✅ | `voice/speaker_attribution.py` |
| 7.5 Focalization Declaration | ✅ | `focalization/declaration.py` |
| 7.6 Focalization Violations | ✅ | `focalization/violations.py` |
| 7.7 Temporal Markers | ✅ | `temporal/markers.py` |
| 7.8 Timeline Builder | ✅ | `temporal/timeline.py` |
| 7.9 Temporal Inconsistencies | ✅ | `temporal/inconsistencies.py` |

#### Phase 8: Integración y Alertas ✅
| Step | Estado | Módulo |
|------|--------|--------|
| 8.1 Alert Models | ✅ | `alerts/models.py` |
| 8.2 Alert Engine | ✅ | `alerts/engine.py` (13 categorías) |
| 8.3 Alert Repository | ✅ | `alerts/repository.py` |
| 8.4 Character Sheets | ✅ | `exporters/character_sheets.py` |
| 8.5 Style Guide | ✅ | `exporters/style_guide.py` |
| 8.6 Pipeline Legacy | ✅ | `pipelines/analysis_pipeline.py` |
| 8.7 Pipeline Unified | ✅ | `pipelines/unified_analysis.py` |
| 8.8 Pipeline Export | ✅ | `pipelines/export.py` |
| 8.9 CLI | ✅ | `cli.py` |

#### Phase 9: Grafo de Relaciones ✅
| Step | Estado | Módulo |
|------|--------|--------|
| 9.1 Relationship Models | ✅ | `relationships/models.py` (50+ tipos) |
| 9.2 Relationship Detector | ✅ | `relationships/detector.py` |
| 9.3 Relationship Repository | ✅ | `relationships/repository.py` |
| 9.4 Relationship Analyzer | ✅ | `relationships/analyzer.py` |
| 9.5 Expectation Inference | ✅ | `relationships/inference.py` |
| 9.6 Interaction Models | ✅ | `interactions/models.py` |
| 9.7 Interaction Detector | ✅ | `interactions/detector.py` |
| 9.8 Interaction Patterns | ✅ | `interactions/pattern_analyzer.py` |
| 9.9 Interaction Repository | ✅ | `interactions/repository.py` |
| 9.10 LLM Client | ✅ | `llm/client.py` |
| 9.11 LLM Expectation Inference | ✅ | `llm/expectation_inference.py` |
| 9.12 Analysis: Emotional Coherence | ✅ | `analysis/emotional_coherence.py` |
| 9.13 Analysis: Relationship Clustering | ✅ | `analysis/relationship_clustering.py` |
| 9.14 Analysis: Character Knowledge | ✅ | `analysis/character_knowledge.py` |

---

### FASES FRONTEND (10-14) - ✅ COMPLETADO

#### Phase 10: UI Setup ✅
| Step | Estado | Componente |
|------|--------|------------|
| 10.1 Tauri Setup | ✅ | `src-tauri/` |
| 10.2 Vue + Vite | ✅ | `frontend/` |
| 10.3 PrimeVue | ✅ | Componentes UI |
| 10.4 Pinia Stores | ✅ | `stores/` (7 stores) |
| 10.5 Vue Router | ✅ | 7 vistas |
| 10.6 FastAPI Bridge | ✅ | `api-server/main.py` (33 endpoints) |

#### Phase 11: UI Core Features ✅
| Step | Estado | Componente |
|------|--------|------------|
| 11.1 Projects List | ✅ | `ProjectsView.vue` |
| 11.2 Analysis Progress | ✅ | `analysis/AnalysisProgress.vue` |
| 11.3 Project Dashboard | ✅ | `ProjectDetailView.vue` |
| 11.4 Document Viewer | ✅ | `DocumentViewer.vue` |
| 11.5 Chapter Tree | ✅ | `ChapterTree.vue` |

#### Phase 12: UI Entity Management ✅
| Step | Estado | Componente |
|------|--------|------------|
| 12.1 Entity List | ✅ | `EntityList.vue`, `EntitiesView.vue` |
| 12.2 Entity Fusion | ✅ | `MergeEntitiesDialog.vue` |
| 12.3 Character Sheet | ✅ | `CharacterSheet.vue`, `CharacterView.vue` |

#### Phase 13: UI Alerts & Relations ✅
| Step | Estado | Componente |
|------|--------|------------|
| 13.1 Alert List | ✅ | `AlertList.vue`, `AlertsView.vue` |
| 13.2 Alert Management | ✅ | Resolver/Descartar/Reabrir |
| 13.3 Relationship Graph | ✅ | `RelationshipGraph.vue` (vis-network) |
| 13.4 Behavior Expectations | ✅ | `BehaviorExpectations.vue` |

#### Phase 14: UI Polish ✅
| Step | Estado | Componente |
|------|--------|------------|
| 14.1 Export Dialog | ✅ | `ExportDialog.vue` |
| 14.2 Settings View | ✅ | `SettingsView.vue` |
| 14.3 Theme System | ✅ | Dark/Light/Auto (`theme.ts`) |
| 14.4 Workspace Layout | ✅ | `workspace/WorkspaceLayout.vue` |
| 14.5 Design System | ✅ | `components/ds/` (7 componentes) |

---

## Inventario de Módulos Backend

### Módulos Principales (17)

| # | Módulo | Archivos | Descripción |
|---|--------|----------|-------------|
| 1 | `core/` | 4 | Infraestructura: config, device, errors, result |
| 2 | `persistence/` | 6 | BD: database, project, session, history, fingerprint, chapter |
| 3 | `parsers/` | 5 | Documentos: base, docx, txt, structure, sanitization |
| 4 | `entities/` | 4 | Entidades: models, repository, fusion, semantic_fusion |
| 5 | `nlp/` | 12 | NLP core + submódulos |
| 6 | `analysis/` | 4 | Consistencia: attributes, relationships, knowledge, emotional |
| 7 | `voice/` | 4 | Voz: profiles, deviations, register, speaker_attribution |
| 8 | `focalization/` | 2 | POV: declaration, violations |
| 9 | `temporal/` | 3 | Timeline: markers, timeline, inconsistencies |
| 10 | `relationships/` | 5 | Relaciones: models, detector, repository, analyzer, inference |
| 11 | `interactions/` | 4 | Interacciones: models, detector, pattern_analyzer, repository |
| 12 | `alerts/` | 3 | Alertas: models, engine, repository |
| 13 | `llm/` | 2 | LLM local: client, expectation_inference |
| 14 | `pipelines/` | 3 | Orquestación: analysis, unified, export |
| 15 | `exporters/` | 2 | Reportes: character_sheets, style_guide |
| 16 | `cli.py` | 1 | Interfaz de línea de comandos |
| 17 | `api-server/` | 1 | FastAPI bridge (main.py - 3300+ líneas) |

### Submódulos NLP (5)

| Submódulo | Archivos | Descripción |
|-----------|----------|-------------|
| `nlp/extraction/` | 7 | Pipeline de extracción: router, aggregator, base, extractors/ |
| `nlp/grammar/` | 5 | Gramática: checker, spanish_rules, languagetool, base |
| `nlp/orthography/` | 3 | Ortografía: spelling_checker, base |
| `nlp/style/` | 2 | Estilo: repetition_detector, coherence_detector |
| `nlp/training_data/` | 3 | Training: examples, weight_learner |

---

## Inventario de Componentes Frontend

### Vistas (7)
- `HomeView.vue` - Pantalla inicio
- `ProjectsView.vue` - Lista de proyectos
- `ProjectDetailView.vue` - Dashboard proyecto
- `EntitiesView.vue` - Gestión entidades
- `CharacterView.vue` - Ficha personaje
- `AlertsView.vue` - Lista alertas
- `SettingsView.vue` - Configuración

### Componentes (53 total)

| Categoría | Cantidad | Componentes |
|-----------|----------|-------------|
| workspace/ | 8 | WorkspaceLayout, ProjectWorkspace, Tabs, TextTab, EntitiesTab, AlertsTab, RelationsTab, ResumenTab, PanelResizer |
| sidebar/ | 3 | AlertsPanel, CharactersPanel, ChaptersPanel |
| inspector/ | 4 | EntityInspector, AlertInspector, ChapterInspector, ProjectSummary |
| panels/ | 3 | EntityPanel, AlertPanel, DetailPanel |
| ds/ | 7 | DsBadge, DsCard, DsEmptyState, DsInput, DsListItem, DsLoadingState, DsTooltip |
| modals/ | 2 | EntityModal, AlertModal |
| analysis/ | 1 | AnalysisProgress |
| document/ | 1 | TextHighlighter |
| layout/ | 1 | StatusBar |
| Root | 14 | AboutDialog, AlertList, BehaviorExpectations, ChapterTree, CharacterSheet, CommandPalette, DocumentViewer, EntityList, ExportDialog, KeyboardShortcutsDialog, MenuBar, MergeEntitiesDialog, RelationshipGraph, TutorialDialog |

### Stores (7)
- `app.ts` - Estado global
- `projects.ts` - Gestión proyectos
- `workspace.ts` - Estado workspace
- `selection.ts` - Selección actual
- `theme.ts` - Temas UI (19KB, muy completo)
- `analysis.ts` - Estado análisis
- `system.ts` - Estado del sistema

### Composables (8)
- `useKeyboardShortcuts.ts` - Atajos de teclado
- `useAnalysisStream.ts` - SSE para análisis
- `useEntityUtils.ts` - Utilidades de entidades
- `useAlertUtils.ts` - Utilidades de alertas
- `useNavigation.ts` - Navegación
- `useHighlight.ts` - Resaltado de texto
- `usePerformance.ts` - Métricas de rendimiento
- `index.ts` - Exportaciones

---

## Tests

| Suite | Tests | Estado |
|-------|-------|--------|
| Unit tests | 612 | ✅ Passing |
| Integration | 12 | ✅ Passing |
| E2E (Playwright) | Pending | 🔄 |

### Tests por módulo destacados:
- `test_relationships.py` - 56 tests
- `test_interactions.py` - 48 tests
- `test_voice.py` - 46 tests
- `test_sentiment.py` - 35 tests
- `test_coreference_resolver.py` - 32 tests
- Otros - 395 tests

---

## Métricas Reales

### Backend
- **Archivos Python**: 103
- **Líneas de código**: ~49,000 LoC Python
- **Tipos de entidad**: 18
- **Tipos de relación**: 50+
- **Categorías de alerta**: 13
- **Métodos de correferencia**: 4 (embeddings, llm, morpho, heuristics)

### Frontend
- **Componentes Vue**: 53
- **Vistas**: 7
- **Líneas de código**: ~30,000 LoC TypeScript/Vue
- **Stores Pinia**: 7
- **Composables**: 8
- **Endpoints API**: 33

### API Server
- **Líneas de código**: 3,500+ LoC
- **Endpoints**: 33 (GET, POST, PUT, DELETE)
- **Integración backend**: Completa (imports de 20+ módulos)

---

## Lo que FALTA por hacer (Audit Detallado)

> **Audit realizado**: 2026-01-19 (verificación completa - MVP listo)

---

### 🚨 P0 - CRÍTICO (Blockers para release) ✅ COMPLETADO

#### Tauri - ✅ COMPLETADO

| Archivo | Estado |
|---------|--------|
| `src-tauri/icons/` | ✅ **COMPLETADO** - 32x32, 128x128, icns, ico |
| `src-tauri/src/menu.rs` | ✅ **COMPLETADO** - Menú nativo implementado |
| Sidecar binary | ✅ **COMPLETADO** - `scripts/build_sidecar.py` |

#### API Server - ✅ COMPLETADO

| Archivo | Línea | Estado |
|---------|-------|--------|
| `api-server/main.py` | 906 | ✅ **Fusión de entidades IMPLEMENTADA** (2026-01-14) |

#### Frontend - CRUD Stubs - ✅ COMPLETADO

| Archivo | Función | Estado |
|---------|---------|--------|
| `EntitiesView.vue` | `saveEntity()` | ✅ **IMPLEMENTADO** (2026-01-14) - PUT /api/.../entities/{id} |
| `EntitiesView.vue` | `onEntityDelete()` | ✅ **IMPLEMENTADO** (2026-01-14) - DELETE /api/.../entities/{id} |
| `CharacterView.vue` | `saveCharacter()` | ✅ **IMPLEMENTADO** (2026-01-14) - PUT /api/.../entities/{id} |
| `CharacterView.vue` | `saveAttribute()` | ✅ **IMPLEMENTADO** (2026-01-14) - POST /api/.../attributes |
| `CharacterView.vue` | `onDeleteAttribute()` | ✅ **IMPLEMENTADO** (2026-01-14) - DELETE /api/.../attributes/{id} |
| `AlertsView.vue` | Bulk actions | ✅ **COMPLETADO** - resolve/dismiss/reopen/resolve-all funcionan |

**Endpoints API añadidos:**
- `PUT /api/projects/{id}/entities/{entity_id}` - Actualizar entidad
- `DELETE /api/projects/{id}/entities/{entity_id}` - Eliminar/desactivar entidad
- `GET /api/projects/{id}/entities/{entity_id}/attributes` - Listar atributos
- `POST /api/projects/{id}/entities/{entity_id}/attributes` - Crear atributo
- `PUT /api/projects/{id}/entities/{entity_id}/attributes/{attr_id}` - Actualizar atributo
- `DELETE /api/projects/{id}/entities/{entity_id}/attributes/{attr_id}` - Eliminar atributo

---

### 🔶 P1 - IMPORTANTE (Funcionalidad incompleta)

#### Backend TODOs con líneas específicas

| Archivo | Línea | Estado |
|---------|-------|--------|
| `core/config.py` | 313, 325 | ✅ **save_config() y load_config() IMPLEMENTADOS** (2026-01-14) |
| `persistence/history.py` | 399 | ✅ **undo_merge() IMPLEMENTADO** (2026-01-14) |
| `pipelines/unified_analysis.py` | 1254, 1259 | ✅ **temporal/focalization consistency IMPLEMENTADOS** (2026-01-14) |
| `pipelines/analysis_pipeline.py` | 1296 | ✅ **source_mention_id IMPLEMENTADO** (2026-01-14) - busca mención por posición |
| `pipelines/analysis_pipeline.py` | 1452 | ✅ **position en alertas IMPLEMENTADO** (2026-01-14) - desde AttributeInconsistency |
| `pipelines/analysis_pipeline.py` | 1915 | ✅ **Persistencia SQLite IMPLEMENTADA** (2026-01-14) - FocalizationDeclarationService |
| `nlp/ai_attribute_extractor.py` | 218 | ✅ **Resolución pronombres IMPLEMENTADA** (2026-01-14) - _resolve_pronoun_to_entity() |
| `entities/semantic_fusion.py` | 178 | ✅ **Umbral configurable IMPLEMENTADO** (2026-01-14) - `update_fusion_threshold()` + config |
| `alerts/engine.py` | 892 | ✅ **Priorización por capítulo IMPLEMENTADA** (2026-01-14) - `get_by_project_prioritized()` |

**Implementaciones completadas (2026-01-14):**
- **`find_mention_by_position()`** en `entities/repository.py`: Nuevo método para buscar menciones por posición de caracteres
- **`AttributeInconsistency.value1_position/value2_position`**: Nuevos campos para tracking de posición en inconsistencias
- **`SQLiteFocalizationRepository`** en `focalization/declaration.py`: Persistencia SQLite para declaraciones de focalización
- **`_resolve_pronoun_to_entity()`** en `nlp/ai_attribute_extractor.py`: Resolución de pronombres a entidades por proximidad y concordancia
- **Schema v2**: Nueva tabla `focalization_declarations` para persistir focalización
- **`_get_fusion_threshold()` + `update_fusion_threshold()`**: Umbral de fusión configurable desde Settings
- **`get_by_project_prioritized()`** en `alerts/repository.py`: Alertas priorizadas por capítulo actual
- **Endpoints API**: `POST/DELETE /api/projects/{id}/relationships` para CRUD de relaciones

#### Frontend TODOs con líneas específicas

| Archivo | Línea | Estado |
|---------|-------|--------|
| `ProjectDetailView.vue` | 571 | ✅ **Filtro severidad IMPLEMENTADO** - usa `workspaceStore.setAlertSeverityFilter()` |
| `ProjectDetailView.vue` | 596 | ✅ **Navegación a menciones IMPLEMENTADO** - usa `workspaceStore.navigateToEntityMentions()` |
| `CharacterView.vue` | 489 | ✅ **Guardado relación IMPLEMENTADO** - `POST /api/.../relationships` |
| `CharacterView.vue` | 496 | ✅ **Eliminación relación IMPLEMENTADO** - `DELETE /api/.../relationships/{id}` |
| `CharacterView.vue` | 501 | ✅ **Exportación ficha IMPLEMENTADO** - descarga JSON |
| `EntitiesView.vue` | 524 | ✅ **Exportación entidades IMPLEMENTADO** - descarga JSON |
| `AlertsView.vue` | 454 | ✅ **Exportación alertas IMPLEMENTADO** - descarga JSON |
| `DocumentViewer.vue` | 413 | 🔄 **Exportación DOCX/PDF** - pendiente (solo JSON implementado) |
| `RelationshipGraph.vue` | 189 | 🔄 Post-MVP: Filtros por tipo de relación |
| `BehaviorExpectations.vue` | 167 | 🔄 Post-MVP: Edición manual de expectativas |
| `MergeEntitiesDialog.vue` | 203 | 🔄 Post-MVP: Preview de merge |

#### Tauri - ✅ COMPLETADO

- `src-tauri/src/menu.rs` - Implementado con File, Edit, View, Help
- `src-tauri/icons/` - 6 archivos de iconos generados

#### Tests - 14+ tests skipped por fixtures faltantes

| Archivo | Tests Skipped | Razón |
|---------|---------------|-------|
| `test_docx_parser.py` | 3 | Falta fixture `complex_document.docx` |
| `test_txt_parser.py` | 2 | Falta fixture `malformed_encoding.txt` |
| `test_coreference_resolver.py` | 4 | Requiere Ollama running |
| `test_llm_client.py` | 5 | Requiere Ollama running |

#### Tests E2E - NO implementados

| Archivo | Estado | Cobertura necesaria |
|---------|--------|---------------------|
| `frontend/e2e/alerts.spec.ts` | 🔄 Parcial | Solo alertas básicas |
| `frontend/e2e/projects.spec.ts` | ❌ No existe | CRUD proyectos |
| `frontend/e2e/entities.spec.ts` | ❌ No existe | CRUD entidades |
| `frontend/e2e/analysis.spec.ts` | ❌ No existe | Flujo completo de análisis |

---

### 🔷 P2 - MEJORAS (Post-MVP)

#### Backend - Mejoras de consistencia

| Módulo | TODO |
|--------|------|
| `temporal/inconsistencies.py` | Verificación de inconsistencias temporales básica - faltan edge cases |
| `focalization/violations.py` | Solo detecta violaciones simples |
| `voice/deviations.py` | Umbral de desviación hardcodeado |

#### Frontend - Archivos CSS - ✅ COMPLETADOS

| Archivo | Estado |
|---------|--------|
| `assets/animations.css` | ✅ **441 líneas** - Transiciones, loading, hover, alertas, highlight |
| `assets/themes.css` | ✅ **219 líneas** - Variables light/dark, entidades, alertas, scrollbar |
| `assets/design-system/utilities.css` | ✅ Incluye highlight animations (líneas 415-459) |
| Temas PrimeVue | ✅ **6 presets configurados** (Aura, Lara, Material, Nora + Grammarly, Scrivener) |

#### Exportaciones

| Formato | Estado |
|---------|--------|
| JSON | ✅ Funcional |
| Markdown | ✅ Funcional |
| PDF | 🔄 Parcial (solo estructura) |
| DOCX | 🔄 Parcial (sin estilos) |

---

### 🔹 P3 - FUTURO (Nice to have)

| Tarea | Descripción |
|-------|-------------|
| Parser PDF | Soporte para manuscritos en PDF |
| Parser EPUB | Soporte para ebooks |
| Redis state | `api-server/main.py:1374` - Para producción multi-usuario |
| Documentación API | Swagger/OpenAPI completo |
| i18n | Internacionalización (actualmente solo español) |
| Plugins | Sistema de plugins para análisis custom |

---

### UI - ✅ COMPLETADO

| Fase | Nombre | Estado |
|------|--------|--------|
| UI-1 | Design System | ✅ `components/ds/` (7 componentes) |
| UI-2 | Layout + Menú Tauri | ✅ `WorkspaceLayout` + `menu.rs` |
| UI-3 | Análisis SSE | ✅ Streaming implementado |
| UI-4 | Tabs Workspace | ✅ 6 tabs |
| UI-5 | Sidebar e Inspector | ✅ 3 panels + 4 inspectors |
| UI-6 | Command Palette | ✅ `CommandPalette.vue` |
| UI-7 | Polish + Empaquetado | ✅ Temas, WCAG, Tauri build |

**Empaquetado Tauri:**
- ✅ Iconos generados (32x32, 128x128, icns, ico)
- ✅ Menú nativo (File, Edit, View, Help)
- ✅ Sidecar Python configurado
- ⚠️ Code signing pendiente (requiere certificados)

---

## Para Otra Instancia de Claude

### Cómo empezar:
```bash
cd /Users/paubach/repos/tfm
source .venv/bin/activate
narrative-assistant verify
pytest -v  # 612 tests
```

### Archivos clave:
- `docs/PROJECT_STATUS.md` - Este archivo
- `CLAUDE.md` - Instrucciones para Claude
- `src/narrative_assistant/` - Backend Python (103 archivos)
- `frontend/src/` - Frontend Vue (53 componentes)
- `api-server/main.py` - FastAPI bridge (3300+ líneas)

### Estado de Tauri:
```
src-tauri/
├── Cargo.toml           ✅ Configurado
├── tauri.conf.json      ✅ Configurado (bundle, ventana)
├── src/main.rs          ✅ Implementado (start/stop backend, health check, menu)
├── src/menu.rs          ✅ **COMPLETADO** (2026-01-15) - Menu nativo
└── icons/               ✅ **COMPLETADO** (2026-01-15) - 32x32, 128x128, icns, ico
```

**Comandos pendientes para build:**
```bash
# Crear iconos (necesita imagen base de 1024x1024)
cargo tauri icon path/to/icon.png

# Build para macOS (Intel)
cargo tauri build --target x86_64-apple-darwin

# Build para macOS (Apple Silicon)
cargo tauri build --target aarch64-apple-darwin

# Build para Windows
cargo tauri build --target x86_64-pc-windows-msvc
```

### Última actualización:
```
2026-01-19: MVP LISTO PARA RELEASE
- ✅ Backend completo (Phases 0-9) - 103 archivos Python
- ✅ Frontend completo (Phases 10-14) - 53 componentes Vue
- ✅ API server integrado (39 endpoints)
- ✅ Tauri empaquetado (icons, menu, sidecar)
- ✅ Sistema de licencias
- ✅ Modelos bajo demanda
- ⚠️ Code signing pendiente (requiere certificados)
```

### Resumen estado actual:

| Prioridad | Items | Estado |
|-----------|-------|--------|
| **P0** | 8 items | ✅ 100% completado |
| **P1** | 7 items | ✅ 100% completado |
| **P2** | 8 items | ✅ 75% (code signing pendiente) |
| **P3** | 10 items | ⚠️ 10% (post-MVP) |

---

## Gap Analysis: Backend vs Frontend

> **Audit realizado**: 2026-01-14
> **Conclusión**: ~35% de funcionalidades backend NO tienen UI adecuada

### Features con soporte COMPLETO ✅

| Feature | Backend | Frontend |
|---------|---------|----------|
| CRUD Proyectos | 10 endpoints | ProjectsView |
| CRUD Entidades | 11 endpoints | EntitiesView, CharacterView |
| CRUD Alertas | 6 endpoints | AlertsView, AlertsTab |
| CRUD Atributos | 4 endpoints | CharacterView |
| CRUD Relaciones | 4 endpoints | CharacterView, RelationshipGraph |
| Análisis Progress | SSE streaming | AnalysisProgress |
| Exportación JSON | Backend ready | 3 vistas |
| Filtros alertas | Priorización | AlertsTab |
| Settings NLP | Configuración | SettingsView |

### Features con soporte PARCIAL ⚠️

| Feature | Backend | Frontend Gap |
|---------|---------|--------------|
| Timeline Temporal | `temporal/` completo | **UI vacía** - datos no se muestran |
| Grafo Relaciones | Detección + clustering | **Sin filtros por tipo** |
| Expectativas Comportamiento | LLM inference | **Solo lectura**, no editable |
| Merge Entidades | Similarity scores | **Sin preview de similitud** |
| Exportación | JSON/MD/PDF/DOCX | **Solo JSON funciona** |
| Navegación texto | Posiciones exactas | **No scroll a posición** |

### Features SIN soporte frontend ❌

| Feature Backend | Módulo | Impacto |
|-----------------|--------|---------|
| Correferencia Voting | `nlp/coreference_resolver.py` | Usuario no ve razón de fusión |
| Knowledge Tracking | `analysis/character_knowledge.py` | Qué sabe cada personaje invisible |
| Voice Profiles | `voice/profiles.py` | Análisis voz narrativa invisible |
| Voice Deviations | `voice/deviations.py` | Solo alertas genéricas |
| Register Analysis | `voice/register.py` | Registro lingüístico invisible |
| Speaker Attribution | `voice/speaker_attribution.py` | Atribución diálogos invisible |
| Focalization | `focalization/` | Solo alertas genéricas |
| Emotional Coherence | `analysis/emotional_coherence.py` | Invisible |
| Style Guide Export | `exporters/style_guide.py` | **Stub en frontend** |
| Interaction Patterns | `interactions/` | Invisible |
| Spelling/Grammar Highlight | `nlp/orthography/`, `nlp/grammar/` | Solo lista, no marcados en texto |
| Gazetteer Management | `nlp/ner.py` | Lista entidades no editable |
| Undo Merge | `persistence/history.py` | No se puede deshacer |

### Endpoints API no usados por frontend

| Endpoint | Descripción | Razón |
|----------|-------------|-------|
| `GET /projects/{id}/timeline` | Timeline temporal | Vista no implementada |
| `GET /relationships/asymmetry/{a}/{b}` | Asimetría relacional | UI no implementada |
| `POST /characters/{id}/analyze-behavior` | Inferir expectativas | Solo interno |
| `POST /characters/{id}/detect-violations` | Detectar violaciones | Solo interno |

---

## Instalador y Distribución 📦

### Estado: ✅ LISTO PARA RELEASE (excepto code signing)

| Componente | Estado |
|------------|--------|
| Tauri Icons | ✅ Generados (6 archivos) |
| Tauri Menu | ✅ Implementado (`menu.rs`) |
| Sidecar Python | ✅ Configurado (`build_sidecar.py`) |
| Code Signing macOS | ❌ Pendiente (requiere Apple Developer) |
| Code Signing Windows | ❌ Pendiente (requiere certificado) |
| Auto-update | ❌ Pendiente (P3) |

### Arquitectura de Instalador

```
Narrative-Assistant-Setup.exe / .dmg / .AppImage
├── Frontend (Tauri + Vue)         ~50 MB
├── Backend Sidecar (Python)       ~100 MB (sin modelos)
└── Modelos NLP                    ~2 GB
    ├── spaCy es_core_news_lg      ~500 MB
    └── sentence-transformers       ~500 MB
    └── Ollama models (opcional)    ~4 GB

TOTAL: ~2.5-6 GB según modelos
```

### Opciones de distribución

| Opción | Tamaño | Pros | Contras |
|--------|--------|------|---------|
| A) Todo incluido | ~6 GB | Offline inmediato | Descarga enorme |
| **B) Modelos a demanda** | ~150 MB + descarga | **Instalador pequeño** | Internet 1ª vez |
| C) Modelos externos | ~150 MB | Muy pequeño | Setup manual Ollama |

**Decisión**: Opción B ✅ IMPLEMENTADA (2026-01-15)

### Descarga de Modelos Bajo Demanda ✅

> **Implementado en**: `src/narrative_assistant/core/model_manager.py`

- Modelos se descargan automáticamente la primera vez que se necesitan
- Cache en `~/.narrative_assistant/models/`
- Variable de entorno `NA_MODELS_DIR` para override
- Verificación de integridad tras descarga
- Progreso de descarga con callbacks para UI

### Ollama Bajo Demanda ✅

> **Implementado en**: `src/narrative_assistant/llm/ollama_manager.py`

- Ollama se instala solo cuando usuario intenta usar funcionalidades LLM
- Detección automática de plataforma (Windows, macOS, Linux)
- Descarga de modelos individual (llama3.2, qwen2.5, mistral, gemma2)
- Estado persistido en `~/.narrative_assistant/ollama_state.json`

### Tareas de instalador (8-12h)

| Tarea | Tiempo | Archivo |
|-------|--------|---------|
| Generar iconos Tauri | 0.5h | `src-tauri/icons/` |
| Crear menu.rs nativo | 3h | `src-tauri/src/menu.rs` |
| Build sidecar PyInstaller | 2h | `api-server/build.py` |
| Integrar sidecar en Tauri | 2h | `src-tauri/binaries/` |
| Test build Windows | 2h | CI/CD |
| Test build macOS | 2h | CI/CD |

---

## Sistema de Licencias 🔐

### Estado: 🔄 EN PROGRESO

> **Documentación completa**: [docs/02-architecture/LICENSING.md](02-architecture/LICENSING.md)

### Backend: ✅ IMPLEMENTADO (2026-01-15)

```
src/narrative_assistant/licensing/
├── __init__.py          # Exports públicos
├── models.py            # License, Device, Subscription, UsageRecord
├── verification.py      # LicenseVerifier: verificación online/offline
└── fingerprint.py       # Hardware fingerprinting
```

### Modelo de Precios Aprobado

**Tiers**:
- **Freelance**: 5 manuscritos/mes, 1 dispositivo
- **Agencia**: 15 manuscritos/mes, 2 dispositivos
- **Editorial**: Ilimitado, 5+ dispositivos

**Bundles Mensuales**:

| Bundle | Freelance | Agencia | Editorial |
|--------|-----------|---------|-----------|
| Solo Core | 19€ | 49€ | 149€ |
| Profesional | 55€ | 129€ | 399€ |
| Completo | 65€ | 159€ | 499€ |

**Bundles Anuales (×10 meses = 17% dto)**:

| Bundle | Freelance | Agencia | Editorial |
|--------|-----------|---------|-----------|
| Solo Core | 190€ | 490€ | 1.490€ |
| Profesional | 550€ | 1.290€ | 3.990€ |
| Completo | 650€ | 1.590€ | 4.990€ |

### Características implementadas

- ✅ Hardware fingerprint (CPU, RAM, disco, MAC, machine ID)
- ✅ Verificación online con 14 días gracia offline
- ✅ Control de dispositivos con cooldown 48h
- ✅ Control de cuota de manuscritos (re-análisis no cuenta)
- ✅ Errores específicos: LicenseExpiredError, DeviceLimitError, QuotaExceededError

### Implementación (2026-01-15)

| Tarea | Archivo | Estado |
|-------|---------|--------|
| Endpoints API licencias | `api-server/main.py` (8 endpoints) | ✅ **COMPLETADO** |
| LicenseDialog.vue | `frontend/src/components/LicenseDialog.vue` | ✅ **COMPLETADO** |
| LicenseStore.ts | `frontend/src/stores/license.ts` | ✅ **COMPLETADO** |
| Integración Stripe webhooks | `api-server/` | ❌ Pendiente (P2) |
| Tests E2E licencias | `frontend/e2e/` | ❌ Pendiente (P2) |

**Endpoints de licencias añadidos:**
- `GET /api/license/status` - Estado actual de licencia
- `POST /api/license/activate` - Activar licencia
- `POST /api/license/verify` - Verificar licencia online
- `GET /api/license/devices` - Listar dispositivos
- `POST /api/license/devices/deactivate` - Desactivar dispositivo
- `GET /api/license/usage` - Uso del periodo actual
- `POST /api/license/record-manuscript` - Registrar uso manuscrito
- `GET /api/license/check-module/{name}` - Verificar acceso a módulo

---

## Regla: Backend + Frontend Siempre Juntos

A partir de 2026-01-14, cualquier feature nueva DEBE incluir:

1. **Backend**: Endpoint API + lógica
2. **Frontend**: UI completa para usar el endpoint
3. **Tests**: Unit + E2E para el flujo
4. **Docs**: Actualizar este archivo

### Checklist nuevas features

- [ ] Endpoint en `api-server/main.py`
- [ ] Tipos en `frontend/src/types/`
- [ ] Componente Vue para visualizar
- [ ] Store action para llamar API
- [ ] Test E2E del flujo
- [ ] PROJECT_STATUS.md actualizado

---

## Plan de Trabajo Consolidado (Post-Audit)

> **Criterio de priorización**: Funcionalidades útiles para correctores > información técnica de IA
> **Regla**: Backend + Frontend siempre juntos

---

### 🚨 P0 - CRÍTICO (Bloqueantes para release) ✅ COMPLETADO

| # | Item | Archivo/Módulo | Tiempo | Estado |
|---|------|----------------|--------|--------|
| 1 | Tauri Icons | `src-tauri/icons/` | 30min | ✅ **COMPLETADO** (2026-01-15) |
| 2 | Menú nativo Tauri | `src-tauri/src/menu.rs` | 2-3h | ✅ **COMPLETADO** (2026-01-15) |
| 3 | Sidecar Python | `scripts/build_sidecar.py` | 2-4h | ✅ **COMPLETADO** (2026-01-15) |
| 4 | Sistema licencias (backend) | `src/narrative_assistant/licensing/` | 4h | ✅ **COMPLETADO** (2026-01-15) |
| 5 | Sistema licencias (API) | `api-server/main.py` | 2h | ✅ **COMPLETADO** (2026-01-15) |
| 6 | Sistema licencias (frontend) | `LicenseDialog.vue`, `license.ts` | 4h | ✅ **COMPLETADO** (2026-01-15) |
| 7 | Modelos bajo demanda | `core/model_manager.py` | 3h | ✅ **COMPLETADO** (2026-01-15) |
| 8 | Ollama bajo demanda | `llm/ollama_manager.py` | 3h | ✅ **COMPLETADO** (2026-01-15) |

**Subtotal P0: ✅ 8/8 COMPLETADOS**

---

### 🔶 P1 - FUNCIONALIDAD CORE ✅ COMPLETADO (2026-01-19)

| # | Item | Archivo | Estado |
|---|------|---------|--------|
| 7 | Timeline temporal UI | `components/timeline/TimelineView.vue` | ✅ **COMPLETADO** |
| 8 | Filtros grafo relaciones | `RelationshipGraph.vue` + store | ✅ **COMPLETADO** |
| 9 | Preview merge con scores | `MergeEntitiesDialog.vue` | ✅ **COMPLETADO** |
| 10 | Scroll to highlight | `DocumentViewer.vue` | ✅ **COMPLETADO** - scrollIntoView + animaciones |
| 11 | Grammar/Spelling en texto | `TextHighlighter.vue` + `DocumentViewer.vue` | ✅ **COMPLETADO** |
| 12 | Exportación Style Guide | `ExportDialog.vue` + endpoint | ✅ **COMPLETADO** |
| 13 | Undo merge | `UndoMergeDialog.vue` + `MergeHistoryPanel.vue` | ✅ **COMPLETADO** |

**Subtotal P1: ✅ 7/7 COMPLETADOS**

---

### 🔷 P2 - MEJORAS UX ✅ COMPLETADO (excepto code signing)

| # | Item | Archivo | Estado |
|---|------|---------|--------|
| 14 | Edición expectativas | `BehaviorExpectations.vue` | ✅ **COMPLETADO** - CRUD completo |
| 15 | Exportación DOCX | `exporters/document_exporter.py` | ✅ **COMPLETADO** |
| 16 | Exportación PDF | `exporters/document_exporter.py` | ✅ **COMPLETADO** |
| 17 | Edge cases temporal | `temporal/inconsistencies.py` | ✅ **COMPLETADO** - 5+ casos cubiertos |
| 18 | Violaciones focalization | `focalization/violations.py` | ✅ **COMPLETADO** - 5 tipos de violación |
| 19 | Umbral voice configurable | `voice/deviations.py` | ✅ **COMPLETADO** - 4 umbrales parametrizables |
| 20 | Code signing Windows | `tauri.conf.json` | ❌ Pendiente (necesita certificado) |
| 21 | Code signing macOS | `tauri.conf.json` | ❌ Pendiente (necesita Apple Developer) |

**Subtotal P2: ✅ 6/8 completados** (code signing requiere certificados externos)

---

### 🔹 P3 - FUTURO (Nice to have)

| # | Item | Tiempo | Estado |
|---|------|--------|--------|
| 22 | Parser PDF | 4-6h | ❌ No implementado |
| 23 | Parser EPUB | 2-4h | ❌ No implementado |
| 24 | Tests E2E completos | 4h | ⚠️ Parcial - 8 specs, algunos fallando |
| 25 | Auto-update Tauri | 4h | ❌ No configurado |
| 26 | Redis state | 2-3h | ❌ No implementado (no necesario MVP) |
| 27 | Swagger/OpenAPI docs | 2-3h | ❌ No implementado |
| 28 | i18n | 4-8h | ❌ No implementado (solo español) |
| 29 | Sistema plugins | 8-16h | ❌ No implementado |
| 30 | CI/CD pipeline | 4h | ❌ No hay .github/workflows |
| 31 | Landing page | 4h | ❌ No implementado |

**Subtotal P3: 1/10 parcialmente completado**

---

### Resumen Estado Actual (2026-01-19)

| Prioridad | Items | Completados | Estado |
|-----------|-------|-------------|--------|
| **P0** | 8 | 8/8 | ✅ **100% COMPLETADO** |
| **P1** | 7 | 7/7 | ✅ **100% COMPLETADO** |
| **P2** | 8 | 6/8 | ✅ **75%** (code signing pendiente) |
| **P3** | 10 | 1/10 | ⚠️ **10%** (post-MVP) |

### Lo que queda por hacer

**Code Signing (P2)** - Requiere certificados externos:
- Windows: Certificado de firma de código (~$200-500/año)
- macOS: Apple Developer Program ($99/año)

**P3 - Post-MVP**:
- Parsers PDF/EPUB si hay demanda
- CI/CD cuando se prepare para producción
- i18n si se expande a otros mercados

### MVP LISTO PARA RELEASE

El proyecto está funcionalmente completo para un MVP:
- ✅ Backend completo (103 archivos Python)
- ✅ Frontend completo (53 componentes Vue)
- ✅ API integrada (39 endpoints)
- ✅ Tauri empaquetado (icons, menu, sidecar)
- ✅ Sistema de licencias
- ✅ Análisis NLP + LLM local
