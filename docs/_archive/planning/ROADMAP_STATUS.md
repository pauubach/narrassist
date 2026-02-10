# Estado Real del Roadmap - Enero 2026

> Documento generado automáticamente tras auditoría de código.
> **Última auditoría exhaustiva: 31 Enero 2026 (Sesión 7)**

---

## Resumen Ejecutivo

**El proyecto está prácticamente completo para la funcionalidad core de correctores.**

Todas las features del Competitive Analysis clasificadas como "Quick Wins", "Diferenciadores" y "Avanzado" están implementadas. Los 4 sprints planificados (A-D) se han completado al 100%. **0 features pendientes** — solo queda infraestructura (CI/CD, code signing, i18n, landing page).

---

## Estado de Features por Fase

### Fase 1: Quick Wins — ✅ COMPLETA

| Feature | Backend | Frontend | Endpoint | Estado |
|---------|---------|----------|----------|--------|
| **Sticky Sentences** | ✅ `nlp/style/sticky_sentences.py` | ✅ `StickySentencesTab.vue` | `/api/projects/{id}/sticky-sentences` | **COMPLETO** |
| **Echo/Repetitions** | ✅ `nlp/style/repetition_detector.py` | ✅ `EchoReportTab.vue` | `/api/projects/{id}/echo-report` | **COMPLETO** |
| **Sentence Variation** | ✅ `nlp/style/readability.py` | ✅ `SentenceVariationTab.vue` | `/api/projects/{id}/sentence-variation` | **COMPLETO** |
| **Clarity Index Español** | ✅ `nlp/style/readability.py` (Flesch-Szigriszt, INFLESZ) | ✅ Integrado en SentenceVariationTab y AgeReadabilityTab | `/api/projects/{id}/age-readability` | **COMPLETO** |
| **Pacing Analysis** | ✅ `analysis/pacing.py` | ✅ `PacingAnalysisTab.vue` | `/api/projects/{id}/pacing-analysis` | **COMPLETO** |

### Fase 2: Diferenciadores — ✅ COMPLETA

| Feature | Backend | Frontend | Endpoint | Estado |
|---------|---------|----------|----------|--------|
| **Timeline automático** | ✅ `temporal/timeline.py`, `temporal/markers.py` | ✅ `TimelineView.vue` | `/api/projects/{id}/timeline` | **COMPLETO** |
| **Character Consistency** | ✅ `analysis/attribute_consistency.py` | ✅ Alertas automáticas | Genera alertas en pipeline | **COMPLETO** |
| **POV Consistency** | ✅ `corrections/detectors/pov.py` | ✅ Detector configurable | Vía correcciones | **COMPLETO** |
| **Focalization Violations** | ✅ `focalization/violations.py` | ✅ `FocalizationTab.vue` | `/api/projects/{id}/focalization` | **COMPLETO** |
| **Dialogue Tags Detection** | ✅ `nlp/dialogue.py` (49 verbos, 6 regex) + `voice/speaker_attribution.py` (60+ verbos, 5 estrategias) | ✅ `DialogueAttributionPanel.vue` (492 líneas) | `/api/projects/{id}/chapters/{n}/dialogue-attributions` | **COMPLETO** |

### Fase 3: Avanzado — ✅ COMPLETA

| Feature | Backend | Frontend | Endpoint | Estado |
|---------|---------|----------|----------|--------|
| **Deceased Character Alert** | ✅ `analysis/vital_status.py` | ✅ `VitalStatusTab.vue` | `/api/projects/{id}/vital-status` | **COMPLETO** |
| **Character Location** | ✅ `analysis/character_location.py` | ✅ `CharacterLocationTab.vue` | `/api/projects/{id}/character-locations` | **COMPLETO** |
| **Chapter Progress Summary** | ✅ `analysis/chapter_summary.py` | ✅ `ChapterProgressTab.vue` + `ChapterInspector.vue` | `/api/projects/{id}/chapter-progress` | **COMPLETO** |
| **Scene Tagging + Cards** | ✅ `scenes/service.py` | ✅ `SceneTaggingTab.vue` (dual: list + cards) + `SceneCardsView.vue` | `/api/projects/{id}/scenes` (8 endpoints) | **COMPLETO** |
| **Knowledge Graph** | ✅ `relationships/analyzer.py` | ✅ `RelationshipGraph.vue` (vis-network) | `/api/projects/{id}/relationships` | **COMPLETO** |

### Fase 4: Diferenciadores Competitivos — ✅ COMPLETA

| Feature | Backend | Frontend | Endpoint | Estado |
|---------|---------|----------|----------|--------|
| **Sensory Report (5 sentidos)** | ✅ `nlp/style/sensory_report.py` (552 líneas, 5 sentidos) | ✅ `SensoryReportTab.vue` (en StyleTab → Estilo) | `/api/projects/{id}/sensory-report` | **COMPLETO** |
| **Story Bible/Wiki** | ✅ `analysis/story_bible.py` (365 líneas) | ✅ `StoryBibleTab.vue` (tab principal con sidebar+detail) | `/api/projects/{id}/story-bible`, `/story-bible/{id}` | **COMPLETO** |
| **Export Scrivener (.scriv)** | ✅ `exporters/scrivener_exporter.py` (498 líneas, formato Scrivener 3) | ✅ Integrado en `ExportDialog.vue` (card con opciones) | `/api/projects/{id}/export/scrivener` | **COMPLETO** |
| **Genre Benchmarking** | ✅ `pacing.py` (12 géneros) + `register.py` (12 géneros) | ✅ Integrado en PacingAnalysisTab + RegisterAnalysisTab | 4 endpoints benchmark + comparison | **COMPLETO** |
| **Tension Curve** | ✅ `pacing.py: compute_tension_curve()` (6 componentes) | ✅ Integrado en PacingAnalysisTab | `/api/projects/{id}/tension-curve` | **COMPLETO** |
| **Pacing Suggestions** | ✅ `pacing.py: _generate_pacing_suggestions()` con prioridades | ✅ Integrado | Parte de genre-comparison | **COMPLETO** |

### Módulos Transversales — ✅ COMPLETOS

| Feature | Backend | Frontend | Endpoint | Estado |
|---------|---------|----------|----------|--------|
| **Style Alerts** | ✅ 4 métodos `create_from_*` en AlertEngine (pacing, sticky, style_variation, word_echo) | ✅ Se muestran en AlertsTab | Wired en pipeline (3 de 4) | **COMPLETO** |
| **Voice Profiles** | ✅ `profiles.py` (440 líneas, 13+ métricas) + `deviations.py` (442 líneas, 7 tipos) | ✅ Integrado | `/api/projects/{id}/voice-profiles`, `/voice-deviations` | **COMPLETO** |
| **Speaker Attribution** | ✅ 5 estrategias, 60+ verbos, pipeline corregido | ✅ `DialogueAttributionPanel.vue` | `/api/projects/{id}/chapters/{n}/dialogue-attributions` | **COMPLETO** |
| **Register per-chapter** | ✅ API per-chapter endpoint + summary | ✅ Grid cards + accordion + ChapterTimeline en RegisterAnalysisTab | `/api/projects/{id}/register-analysis` (incluye `per_chapter`) | **COMPLETO** |
| **UI Categories** | N/A | ✅ StyleTab con 2 filas: categorías (Narrativa/Estilo/Consistencia) + sub-tabs filtrados | N/A | **COMPLETO** |
| **Coreference Reasoning** | ✅ Per-method reasoning en coreference_resolver.py | ✅ Collapsible "Ver razonamiento" en EntityInspector.vue | `/api/projects/{id}/entities/{id}/coreference` | **COMPLETO** |
| **Character Knowledge** | ✅ `analysis/character_knowledge.py` (rules + LLM) | ✅ `CharacterKnowledgeAnalysis.vue` + store | API endpoints | **COMPLETO** (pulido UI menor) |
| **Feature Profiles** | ✅ `feature_profile/` (models.py, service.py) | ✅ `DocumentTypeChip.vue`, `useFeatureProfile.ts` | 3 endpoints | **COMPLETO** |
| **Color-Coded Revisions** | ✅ Parcial: `corrected_document_exporter.py` (Track Changes Word) | ❌ Sin UI | Sin endpoint API | **30% — Solo export backend** |

---

## Sub-tabs en StyleTab.vue

> StyleTab usa **dos filas**: categorías arriba (Narrativa/Estilo/Consistencia) y sub-tabs debajo.
> CorrectionConfigPanel y Reglas Editoriales → `CorrectionConfigModal.vue` (modal).

### Categoría: Narrativa (9 tabs)

| ID | Label | Componente | Condicional |
|----|-------|-----------|-------------|
| `register` | Registro | RegisterAnalysisTab | Siempre visible |
| `focalization` | Focalización | FocalizationTab | Siempre visible |
| `scenes` | Escenas | SceneTaggingTab | `hasScenes && isFeatureAvailable('scenes')` |
| `pacing` | Ritmo | PacingAnalysisTab | `isFeatureAvailable('pacing')` |
| `emotions` | Emociones | EmotionalAnalysisTab | `isFeatureAvailable('emotional_analysis')` |
| `progress` | Progreso | ChapterProgressTab | `isFeatureAvailable('chapter_progress')` |
| `templates` | Plantillas | NarrativeTemplatesTab | `isFeatureAvailable('narrative_templates')` |
| `health` | Salud | NarrativeHealthTab | `isFeatureAvailable('narrative_health')` |
| `archetypes` | Arquetipos | CharacterArchetypesTab | `isFeatureAvailable('character_archetypes')` |

### Categoría: Estilo (6 tabs)

| ID | Label | Componente | Condicional |
|----|-------|-----------|-------------|
| `sticky` | Densidad | StickySentencesTab | `isFeatureAvailable('sticky_sentences')` |
| `echo` | Ecos | EchoReportTab | `isFeatureAvailable('echo_repetitions')` |
| `variation` | Variación | SentenceVariationTab | `isFeatureAvailable('sentence_variation')` |
| `readability` | Legibilidad | AgeReadabilityTab | `isFeatureAvailable('age_readability')` |
| `sensory` | Sensorial | SensoryReportTab | `isFeatureAvailable('sensory_report')` |
| `energy` | Energía | SentenceEnergyTab | `isFeatureAvailable('sentence_energy')` |

### Categoría: Consistencia (2 tabs)

| ID | Label | Componente | Condicional |
|----|-------|-----------|-------------|
| `vital` | Estado vital | VitalStatusTab | `isFeatureAvailable('vital_status')` |
| `locations` | Ubicaciones | CharacterLocationTab | `isFeatureAvailable('character_location')` |

---

## Endpoints API Completos

### Análisis de Estilo y Narrativa

| Endpoint | Descripción |
|----------|-------------|
| `/api/projects/{id}/sticky-sentences` | Oraciones pesadas |
| `/api/projects/{id}/chapters/{n}/sticky-sentences` | Sticky por capítulo |
| `/api/projects/{id}/echo-report` | Repeticiones léxicas |
| `/api/projects/{id}/chapters/{n}/echo-report` | Echo por capítulo |
| `/api/projects/{id}/sentence-variation` | Variación longitud oraciones |
| `/api/projects/{id}/pacing-analysis` | Análisis de ritmo narrativo |
| `/api/projects/{id}/pacing-analysis/genre-comparison` | Comparación con benchmarks de género |
| `/api/projects/{id}/tension-curve` | Curva de tensión narrativa |
| `/api/pacing/genre-benchmarks` | Benchmarks pacing por género |
| `/api/projects/{id}/register-analysis` | Análisis de registro (incluye per_chapter) |
| `/api/projects/{id}/chapters/{n}/register-analysis` | Registro detallado por capítulo |
| `/api/projects/{id}/register-analysis/genre-comparison` | Comparación registro vs género |
| `/api/register/genre-benchmarks` | Benchmarks registro por género |
| `/api/projects/{id}/sensory-report` | Reporte 5 sentidos |
| `/api/projects/{id}/voice-profiles` | Perfiles de voz por personaje |
| `/api/projects/{id}/voice-deviations` | Desviaciones de voz detectadas |
| `/api/projects/{id}/emotional-analysis` | Análisis emocional |
| `/api/projects/{id}/age-readability` | Legibilidad por edad |
| `/api/projects/{id}/sentence-energy` | Energía de oraciones (voz pasiva, verbos débiles) |
| `/api/projects/{id}/narrative-templates` | Plantillas narrativas (5 estructuras) |
| `/api/projects/{id}/narrative-health` | Salud narrativa (12 dimensiones) |
| `/api/projects/{id}/character-archetypes` | Arquetipos de personajes (Jung/Campbell) |

### Consistencia y Personajes

| Endpoint | Descripción |
|----------|-------------|
| `/api/projects/{id}/timeline` | Timeline temporal |
| `/api/projects/{id}/vital-status` | Estado vital de personajes |
| `/api/projects/{id}/vital-status/generate-alerts` | Generar alertas de estado vital |
| `/api/projects/{id}/character-locations` | Ubicaciones de personajes |
| `/api/projects/{id}/chapter-progress` | Progreso por capítulo |
| `/api/projects/{id}/relationships` | Relaciones entre personajes |
| `/api/projects/{id}/entities/{id}/coreference` | Correferencia con razonamiento |
| `/api/projects/{id}/chapters/{n}/dialogue-attributions` | Atribución de hablantes |
| `/api/projects/{id}/story-bible` | Story Bible completa |
| `/api/projects/{id}/story-bible/{id}` | Entry individual de Story Bible |

### Escenas y Estructura

| Endpoint | Descripción |
|----------|-------------|
| `/api/projects/{id}/scenes` | Escenas con etiquetas |
| `/api/projects/{id}/scenes/stats` | Estadísticas de escenas |
| `/api/projects/{id}/chapters/{n}/scenes` | Escenas por capítulo |
| `/api/projects/{id}/scenes/{id}/tags` | Etiquetado de escenas (PUT) |
| `/api/projects/{id}/scenes/{id}/custom-tags` | Tags personalizados (POST/DELETE) |
| `/api/projects/{id}/scenes/tag-catalog` | Catálogo de tags |
| `/api/projects/{id}/scenes/filter` | Filtro de escenas |

### Configuración y Herramientas

| Endpoint | Descripción |
|----------|-------------|
| `/api/document-types` | Catálogo de tipos de documento |
| `/api/projects/{id}/document-type` | Tipo de documento del proyecto |
| `/api/projects/{id}/feature-profile` | Perfil de features |
| `/api/projects/{id}/focalization` | Declaraciones de focalización (CRUD) |
| `/api/projects/{id}/focalization/violations` | Violaciones de focalización |
| `/api/projects/{id}/glossary` | Glosario |
| `/api/projects/{id}/style-guide` | Guía de estilo |
| `/api/projects/{id}/export/scrivener` | Exportar a Scrivener |

---

## Cobertura de Tests

### Tests Unitarios (Enero 2026)

| Módulo | Archivo de Test | Tests | Estado |
|--------|-----------------|-------|--------|
| `analysis/vital_status.py` | `tests/unit/test_vital_status.py` | 57 | ✅ Passing |
| `nlp/style/sticky_sentences.py` | `tests/unit/test_sticky_sentences.py` | 55 | ✅ Passing |
| `nlp/style/readability.py` | `tests/unit/test_readability.py` | 53 | ✅ Passing |
| `feature_profile/models.py` | `tests/unit/test_feature_profile.py` | 44 | ✅ Passing |
| `analysis/pacing.py` | `tests/unit/test_pacing.py` | 42 | ✅ Passing |
| `analysis/character_location.py` | `tests/unit/test_character_location.py` | 42 | ✅ Passing |
| `analysis/chapter_summary.py` | `tests/unit/test_chapter_summary.py` | 39 | ✅ Passing |

**Total**: 332 tests unitarios

### Tests Adversariales y Evaluación

| Archivo | Tests | Estado | Área |
|---------|-------|--------|------|
| `tests/adversarial/test_full_pipeline_e2e.py` | 37 (30 passed, 7 xfail) | ✅ v0.3.37 | **Pipeline E2E**: 3 manuscritos (ficción, no-ficción, complejo), 40+ errores plantados |
| `tests/adversarial/test_multimethod_evaluation.py` | 28 (28 passed) | ✅ v0.3.37 | **Evaluación multi-método**: extractores, fusión, NER, spelling |
| `tests/adversarial/test_attribute_adversarial.py` | 21 | ✅ | Attribute consistency |
| `tests/regression/test_ojos_verdes_bug.py` | 8 | ✅ | Bug "ojos verdes" |

**Progreso xfails E2E**: 18 xfails (v0.3.35) → 7 xfails (v0.3.36) — 11 resueltos.
Detalle: [XFAIL_RESEARCH_ROADMAP.md](XFAIL_RESEARCH_ROADMAP.md)

---

## LO QUE REALMENTE QUEDA PENDIENTE

> Las 3 features con backend+API completado (Sensory Report, Story Bible, Scrivener Export) ya tienen frontend completo desde la Sesión 4.

### Sprint A: Quick Wins (1 día)

| Feature | Tipo | Estado | Esfuerzo |
|---------|------|--------|----------|
| **Color-Coded Revisions UI** | ENHANCE | ✅ COMPLETO | Card en ExportDialog con categorías, confianza, track changes |
| **Percentiles por Género** | ENHANCE | ✅ COMPLETO | Backend percentiles + UI gauges en PacingAnalysisTab |
| **Sensory Report Suggestions** | ENHANCE | ✅ COMPLETO | Backend sugerencias + UI card en SensoryReportTab |

### Sprint B: Sentence Energy (1-2 días)

| Feature | Tipo | Estado | Esfuerzo |
|---------|------|--------|----------|
| **Sentence Energy** (voz pasiva, verbos débiles, energía) | BUILD | ✅ COMPLETO | Backend + API + Tab |

### Sprint C: Estructura Narrativa (3-4 días)

| Feature | Tipo | Estado | Esfuerzo |
|---------|------|--------|----------|
| **Plantillas estructuras narrativas** (Hero's Journey, Three-Act, Save the Cat, Kishotenketsu, Freytag) | BUILD | ✅ COMPLETO | Backend + API + Tab |
| **Narrative Health Check** (12 dimensiones: protagonista, conflicto, clímax, resolución, arco emocional, etc.) | BUILD | ✅ COMPLETO | Backend + API + Tab |

### Sprint D: Arquetipos (2 días)

| Feature | Tipo | Estado | Esfuerzo |
|---------|------|--------|----------|
| **Character Archetype Detector** (Jung/Campbell) | BUILD | ✅ COMPLETO | Backend + API + Tab |

### Ideas Futuras (v2.0+ — Para escritores, fuera de scope actual)

> Decisión del debate multi-experto (Sesión 5): estas features implican *generación* de texto, no *diagnóstico*. Un corrector propone y señala, pero no genera. Se documentan aquí como ideas a evaluar cuando el producto amplíe su público objetivo a escritores.

| Feature | Por qué se aplaza | Podría reenfocarse como... |
|---------|-------------------|---------------------------|
| **Continue Writing (LLM)** | Corrector no genera texto por el autor | "Sugerir dirección narrativa" — señalar posibles continuaciones sin escribirlas |
| **Change POV (1a↔3a)** | Transformación NLP compleja, no corrección | "Detector de inconsistencia de POV" — ya implementado como corrección |
| **Development Stages Workflow** | Gestión de proceso, no análisis | "Checklist de fases editoriales" — guía de proceso del corrector |
| **Brainstorm Infinito** | Ideación creativa, feature de escritor | "Sugerir alternativas" — ante un problema detectado, proponer direcciones |

### Sprints de Calidad Post-Auditoría (Sesión 5)

> Auditoría completa con 4 auditores + 3 paneles de 9 expertos.
> Detalle completo: [AUDIT_DECISIONS_AND_ROADMAP.md](AUDIT_DECISIONS_AND_ROADMAP.md)

| Sprint | Objetivo | Items | Días |
|--------|----------|-------|------|
| **E: Hotfix Crítico** | Crashes + XSS | 5 | <1 |
| **F: Calidad Frontend** | Error handling, apiUrl, watch | 6 | 1-2 |
| **G: Lingüística Española** | Pasiva refleja, estar, haber, nominalizaciones | 8 | 2-3 |
| **H: Calibración Narrativa** | Tono diagnóstico, templates, arquetipos | 10 | 2-3 |
| **I: Tests + Calibración Fina** | Cobertura esencial + umbrales | 15 | 3-4 |

### Infraestructura

| Tarea | Prioridad | Esfuerzo | Bloqueante |
|-------|-----------|----------|------------|
| **Code signing Windows** | Alta | $300/año + 2h | Para distribución |
| **Code signing macOS** | Alta | $99/año + 2h | Para distribución |
| **CI/CD Pipeline** | Media | 4-5 días | No |
| **i18n (inglés + catalán)** | Baja | 8-10 días | No |
| **Landing page** | Media | 5-6 días | No |
| **Auto-updater** | Baja | 3-4 días | No |

### Tests Pendientes

| Área | Estado | Prioridad |
|------|--------|-----------|
| Tests esenciales post-auditoría | 7 tests identificados como **ESENCIALES** | **ALTA** |
| Tests recomendados post-auditoría | 6 tests adicionales | Media |
| Fixtures faltantes | 14+ tests skipped | Media |
| Tests E2E adicionales | Solo 12 specs | Media |
| Coverage general | ~10% → objetivo 50% | Baja |

---

## Resumen de Esfuerzo Total

| Categoría | Items | Días |
|-----------|-------|------|
| ~~Frontend para features con backend listo~~ | ~~3~~ | ~~2-3~~ ✅ HECHO |
| ~~Sprint A: Quick Wins (enhance)~~ | ~~3~~ | ~~1~~ ✅ HECHO |
| ~~Sprint B: Sentence Energy~~ | ~~1~~ | ~~1-2~~ ✅ HECHO |
| ~~Sprint C: Estructura Narrativa~~ | ~~2~~ | ~~3-4~~ ✅ HECHO |
| ~~Sprint D: Arquetipos~~ | ~~1~~ | ~~2~~ ✅ HECHO |
| Sprint E-I: Calidad post-auditoría | 44 | ~10 |
| Infraestructura | 6 | 25 |
| **TOTAL PENDIENTE (features)** | **0** | **0 días** |
| **TOTAL PENDIENTE (calidad)** | **44** | **~10 días** |
| **TOTAL PENDIENTE (calidad + infra)** | **50** | **~35 días** |

---

## Historial de Auditorías

| Fecha | Hallazgo |
|-------|----------|
| 26 Ene 2026 | Documento inicial creado |
| 27 Ene 2026 | Auditoría completa de gaps, propuesta UI, orden de implementación |
| 29 Ene Sesión 1 | 12 sub-tabs (no 14), endpoints corregidos, Character Knowledge NO vacío |
| 29 Ene Sesión 2 | Dialogue Tags YA implementado, Voice Profiles 90%, Speaker Attribution 85% |
| 29 Ene Sesión 3 | **Auditoría exhaustiva**: Sprint restante (4 items) TODOS completados: Scene Cards (SceneCardsView.vue + dual view), Register per-chapter (grid cards + accordion + ChapterTimeline), UI categorías (3 categorías con 2 filas), Coreference reasoning (collapsible voting en EntityInspector). Genre Benchmarking COMPLETO (12 géneros pacing + register). Alertas de estilo WIRED en pipeline. Tension curve IMPLEMENTADA. Sensory Report, Story Bible, Scrivener Export: backend+API OK, frontend pendiente. |
| 29 Ene Sesión 4 | **Análisis 3 perspectivas** (Frontend/UX, Backend/Arquitectura, Producto/Competitivo). Consenso unánime: construir 3 UIs pendientes. Implementados: `SensoryReportTab.vue` (stats + balance + accordion + detalle paginado), `StoryBibleTab.vue` (sidebar + detail con TabView de 5 secciones), Scrivener export en `ExportDialog.vue` (card con opciones + descarga ZIP). Integrados en StyleTab, WorkspaceTabs, ProjectDetailView. **Ya no quedan features con backend sin frontend.** |
| 29 Ene Sesión 5 | **4 Sprints completados** (A-D). Sprint A: Quick Wins (revisions UI, genre percentiles, sensory suggestions). Sprint B: Sentence Energy (voz pasiva, verbos débiles, energía). Sprint C: Estructura Narrativa (5 plantillas + 12 dimensiones salud narrativa). Sprint D: Arquetipos (16 arquetipos Jung/Campbell). **0 features pendientes — solo queda infraestructura.** |
| 29 Ene Sesión 5b | **Auditoría exhaustiva post-Sprint D**: 4 auditores independientes (Frontend/UX, Backend/Arquitectura, Lógica/Concepto, Seguridad/API) + 3 paneles de 9 expertos (Lingüista, Corrector, Narratólogo, Arquitecto, Seguridad, QA, PO, UX, FE). **38 hallazgos, 0 rechazados**. 3 crashes críticos (ErrorSeverity, ArchetypeId, variable scoping), 1 XSS (v-html), 6 errores lingüísticos graves (pasiva refleja, estar+participio, haber compuesto). Planificados Sprints E-I de calidad (~10 días). Ver [AUDIT_DECISIONS_AND_ROADMAP.md](AUDIT_DECISIONS_AND_ROADMAP.md). |
| 30 Ene Sesión 6 | **Framework de evaluación multi-método** + tests adversariales E2E. 3 manuscritos de prueba (ficción/no-ficción/complejo) con 40+ errores plantados. Evaluación medida: extracción F1=0.71, fusión F1=1.00, NER F1=1.00, spelling F1=0.95. Mejoras: EmbeddingsExtractor (threshold 0.40 + sub-frases), RegexExtractor (+profesiones), tabla hipocorísticos (~50 nombres). 18 xfails categorizados en 5 grupos (A-E). |
| 31 Ene Sesión 7 | **11 xfails resueltos** (18→7). Fixes: módulo temporal activado + cross-chapter date conflicts, LanguageTool newline cleanup, EntityType enum filter fix, accent patterns (veintidós/veintitrés/veintiséis), speaker attribution entity filter, test dict access fix. Análisis experto de 7 xfails restantes + investigación sintáctica con spaCy deps para posesivos. Roadmap de I+D creado. Ver [XFAIL_RESEARCH_ROADMAP.md](XFAIL_RESEARCH_ROADMAP.md). |

---

## Referencias Documentación

| Documento | Contenido |
|-----------|-----------|
| [AUDIT_DECISIONS_AND_ROADMAP.md](AUDIT_DECISIONS_AND_ROADMAP.md) | **Decisiones de auditoría y hoja de ruta E-I** (38 hallazgos, 9 expertos) |
| [XFAIL_RESEARCH_ROADMAP.md](XFAIL_RESEARCH_ROADMAP.md) | **Roadmap I+D**: 7 xfails restantes, investigación posesivos, tests adversariales |
| [UI_REDESIGN_PROPOSAL.md](UI_REDESIGN_PROPOSAL.md) | Propuesta reorganización de tabs (implementada como categorías) |
| [COMPETITIVE_ANALYSIS_2025.md](COMPETITIVE_ANALYSIS_2025.md) | Análisis de competidores |
| [ALERTS_INTEGRATION_MAP.md](ALERTS_INTEGRATION_MAP.md) | Mapa de alertas |
| [AGE_READABILITY_IMPROVEMENTS.md](AGE_READABILITY_IMPROVEMENTS.md) | Mejoras edad lectora |
| [PROJECT_STATUS.md](../PROJECT_STATUS.md) | Estado técnico detallado |
| [DOCUMENT_TYPE_FEATURES.md](DOCUMENT_TYPE_FEATURES.md) | 13 tipos de documento con subtipos |

---

*Documento generado: Enero 2026*
*Última auditoría exhaustiva: 31 Enero 2026 (Sesión 7)*
