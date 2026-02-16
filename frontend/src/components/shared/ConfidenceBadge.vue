<template>
  <component :is="componentTag" :class="badgeClasses" :style="badgeStyle">
    <!-- Badge variant -->
    <template v-if="variant === 'badge'">
      <i v-if="showIcon" :class="iconClass"></i>
      <span class="confidence-value">{{ formattedValue }}</span>
      <span v-if="showLabel" class="confidence-label">{{ label }}</span>
    </template>

    <!-- Bar variant -->
    <template v-else-if="variant === 'bar'">
      <div class="bar-container">
        <div class="bar-fill" :style="barStyle"></div>
      </div>
      <span v-if="showValue" class="bar-value">{{ formattedValue }}</span>
    </template>

    <!-- Dot variant -->
    <template v-else-if="variant === 'dot'">
      <span class="dot" :style="dotStyle"></span>
      <span v-if="showValue" class="dot-value">{{ formattedValue }}</span>
    </template>
  </component>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type ConfidenceVariant = 'badge' | 'bar' | 'dot'
type ConfidenceSize = 'sm' | 'md' | 'lg'
type ConfidenceLevel = 'high' | 'medium' | 'low'

interface Props {
  /** Confidence value between 0 and 1 */
  value: number
  /** Display variant */
  variant?: ConfidenceVariant
  /** Size of the component */
  size?: ConfidenceSize
  /** Show icon in badge variant */
  showIcon?: boolean
  /** Show label text */
  showLabel?: boolean
  /** Show numeric value */
  showValue?: boolean
  /** Custom label */
  label?: string
  /** Render as span instead of div */
  inline?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'badge',
  size: 'md',
  showIcon: true,
  showLabel: false,
  showValue: true,
  label: 'confianza',
  inline: false
})

// Computed confidence level
const confidenceLevel = computed<ConfidenceLevel>(() => {
  if (props.value >= 0.7) return 'high'
  if (props.value >= 0.5) return 'medium'
  return 'low'
})

// Component tag (div or span)
const componentTag = computed(() => props.inline ? 'span' : 'div')

// Formatted percentage value
const formattedValue = computed(() => {
  return `${Math.round(props.value * 100)}%`
})

// Color based on confidence level - WCAG AA: usar tokens semánticos con fallbacks
const confidenceColor = computed(() => {
  switch (confidenceLevel.value) {
    case 'high': return 'var(--app-success-text, var(--p-green-700, #15803d))'
    case 'medium': return 'var(--app-warning-text, var(--p-yellow-700, #a16207))'
    case 'low':
    default: return 'var(--app-danger-text, var(--p-red-700, #b91c1c))'
  }
})

const confidenceBgColor = computed(() => {
  switch (confidenceLevel.value) {
    case 'high': return 'var(--app-success-bg, var(--p-green-50, #f0fdf4))'
    case 'medium': return 'var(--app-warning-bg, var(--p-yellow-50, #fefce8))'
    case 'low':
    default: return 'var(--app-danger-bg, var(--p-red-50, #fef2f2))'
  }
})

// Icon based on confidence level
const iconClass = computed(() => {
  switch (confidenceLevel.value) {
    case 'high': return 'pi pi-check-circle'
    case 'medium': return 'pi pi-exclamation-circle'
    case 'low':
    default: return 'pi pi-times-circle'
  }
})

// Classes
const badgeClasses = computed(() => [
  'confidence-badge',
  `variant-${props.variant}`,
  `size-${props.size}`,
  `level-${confidenceLevel.value}`
])

// Styles
const badgeStyle = computed(() => {
  if (props.variant === 'badge') {
    return {
      backgroundColor: confidenceBgColor.value,
      color: confidenceColor.value,
      borderColor: confidenceColor.value
    }
  }
  return {}
})

const barStyle = computed(() => ({
  width: `${props.value * 100}%`,
  backgroundColor: confidenceColor.value
}))

const dotStyle = computed(() => ({
  backgroundColor: confidenceColor.value
}))
</script>

<style scoped>
.confidence-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

/* Badge variant */
.variant-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 9999px;
  border: 1px solid;
  font-weight: 500;
}

.variant-badge.size-sm {
  font-size: 0.7rem;
  padding: 0.125rem 0.375rem;
}

.variant-badge.size-md {
  font-size: 0.8rem;
  padding: 0.25rem 0.5rem;
}

.variant-badge.size-lg {
  font-size: 0.9rem;
  padding: 0.375rem 0.625rem;
}

.variant-badge i {
  font-size: 0.875em;
}

.confidence-label {
  font-weight: 400;
  opacity: 0.8;
  margin-left: 0.125rem;
}

/* Bar variant */
.variant-bar {
  gap: 0.5rem;
}

.bar-container {
  flex: 1;
  height: 6px;
  background: var(--surface-200);
  border-radius: var(--app-radius-sm);
  overflow: hidden;
  min-width: 60px;
}

.variant-bar.size-sm .bar-container {
  height: 4px;
  min-width: 40px;
}

.variant-bar.size-lg .bar-container {
  height: 8px;
  min-width: 80px;
}

.bar-fill {
  height: 100%;
  border-radius: var(--app-radius-sm);
  transition: width 0.3s ease;
}

.bar-value {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  min-width: 2.5rem;
  text-align: right;
}

.variant-bar.size-sm .bar-value {
  font-size: 0.7rem;
}

.variant-bar.size-lg .bar-value {
  font-size: 0.85rem;
}

/* Dot variant */
.variant-dot {
  gap: 0.375rem;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.variant-dot.size-sm .dot {
  width: 6px;
  height: 6px;
}

.variant-dot.size-lg .dot {
  width: 10px;
  height: 10px;
}

.dot-value {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

.variant-dot.size-sm .dot-value {
  font-size: 0.7rem;
}

.variant-dot.size-lg .dot-value {
  font-size: 0.9rem;
}
</style>
