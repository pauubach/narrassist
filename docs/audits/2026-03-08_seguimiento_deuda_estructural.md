# Seguimiento de deuda estructural

Fecha: 2026-03-08
Estado: seguimiento activo posterior a las auditorias del 2026-03-07
Alcance: frontend desktop Tauri, shell de arranque, transporte HTTP, UX de confirmacion y deuda de mantenibilidad

## 1. Resumen ejecutivo

Entre el 2026-03-07 y el 2026-03-08 se ha cerrado la mayor parte de la deuda estructural inmediata del frontend:

- `fetch()` directo en producto: cerrado
- dialogos nativos `alert/confirm/prompt`: cerrados
- acciones placeholder visibles en menu/contexto principal: cerradas
- `console.log/debug` de producto: cerrados en `frontend/src`
- smoke test desktop MVP del shell Tauri: cerrado a nivel de store/eventos

El sistema queda mas consistente y menos propenso a divergencias entre vistas, stores y servicios compartidos.

## 2. Cambios estructurales cerrados

### 2.1 Transporte HTTP centralizado

Se ha consolidado el transporte de producto sobre `apiClient` y servicios compartidos.

Piezas nuevas o reforzadas:

- `frontend/src/services/apiClient.ts`
- `frontend/src/services/projectExports.ts`
- `frontend/src/services/eventStats.ts`
- `frontend/src/utils/fileDownload.ts`

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
- solo permanecen `fetch()` en `apiClient` y en `logger`, ambos como infraestructura

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

- prueba automatizada sobre binario Tauri empaquetado por plataforma
- verificacion de bootstrap real fuera del entorno de desarrollo
- validacion de sidecar + ventana + backend ya compilados

Estado: no bloqueante para desarrollo diario, pero si deuda real de release.

### 4.2 Logger como transporte especial

`frontend/src/services/logger.ts` sigue usando `fetch()` directo.

Valoracion:

- aceptable a corto plazo
- razon tecnica: evitar acoplar el logger a `apiClient` y crear recursion de logging o dependencia circular

Recomendacion futura:

- extraer un transporte de bajo nivel comun para `apiClient` y `logger`, o
- documentar explicitamente el logger como excepcion arquitectonica permitida

### 4.3 Monolitos grandes

Siguen siendo la deuda de mantenibilidad mas costosa:

- `frontend/src/views/SettingsView.vue`
- `frontend/src/views/ProjectDetailView.vue`
- `frontend/src/components/DocumentViewer.vue`
- `api-server/routers/_analysis_phases.py`
- `src/narrative_assistant/pipelines/analysis_pipeline.py`

Prioridad recomendada:

1. `SettingsView.vue`
2. `ProjectDetailView.vue`
3. `DocumentViewer.vue`
4. `_analysis_phases.py`
5. `analysis_pipeline.py`

### 4.4 Cobertura funcional E2E de exportaciones e importaciones

Aunque las rutas y componentes ya usan capas comunes, sigue faltando blindaje E2E especifico para:

- exportaciones DOCX/PDF/Scrivener/editorial
- importacion de trabajo editorial
- errores de permisos o cancelacion en dialogos Tauri

## 5. Validacion realizada

Frontend:

- `npm run type-check`
- `npm run test:run -- src/stores/__tests__/app.spec.ts src/stores/__tests__/system.spec.ts src/stores/__tests__/theme.spec.ts src/components/DocumentViewer.spec.ts`

Comprobaciones de estructura:

- `rg -n "\\bfetch\\(" frontend/src --glob '!**/*.spec.ts' --glob '!**/*.test.ts'`
- `rg -n "\\b(alert|confirm|prompt)\\(" frontend/src --glob '!**/*.spec.ts' --glob '!**/*.test.ts'`
- `rg -n "console\\.(log|debug)\\(" frontend/src --glob '!**/*.spec.ts' --glob '!**/*.test.ts'`

Resultado:

- `type-check`: OK
- tests: OK
- `fetch()` de producto: 0
- dialogos nativos: 0
- `console.log/debug` de producto: 0

## 6. Veredicto

La deuda estructural inmediata del frontend queda mayoritariamente cerrada.

Lo pendiente ya no es un problema de higiene basica, sino de siguientes capas de calidad:

- release testing desktop empaquetado
- refactor por slices de archivos monoliticos
- cobertura E2E especifica de export/import
- formalizar la excepcion del logger o extraer transporte de bajo nivel compartido