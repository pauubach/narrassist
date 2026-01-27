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
| `/api/projects/{id}/scenes/{id}/tags` | Etiquetado predefinido de escenas |
| `/api/projects/{id}/scenes/{id}/custom-tags` | Etiquetas personalizadas de escenas |
| `/api/document-types` | Catálogo de tipos de documento |
| `/api/projects/{id}/document-type` | Tipo de documento del proyecto (GET/PUT) |
| `/api/projects/{id}/feature-profile` | Perfil de features según tipo de documento |
| `/api/projects/{id}/emotional-analysis` | Análisis emocional del proyecto |
| `/api/projects/{id}/sticky-sentences` | Detección de oraciones pesadas |
| `/api/projects/{id}/echo-report` | Detección de repeticiones/ecos |
| `/api/projects/{id}/sentence-variation` | Variación de longitud de oraciones |
| `/api/projects/{id}/pacing-analysis` | Análisis de ritmo narrativo |
| `/api/projects/{id}/age-readability` | Legibilidad por edad (infantil/juvenil) |

### Backend Implementado, Frontend Faltante o Parcial

| Endpoint | Descripción | Gap |
|----------|-------------|-----|
| `/api/projects/{id}/chapters/{n}/sticky-sentences` | Sticky por capítulo | Frontend solo usa el global |
| `/api/projects/{id}/chapters/{n}/echo-report` | Echo por capítulo | Frontend solo usa el global |
| `/api/projects/{id}/characters/{name}/emotional-profile` | Perfil emocional personaje | Usado en CharacterView pero no en workspace |
| `/api/projects/{id}/chapters/{n}/dialogue-attributions` | Atribución de hablantes | Store implementado, UI parcial |

> **Nota**: `/api/projects/{id}/emotional-analysis` ahora está integrado en `EmotionalAnalysisTab.vue` dentro de StyleTab (Tab 10)

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

3. **Análisis por Capítulo en UI**
   - Endpoints existen (`/chapters/{n}/sticky-sentences`, `/chapters/{n}/echo-report`, `/chapters/{n}/pacing-analysis`)
   - Los componentes muestran datos globales, pero el backend soporta por capítulo
   - **Acción**: Los tabs ya tienen acordeón por capítulo; mejora menor

4. ~~**Focalization UI**~~ ✅ RESUELTO
   - ~~Backend completo (`violations.py`, `declaration.py`)~~
   - Creado `FocalizationTab.vue` en workspace/StyleTab (Tab 4: Focalización)
   - Endpoints: `/api/projects/{id}/focalization` (CRUD), `/api/projects/{id}/focalization/violations`

5. **Vital Status UI**
   - Backend: ✅ `analysis/vital_status.py` con 57 tests
   - API: ✅ Endpoints `/api/projects/{id}/vital-status`, `/api/projects/{id}/vital-status/events`, `/api/projects/{id}/vital-status/post-mortem`
   - Frontend: ⚠️ Falta `VitalStatusPanel.vue` en AlertsTab
   - **Acción**: Crear panel que muestre eventos de muerte y alertas de reapariciones

6. **Character Location Tracking**
   - Backend: ⚠️ Solo `KnowledgeType.LOCATION` en character_knowledge.py
   - **Acción**: Implementar tracking real de ubicaciones con cambios de escena
   - Ver sección "Próximos Pasos" para detalles de implementación

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
| `nlp/style/readability.py` | `tests/unit/test_readability.py` | 52 | ✅ Passing |
| `analysis/pacing.py` | `tests/unit/test_pacing.py` | 42 | ✅ Passing |
| `feature_profile/models.py` | `tests/unit/test_feature_profile.py` | 44 | ✅ Passing |
| `analysis/chapter_summary.py` | `tests/unit/test_chapter_summary.py` | 39 | ✅ Passing |
| `analysis/character_location.py` | `tests/unit/test_character_location.py` | 42 | ✅ Passing |

**Total**: 331 tests unitarios para módulos de análisis de estilo, vital status, pacing, feature profiles, chapter summary y character location.

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

## Tabs Implementados en StyleTab.vue

1. **Detectores** - CorrectionConfigPanel (configuración de correctores)
2. **Registro narrativo** - RegisterAnalysisTab (análisis de registro)
3. **Reglas editoriales** - Editor de reglas personalizadas
4. **Focalización** - FocalizationTab (declaración y violaciones de focalización)
5. **Escenas** - SceneTaggingTab (condicional: `hasScenes && isFeatureAvailable('scenes')`)
6. **Oraciones pesadas** - StickySentencesTab (condicional: `isFeatureAvailable('sticky_sentences')`)
7. **Repeticiones** - EchoReportTab (condicional: `isFeatureAvailable('echo_repetitions')`)
8. **Variación** - SentenceVariationTab (condicional: `isFeatureAvailable('sentence_variation')`)
9. **Ritmo** - PacingAnalysisTab (condicional: `isFeatureAvailable('pacing')`)
10. **Emociones** - EmotionalAnalysisTab (condicional: `isFeatureAvailable('emotional_analysis')`)
11. **Edad lectora** - AgeReadabilityTab (condicional: `isFeatureAvailable('age_readability')`, solo INF)
12. **Estado vital** - VitalStatusTab (condicional: `isFeatureAvailable('vital_status')`)
13. **Ubicaciones** - CharacterLocationTab (condicional: `isFeatureAvailable('character_location')`)
14. **Avance narrativo** - ChapterProgressTab (condicional: `isFeatureAvailable('chapter_progress')`)

---

## Documentación de Mejoras Pendientes

| Feature | Documento | Estado |
|---------|-----------|--------|
| Age Readability (INF) | [AGE_READABILITY_IMPROVEMENTS.md](AGE_READABILITY_IMPROVEMENTS.md) | Documentado |
| Integración Alertas | [ALERTS_INTEGRATION_MAP.md](ALERTS_INTEGRATION_MAP.md) | Documentado |

### Nota sobre Rimas y Poesía

Si se implementa detección de rimas para literatura infantil (INF), se debe desarrollar simultáneamente el módulo de análisis poético (POE) para aprovechar el código compartido. Ver [AGE_READABILITY_IMPROVEMENTS.md](AGE_READABILITY_IMPROVEMENTS.md#sinergia-con-poesía-poe).

---

## GAPS IDENTIFICADOS Y PENDIENTES (Auditoría 27 Enero 2026)

### Problema Crítico: Arquitectura de UI

> **Ver documento completo**: [UI_REDESIGN_PROPOSAL.md](UI_REDESIGN_PROPOSAL.md)

**Diagnóstico**: StyleTab contiene 14 subtabs mezclando configuración, análisis de estilo, análisis narrativo y organización. Esto viola principios básicos de UX y dificulta la navegación.

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
| **Dialogue Tags Detector** | ProWritingAid | 🟢 Baja | Alto | 4h |
| **Sensory Report (5 sentidos)** | ProWritingAid | 🟡 Media | Alto | 2 días |
| **Benchmarking por género** | AutoCrit | 🔴 Alta | Muy alto | 5+ días |
| **Story Bible/Wiki navegable** | Sudowrite | 🟡 Media | Alto | 3 días |
| **Export Scrivener (.scriv)** | Atticus | 🟡 Media | Alto | 2 días |
| **Scene Cards View** | yWriter | 🟡 Media | Medio | 2 días |

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

| Módulo | Completitud | Gap Crítico | Esfuerzo |
|--------|-------------|-------------|----------|
| **Character Knowledge** | 60% | `_extract_knowledge_facts()` VACÍO | 5-7 días |
| **Voice Profiles** | 70% | API no devuelve todas métricas | 3-4 días |
| **Register Analysis** | 75% | Sin análisis por capítulo | 2-3 días |
| **Speaker Attribution** | 80% | Voice matching débil | 2-3 días |
| **Pacing Analysis** | 80% | Sin curva de tensión | 2-3 días |
| **Coreference Resolver** | 85% | Sin razonamiento expuesto | 1-2 días |

**Total**: 15-22 días para completar módulos existentes

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

1. **Rediseño UI (3 días)** - Reorganizar tabs según propuesta
2. **Dialogue Tags Detector (4h)** - Fácil, alto impacto
3. **Alertas desde métricas (4h)** - Sticky, Variation, Pacing

### Sprint 2: Diferenciadores (2 semanas)

4. **Character Knowledge core (5-7 días)** - CRÍTICO, desbloquea feature completa
5. **Story Bible/Wiki view (3 días)** - Diferenciador competitivo
6. **Voice Profiles completo (3-4 días)** - Extender API

### Sprint 3: Valor Añadido (2 semanas)

7. **Sensory Report (2 días)** - Análisis 5 sentidos
8. **Export Scrivener (2 días)** - Alta demanda del mercado
9. **Scene Cards View (2 días)** - Mejora UX organización

### Sprint 4: Pulido (1 semana)

10. **Register por capítulo (2-3 días)**
11. **Pacing tension curve (2-3 días)**
12. **Speaker Attribution mejorado (2-3 días)**

### Backlog (Por priorizar)

- Benchmarking por género (requiere corpus)
- Plantillas estructuras narrativas
- Story Completeness Checker
- Continue Writing / Add Sensory (LLM)
- Code signing y distribución

---

## Resumen de Esfuerzo Total

| Categoría | Items | Días |
|-----------|-------|------|
| UI Redesign | 1 | 3 |
| Features nuevas (alta prioridad) | 6 | 12 |
| Módulos incompletos | 6 | 18 |
| Infraestructura | 4 | 15 |
| **TOTAL** | | **~48 días** |

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
*Última actualización: 27 Enero 2026 - Auditoría completa de gaps, propuesta UI, orden de implementación*
