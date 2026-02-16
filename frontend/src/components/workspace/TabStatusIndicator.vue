<script lang="ts">
export type TabStatus = 'idle' | 'pending' | 'running' | 'partial' | 'completed' | 'failed'
</script>

<script setup lang="ts">
/**
 * TabStatusIndicator - Indicador de estado para tabs del workspace.
 *
 * Muestra un dot animado (running), check (completed), count (alerts),
 * o icono de error (failed) segun el estado de la fase asociada al tab.
 */
import { computed } from 'vue'

const props = defineProps<{
  /** Estado de la fase asociada al tab */
  status: TabStatus
  /** Conteo numérico para mostrar en badge (alertas, entidades) */
  count?: number
  /** Si el conteo es de alertas sin resolver (true = warning, false = success) */
  isWarning?: boolean
}>()

const showDot = computed(() => props.status === 'running')
const showPartial = computed(() => props.status === 'partial')
const showCheck = computed(() => props.status === 'completed' && !props.count)
const showFailed = computed(() => props.status === 'failed')
const showCount = computed(() => props.count !== undefined && props.count > 0)

const countLabel = computed(() => {
  if (!props.count) return ''
  return props.count > 99 ? '99+' : String(props.count)
})

const badgeClass = computed(() => {
  if (props.isWarning) return 'tab-status__count--warning'
  return 'tab-status__count--primary'
})
</script>

<template>
  <span class="tab-status" aria-hidden="true">
    <!-- Dot animado: fase en ejecucion -->
    <span v-if="showDot" class="tab-status__dot tab-status__dot--running" />

    <!-- Partial: datos disponibles pero incompletos -->
    <span v-else-if="showPartial" class="tab-status__dot tab-status__dot--partial" />

    <!-- Check: fase completada sin conteo -->
    <i v-else-if="showCheck" class="pi pi-check tab-status__check" />

    <!-- Error: fase fallida -->
    <i v-else-if="showFailed" class="pi pi-exclamation-circle tab-status__failed" />

    <!-- Badge numerico: conteo de alertas/entidades -->
    <span v-if="showCount" class="tab-status__count" :class="badgeClass">
      {{ countLabel }}
    </span>
  </span>
</template>

<style scoped>
.tab-status {
  display: inline-flex;
  align-items: center;
  gap: var(--ds-space-1);
}

/* Dot animado */
.tab-status__dot {
  width: 8px;
  height: 8px;
  border-radius: var(--ds-radius-full);
}

.tab-status__dot--running {
  background-color: var(--ds-color-primary);
  animation: pulse-dot 1.5s ease-in-out infinite;
}

.tab-status__dot--partial {
  background-color: var(--ds-alert-medium, #f59e0b);
  animation: pulse-dot 2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.75); }
}

@media (prefers-reduced-motion: reduce) {
  .tab-status__dot--running,
  .tab-status__dot--partial {
    animation: none;
  }
}

/* Check */
.tab-status__check {
  font-size: 0.7rem;
  color: var(--ds-color-success);
}

/* Failed */
.tab-status__failed {
  font-size: 0.75rem;
  color: var(--ds-color-danger);
}

/* Badge numerico */
.tab-status__count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 var(--ds-space-1);
  font-size: 0.6875rem;
  font-weight: var(--ds-font-weight-semibold);
  color: white;
  border-radius: var(--ds-radius-full);
  line-height: 1;
}

.tab-status__count--primary {
  background-color: var(--ds-color-primary);
}

.tab-status__count--warning {
  background-color: var(--ds-alert-high);
}

/* Dentro de tab activo, oscurecer ligeramente */
:deep(.workspace-tabs__tab--active) .tab-status__count--primary {
  background-color: var(--ds-color-primary-dark, var(--ds-color-primary));
}
</style>
