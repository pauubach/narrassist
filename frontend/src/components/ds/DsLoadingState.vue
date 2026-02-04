<script setup lang="ts">
import { computed } from 'vue'

/**
 * DsLoadingState - Estado de carga con spinner, progreso y mensaje.
 *
 * Uso:
 *   <DsLoadingState message="Analizando documento..." />
 *   <DsLoadingState :progress="65" message="Procesando capítulos..." />
 *   <DsLoadingState variant="inline" size="sm" />
 */

export interface Props {
  /** Mensaje a mostrar */
  message?: string
  /** Progreso (0-100), si se especifica muestra barra de progreso */
  progress?: number
  /** Tamaño */
  size?: 'sm' | 'md' | 'lg'
  /** Variante: fullscreen overlay, inline o subtle */
  variant?: 'overlay' | 'inline' | 'subtle'
}

const props = withDefaults(defineProps<Props>(), {
  size: 'md',
  variant: 'inline'
})

const classes = computed(() => [
  'ds-loading-state',
  `ds-loading-state--${props.size}`,
  `ds-loading-state--${props.variant}`
])

const showProgress = computed(() => typeof props.progress === 'number')
</script>

<template>
  <div :class="classes">
    <div class="ds-loading-state__content">
      <div v-if="!showProgress" class="ds-loading-state__spinner">
        <svg viewBox="0 0 50 50" class="ds-loading-state__spinner-svg">
          <circle
            cx="25"
            cy="25"
            r="20"
            fill="none"
            stroke="currentColor"
            stroke-width="4"
            stroke-linecap="round"
          />
        </svg>
      </div>

      <div v-else class="ds-loading-state__progress">
        <div class="ds-loading-state__progress-track">
          <div
            class="ds-loading-state__progress-fill"
            :style="{ width: `${Math.min(100, Math.max(0, progress || 0))}%` }"
          />
        </div>
        <span class="ds-loading-state__progress-text">{{ progress }}%</span>
      </div>

      <p v-if="message" class="ds-loading-state__message">{{ message }}</p>
    </div>
  </div>
</template>

<style scoped>
.ds-loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Variants */
.ds-loading-state--overlay {
  position: fixed;
  inset: 0;
  background-color: color-mix(in srgb, var(--ds-surface-ground) 90%, transparent);
  backdrop-filter: blur(2px);
  z-index: var(--ds-z-modal);
}

.ds-loading-state--inline {
  padding: var(--ds-space-8);
  width: 100%;
}

.ds-loading-state--subtle {
  padding: var(--ds-space-2);
}

/* Content */
.ds-loading-state__content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--ds-space-4);
}

.ds-loading-state--subtle .ds-loading-state__content {
  flex-direction: row;
  gap: var(--ds-space-2);
}

/* Spinner */
.ds-loading-state__spinner {
  display: flex;
  align-items: center;
  justify-content: center;
}

.ds-loading-state__spinner-svg {
  animation: ds-spin 1s linear infinite;
  color: var(--ds-color-primary);
}

.ds-loading-state--sm .ds-loading-state__spinner-svg {
  width: 24px;
  height: 24px;
}

.ds-loading-state--md .ds-loading-state__spinner-svg {
  width: 40px;
  height: 40px;
}

.ds-loading-state--lg .ds-loading-state__spinner-svg {
  width: 56px;
  height: 56px;
}

.ds-loading-state__spinner-svg circle {
  stroke-dasharray: 90, 150;
  stroke-dashoffset: 0;
}

@keyframes ds-spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

/* Progress */
.ds-loading-state__progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--ds-space-2);
  width: 100%;
  max-width: 200px;
}

.ds-loading-state--lg .ds-loading-state__progress {
  max-width: 300px;
}

.ds-loading-state__progress-track {
  width: 100%;
  height: 8px;
  background-color: var(--ds-surface-border);
  border-radius: var(--ds-radius-full);
  overflow: hidden;
}

.ds-loading-state--sm .ds-loading-state__progress-track {
  height: 4px;
}

.ds-loading-state__progress-fill {
  height: 100%;
  background-color: var(--ds-color-primary);
  border-radius: var(--ds-radius-full);
  transition: width var(--ds-transition-base);
}

.ds-loading-state__progress-text {
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-medium);
  color: var(--ds-color-text-secondary);
}

/* Message */
.ds-loading-state__message {
  margin: 0;
  color: var(--ds-color-text-secondary);
  text-align: center;
}

.ds-loading-state--sm .ds-loading-state__message {
  font-size: var(--ds-font-size-sm);
}

.ds-loading-state--md .ds-loading-state__message {
  font-size: var(--ds-font-size-base);
}

.ds-loading-state--lg .ds-loading-state__message {
  font-size: var(--ds-font-size-lg);
}

.ds-loading-state--subtle .ds-loading-state__message {
  font-size: var(--ds-font-size-sm);
}
</style>
