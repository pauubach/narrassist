# Z-Index Audit - Narrative Assistant

**Fecha**: 2026-02-16
**Problema**: El buscador de texto se solapa con otros elementos. Múltiples componentes usan z-index hardcodeados.

## Design System Z-Index Scale

Definido en `frontend/src/assets/design-system/tokens.css` (líneas 365-375):

```css
--ds-z-dropdown: 1000;
--ds-z-sticky: 1020;
--ds-z-fixed: 1030;
--ds-z-modal-backdrop: 1040;
--ds-z-modal: 1050;
--ds-z-popover: 1060;
--ds-z-tooltip: 1070;
--ds-z-toast: 1080;
```

## Problemas Encontrados

### 🔴 CRÍTICO - Solapamientos ✅ RESUELTO

| Componente | Archivo | Línea | Z-Index Previo | Token Aplicado | Estado |
|------------|---------|-------|----------------|----------------|--------|
| `.find-bar` | `workspace/TextFindBar.vue` | 253 | `10` | `--ds-z-sticky` (1020) | ✅ |
| `.menu-dropdown` | `MenuBar.vue` | 441 | `--ds-z-sticky` (1020) | `--ds-z-dropdown` (1000) | ✅ |
| `.menubar` | `MenuBar.vue` | 402 | `--ds-z-dropdown` (1000) | `--ds-z-sticky` (1020) | ✅ |

### ⚠️ MEDIO - Hardcoded z-index (sin tokens) ✅ RESUELTO

| Componente | Archivo | Línea | Z-Index Previo | Token Aplicado | Estado |
|------------|---------|-------|----------------|----------------|--------|
| `.top-actions` | `views/HomeView.vue` | 184 | `10` | `--ds-z-fixed` (1030) | ✅ |
| `.not-executed-overlay` | `analysis/AnalysisRequired.vue` | 200 | `10` | `--ds-z-fixed` (1030) | ✅ |
| `.failed-overlay` | `analysis/AnalysisRequired.vue` | 294 | `10` | `--ds-z-fixed` (1030) | ✅ |
| `.running-overlay` | `analysis/AnalysisRequired.vue` | 323 | `20` | `--ds-z-modal-backdrop` (1040) | ✅ |
| `.entity-panel` | `RelationshipGraph.vue` | 2102 | `10` | `--ds-z-popover` (1060) | ✅ |
| `.panel-resizer` | `workspace/PanelResizer.vue` | 94 | `2` | `--ds-z-fixed` (1030) | ✅ |

### ✅ OK - Ya usan tokens correctamente

| Componente | Archivo | Token | Correcto |
|------------|---------|-------|----------|
| `.error-suggestion-popup` | `document/TextHighlighter.vue` | `--ds-z-tooltip` | ✅ |
| `DsTooltip` | `ds/DsTooltip.vue` | `--ds-z-tooltip` | ✅ |
| `DsLoadingState` | `ds/DsLoadingState.vue` | `--ds-z-modal` | ✅ |
| `StatusBar` dropdown | `layout/StatusBar.vue` | `--ds-z-dropdown` | ✅ |

### ℹ️ INFO - Casos especiales

| Componente | Archivo | Líneas | Z-Index | Razón |
|------------|---------|--------|---------|-------|
| Timeline vis.js overrides | `timeline/VisTimeline.vue` | 696-714 | `0, 1, 2, auto` | Override necesario para vis.js internals |
| ChapterTimeline markers | `shared/ChapterTimeline.vue` | 220, 237 | `1` | Dentro de contexto local, no global |
| MergeEntitiesDialog checkboxes | `MergeEntitiesDialog.vue` | 1445, 1453 | `1` | Fix de PrimeVue checkbox layering |

## Jerarquía Visual Correcta (de menor a mayor)

```
1. Contenido base (z-index: auto/0)
2. Panel resizers (--ds-z-fixed: 1030)
3. Sticky headers/toolbars (--ds-z-sticky: 1020)
4. Dropdowns/menus (--ds-z-dropdown: 1000)
5. Overlays de estado (--ds-z-fixed: 1030)
6. Modals y backdrops (--ds-z-modal-backdrop: 1040 / --ds-z-modal: 1050)
7. Popovers (--ds-z-popover: 1060)
8. Tooltips (--ds-z-tooltip: 1070)
9. Toasts/notificaciones (--ds-z-toast: 1080)
```

## Plan de Corrección ✅ COMPLETADO

### Fase 1: CRÍTICO - Menú y Buscador ✅
1. **MenuBar.vue**: ✅
   - `.menubar`: `z-index: var(--ds-z-sticky)` (era --ds-z-dropdown)
   - `.menu-dropdown`: `z-index: var(--ds-z-dropdown)` (era --ds-z-sticky)

2. **TextFindBar.vue**: ✅
   - `.find-bar`: `z-index: var(--ds-z-sticky)` (era 10)

### Fase 2: Normalización de Overlays ✅
3. **AnalysisRequired.vue**: ✅
   - `.not-executed-overlay`: `z-index: var(--ds-z-fixed)` (era 10)
   - `.failed-overlay`: `z-index: var(--ds-z-fixed)` (era 10)
   - `.running-overlay`: `z-index: var(--ds-z-modal-backdrop)` (era 20)

4. **HomeView.vue**: ✅
   - `.top-actions`: `z-index: var(--ds-z-fixed)` (era 10)

5. **RelationshipGraph.vue**: ✅
   - `.entity-panel`: `z-index: var(--ds-z-popover)` (era 10)

6. **PanelResizer.vue**: ✅
   - `.panel-resizer`: `z-index: var(--ds-z-fixed)` (era 2)

### Fase 3: Verificación
- [ ] Probar buscador (Ctrl/Cmd+F) sobre contenido
- [ ] Probar menús desplegables (File/Edit/View)
- [ ] Probar overlays de análisis
- [ ] Probar entity-panel en RelationshipGraph
- [ ] Probar tooltips sobre todos los elementos
- [ ] Probar modales sobre overlays
- [ ] Verificar en dark mode
- [ ] Probar panel resizer arrastrable

## Reglas de Oro para Z-Index

1. **NUNCA usar números mágicos** (10, 20, 100, 9999)
2. **SIEMPRE usar tokens del design system** (`--ds-z-*`)
3. **Los valores hardcoded solo se permiten para**:
   - Overrides de librerías de terceros (vis.js, PrimeVue)
   - Contextos locales dentro de un componente (stacking context aislado)
4. **Documentar excepciones** con comentarios explicativos
5. **Probar la jerarquía completa** antes de commitear

## Casos Especiales Documentados

### vis.js Timeline
- **Contexto**: La librería vis.js crea su propio stacking context
- **Solución**: Overrides necesarios con `!important` para controlar el orden interno
- **Archivo**: `timeline/VisTimeline.vue:696-714`

### PrimeVue Checkbox
- **Contexto**: Checkboxes en diálogos necesitan `z-index: 1` para aparecer sobre el fondo
- **Solución**: Override local con valor mínimo
- **Archivo**: `MergeEntitiesDialog.vue:1445,1453`

### ChapterTimeline Markers
- **Contexto**: Marcadores de línea temporal dentro de un contenedor local
- **Solución**: `z-index: 1` dentro del stacking context del componente
- **Archivo**: `shared/ChapterTimeline.vue:220,237`

## Testing Checklist

- [ ] Buscador de texto (Ctrl/Cmd+F) visible sobre todo el contenido
- [ ] Menú File/Edit/View se despliega bajo la barra pero sobre el contenido
- [ ] Overlay "Ejecuta el análisis" cubre todo el panel
- [ ] Overlay de progreso "Analizando..." cubre overlays de estado
- [ ] Tooltips aparecen sobre overlays
- [ ] Modales (MergeEntities, Settings) aparecen sobre todo
- [ ] Panel resizer arrastrable sobre contenido
- [ ] StatusBar dropdowns visibles
- [ ] Dark mode mantiene la jerarquía
