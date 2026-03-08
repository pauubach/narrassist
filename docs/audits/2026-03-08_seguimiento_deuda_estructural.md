# Seguimiento de deuda estructural

Fecha: 2026-03-08
Estado: seguimiento activo posterior a las auditorias del 2026-03-07
Alcance: frontend desktop Tauri, shell de arranque, smoke desktop, transporte HTTP y troceado progresivo de monolitos frontend/backend

## 1. Resumen ejecutivo

Entre el 2026-03-07 y el 2026-03-08 se ha cerrado la mayor parte de la deuda estructural inmediata y se ha avanzado un tramo real del refactor de monolitos.

Cierres y avances ya materializados:

- `fetch()` directo en producto: cerrado
- transporte HTTP de bajo nivel compartido (`apiClient` + `logger` + `httpTransport`): cerrado
- dialogos nativos `alert/confirm/prompt`: cerrados en `frontend/src`
- acciones placeholder visibles en menu/contexto principal: cerradas
- `console.log/debug` de producto: cerrados en `frontend/src`
- smoke test desktop MVP del shell Tauri: cerrado a nivel de store/eventos
- smoke reproducible sobre binario construido: cerrado
- smoke reproducible sobre instalador NSIS y DMG final: cerrado a nivel de script, tests y workflow
- `SettingsView` troceado y cubierto: cerrado en este tramo
- flujo `.nra` y flujo editorial: cubiertos con tests de composable/dialogos
- `ProjectDetailView` con bootstrap, analisis, alertas, exportaciones y lifecycle extraidos: avance solido
- `DocumentViewer` con exportacion, preferencias, datos, dialogos y helpers puros extraidos: avance solido
- `_analysis_phases.py` con helpers runtime/cache/structure extraidos: avance solido
- `analysis_pipeline.py` con modelos, temporal y dialogo/voz extraidos: avance solido

Resultado global:

- menos duplicacion de infraestructura
- menos IO incrustada en vistas grandes
- mas cobertura especifica de flujos reales
- menos riesgo de regresion silenciosa en desktop
- monolitos sensiblemente mas pequeños y con responsabilidades mejor separadas

## 2. Cambios estructurales cerrados

### 2.1 Transporte HTTP centralizado

Piezas consolidadas:

- `frontend/src/services/apiClient.ts`
- `frontend/src/services/httpTransport.ts`
- `frontend/src/services/projectExports.ts`
- `frontend/src/services/eventStats.ts`
- `frontend/src/utils/fileDownload.ts`
- `frontend/src/services/logger.ts`

Resultado verificado:

- en `frontend/src` ya no quedan `fetch()` directos de producto
- `fetch()` queda encapsulado en `frontend/src/services/httpTransport.ts`
- `apiClient` y `logger` comparten el mismo transporte de bajo nivel

### 2.2 Dialogos nativos eliminados

Capa comun:

- `frontend/src/composables/useAppConfirm.ts`

Resultado verificado:

- no quedan llamadas a `alert()`, `confirm()` ni `prompt()` en `frontend/src`

### 2.3 Placeholders visibles cerrados

Puntos principales saneados:

- `frontend/src/views/ProjectsView.vue`
- `frontend/src/composables/useNativeMenu.ts`
- `frontend/src/App.vue`

### 2.4 Limpieza de logging de depuracion

Resultado verificado:

- `console.log/debug` de producto: 0
- se conservan `console.warn` y `console.error` donde aportan diagnostico real

### 2.5 Smoke test desktop MVP del shell Tauri

Cobertura reforzada en `frontend/src/stores/__tests__/app.spec.ts`:

- `starting`
- `running`
- `restarting`
- `error`

### 2.6 Refactor de SettingsView blindado

Cobertura:

- `frontend/src/components/settings/SettingsSections.spec.ts`
- `frontend/src/views/SettingsView.spec.ts`

### 2.7 Flujo de archivos `.nra` blindado

Cobertura:

- `frontend/src/composables/useProjectFile.spec.ts`

### 2.8 Importacion de trabajo editorial blindada

Cobertura:

- `frontend/src/components/ImportWorkDialog.spec.ts`

### 2.9 Smoke desktop sobre binario construido

Piezas:

- `scripts/smoke_desktop_app.py`
- `tests/scripts/test_smoke_desktop_app.py`

Cobertura:

- autodeteccion de binario release
- arranque del binario desktop
- polling de `/api/health`
- comprobacion de `backend_loaded` cuando existe
- cierre del proceso al finalizar o en error

### 2.10 Smoke desktop sobre instalador NSIS y DMG final

El smoke runner cubre tambien:

- modo `windows-installer`
- modo `macos-dmg`

Integracion:

- `.github/workflows/build-release.yml`
- `.github/workflows/release.yml`

Cobertura nueva:

- descubrimiento del instalador NSIS o del DMG
- instalacion silenciosa temporal en Windows y arranque de la app instalada
- montaje temporal del DMG en macOS y arranque desde el bundle
- limpieza posterior del directorio o punto de montaje temporal

### 2.11 Extraccion funcional de DocumentViewer

Slices ya extraidos:

- `frontend/src/components/document-viewer/useDocumentViewerExport.ts`
- `frontend/src/components/document-viewer/useDocumentViewerPreferences.ts`
- `frontend/src/components/document-viewer/useDocumentViewerData.ts`
- `frontend/src/components/document-viewer/useDocumentViewerDialogues.ts`
- `frontend/src/components/document-viewer/documentViewerText.ts`
- `frontend/src/components/document-viewer/useDocumentViewerInteractions.ts`

Cobertura asociada:

- `useDocumentViewerExport.spec.ts`
- `useDocumentViewerPreferences.spec.ts`
- `useDocumentViewerData.spec.ts`
- `useDocumentViewerDialogues.spec.ts`
- `documentViewerText.spec.ts`
- `useDocumentViewerInteractions.spec.ts`
- `DocumentViewer.spec.ts`

Resultado:

- `DocumentViewer.vue` reduce IO, helpers puros, interaccion de seleccion/click y estado mezclado
- el componente principal baja a ~1922 lineas
- la logica de exportacion, datos, dialogos, preferencias y texto queda testeada por separado

### 2.12 Extraccion funcional de ProjectDetailView

Slices ya extraidos:

- `frontend/src/views/project-detail/useProjectDetailExports.ts`
- `frontend/src/views/project-detail/useProjectDetailAlerts.ts`
- `frontend/src/views/project-detail/projectDetailBootstrap.ts`
- `frontend/src/views/project-detail/useProjectDetailAnalysis.ts`
- `frontend/src/views/project-detail/useProjectDetailLifecycle.ts`

Cobertura asociada:

- `useProjectDetailExports.spec.ts`
- `useProjectDetailAlerts.spec.ts`
- `projectDetailBootstrap.spec.ts`
- `useProjectDetailAnalysis.spec.ts`
- `useProjectDetailLifecycle.spec.ts`

Resultado:

- `ProjectDetailView.vue` reduce bootstrap incrustado, reanalisis, toasts, recargas reactivas y wiring de tabs
- la carrera inicial de `?alert=` queda corregida y testeada
- el componente principal baja a ~1865 lineas

### 2.13 Primer troceado de monolitos backend

Modulos nuevos en routers:

- `api-server/routers/_analysis_runtime.py`
- `api-server/routers/_analysis_cache_helpers.py`
- `api-server/routers/_analysis_structure_helpers.py`

Responsabilidades extraidas:

- capabilities runtime y filtrado de metodos NLP
- serializacion/restauracion de cache de entidades, menciones y coreferencia
- metricas ligeras por capitulo
- deteccion/persistencia de dialogos
- inicializacion de `dialogue_style_preference`

Cobertura asociada:

- `tests/unit/test_cr03_runtime_settings.py`
- `tests/unit/test_analysis_cache_roundtrip.py`
- `tests/unit/test_analysis_structure_helpers.py`

Resultado:

- `_analysis_phases.py` baja a ~4968 lineas
- se mantiene compatibilidad con los puntos de monkeypatch historicos de la suite

### 2.14 Primer troceado del pipeline legacy

Modulos nuevos:

- `src/narrative_assistant/pipelines/analysis_pipeline_models.py`
- `src/narrative_assistant/pipelines/analysis_pipeline_temporal.py`
- `src/narrative_assistant/pipelines/analysis_pipeline_dialogue.py`

Responsabilidades extraidas:

- modelos/dataclasses del pipeline
- analisis temporal y persistencia de timeline
- extraccion de dialogos por capitulo
- conversion de dialogos para analisis emocional
- analisis legacy de voz

Cobertura asociada:

- `tests/unit/test_analysis_pipeline_dialogue.py`
- `tests/unit/test_temporal_entity_mentions_integration.py`

Resultado:

- `analysis_pipeline.py` baja a ~1995 lineas
- la logica de dialogo/voz deja de vivir incrustada en el pipeline principal

## 3. Reutilizacion y centralizacion logradas

Piezas reutilizables nuevas o consolidadas:

1. `apiClient` como transporte unico de producto.
2. `httpTransport` como unico punto de salida HTTP de bajo nivel.
3. `projectExports` como capa comun de exportaciones binarias.
4. `fileDownload` como utilitario comun de descarga y conversion de blobs/base64.
5. `useAppConfirm` como confirmacion comun desacoplada de componentes concretos.
6. `projectDetailBootstrap` como bootstrap reutilizable y testeable del detalle.
7. `useProjectDetailAnalysis` como slice reutilizable del flujo de analisis del detalle.
8. `useProjectDetailLifecycle` como sincronizacion reactiva reutilizable del detalle.
9. `documentViewerText` como modulo puro reutilizable para transformaciones textuales del visor.
10. `analysis_pipeline_dialogue` como modulo reutilizable de dialogo/voz para el pipeline legacy.
11. `_analysis_structure_helpers` como capa reutilizable de estructura persistida en router.

## 4. Lo que sigue pendiente de verdad

### 4.1 Release testing final sobre artefactos empaquetados

Ya no falta soporte tecnico. Lo pendiente es operativo:

- ejecutar sistematicamente el smoke sobre artefactos generados en runners/plataformas reales
- convertirlo en puerta formal de release, no solo en script/workflow disponible
- añadir validacion final de ventana visible y sidecar en entorno empaquetado real cuando aplique

### 4.2 Monolitos grandes restantes

Siguen siendo la deuda de mantenibilidad mas costosa:

- `frontend/src/views/SettingsView.vue` (~1630 lineas)
- `frontend/src/views/ProjectDetailView.vue` (~1865 lineas)
- `frontend/src/components/DocumentViewer.vue` (~1922 lineas)
- `api-server/routers/_analysis_phases.py` (~4968 lineas)
- `src/narrative_assistant/pipelines/analysis_pipeline.py` (~1995 lineas)

Prioridad recomendada:

1. `DocumentViewer.vue`
2. `ProjectDetailView.vue`
3. `_analysis_phases.py`
4. `analysis_pipeline.py`

### 4.3 Cobertura E2E de export/import en desktop real

Cobertura ya cerrada a nivel unit/integration:

- `projectExports.spec.ts`
- `useProjectFile.spec.ts`
- `ImportWorkDialog.spec.ts`
- `ExportDialog.spec.ts`

Lo pendiente aqui es el salto a flujo desktop real o Playwright/Tauri real para:

- exportaciones DOCX/PDF/Scrivener/editorial
- importacion de trabajo editorial
- errores de permisos o cancelacion en dialogos Tauri

### 4.4 Politica global de logging de error

Ya no queda ruido de depuracion basico, pero sigue faltando decidir una politica comun para `console.error` / `console.warn` residuales:

- que se conserva como diagnostico local legitimo
- que debe pasar por logger estructurado
- que debe degradarse a toast, telemetry o silence controlado

## 5. Validacion realizada

Frontend:

- `npm run type-check`
- `npm run test:run -- src/stores/__tests__/app.spec.ts src/stores/__tests__/system.spec.ts src/stores/__tests__/theme.spec.ts src/stores/__tests__/analysis.spec.ts src/components/layout/__tests__/StatusBar.spec.ts`
- `npm run test:run -- src/components/settings/SettingsSections.spec.ts src/views/SettingsView.spec.ts src/composables/useProjectFile.spec.ts src/components/ImportWorkDialog.spec.ts src/services/httpTransport.spec.ts`
- `npm run test:run -- src/services/projectExports.spec.ts src/components/ExportDialog.spec.ts`
- `npm run test:run -- src/views/project-detail/useProjectDetailExports.spec.ts src/views/project-detail/useProjectDetailAlerts.spec.ts src/views/project-detail/projectDetailBootstrap.spec.ts src/views/project-detail/useProjectDetailAnalysis.spec.ts src/views/project-detail/useProjectDetailLifecycle.spec.ts`
- `npm run test:run -- src/components/document-viewer/useDocumentViewerExport.spec.ts src/components/document-viewer/useDocumentViewerPreferences.spec.ts src/components/document-viewer/useDocumentViewerData.spec.ts src/components/document-viewer/useDocumentViewerDialogues.spec.ts src/components/document-viewer/documentViewerText.spec.ts src/components/document-viewer/useDocumentViewerInteractions.spec.ts src/components/DocumentViewer.spec.ts`

Backend / scripts:

- `pytest tests/scripts/test_smoke_desktop_app.py -q`
- `pytest tests/unit/test_cr03_runtime_settings.py tests/unit/test_analysis_cache_roundtrip.py tests/unit/test_analysis_structure_helpers.py tests/unit/test_analysis_pipeline_dialogue.py tests/unit/test_temporal_entity_mentions_integration.py -q`
- `python -m compileall api-server/routers/_analysis_runtime.py api-server/routers/_analysis_cache_helpers.py api-server/routers/_analysis_structure_helpers.py src/narrative_assistant/pipelines/analysis_pipeline.py src/narrative_assistant/pipelines/analysis_pipeline_models.py src/narrative_assistant/pipelines/analysis_pipeline_temporal.py src/narrative_assistant/pipelines/analysis_pipeline_dialogue.py`

Comprobaciones de estructura:

- `rg -n "\\bfetch\\(" frontend/src --glob '!**/*.spec.ts' --glob '!**/*.test.ts'`
- `rg -n "\\b(alert|confirm|prompt)\\(" frontend/src --glob '!**/*.spec.ts' --glob '!**/*.test.ts'`
- `rg -n "console\\.(log|debug)\\(" frontend/src --glob '!**/*.spec.ts' --glob '!**/*.test.ts'`

Resultado:

- `type-check`: OK
- tests del bloque nuevo: OK
- `fetch()` directo de producto: 0
- dialogos nativos: 0
- `console.log/debug` de producto: 0

## 6. Veredicto

La deuda estructural inmediata de este bloque queda ampliamente cerrada.

Lo pendiente ya no es higiene basica ni soporte tecnico faltante, sino trabajo de siguiente escala:

- release testing final sobre artefactos empaquetados
- siguiente troceado de monolitos grandes
- cobertura desktop real de export/import
- politica transversal de logging de error
