<script setup lang="ts">
import { ref, computed } from 'vue'
import { useSelectionStore } from '@/stores/selection'
import { useAlertUtils } from '@/composables/useAlertUtils'
import DsInput from '@/components/ds/DsInput.vue'
import DsBadge from '@/components/ds/DsBadge.vue'
import DsEmptyState from '@/components/ds/DsEmptyState.vue'
import DsLoadingState from '@/components/ds/DsLoadingState.vue'
import type { Alert, AlertSeverity, AlertStatus } from '@/types'

/**
 * AlertPanel - Panel lateral con lista de alertas filtrable.
 *
 * Muestra alertas ordenadas por severidad con filtros.
 */

const props = defineProps<{
  /** Lista de alertas */
  alerts: Alert[]
  /** Si está cargando */
  loading?: boolean
}>()

const emit = defineEmits<{
  select: [alert: Alert]
  dismiss: [alert: Alert]
  resolve: [alert: Alert]
}>()

const selectionStore = useSelectionStore()
const {
  getSeverityConfig,
  getCategoryConfig,
  filterAlerts,
  sortAlerts,
  countBySeverity,
  getActiveAlerts,
  formatAlertLocation,
} = useAlertUtils()

const searchQuery = ref('')
const activeStatusFilter = ref<AlertStatus | 'all'>('active')
const activeSeverityFilter = ref<AlertSeverity | 'all'>('all')

// Contadores por severidad
const severityCounts = computed(() => countBySeverity(props.alerts))

// Filtros de severidad
const severityFilters = computed(() => [
  { value: 'all' as const, label: 'Todas', count: props.alerts.length },
  { value: 'critical' as const, label: 'Críticas', count: severityCounts.value.critical },
  { value: 'high' as const, label: 'Altas', count: severityCounts.value.high },
  { value: 'medium' as const, label: 'Medias', count: severityCounts.value.medium },
  { value: 'low' as const, label: 'Bajas', count: severityCounts.value.low },
])

// Alertas filtradas y ordenadas
const filteredAlerts = computed(() => {
  let result = props.alerts

  // Filtrar por estado
  if (activeStatusFilter.value !== 'all') {
    result = result.filter((a) => a.status === activeStatusFilter.value)
  }

  // Filtrar por severidad
  if (activeSeverityFilter.value !== 'all') {
    result = result.filter((a) => a.severity === activeSeverityFilter.value)
  }

  // Filtrar por búsqueda
  result = filterAlerts(result, searchQuery.value)

  // Ordenar por severidad
  return sortAlerts(result)
})

// Estadísticas rápidas
const activeCount = computed(() => getActiveAlerts(props.alerts).length)
const criticalCount = computed(
  () => props.alerts.filter((a) => a.status === 'active' && a.severity === 'critical').length,
)

function handleSelect(alert: Alert) {
  selectionStore.selectAlert(alert)
  emit('select', alert)
}

function handleDismiss(event: Event, alert: Alert) {
  event.stopPropagation()
  emit('dismiss', alert)
}

function handleResolve(event: Event, alert: Alert) {
  event.stopPropagation()
  emit('resolve', alert)
}

function isSelected(alert: Alert): boolean {
  return selectionStore.isSelected('alert', alert.id)
}

// Obtener mensaje de la alerta
function getAlertMessage(alert: Alert): string {
  return alert.description || alert.title || ''
}
</script>

<template>
  <div class="alert-panel">
    <!-- Header con estadísticas -->
    <div class="alert-panel__header">
      <div class="alert-panel__stats">
        <div class="alert-panel__stat">
          <span class="alert-panel__stat-value">{{ activeCount }}</span>
          <span class="alert-panel__stat-label">Activas</span>
        </div>
        <div v-if="criticalCount > 0" class="alert-panel__stat alert-panel__stat--critical">
          <span class="alert-panel__stat-value">{{ criticalCount }}</span>
          <span class="alert-panel__stat-label">Críticas</span>
        </div>
      </div>
      <DsInput
        v-model="searchQuery"
        placeholder="Buscar alertas..."
        icon="pi pi-search"
        size="sm"
        clearable
      />
    </div>

    <!-- Filtros de estado -->
    <div class="alert-panel__status-filters">
      <button
        type="button"
        class="alert-panel__status-btn"
        :class="{ 'alert-panel__status-btn--active': activeStatusFilter === 'all' }"
        @click="activeStatusFilter = 'all'"
      >
        Todas
      </button>
      <button
        type="button"
        class="alert-panel__status-btn"
        :class="{ 'alert-panel__status-btn--active': activeStatusFilter === 'active' }"
        @click="activeStatusFilter = 'active'"
      >
        Activas
      </button>
      <button
        type="button"
        class="alert-panel__status-btn"
        :class="{ 'alert-panel__status-btn--active': activeStatusFilter === 'resolved' }"
        @click="activeStatusFilter = 'resolved'"
      >
        Resueltas
      </button>
      <button
        type="button"
        class="alert-panel__status-btn"
        :class="{ 'alert-panel__status-btn--active': activeStatusFilter === 'dismissed' }"
        @click="activeStatusFilter = 'dismissed'"
      >
        Descartadas
      </button>
    </div>

    <!-- Filtros de severidad -->
    <div class="alert-panel__severity-filters">
      <button
        v-for="filter in severityFilters"
        :key="filter.value"
        type="button"
        class="alert-panel__severity-btn"
        :class="[
          `alert-panel__severity-btn--${filter.value}`,
          { 'alert-panel__severity-btn--active': activeSeverityFilter === filter.value },
        ]"
        @click="activeSeverityFilter = filter.value"
      >
        {{ filter.count }}
      </button>
    </div>

    <!-- Loading state -->
    <DsLoadingState v-if="loading" message="Cargando alertas..." size="sm" />

    <!-- Empty state -->
    <DsEmptyState
      v-else-if="filteredAlerts.length === 0"
      icon="pi pi-check-circle"
      :title="searchQuery ? 'Sin resultados' : 'Sin alertas'"
      :description="searchQuery ? 'Prueba con otros términos' : '¡No hay inconsistencias detectadas!'"
      size="sm"
    />

    <!-- Lista de alertas -->
    <div v-else class="alert-panel__list">
      <div
        v-for="alert in filteredAlerts"
        :key="alert.id"
        class="alert-panel__item"
        :class="[
          `alert-panel__item--${alert.severity}`,
          { 'alert-panel__item--selected': isSelected(alert) },
        ]"
        @click="handleSelect(alert)"
      >
        <div class="alert-panel__item-header">
          <DsBadge :severity="alert.severity" size="sm">
            {{ getSeverityConfig(alert.severity).label }}
          </DsBadge>
          <span class="alert-panel__item-category">
            {{ getCategoryConfig(alert.category).label }}
          </span>
        </div>

        <p class="alert-panel__item-message">{{ getAlertMessage(alert) }}</p>

        <div class="alert-panel__item-footer">
          <span class="alert-panel__item-location">
            <i class="pi pi-map-marker" />
            {{ formatAlertLocation(alert) }}
          </span>

          <div v-if="alert.status === 'active'" class="alert-panel__item-actions">
            <button
              type="button"
              class="alert-panel__action-btn"
              title="Descartar"
              @click="handleDismiss($event, alert)"
            >
              <i class="pi pi-times" />
            </button>
            <button
              type="button"
              class="alert-panel__action-btn alert-panel__action-btn--resolve"
              title="Marcar como resuelta"
              @click="handleResolve($event, alert)"
            >
              <i class="pi pi-check" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="alert-panel__footer">
      <span>{{ filteredAlerts.length }} de {{ alerts.length }} alertas</span>
    </div>
  </div>
</template>

<style scoped>
.alert-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.alert-panel__header {
  padding: var(--ds-space-3);
  border-bottom: 1px solid var(--ds-surface-border);
}

.alert-panel__stats {
  display: flex;
  gap: var(--ds-space-4);
  margin-bottom: var(--ds-space-3);
}

.alert-panel__stat {
  display: flex;
  flex-direction: column;
}

.alert-panel__stat-value {
  font-size: var(--ds-font-size-xl);
  font-weight: var(--ds-font-weight-bold);
  color: var(--ds-color-text);
}

.alert-panel__stat--critical .alert-panel__stat-value {
  color: var(--ds-alert-critical);
}

.alert-panel__stat-label {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-muted);
}

.alert-panel__status-filters {
  display: flex;
  border-bottom: 1px solid var(--ds-surface-border);
}

.alert-panel__status-btn {
  flex: 1;
  padding: var(--ds-space-2);
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: var(--ds-transition-fast);
}

.alert-panel__status-btn:hover {
  background-color: var(--ds-surface-hover);
}

.alert-panel__status-btn--active {
  color: var(--ds-color-primary);
  border-bottom-color: var(--ds-color-primary);
}

.alert-panel__severity-filters {
  display: flex;
  gap: var(--ds-space-1);
  padding: var(--ds-space-2) var(--ds-space-3);
  border-bottom: 1px solid var(--ds-surface-border);
}

.alert-panel__severity-btn {
  flex: 1;
  padding: var(--ds-space-1);
  font-size: var(--ds-font-size-xs);
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-text-secondary);
  background: var(--ds-surface-hover);
  border: 1px solid transparent;
  border-radius: var(--ds-radius-sm);
  cursor: pointer;
  transition: var(--ds-transition-fast);
}

.alert-panel__severity-btn--active {
  border-color: currentColor;
}

.alert-panel__severity-btn--critical {
  color: var(--ds-alert-critical);
}
.alert-panel__severity-btn--high {
  color: var(--ds-alert-high);
}
.alert-panel__severity-btn--medium {
  color: var(--ds-alert-medium);
}
.alert-panel__severity-btn--low {
  color: var(--ds-alert-low);
}
.alert-panel__severity-btn--all {
  color: var(--ds-color-text-secondary);
}

.alert-panel__list {
  flex: 1;
  overflow-y: auto;
  padding: var(--ds-space-2);
}

.alert-panel__item {
  padding: var(--ds-space-3);
  margin-bottom: var(--ds-space-2);
  background-color: var(--ds-surface-card);
  border-radius: var(--ds-radius-md);
  border-left: 3px solid var(--ds-surface-border);
  cursor: pointer;
  transition: var(--ds-transition-fast);
}

.alert-panel__item:hover {
  box-shadow: var(--ds-shadow-sm);
}

.alert-panel__item--selected {
  background-color: var(--ds-surface-hover);
}

.alert-panel__item--critical {
  border-left-color: var(--ds-alert-critical);
}
.alert-panel__item--high {
  border-left-color: var(--ds-alert-high);
}
.alert-panel__item--medium {
  border-left-color: var(--ds-alert-medium);
}
.alert-panel__item--low {
  border-left-color: var(--ds-alert-low);
}
.alert-panel__item--info {
  border-left-color: var(--ds-alert-info);
}

.alert-panel__item-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  margin-bottom: var(--ds-space-2);
}

.alert-panel__item-category {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-muted);
}

.alert-panel__item-message {
  margin: 0;
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
  line-height: var(--ds-line-height-normal);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.alert-panel__item-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--ds-space-2);
}

.alert-panel__item-location {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-muted);
}

.alert-panel__item-location i {
  font-size: 10px;
}

.alert-panel__item-actions {
  display: flex;
  gap: var(--ds-space-1);
  opacity: 0;
  transition: var(--ds-transition-fast);
}

.alert-panel__item:hover .alert-panel__item-actions {
  opacity: 1;
}

.alert-panel__action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  color: var(--ds-color-text-muted);
  background: transparent;
  border: none;
  border-radius: var(--ds-radius-sm);
  cursor: pointer;
  transition: var(--ds-transition-fast);
}

.alert-panel__action-btn:hover {
  background-color: var(--ds-surface-border);
  color: var(--ds-color-text);
}

.alert-panel__action-btn--resolve:hover {
  color: var(--ds-color-success);
}

.alert-panel__footer {
  padding: var(--ds-space-2) var(--ds-space-3);
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-muted);
  text-align: center;
  border-top: 1px solid var(--ds-surface-border);
}
</style>
