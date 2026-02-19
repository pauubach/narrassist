<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Alert, AlertSeverity } from '@/types'
import { useAlertUtils, META_CATEGORIES, type MetaCategoryKey } from '@/composables/useAlertUtils'
import { useListKeyboardNav } from '@/composables/useListKeyboardNav'
import { useSelectionStore } from '@/stores/selection'

/**
 * AlertsPanel - Panel de alertas para el sidebar.
 *
 * Muestra alertas ordenadas por severidad con filtro rápido por meta-categoría.
 * Click en una alerta la selecciona en el inspector (panel dcho).
 */

const props = defineProps<{
  /** Lista de alertas (ya filtradas por el parent si aplica) */
  alerts: Alert[]
}>()

const emit = defineEmits<{
  (e: 'navigate'): void
  (e: 'filter-severity', severity: AlertSeverity): void
  (e: 'alert-click', alert: Alert): void
  (e: 'alert-navigate', alert: Alert): void
}>()

const selectionStore = useSelectionStore()
const { getSeverityColor, getCategoryConfig } = useAlertUtils()
const { setItemRef: setAlertRef, getTabindex: getAlertTabindex, onKeydown: onAlertListKeydown, focusedIndex: alertFocusedIndex } = useListKeyboardNav()

/** Filtro activo por meta-categoría */
const activeFilter = ref<MetaCategoryKey | null>(null)

/** Orden de severidad */
const severityOrder: Record<AlertSeverity, number> = {
  critical: 0, high: 1, medium: 2, low: 3, info: 4
}

/** Conteo por meta-categoría */
const metaCounts = computed(() => {
  const counts: Record<MetaCategoryKey, number> = { errors: 0, inconsistencies: 0, quality: 0, suggestions: 0 }
  for (const alert of props.alerts) {
    if (alert.status !== 'active') continue
    for (const [key, meta] of Object.entries(META_CATEGORIES)) {
      if (meta.categories.includes(alert.category as never)) {
        counts[key as MetaCategoryKey]++
        break
      }
    }
  }
  return counts
})

/** Alertas filtradas y ordenadas */
const filteredAlerts = computed(() => {
  let list = props.alerts
  if (activeFilter.value) {
    const cats = META_CATEGORIES[activeFilter.value].categories
    list = list.filter(a => cats.includes(a.category as never))
  }
  return [...list].sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity])
})

/** Total visible */
const visibleCount = computed(() => filteredAlerts.value.length)
const totalCount = computed(() => props.alerts.length)

/** Toggle filtro */
function toggleFilter(key: MetaCategoryKey) {
  activeFilter.value = activeFilter.value === key ? null : key
}

/** Truncar título */
function truncateTitle(title: string, maxLen = 40): string {
  if (title.length <= maxLen) return title
  return title.slice(0, maxLen - 3) + '...'
}

/** Check si una alerta está seleccionada */
function isSelected(alert: Alert): boolean {
  return selectionStore.selectedAlertIds.includes(alert.id)
}

/** Obtener color de meta-categoría para una alerta */
function getAlertMetaColor(alert: Alert): string {
  for (const [key, metaConfig] of Object.entries(META_CATEGORIES)) {
    const meta = metaConfig as typeof META_CATEGORIES[MetaCategoryKey]
    if (meta.categories.includes(alert.category as never)) {
      return meta.color
    }
  }
  // Fallback a sugerencias
  return META_CATEGORIES.suggestions.color
}

function handleAlertClick(alert: Alert) {
  emit('alert-click', alert)
}
</script>

<template>
  <div class="alerts-panel">
    <!-- Header -->
    <div class="panel-header">
      <span class="panel-title">Alertas</span>
      <span class="panel-count">
        {{ activeFilter ? `${visibleCount}/${totalCount}` : totalCount }}
      </span>
    </div>

    <!-- Filtros rápidos por meta-categoría -->
    <div class="meta-filters">
      <button
        v-for="(meta, key) in META_CATEGORIES"
        :key="key"
        class="meta-filter"
        :class="{ 'meta-filter--active': activeFilter === key }"
        :style="{ '--meta-color': meta.color }"
        :title="`${meta.label} (${metaCounts[key as MetaCategoryKey]})`"
        @click="toggleFilter(key as MetaCategoryKey)"
      >
        <i :class="meta.icon" class="meta-filter-icon"></i>
        <span class="meta-filter-count">{{ metaCounts[key as MetaCategoryKey] }}</span>
      </button>
    </div>

    <!-- Empty state -->
    <div v-if="filteredAlerts.length === 0" class="empty-state">
      <i class="pi pi-check-circle"></i>
      <span>{{ activeFilter ? 'Sin alertas de este tipo' : 'Sin alertas' }}</span>
    </div>

    <!-- Lista de alertas -->
    <div v-else class="alerts-list" role="listbox" aria-label="Alertas" @keydown="onAlertListKeydown">
      <button
        v-for="(alert, index) in filteredAlerts"
        :key="alert.id"
        :ref="el => setAlertRef(el, index)"
        type="button"
        role="option"
        class="alert-row"
        :class="{ 'alert-row--selected': isSelected(alert), 'alert-row--resolved': alert.status !== 'active' }"
        :tabindex="getAlertTabindex(index)"
        :aria-selected="isSelected(alert)"
        :aria-label="`${alert.severity}: ${alert.title}${alert.chapter ? `, Cap. ${alert.chapter}` : ''}`"
        @click="handleAlertClick(alert)"
        @keydown.enter.stop="handleAlertClick(alert)"
        @focus="alertFocusedIndex = index"
      >
        <span
          class="severity-dot"
          :style="{ backgroundColor: getAlertMetaColor(alert) }"
        ></span>
        <span class="alert-title">{{ truncateTitle(alert.title) }}</span>
        <span v-if="alert.chapter" class="alert-chapter">{{ alert.chapter }}</span>
        <i
          v-if="alert.status === 'resolved'"
          class="pi pi-check status-icon status-icon--resolved"
          title="Resuelta"
        ></i>
        <i
          v-else-if="alert.status === 'dismissed'"
          class="pi pi-minus-circle status-icon status-icon--dismissed"
          title="Descartada"
        ></i>
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

/* Meta-category filters */
.meta-filters {
  display: flex;
  gap: var(--ds-space-1);
  padding: var(--ds-space-2) var(--ds-space-3);
  border-bottom: 1px solid var(--ds-surface-border);
}

.meta-filter {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border: 1px solid var(--ds-surface-border);
  border-radius: var(--ds-radius-full);
  background: transparent;
  cursor: pointer;
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  transition: all var(--ds-transition-fast);
}

.meta-filter:hover {
  background: var(--ds-surface-hover);
}

.meta-filter--active {
  background: var(--meta-color);
  color: white;
  border-color: var(--meta-color);
}

.meta-filter-icon {
  font-size: 0.7rem;
}

.meta-filter-count {
  font-weight: var(--ds-font-weight-semibold);
}

/* Empty state */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-6);
  color: var(--ds-color-text-secondary);
  font-size: var(--ds-font-size-sm);
}

.empty-state i {
  font-size: 1.5rem;
  color: var(--ds-color-success);
}

/* Alerts list */
.alerts-list {
  display: flex;
  flex-direction: column;
  padding: var(--ds-space-1);
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.alert-row {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: 6px var(--ds-space-2);
  border: none;
  border-left: 3px solid transparent;
  background: transparent;
  border-radius: 0 var(--ds-radius-md) var(--ds-radius-md) 0;
  cursor: pointer;
  transition: background-color var(--ds-transition-fast), border-color var(--ds-transition-fast);
  width: 100%;
  text-align: left;
}

.alert-row:hover {
  background: var(--ds-surface-hover);
}

.alert-row--selected {
  border-left-color: var(--ds-color-primary, var(--primary-color));
  background: var(--surface-100, rgba(0, 0, 0, 0.04));
}

.alert-row--resolved {
  opacity: 0.55;
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
  min-width: 0;
}

.alert-chapter {
  flex-shrink: 0;
  font-size: 0.6875rem;
  color: var(--ds-color-text-secondary);
  background: var(--ds-surface-hover);
  padding: 1px 6px;
  border-radius: var(--ds-radius-full);
}

.status-icon {
  flex-shrink: 0;
  font-size: 0.7rem;
}

.status-icon--resolved {
  color: var(--ds-color-success, var(--green-500));
}

.status-icon--dismissed {
  color: var(--ds-color-text-secondary);
}

/* Dark mode */
:global(.dark) .alert-row--selected {
  background: var(--surface-700, rgba(255, 255, 255, 0.08));
}

:global(.dark) .meta-filter {
  border-color: var(--surface-600);
}
</style>
