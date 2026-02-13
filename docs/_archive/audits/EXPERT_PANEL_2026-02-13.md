# Panel de Expertos — Análisis de Backlog y Plan de Trabajo

**Fecha**: 2026-02-13
**Versión actual**: v0.9.3 (commit 305a99c con fixes de auditoría)
**Contexto**: Pre-defensa TFM, todos los sprints S0-S12 completados

---

## 1. Composición del Panel

### Track Técnico
| Rol | Foco |
|-----|------|
| **QA Senior** | Testing, edge cases, cobertura, regresiones |
| **Arquitecto Python/FastAPI** | Patrones, threading, APIs, deuda técnica |
| **Lingüista Computacional** | Pipeline NLP, correferencias, español, calidad |
| **AppSec Specialist** | Path traversal, XSS, seguridad de manuscritos |

### Track Producto
| Rol | Foco |
|-----|------|
| **Corrector Editorial (15+ años)** | Utilidad real, flujo profesional |
| **Frontend Engineer (Vue/Tauri)** | Componentes, estado, rendimiento, accesibilidad |
| **Product Owner** | Priorización, ROI, valor para usuario y tribunal |
| **UX Designer** | Onboarding, usabilidad, feedback, WCAG |

---

## 2. Estado del Backlog — Auditoría Completa

### 2.1 Items Completados (19 de 29)

| ID | Título | Sprint | Notas |
|----|--------|--------|-------|
| ~~BK-05~~ | Comparativa antes/después | PP | ComparisonService, two-pass matching |
| ~~BK-06~~ | Exportar a Scrivener | SP | `scrivener_exporter.py` (~400 líneas), endpoint funcional |
| ~~BK-07~~ | Análisis multi-documento | SP | Collections, entity links, cross-book |
| ~~BK-09~~ | Merge FK migration | S9 | `move_related_data()`, 14 FK cols, 16 tests |
| ~~BK-10~~ | Dialogue attribution fixes | S9 | BK-10b/c (scene breaks + confidence decay) en cf11a00 |
| ~~BK-11~~ | Narrativa no lineal | S10 | TemporalMap, NonLinearDetector, 15 tests |
| ~~BK-13~~ | Pro-drop ambigüedad | S11 | ProDropAmbiguityScorer, SaliencyTracker, 10 tests |
| ~~BK-14~~ | Ubicaciones jerárquicas | S10 | LocationOntology, 7 niveles, gazetteer, 19 tests |
| ~~BK-15~~ | Emotional masking | S9 | `_check_emotional_masking()`, 7 familias, 6 tests |
| ~~BK-16~~ | Chekhov tracker | S11 | ChekhovTracker, abandoned threads, 8 tests |
| ~~BK-17~~ | Glossary → NER | S9 | `_inject_glossary_entities()`, CRUD API, 6 tests |
| ~~BK-18~~ | Confidence decay | S12 | `0.97^chapter_distance`, floor 0.15, 3 tests |
| ~~BK-19~~ | UI añadir/editar atributo | PP-2 | Inline CRUD en EntitiesTab |
| ~~BK-20~~ | UI corregir hablante | PP-2 | Dropdown + POST speaker_corrections |
| ~~BK-21~~ | Conflictos atributos merge | PP-2 | MergeEntitiesDialog paso 3 |
| ~~BK-22~~ | Feedback loop | PP-4 | detector_calibration, recalibración FP |
| ~~BK-23~~ | Loading patterns | PP | 23a (DsDownloadProgress), 23b (skeleton), 23c (z-index) |
| ~~BK-24~~ | Export endpoints | PP-1 | characters, report, alerts+CSV |

> **Nota**: BK-06, BK-10, BK-15, BK-17 y BK-23 estaban sin tachar en IMPROVEMENT_PLAN.md
> pero el código confirma que están completados. Hay que actualizar el documento.

### 2.2 Items Pendientes Accionables (3)

#### BK-08: Timeline en vital_status — 80% completado

| Campo | Valor |
|-------|-------|
| **Prioridad** | P1 |
| **Esfuerzo restante** | S (4-8h) |
| **Dependencias** | BK-11 (TemporalMap) ✅ DONE |
| **Valor TFM** | ALTO — demuestra razonamiento temporal sofisticado |

**Lo que hay**:
- `vital_status.py` acepta `temporal_map` opcional
- `check_post_mortem_appearances()` usa `is_character_alive_in_chapter()` con story_time
- Death events registrados en temporal_map
- 57 tests en `test_vital_status.py`

**Lo que falta**:
- Edge cases: muerte en frontera de capítulo, flashback que cruza fecha de muerte
- Desambiguación LLM para marcadores temporales ambiguos
- Tests de integración timeline↔vital_status dedicados (~4 tests)

#### BK-25: Revision Intelligence — No iniciado

| Campo | Valor |
|-------|-------|
| **Prioridad** | P2 |
| **Esfuerzo** | L (40h full, 3h MVP) |
| **Dependencias** | Schema migration (alert version history) |
| **Valor TFM** | MEDIO — impresiona si hay demo, no bloquea defensa |

**Concepto**: Clasificar alertas tras reanálisis como `resolved` / `still_present` / `new_issue` / `dismissed`.

**Consenso del panel**:
- *Corrector Editorial*: "CRÍTICO para flujo iterativo real. Sin esto, reanálisis se siente como empezar de cero."
- *Arquitecto*: "40h para implementación completa. Viable un MVP de 3h (solo conteo de alertas, sin diff visual)."
- *Product Owner*: "Excepcional para demo, pero no bloquea defensa. Programar para v1.0."

#### BK-27: Filtrado por rango de capítulos — No iniciado

| Campo | Valor |
|-------|-------|
| **Prioridad** | P2 |
| **Esfuerzo** | M (4-6h) |
| **Dependencias** | Ninguna |
| **Valor TFM** | BAJO — mejora incremental de UI |

**Concepto**: "Solo alertas de caps 6-10" para trabajo editorial paralelo. Incluir alertas cross-chapter.

**Consenso**: Quick win post-defensa. No prioritario para TFM.

### 2.3 Items Intencionalmente Diferidos (1)

#### BK-12: Cache fases de enriquecimiento

| Campo | Valor |
|-------|-------|
| **Prioridad original** | P1 |
| **Estado** | Diferido intencionalmente en S8a |
| **Razón** | Latencia aceptable para app desktop single-user |
| **Acción** | Perfilar si usuarios reportan lentitud (2h estudio) |

### 2.4 Items Bloqueados por Dependencias Externas (4)

| ID | Título | Bloqueador | Horizonte |
|----|--------|-----------|-----------|
| BK-01 | Maverick coreference | Sin soporte español | 2027+ |
| BK-02 | BookNLP multilingüe | No publicado | 2027+ |
| BK-03 | FlawedFictions benchmark | Dataset no público | Indeterminado |
| BK-04 | Fine-tune RoBERTa ficción | Requiere 100+ manuscritos etiquetados | Post-lanzamiento |

**Consenso**: Documentar como "investigación futura" en release notes. No accionable.

### 2.5 Items Post-TFM / Infraestructura (3)

| ID | Título | Esfuerzo | Depende de | Horizonte |
|----|--------|----------|------------|-----------|
| BK-26 | Colaboración real-time | XL (120h+) | Servidor, E2E encryption | v2.0+ |
| BK-28 | Historial versiones + dashboard | L (80h) | BK-25 | v1.1+ |
| BK-29 | Step-up pricing (packs) | M (40h) | Stripe integration | v1.0+ |

---

## 3. Hallazgos de Auditoría — Estado

### 3.1 Fixes Aplicados (commit 305a99c)

| ID | Fix | Estado |
|----|-----|--------|
| F-003 | `AnalysisCancelledException` | ✅ Aplicado |
| F-001 | Rutas glosario muertas en entities.py | ✅ Aplicado |
| F-018 | Sync versión en docs | ✅ Aplicado |

### 3.2 Fixes Pendientes

| ID | Fix | Esfuerzo | Prioridad |
|----|-----|----------|-----------|
| F-006 | Race condition en progress storage | 30 min | HIGH |
| F-002 | Botón análisis parcial (sin backend) | 10 min | INFO |
| F-010 | Frontend tests en CI | 2h | MEDIUM |
| F-011 | Contract tests SSE/glossary | 3h | MEDIUM |
| F-005 | Queue refactor a project_id | 45 min | LOW |
| F-009 | Guard re-análisis encolado | 30 min | LOW |
| F-007 | SSE timeout alignment | 30 min | LOW |
| F-015/16 | Hardening path validation | 1h | MEDIUM |

---

## 4. Evaluación por Experto

### 4.1 QA Senior

**Scorecard**: A-

**Fortalezas**:
- 1.699 tests activos, 1.636 @heavy excluidos (auto-marking en conftest.py excelente)
- Session fixtures para spaCy previenen recarga de ~500MB
- 92 xfails documentados (5 decoradores + 87 runtime) — limitaciones NLP conocidas

**Gaps identificados**:
- Sin test de integración para concurrencia Tier 1 (2 proyectos simultáneos)
- Faltan tests dedicados timeline↔vital_status para BK-08
- Frontend tests (10 .spec.ts) existen pero NO en CI (F-010)
- Ejecutar `pytest --runxfail tests/adversarial/` para identificar xfails ya resueltos (1h)

**Recomendación**: "Cobertura suficiente para TFM. Cerrar gap de frontend tests para v1.0."

### 4.2 Arquitecto Python/FastAPI

**Scorecard**: B+

**Fortalezas**:
- Sistema de Tiers bien diseñado (Tier 1: parsing, Tier 2: heavy, Tier 3: enrichment)
- ProgressTracker encapsulado con pesos por fase
- Result pattern + error hierarchy + singletons thread-safe
- DI limpia vía `deps.py`

**Deuda técnica**:
- `_analysis_phases.py` tiene 3.002 líneas (HTTP + business logic mezclados)
  - **Acción v1.1**: Extraer a `AnalysisOrchestrator` (3-4h)
- Thread safety parcial: writes directos a `analysis_progress_storage` sin lock (F-006)
  - **Acción inmediata**: Wrapper `update_progress()` (30 min)
- Sin migrations formales (schema hardcoded)
  - **Acción v1.0**: Considerar Alembic

**Recomendación**: "Arquitectura sólida para TFM. F-006 es el único fix urgente."

### 4.3 Lingüista Computacional

**Scorecard**: B

**Fortalezas**:
- Voting multi-método maduro (4 métodos, pesos calibrados)
- Soporte español específico: classical Spanish, pro-drop, saliency scoring
- Gazetteer injection (BK-17) compensa limitaciones de NER genérico

**Limitaciones documentadas**:
- NER basado en noticias (spaCy `es_core_news_lg`): F1 ~65% en ficción vs ~88% en noticias
- Pro-drop gender: ~70% accuracy (xfails documentados)
- Voseo: parcialmente detectado vía morfología

**Mejora alcanzable < 1 día**:
- Migrar a PlanTL RoBERTa para NER (+26% precisión en ficción, 8h)
- **Timing**: v1.0 o v1.1, no pre-defensa

**Recomendación**: "Calidad NLP suficiente para TFM. Documentar limitaciones en release notes."

### 4.4 AppSec Specialist

**Scorecard**: A-

**Sin vulnerabilidades críticas encontradas.**

**Fortalezas**:
- Manuscritos nunca salen de la máquina
- `InputSanitizer`: path traversal, chars peligrosos, Windows reserved names
- Vue 3 escaping automático (sin `v-html` / `dangerouslySetInnerHTML`)
- SQLAlchemy ORM (sin SQL injection)
- Ollama bind a localhost por defecto

**Para v1.0**:
- Documentar: "Manuscritos en `~/.narrative_assistant/`, sin cifrado at-rest"
- CORS restringir a origen exacto en producción
- Audit logging para mutaciones de datos (si multi-usuario)

**Recomendación**: "Postura de seguridad excelente para app desktop. No hay bloqueadores."

### 4.5 Corrector Editorial (15+ años)

**Scorecard**: "Herramienta impresionante para el estado del arte."

**Lo que funciona bien**:
- Detección de inconsistencias temporales (anachronisms)
- Character profiling con 6 indicadores
- Merge de entidades con resolución de conflictos
- Export a Scrivener (herramienta estándar del sector)

**Lo que falta para flujo profesional real**:
- **Revision Intelligence (BK-25)**: "Sin esto, reanálisis se siente como empezar de cero"
- **Explicación de alertas**: Falta sección "¿Por qué es una alerta?" en AlertPanel
- **Contexto temporal en VitalStatus**: Tooltip mostrando delta temporal

**Quick wins para demo**:
- Texto explicativo en alertas (2h)
- Timeline tooltip en post-mortem (1h)

### 4.6 Frontend Engineer

**Scorecard**: B+

**Fortalezas**:
- 105 componentes Vue bien estructurados
- Empty states comprehensivos (30+ DsEmptyState)
- Tutorial de 8 pasos + User Guide
- Export maduro (ExportDialog con selección modular)

**Gaps**:
- Progreso de análisis opaco (barra indeterminada en análisis largos)
- Tests frontend no en CI (10 .spec.ts existentes)
- Accesibilidad inconsistente (aria-* en 58 ficheros, pero gaps)

**Quick wins**:
- Phase breakdown en progreso de análisis (3h)
- ETA estimado durante análisis (2h)

### 4.7 Product Owner

**Scorecard**: "Ready for TFM defense at 85%. Sprint de 27-35h → 95%."

**Feature set actual**: Suficiente para demo convincente.
- 25+ tipos de análisis, voting multi-método, timeline, network, export

**Lo que impresiona a un tribunal**:
- Razonamiento temporal (BK-08 completado)
- Proceso de calidad (auditoría → verificación → fix)
- Privacidad by design (100% offline)

**Lo que NO enfatizar en defensa**:
- BK-01..04 (bloqueadores externos)
- BK-26..29 (infraestructura futura)

### 4.8 UX Designer

**Scorecard**: B

**Fortalezas**: Onboarding con tutorial, empty states, skeleton loaders
**Gaps**: Color como único indicador de estado (WCAG 1.4.1), keyboard nav incompleta

**Quick wins**:
- Badges de tier en features ("Disponible en: Profesional") — 2h
- Guía mejorada en empty state de HomeView — 1.5h
- Spot-check WCAG AA — 2-3h

---

## 5. Consenso del Panel — Votación MoSCoW

### MUST (Imprescindible para defensa)

| Item | Esfuerzo | Justificación |
|------|----------|---------------|
| Completar BK-08 (timeline↔vital_status) | 4-8h | Demuestra razonamiento temporal, 80% ya hecho |
| Fix F-006 (race condition progress) | 30 min | Bug real, thread safety |
| Verificar fixes de auditoría funcionan en demo | 1h | Smoke test pre-defensa |

### SHOULD (Mejora significativa de demo)

| Item | Esfuerzo | Justificación |
|------|----------|---------------|
| Phase breakdown en progreso de análisis | 3h | Transparencia durante análisis largo |
| Texto explicativo en alertas ("¿Por qué?") | 2h | Corrector necesita entender alertas |
| Limpiar xfails obsoletos | 1h | Higiene de tests |
| Actualizar IMPROVEMENT_PLAN.md (BK-06,10,15,17,23 → tachados) | 30 min | Documentación precisa |

### COULD (Nice-to-have si hay tiempo)

| Item | Esfuerzo | Justificación |
|------|----------|---------------|
| BK-25 MVP (conteo alertas antes/después, sin diff) | 3h | Impresiona si da tiempo |
| Spot-check WCAG AA | 2-3h | Accesibilidad básica |
| Badges de tier licensing | 2h | Modelo de negocio visible |
| Timeline tooltip en post-mortem | 1h | Polish editorial |

### WONT (No para TFM)

| Item | Razón |
|------|-------|
| BK-01..04 | Bloqueados por dependencias externas |
| BK-12 | Diferido intencionalmente, no bloquea |
| BK-25 full | 40h, programar para v1.0 |
| BK-26, 28, 29 | Infraestructura post-TFM |
| BK-27 | Quick win post-defensa, no impacta demo |
| PlanTL RoBERTa migration | 8h, mejora calidad pero riesgo de regresión pre-defensa |

---

## 6. Plan de Trabajo Recomendado

### Fase 1: Pre-Defensa (1 semana, ~20h)

**Día 1-2: Fixes críticos (3h)**
```
[ ] Fix F-006: Wrapper update_progress() thread-safe (30 min)
[ ] Fix F-002: Verificar botón análisis parcial deshabilitado (10 min)
[ ] Smoke test: Iniciar análisis → cancelar → verificar "cancelled" (15 min)
[ ] Smoke test: Análisis completo de manuscrito ~80K palabras (15 min)
[ ] Limpiar xfails obsoletos: pytest --runxfail adversarial/ (1h)
[ ] Actualizar BK-06,10,15,17,23 como ✅ DONE en IMPROVEMENT_PLAN.md (30 min)
```

**Día 2-3: Completar BK-08 (6h)**
```
[ ] Edge case: muerte en frontera de capítulo
[ ] Edge case: flashback que cruza fecha de muerte
[ ] Edge case: pluscuamperfecto ("había muerto hace años")
[ ] Tests de integración timeline↔vital_status (4 tests)
[ ] Verificar PostMortemAppearance.is_valid en escenarios no lineales
```

**Día 3-4: UX de demo (5h)**
```
[ ] Texto explicativo en AlertPanel: sección "¿Por qué?" (2h)
[ ] Phase breakdown en AnalysisProgress (3h)
```

**Día 5: Documentación y versión (4h)**
```
[ ] Limpiar docs: borrar temp files, consolidar audit docs
[ ] Version sync a 0.9.4
[ ] Tag v0.9.4
[ ] Ensayo de demo completo
```

### Fase 2: Post-Defensa v1.0 (4-6 semanas, ~80h)

| Semana | Items | Esfuerzo |
|--------|-------|----------|
| 1 | BK-25 Revision Intelligence | 40h |
| 2 | F-010 Frontend tests CI + F-011 Contract tests | 5h |
| 2 | BK-27 Filtrado por capítulos | 6h |
| 3 | PlanTL RoBERTa NER upgrade | 8h |
| 3 | F-005, F-009, F-007 (queue + SSE) | 2h |
| 4 | Accessibility audit WCAG 2.1 AA | 10h |
| 4 | Extraer AnalysisOrchestrator de _analysis_phases.py | 4h |

### Fase 3: v1.1+ (Roadmap futuro)

| Item | Esfuerzo | Trigger |
|------|----------|---------|
| BK-29: Step-up pricing | 40h | Cuando haya usuarios pagando |
| BK-28: Historial versiones | 80h | Después de BK-25 |
| BK-12: Cache enriquecimiento | 12h | Si usuarios reportan lentitud |
| BK-26: Colaboración real-time | 120h+ | Después de licensing server |
| BK-01..04: Integraciones NLP | Variable | Cuando libs estén disponibles |

---

## 7. Limpieza de Documentación

### 7.1 Borrar (archivos temporales/no-proyecto)

| Archivo | Razón |
|---------|-------|
| `_tmp_fastapi_dup.py` | Artefacto de debugging |
| `_tmp_router_src.txt` | Snippet temporal |
| `linkedin_post.md` | Marketing, no documentación del proyecto |

### 7.2 Actualizar (version drift)

| Archivo | Problema | Acción |
|---------|----------|--------|
| `docs/README.md` | Dice v0.7.17 | → 0.9.3 (o 0.9.4) |
| `docs/ROADMAP.md` | Header dice v0.7.17 | Clarificar, marcar S0-S12 como DONE |
| `docs/BUILD_AND_DEPLOY.md` | Header dice v0.3.0 | → 0.9.3 (o 0.9.4) |
| `docs/CHANGELOG.md` | Falta detalle v0.9.1-0.9.3 | Añadir entries |
| `docs/IMPROVEMENT_PLAN.md` | BK-06,10,15,17,23 sin tachar | Marcar como ✅ DONE |

### 7.3 Consolidar (documentos de auditoría)

**Mantener** (fuentes de verdad):
- `docs/AUDIT_INDEX.md` — Navegador principal
- `docs/AUDIT_TL_DR.md` — Resumen ejecutivo 1 página
- `docs/AUDIT_MEDIATION_FINAL_VERDICT.md` — Veredicto definitivo (4.500 palabras)
- `docs/MEDIATION_CONSOLIDATED_2026-02-13.md` — Resumen unificado 41 hallazgos

**Archivar** (a `docs/_archive/audits/`):
- `docs/AUDIT_FINDINGS.md` → supersedido por VERDICT
- `docs/AUDIT_FINDINGS_TABLE.md` → formato tabular del mismo contenido
- `docs/AUDIT_FULL_2026-02-12.md` → output original de Codex
- `docs/AUDIT_RESPONSE_INDEX.md` → duplica AUDIT_INDEX
- `docs/AUDIT_RESPONSE_TO_CODEX.md` → cubierto en VERDICT
- `docs/CODE_FINDINGS_2026-02-12.md` → fuente ya integrada en VERDICT
- `docs/MEDIATION_CODE_FINDINGS_2026-02-12.md` → paso intermedio

**Archivar tras release v0.9.4**:
- `docs/QUICK_FIX_PLAN_v0.9.4.md`
- `docs/IMMEDIATE_ACTION_CHECKLIST.md`
- `docs/IMPLEMENTATION_F003_AnalysisCancellation.md`
- `docs/FIX_REFERENCE_CARD.md`
- `AUDIT_EXECUTIVE_SUMMARY.md`

### 7.4 Mantener (documentación activa)

**Core**: CLAUDE.md, README.md, IMPROVEMENT_PLAN.md, PROJECT_STATUS.md, SETUP.md
**Arquitectura**: Toda `docs/02-architecture/` (13 ficheros, actuales)
**Teoría**: Toda `docs/01-theory/` (7 ficheros, fundamentos teóricos)
**API Reference**: Toda `docs/api-reference/` (8 ficheros, actuales)
**Research**: Toda `docs/research/` (9 ficheros, investigación válida)
**Otros**: COREFERENCE_RESOLUTION.md, WCAG_COLOR_AUDIT.md, OPTIMIZATION_STATUS.md

---

## 8. Métricas de Calidad — Scorecard del Panel

| Aspecto | Nota | Notas |
|---------|------|-------|
| **Arquitectura** | B+ | Sólida, refactoring de orchestration para v1.1 |
| **Calidad NLP** | B | Voting multi-método bueno, NER limitado por dominio noticias |
| **Testing** | A- | 1.699 activos, constraints de HW bien gestionados |
| **Seguridad** | A- | Excelente para desktop, manuscritos nunca salen |
| **Código** | B+ | Ficheros grandes pero manejables, thread safety parcial |
| **Frontend** | B+ | 105 componentes, empty states, UX gaps menores |
| **Documentación** | B | Comprehensiva pero con drift de versiones |
| **UX/Producto** | B | Feature set completo, polish necesario |

**Nota global**: **B+ (Thesis-Ready)**
**Con sprint pre-defensa**: **A- (Production-Ready MVP)**

---

## 9. Recomendación para Defensa TFM

### Qué destacar
1. **Pipeline NLP completo**: 25+ tipos de análisis, voting multi-método, 4 backends
2. **Razonamiento temporal**: TemporalMap, NonLinearDetector, confidence decay
3. **Privacidad by design**: 100% offline, manuscritos nunca salen de la máquina
4. **Proceso de calidad**: Auditoría sistemática → verificación → fixes (demostrable)
5. **Escalabilidad**: Sistema de tiers (Tier 1/2/3), licensing 3 niveles, export multi-formato

### Qué reconocer como limitaciones
1. Pro-drop gender: ~70% (limitación inherente del español sin contexto)
2. NER dominio noticias: F1 ~65% en ficción (mejora planificada con PlanTL RoBERTa)
3. 92 xfails documentados (NLP, no bugs)

### Narrativa de demo
> "Herramienta que detecta inconsistencias en manuscritos combinando 4 métodos NLP
> independientes con votación ponderada, razonamiento temporal no lineal, y perfilado
> de personajes. 100% offline, privacidad del manuscrito garantizada. 1.699 tests,
> auditoría de seguridad superada, listo para primeros usuarios."

---

> **Panel de expertos (13-Feb-2026)**: 8 expertos simulados (QA Senior, Arquitecto Python/FastAPI,
> Lingüista Computacional, AppSec Specialist, Corrector Editorial 15+ años, Frontend Engineer,
> Product Owner, UX Designer). Análisis completo de backlog, auditoría de documentación,
> plan de trabajo faseado. Resultado: B+ global, sprint de 20h para A-.
