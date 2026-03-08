# Auditoría Funcional, UX, Usabilidad y Arquitectura

Fecha: 2026-03-07
Repositorio: `d:\repos\tfm`
Tipo: auditoría de producto y experiencia sobre la app desktop local.

## 1. Objetivo

Esta auditoría no se centra sólo en bugs técnicos. Evalúa la app desde el punto de vista de:

- funcionalidad real de extremo a extremo
- flujos de usuario
- UX para correctores/editoriales no técnicos
- accesibilidad y consistencia visual en light/dark y presets
- arquitectura de frontend/backend reutilizable y mantenible
- duplicaciones, repeticiones y oportunidades de centralización
- documentación, testing y soporte operativo

## 2. Metodología

Se usó una combinación de:

- revisión estática de código y documentación
- conteo de patrones repetidos (`fetch`, `localStorage`, `alert/confirm/prompt`, `console.log`)
- revalidación de tests de stores, shell Tauri, backend y persistencia
- lectura dirigida de vistas clave:
  - `HomeView.vue`
  - `ProjectsView.vue`
  - `ProjectDetailView.vue`
  - `SettingsView.vue`
  - `DocumentViewer.vue`
  - `StatusBar.vue`
  - `ModelSetupDialog.vue`

## 3. Estado funcional por flujo

## 3.1 Primer arranque, instalación y preparación del sistema

### Estado

**Bueno y bastante maduro**.

Fortalezas:

- `ModelSetupDialog.vue` comunica instalación, descarga, error, falta de Python y necesidad de reinicio con lenguaje razonablemente editorial.
- `systemStore` expone progreso granular y estados explícitos (`backendStarting`, `backendStartupError`, `needsRestart`, `isLlmDownloading`).
- `main.rs` diferencia liveness de readiness y emite `starting/restarting/running/error`.
- Si el backend tarda en cargar módulos, la UI ya no aparenta “bloqueo silencioso”.

Riesgo residual:

- sigue faltando una prueba de humo empaquetada cross-platform que compruebe la experiencia completa del binario final, no sólo helpers y stores.

Veredicto:

- **Funcionalmente sólido** para usuario final.
- **Todavía no totalmente blindado** como experiencia de release empaquetada.

## 3.2 Crear proyecto -> analizar -> revisar -> reanalizar

### Estado

**Flujo central sólido**.

Fortalezas:

- create project + start analysis ya no tropieza con la carrera `idle`/`start inflight`.
- el estado de análisis distingue mejor entre arranque local, ejecución real, cancelación y finalización.
- `timeline` ya participa como fase real y se puede reintentar aisladamente.
- el reanálisis incremental ya no es sólo “por fase gruesa”: existe subgrafo de impacto por entidades/capítulos y reutilización de caches en enrichment.
- tras cancelar, el fast-path ya contempla `completed`, `cancelled` y `pending` si el documento no cambió.

Riesgo residual:

- algunas superficies secundarias todavía usan `fetch`/`alert` directos y no heredan el mismo nivel de tratamiento de errores que el store principal.

Veredicto:

- **Flujo core correcto y competitivo**.
- La deuda no está en la lógica principal, sino en el acabado desigual de algunas superficies laterales.

## 3.3 Revisión de alertas y trabajo editorial diario

### Estado

**Bueno, pero no completamente uniforme**.

Fortalezas:

- vocabulario principal de alertas ya está alineado con el modelo editorial (`Resuelta`, `Descartada`, etc.).
- hay filtros, focus mode, navegación al texto, batch actions y reanálisis conectado al estado del proyecto.
- el `StatusBar` y el workspace ya reflejan mejor el estado real del análisis y de revisión.

Hallazgos:

### UX-01. Persisten diálogos nativos del navegador/sistema en flujos de trabajo normales, aunque ya son menos que al inicio de la revisión

Evidencia representativa:

- `frontend/src/composables/useProjectFile.ts`
- `frontend/src/composables/useEntityCrud.ts`
- `frontend/src/views/CharacterView.vue`
- `frontend/src/views/CollectionsView.vue`
- `frontend/src/views/CollectionDetailView.vue`
- `frontend/src/components/collections/EntityLinkPanel.vue`
- `frontend/src/components/collections/CollectionBookList.vue`

Impacto:

- rompen consistencia visual
- empeoran accesibilidad
- degradan el tono del producto en una app de escritorio cuidada

Recomendación:

- capa única de confirmación/feedback con componentes propios y fallback nativo sólo cuando Tauri lo requiera de verdad

### UX-02. Hay mucho feedback bueno con toast, pero no está completamente centralizado

Evidencia:

- `ProjectDetailView.vue` concentra gran cantidad de `toast.add(...)`
- `SettingsView.vue` repite patrones de éxito/error/manual retry
- otras superficies usan `alert()` o errores inline distintos

Impacto:

- tono correcto en muchas rutas, pero sin un patrón único de severidad, duración y redacción
- más difícil mantener copy consistente para usuario no técnico

Recomendación:

- crear una pequeña librería de mensajes de producto por dominio:
  - análisis
  - exportación
  - configuración
  - sidecar/sistema

## 3.4 Exportación, importación y persistencia de proyecto

### Estado

**Funcionalmente bueno**, con un hueco claro de uniformidad arquitectónica.

Fortalezas:

- import/export `.nra` revalidado con tests backend y remapeo correcto
- endpoints de proyecto y settings cubiertos
- `useProjectFile` ya estaba endurecido respecto a warnings y diálogo Tauri

Hallazgos:

### UX-03 / ARQ-01. Export/import/undo aún no pasan todos por la misma infraestructura HTTP

Evidencia:

- `ExportDialog.vue`
- `ImportWorkDialog.vue`
- `ProjectDetailView.vue`
- `TimelineView.vue`
- `EventStatsCard.vue`

Impacto:

- timeouts, retries, backend-down banner y errores homogéneos no se aplican de forma universal
- la experiencia de fallo cambia según la superficie

Recomendación:

- extender `apiClient` con helpers de descarga/subida/raw request y migrar estas rutas primero

## 3.5 Configuración y capacidades de máquina

### Estado

**Buena y mucho más coherente que en auditorías previas**.

Fortalezas:

- `analysis_features` ya gobierna realmente el backend.
- `SettingsView.vue` expone más señal útil para usuario avanzado, incluyendo thresholds de votación y warnings de detección incierta.
- el backend diferencia mejor entre `installed`, `available` y `hardware_supported`.
- la UI muestra `needsRestart` y estados de descarga/instalación mejor descritos.

Hallazgo residual:

### UX-04. `SettingsView.vue` es funcional pero cognitivamente demasiado densa

Dato estructural:

- `frontend/src/views/SettingsView.vue`: 3348 líneas

Lectura de producto:

- no está “rota”, pero su tamaño delata exceso de responsabilidades en una sola pantalla.
- para correctores no técnicos, tanta densidad aumenta fatiga y reduce comprensibilidad.

Recomendación:

1. Dividir por secciones reales o subrutas:
   - General
   - Apariencia
   - Análisis
   - Motores y recursos
   - Datos/licencia
2. Añadir resúmenes cortos por bloque y esconder detalles avanzados detrás de expanders claros.

## 4. Accesibilidad, temas y diseño visual

## 4.1 Estado actual

Fortaleza real actual:

- `frontend/e2e/accessibility.spec.ts` cubre 6 presets (`aura`, `lara`, `material`, `nora`, `grammarly`, `scrivener`) en light/dark.
- los checks relevantes ahora son estrictos en vez de tolerantes.
- se reforzaron labels, focus states y contraste en múltiples superficies.

Esto es una mejora material respecto a estados anteriores.

## 4.2 Deuda residual

### A11Y-01. Aún falta revisión manual de componentes complejos no totalmente cubiertos por axe

Áreas sensibles:

- `RelationshipGraph.vue`
- `TimelineView.vue`
- vistas con canvas/vis-network/vis-timeline
- diálogos nativos (`alert/confirm/prompt`)

Recomendación:

- checklist manual por release para foco, semántica equivalente y navegación por teclado

### A11Y-02. `docs/WCAG_COLOR_AUDIT.md` debe seguir tratándose como histórico técnico, no como estado presente

Estado correcto actual:

- ya tiene nota de vigencia y no se usa como certificación global actual

Riesgo:

- sigue siendo fácil leerlo fuera de contexto si no se acompaña del índice de auditorías actualizado

## 4.3 Diseño y consistencia visual

Lectura general:

- la dirección visual ha mejorado, especialmente en contraste, icon-only buttons y temas custom.
- la principal deuda visual ya no es “mal diseño”, sino dispersión de patrones: algunas superficies siguen fuera del sistema de diálogo/feedback y eso rompe percepción de cohesión.

## 5. Arquitectura, reutilización y centralización

## 5.1 Transporte HTTP

### ARQ-02. `apiClient` ya existe, pero la migración está incompleta

Métrica estática:

- 13 archivos frontend siguen usando `fetch()` fuera de `apiClient`

Problema:

- el proyecto ya construyó la capa correcta, pero no la usa de forma universal
- esto genera dos arquitecturas a la vez

Mejor enfoque:

- no reescribir todo a la vez
- completar la migración por familias de uso:
  1. export/import/download
  2. undo/history
  3. vistas secundarias (`timeline`, `feature-profile`, `mention navigation`)

## 5.2 Storage local

### ARQ-03. El storage local sigue sin una gobernanza única

Métrica estática:

- 19 archivos con `localStorage` o `sessionStorage`

Problema:

- no todos esos usos son incorrectos, pero sí están poco orquestados
- la app ya tiene necesidades de migración/versionado suficientes para justificar una capa común

Mejor enfoque:

- `storageRegistry` con metadata de cada clave
- wrapper único para lectura/escritura segura y migraciones

## 5.3 Componentes y módulos demasiado grandes

### ARQ-04. Hay valor en el producto, pero gran parte de él está concentrado en pocos monolitos

Monolitos destacados:

- `_analysis_phases.py` (6174)
- `attributes.py` (4285)
- `SettingsView.vue` (3348)
- `analysis_pipeline.py` (2972)
- `entities.py` (2779)
- `alerts/engine.py` (2670)
- `DocumentViewer.vue` (2605)
- `ProjectDetailView.vue` (2575)

Consecuencia:

- la app puede funcionar bien y aun así volverse lenta de evolucionar
- cada refactor o fix marginal tiene demasiado radio de explosión

Mejor enfoque:

- extraer por subdominio estable, no por “trozos arbitrarios de 500 líneas”

## 5.4 Logging y observabilidad

### ARQ-05. Sigue habiendo demasiada depuración de consola en runtime

Métrica estática:

- 15 archivos con `console.log(...)` en código de producto

Lectura correcta:

- esto no rompe al usuario directamente
- pero sí debilita soporte, claridad operativa y disciplina de release

Mejor enfoque:

- modo debug explícito
- logger centralizado
- política de no dejar `console.log` de inspección en rutas de producto

## 6. Base de datos, pipeline y rendimiento

## 6.1 Persistencia

Estado actual:

- no he detectado en esta revisión un bug nuevo de integridad de datos en las rutas auditadas
- `.nra`, `analysis_runs/analysis_phases`, incremental planner y enrichment cache están sensiblemente mejor que en auditorías anteriores

## 6.2 Rendimiento

Fortalezas:

- planner incremental y caches ya aportan beneficio real
- fast-path y run ledger reducen recomputaciones inútiles y falsos estados

Riesgo estructural:

- el rendimiento futuro depende menos del algoritmo base y más de mantener controlada la complejidad accidental de los monolitos y de la dispersión de responsabilidades

## 7. Testing y completitud

## 7.1 Lo que está bien

- volumen alto de tests (backend + frontend)
- tests específicos en shell/store/backend/persistencia
- accesibilidad automatizada ya útil como guardrail real

## 7.2 Lo que falta

### TEST-01. Falta smoke desktop empaquetado por plataforma

Sigue siendo el hueco más importante.

### TEST-02. Faltan E2E de algunas superficies secundarias de alto valor

Candidatos claros:

- export/import completos desde UI
- historial/undo-all
- guardado/apertura `.nra` desde flujo Tauri completo
- restart del sidecar visible desde la shell

### TEST-03. Los documentos de estado de testing antiguos ya no sirven como fuente de verdad

Documentos problemáticos:

- `docs/FRONTEND_TESTS_STATUS.md`
- `docs/NEXT_STEPS.md`
- `docs/SUMMARY_WORK_COMPLETED.md`
- `docs/OPTIMIZATION_STATUS.md`
- `docs/STATUS_2026-02-18.md`

Problema:

- siguen siendo útiles como histórico, pero no como estado operativo presente

## 8. Documentación: qué sobra, qué sirve y qué necesita actualización

## 8.1 Canónicos útiles

- `README.md`
- `docs/README.md`
- `docs/PLAN_ACTIVE.md`
- `docs/PROJECT_STATUS.md`
- `docs/ROADMAP.md`
- `docs/AUDIT_INDEX.md`

## 8.2 Históricos útiles, pero no canónicos

- `docs/IMPROVEMENT_PLAN.md`
- `docs/WCAG_COLOR_AUDIT.md`
- `docs/debugging/CACHE_SYSTEM_NOTES.md`
- auditorías 2026-02-14 y 2026-03-02
- `docs/FRONTEND_TESTS_STATUS.md`
- `docs/NEXT_STEPS.md`
- `docs/SUMMARY_WORK_COMPLETED.md`
- `docs/OPTIMIZATION_STATUS.md`
- `docs/STATUS_2026-02-18.md`

## 8.3 Documento que conviene dividir más adelante

- `docs/BUILD_AND_DEPLOY.md`

Motivo:

- mezcla setup de desarrollo, build y runtime empaquetado

## 9. Veredicto global

La app ya está en un estado donde el flujo editorial principal funciona y tiene bastante hardening técnico. El problema principal ya no es de “capacidad del producto”, sino de **uniformidad operacional y mantenimiento**.

La foto actual es esta:

- **Funcionalidad core**: buena
- **Primer arranque y sidecar local**: buena, pero sin smoke empaquetado completo
- **UX no técnica**: buena en flujos principales, desigual en secundarios
- **Accesibilidad automatizada**: buena
- **Arquitectura**: correcta en dirección, incompleta en centralización
- **Mantenibilidad**: penalizada por monolitos, `fetch` disperso, storage disperso y logging de depuración

## 10. Recomendación de ejecución

### Sprint corto recomendado

1. Smoke test empaquetado desktop.
2. `fetch -> apiClient` en export/import/undo.
3. Sustituir `alert/confirm/prompt` en flujos visibles.

### Sprint de consolidación

1. `storageRegistry`.
2. limpieza de `console.log`.
3. extracción de `SettingsView` y `ProjectDetailView`.

### Sprint estructural

1. dividir `_analysis_phases.py`
2. dividir `attributes.py`
3. reforzar telemetría de fallbacks/degradaciones
