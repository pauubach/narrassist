<script setup lang="ts">
import { computed } from 'vue'
import type { Alert, AlertSeverity } from '@/types'
import { useAlertUtils } from '@/composables/useAlertUtils'

/**
 * AlertsPanel - Panel compacto de alertas para el sidebar.
 *
 * Muestra un resumen de alertas agrupadas por severidad.
 * Click en cualquier fila navega al tab de alertas.
 */

const props = defineProps<{
  /** Lista de alertas */
  alerts: Alert[]
}>()

const emit = defineEmits<{
  /** Cuando se hace click para navegar a alertas */
  (e: 'navigate'): void
  /** Cuando se selecciona una severidad específica */
  (e: 'filter-severity', severity: AlertSeverity): void
}>()

const { getSeverityLabel, getSeverityColor } = useAlertUtils()

/** Total de alertas */
const totalCount = computed(() => props.alerts.length)

/** Alertas agrupadas por severidad */
const alertsBySeverity = computed(() => {
  const counts: Partial<Record<AlertSeverity, number>> = {}
  const severityOrder: AlertSeverity[] = ['critical', 'high', 'medium', 'low', 'info']

  for (const alert of props.alerts) {
    counts[alert.severity] = (counts[alert.severity] || 0) + 1
  }

  // Devolver solo las que tienen alertas, en orden de severidad
  return severityOrder
    .filter(s => counts[s] && counts[s]! > 0)
    .map(severity => ({
      severity,
      count: counts[severity]!,
      label: getSeverityLabel(severity),
      color: getSeverityColor(severity)
    }))
})

function handleRowClick(severity: AlertSeverity) {
  emit('filter-severity', severity)
  emit('navigate')
}
</script>

<template>
  <div class="alerts-panel">
    <div class="panel-header">
      <span class="panel-title">Alertas</span>
      <span class="panel-count">{{ totalCount }}</span>
    </div>

    <div v-if="alertsBySeverity.length === 0" class="empty-state">
      <i class="pi pi-check-circle"></i>
      <span>Sin alertas</span>
    </div>

    <div v-else class="severity-list">
      <button
        v-for="item in alertsBySeverity"
        :key="item.severity"
        type="button"
        class="severity-row"
        @click="handleRowClick(item.severity)"
      >
        <span class="severity-dot" :style="{ backgroundColor: item.color }"></span>
        <span class="severity-label">{{ item.label }}</span>
        <span class="severity-count">{{ item.count }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.alerts-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--ds-space-3);
  border-bottom: 1px solid var(--ds-surface-border);
}

.panel-title {
  font-weight: var(--ds-font-weight-semibold);
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
}

.panel-count {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  background: var(--ds-surface-hover);
  padding: 2px 8px;
  border-radius: var(--ds-radius-full);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-6);
  color: var(--ds-color-text-secondary);
}

.empty-state i {
  font-size: 2rem;
  color: var(--ds-color-success);
}

.severity-list {
  display: flex;
  flex-direction: column;
  padding: var(--ds-space-2);
}

.severity-row {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
  padding: var(--ds-space-2) var(--ds-space-3);
  border: none;
  background: transparent;
  border-radius: var(--ds-radius-md);
  cursor: pointer;
  transition: background-color var(--ds-transition-fast);
  width: 100%;
  text-align: left;
}

.severity-row:hover {
  background: var(--ds-surface-hover);
}

.severity-dot {
  width: 10px;
  height: 10px;
  border-radius: var(--ds-radius-full);
  flex-shrink: 0;
}

.severity-label {
  flex: 1;
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
}

.severity-count {
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-medium);
  color: var(--ds-color-text-secondary);
}
</style>
