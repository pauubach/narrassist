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
| **Deceased Character Alert** | ✅ `analysis/vital_status.py` | ✅ API endpoints | `/api/projects/{id}/vital-status` | **COMPLETO** - Detecta muertes y reapariciones |
| **Character Location** | ⚠️ Parcial (`KnowledgeType.LOCATION`) | ❌ | N/A | **Solo tracking de conocimiento, no ubicación real** |
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

---

## Documentación de Mejoras Pendientes

| Feature | Documento | Estado |
|---------|-----------|--------|
| Age Readability (INF) | [AGE_READABILITY_IMPROVEMENTS.md](AGE_READABILITY_IMPROVEMENTS.md) | Documentado |
| Integración Alertas | [ALERTS_INTEGRATION_MAP.md](ALERTS_INTEGRATION_MAP.md) | Documentado |

### Nota sobre Rimas y Poesía

Si se implementa detección de rimas para literatura infantil (INF), se debe desarrollar simultáneamente el módulo de análisis poético (POE) para aprovechar el código compartido. Ver [AGE_READABILITY_IMPROVEMENTS.md](AGE_READABILITY_IMPROVEMENTS.md#sinergia-con-poesía-poe).

---

*Documento generado: Enero 2026*
*Última auditoría de código: 26 Enero 2026*
*Última actualización: 26 Enero 2026 - Documentadas mejoras de age_readability*
