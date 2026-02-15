<script setup lang="ts">
import { computed } from 'vue'
import type { Alert, AlertSeverity } from '@/types'
import { useAlertUtils } from '@/composables/useAlertUtils'
import { useListKeyboardNav } from '@/composables/useListKeyboardNav'

/**
 * AlertsPanel - Panel compacto de alertas para el sidebar.
 *
 * Muestra las alertas directamente ordenadas por severidad.
 * Click en una alerta navega al tab de alertas con esa alerta seleccionada.
 */

const props = defineProps<{
  /** Lista de alertas */
  alerts: Alert[]
}>()

const emit = defineEmits<{
  /** Cuando se hace click para navegar a pantalla de alertas */
  (e: 'navigate'): void
  /** Cuando se selecciona una severidad específica */
  (e: 'filter-severity', severity: AlertSeverity): void
  /** Cuando se hace click en una alerta específica - navega al texto */
  (e: 'alert-click', alert: Alert): void
  /** Cuando se quiere navegar al texto donde está la alerta */
  (e: 'alert-navigate', alert: Alert): void
}>()

const { getSeverityColor } = useAlertUtils()
const { setItemRef: setAlertRef, getTabindex: getAlertTabindex, onKeydown: onAlertListKeydown, focusedIndex: alertFocusedIndex } = useListKeyboardNav()

/** Orden de severidad para ordenar alertas */
const severityOrder: Record<AlertSeverity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4
}

/** Total de alertas */
const totalCount = computed(() => props.alerts.length)

/** Número máximo de alertas a mostrar en el panel */
const MAX_VISIBLE_ALERTS = 15

/** Alertas ordenadas por severidad, limitadas */
const sortedAlerts = computed(() => {
  return [...props.alerts]
    .sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity])
    .slice(0, MAX_VISIBLE_ALERTS)
})

/** Si hay más alertas de las que mostramos */
const hasMoreAlerts = computed(() => props.alerts.length > MAX_VISIBLE_ALERTS)

/** Truncar título si es muy largo */
function truncateTitle(title: string, maxLen = 45): string {
  if (title.length <= maxLen) return title
  return title.slice(0, maxLen - 3) + '...'
}

function handleAlertClick(alert: Alert) {
  emit('alert-click', alert)
  // Navegar al texto donde está la alerta, no a la pantalla de alertas
  emit('alert-navigate', alert)
}

function handleViewAll() {
  emit('navigate')
}
</script>

<template>
  <div class="alerts-panel">
    <div class="panel-header">
      <span class="panel-title">Alertas</span>
      <span class="panel-count">{{ totalCount }}</span>
    </div>

    <div v-if="alerts.length === 0" class="empty-state">
      <i class="pi pi-check-circle"></i>
      <span>Sin alertas</span>
    </div>

    <div v-else class="alerts-list" role="listbox" aria-label="Alertas" @keydown="onAlertListKeydown">
      <button
        v-for="(alert, index) in sortedAlerts"
        :key="alert.id"
        :ref="el => setAlertRef(el, index)"
        type="button"
        role="option"
        class="alert-row"
        :tabindex="getAlertTabindex(index)"
        :title="alert.title"
        :aria-selected="alertFocusedIndex === index"
        @click="handleAlertClick(alert)"
        @keydown.enter.stop="handleAlertClick(alert)"
        @focus="alertFocusedIndex = index"
      >
        <span
          class="severity-dot"
          :style="{ backgroundColor: getSeverityColor(alert.severity) }"
        ></span>
        <span class="alert-title">{{ truncateTitle(alert.title) }}</span>
      </button>

      <button
        v-if="hasMoreAlerts"
        type="button"
        class="view-all-row"
        @click="handleViewAll"
      >
        <i class="pi pi-arrow-right"></i>
        <span>Ver todas ({{ totalCount }})</span>
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

.alerts-list {
  display: flex;
  flex-direction: column;
  padding: var(--ds-space-2);
  overflow-y: auto;
  flex: 1;
}

.alert-row {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2) var(--ds-space-3);
  border: none;
  background: transparent;
  border-radius: var(--ds-radius-md);
  cursor: pointer;
  transition: background-color var(--ds-transition-fast);
  width: 100%;
  text-align: left;
}

.alert-row:hover {
  background: var(--ds-surface-hover);
}

.severity-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--ds-radius-full);
  flex-shrink: 0;
}

.alert-title {
  flex: 1;
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.view-all-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2) var(--ds-space-3);
  margin-top: var(--ds-space-2);
  border: none;
  background: transparent;
  border-radius: var(--ds-radius-md);
  cursor: pointer;
  transition: background-color var(--ds-transition-fast);
  width: 100%;
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.view-all-row:hover {
  background: var(--ds-surface-hover);
  color: var(--ds-color-text);
}

.view-all-row i {
  font-size: 0.75rem;
}
</style>
