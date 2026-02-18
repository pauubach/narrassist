# ADR-005: PrimeVue para Componentes de UI

## Estado

**Aceptada** — 2026-01-10 (v0.2.0)

## Contexto

El frontend requiere una biblioteca de componentes UI que:
1. **Accesibilidad**: WCAG 2.1 AA compliant (target: correctores, no developers)
2. **Temas**: Dark mode + light mode
3. **Componentes complejos**: DataTable, Tree, Timeline, Charts
4. **Español**: i18n nativo
5. **Performance**: Tree-shakeable, lazy-loading
6. **Desktop-friendly**: Funcione bien en Tauri (no solo web)

Alternativas consideradas:

| Biblioteca | Componentes | A11y | Temas | i18n | Bundle Size | Licencia |
|------------|-------------|------|-------|------|-------------|----------|
| **PrimeVue** | 90+ | ✅ WCAG | ✅ Material/Lara | ✅ | ~200 KB | MIT |
| **Vuetify** | 80+ | ✅ WCAG | ✅ Material | ✅ | ~300 KB | MIT |
| **Element Plus** | 60+ | ⚠️ Parcial | ✅ | ✅ | ~250 KB | MIT |
| **Ant Design Vue** | 60+ | ⚠️ Parcial | ✅ | ✅ | ~280 KB | MIT |
| **Quasar** | 70+ | ✅ WCAG | ✅ Material | ✅ | ~220 KB | MIT |
| **Headless UI** | 15 | ✅ WCAG | ❌ DIY | ❌ | ~50 KB | MIT |

**Evaluación detallada**:

### PrimeVue ✅
- **Pros**: 90+ componentes, DataTable muy potente, Timeline/Charts incluidos, WCAG compliant, temas Material/Lara/custom
- **Cons**: API verbosa, estilos menos "modernos" que Vuetify

### Vuetify ⚠️
- **Pros**: Material Design limpio, muy popular (38k stars)
- **Cons**: Bundle size mayor, dependencia fuerte de Material (difícil customizar)

### Element Plus ❌
- **Pros**: Componentes limpios, usado en producción por Alibaba
- **Cons**: Accesibilidad incompleta, diseño muy "enterprise" (no editorial)

### Quasar ⚠️
- **Pros**: Completo, incluye SSR/PWA/mobile
- **Cons**: Opinionated (estructura de proyecto específica), overkill para Tauri

### Headless UI ❌
- **Pros**: Máxima flexibilidad, muy ligero
- **Cons**: Requiere implementar todos los estilos desde cero (400+ horas)

## Decisión

Usar **PrimeVue 4.x** con tema **Lara Light/Dark** (Material Design).

**Justificación**:
1. **DataTable**: Necesario para Alerts (filtrado, sorting, paginación)
2. **Timeline**: Componente `vis-timeline` se integra fácilmente
3. **Tree**: Para estructura de capítulos
4. **Charts**: `primevue/chart` wrapper de Chart.js
5. **A11y**: WCAG 2.1 AA out-of-the-box
6. **Temas**: Lara theme con CSS variables → fácil customización

**Configuración**:
```typescript
// main.ts
import PrimeVue from 'primevue/config';
import Lara from '@primevue/themes/lara';

app.use(PrimeVue, {
  theme: {
    preset: Lara,
    options: {
      darkModeSelector: '.dark-mode',  // toggle manual
    },
  },
  locale: {
    // Traducciones español
    startsWith: 'Empieza con',
    contains: 'Contiene',
    // ... ~50 strings
  },
});
```

**Componentes principales usados**:

| Componente | Uso | Archivo |
|------------|-----|---------|
| **DataTable** | Lista de alertas con filtros | `AlertsDashboard.vue` |
| **Tree** | Estructura de capítulos | `ChapterTree.vue` |
| **TabView** | Navegación principal | `ProjectView.vue` |
| **Dialog** | Modales (fusionar entidades, settings) | `EntityMergeDialog.vue` |
| **Dropdown/MultiSelect** | Filtros de alertas | `AlertsDashboard.vue` |
| **Accordion** | Inspección de capítulos | `ChapterInspector.vue` |
| **Badge** | Tags de entidades, severidad | `EntityBadge.vue`, `AlertBadge.vue` |
| **Chart** | Gráficos de métricas | `MetricsPanel.vue` |

**Integración con vis.js**:
- **vis-network**: Grafo de relaciones (no hay componente PrimeVue equivalente)
- **vis-timeline**: Línea temporal de eventos (PrimeVue Timeline es solo UI estática)

**Design System custom**:
- CSS variables en `frontend/src/styles/design-tokens.css`
- Tokens semánticos: `--ds-text-primary`, `--ds-bg-surface`, etc.
- Override de colores PrimeVue para consistencia

## Consecuencias

### Positivas ✅

1. **Productividad**: 90+ componentes listos → -300 horas de desarrollo
2. **Accesibilidad**: WCAG AA out-of-the-box (keyboard nav, ARIA, focus management)
3. **Consistencia**: Diseño uniforme en toda la app
4. **Mantenimiento**: PrimeVue actualizado activamente (10k+ commits, 600+ contributors)
5. **Performance**: Tree-shaking reduce bundle a ~200 KB (solo componentes usados)
6. **Documentación**: Docs excelentes con ejemplos interactivos
7. **Customización**: CSS variables permiten theming sin recompilar

### Negativas ⚠️

1. **Bundle size**: +200 KB (mitigado con tree-shaking)
2. **API verbosa**: Componentes con muchos props (ej: DataTable tiene 100+ props)
3. **Estilo enterprise**: Diseño menos "moderno" que Vuetify (ajustado con custom CSS)
4. **Dependencia externa**: Cambiar a otra lib requeriría reescribir ~30 componentes
5. **Curva de aprendizaje**: DataTable/Tree tienen APIs complejas

### Mitigaciones

- **Tree-shaking**: Vite elimina componentes no usados
- **Lazy loading**: Componentes pesados (Chart, DataTable) con dynamic imports
- **Custom design tokens**: `design-tokens.css` centraliza colores → fácil migrar si es necesario
- **Wrapper components**: `DsDataTable.vue`, `DsDialog.vue` abstraen PrimeVue → facilita futura migración

## Notas de Implementación

Ver:
- `frontend/src/main.ts` — configuración de PrimeVue + i18n español
- `frontend/src/styles/design-tokens.css` — tokens de diseño custom
- `frontend/src/components/ds/` — wrappers de componentes PrimeVue
- `frontend/src/composables/usePrimeVueLocale.ts` — traducciones dinámicas

**Componentes custom creados**:
- `DsLoadingState.vue` — skeleton screens con PrimeVue Skeleton
- `DsDownloadProgress.vue` — barra de descarga de modelos
- `DsErrorBoundary.vue` — error boundaries con PrimeVue Message
- `DsDataTable.vue` — wrapper de DataTable con defaults del proyecto

**Migración de componentes custom a PrimeVue**:
- **Antes (v0.1.0)**: Componentes escritos desde cero con Tailwind
- **Después (v0.2.0)**: Migrados a PrimeVue + Tailwind utility classes

**Temas**:
- **Lara Light**: Default
- **Lara Dark**: Toggle con clase `.dark-mode` en `<html>`
- **Custom theme**: Extendido con `design-tokens.css` para colores de marca

## Alternativa Futura

Si PrimeVue se vuelve problema (bundle size, performance):
- **Headless UI + shadcn-vue**: Componentes headless + estilos custom
- **Estimación**: 200 horas de migración (30 componentes × 6-7h cada uno)
- **Beneficio**: -150 KB bundle, máxima flexibilidad

Por ahora, PrimeVue es la mejor opción para el contexto del proyecto.

## Referencias

- [PrimeVue](https://primevue.org/) — Documentación oficial
- [WCAG 2.1 AA](https://www.w3.org/WAI/WCAG21/quickref/) — Guidelines de accesibilidad
- [Lara Theme](https://primevue.org/theming/#lara) — Tema Material Design de PrimeVue
- [vis.js](https://visjs.org/) — Grafos y timelines interactivos
- Adoptado en v0.2.0, migración completa en v0.3.0
