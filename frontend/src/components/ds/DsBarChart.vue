<script setup lang="ts">
import { computed } from 'vue'

/**
 * DsBarChart - Componente de gráfico de barras del Design System
 *
 * Componente reutilizable para mostrar barras de datos con etiquetas y contadores.
 * Soporta barras simples o segmentadas con múltiples colores.
 *
 * @example
 * // Barra simple
 * <DsBarChart
 *   :items="[
 *     { label: 'Cap. 1', value: 15, max: 20, color: '#ef4444' },
 *     { label: 'Cap. 2', value: 8, max: 20, color: '#3b82f6' }
 *   ]"
 * />
 *
 * @example
 * // Barra segmentada
 * <DsBarChart
 *   :items="[{
 *     label: 'Cap. 1',
 *     value: 15,
 *     segments: [
 *       { value: 8, color: '#ef4444', label: 'Errores' },
 *       { value: 5, color: '#f59e0b', label: 'Warnings' },
 *       { value: 2, color: '#3b82f6', label: 'Info' }
 *     ]
 *   }]"
 * />
 */

export interface BarSegment {
  /** Valor del segmento */
  value: number
  /** Color del segmento (CSS color) */
  color: string
  /** Label para tooltip */
  label?: string
}

export interface BarChartItem {
  /** Etiqueta de la barra (mostrada a la izquierda) */
  label: string
  /** Valor total de la barra */
  value: number
  /** Valor máximo para calcular porcentaje (si no se especifica, usa max global) */
  max?: number
  /** Color de la barra (solo para barras simples) */
  color?: string
  /** Segmentos de la barra (para barras segmentadas) */
  segments?: BarSegment[]
  /** Tooltip personalizado (si no se especifica, usa label + value) */
  tooltip?: string
}

export type BarSize = 'compact' | 'normal' | 'prominent'

interface Props {
  /** Items a mostrar en el gráfico */
  items: BarChartItem[]
  /** Altura de las barras */
  size?: BarSize
  /** Ancho de la columna de etiquetas (en px) */
  labelWidth?: number
  /** Ancho de la columna de contadores (en px) */
  countWidth?: number
  /** Mostrar contador numérico a la derecha */
  showCount?: boolean
  /** Valor máximo global (si no se especifica, usa el máximo de los items) */
  maxValue?: number
  /** Color por defecto para barras sin color especificado */
  defaultColor?: string
}

const props = withDefaults(defineProps<Props>(), {
  size: 'normal',
  labelWidth: 120,
  countWidth: 40,
  showCount: true,
  defaultColor: 'var(--primary-color)'
})

/** Mapeo de tamaños a alturas en px */
const BAR_HEIGHTS: Record<BarSize, number> = {
  compact: 8,
  normal: 12,
  prominent: 16
}

/** Altura de la barra según el tamaño */
const barHeight = computed(() => `${BAR_HEIGHTS[props.size]}px`)

/** Máximo global para calcular porcentajes */
const globalMax = computed(() => {
  if (props.maxValue) return props.maxValue
  return Math.max(...props.items.map(item => item.max ?? item.value))
})

/** Calcula el porcentaje de una barra respecto al máximo */
function getBarPercentage(item: BarChartItem): number {
  const max = item.max ?? globalMax.value
  if (max === 0) return 0
  return Math.min((item.value / max) * 100, 100)
}

/** Calcula el porcentaje de un segmento respecto al total de la barra */
function getSegmentPercentage(segment: BarSegment, total: number): number {
  if (total === 0) return 0
  return (segment.value / total) * 100
}

/** Tooltip por defecto para un item */
function getTooltip(item: BarChartItem): string {
  if (item.tooltip) return item.tooltip
  return `${item.label}: ${item.value}`
}

/** Tooltip para un segmento */
function getSegmentTooltip(segment: BarSegment, item: BarChartItem): string {
  const label = segment.label || item.label
  return `${label}: ${segment.value}`
}
</script>

<template>
  <div class="ds-bar-chart">
    <div
      v-for="(item, index) in items"
      :key="index"
      class="chart-bar-wrapper"
      :style="{
        gridTemplateColumns: `${labelWidth}px 1fr ${showCount ? `${countWidth}px` : '0px'}`
      }"
    >
      <!-- Label -->
      <span
        class="bar-label"
        :title="getTooltip(item)"
      >
        {{ item.label }}
      </span>

      <!-- Track de la barra -->
      <div class="bar-track" :style="{ height: barHeight }">
        <!-- Barra segmentada -->
        <div
          v-if="item.segments && item.segments.length > 0"
          class="bar-fill-container"
          :style="{ width: `${Math.max(getBarPercentage(item), 1)}%` }"
        >
          <div
            v-for="(segment, segIndex) in item.segments"
            :key="segIndex"
            class="bar-segment"
            :style="{
              width: `${getSegmentPercentage(segment, item.value)}%`,
              backgroundColor: segment.color
            }"
            :title="getSegmentTooltip(segment, item)"
          ></div>
        </div>

        <!-- Barra simple -->
        <div
          v-else
          class="bar-fill-container"
          :style="{
            width: `${Math.max(getBarPercentage(item), 1)}%`,
            backgroundColor: item.color || defaultColor
          }"
          :title="getTooltip(item)"
        ></div>
      </div>

      <!-- Contador -->
      <span v-if="showCount" class="bar-count">{{ item.value }}</span>
    </div>
  </div>
</template>

<style scoped>
.ds-bar-chart {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.chart-bar-wrapper {
  display: grid;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.bar-label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.3;
  cursor: default;
}

.bar-track {
  background: var(--surface-100);
  border-radius: var(--border-radius);
  overflow: hidden;
  position: relative;
}

.bar-fill-container {
  height: 100%;
  display: flex;
  flex-direction: row;
  border-radius: inherit;
  transition: width 0.3s ease;
  min-width: 1px;
  overflow: hidden;
}

.bar-fill-container:hover {
  filter: brightness(1.1);
}

/* Segmentos individuales (para barras segmentadas) */
.bar-segment {
  height: 100%;
  transition: width 0.3s ease, background-color 0.3s ease;
  cursor: help;
  position: relative;
}

.bar-segment:hover {
  filter: brightness(1.15);
}

.bar-segment + .bar-segment {
  border-left: 1px solid rgba(255, 255, 255, 0.2);
}

.bar-count {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-color);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

/* Dark mode */
.dark .bar-track {
  background: var(--surface-700);
}

.dark .bar-segment + .bar-segment {
  border-left: 1px solid rgba(0, 0, 0, 0.3);
}
</style>
