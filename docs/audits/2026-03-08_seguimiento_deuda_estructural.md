# Seguimiento de deuda estructural

Fecha: 2026-03-08
Estado: seguimiento activo posterior a las auditorias del 2026-03-07
Alcance: frontend desktop Tauri, shell de arranque, transporte HTTP, UX de confirmacion y deuda de mantenibilidad

## 1. Resumen ejecutivo

Entre el 2026-03-07 y el 2026-03-08 se ha cerrado la mayor parte de la deuda estructural inmediata del frontend:

- `fetch()` directo en producto: cerrado
- transporte HTTP de bajo nivel compartido (`apiClient` + `logger`): cerrado
- dialogos nativos `alert/confirm/prompt`: cerrados
- acciones placeholder visibles en menu/contexto principal: cerradas
- `console.log/debug` de producto: cerrados en `frontend/src`
- smoke test desktop MVP del shell Tauri: cerrado a nivel de store/eventos
- smoke reproducible sobre binario desktop construido: disponible
- smoke de binario construido integrado en CI para Windows y macOS: cerrado
- refactor de `SettingsView` cubierto con smoke test y tests por seccion: cerrado
- flujo `.nra` (dialogo Tauri + backend): cubierto con tests de composable

El sistema queda mas consistente y menos propenso a divergencias entre vistas, stores y servicios compartidos.

## 2. Cambios estructurales cerrados

### 2.1 Transporte HTTP centralizado

Se ha consolidado el transporte de producto sobre `apiClient` y servicios compartidos.

Piezas nuevas o reforzadas:

- `frontend/src/services/apiClient.ts`
- `frontend/src/services/httpTransport.ts`
- `frontend/src/services/projectExports.ts`
- `frontend/src/services/eventStats.ts`
- `frontend/src/utils/fileDownload.ts`
- `frontend/src/services/logger.ts`

Migraciones relevantes:

- `frontend/src/components/ExportDialog.vue`
- `frontend/src/components/ImportWorkDialog.vue`
- `frontend/src/components/events/EventStatsCard.vue`
- `frontend/src/components/events/EventsExportDialog.vue`
- `frontend/src/components/timeline/TimelineView.vue`
- `frontend/src/components/DocumentViewer.vue`
- `frontend/src/views/ProjectDetailView.vue`
- `frontend/src/composables/useFeatureProfile.ts`
- `frontend/src/composables/useMentionNavigation.ts`
- `frontend/src/composables/useSequentialMode.ts`
- `frontend/src/composables/useGlobalUndo.ts`

Resultado verificado:

- en `frontend/src` ya no quedan `fetch()` directos de producto
- `fetch()` queda encapsulado en `frontend/src/services/httpTransport.ts`
- `apiClient` y `logger` comparten ese transporte de bajo nivel sin dependencia circular

### 2.2 Dialogos nativos eliminados

Se ha extraido una capa comun de confirmacion:

- `frontend/src/composables/useAppConfirm.ts`

Migraciones aplicadas en CRUD y flujos de gestion:

- `frontend/src/views/CollectionsView.vue`
- `frontend/src/views/CollectionDetailView.vue`
- `frontend/src/views/CharacterView.vue`
- `frontend/src/components/collections/CollectionBookList.vue`
- `frontend/src/components/collections/EntityLinkPanel.vue`
- `frontend/src/composables/useEntityCrud.ts`
- `frontend/src/composables/useProjectFile.ts`
- `frontend/src/components/sidebar/HistoryPanel.vue`
- `frontend/src/components/workspace/GlossaryTab.vue`
- `frontend/src/App.vue` (ConfirmDialog global)

Resultado verificado:

- no quedan llamadas a `alert()`, `confirm()` ni `prompt()` en `frontend/src`

### 2.3 Placeholders visibles cerrados

Se han eliminado acciones visibles que antes no hacian nada o solo escribian en consola.

- `frontend/src/views/ProjectsView.vue`
  - `Re-analizar` abre el proyecto y despacha `menubar:run-analysis`
  - `Exportar` abre el proyecto y despacha `menubar:export`
- `frontend/src/composables/useNativeMenu.ts`
- `frontend/src/App.vue`
  - `check_updates` deja de ser un placeholder silencioso y responde con mensaje explicito al usuario

### 2.4 Limpieza de logging de depuracion

Se ha eliminado el logging de depuracion (`console.log` / `console.debug`) de `frontend/src`.

Archivos limpiados en esta pasada:

- `frontend/src/App.vue`
- `frontend/src/stores/app.ts`
- `frontend/src/stores/theme.ts`
- `frontend/src/composables/useNativeMenu.ts`
- `frontend/src/composables/useProjectData.ts`
- `frontend/src/composables/useMentionNavigation.ts`
- `frontend/src/components/sidebar/ChatMessageContent.vue`
- `frontend/src/components/sidebar/AssistantPanel.vue`
- `frontend/src/components/workspace/TextTab.vue`
- `frontend/src/components/DocumentViewer.vue`
- `frontend/src/components/RelationshipGraph.vue`
- `frontend/src/views/SettingsView.vue`

Se conservan `console.warn` y `console.error` donde siguen aportando diagnostico real.

### 2.5 Smoke test desktop MVP

Se ha reforzado `frontend/src/stores/__tests__/app.spec.ts` con un caso de ciclo completo del shell Tauri:

- arranque
- `starting`
- `running`
- `restarting`
- `running`
- `error`

Este smoke test no sustituye una prueba sobre binario empaquetado, pero si cierra el hueco de regresion obvia en el flujo de eventos del sidecar local.

### 2.6 Refactor de SettingsView blindado

El troceado de `frontend/src/views/SettingsView.vue` ya no queda sin red de seguridad.

Cobertura nueva:

- `frontend/src/components/settings/SettingsSections.spec.ts`
  - valida wiring de `AnalysisSection`, `SemanticAnalyzerSection`, `DetectionMethodsSection`,
    `CorrectionsSection`, `DataMaintenanceSection` y `LicenseSection`
- `frontend/src/views/SettingsView.spec.ts`
  - smoke test del contenedor
  - validacion de `provide/inject` indirecta via montaje
  - carga inicial de settings/capabilities/proyecto
  - apertura de dialogos y enrutado de eventos de secciones

Resultado:

- el refactor deja de estar cubierto solo "por inspeccion"
- hay red de seguridad para futuras extracciones del monolito

### 2.7 Flujo de archivos `.nra` blindado

Se ha añadido cobertura especifica para el composable de archivo de proyecto:

- `frontend/src/composables/useProjectFile.spec.ts`

Casos cubiertos:

- guardado con sanitizacion del nombre por defecto
- cancelacion del dialogo de guardado
- apertura con normalizacion de `warnings` y nombre por defecto
- error explicito fuera de entorno Tauri

### 2.8 Importacion de trabajo editorial blindada

Se ha añadido cobertura funcional del dialogo de importacion editorial:

- `frontend/src/components/ImportWorkDialog.spec.ts`

Casos cubiertos:

- seleccion de archivo y preview via `postForm`
- confirmacion de importacion con payload correcto
- cierre y reset del flujo tras completar
- error de preview con toast accionable para el usuario

### 2.9 Smoke desktop sobre binario construido

Se ha anadido un smoke runner reproducible para la app desktop ya construida:

- `scripts/smoke_desktop_app.py`
- `tests/scripts/test_smoke_desktop_app.py`

Cobertura:

- autodeteccion de binario release cuando existe
- arranque del binario desktop
- polling de `http://127.0.0.1:8008/api/health`
- requisito de readiness real si el payload expone `backend_loaded`
- cierre del proceso al finalizar o en error

Limite actual:

- no sustituye una prueba sobre instalador/DMG final
- pero elimina el hueco de "no hay script reproducible para comprobar el binario"
- el script queda integrado en workflows de Windows y macOS tras `cargo tauri build`

### 2.10 Extraccion del flujo de exportacion en DocumentViewer

Se ha separado la logica de exportacion del visor de documento en un composable dedicado:

- `frontend/src/components/document-viewer/useDocumentViewerExport.ts`
- `frontend/src/components/document-viewer/useDocumentViewerExport.spec.ts`
- `frontend/src/components/document-viewer/useDocumentViewerPreferences.ts`
- `frontend/src/components/document-viewer/useDocumentViewerPreferences.spec.ts`

Resultado:

- `DocumentViewer.vue` deja de mezclar estado visual con exportacion JSON/binaria
- las preferencias de apariencia y visibilidad de errores salen del componente principal
- el flujo de exportacion queda testeado de forma aislada
- el componente principal reduce tamaño y superficie de regresion (~2146 lineas)

### 2.11 Extraccion de exportaciones y acciones de alertas en ProjectDetailView

Se han separado dos bloques funcionales del detalle de proyecto:

- `frontend/src/views/project-detail/useProjectDetailExports.ts`
- `frontend/src/views/project-detail/useProjectDetailExports.spec.ts`
- `frontend/src/views/project-detail/useProjectDetailAlerts.ts`
- `frontend/src/views/project-detail/useProjectDetailAlerts.spec.ts`

Bloques extraidos:

- apertura y estado del dialogo de exportacion
- exportacion rapida de guia de estilo
- exportacion de documento corregido
- resolucion/descarte de alertas
- resolucion batch de ambiguas
- cambio de estado de alerta con notificacion a historial

Resultado:

- `ProjectDetailView.vue` baja a ~2.1K lineas
- la IO y los toasts de alertas/exportaciones dejan de vivir incrustados en la vista
- el refactor queda blindado con tests especificos y no solo con smoke del contenedor
- los caminos batch (`resolve-all`, `batch-resolve-attributes`) tambien quedan cubiertos

## 3. Reutilizacion y centralizacion logradas

La pasada deja cuatro piezas reutilizables nuevas o consolidadas:

1. `apiClient` como transporte unico de producto.
2. `projectExports` como capa comun de exportaciones binarias.
3. `fileDownload` como utilitario comun de descarga y conversion de blobs/base64.
4. `useAppConfirm` como confirmacion comun, desacoplada de componentes concretos.

Esto reduce duplicacion y baja el coste de seguir troceando vistas monoliticas.

## 4. Lo que sigue pendiente de verdad

### 4.1 Smoke test desktop empaquetado

Pendiente:

- verificacion de bootstrap real fuera del entorno de desarrollo
- validacion de sidecar + ventana + backend ya compilados

Estado:

- cerrado para binario construido en CI Windows/macOS
- pendiente solo el ultimo tramo sobre instalador/DMG empaquetado final

### 4.2 Monolitos grandes

Siguen siendo la deuda de mantenibilidad mas costosa:

- `frontend/src/views/SettingsView.vue` (~1630 lineas)
- `frontend/src/views/ProjectDetailView.vue` (~2126 lineas)
- `frontend/src/components/DocumentViewer.vue` (~2146 lineas)
- `api-server/routers/_analysis_phases.py`
- `src/narrative_assistant/pipelines/analysis_pipeline.py`

Prioridad recomendada:

1. `ProjectDetailView.vue`
2. `DocumentViewer.vue`
3. `_analysis_phases.py`
4. `analysis_pipeline.py`

Nota:

- `SettingsView.vue` sigue siendo grande, pero ya esta parcialmente troceado y cubierto
- `ProjectDetailView.vue` y `DocumentViewer.vue` ya tienen slices funcionales extraidos, pero siguen siendo monolitos
- la prioridad se desplaza al siguiente troceado util de esas dos vistas y a los monolitos backend

### 4.3 Cobertura funcional E2E de exportaciones e importaciones

Aunque las rutas y componentes ya usan capas comunes, sigue faltando blindaje E2E especifico para:

- exportaciones DOCX/PDF/Scrivener/editorial
- importacion de trabajo editorial
- errores de permisos o cancelacion en dialogos Tauri

Cobertura ya cerrada a nivel unit/integration:

- `projectExports.spec.ts`
- `useProjectFile.spec.ts`
- `ImportWorkDialog.spec.ts`

Lo pendiente aqui es el salto a flujo empaquetado real o Playwright desktop, no la ausencia total de tests.

## 5. Validacion realizada

Frontend:

- `npm run type-check`
- `npm run test:run -- src/stores/__tests__/app.spec.ts src/stores/__tests__/system.spec.ts src/stores/__tests__/theme.spec.ts src/stores/__tests__/analysis.spec.ts src/components/layout/__tests__/StatusBar.spec.ts`
- `npm run test:run -- src/components/settings/SettingsSections.spec.ts src/views/SettingsView.spec.ts src/composables/useProjectFile.spec.ts src/components/ImportWorkDialog.spec.ts src/services/httpTransport.spec.ts`
- `npm run test:run -- src/services/projectExports.spec.ts src/components/ExportDialog.spec.ts`
- `npm run test:run -- src/components/document-viewer/useDocumentViewerExport.spec.ts src/components/document-viewer/useDocumentViewerPreferences.spec.ts src/views/project-detail/useProjectDetailExports.spec.ts src/views/project-detail/useProjectDetailAlerts.spec.ts`

Backend / scripts:

- `pytest tests/scripts/test_smoke_desktop_app.py -q`

Comprobaciones de estructura:

- `rg -n "\\bfetch\\(" frontend/src --glob '!**/*.spec.ts' --glob '!**/*.test.ts'`
- `rg -n "\\b(alert|confirm|prompt)\\(" frontend/src --glob '!**/*.spec.ts' --glob '!**/*.test.ts'`
- `rg -n "console\\.(log|debug)\\(" frontend/src --glob '!**/*.spec.ts' --glob '!**/*.test.ts'`

Resultado:

- `type-check`: OK
- tests: OK
- `fetch()` directo de producto: 0
- `fetch()` compartido encapsulado en `httpTransport`: 1 punto de salida controlado
- dialogos nativos: 0
- `console.log/debug` de producto: 0

## 6. Veredicto

La deuda estructural inmediata del frontend queda mayoritariamente cerrada.

Lo pendiente ya no es un problema de higiene basica, sino de siguientes capas de calidad:

- release testing final sobre instalador/DMG
- refactor por slices de archivos monoliticos
- cobertura E2E especifica de export/import
- continuar troceando vistas grandes ya con cobertura incremental
