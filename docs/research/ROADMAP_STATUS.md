# Estado Real del Roadmap - Enero 2026

> Documento generado automáticamente tras auditoría de código.

---

## Resumen Ejecutivo

**El proyecto está significativamente más avanzado de lo que indica el COMPETITIVE_ANALYSIS_2025.md.**

La mayoría de "Quick Wins" y "Diferenciadores" **ya están implementados en el backend**, aunque algunos carecen de UI en el frontend.

---

## Estado de Features por Fase

### Fase 1: Quick Wins

| Feature | Backend | Frontend | Endpoint | Estado |
|---------|---------|----------|----------|--------|
| **Sticky Sentences** | ✅ `nlp/style/sticky_sentences.py` | ✅ `StickySentencesTab.vue` | `/api/projects/{id}/sticky-sentences` | **COMPLETO** |
| **Echo/Repetitions** | ✅ `nlp/style/repetition_detector.py` | ✅ `EchoReportTab.vue` | `/api/projects/{id}/echo-report` | **COMPLETO** |
| **Sentence Variation** | ✅ `nlp/style/readability.py` | ✅ `SentenceVariationTab.vue` | `/api/projects/{id}/sentence-variation` | **COMPLETO** |
| **Clarity Index Español** | ✅ `nlp/style/readability.py` (Flesch-Szigriszt, INFLESZ) | ⚠️ Parcial | N/A | **Backend OK, UI integrada en Readability pero sin panel dedicado** |
| **Pacing Analysis** | ✅ `analysis/pacing.py` | ✅ `PacingAnalysisTab.vue` | `/api/projects/{id}/pacing-analysis` | **COMPLETO** |

### Fase 2: Diferenciadores

| Feature | Backend | Frontend | Endpoint | Estado |
|---------|---------|----------|----------|--------|
| **Timeline automático** | ✅ `temporal/timeline.py`, `temporal/markers.py` | ✅ `TimelineView.vue` | `/api/projects/{id}/timeline` | **COMPLETO** |
| **Character Consistency** | ✅ `analysis/attribute_consistency.py` | ⚠️ Alertas | Genera alertas | **Funciona vía alertas** |
| **POV Consistency** | ✅ `corrections/detectors/pov.py` | ⚠️ Config | Detector configurable | **Funciona vía correcciones** |
| **Focalization Violations** | ✅ `focalization/violations.py` | ✅ `FocalizationTab.vue` | `/api/projects/{id}/focalization` | **COMPLETO** |

### Fase 3: Avanzado

| Feature | Backend | Frontend | Endpoint | Estado |
|---------|---------|----------|----------|--------|
| **Deceased Character Alert** | ✅ `analysis/vital_status.py` | ✅ `VitalStatusTab.vue` | `/api/projects/{id}/vital-status` | **COMPLETO** - Detecta muertes y reapariciones con panel de visualización |
| **Character Location** | ✅ `analysis/character_location.py` | ✅ `CharacterLocationTab.vue` | `/api/projects/{id}/character-locations` | **COMPLETO** - Tracking de ubicaciones y detección de inconsistencias |
| **Chapter Progress Summary** | ✅ `analysis/chapter_summary.py` | ✅ `ChapterProgressTab.vue` + `ChapterInspector.vue` | `/api/projects/{id}/chapter-progress` | **COMPLETO** - Resumen por capítulo con eventos, personajes, arcos narrativos |
| **Scene Tagging** | ✅ `scenes/service.py` | ✅ `SceneTaggingTab.vue` | `/api/projects/{id}/scenes` | **COMPLETO** |
| **Knowledge Graph** | ✅ `relationships/analyzer.py` | ✅ `RelationshipGraph.vue` (vis-network) | `/api/projects/{id}/relationships` | **COMPLETO** - Grafo interactivo con filtros, layouts y clustering |

---

## Endpoints Disponibles vs Frontend

### Completamente Implementados (Backend + Frontend)

| Endpoint | Descripción |
|----------|-------------|
| `/api/projects/{id}/sticky-sentences` | Oraciones pesadas |
| `/api/projects/{id}/echo-report` | Repeticiones léxicas |
| `/api/projects/{id}/sentence-variation` | Variación longitud oraciones |
| `/api/projects/{id}/pacing-analysis` | Análisis de ritmo narrativo |
| `/api/projects/{id}/register-analysis` | Análisis de registro narrativo |
| `/api/projects/{id}/voice-profiles` | Perfiles de voz por personaje |
| `/api/projects/{id}/timeline` | Timeline temporal |
| `/api/projects/{id}/relationships` | Relaciones entre personajes |
| `/api/projects/{id}/glossary` | Glosario del proyecto |
| `/api/projects/{id}/style-guide` | Guía de estilo generada |
| `/api/projects/{id}/focalization` | Declaraciones de focalización (CRUD) |
| `/api/projects/{id}/focalization/violations` | Detección de violaciones de focalización |
| `/api/projects/{id}/scenes` | Escenas con etiquetas (listado y stats) |
| `/api/projects/{id}/scenes/{id}/tags` | Etiquetado predefinido de escenas (PUT) |
| `/api/projects/{id}/scenes/{id}/custom-tags` | Etiquetas personalizadas de escenas |
| `/api/document-types` | Catálogo de tipos de documento |
| `/api/projects/{id}/document-type` | Tipo de documento del proyecto (GET/PUT) |
| `/api/projects/{id}/feature-profile` | Perfil de features según tipo de documento |
| `/api/projects/{id}/emotional-analysis` | Análisis emocional del proyecto |
| `/api/projects/{id}/age-readability` | Legibilidad por edad (infantil/juvenil) |
| `/api/projects/{id}/vital-status` | Estado vital de personajes |
| `/api/projects/{id}/vital-status/generate-alerts` | Generar alertas de estado vital (POST) |
| `/api/projects/{id}/character-locations` | Ubicaciones de personajes |
| `/api/projects/{id}/chapter-progress` | Progreso por capítulo |

### Backend Implementado, Frontend Faltante o Parcial

| Endpoint | Descripción | Gap |
|----------|-------------|-----|
| `/api/projects/{id}/chapters/{n}/sticky-sentences` | Sticky por capítulo | Frontend solo usa el global |
| `/api/projects/{id}/chapters/{n}/echo-report` | Echo por capítulo | Frontend solo usa el global |
| `/api/projects/{id}/characters/{name}/emotional-profile` | Perfil emocional personaje | Usado en CharacterView pero no en workspace |
| `/api/projects/{id}/chapters/{n}/dialogue-attributions` | Atribución de hablantes | Store implementado, UI parcial |

> **Nota**: `/api/projects/{id}/emotional-analysis` integrado en `EmotionalAnalysisTab.vue` dentro de StyleTab

---

## Módulos Backend Implementados

### NLP / Style (`src/narrative_assistant/nlp/style/`)

```
✅ sticky_sentences.py    - StickySentenceDetector, StickyReport
✅ repetition_detector.py - RepetitionDetector, RepetitionReport
✅ readability.py         - ReadabilityAnalyzer (Flesch-Szigriszt, INFLESZ)
✅ coherence_detector.py  - Detección de coherencia
✅ filler_detector.py     - Detección de muletillas
```

### Analysis (`src/narrative_assistant/analysis/`)

```
✅ attribute_consistency.py - AttributeConsistencyChecker
✅ pacing.py               - Análisis de ritmo/pacing
✅ character_knowledge.py  - Tracking de conocimiento de personajes
✅ emotional_coherence.py  - Coherencia emocional
```

### Temporal (`src/narrative_assistant/temporal/`)

```
✅ timeline.py      - TimelineBuilder, TimelineEvent
✅ markers.py       - TemporalMarker, extracción de marcadores
✅ inconsistencies.py - Detección de inconsistencias temporales
```

### Focalization (`src/narrative_assistant/focalization/`)

```
✅ declaration.py   - FocalizationDeclaration, SQLiteFocalizationRepository
✅ violations.py    - FocalizationViolationDetector
```

### Corrections (`src/narrative_assistant/corrections/detectors/`)

```
✅ pov.py           - POVDetector (cambios de punto de vista)
✅ repetition.py    - Detector de repeticiones (integrado con corrections)
✅ clarity.py       - Detector de claridad
✅ orthographic_variants.py - Variantes ortográficas
✅ field_terminology.py - Terminología de campo
```

---

## Gaps Prioritarios a Resolver

### Prioridad Alta (UX básica faltante)

1. ~~**Emotional Analysis UI en Workspace**~~ ✅ RESUELTO
   - ~~`EmotionalAnalysis.vue` existe pero solo se usa desde CharacterSheet~~
   - Ahora integrado `EmotionalAnalysisTab.vue` en workspace/StyleTab (Tab 10: Emociones)
   - Usa endpoint `/api/projects/{id}/emotional-analysis`
   - Condicional según tipo de documento via `useFeatureProfile`

2. ~~**Readability/Clarity Metrics UI**~~ ✅ RESUELTO
   - ~~Backend tiene `readability.py` con Flesch-Szigriszt español~~
   - Ya integrado en SentenceVariationTab con estadísticas globales

### Prioridad Media (Mejoras)

3. **Análisis por Capítulo en UI** ⚠️ PARCIALMENTE RESUELTO (Auditoría 29 Ene)
   - Endpoints existen (`/chapters/{n}/sticky-sentences`, `/chapters/{n}/echo-report`)
   - **Hallazgo**: Todos los tabs ya muestran datos organizados por capítulo en Accordion panels (client-side)
   - `AlertsTab` tiene dropdown explícito de filtro por capítulo
   - `PacingAnalysisTab` permite click en capítulo para seleccionar
   - `RegisterAnalysisTab` tiene ChapterTimeline interactivo
   - **Gap real**: No hay filtrado API-level (se descarga todo y se filtra en frontend) → decisión de diseño, no bug
   - **Acción**: Mejora menor de UX (añadir dropdown de capítulo a Sticky/Echo/Variation)

4. ~~**Focalization UI**~~ ✅ RESUELTO
   - ~~Backend completo (`violations.py`, `declaration.py`)~~
   - Creado `FocalizationTab.vue` en workspace/StyleTab (Tab 4: Focalización)
   - Endpoints: `/api/projects/{id}/focalization` (CRUD), `/api/projects/{id}/focalization/violations`

5. ~~**Vital Status UI**~~ ✅ RESUELTO
   - Backend: ✅ `analysis/vital_status.py` con 57 tests
   - API: ✅ Endpoints `/api/projects/{id}/vital-status` (GET), `/api/projects/{id}/vital-status/generate-alerts` (POST)
   - Frontend: ✅ `VitalStatusTab.vue` en StyleTab (sub-tab "Estado vital")
   - ~~NOTA: Los endpoints `/vital-status/events` y `/vital-status/post-mortem` documentados anteriormente NO existen~~

6. ~~**Character Location Tracking**~~ ✅ RESUELTO
   - Backend: ✅ `analysis/character_location.py` con CharacterLocationAnalyzer (42 tests)
   - API: ✅ `/api/projects/{id}/character-locations`
   - Frontend: ✅ `CharacterLocationTab.vue` en StyleTab (sub-tab "Ubicaciones")

### Prioridad Baja (Nice to have)

5. ~~**Scene Tagging**~~ ✅ RESUELTO
   - ~~No implementado backend ni frontend~~
   - Creado modelo de datos: tablas `scenes`, `scene_tags`, `scene_custom_tags`, `project_custom_tag_catalog`
   - Creado módulo `src/narrative_assistant/scenes/` con service y repository
   - Creado `SceneTaggingTab.vue` en workspace/StyleTab (Tab 5: Escenas, condicional)
   - Endpoints: `/api/projects/{id}/scenes` (CRUD + filtros)

6. ~~**Knowledge Graph Visual**~~ ✅ RESUELTO
   - Implementado en `RelationshipGraph.vue` usando vis-network
   - Incluye filtros por tipo, fuerza y valencia
   - Soporte para clustering automático
   - Múltiples layouts (force-directed, hierarchical, etc.)
   - Panel de detalle de entidad seleccionada

---

## Cobertura de Tests

### Tests Unitarios Añadidos (Enero 2026)

| Módulo | Archivo de Test | Tests | Estado |
|--------|-----------------|-------|--------|
| `analysis/vital_status.py` | `tests/unit/test_vital_status.py` | 57 | ✅ Passing |
| `nlp/style/sticky_sentences.py` | `tests/unit/test_sticky_sentences.py` | 55 | ✅ Passing |
| `nlp/style/readability.py` | `tests/unit/test_readability.py` | 53 | ✅ Passing |
| `analysis/pacing.py` | `tests/unit/test_pacing.py` | 42 | ✅ Passing |
| `feature_profile/models.py` | `tests/unit/test_feature_profile.py` | 44 | ✅ Passing |
| `analysis/chapter_summary.py` | `tests/unit/test_chapter_summary.py` | 39 | ✅ Passing |
| `analysis/character_location.py` | `tests/unit/test_character_location.py` | 42 | ✅ Passing |

**Total**: 332 tests unitarios para módulos de análisis de estilo, vital status, pacing, feature profiles, chapter summary y character location.

### Áreas Cubiertas

- **VitalStatus**: Detección de muertes, apariciones post-mortem, flashbacks, referencias válidas
- **StickySentences**: Detección de glue words, cálculo de stickiness, severidad, reportes
- **Readability**: Flesch-Szigriszt, Fernández-Huerta, INFLESZ, legibilidad por edad (infantil)
- **Pacing**: Análisis de ritmo, detección de capítulos cortos/largos, balance de diálogo, bloques densos
- **FeatureProfile**: Perfiles por tipo de documento, ajustes por subtipo, validación de features
- **ChapterSummary**: Dataclasses (NarrativeEvent, CharacterPresence, ChekhovElement, CharacterArc, etc.), enums (AnalysisMode, EventType), patrones de revelación/muerte/decisión
- **CharacterLocation**: LocationEvent, LocationInconsistency, CharacterLocationAnalyzer, patrones de llegada/salida/presencia/transición

---

## Firmas de Funciones Verificadas

### StickySentenceDetector

```python
def analyze(self, text: str, threshold: float = 0.40) -> Result[StickyReport]
```

- **threshold**: 0.0-1.0 (proporción de glue words)
- **Return**: `Result[StickyReport]` con `sticky_sentences`, `total_sentences`, `avg_glue_percentage`

### RepetitionDetector

```python
def detect_lexical(self, text: str, min_distance: int = 50, min_occurrences: int = 2) -> Result[RepetitionReport]
def detect_lemma(self, text: str, min_distance: int = 50, min_occurrences: int = 2) -> Result[RepetitionReport]
def detect_semantic(self, text: str, min_distance: int = 100) -> Result[RepetitionReport]
```

- **min_distance**: Palabras de separación mínima para considerar repetición
- **min_occurrences**: Mínimo de repeticiones para reportar

### ReadabilityAnalyzer

```python
def analyze(self, text: str) -> Result[ReadabilityReport]
```

- **Return**: `ReadabilityReport` con `flesch_score`, `inflesz_level`, `avg_sentence_length`, etc.

---

## Próximos Pasos Recomendados

### Completados ✅

1. ~~**Inmediato**: Integrar `EmotionalAnalysis.vue` en workspace~~ ✅ HECHO
2. ~~**Corto plazo**: UI de focalización declarativa~~ ✅ HECHO
3. ~~**Medio plazo**: Scene tagging con modelo de datos~~ ✅ HECHO
4. ~~**Próximo**: Sistema de perfiles de features por tipo de documento~~ ✅ HECHO
   - Modelo de datos: `document_type`, `document_subtype` en tabla `projects` (schema v9)
   - Backend: `src/narrative_assistant/feature_profile/` (models.py, service.py)
   - API: `/api/document-types`, `/api/projects/{id}/document-type`, `/api/projects/{id}/feature-profile`
   - Frontend: `DocumentTypeChip.vue`, `useFeatureProfile.ts`
   - 13 tipos de documento con subtipos (ver `docs/research/DOCUMENT_TYPE_FEATURES.md`)
5. ~~**Largo plazo**: Knowledge graph visual (vis.js)~~ ✅ Ya implementado en `RelationshipGraph.vue`
6. ~~**Tests**: Cobertura de módulos de análisis~~ ✅ HECHO (164 tests)

### Completados (Enero 2026)

7. ~~**Vital Status UI**~~ ✅ HECHO
   - Creado `VitalStatusTab.vue` en StyleTab (Tab 12)
   - Muestra lista de eventos de muerte con contexto
   - Destaca alertas de apariciones post-mortem
   - Indica si son flashbacks válidos o errores

8. ~~**Character Location Tracking**~~ ✅ HECHO
   - Creado `analysis/character_location.py` con CharacterLocationAnalyzer
   - Detecta cambios de ubicación (llegadas, salidas, presencias, transiciones)
   - Modelo de datos LocationEvent, LocationInconsistency
   - Detecta inconsistencias (personaje en dos lugares en el mismo capítulo)
   - API: `/api/projects/{id}/character-locations`
   - Frontend: `CharacterLocationTab.vue` en StyleTab (Tab 13)

9. ~~**Chapter Progress Summary**~~ ✅ HECHO
   - Creado `analysis/chapter_summary.py` con tres modos (BASIC, STANDARD, DEEP)
   - Extracción de eventos clave con patrones + LLM
   - Detección de arcos narrativos y Chekhov's guns
   - API: `/api/projects/{id}/chapter-progress`
   - Frontend: `ChapterProgressTab.vue` (Tab 14) + `ChapterInspector.vue` contextual en panel derecho
   - El inspector derecho muestra automáticamente el resumen del capítulo visible durante el scroll

10. ~~**Mejoras de UX en Inspector Contextual**~~ ✅ HECHO
    - Mini-timeline de apariciones por capítulo en EntityInspector
    - Alertas relacionadas con la entidad seleccionada
    - Sección dedicada para inconsistencias de atributos
    - TextSelectionInspector para mostrar info del texto seleccionado (palabras, caracteres, entidades mencionadas)

### Completados (Tests)

11. ~~**Tests unitarios para módulos nuevos**~~ ✅ HECHO
    - `tests/unit/test_chapter_summary.py` - 39 tests para dataclasses, enums, patrones
    - `tests/unit/test_character_location.py` - 42 tests para analyzer, dataclasses, patrones

---

## Sub-tabs en StyleTab.vue (12 sub-tabs)

> **Nota**: CorrectionConfigPanel y Reglas Editoriales se movieron a `CorrectionConfigModal.vue`,
> accesible desde ProjectDetailView. Ya no son sub-tabs de StyleTab.

| # | ID | Label | Componente | Condicional |
|---|-----|-------|-----------|-------------|
| 1 | `register` | Registro | RegisterAnalysisTab | Siempre visible |
| 2 | `focalization` | Focalización | FocalizationTab | Siempre visible |
| 3 | `scenes` | Escenas | SceneTaggingTab | `hasScenes && isFeatureAvailable('scenes')` |
| 4 | `sticky` | Densidad | StickySentencesTab | `isFeatureAvailable('sticky_sentences')` |
| 5 | `echo` | Ecos | EchoReportTab | `isFeatureAvailable('echo_repetitions')` |
| 6 | `variation` | Variación | SentenceVariationTab | `isFeatureAvailable('sentence_variation')` |
| 7 | `pacing` | Ritmo | PacingAnalysisTab | `isFeatureAvailable('pacing')` |
| 8 | `emotions` | Emociones | EmotionalAnalysisTab | `isFeatureAvailable('emotional_analysis')` |
| 9 | `readability` | Legibilidad | AgeReadabilityTab | `isFeatureAvailable('age_readability')` |
| 10 | `vital` | Estado vital | VitalStatusTab | `isFeatureAvailable('vital_status')` |
| 11 | `locations` | Ubicaciones | CharacterLocationTab | `isFeatureAvailable('character_location')` |
| 12 | `progress` | Progreso | ChapterProgressTab | `isFeatureAvailable('chapter_progress')` |

### Accesibles fuera de StyleTab

| Componente | Ubicación | Acceso |
|-----------|-----------|--------|
| CorrectionConfigModal | ProjectDetailView | Modal, botón en toolbar |
| Editorial Rules | Dentro de CorrectionConfigModal | Sección `editorial_rules` |

---

## Documentación de Mejoras Pendientes

| Feature | Documento | Estado |
|---------|-----------|--------|
| Age Readability (INF) | [AGE_READABILITY_IMPROVEMENTS.md](AGE_READABILITY_IMPROVEMENTS.md) | Documentado |
| Integración Alertas | [ALERTS_INTEGRATION_MAP.md](ALERTS_INTEGRATION_MAP.md) | Documentado |

### Nota sobre Rimas y Poesía

Si se implementa detección de rimas para literatura infantil (INF), se debe desarrollar simultáneamente el módulo de análisis poético (POE) para aprovechar el código compartido. Ver [AGE_READABILITY_IMPROVEMENTS.md](AGE_READABILITY_IMPROVEMENTS.md#sinergia-con-poesía-poe).

---

## RECIENTES MEJORAS (27 Enero 2026)

### Pipeline de Análisis Integrado

**Resuelto**: Los módulos de análisis `vital_status`, `character_location` y `chapter_summary` ahora se ejecutan **automáticamente** durante el análisis de documentos (FASE 5 - Consistencia).

**Antes**: Estos análisis solo estaban disponibles como endpoints on-demand, requiriendo que el usuario los solicitara manualmente.

**Ahora**: Se ejecutan automáticamente en sub-fases:
- Sub-fase 5.1: Estado vital (muertes y reapariciones)
- Sub-fase 5.2: Ubicaciones de personajes (inconsistencias de ubicación)
- Sub-fase 5.3: Resumen por capítulo (modo básico sin LLM)

Las alertas generadas (personajes fallecidos que reaparecen, inconsistencias de ubicación) se crean automáticamente en FASE 7.

### Bug de Atributos Corregido (Actualizado 27 Enero 2026)

**Resuelto**: El bug donde "ojos verdes" se asignaba incorrectamente a Juan en lugar de María.

**Causa raíz**: Múltiples fallos en el algoritmo de extracción de atributos:
1. El sistema no diferenciaba artículos ("la cafetería") de pronombres objeto ("la vio")
2. No detectaba correctamente sujetos elípticos en español (pro-drop)
3. No penalizaba entidades dentro de cláusulas relativas
4. Capturaba palabras comunes como nombres de entidad debido a re.IGNORECASE

**Solución** (commits `c5660f8`, `4032ce6`, `5f1ea74`):
1. Separación de `SPANISH_POSSESSIVES` de `SPANISH_PRONOUNS`
2. Método `_find_most_recent_subject_candidate()` para posesivos
3. Bonus de scoring basado en distancia de oración
4. **Nuevas mejoras (27 Enero 2026)**:
   - Patrones de negación expandidos (NEGATION_INDICATORS, CONTRASTIVE_PATTERNS)
   - Filtrado de atributos temporales/condicionales
   - Detección de cláusulas relativas (`_is_inside_relative_clause`)
   - Penalización de objetos en resolución de sujeto elíptico
   - Validación de nombres de entidad expandida (excluye verbos y palabras comunes)
   - Carga de menciones corregida para usar todas las menciones de la BD

**Tests de regresión**: `tests/regression/test_ojos_verdes_bug.py` (8 tests passing)
**Tests adversariales**: `tests/adversarial/test_attribute_adversarial.py` (21 test functions)

---

## GAPS IDENTIFICADOS Y PENDIENTES (Auditoría 27 Enero 2026)

### Problema Crítico: Arquitectura de UI

> **Ver documento completo**: [UI_REDESIGN_PROPOSAL.md](UI_REDESIGN_PROPOSAL.md)

**Diagnóstico**: StyleTab contiene 12 subtabs de análisis (config/reglas se movieron a CorrectionConfigModal). Sigue siendo mucha información en un solo tab.

**Propuesta aprobada**: Reorganizar en tabs por intención del usuario:
- Consistencia (entidades, timeline, ubicaciones, estado vital)
- Análisis (sticky, repeticiones, variación, legibilidad)
- Narrativa (ritmo, emociones, focalización, registro, avance, escenas)
- Configuración (detectores, reglas)

**Esfuerzo**: ~3 días de implementación

---

### Features del Competitive Analysis NO Implementadas

#### Prioridad Alta (Diferenciadores competitivos)

| Feature | Origen | Complejidad | Impacto | Tiempo Est. |
|---------|--------|-------------|---------|-------------|
| ~~**Dialogue Tags Detector**~~ | ProWritingAid | — | — | — |
| ~~**Sensory Report (5 sentidos)**~~ | ProWritingAid | 🟡 Media | Alto | ✅ HECHO |
| **Benchmarking por género** | AutoCrit | 🔴 Alta | Muy alto | 5+ días |
| ~~**Story Bible/Wiki navegable**~~ | Sudowrite | 🟡 Media | Alto | ✅ HECHO |
| ~~**Export Scrivener (.scriv)**~~ | Atticus | 🟡 Media | Alto | ✅ HECHO |
| **Scene Cards View** | yWriter | 🟡 Media | Medio | 2 días |

> **Dialogue Tags Detector**: ✅ YA IMPLEMENTADO en `nlp/dialogue.py` (49 speech verbs, 6 regex patterns, 4 formatos de diálogo) y `voice/speaker_attribution.py` (60+ verbos conjugados, 5 estrategias de atribución: explícita, alternancia, perfil de voz, proximidad, fallback). Frontend: `DialogueAttributionPanel.vue` (492 líneas).

#### Prioridad Media

| Feature | Origen | Complejidad | Impacto | Tiempo Est. |
|---------|--------|-------------|---------|-------------|
| **Continue Writing (LLM)** | ProWritingAid | 🟡 Media | Medio | 2 días |
| **Add Sensory Detail (LLM)** | ProWritingAid | 🟡 Media | Medio | 1 día |
| **Plantillas estructuras** | Plottr | 🟢 Baja | Medio | 1 día |
| **Story Completeness Checker** | Dramatica | 🔴 Alta | Alto | 5 días |
| **Character Archetype Detector** | Dramatica | 🟡 Media | Medio | 2 días |
| **Color-Coded Revisions** | Final Draft | 🟡 Media | Medio | 2 días |

#### Prioridad Baja (Nice to have)

| Feature | Origen | Complejidad | Tiempo Est. |
|---------|--------|-------------|-------------|
| Change POV (1ª↔3ª persona) | ProWritingAid | 🔴 Alta | 3 días |
| Sentence Energy | StyleWriter | 🟡 Media | 2 días |
| Development Stages Workflow | StoryWeaver | 🟡 Media | 3 días |
| Percentiles por género | AutoCrit | 🔴 Alta | 5 días |
| Brainstorm infinito | Sudowrite | 🟡 Media | 2 días |

---

### Módulos Backend Incompletos

| Módulo | Completitud | Gap Real (Auditoría 29 Ene) | Esfuerzo |
|--------|-------------|-------------|----------|
| ~~**Character Knowledge**~~ | **90%** | ✅ RECLASIFICADO: Backend completo, API endpoints, frontend CharacterKnowledgeAnalysis.vue, store integrado. Gap: solo falta pulido UI | 1 día |
| ~~**Voice Profiles**~~ | **95%** | ✅ RECLASIFICADO: Endpoint `/voice-deviations` añadido (29 Ene). Backend + API + frontend completos | — |
| **Register Analysis** | 75% | Sin análisis por capítulo | 2-3 días |
| ~~**Speaker Attribution**~~ | **95%** | ✅ RECLASIFICADO: Pipeline `unified_analysis.py` corregido (29 Ene). Usa API correcta de SpeakerAttributor | — |
| ~~**Pacing Analysis**~~ | **95%** | ✅ Curva de tensión implementada (29 Ene): `compute_tension_curve()`, endpoint `/tension-curve`, clasificación de arco narrativo | — |
| **Coreference Resolver** | 85% | Sin razonamiento expuesto | 1-2 días |

**Total**: ~4-6 días para completar módulos restantes (reducido significativamente)

---

### Alertas Pendientes de Conectar

| Métrica actual | Posible alerta | Complejidad |
|----------------|----------------|-------------|
| Sticky Sentences | "Más del 60% de oraciones son pesadas" | 🟢 Baja |
| Sentence Variation | "Desviación estándar <3 (monótono)" | 🟢 Baja |
| Pacing Analysis | "10+ páginas sin diálogo" | 🟢 Baja |
| Age Readability | "Texto muy complejo para edad objetivo" | 🟡 Media |

---

### Infraestructura Pendiente

| Tarea | Prioridad | Esfuerzo | Bloqueante |
|-------|-----------|----------|------------|
| **Code signing Windows** | Alta | $300/año + 2h | Para distribución |
| **Code signing macOS** | Alta | $99/año + 2h | Para distribución |
| **CI/CD Pipeline** | Media | 4-5 días | No |
| **i18n (inglés + catalán)** | Baja | 8-10 días | No |
| **Landing page** | Media | 5-6 días | No |
| **Auto-updater** | Baja | 3-4 días | No |

---

### Tests Pendientes

| Área | Estado | Prioridad |
|------|--------|-----------|
| Fixtures faltantes | 14+ tests skipped | Media |
| Tests E2E adicionales | Solo 12 specs | Media |
| Coverage general | ~10% → objetivo 50% | Baja |

---

## ORDEN DE IMPLEMENTACIÓN RECOMENDADO

### Sprint 1: Quick Wins de Alto Impacto (1 semana)

1. ~~**Rediseño UI (3 días)**~~ → POSPUESTO: Evaluación multi-stakeholder recomienda "dos filas con categorías" (6h) en vez de rediseño completo. Implementar tras completar features.
2. ~~**Dialogue Tags Detector (4h)**~~ → ✅ YA IMPLEMENTADO
3. ~~**Alertas desde métricas (4h)**~~ → ✅ HECHO (29 Ene): 4 métodos `create_from_*` en AlertEngine (pacing, sticky, style_variation, word_echo)
4. ~~**Exponer Voice Deviations via API (4h)**~~ → ✅ HECHO (29 Ene): Endpoint `/voice-deviations`
5. ~~**Speaker Attribution pipeline fix (1 día)**~~ → ✅ HECHO (29 Ene): Reescrito `_attribute_dialogues()` con API correcta
6. ~~**Pacing tension curve (2-3 días)**~~ → ✅ HECHO (29 Ene): `compute_tension_curve()`, endpoint `/tension-curve`
7. ~~**Sensory Report (2 días)**~~ → ✅ HECHO (29 Ene): `sensory_report.py`, endpoint `/sensory-report`
8. ~~**Story Bible/Wiki view (3 días)**~~ → ✅ HECHO (29 Ene): `story_bible.py`, endpoints `/story-bible` y `/story-bible/{id}`
9. ~~**Export Scrivener (2 días)**~~ → ✅ HECHO (29 Ene): `scrivener_exporter.py`, endpoint `/export/scrivener`
10. ~~**Chapter filtering entities/mentions**~~ → ✅ HECHO (29 Ene): Parámetro `chapter_number` en endpoints de entidades y menciones

### Sprint Restante: Features Pendientes

11. **Scene Cards View (2 días)** - Mejora UX organización
12. **Register por capítulo (2-3 días)** - Análisis más granular
13. **UI categorías en StyleTab (6h)** - Dos filas con categorías (Narrativa/Estilo/Consistencia)
14. **Coreference reasoning expuesto (1-2 días)** - Mostrar cadena de razonamiento

### Backlog (Por priorizar)

- Benchmarking por género (requiere corpus)
- Plantillas estructuras narrativas
- Story Completeness Checker
- Continue Writing / Add Sensory (LLM)
- Character Archetype Detector
- Code signing y distribución

---

## Resumen de Esfuerzo Total (Revisado 29 Ene - Sesión 2)

| Categoría | Items | Días | Nota |
|-----------|-------|------|------|
| ~~Sprint 1 Quick Wins~~ | ~~6~~ | ~~0~~ | ✅ TODO COMPLETADO |
| ~~Sprint 2 Diferenciadores~~ | ~~3~~ | ~~0~~ | ✅ TODO COMPLETADO |
| ~~Sprint 3 Valor Añadido (parcial)~~ | ~~2~~ | ~~0~~ | ✅ Sensory + Scrivener COMPLETADOS |
| Sprint restante | 4 | 7-9 | Scene Cards, Register/cap, UI cats, Coref reasoning |
| Backlog estratégico | 6 | 18+ | Benchmarking, Plantillas, Completeness, etc. |
| Infraestructura | 4 | 15 | Code signing, CI/CD, Landing, i18n |
| **TOTAL PENDIENTE** | | **~22-27 días** | Reducido de 40 tras implementaciones |

---

## Referencias Documentación

| Documento | Contenido |
|-----------|-----------|
| [UI_REDESIGN_PROPOSAL.md](UI_REDESIGN_PROPOSAL.md) | Propuesta reorganización de tabs |
| [COMPETITIVE_ANALYSIS_2025.md](COMPETITIVE_ANALYSIS_2025.md) | Análisis de competidores |
| [ALERTS_INTEGRATION_MAP.md](ALERTS_INTEGRATION_MAP.md) | Mapa de alertas |
| [AGE_READABILITY_IMPROVEMENTS.md](AGE_READABILITY_IMPROVEMENTS.md) | Mejoras edad lectora |
| [PROJECT_STATUS.md](../PROJECT_STATUS.md) | Estado técnico detallado |

---

*Documento generado: Enero 2026*
*Última auditoría de código: 26 Enero 2026*
*Actualización: 27 Enero 2026 - Auditoría completa de gaps, propuesta UI, orden de implementación*
*Verificación: 29 Enero 2026 - Cruce contra código real: 12 sub-tabs (no 14), endpoints corregidos, test counts actualizados, Character Knowledge NO está vacío*
*Auditoría profunda: 29 Enero 2026 - Revisión de "gaps" contra funcionalidades existentes: Dialogue Tags YA implementado (nlp/dialogue.py + voice/speaker_attribution.py), Voice Profiles al 90% (no 70%), Speaker Attribution al 85% (no 80%), per-chapter UI parcialmente resuelto via Accordion. Esfuerzo total reducido de 48 a ~40 días*
