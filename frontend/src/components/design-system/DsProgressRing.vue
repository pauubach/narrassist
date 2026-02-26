<template>
  <div class="ds-progress-ring" :class="{ 'ds-progress-ring--large': size === 'large' }">
    <svg
      :width="svgSize"
      :height="svgSize"
      :viewBox="`0 0 ${svgSize} ${svgSize}`"
      class="progress-svg"
    >
      <!-- Background circle -->
      <circle
        :cx="center"
        :cy="center"
        :r="radius"
        class="progress-bg"
        :stroke-width="strokeWidth"
        fill="none"
      />

      <!-- Progress circle -->
      <circle
        :cx="center"
        :cy="center"
        :r="radius"
        class="progress-bar"
        :class="progressClass"
        :stroke-width="strokeWidth"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="dashOffset"
        fill="none"
        stroke-linecap="round"
      />
    </svg>

    <!-- Center content -->
    <div class="progress-content">
      <div class="progress-value">{{ displayValue }}%</div>
      <div v-if="label" class="progress-label">{{ label }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export interface DsProgressRingProps {
  /** Valor del progreso (0-100) */
  value: number
  /** Tamaño del anillo */
  size?: 'normal' | 'large'
  /** Etiqueta debajo del porcentaje */
  label?: string
  /** Color del progreso: auto (basado en valor), primary, success, warning, danger */
  color?: 'auto' | 'primary' | 'success' | 'warning' | 'danger'
}

const props = withDefaults(defineProps<DsProgressRingProps>(), {
  size: 'normal',
  color: 'auto'
})

// Dimensiones según tamaño
const svgSize = computed(() => props.size === 'large' ? 160 : 120)
const strokeWidth = computed(() => props.size === 'large' ? 8 : 6)
const center = computed(() => svgSize.value / 2)
const radius = computed(() => (svgSize.value - strokeWidth.value) / 2)

// Cálculos del círculo
const circumference = computed(() => 2 * Math.PI * radius.value)
const dashOffset = computed(() => {
  const progress = Math.min(Math.max(props.value, 0), 100)
  return circumference.value - (progress / 100) * circumference.value
})

// Valor redondeado para mostrar
const displayValue = computed(() => Math.round(props.value))

// Color del progreso
const progressClass = computed(() => {
  if (props.color !== 'auto') {
    return `progress-${props.color}`
  }

  // Auto: basado en el valor
  if (props.value >= 80) return 'progress-success'
  if (props.value >= 50) return 'progress-primary'
  if (props.value >= 30) return 'progress-warning'
  return 'progress-danger'
})
</script>

<style scoped>
.ds-progress-ring {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.progress-svg {
  transform: rotate(-90deg);
}

.progress-bg {
  stroke: var(--surface-200);
  opacity: 0.3;
}

.progress-bar {
  transition: stroke-dashoffset 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.progress-primary {
  stroke: var(--primary-color);
}

.progress-success {
  stroke: var(--green-500);
}

.progress-warning {
  stroke: var(--orange-500);
}

.progress-danger {
  stroke: var(--red-500);
}

.progress-content {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  pointer-events: none;
}

.progress-value {
  font-size: 1.75rem;
  font-weight: 700;
  line-height: 1;
  color: var(--text-color);
  margin-bottom: 0.25rem;
}

.ds-progress-ring--large .progress-value {
  font-size: 2.5rem;
}

.progress-label {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.ds-progress-ring--large .progress-label {
  font-size: 0.875rem;
}

/* Dark mode */
@media (prefers-color-scheme: dark) {
  .progress-bg {
    stroke: var(--surface-600);
    opacity: 0.4;
  }
}
</style>
