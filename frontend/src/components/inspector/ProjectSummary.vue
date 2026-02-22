<script setup lang="ts">
/**
 * ProjectSummary - Resumen del proyecto para el inspector.
 *
 * Se muestra cuando no hay ningún elemento seleccionado.
 * Proporciona una vista rápida de las estadísticas del proyecto.
 */
import { computed } from 'vue'
import { useAlertUtils } from '@/composables/useAlertUtils'
import type { Alert } from '@/types'

const props = withDefaults(defineProps<{
  /** Número total de palabras */
  wordCount: number
  /** Número de capítulos */
  chapterCount: number
  /** Número de entidades */
  entityCount: number
  /** Número de alertas */
  alertCount: number
  /** Alertas cargadas para mostrar progreso detallado */
  alerts?: Alert[]
}>(), {
  alerts: () => [],
})

const emit = defineEmits<{
  /** Cuando se hace click en una estadística */
  (e: 'stat-click', stat: 'words' | 'chapters' | 'entities' | 'alerts'): void
}>()

const { getCategoryLabel } = useAlertUtils()

const hasDetailedAlerts = computed(() => props.alerts.length > 0)

const alertStatusCounts = computed(() => {
  const counts = {
    active: 0,
    resolved: 0,
    dismissed: 0,
  }

  for (const alert of props.alerts) {
    counts[alert.status] += 1
  }

  return counts
})

const totalDetailedAlerts = computed(() => props.alerts.length)
const resolvedCount = computed(() => alertStatusCounts.value.resolved)
const dismissedCount = computed(() => alertStatusCounts.value.dismissed)
const activeCount = computed(() => alertStatusCounts.value.active)
const reviewedCount = computed(() => resolvedCount.value + dismissedCount.value)

const resolvedRate = computed(() => {
  if (!totalDetailedAlerts.value) return 0
  return Math.round((resolvedCount.value / totalDetailedAlerts.value) * 100)
})

const dismissedRate = computed(() => {
  if (!totalDetailedAlerts.value) return 0
  return Math.round((dismissedCount.value / totalDetailedAlerts.value) * 100)
})

const activeRate = computed(() => {
  if (!totalDetailedAlerts.value) return 0
  return Math.round((activeCount.value / totalDetailedAlerts.value) * 100)
})

const reviewRate = computed(() => {
  if (!totalDetailedAlerts.value) return 0
  return Math.round((reviewedCount.value / totalDetailedAlerts.value) * 100)
})

const categoryOverview = computed(() => {
  if (!props.alerts.length) return []

  const totalByCategory = new Map<Alert['category'], number>()
  const pendingByCategory = new Map<Alert['category'], number>()

  for (const alert of props.alerts) {
    totalByCategory.set(alert.category, (totalByCategory.get(alert.category) ?? 0) + 1)
    if (alert.status === 'active') {
      pendingByCategory.set(alert.category, (pendingByCategory.get(alert.category) ?? 0) + 1)
    }
  }

  return [...totalByCategory.entries()]
    .map(([category, count]) => ({
      category,
      label: getCategoryLabel(category),
      totalCount: count,
      pendingCount: pendingByCategory.get(category) ?? 0,
      totalPercentage: Math.round((count / props.alerts.length) * 100),
      pendingPercentageOfAll: Math.round(((pendingByCategory.get(category) ?? 0) / props.alerts.length) * 100),
      pendingWithinType: count > 0 ? Math.round(((pendingByCategory.get(category) ?? 0) / count) * 100) : 0,
    }))
    .sort((a, b) => b.totalCount - a.totalCount)
    .slice(0, 5)
})
</script>

<template>
  <div class="project-summary">
    <!-- Stats en grid 2x2 para aprovechar mejor el espacio -->
    <div class="summary-stats">
      <button
        type="button"
        class="stat-card"
        @click="emit('stat-click', 'words')"
      >
        <i class="pi pi-file-edit stat-icon"></i>
        <div class="stat-content">
          <span class="stat-value">{{ wordCount.toLocaleString() }}</span>
          <span class="stat-label">palabras</span>
        </div>
      </button>

      <button
        type="button"
        class="stat-card"
        @click="emit('stat-click', 'chapters')"
      >
        <i class="pi pi-book stat-icon"></i>
        <div class="stat-content">
          <span class="stat-value">{{ chapterCount }}</span>
          <span class="stat-label">capítulos</span>
        </div>
      </button>

      <button
        type="button"
        class="stat-card"
        @click="emit('stat-click', 'entities')"
      >
        <i class="pi pi-users stat-icon"></i>
        <div class="stat-content">
          <span class="stat-value">{{ entityCount }}</span>
          <span class="stat-label">entidades</span>
        </div>
      </button>

      <button
        type="button"
        class="stat-card"
        :class="{ 'stat-card--alert': alertCount > 0 }"
        @click="emit('stat-click', 'alerts')"
      >
        <i class="pi pi-exclamation-triangle stat-icon"></i>
        <div class="stat-content">
          <span class="stat-value">{{ alertCount }}</span>
          <span class="stat-label">alertas</span>
        </div>
      </button>
    </div>

    <div v-if="hasDetailedAlerts" class="summary-section">
      <div class="section-header">
        <span class="section-title">Progreso de alertas</span>
        <button
          type="button"
          class="section-link"
          @click="emit('stat-click', 'alerts')"
        >
          Ver alertas
        </button>
      </div>

      <p class="progress-caption">
        <span class="progress-main">
          <strong>{{ reviewRate }}%</strong> revisadas
        </span>
        <span class="progress-detail">({{ reviewedCount }} de {{ totalDetailedAlerts }})</span>
      </p>

      <div class="progress-track">
        <div class="progress-fill" :style="{ width: `${reviewRate}%` }"></div>
      </div>

      <div class="status-grid">
        <div class="status-chip status-chip--active">
          <span>Pendientes</span>
          <strong>{{ activeCount }}</strong>
          <small>{{ activeRate }}%</small>
        </div>
        <div class="status-chip status-chip--resolved">
          <span>Aceptadas</span>
          <strong>{{ resolvedCount }}</strong>
          <small>{{ resolvedRate }}%</small>
        </div>
        <div class="status-chip status-chip--dismissed">
          <span>Rechazadas</span>
          <strong>{{ dismissedCount }}</strong>
          <small>{{ dismissedRate }}%</small>
        </div>
      </div>
    </div>

    <div v-if="categoryOverview.length > 0" class="summary-section">
      <div class="section-title">Distribución y pendientes por tipo</div>

      <div class="category-legend">
        <span class="legend-item">
          <i class="legend-dot legend-dot--total"></i>
          Total
        </span>
        <span class="legend-item">
          <i class="legend-dot legend-dot--pending"></i>
          Pendiente
        </span>
      </div>

      <div class="category-list category-list--compact">
        <div
          v-for="item in categoryOverview"
          :key="item.category"
          class="category-overview-row"
        >
          <div class="category-row">
            <span class="category-name">{{ item.label }}</span>
            <span class="category-meta">{{ item.totalCount }} · {{ item.totalPercentage }}%</span>
          </div>
          <div class="category-row category-row--pending">
            <span class="category-pending">{{ item.pendingCount }} pendientes</span>
            <span class="category-meta">{{ item.pendingWithinType }}%</span>
          </div>
          <div class="dual-track">
            <div class="dual-track-line dual-track-line--total">
              <div class="dual-track-fill dual-track-fill--total" :style="{ width: `${item.totalPercentage}%` }"></div>
            </div>
            <div class="dual-track-line dual-track-line--pending">
              <div class="dual-track-fill dual-track-fill--pending" :style="{ width: `${item.pendingPercentageOfAll}%` }"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Tip de uso -->
    <div class="summary-tip">
      <i class="pi pi-info-circle"></i>
      <span>
        {{ hasDetailedAlerts
          ? 'Abre Alertas para continuar la revisión y resolver las pendientes'
          : 'Selecciona una entidad o alerta para ver sus detalles aquí' }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.project-summary {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3);
  padding: var(--ds-space-3);
  width: 100%;
  min-width: 0;
  overflow: hidden;
}

.summary-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--ds-space-2);
}

.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-3);
  background: var(--ds-surface-ground);
  border: var(--ds-border-1) solid var(--ds-surface-border);
  border-radius: var(--ds-radius-lg);
  cursor: pointer;
  transition: all var(--ds-transition-fast);
  text-align: center;
  min-height: calc(var(--ds-space-10) * 2);
}

.stat-card:hover {
  background: var(--ds-surface-hover);
  border-color: var(--ds-color-primary-light);
}

.stat-card--alert {
  border-color: var(--ds-color-warning-light);
}

.stat-card--alert:hover {
  border-color: var(--ds-color-warning);
}

.stat-icon {
  font-size: var(--ds-font-xl);
  color: var(--ds-color-text-secondary);
}

.stat-card--alert .stat-icon {
  color: var(--ds-color-warning);
}

.stat-content {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: var(--ds-font-size-lg);
  font-weight: var(--ds-font-weight-bold);
  color: var(--ds-color-text);
  line-height: var(--ds-leading-tight);
}

.stat-label {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.summary-tip {
  display: flex;
  align-items: flex-start;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2);
  background: var(--ds-surface-section);
  border-radius: var(--ds-radius-md);
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  line-height: 1.4;
}

.summary-tip i {
  flex-shrink: 0;
  margin-top: var(--ds-space-0-5);
}

.summary-section {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-1-5);
  padding: var(--ds-space-2);
  background: var(--ds-surface-ground);
  border: var(--ds-border-1) solid var(--ds-surface-border);
  border-radius: var(--ds-radius-lg);
  min-width: 0;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-2);
  min-width: 0;
}

.section-title {
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-text);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.section-link {
  border: none;
  background: transparent;
  color: var(--ds-color-primary);
  font-size: var(--ds-font-size-xs);
  cursor: pointer;
  padding: 0;
  white-space: nowrap;
  flex-shrink: 0;
}

.section-link:hover {
  text-decoration: underline;
}

.progress-caption {
  margin: 0;
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-1);
  align-items: baseline;
  min-width: 0;
}

.progress-caption strong {
  color: var(--ds-color-text);
  margin-right: var(--ds-space-1);
}

.progress-main,
.progress-detail {
  min-width: 0;
}

.progress-track {
  width: 100%;
  height: var(--ds-space-2);
  border-radius: var(--ds-radius-full);
  background: var(--ds-surface-section);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(
    90deg,
    var(--ds-color-success, var(--green-500)) 0%,
    var(--ds-color-primary, var(--primary-500)) 100%
  );
  transition: width var(--ds-transition-fast);
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(calc(var(--ds-space-10) * 2.2), 1fr));
  gap: var(--ds-space-2);
  min-width: 0;
}

.status-chip {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-0-5);
  padding: var(--ds-space-1-5);
  border-radius: var(--ds-radius-md);
  border: var(--ds-border-1) solid var(--ds-surface-border);
  background: var(--ds-surface-section);
  min-width: 0;
}

.status-chip span {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  overflow-wrap: anywhere;
  line-height: var(--ds-leading-tight);
}

.status-chip strong {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
}

.status-chip small {
  font-size: var(--ds-font-xs);
  color: var(--ds-color-text-secondary);
  font-variant-numeric: tabular-nums;
}

.status-chip--active {
  border-color: var(--ds-alert-high, var(--orange-500));
  background: color-mix(in srgb, var(--ds-alert-high, var(--orange-500)) 8%, var(--ds-surface-ground));
}

.status-chip--resolved {
  border-color: var(--ds-color-success);
  background: color-mix(in srgb, var(--ds-color-success) 8%, var(--ds-surface-ground));
}

.status-chip--dismissed {
  border-color: var(--ds-color-text-muted, var(--ds-surface-border-strong, var(--ds-surface-border)));
}

.category-list {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
  min-width: 0;
}

.category-list--compact {
  gap: var(--ds-space-1-5);
}

.category-overview-row {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-1);
  min-width: 0;
}

.category-legend {
  display: flex;
  gap: var(--ds-space-3);
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  flex-wrap: wrap;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: var(--ds-space-1);
}

.legend-dot {
  width: var(--ds-space-1-5);
  height: var(--ds-space-1-5);
  border-radius: var(--ds-radius-full);
  display: inline-block;
}

.legend-dot--total {
  background: var(--ds-color-primary, var(--primary-500));
}

.legend-dot--pending {
  background: var(--ds-alert-high, var(--orange-500));
}

.category-row--pending {
  font-size: var(--ds-font-size-xs);
}

.category-pending {
  color: var(--ds-alert-high, var(--orange-500));
}

.dual-track {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-0-5);
}

.dual-track-line {
  width: 100%;
  height: var(--ds-space-1);
  border-radius: var(--ds-radius-full);
  background: var(--ds-surface-section);
  overflow: hidden;
}

.dual-track-line--pending {
  height: var(--ds-space-0-5);
}

.dual-track-fill {
  height: 100%;
  border-radius: inherit;
}

.dual-track-fill--total {
  background: linear-gradient(
    90deg,
    var(--ds-color-primary, var(--primary-500)) 0%,
    var(--ds-color-primary-light, var(--primary-300)) 100%
  );
}

.dual-track-fill--pending {
  background: linear-gradient(
    90deg,
    var(--ds-alert-high, var(--orange-500)) 0%,
    color-mix(in srgb, var(--ds-alert-high, var(--orange-500)) 65%, white) 100%
  );
}

.category-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-2);
  font-size: var(--ds-font-size-xs);
  min-width: 0;
}

.category-name {
  color: var(--ds-color-text);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.category-meta {
  color: var(--ds-color-text-secondary);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
  white-space: nowrap;
}
</style>
