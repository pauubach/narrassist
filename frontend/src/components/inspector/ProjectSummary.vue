<script setup lang="ts">
/**
 * ProjectSummary - Resumen optimizado del proyecto para el inspector.
 *
 * Se muestra cuando no hay ningún elemento seleccionado.
 * Enfocado en trabajo diario: progreso, siguiente alerta, acciones rápidas.
 */
import { computed, ref, onMounted } from 'vue'
import { useAlertUtils } from '@/composables/useAlertUtils'
import type { Alert } from '@/types'

const props = withDefaults(defineProps<{
  /** Alertas cargadas para mostrar progreso detallado */
  alerts?: Alert[]
  /** Resumen global del manuscrito */
  globalSummary?: string | null
}>(), {
  alerts: () => [],
  globalSummary: null,
})

const emit = defineEmits<{
  /** Navegar a alerta específica */
  (e: 'navigate-to-alert', alert: Alert): void
  /** Ver todas las alertas */
  (e: 'view-alerts'): void
  /** Filtrar alertas por categoría */
  (e: 'filter-alerts', category: Alert['category']): void
  /** Ejecutar acción sobre alerta (accept/reject) */
  (e: 'alert-action', alert: Alert, action: 'accept' | 'reject'): void
}>()

const { getCategoryLabel, getSeverityLabel } = useAlertUtils()

// Sinopsis colapsable
const synopsisExpanded = ref(false)

onMounted(() => {
  // Mostrar sinopsis solo en primera visita
  const visited = localStorage.getItem('project-summary-visited')
  if (!visited) {
    synopsisExpanded.value = true
    localStorage.setItem('project-summary-visited', 'true')
  }
})

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

// Siguiente alerta pendiente (por severidad y luego posición)
const nextPendingAlert = computed(() => {
  const pending = props.alerts.filter(a => a.status === 'active')
  if (!pending.length) return null

  // Ordenar por severidad (critical > high > medium > low > info) y luego por posición
  const severityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
  return pending.sort((a, b) => {
    const severityDiff = (severityOrder[a.severity] ?? 99) - (severityOrder[b.severity] ?? 99)
    if (severityDiff !== 0) return severityDiff
    return (a.spanStart ?? 0) - (b.spanStart ?? 0)
  })[0]
})

// Estimación de tiempo para completar alertas pendientes
const estimatedTimeRemaining = computed(() => {
  if (!activeCount.value) return null

  // Estimación conservadora: 30 segundos por alerta
  const minutes = Math.ceil((activeCount.value * 0.5))
  if (minutes < 1) return '< 1 min'
  if (minutes < 60) return `~${minutes} min`
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return mins > 0 ? `~${hours}h ${mins}m` : `~${hours}h`
})

function handleAlertAction(alert: Alert, action: 'accept' | 'reject') {
  // Emitir acción al padre para que la ejecute
  emit('alert-action', alert, action)
}
</script>

<template>
  <div class="project-summary">
    <!-- Sinopsis colapsable (default: cerrada) -->
    <div v-if="globalSummary" class="summary-section synopsis-section">
      <button
        type="button"
        class="section-header section-header--collapsible"
        @click="synopsisExpanded = !synopsisExpanded"
      >
        <div class="section-title">
          <i class="pi pi-book"></i>
          <span>Sinopsis</span>
        </div>
        <i
          class="pi collapse-icon"
          :class="synopsisExpanded ? 'pi-chevron-up' : 'pi-chevron-down'"
        ></i>
      </button>
      <p v-if="synopsisExpanded" class="synopsis-text">{{ globalSummary }}</p>
    </div>

    <!-- Preview de siguiente alerta pendiente -->
    <div v-if="nextPendingAlert" class="summary-section next-alert-section">
      <div class="section-header">
        <div class="section-title">
          <i class="pi pi-arrow-right"></i>
          <span>Siguiente alerta</span>
        </div>
        <span class="alert-severity-badge" :class="`severity-${nextPendingAlert.severity}`">
          {{ getSeverityLabel(nextPendingAlert.severity) }}
        </span>
      </div>

      <div class="next-alert-preview">
        <div class="alert-category">{{ getCategoryLabel(nextPendingAlert.category) }}</div>
        <div class="alert-message">{{ nextPendingAlert.description }}</div>

        <div class="alert-actions">
          <button
            type="button"
            class="action-btn action-btn--accept"
            title="Aceptar sugerencia"
            @click="handleAlertAction(nextPendingAlert, 'accept')"
          >
            <i class="pi pi-check"></i>
            Aceptar
          </button>
          <button
            type="button"
            class="action-btn action-btn--reject"
            title="Rechazar alerta"
            @click="handleAlertAction(nextPendingAlert, 'reject')"
          >
            <i class="pi pi-times"></i>
            Rechazar
          </button>
          <button
            type="button"
            class="action-btn action-btn--view"
            title="Ver en contexto"
            @click="emit('navigate-to-alert', nextPendingAlert)"
          >
            <i class="pi pi-eye"></i>
            Ver
          </button>
        </div>
      </div>
    </div>

    <!-- Progreso simplificado -->
    <div v-if="hasDetailedAlerts" class="summary-section">
      <div class="section-header">
        <span class="section-title">Progreso</span>
        <button
          type="button"
          class="section-link"
          @click="emit('view-alerts')"
        >
          Ver todas
        </button>
      </div>

      <div class="progress-summary">
        <div class="progress-text">
          <strong>{{ reviewRate }}%</strong> revisadas
          <span class="progress-meta">{{ reviewedCount }}/{{ totalDetailedAlerts }}</span>
        </div>
        <div v-if="estimatedTimeRemaining" class="progress-time">
          {{ estimatedTimeRemaining }} restantes
        </div>
      </div>

      <div class="progress-track">
        <div class="progress-fill" :style="{ width: `${reviewRate}%` }"></div>
      </div>

      <div class="compact-stats">
        <span class="compact-stat compact-stat--pending">
          <i class="pi pi-circle-fill"></i>
          {{ activeCount }} pendientes
        </span>
        <span class="compact-stat compact-stat--resolved">
          <i class="pi pi-check-circle"></i>
          {{ resolvedCount }} aceptadas
        </span>
        <span class="compact-stat compact-stat--dismissed">
          <i class="pi pi-times-circle"></i>
          {{ dismissedCount }} rechazadas
        </span>
      </div>
    </div>

    <!-- Distribución por tipo (top 5) -->
    <div v-if="categoryOverview.length > 0" class="summary-section">
      <div class="section-title">Top alertas por tipo</div>

      <div class="category-list">
        <button
          v-for="item in categoryOverview"
          :key="item.category"
          type="button"
          class="category-item"
          @click="emit('filter-alerts', item.category)"
        >
          <div class="category-header">
            <span class="category-name">{{ item.label }}</span>
            <span class="category-counts">
              <strong>{{ item.totalCount }}</strong>
              <span v-if="item.pendingCount > 0" class="pending-badge">
                {{ item.pendingCount }}
              </span>
            </span>
          </div>

          <!-- Barra de progreso dual: completadas (verde) + pendientes (naranja) -->
          <div class="dual-progress-bar">
            <div
              class="dual-progress-completed"
              :style="{
                width: `${item.totalPercentage - item.pendingWithinType * item.totalPercentage / 100}%`
              }"
            ></div>
            <div
              v-if="item.pendingCount > 0"
              class="dual-progress-pending"
              :style="{
                width: `${item.pendingWithinType * item.totalPercentage / 100}%`
              }"
            ></div>
          </div>

          <div class="category-footer">
            <span class="category-meta">{{ item.totalPercentage }}% del total</span>
            <span v-if="item.pendingCount > 0" class="category-pending-meta">
              {{ item.pendingWithinType }}% pendiente
            </span>
          </div>
        </button>
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
  gap: var(--ds-space-2-5);
  padding: var(--ds-space-3);
  width: 100%;
  min-width: 0;
  overflow: hidden;
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

.section-header--collapsible {
  width: 100%;
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  text-align: left;
  transition: opacity var(--ds-transition-fast);
}

.section-header--collapsible:hover {
  opacity: 0.8;
}

.collapse-icon {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  flex-shrink: 0;
}

.section-title {
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-text);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: var(--ds-space-1-5);
}

.section-title i {
  color: var(--ds-color-primary);
  font-size: var(--ds-font-size-sm);
  flex-shrink: 0;
}

.synopsis-section {
  background: var(--ds-surface-section);
  border-color: var(--ds-color-primary-light);
}

.synopsis-text {
  margin: 0;
  font-size: var(--ds-font-size-sm);
  line-height: var(--ds-leading-relaxed);
  color: var(--ds-color-text);
  text-align: justify;
}

/* Preview de siguiente alerta */
.next-alert-section {
  background: linear-gradient(135deg,
    color-mix(in srgb, var(--ds-color-primary) 5%, var(--ds-surface-ground)),
    var(--ds-surface-ground)
  );
  border-color: var(--ds-color-primary-light);
}

.alert-severity-badge {
  font-size: var(--ds-font-size-xs);
  font-weight: var(--ds-font-weight-semibold);
  padding: var(--ds-space-0-5) var(--ds-space-1-5);
  border-radius: var(--ds-radius-full);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.severity-critical {
  background: var(--ds-alert-critical);
  color: white;
}

.severity-high {
  background: var(--ds-alert-high);
  color: white;
}

.severity-medium {
  background: var(--ds-alert-medium);
  color: var(--ds-color-text);
}

.severity-low,
.severity-info {
  background: var(--ds-alert-low);
  color: var(--ds-color-text);
}

.next-alert-preview {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.alert-category {
  font-size: var(--ds-font-size-xs);
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-primary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.alert-message {
  font-size: var(--ds-font-size-sm);
  line-height: var(--ds-leading-relaxed);
  color: var(--ds-color-text);
}

.alert-actions {
  display: flex;
  gap: var(--ds-space-1-5);
  flex-wrap: wrap;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--ds-space-1);
  padding: var(--ds-space-1) var(--ds-space-2);
  border-radius: var(--ds-radius-md);
  border: var(--ds-border-1) solid var(--ds-surface-border);
  background: var(--ds-surface-ground);
  font-size: var(--ds-font-size-xs);
  font-weight: var(--ds-font-weight-medium);
  cursor: pointer;
  transition: all var(--ds-transition-fast);
  flex: 1;
  justify-content: center;
  min-width: 0;
}

.action-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.action-btn i {
  font-size: var(--ds-font-size-xs);
}

.action-btn--accept {
  border-color: var(--ds-color-success);
  color: var(--ds-color-success);
}

.action-btn--accept:hover {
  background: var(--ds-color-success);
  color: white;
}

.action-btn--reject {
  border-color: var(--ds-color-danger);
  color: var(--ds-color-danger);
}

.action-btn--reject:hover {
  background: var(--ds-color-danger);
  color: white;
}

.action-btn--view {
  border-color: var(--ds-color-primary);
  color: var(--ds-color-primary);
}

.action-btn--view:hover {
  background: var(--ds-color-primary);
  color: white;
}

.section-link {
  border: none;
  background: transparent;
  color: var(--ds-color-primary);
  font-size: var(--ds-font-size-xs);
  font-weight: var(--ds-font-weight-medium);
  cursor: pointer;
  padding: 0;
  white-space: nowrap;
  flex-shrink: 0;
  transition: opacity var(--ds-transition-fast);
}

.section-link:hover {
  opacity: 0.8;
  text-decoration: underline;
}

/* Progreso simplificado */
.progress-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-2);
  flex-wrap: wrap;
}

.progress-text {
  display: flex;
  align-items: baseline;
  gap: var(--ds-space-1-5);
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
}

.progress-text strong {
  font-size: var(--ds-font-size-lg);
  font-weight: var(--ds-font-weight-bold);
}

.progress-meta {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.progress-time {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-primary);
  font-weight: var(--ds-font-weight-medium);
  white-space: nowrap;
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

/* Stats compactas */
.compact-stats {
  display: flex;
  gap: var(--ds-space-2);
  flex-wrap: wrap;
  font-size: var(--ds-font-size-xs);
}

.compact-stat {
  display: inline-flex;
  align-items: center;
  gap: var(--ds-space-1);
  color: var(--ds-color-text-secondary);
  font-variant-numeric: tabular-nums;
}

.compact-stat i {
  font-size: var(--ds-font-size-xs);
}

.compact-stat--pending {
  color: var(--ds-alert-high, var(--orange-500));
}

.compact-stat--pending i {
  color: var(--ds-alert-high, var(--orange-500));
}

.compact-stat--resolved {
  color: var(--ds-color-success);
}

.compact-stat--resolved i {
  color: var(--ds-color-success);
}

.compact-stat--dismissed {
  color: var(--ds-color-text-muted, var(--ds-color-text-secondary));
}

.compact-stat--dismissed i {
  color: var(--ds-color-text-muted, var(--ds-color-text-secondary));
}

/* Categorías con barras compuestas */
.category-list {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-1-5);
  min-width: 0;
}

.category-item {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-1);
  padding: var(--ds-space-2);
  border: var(--ds-border-1) solid var(--ds-surface-border);
  border-radius: var(--ds-radius-md);
  background: var(--ds-surface-ground);
  cursor: pointer;
  transition: all var(--ds-transition-fast);
  text-align: left;
  width: 100%;
  min-width: 0;
}

.category-item:hover {
  border-color: var(--ds-color-primary-light);
  background: var(--ds-surface-hover);
  transform: translateX(2px);
}

.category-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-2);
  min-width: 0;
}

.category-name {
  font-size: var(--ds-font-size-xs);
  font-weight: var(--ds-font-weight-medium);
  color: var(--ds-color-text);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.category-counts {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
  font-size: var(--ds-font-size-xs);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}

.category-counts strong {
  color: var(--ds-color-text);
}

.pending-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: var(--ds-space-4);
  padding: 0 var(--ds-space-1);
  height: var(--ds-space-3);
  background: var(--ds-alert-high, var(--orange-500));
  color: white;
  border-radius: var(--ds-radius-full);
  font-size: var(--ds-font-xs);
  font-weight: var(--ds-font-weight-bold);
}

/* Barra de progreso dual: usa color primario con opacidades */
.dual-progress-bar {
  display: flex;
  width: 100%;
  height: var(--ds-space-1-5);
  background: var(--ds-surface-section);
  border-radius: var(--ds-radius-full);
  overflow: hidden;
}

.dual-progress-completed {
  height: 100%;
  background: linear-gradient(
    90deg,
    var(--ds-color-primary, var(--primary-500)) 0%,
    color-mix(in srgb, var(--ds-color-primary, var(--primary-500)) 85%, white) 100%
  );
  transition: width var(--ds-transition-fast);
}

.dual-progress-pending {
  height: 100%;
  background: color-mix(
    in srgb,
    var(--ds-color-primary, var(--primary-500)) 25%,
    var(--ds-surface-section)
  );
  transition: width var(--ds-transition-fast);
}

.category-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-2);
  font-size: var(--ds-font-xs);
  color: var(--ds-color-text-secondary);
}

.category-pending-meta {
  color: var(--ds-alert-high, var(--orange-500));
  font-weight: var(--ds-font-weight-medium);
}
</style>
