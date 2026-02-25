# Estándares Visuales - Narrative Assistant

Guía de estandarización visual para mantener consistencia en toda la aplicación.

## 📊 Componentes de Visualización

### DsBarChart

Componente reutilizable para gráficos de barras.

#### Uso Básico

```vue
<script setup>
import DsBarChart from '@/components/ds/DsBarChart.vue'

const items = [
  { label: 'Cap. 1', value: 15, color: '#ef4444' },
  { label: 'Cap. 2', value: 8, color: '#3b82f6' }
]
</script>

<template>
  <DsBarChart :items="items" size="normal" />
</template>
```

#### Barras con Color del Tema (Recomendado por defecto)

```vue
// SIN colores específicos - usa el color primario del tema
const items = [
  { label: 'el', value: 245 },
  { label: 'de', value: 189 },
  { label: 'que', value: 156 }
]
```

**Cuándo usar**: Datos sin clasificación semántica (palabras frecuentes, capítulos más largos, etc.)

#### Barras con Colores Específicos

```vue
// CON colores - solo cuando hay clasificación semántica
const items = [
  { label: 'Errores', value: 45, color: '#dc2626' },
  { label: 'Warnings', value: 28, color: '#f59e0b' },
  { label: 'Info', value: 12, color: '#3b82f6' }
]
```

**Cuándo usar**: Severidades, categorías, estados (donde el color comunica significado)

#### Barras Segmentadas

```vue
const items = [{
  label: 'Cap. 1',
  value: 15,
  segments: [
    { value: 8, color: '#ef4444', label: 'Errores' },
    { value: 5, color: '#f59e0b', label: 'Warnings' },
    { value: 2, color: '#3b82f6', label: 'Info' }
  ]
}]
```

**Cuándo usar**: Mostrar composición de un total (tipos de alertas por capítulo, etc.)

#### Tamaños

| Size | Altura | Uso Recomendado |
|------|--------|-----------------|
| `compact` | 8px | Gráficos secundarios, sparklines |
| `normal` | 12px | Gráficos estándar, dashboards |
| `prominent` | 16px | Gráficos principales, énfasis visual |

#### Props

```typescript
interface BarChartItem {
  label: string          // Etiqueta mostrada a la izquierda
  value: number         // Valor total de la barra
  max?: number          // Máximo para calcular porcentaje
  color?: string        // Color (solo barras simples)
  segments?: BarSegment[] // Segmentos (barras segmentadas)
  tooltip?: string      // Tooltip personalizado
}

interface BarSegment {
  value: number
  color: string
  label?: string
}

interface Props {
  items: BarChartItem[]
  size?: 'compact' | 'normal' | 'prominent'
  labelWidth?: number     // Default: 120px
  countWidth?: number     // Default: 40px
  showCount?: boolean     // Default: true
  maxValue?: number       // Máximo global
  defaultColor?: string   // Color por defecto
}
```

---

## 🎨 Paleta de Colores para Meta-Categorías

Usar los colores definidos en `META_CATEGORIES` (de `useAlertUtils.ts`):

```typescript
{
  errors: {
    color: 'var(--p-red-600, #dc2626)',
    bgColor: 'var(--p-red-50, #fef2f2)',
  },
  inconsistencies: {
    color: 'var(--p-orange-400, #fb923c)',
    bgColor: 'var(--p-orange-50, #fff7ed)',
  },
  quality: {
    color: 'var(--p-yellow-300, #fde047)',
    bgColor: 'var(--p-yellow-50, #fefce8)',
  },
  suggestions: {
    color: 'var(--p-teal-300, #5eead4)',
    bgColor: 'var(--p-teal-50, #f0fdfa)',
  }
}
```

---

## 📐 Grid Layouts Estándar

### Barras con Label + Valor

```css
grid-template-columns: 120px 1fr 40px;
```

- **120px**: Etiqueta (texto truncado con ellipsis)
- **1fr**: Barra (ancho flexible)
- **40px**: Contador numérico (alineado a la derecha)

### Tarjetas de Stats

```css
display: grid;
grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
gap: var(--ds-space-3);
```

---

## 🔲 Bordes Coloreados

Para indicar severidad o categoría:

```css
border-left: 3px solid var(--color);
```

Ejemplos:
- **Crítico**: `#dc2626` (rojo)
- **Alto**: `#f59e0b` (naranja)
- **Medio**: `#fde047` (amarillo)
- **Bajo**: `#3b82f6` (azul)
- **Info**: `#5eead4` (teal)

---

## 📈 Alturas Estandarizadas

| Elemento | Altura | Uso |
|----------|--------|-----|
| Barra compact | 8px | Gráficos secundarios |
| Barra normal | 12px | Gráficos estándar |
| Barra prominent | 16px | Gráficos principales |
| Progress bar | 8px | Indicadores de progreso |
| Gauge stroke | 4px | Círculos de puntuación |
| Tag/Badge | 20px | Etiquetas inline |
| Button small | 28px | Botones compactos |
| Button normal | 36px | Botones estándar |

---

## 🎯 Transiciones

```css
/* Estándar para barras */
transition: width 0.3s ease;

/* Hover effects */
.bar:hover {
  filter: brightness(1.1);
}

/* Segmentos */
.segment:hover {
  filter: brightness(1.15);
}
```

---

## 🌙 Dark Mode

Siempre definir variantes para dark mode:

```css
/* Light mode */
.bar-track {
  background: var(--surface-100);
}

/* Dark mode */
.dark .bar-track {
  background: var(--surface-700);
}
```

---

## 📝 Tipografía para Visualizaciones

```css
/* Labels */
font-size: 0.75rem;
color: var(--text-color-secondary);
line-height: 1.3;

/* Valores grandes */
font-size: 1.75rem;
font-weight: 800;
color: var(--text-color);

/* Contadores */
font-size: 0.75rem;
font-weight: 600;
font-variant-numeric: tabular-nums; /* Números monoespaciados */
```

---

## ✅ Componentes a Migrar

### Alta Prioridad

- [x] **AlertsAnalytics.vue** - ✅ Ya usa DsBarChart
- [ ] **PacingAnalysisTab.vue** - Barras de narración/diálogo
- [ ] **MethodVotingBar.vue** - Barras de consenso de métodos

### Media Prioridad

- [ ] **EventDensityStrip.vue** - Considerar extraer lógica reutilizable
- [ ] **NarrativeHealthTab.vue** - Crear DsGauge para círculos
- [ ] **ChapterProgressTab.vue** - Usar DsBarChart para progress

### Baja Prioridad

- [ ] **VersionSparkline.vue** - Ya es bastante genérico
- [ ] **DsDownloadProgress.vue** - Considerar unificar con DsBarChart

---

## 🚀 Mejores Prácticas

1. **Usar componentes del Design System** siempre que sea posible
2. **No duplicar CSS** - extraer a componentes reutilizables
3. **Variables CSS** para colores, no valores hardcoded
4. **Grid layouts** para alineación consistente
5. **Tooltips** en elementos interactivos
6. **Transiciones suaves** (0.3s ease)
7. **Dark mode** como ciudadano de primera clase
8. **Accesibilidad**: cursor: help, títulos descriptivos

---

## 📚 Referencias

- [DsBarChart.vue](../src/components/ds/DsBarChart.vue) - Componente principal
- [AlertsAnalytics.vue](../src/components/alerts/AlertsAnalytics.vue) - Ejemplo de uso
- [useAlertUtils.ts](../src/composables/useAlertUtils.ts) - Colores de meta-categorías
- [PrimeVue Theming](https://primevue.org/theming/) - Variables CSS disponibles

---

**Última actualización**: 2026-02-25
**Mantenedor**: Design System Team
