<script setup lang="ts">
import DsBarChart, { type BarChartItem } from './DsBarChart.vue'

/**
 * DsBarChart Demo
 *
 * Muestra todas las variantes y casos de uso del componente DsBarChart.
 * Usar este archivo como referencia y para testing visual.
 */

// Ejemplo 1: Barras simples con diferentes colores
const simpleItems: BarChartItem[] = [
  { label: 'Capítulo 1', value: 15, color: '#ef4444', tooltip: 'Capítulo 1: 15 alertas' },
  { label: 'Capítulo 2', value: 22, color: '#f59e0b', tooltip: 'Capítulo 2: 22 alertas' },
  { label: 'Capítulo 3', value: 8, color: '#3b82f6', tooltip: 'Capítulo 3: 8 alertas' },
  { label: 'Capítulo 4', value: 12, color: '#8b5cf6', tooltip: 'Capítulo 4: 12 alertas' }
]

// Ejemplo 2: Barras segmentadas (meta-categorías)
const segmentedItems: BarChartItem[] = [
  {
    label: '1. La Llegada',
    value: 15,
    segments: [
      { value: 8, color: '#dc2626', label: 'Errores' },
      { value: 5, color: '#fb923c', label: 'Inconsistencias' },
      { value: 2, color: '#fde047', label: 'Calidad' }
    ]
  },
  {
    label: '2. El Encuentro',
    value: 22,
    segments: [
      { value: 12, color: '#dc2626', label: 'Errores' },
      { value: 7, color: '#fb923c', label: 'Inconsistencias' },
      { value: 3, color: '#5eead4', label: 'Sugerencias' }
    ]
  },
  {
    label: '3. La Revelación',
    value: 18,
    segments: [
      { value: 6, color: '#dc2626', label: 'Errores' },
      { value: 8, color: '#fb923c', label: 'Inconsistencias' },
      { value: 4, color: '#fde047', label: 'Calidad' }
    ]
  }
]

// Ejemplo 3: Top categorías (barras simples con colores por meta-categoría)
const categoryItems: BarChartItem[] = [
  { label: 'Gramática', value: 45, color: '#dc2626' },
  { label: 'Atributos', value: 38, color: '#fb923c' },
  { label: 'Repetición', value: 24, color: '#fde047' },
  { label: 'Estructura', value: 12, color: '#5eead4' },
  { label: 'Puntuación', value: 8, color: '#dc2626' }
]

// Ejemplo 4: Barras compactas (para espacios reducidos)
const compactItems: BarChartItem[] = [
  { label: 'Crítico', value: 3, color: '#dc2626' },
  { label: 'Alto', value: 12, color: '#f59e0b' },
  { label: 'Medio', value: 28, color: '#fde047' },
  { label: 'Bajo', value: 45, color: '#3b82f6' }
]

// Ejemplo 5: Sin colores específicos (usa color del tema)
const themeColorItems: BarChartItem[] = [
  { label: 'el', value: 245 },
  { label: 'de', value: 189 },
  { label: 'que', value: 156 },
  { label: 'la', value: 142 },
  { label: 'en', value: 98 }
]
</script>

<template>
  <div class="demo-container">
    <h1>DsBarChart - Ejemplos y Variantes</h1>

    <!-- Tamaños -->
    <section class="demo-section">
      <h2>Tamaños (Sizes)</h2>

      <div class="size-example">
        <h3>Compact (8px)</h3>
        <DsBarChart :items="compactItems" size="compact" />
      </div>

      <div class="size-example">
        <h3>Normal (12px) - Default</h3>
        <DsBarChart :items="compactItems" size="normal" />
      </div>

      <div class="size-example">
        <h3>Prominent (16px)</h3>
        <DsBarChart :items="compactItems" size="prominent" />
      </div>
    </section>

    <!-- Barras simples -->
    <section class="demo-section">
      <h2>Barras Simples</h2>
      <p class="description">
        Cada barra tiene un color único. Ideal para categorías independientes.
      </p>
      <DsBarChart :items="simpleItems" size="normal" />
    </section>

    <!-- Barras segmentadas -->
    <section class="demo-section">
      <h2>Barras Segmentadas</h2>
      <p class="description">
        Cada barra se divide en segmentos de colores. Ideal para mostrar composición.
      </p>
      <DsBarChart :items="segmentedItems" size="prominent" />
    </section>

    <!-- Top categorías -->
    <section class="demo-section">
      <h2>Top Categorías</h2>
      <p class="description">
        Barras ordenadas por valor con colores consistentes por meta-categoría.
      </p>
      <DsBarChart :items="categoryItems" size="normal" />
    </section>

    <!-- Color del tema por defecto -->
    <section class="demo-section">
      <h2>Color del Tema (Por Defecto)</h2>
      <p class="description">
        Sin especificar <code>color</code>, las barras usan automáticamente
        <code>var(--primary-color)</code> del tema activo. Ideal para datos
        sin clasificación semántica (ej: palabras más usadas, capítulos más largos).
      </p>
      <DsBarChart :items="themeColorItems" size="normal" />
    </section>

    <!-- Sin contador -->
    <section class="demo-section">
      <h2>Sin Contador</h2>
      <p class="description">
        Ocultar la columna de contadores con <code>:show-count="false"</code>.
      </p>
      <DsBarChart :items="simpleItems" :show-count="false" />
    </section>

    <!-- Ancho personalizado -->
    <section class="demo-section">
      <h2>Anchos Personalizados</h2>
      <p class="description">
        Ajustar ancho de etiquetas y contadores con <code>label-width</code> y <code>count-width</code>.
      </p>
      <DsBarChart
        :items="categoryItems"
        :label-width="180"
        :count-width="50"
      />
    </section>

    <!-- Dark mode preview -->
    <section class="demo-section dark-preview">
      <h2>Vista Previa Dark Mode</h2>
      <div class="dark">
        <div style="background: var(--surface-900); padding: 1rem; border-radius: 8px;">
          <DsBarChart :items="segmentedItems" size="prominent" />
        </div>
      </div>
    </section>

    <!-- Código de ejemplo -->
    <section class="demo-section">
      <h2>Código de Ejemplo</h2>
      <pre><code>&lt;script setup&gt;
import DsBarChart from '@/components/ds/DsBarChart.vue'

const items = [
  {
    label: 'Cap. 1',
    value: 15,
    segments: [
      { value: 8, color: '#dc2626', label: 'Errores' },
      { value: 5, color: '#fb923c', label: 'Warnings' },
      { value: 2, color: '#3b82f6', label: 'Info' }
    ]
  }
]
&lt;/script&gt;

&lt;template&gt;
  &lt;DsBarChart :items="items" size="prominent" /&gt;
&lt;/template&gt;</code></pre>
    </section>
  </div>
</template>

<style scoped>
.demo-container {
  max-width: 1000px;
  margin: 2rem auto;
  padding: 2rem;
  font-family: var(--font-family);
}

h1 {
  margin-bottom: 2rem;
  color: var(--text-color);
  font-size: 2rem;
}

h2 {
  margin-top: 3rem;
  margin-bottom: 0.75rem;
  color: var(--text-color);
  font-size: 1.5rem;
  border-bottom: 2px solid var(--surface-border);
  padding-bottom: 0.5rem;
}

h3 {
  margin-top: 1.5rem;
  margin-bottom: 0.5rem;
  color: var(--text-color);
  font-size: 1rem;
  font-weight: 600;
}

.demo-section {
  margin-bottom: 3rem;
}

.description {
  color: var(--text-color-secondary);
  margin-bottom: 1rem;
  font-size: 0.95rem;
}

.size-example {
  margin-bottom: 2rem;
}

.dark-preview {
  background: var(--surface-50);
  padding: 1.5rem;
  border-radius: var(--border-radius);
}

pre {
  background: var(--surface-100);
  padding: 1rem;
  border-radius: var(--border-radius);
  overflow-x: auto;
  font-size: 0.85rem;
  line-height: 1.5;
}

code {
  font-family: 'Courier New', monospace;
  color: var(--text-color);
}
</style>
