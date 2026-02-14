# AUDITORÍA TÉCNICA INTEGRAL — Narrative Assistant v0.9.5

**Fecha**: 2026-02-14
**Herramienta**: Claude Code (Claude Opus 4.6)
**Metodología**: Auditoría multiagente (4 agentes especializados + verificación manual)
**Alcance**: 236 archivos Python (~118K LOC), 208 archivos Vue/TS, 128 archivos test, 21 routers API, schema SQLite v24

---

## 1. RESUMEN EJECUTIVO

Narrative Assistant es un producto **funcionalmente completo en su flujo core** (upload → análisis → alertas → resolución → exportación), con 4 sub-análisis pendientes (interactions, emotional, sentiment, focalization). La arquitectura NLP de 6 fases con votación multi-método es sólida y diferenciadora. Con 1.231 tests pasando, 234 endpoints API, y soporte para 5 formatos de documento, el producto está a nivel de **beta pública**.

Los riesgos principales son: (1) **seguridad**: SQL injection implícita y falta de CSRF en la API local, (2) **calidad NLP**: las claims de F1 (~60-70%) no están validadas con benchmarks empíricos, (3) **testing**: 22 routers API sin tests de integración dedicados, y (4) **accesibilidad**: dark mode incumple WCAG AA en 15/19 colores de entidad. No hay bloqueantes arquitectónicos: la deuda técnica es moderada y gestionable (11 ítems). El producto es **viable comercialmente** con breakeven a 76 clientes (3.8% SAM) en 12 meses.

Remediación estimada: **3-5 semanas** (2 desarrolladores) para pasar de beta a producción.

---

## 2. MATRIZ DE RIESGOS

| Severidad | Seguridad | Arquitectura | Testing | NLP/Modelos | UX/Accesibilidad | DB | Cross-Platform | Total |
|-----------|-----------|-------------|---------|-------------|-------------------|-----|----------------|-------|
| **Crítico** | 1 | 0 | 2 | 1 | 1 | 0 | 0 | **5** |
| **Alto** | 3 | 1 | 3 | 3 | 0 | 1 | 1 | **12** |
| **Medio** | 2 | 4 | 2 | 2 | 2 | 1 | 3 | **16** |
| **Bajo** | 1 | 2 | 0 | 0 | 0 | 1 | 0 | **4** |
| **Total** | **7** | **7** | **7** | **6** | **3** | **3** | **4** | **37** |

---

## 3. HALLAZGOS PRIORIZADOS

### CRÍTICOS (5)

| ID | Dominio | Hallazgo | Evidencia | Impacto | Causa raíz | Solución | Esfuerzo | Riesgo cambio |
|----|---------|----------|-----------|---------|-------------|----------|----------|---------------|
| ~~C-01~~ | ~~Seguridad~~ | ~~SQL injection implícita en `update_metrics()`~~ | ~~chapter.py:298-302~~ | **REBAJADO A BAJO (B-05)**: allowlist explícita en chapter.py:283-293 filtra keys contra set hardcodeado. Valores parametrizados. Riesgo solo hipotético si futuro mantenedor modifica el set. | — | — | — | — |
| C-02 | Testing | 22 routers API sin tests de integración dedicados | api-server/routers/ — 234 endpoints; solo `test_api_404.py` y `test_api_analysis.py` genéricos | Regresiones en API silenciosas (tipos, campos, status codes) | Tests escritos para NLP core; layer API diferida | Crear 1 test file por router con TestClient de FastAPI (~18 archivos) | L | Bajo |
| C-03 | Testing | Frontend: 16 archivos test / 452 tests para 108+ componentes | frontend/src/{components,stores,composables,types,utils}/__tests__/ — 16 specs (corregido: no 5). Cobertura sigue baja vs número de componentes | Bugs UI no detectados en componentes sin test | Tests concentrados en stores/utils; muchos componentes UI sin cobertura | Vitest unit tests para componentes UI críticos restantes | L | Bajo |
| C-04 | NLP | Versiones de modelos NLP no pinneadas | model_manager.py — `name="es_core_news_lg"` sin version ni SHA256 | Resultados no reproducibles; CI pasa pero prod falla | Descarga "latest" de HuggingFace/spaCy | Pinear a versión exacta + verificar SHA256 hash | S | Bajo |
| C-05 | Accesibilidad | Dark mode: 15/19 entity badges incumplen WCAG AA | docs/WCAG_COLOR_AUDIT.md — contraste 1.9:1 a 3.9:1 (mínimo 4.5:1) | Usuarios con dificultad visual no distinguen tipos de entidad | Colores dark diseñados para visibilidad en fondo oscuro, pero reducen contraste con texto blanco | Usar texto oscuro (#1a1a1a) en badges filled de dark mode | S | Bajo |

### ALTOS (12)

| ID | Dominio | Hallazgo | Evidencia | Solución | Esfuerzo |
|----|---------|----------|-----------|----------|----------|
| A-01 | DB | N+1 queries en relationships router | relationships.py:83-92 — loop consulta DB por entidad | Batch query con JOIN o subquery | M |
| A-02 | Algoritmos | O(n²) chapter lookup en entities | entities.py:67-73 — búsqueda lineal por entidad | Pre-calcular mapa chapter→range, bisect para lookup | M |
| A-03 | Seguridad | Missing CSRF protection en API FastAPI | main.py:415-433 — CORS sin CSRF tokens | Añadir fastapi-csrf-protect middleware | M |
| A-04 | Seguridad | Paths de entorno no validados en Ollama manager | ollama_manager.py — descarga binarios sin validar path | Validar con `validate_file_path_safe()` + restringir a dirs hardcoded | M |
| A-05 | Seguridad | Path validation permite ataques symlink | sanitization.py:246-304 — `Path.resolve()` sigue symlinks | Detectar symlinks antes de resolve; rechazar paths con symlinks | M |
| A-06 | Testing | 3 analyzers core sin tests (Knowledge, Network, CrossBook) | CharacterKnowledgeAnalyzer (462 LOC), CharacterNetworkAnalyzer, CrossBookAnalyzer — 0 tests | Crear test files con casos representativos | S |
| A-07 | Testing | Persistence layer sub-testeada | Solo 1 archivo test para 15+ repositories | Tests de entity fusion, cascade deletes, schema migrations | M |
| A-08 | NLP | F1 de NER en ficción no validado empíricamente | Claim "F1 ~60-70%" es comentario de código, sin benchmark | Crear gold corpus anotado + benchmark comparativo spaCy vs PlanTL | M |
| A-09 | NLP | Modo offline no testeado | Claim "100% offline post-descarga" sin test que bloquee red | Tests con monkeypatch de urllib + cache populada/vacía | M |
| A-10 | NLP | LLM prompt injection sin sanitización completa | sanitization.py existe pero cobertura parcial | Extender sanitización a todos los paths que envían texto a Ollama | M |
| A-11 | Arquitectura | Mutable global state en deps.py | deps.py — 15+ variables globales con init ordenado | Migrar a FastAPI dependency injection o async context manager | L |
| A-12 | Cross-Platform | Path handling inconsistente en Ollama manager | ollama_manager.py:193-551 — strings hardcoded vs pathlib | Usar `Path()` consistently; añadir CI jobs Win/macOS | M |

### MEDIOS (16)

| ID | Dominio | Hallazgo | Solución | Esfuerzo |
|----|---------|----------|----------|----------|
| M-01 | Arquitectura | Routers monolíticos (`_analysis_phases.py`: 3.1K LOC, `entities.py`: 2.5K LOC) | Extraer helpers a submódulos | L |
| M-02 | Arquitectura | Patrones singleton inconsistentes (metaclass + decorator + manual locks) | Estandarizar en un patrón | M |
| M-03 | Arquitectura | Imports condicionales dispersos para deps NLP | Centralizar en registry/factory | M |
| M-04 | Código | Bare `except Exception` en múltiples routers | Capturar excepciones específicas | M |
| M-05 | Código | JSON en campos TEXT sin validación de schema | Añadir validación JSON schema en write | M |
| M-06 | Código | Magic numbers (umbrales 0.85, 0.65, 2.0 sin documentar) | Extraer a constantes nombradas | S |
| M-07 | DB | Sin query timeout en conexiones SQLite | Configurar `connection.execute("PRAGMA busy_timeout=5000")` | S |
| M-08 | DB | Progreso de análisis solo en RAM (perdido en restart) | Persistir en DB periódicamente | M |
| M-09 | Seguridad | Sin rate limiting en API (DoS en endpoint de análisis) | Añadir `slowapi` o `fastapi-limiter` | S |
| M-10 | Seguridad | Sin SBOM ni dependency scanning | Habilitar Dependabot + generar SBOM con `cyclonedx-bom` | S |
| M-11 | Cross-Platform | Missing `com.apple.security.network.client` en Entitlements.plist | Añadir entitlement para red (licencias, descarga modelos) | S |
| M-12 | Cross-Platform | Registry cleanup incompleto en NSIS uninstaller | Añadir `DeleteRegKey` explícitos | M |
| M-13 | Cross-Platform | Scripts bash sin equivalentes .bat/.ps1 para Windows | Crear batch equivalents para scripts críticos | M |
| M-14 | Docs | CLAUDE.md describe multi-model voting como implementado; realidad es single-model default | Actualizar documentación para reflejar estado real | S |
| M-15 | Docs | API docs incompletas; no auto-generación Swagger | Habilitar FastAPI `/docs` endpoint; documentar seguridad por endpoint | M |
| M-16 | UX | Loading states inconsistentes (52 indicadores, 3 patrones distintos) | Unificar en componente DsLoadingState | M |

### BAJOS (4)

| ID | Dominio | Hallazgo | Esfuerzo |
|----|---------|----------|----------|
| B-01 | DB | Sin slow query logging | S |
| B-02 | Código | Memory leak potencial en embeddings singleton (sin cache eviction) | S |
| B-03 | Arquitectura | 15+ repository classes sin base Repository\<T\> común | M |
| B-04 | Docs | README dice "100% Offline" pero describe descargas en primer uso | S |

---

## 4. INFORME POR DOMINIO

### 4.1 Arquitectura y Diseño

**Fortalezas**:
- Result[T] pattern usado consistentemente para error handling
- Pipeline de 6 fases bien definido con enriquecimiento de 13 subfases
- Thread-safe singletons con double-checked locking
- 21 routers organizados por dominio con clara separación
- Phased module loading para degradación graceful

**Debilidades**:
- `deps.py` con 15+ variables globales mutables (no DI)
- Routers monolíticos (hasta 3.1K LOC)
- Imports condicionales dispersos (no centralizados)
- Concurrencia manual con queues en vez de task queues (Celery/RQ)

### 4.2 Código y Mantenibilidad

**Fortalezas**:
- Solo 14 TODO/FIXME en 118K LOC (excelente disciplina)
- Ruff + mypy configurados; pre-commit hooks
- Naming conventions consistentes
- Type hints en la mayoría de funciones públicas

**Debilidades**:
- Bare `except Exception` en routers API
- Mix de `Optional[X]` y `X | None` (target es 3.11+)
- JSON en campos TEXT sin schema validation
- Enum serialization inconsistente (`.value` vs raw enum)

### 4.3 Seguridad

**Fortalezas**:
- Arquitectura offline-first elimina la mayoría de vectores de ataque remoto
- `InputSanitizer` bien implementado para path traversal
- Queries parametrizadas en la mayoría del código
- DOMPurify en frontend para XSS

**Debilidades**:
- SQL injection implícita en `update_metrics()` (C-01)
- Sin CSRF tokens en API local (A-03)
- Symlink attacks posibles en validación de paths (A-05)
- Sin rate limiting ni SBOM

### 4.4 Base de Datos

**Fortalezas**:
- Schema v24 maduro con 35+ tablas bien indexadas
- WAL mode habilitado para concurrencia
- Foreign keys con CASCADE deletes
- Fingerprinting de documentos (SHA-256 + n-gram Jaccard)

**Debilidades**:
- N+1 queries en relationships router (A-01)
- Sin query timeout en conexiones
- Progreso de análisis solo en RAM
- JSON en TEXT sin validación

### 4.5 Testing

**Fortalezas**:
- 1.231 tests pasando, ~3 min ejecución default
- Auto-marking de @heavy tests (protege RAM)
- Session-scoped spaCy fixture (evita re-cargar 500MB)
- 96 xfails legítimos documentados (limitaciones NLP reales)
- Adversarial tests bien diseñados con parametrización inteligente

**Debilidades**:
- 22 routers API sin tests de integración (C-02)
- 5 tests unitarios frontend para 108+ componentes (C-03)
- 3 analyzers core sin tests (A-06)
- Persistence layer con 1 archivo test para 15+ repos (A-07)
- CI: integration tests y frontend tests con `|| true` (no bloquean)

### 4.6 CI/CD y Pipeline

**Fortalezas**:
- CI con unit tests, lint, type-check, frontend build
- Release workflow para Windows (NSIS) y macOS (DMG)
- Version sync automatizado (7 archivos)

**Debilidades**:
- Integration tests no bloquean CI (`|| true`)
- Frontend tests no bloquean CI (`|| true`)
- Sin CI jobs para Windows/macOS (solo Ubuntu)
- Performance tests solo manual (sin schedule)
- MyPy informational (`|| true`)

### 4.7 Cross-Platform Win/Mac

**Fortalezas**:
- Tauri config con targets NSIS + DMG
- Platform detection en `main.py` (win32/darwin/linux)
- GPU auto-detection (CUDA/MPS/CPU)
- SSL fix con certifi para macOS embedded

**Debilidades**:
- Entitlements.plist sin `com.apple.security.network.client` (M-11)
- NSIS registry cleanup incompleto (M-12)
- Scripts bash sin equivalentes Windows (M-13)
- Path handling inconsistente en ollama_manager (A-12)
- Sin CI testing en Windows/macOS

### 4.8 Modelos NLP/ML

**Fortalezas**:
- Multi-method voting (4 métodos con pesos configurables)
- Fallback chains GPU→CPU con batch reducido
- Cache de modelos en `~/.narrative_assistant/models/`
- Descarga bajo demanda con retry

**Debilidades**:
- Versiones no pinneadas (C-04)
- F1 en ficción no validado empíricamente (A-08)
- Modo offline no testeado (A-09)
- Prompt injection sanitización parcial (A-10)

### 4.9 Documentación

**Fortalezas**:
- IMPROVEMENT_PLAN.md exhaustivo (sprints S0-S16)
- CHANGELOG.md al día
- WCAG audit documentado
- Viabilidad comercial analizada

**Debilidades**:
- API docs no auto-generadas (M-15)
- CLAUDE.md con info desactualizada sobre multi-model (M-14)
- Módulos grandes sin docstrings de algoritmo (5 archivos >1.5K LOC)
- Pipeline phases sin documentación formal

---

## 5. MATRIZ DE COHERENCIA CÓDIGO-DOCUMENTACIÓN

| Claim en docs | Archivo fuente | Estado real | Veredicto |
|---------------|---------------|-------------|-----------|
| "100% offline post-descarga" | CLAUDE.md, README.md | Correcto pero verificación de licencia requiere red | Parcialmente correcto |
| "Multi-model voting (llama3.2, mistral, qwen2.5)" | CLAUDE.md | Implementado pero default es single model | Misleading |
| "F1 ~60-70% en ficción" | nlp/ner.py comentario | Sin benchmark empírico | No verificable |
| "PlanTL RoBERTa mejora NER" | IMPROVEMENT_PLAN S1 | Código implementado en transformer_ner.py | Implementado |
| "Pro-drop resolution" | IMPROVEMENT_PLAN S2 | Código en coref_gender.py, pro_drop_scorer.py | Implementado, sin validación |
| "Anachronism detection" | IMPROVEMENT_PLAN Fase 6 | temporal/anachronisms.py implementado (tecnologías vs épocas); sin detección factual genérica | Parcial |
| "Character location conflicts" | IMPROVEMENT_PLAN | CharacterLocationAnalyzer existe pero no integrado en pipeline | Parcial |
| "Schema v24" | database.py:26 | `SCHEMA_VERSION = 24` verificado | Correcto |
| "12 document types" | correction_config/__init__.py | Todos definidos y con heurísticas | Correcto |
| "4 export formats" | README.md | 7 formatos implementados (DOCX, PDF, MD, JSON, CSV, Scrivener, Style Guide) | Docs desactualizados (subestiman) |

---

## 6. MATRIZ DE COMPLETITUD FUNCIONAL

| Feature | Declarado | Implementado | Testeado | Estado |
|---------|-----------|-------------|----------|--------|
| Parsing DOCX/TXT/MD/PDF/EPUB | Yes | Yes | Yes | Completo |
| NER (spaCy + PlanTL) | Yes | Yes | Sin benchmark | Funcional |
| Coreference multi-método | Yes | Yes | Parcial | Funcional |
| Pro-drop resolution | Yes | Yes | Sin validación corpus | Implementado |
| Attribute extraction | Yes | Yes | Yes | Completo |
| Attribute consistency | Yes | Yes | Yes | Completo |
| Temporal analysis (A+B+C) | Yes | Yes | Yes | Completo |
| Anachronism detection | Yes | Parcial | Yes | **Parcial** (tecnologías vs épocas; sin verificación factual genérica). Detector: temporal/anachronisms.py, endpoint: relationships.py:466, tests: test_temporal.py:532 |
| Character location conflicts | Yes | Parcial | No | Incompleto |
| Out-of-character behavior | Yes | Parcial | Parcial | Incompleto |
| Speaker attribution | Yes | Yes | Parcial | Funcional |
| Voice/register profiles | Yes | Yes | Yes | Completo |
| Emotional coherence | Yes | Yes | Parcial | Funcional |
| Relationship network | Yes | Yes | Sin test dedicado | Funcional |
| Character profiling (6 ind.) | Yes | Yes | Yes | Completo |
| Licensing & tiers | Yes | Yes | Yes | Completo |
| Track changes | Yes | Yes | Yes | Completo |
| Version tracking | Yes | Yes | Yes | Completo |
| Exports (7 formatos) | Yes | Yes | Yes | Completo |
| Collection/saga support | Yes | Yes | Sin test | Funcional |
| Quota & monetization UX | Yes | Yes | Yes | Completo |
| Stripe payments | Yes | No | No | **Bloqueado** (infra externa) |

---

## 7. REGISTRO DE DEUDA TÉCNICA

| ID | Categoría | Descripción | Impacto | Riesgo 3m | Riesgo 12m | Esfuerzo | Prioridad |
|----|-----------|-------------|---------|-----------|------------|----------|-----------|
| DT-01 | Arquitectura | deps.py mutable global state | Medio | Bajo | Medio | L | P3 |
| DT-02 | Arquitectura | Routers monolíticos (3.1K LOC) | Bajo | Bajo | Medio | L | P3 |
| DT-03 | Arquitectura | Persistence layer sin base Repository\<T\> | Bajo | Bajo | Bajo | M | P4 |
| DT-04 | Código | NotImplementedError/deprecated en prod | Bajo | Bajo | Bajo | S | P4 |
| DT-05 | Testing | 22 routers sin integration tests | Alto | Medio | Alto | L | P1 |
| DT-06 | Testing | Frontend 5/108 componentes testeados | Alto | Medio | Alto | L | P2 |
| DT-07 | NLP | Modelos sin version pinning | Medio | Medio | Alto | S | P1 |
| DT-08 | NLP | Sin benchmark empírico de calidad | Medio | Bajo | Alto | M | P2 |
| DT-09 | Docs | API docs no auto-generadas | Medio | Bajo | Medio | M | P3 |
| DT-10 | Docs | Pipeline phases sin doc formal | Bajo | Bajo | Medio | S | P3 |
| DT-11 | CI/CD | Tests no-bloquean CI (`|| true`) | Medio | Medio | Alto | S | P2 |

---

## 8. PLAN DE REMEDIACIÓN 30/60/90 DÍAS

### Días 1-30 (Sprint de estabilización)

| Semana | Acción | Hallazgos | Esfuerzo |
|--------|--------|-----------|----------|
| 1 | Fix SQL injection implícita (C-01) + WCAG dark mode (C-05) | C-01, C-05 | 2d |
| 1 | Pin model versions + SHA256 (C-04) | C-04 | 0.5d |
| 2 | CSRF middleware + rate limiting (A-03, M-09) | A-03, M-09 | 3d |
| 2 | Entitlements.plist network + symlink validation (M-11, A-05) | M-11, A-05 | 2d |
| 3 | API router integration tests (primeros 10 routers) | C-02 parcial | 5d |
| 4 | Prompt injection sanitización completa (A-10) | A-10 | 2d |
| 4 | N+1 fix + O(n²) chapter lookup (A-01, A-02) | A-01, A-02 | 2d |

### Días 31-60 (Sprint de testing + calidad)

| Semana | Acción | Hallazgos | Esfuerzo |
|--------|--------|-----------|----------|
| 5 | API router tests (12 routers restantes) | C-02 completo | 4d |
| 5 | Analyzers sin tests (Knowledge, Network, CrossBook) | A-06 | 2d |
| 6 | Frontend unit tests (30 componentes críticos) | C-03 parcial | 5d |
| 6 | Persistence layer tests | A-07 | 3d |
| 7 | NER benchmark empírico (gold corpus) | A-08 | 3d |
| 7 | Offline mode tests | A-09 | 2d |
| 8 | CI: quitar `|| true`, añadir mock integration tests | M-10, DT-11 | 2d |

### Días 61-90 (Sprint de polish + producción)

| Semana | Acción | Hallazgos | Esfuerzo |
|--------|--------|-----------|----------|
| 9 | API docs auto-generadas (Swagger) | M-15 | 2d |
| 9 | Pipeline phases documentation | DT-10 | 1d |
| 10 | deps.py refactor a DI pattern | DT-01 | 4d |
| 10 | Loading states unificados | M-16 | 2d |
| 11 | Cross-platform CI (Windows + macOS) | A-12, M-13 | 3d |
| 11 | SBOM + Dependabot | M-10 | 0.5d |
| 12 | Frontend tests (30 componentes más) | C-03 completo | 5d |

---

## 9. QUICK WINS (<1 día) Y CAMBIOS ESTRUCTURALES (>1 sprint)

### Quick Wins (impacto inmediato, <1 día cada uno)

| # | Acción | Impacto | Esfuerzo |
|---|--------|---------|----------|
| 1 | Pin model versions + SHA256 en model_manager.py | Reproducibilidad | 2h |
| 2 | Añadir `com.apple.security.network.client` a Entitlements.plist | macOS funcionalidad | 15min |
| 3 | Extraer magic numbers a constantes nombradas | Mantenibilidad | 3h |
| 4 | Habilitar Dependabot en GitHub | Supply chain security | 30min |
| 5 | Actualizar CLAUDE.md re: multi-model voting | Precisión docs | 30min |
| 6 | Configurar `PRAGMA busy_timeout=5000` en SQLite | DB reliability | 30min |
| 7 | Corregir README "100% offline" → clarificar primer uso | Honestidad docs | 30min |
| 8 | Actualizar README con 7 formatos de export (dice 4) | Docs accuracy | 15min |

### Cambios Estructurales (>1 sprint)

| # | Acción | Impacto | Esfuerzo | Sprint |
|---|--------|---------|----------|--------|
| 1 | Suite de integration tests para 22 routers | Testing confidence | 2-3 semanas | S17 |
| 2 | Frontend unit test coverage 60%+ | UI reliability | 2-3 semanas | S17-S18 |
| 3 | deps.py → FastAPI DI pattern | Testability, thread-safety | 1 semana | S18 |
| 4 | Router monolith extraction | Mantenibilidad | 2 semanas | S19 |
| 5 | NLP benchmark pipeline automatizado | Quality tracking | 1 semana | S18 |
| 6 | Cross-platform CI (Win+macOS runners) | Platform confidence | 1 semana | S18 |

---

## 10. BACKLOG DE NUEVAS IDEAS

| Rank | Idea | Impacto | Esfuerzo | Riesgo | ROI |
|------|------|---------|----------|--------|-----|
| 1 | **Smart Alert Triage** — filtro por confidence + saliency scoring | Alto | M (10h) | Bajo | 5/5 |
| 2 | **Quick Manuscript Profiling** — scan 30s → style guide template | Alto | M (12h) | Bajo | 5/5 |
| 3 | **Incremental Re-Analysis** — solo re-analizar secciones modificadas | Alto | M (12h) | Bajo | 5/5 |
| 4 | **Alert Workflow Templates** — batch actions predefinidas | Alto | M (12h) | Medio | 4/5 |
| 5 | **Keyboard Shortcuts Panel** (Alt+?) | Medio | S (4h) | Bajo | 3/5 |
| 6 | **WebSocket Streaming** — resultados live durante análisis | Medio | M (20h) | Medio | 4/5 |
| 7 | **Emotional Arc Heatmap** — visualización temporal de emociones | Medio | M (14h) | Medio | 3/5 |
| 8 | **Anachronism Deep Detector** — base de datos histórica | Medio | L (10h) | Bajo | 3/5 |
| 9 | **Pluggable Detector Framework** — plugins custom de usuario | Medio | M (18h) | Medio | 3/5 |
| 10 | **Accesibilidad visual** — daltonismo, dislexia, AAA. Dos opciones a evaluar: (a) tema/preset dedicado accesible, o (b) interruptor que adapte cualquier tema activo a modo accesible. Analizar dificultad y pros/contras de cada enfoque | Medio | M (8h) | Bajo | 4/5 |
| 11 | **Collaborative Collections** — equipos editoriales | Alto | L (30h) | Alto | 3/5 |
| 12 | **NLP Benchmark Dashboard** — F1 trends por detector | Medio | M (10h) | Bajo | 3/5 |
| 13 | **Arrow/Parquet Export** — para investigadores | Bajo | S (5h) | Bajo | 2/5 |

---

## 11. SUPUESTOS, LIMITACIONES Y "NO VERIFICABLE"

### Supuestos de la auditoría
- El código en `master` refleja el estado de producción
- Los 1.231 tests pasan consistentemente (no ejecutados durante auditoría por restricción de hardware)
- La base de datos SQLite v24 se crea correctamente en primera ejecución

### Limitaciones
- **No ejecutamos tests**: verificación estática del código, no runtime
- **No probamos cross-platform**: auditoría en Windows, macOS inferido de código
- **No verificamos Ollama integration**: requiere servidor corriendo
- **No verificamos Tauri build completo**: requiere Rust toolchain + signing keys

### No Verificable (necesita prueba concreta)

| Claim | Qué falta para verificar |
|-------|--------------------------|
| "F1 ~60-70% en ficción española" | Gold corpus anotado + benchmark script |
| "PlanTL mejora significativamente sobre spaCy" | Benchmark comparativo A/B |
| "Pro-drop resolution funciona" | Evaluación en corpus real con sujetos elididos |
| "Offline mode 100% funcional" | Test con network bloqueada + cache populada |
| "Windows installer funciona end-to-end" | Test en máquina limpia Windows |
| "macOS DMG funciona post-notarization" | Test en macOS con Gatekeeper |
| "Adaptive weights mejoran resultados" | A/B test con/sin pesos adaptativos |
| "Multi-method voting reduce false positives" | Benchmark voting vs single-method |
