<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import DsBadge from '@/components/ds/DsBadge.vue'
import DsEmptyState from '@/components/ds/DsEmptyState.vue'
import type { Alert, Entity } from '@/types'
import { useAlertUtils } from '@/composables/useAlertUtils'
import { getProjectContinuity, type ContinuityResponse } from '@/services/continuity'

/**
 * InconsistenciesPanel - Panel de inconsistencias críticas
 *
 * Agrupa alertas de inconsistencias por entidad:
 * - Atributos contradictorios
 * - Comportamiento OOC (out of character)
 * - Temporales (ubicuidad)
 * - Continuidad (objetos/eventos)
 */

interface Props {
  /** ID del proyecto */
  projectId: number
  /** Alertas del proyecto */
  alerts: Alert[]
  /** Entidades del proyecto */
  entities: Entity[]
  /** Si está cargando */
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

// Estado de continuidad
const continuityData = ref<ContinuityResponse | null>(null)
const continuityLoading = ref(false)
const continuityError = ref<string | null>(null)

// Cargar continuidad cuando cambia el projectId
watch(() => props.projectId, async (newId) => {
  if (!newId) return

  continuityLoading.value = true
  continuityError.value = null

  try {
    continuityData.value = await getProjectContinuity(newId)
  } catch (err) {
    console.error('Error loading continuity:', err)
    continuityError.value = 'Error al cargar continuidad'
  } finally {
    continuityLoading.value = false
  }
}, { immediate: true })

const emit = defineEmits<{
  /** Navegar a una alerta específica */
  'alert-navigate': [alert: Alert]
  /** Seleccionar una entidad */
  'entity-select': [entityId: number]
}>()

const { getSeverityConfig, getCategoryConfig } = useAlertUtils()

// ============================================================================
// Filtrado de inconsistencias
// ============================================================================

/** Categorías que son inconsistencias */
const INCONSISTENCY_CATEGORIES = [
  'attribute',      // Atributos contradictorios
  'behavior',       // Comportamiento OOC
  'temporal',       // Inconsistencias temporales
  'continuity',     // Continuidad narrativa
  'coherence',      // Coherencia general
]

/** Alertas de inconsistencias (activas) */
const inconsistencyAlerts = computed(() => {
  return props.alerts.filter(a =>
    a.status === 'active' &&
    a.category &&
    INCONSISTENCY_CATEGORIES.includes(a.category)
  )
})

// ============================================================================
// Agrupación por entidad
// ============================================================================

interface EntityInconsistency {
  entity: Entity
  alerts: Alert[]
  categories: Set<string>
  maxSeverity: 'critical' | 'high' | 'medium' | 'low' | 'info'
}

const inconsistenciesByEntity = computed((): EntityInconsistency[] => {
  const groupMap = new Map<number, EntityInconsistency>()

  // Agrupar por entidad
  inconsistencyAlerts.value.forEach(alert => {
    if (!alert.entityIds || alert.entityIds.length === 0) return

    // Tomar la primera entidad (principal)
    const entityId = alert.entityIds[0]
    const entity = props.entities.find(e => e.id === entityId)
    if (!entity) return

    if (!groupMap.has(entityId)) {
      groupMap.set(entityId, {
        entity,
        alerts: [],
        categories: new Set(),
        maxSeverity: 'info'
      })
    }

    const group = groupMap.get(entityId)!
    group.alerts.push(alert)
    if (alert.category) {
      group.categories.add(alert.category)
    }

    // Actualizar severidad máxima
    const severityOrder = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
    if (severityOrder[alert.severity] < severityOrder[group.maxSeverity]) {
      group.maxSeverity = alert.severity
    }
  })

  // Ordenar por severidad y luego por cantidad de alertas
  return Array.from(groupMap.values()).sort((a, b) => {
    const severityOrder = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
    const severityDiff = severityOrder[a.maxSeverity] - severityOrder[b.maxSeverity]
    if (severityDiff !== 0) return severityDiff
    return b.alerts.length - a.alerts.length
  })
})

// ============================================================================
// Alertas sin entidad asociada (globales)
// ============================================================================

const globalInconsistencies = computed(() => {
  return inconsistencyAlerts.value.filter(a =>
    !a.entityIds || a.entityIds.length === 0
  )
})

// ============================================================================
// Estadísticas
// ============================================================================

const stats = computed(() => {
  const bySeverity = {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
  }

  inconsistencyAlerts.value.forEach(a => {
    if (a.severity in bySeverity) {
      bySeverity[a.severity as keyof typeof bySeverity]++
    }
  })

  return {
    total: inconsistencyAlerts.value.length,
    byEntity: inconsistenciesByEntity.value.length,
    global: globalInconsistencies.value.length,
    bySeverity,
  }
})

// ============================================================================
// Helpers
// ============================================================================

function getEntityIcon(type: string): string {
  const icons: Record<string, string> = {
    character: 'pi-user',
    location: 'pi-map-marker',
    organization: 'pi-building',
    object: 'pi-box',
    event: 'pi-calendar',
  }
  return icons[type] || 'pi-tag'
}

function getCategoryLabel(category: string): string {
  return getCategoryConfig(category as any).label
}
</script>

<template>
  <div class="inconsistencies-panel">
    <!-- Header con estadísticas -->
    <div class="panel-header">
      <div class="header-title">
        <i class="pi pi-exclamation-circle"></i>
        <h3>Inconsistencias</h3>
      </div>
      <div v-if="stats.total > 0" class="header-stats">
        <DsBadge v-if="stats.bySeverity.critical > 0" severity="critical" size="sm">
          {{ stats.bySeverity.critical }}
        </DsBadge>
        <DsBadge v-if="stats.bySeverity.high > 0" severity="high" size="sm">
          {{ stats.bySeverity.high }}
        </DsBadge>
        <span class="total-count">{{ stats.total }} total</span>
      </div>
    </div>

    <!-- Empty state -->
    <DsEmptyState
      v-if="!loading && !continuityLoading && stats.total === 0 && (!continuityData || continuityData.total_issues === 0)"
      icon="pi-check-circle"
      title="Sin inconsistencias"
      description="No se detectaron inconsistencias críticas en el manuscrito"
    />

    <!-- Sección de continuidad de eventos -->
    <div v-if="continuityData && continuityData.total_issues > 0" class="continuity-section">
      <div class="section-header">
        <i class="pi pi-link"></i>
        <h4>Continuidad de Eventos</h4>
        <DsBadge
          :severity="continuityData.issues_by_severity.critical.length > 0 ? 'critical' : 'high'"
          size="sm"
        >
          {{ continuityData.total_issues }}
        </DsBadge>
      </div>

      <div class="continuity-description">
        Eventos sin resolución detectados en {{ continuityData.total_chapters }} capítulos
      </div>

      <!-- Issues críticos -->
      <div
        v-if="continuityData.issues_by_severity.critical.length > 0"
        class="severity-group"
      >
        <div class="severity-label critical">
          <i class="pi pi-exclamation-triangle"></i>
          <span>Crítico ({{ continuityData.issues_by_severity.critical.length }})</span>
        </div>
        <div
          v-for="(issue, idx) in continuityData.issues_by_severity.critical"
          :key="`critical-${idx}`"
          class="continuity-issue"
        >
          <div class="issue-icon">
            <i class="pi pi-times-circle"></i>
          </div>
          <div class="issue-content">
            <span class="issue-description">{{ issue.description }}</span>
            <span class="issue-type">{{ issue.event_type }} → {{ issue.paired_type }}</span>
          </div>
        </div>
      </div>

      <!-- Issues alta prioridad -->
      <div
        v-if="continuityData.issues_by_severity.high.length > 0"
        class="severity-group"
      >
        <div class="severity-label high">
          <i class="pi pi-exclamation-circle"></i>
          <span>Alta ({{ continuityData.issues_by_severity.high.length }})</span>
        </div>
        <div
          v-for="(issue, idx) in continuityData.issues_by_severity.high"
          :key="`high-${idx}`"
          class="continuity-issue"
        >
          <div class="issue-icon">
            <i class="pi pi-exclamation-circle"></i>
          </div>
          <div class="issue-content">
            <span class="issue-description">{{ issue.description }}</span>
            <span class="issue-type">{{ issue.event_type }} → {{ issue.paired_type }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Lista de inconsistencias por entidad -->
    <div v-else class="inconsistencies-list">
      <!-- Agrupadas por entidad -->
      <div
        v-for="group in inconsistenciesByEntity"
        :key="group.entity.id"
        class="entity-group"
      >
        <div
          class="entity-header"
          @click="emit('entity-select', group.entity.id)"
        >
          <div class="entity-icon-wrapper">
            <i :class="`pi ${getEntityIcon(group.entity.type)}`"></i>
          </div>
          <div class="entity-info">
            <span class="entity-name">{{ group.entity.name }}</span>
            <span class="entity-type">{{ group.entity.type }}</span>
          </div>
          <DsBadge :severity="group.maxSeverity" size="sm">
            {{ group.alerts.length }}
          </DsBadge>
        </div>

        <div class="entity-alerts">
          <div
            v-for="alert in group.alerts"
            :key="alert.id"
            class="alert-item"
            :class="`alert-${alert.severity}`"
            @click.stop="emit('alert-navigate', alert)"
          >
            <div class="alert-icon">
              <i :class="getSeverityConfig(alert.severity).icon"></i>
            </div>
            <div class="alert-content">
              <span class="alert-title">{{ alert.title }}</span>
              <span v-if="alert.category" class="alert-category">
                {{ getCategoryLabel(alert.category) }}
              </span>
              <span v-if="alert.chapter" class="alert-chapter">
                Cap. {{ alert.chapter }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Inconsistencias globales (sin entidad) -->
      <div v-if="globalInconsistencies.length > 0" class="entity-group">
        <div class="entity-header entity-header-global">
          <div class="entity-icon-wrapper">
            <i class="pi pi-globe"></i>
          </div>
          <div class="entity-info">
            <span class="entity-name">Globales</span>
            <span class="entity-type">Sin entidad asociada</span>
          </div>
          <DsBadge severity="info" size="sm">
            {{ globalInconsistencies.length }}
          </DsBadge>
        </div>

        <div class="entity-alerts">
          <div
            v-for="alert in globalInconsistencies"
            :key="alert.id"
            class="alert-item"
            :class="`alert-${alert.severity}`"
            @click="emit('alert-navigate', alert)"
          >
            <div class="alert-icon">
              <i :class="getSeverityConfig(alert.severity).icon"></i>
            </div>
            <div class="alert-content">
              <span class="alert-title">{{ alert.title }}</span>
              <span v-if="alert.category" class="alert-category">
                {{ getCategoryLabel(alert.category) }}
              </span>
              <span v-if="alert.chapter" class="alert-chapter">
                Cap. {{ alert.chapter }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.inconsistencies-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* Header */
.panel-header {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
  padding: var(--ds-space-4);
  border-bottom: 1px solid var(--surface-border);
}

.header-title {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.header-title i {
  font-size: 1.25rem;
  color: var(--orange-500);
}

.header-title h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-color);
}

.header-stats {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  flex-wrap: wrap;
}

.total-count {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  margin-left: auto;
}

/* Lista */
.inconsistencies-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--ds-space-2);
}

/* Grupo de entidad */
.entity-group {
  margin-bottom: var(--ds-space-3);
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  overflow: hidden;
}

.entity-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2) var(--ds-space-3);
  background: var(--surface-50);
  cursor: pointer;
  transition: background 0.15s;
}

.entity-header:hover {
  background: var(--surface-100);
}

.entity-header-global {
  cursor: default;
}

.entity-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: var(--surface-0, white);
  border-radius: var(--border-radius);
  flex-shrink: 0;
}

.entity-icon-wrapper i {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.entity-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.entity-name {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--text-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.entity-type {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  text-transform: capitalize;
}

/* Alertas de la entidad */
.entity-alerts {
  padding: var(--ds-space-2);
  background: var(--surface-0, white);
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-1);
}

.alert-item {
  display: flex;
  align-items: flex-start;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2);
  border-radius: var(--border-radius);
  border-left: 3px solid transparent;
  cursor: pointer;
  transition: all 0.15s;
}

.alert-item:hover {
  background: var(--surface-50);
}

.alert-critical {
  border-left-color: var(--red-500);
}

.alert-high {
  border-left-color: var(--orange-500);
}

.alert-medium {
  border-left-color: var(--yellow-500);
}

.alert-low {
  border-left-color: var(--blue-500);
}

.alert-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  margin-top: 2px;
}

.alert-icon i {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.alert-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 0;
}

.alert-title {
  font-size: 0.85rem;
  color: var(--text-color);
  line-height: 1.3;
}

.alert-category,
.alert-chapter {
  font-size: 0.7rem;
  color: var(--text-color-secondary);
}

/* Dark mode */
.dark .entity-header {
  background: var(--surface-800);
}

.dark .entity-header:hover {
  background: var(--surface-700);
}

.dark .entity-icon-wrapper {
  background: var(--surface-900);
}

.dark .entity-alerts {
  background: var(--surface-900);
}

.dark .alert-item:hover {
  background: var(--surface-800);
}

/* Continuity section */
.continuity-section {
  margin-bottom: var(--ds-space-4);
  padding: var(--ds-space-3);
  background: var(--surface-0);
  border-radius: var(--border-radius);
  border: 1px solid var(--surface-200);
}

.continuity-section .section-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  margin-bottom: var(--ds-space-2);
}

.continuity-section .section-header i {
  color: var(--primary-color);
}

.continuity-section .section-header h4 {
  flex: 1;
  margin: 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-color);
}

.continuity-description {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  margin-bottom: var(--ds-space-3);
}

.severity-group {
  margin-bottom: var(--ds-space-3);
}

.severity-label {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
  font-size: 0.75rem;
  font-weight: 600;
  margin-bottom: var(--ds-space-2);
  padding: var(--ds-space-1) var(--ds-space-2);
  border-radius: var(--border-radius);
}

.severity-label.critical {
  color: var(--red-600);
  background: var(--red-50);
}

.severity-label.high {
  color: var(--orange-600);
  background: var(--orange-50);
}

.continuity-issue {
  display: flex;
  align-items: flex-start;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2);
  margin-bottom: var(--ds-space-1);
  border-radius: var(--border-radius);
  background: var(--surface-50);
}

.issue-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  margin-top: 2px;
}

.issue-icon i {
  font-size: 0.7rem;
  color: var(--text-color-secondary);
}

.issue-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 0;
}

.issue-description {
  font-size: 0.8rem;
  color: var(--text-color);
  line-height: 1.3;
}

.issue-type {
  font-size: 0.7rem;
  color: var(--text-color-secondary);
  font-family: monospace;
}

.dark .continuity-section {
  background: var(--surface-800);
  border-color: var(--surface-700);
}

.dark .severity-label.critical {
  color: var(--red-400);
  background: var(--red-900);
}

.dark .severity-label.high {
  color: var(--orange-400);
  background: var(--orange-900);
}

.dark .continuity-issue {
  background: var(--surface-700);
}
</style>
