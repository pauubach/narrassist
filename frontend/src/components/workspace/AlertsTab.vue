<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import MultiSelect from 'primevue/multiselect'
import Dialog from 'primevue/dialog'
import DsBadge from '@/components/ds/DsBadge.vue'
import DsEmptyState from '@/components/ds/DsEmptyState.vue'
import SequentialCorrectionMode from './SequentialCorrectionMode.vue'
import type { Alert, AlertSeverity, AlertStatus, AlertSource, AlertCategory } from '@/types'
import { useAlertUtils } from '@/composables/useAlertUtils'
import { useSequentialMode } from '@/composables/useSequentialMode'
import { useWorkspaceStore } from '@/stores/workspace'
import { useToast } from 'primevue/usetoast'
import { useDebouncedRef } from '@/composables/usePerformance'

/**
 * AlertsTab - Pestaña de gestión de alertas
 *
 * Muestra todas las alertas del proyecto con:
 * - Filtros avanzados (severidad, categoría, estado, capítulo, confianza)
 * - Acciones de resolución y descarte
 * - Acciones bulk (resolver todas, exportar)
 * - Navegación al texto
 */

interface Props {
  /** Alertas del proyecto */
  alerts: Alert[]
  /** ID del proyecto (para acciones bulk) */
  projectId?: number
  /** Si está cargando */
  loading?: boolean
  /** Capítulos disponibles (para filtro) */
  chapters?: Array<{ id: number; chapterNumber: number; title: string }>
  /** Si el análisis de alertas ya se ejecutó */
  analysisExecuted?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  projectId: 0,
  loading: false,
  chapters: () => [],
  analysisExecuted: true
})

const emit = defineEmits<{
  'alert-select': [alert: Alert]
  'alert-resolve': [alert: Alert]
  'alert-dismiss': [alert: Alert]
  'alert-reopen': [alert: Alert]
  /** Navega al texto de la alerta, opcionalmente a una fuente específica */
  'alert-navigate': [alert: Alert, source?: AlertSource]
  'resolve-all': []
  'refresh': []
  'open-correction-config': []
}>()

const toast = useToast()

const { getSeverityLabel, getCategoryConfig } = useAlertUtils()
const workspaceStore = useWorkspaceStore()

// Sequential mode
const sequentialMode = useSequentialMode(
  () => props.alerts,
  () => props.projectId,
  (alertId: number, newStatus: AlertStatus) => {
    // Update local alert status when changed in sequential mode
    const alert = props.alerts.find(a => a.id === alertId)
    if (alert) {
      alert.status = newStatus
    }
  }
)

// Estado para diálogos
const showResolveAllDialog = ref(false)

// Estado de filtros
// Debounce la búsqueda para evitar filtrados excesivos en cada keystroke
const { value: searchQuery, debouncedValue: debouncedSearchQuery } = useDebouncedRef('', 300)
const selectedSeverities = ref<AlertSeverity[]>([])

// Sincronizar con el filtro de severidad del store
watch(() => workspaceStore.alertSeverityFilter, (newFilter) => {
  if (newFilter) {
    // Aplicar el filtro desde el store (ej: desde el dashboard)
    selectedSeverities.value = [newFilter as AlertSeverity]
    // Limpiar el filtro del store después de aplicarlo
    workspaceStore.setAlertSeverityFilter(null)
  }
}, { immediate: true })

onMounted(() => {
  // Aplicar filtro pendiente al montar
  if (workspaceStore.alertSeverityFilter) {
    selectedSeverities.value = [workspaceStore.alertSeverityFilter as AlertSeverity]
    workspaceStore.setAlertSeverityFilter(null)
  }
})
const selectedCategories = ref<string[]>([])
const selectedStatuses = ref<string[]>(['active'])
const selectedChapter = ref<number | null>(null)
const minConfidence = ref<number | null>(null)

// Opciones de filtros
const severityOptions: Array<{ label: string; value: AlertSeverity }> = [
  { label: 'Crítica', value: 'critical' },
  { label: 'Alta', value: 'high' },
  { label: 'Media', value: 'medium' },
  { label: 'Baja', value: 'low' },
  { label: 'Info', value: 'info' }
]

const categoryOptions = computed(() => {
  const categories = new Set(props.alerts.map(a => a.category).filter(Boolean))
  return Array.from(categories).map(cat => ({
    label: getCategoryLabel(cat!),
    value: cat
  }))
})

const statusOptions = [
  { label: 'Activas', value: 'active' },
  { label: 'Resueltas', value: 'resolved' },
  { label: 'Descartadas', value: 'dismissed' }
]

const chapterOptions = computed(() => [
  { label: 'Todos los capítulos', value: null },
  ...props.chapters.map(ch => ({
    label: `Cap. ${ch.chapterNumber}: ${ch.title}`,
    value: ch.chapterNumber
  }))
])

const confidenceOptions = [
  { label: 'Cualquier confianza', value: null },
  { label: '> 90%', value: 90 },
  { label: '> 80%', value: 80 },
  { label: '> 70%', value: 70 }
]

// Alertas filtradas (usa búsqueda con debounce para optimizar)
const filteredAlerts = computed(() => {
  let result = props.alerts

  // Filtrar por búsqueda (usa valor con debounce)
  if (debouncedSearchQuery.value) {
    const query = debouncedSearchQuery.value.toLowerCase()
    result = result.filter(a =>
      a.title.toLowerCase().includes(query) ||
      a.description?.toLowerCase().includes(query)
    )
  }

  // Filtrar por severidad
  if (selectedSeverities.value.length > 0) {
    result = result.filter(a => selectedSeverities.value.includes(a.severity))
  }

  // Filtrar por categoría
  if (selectedCategories.value.length > 0) {
    result = result.filter(a => a.category && selectedCategories.value.includes(a.category))
  }

  // Filtrar por estado
  if (selectedStatuses.value.length > 0) {
    result = result.filter(a => selectedStatuses.value.includes(a.status))
  }

  // Filtrar por capítulo
  if (selectedChapter.value !== null) {
    result = result.filter(a => a.chapter === selectedChapter.value)
  }

  // Filtrar por confianza
  if (minConfidence.value !== null) {
    result = result.filter(a => (a.confidence ?? 0) >= minConfidence.value!)
  }

  // Ordenar por severidad y luego por capítulo
  const severityOrder = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
  return [...result].sort((a, b) => {
    const severityDiff = severityOrder[a.severity] - severityOrder[b.severity]
    if (severityDiff !== 0) return severityDiff
    return (a.chapter ?? 999) - (b.chapter ?? 999)
  })
})

// Estadísticas
const stats = computed(() => ({
  total: props.alerts.length,
  filtered: filteredAlerts.value.length,
  bySeverity: props.alerts.reduce((acc, a) => {
    acc[a.severity] = (acc[a.severity] || 0) + 1
    return acc
  }, {} as Record<string, number>),
  active: props.alerts.filter(a => a.status === 'active').length
}))

// Helpers - usar composable centralizado
function getCategoryLabel(category: string): string {
  return getCategoryConfig(category as AlertCategory).label
}

function clearFilters() {
  searchQuery.value = ''
  selectedSeverities.value = []
  selectedCategories.value = []
  selectedStatuses.value = ['active']
  selectedChapter.value = null
  minConfidence.value = null
}

// Handlers
function handleAlertClick(alert: Alert) {
  emit('alert-select', alert)
}

function handleResolveAll() {
  showResolveAllDialog.value = true
}

function confirmResolveAll() {
  showResolveAllDialog.value = false
  emit('resolve-all')
}

function handleReopen(alert: Alert) {
  emit('alert-reopen', alert)
}

function exportAlerts() {
  if (!props.alerts || props.alerts.length === 0) {
    toast.add({ severity: 'warn', summary: 'Sin datos', detail: 'No hay alertas para exportar', life: 4000 })
    return
  }

  try {
    const content = {
      projectId: props.projectId,
      exportedAt: new Date().toISOString(),
      totalAlerts: props.alerts.length,
      bySeverity: {
        critical: props.alerts.filter(a => a.severity === 'critical').length,
        high: props.alerts.filter(a => a.severity === 'high').length,
        medium: props.alerts.filter(a => a.severity === 'medium').length,
        low: props.alerts.filter(a => a.severity === 'low').length,
        info: props.alerts.filter(a => a.severity === 'info').length,
      },
      byStatus: {
        active: props.alerts.filter(a => a.status === 'active').length,
        resolved: props.alerts.filter(a => a.status === 'resolved').length,
        dismissed: props.alerts.filter(a => a.status === 'dismissed').length,
      },
      alerts: props.alerts.map(a => ({
        id: a.id,
        title: a.title,
        description: a.description,
        severity: a.severity,
        category: a.category,
        status: a.status,
        chapter: a.chapter,
        confidence: a.confidence,
        createdAt: a.createdAt,
      })),
    }

    const blob = new Blob([JSON.stringify(content, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `alertas_proyecto_${props.projectId}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    toast.add({ severity: 'success', summary: 'Exportado', detail: `${props.alerts.length} alertas exportadas`, life: 3000 })
  } catch (err) {
    console.error('Error exporting alerts:', err)
    toast.add({ severity: 'error', summary: 'Error', detail: 'Error al exportar alertas', life: 5000 })
  }
}

// Helper para verificar si alerta está activa
function isAlertActive(status: string): boolean {
  return status === 'active'
}

/**
 * Navigate to text from sequential mode.
 * If a specific source is provided (for inconsistency alerts),
 * navigate to that source's location instead of the main alert location.
 */
function handleNavigateFromSequential(source?: AlertSource) {
  const alert = sequentialMode.currentAlert.value
  if (alert) {
    emit('alert-navigate', alert, source)
    sequentialMode.exit()
  }
}
</script>

<template>
  <div class="alerts-tab" role="region" aria-label="Gestión de alertas">
    <!-- Toolbar de filtros -->
    <div class="alerts-toolbar" role="search" aria-label="Filtros de alertas">
      <div class="toolbar-row">
        <span class="p-input-icon-right search-wrapper">
          <InputText
            v-model="searchQuery"
            placeholder="Buscar alertas..."
            class="search-input"
            aria-label="Buscar alertas"
          />
          <i class="pi pi-search" />
        </span>

        <MultiSelect
          v-model="selectedSeverities"
          :options="severityOptions"
          option-label="label"
          option-value="value"
          placeholder="Severidad"
          class="severity-filter"
          :max-selected-labels="2"
        />

        <MultiSelect
          v-if="categoryOptions.length > 0"
          v-model="selectedCategories"
          :options="categoryOptions"
          option-label="label"
          option-value="value"
          placeholder="Categoría"
          class="category-filter"
          :max-selected-labels="2"
        />

        <Select
          v-model="selectedChapter"
          :options="chapterOptions"
          option-label="label"
          option-value="value"
          placeholder="Capítulo"
          class="chapter-filter"
        />

        <Select
          v-model="minConfidence"
          :options="confidenceOptions"
          option-label="label"
          option-value="value"
          placeholder="Confianza"
          class="confidence-filter"
        />
      </div>

      <div class="toolbar-row toolbar-row-secondary">
        <MultiSelect
          v-model="selectedStatuses"
          :options="statusOptions"
          option-label="label"
          option-value="value"
          placeholder="Estado"
          class="status-filter"
        />

        <Button
          v-if="searchQuery || selectedSeverities.length || selectedCategories.length || selectedChapter !== null || minConfidence !== null"
          label="Limpiar filtros"
          icon="pi pi-times"
          text
          size="small"
          @click="clearFilters"
        />

        <div class="toolbar-spacer"></div>

        <span class="results-count" aria-live="polite" role="status">
          {{ stats.filtered }} de {{ stats.total }} alertas
          <span v-if="stats.active > 0" class="active-count">
            ({{ stats.active }} activas)
          </span>
        </span>

        <Button
          v-tooltip="'Configurar detectores'"
          icon="pi pi-sliders-h"
          text
          rounded
          @click="emit('open-correction-config')"
        />

        <Button
          v-tooltip="'Actualizar'"
          icon="pi pi-refresh"
          text
          rounded
          @click="emit('refresh')"
        />

        <Button
          v-tooltip="'Exportar alertas'"
          icon="pi pi-download"
          text
          rounded
          :disabled="alerts.length === 0"
          @click="exportAlerts"
        />

        <Button
          v-tooltip="'Resolver todas las activas'"
          icon="pi pi-check-circle"
          text
          rounded
          severity="success"
          :disabled="stats.active === 0"
          @click="handleResolveAll"
        />

        <Button
          v-tooltip="'Revisar alertas una por una'"
          icon="pi pi-list-check"
          label="Modo secuencial"
          severity="info"
          size="small"
          :disabled="stats.active === 0"
          @click="sequentialMode.enter({ statuses: ['active'] })"
        />
      </div>
    </div>

    <!-- Estadísticas rápidas -->
    <div class="alerts-stats" role="group" aria-label="Estadísticas por severidad">
      <div
        v-for="severity in ['critical', 'high', 'medium', 'low', 'info']"
        :key="severity"
        class="stat-item"
        :class="{ 'stat-active': selectedSeverities.includes(severity as AlertSeverity) }"
        @click="selectedSeverities = selectedSeverities.includes(severity as AlertSeverity)
          ? selectedSeverities.filter(s => s !== severity)
          : [...selectedSeverities, severity as AlertSeverity]"
      >
        <DsBadge :severity="severity as AlertSeverity" size="sm">
          {{ stats.bySeverity[severity] || 0 }}
        </DsBadge>
      </div>
    </div>

    <!-- Lista de alertas -->
    <div class="alerts-list" role="list" aria-label="Lista de alertas">
      <DsEmptyState
        v-if="filteredAlerts.length === 0 && !loading"
        :icon="analysisExecuted ? 'pi pi-check-circle' : 'pi pi-clock'"
        :title="analysisExecuted ? 'Sin alertas' : 'Análisis pendiente'"
        :description="!analysisExecuted
          ? 'Las alertas se generarán cuando se complete el análisis del documento'
          : searchQuery || selectedSeverities.length
            ? 'No se encontraron alertas con los filtros aplicados'
            : 'No hay alertas pendientes en este proyecto'"
      />

      <div
        v-for="alert in filteredAlerts"
        :key="alert.id"
        class="alert-item"
        role="listitem"
        tabindex="0"
        :class="`alert-${alert.severity}`"
        :aria-label="`${getSeverityLabel(alert.severity)}: ${alert.title}`"
        @click="handleAlertClick(alert)"
        @keydown.enter="handleAlertClick(alert)"
      >
        <div class="alert-header">
          <DsBadge :severity="alert.severity" size="sm">
            {{ getSeverityLabel(alert.severity) }}
          </DsBadge>
          <span class="alert-title">{{ alert.title }}</span>
          <span v-if="alert.chapter" class="alert-chapter">
            Cap. {{ alert.chapter }}
          </span>
        </div>

        <p v-if="alert.description" class="alert-description">
          {{ alert.description }}
        </p>

        <div class="alert-footer">
          <span v-if="alert.confidence" class="alert-confidence">
            <i class="pi pi-chart-bar"></i>
            {{ Math.round(alert.confidence * 100) }}% confianza
          </span>
          <span v-if="alert.category" class="alert-category">
            {{ getCategoryLabel(alert.category) }}
          </span>

          <div class="alert-actions">
            <Button
              v-tooltip="'Ver en texto'"
              icon="pi pi-eye"
              text
              rounded
              size="small"
              @click.stop="emit('alert-navigate', alert)"
            />
            <Button
              v-tooltip="'Resolver'"
              icon="pi pi-check"
              text
              rounded
              size="small"
              severity="success"
              @click.stop="emit('alert-resolve', alert)"
            />
            <Button
              v-tooltip="'Descartar'"
              icon="pi pi-times"
              text
              rounded
              size="small"
              severity="secondary"
              @click.stop="emit('alert-dismiss', alert)"
            />
          </div>
        </div>
      </div>
    </div>
    <!-- Diálogo de confirmación para resolver todas -->
    <Dialog
      :visible="showResolveAllDialog"
      header="Resolver todas las alertas"
      :modal="true"
      :style="{ width: '400px' }"
      @update:visible="showResolveAllDialog = $event"
    >
      <p>
        ¿Estás seguro de que deseas marcar como resueltas todas las
        <strong>{{ stats.active }}</strong> alertas activas?
      </p>
      <p class="text-secondary text-sm">
        Esta acción no se puede deshacer.
      </p>
      <template #footer>
        <Button label="Cancelar" text @click="showResolveAllDialog = false" />
        <Button label="Resolver todas" severity="success" @click="confirmResolveAll" />
      </template>
    </Dialog>

    <!-- Modo de corrección secuencial -->
    <Dialog
      :visible="sequentialMode.active.value"
      :modal="true"
      :closable="false"
      :show-header="false"
      :style="{ width: '95vw', maxWidth: '1000px', height: '90vh' }"
      :content-style="{ padding: 0, height: '100%', display: 'flex', flexDirection: 'column' }"
      :pt="{ root: { class: 'sequential-dialog' } }"
      @update:visible="!$event && sequentialMode.exit()"
    >
      <SequentialCorrectionMode
        :current-alert="sequentialMode.currentAlert.value"
        :progress="sequentialMode.progress.value"
        :has-next="sequentialMode.hasNext.value"
        :has-previous="sequentialMode.hasPrevious.value"
        :can-undo="sequentialMode.canUndo.value"
        :updating="sequentialMode.updating.value"
        :recent-actions="sequentialMode.recentActions.value"
        :show-resolved="sequentialMode.settings.value.showResolved"
        :chapters="chapters"
        @next="sequentialMode.next()"
        @previous="sequentialMode.previous()"
        @resolve="sequentialMode.resolveCurrentAndAdvance()"
        @dismiss="sequentialMode.dismissCurrentAndAdvance()"
        @skip="sequentialMode.skipToNext()"
        @flag="sequentialMode.flagCurrentAndAdvance()"
        @undo="sequentialMode.undoLastAction()"
        @exit="sequentialMode.exit()"
        @update:show-resolved="sequentialMode.setSettings({ showResolved: $event })"
        @navigate-to-text="handleNavigateFromSequential($event)"
      />
    </Dialog>
  </div>
</template>

<style scoped>
.alerts-tab {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: visible; /* Permitir que los badges se muestren completos */
}

/* Toolbar */
.alerts-toolbar {
  padding: 0.75rem 1rem;
  background: var(--surface-card);
  border-bottom: 1px solid var(--surface-border);
}

.toolbar-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.toolbar-row-secondary {
  margin-top: 0.5rem;
}

.toolbar-spacer {
  flex: 1;
}

.search-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.search-input {
  width: 180px;
  padding-right: 2.5rem;
}

.search-wrapper .pi-search {
  position: absolute;
  right: 1rem;
  color: var(--text-color-secondary);
  pointer-events: none;
}

.severity-filter,
.category-filter,
.chapter-filter,
.confidence-filter,
.status-filter {
  min-width: 120px;
}

.results-count {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.active-count {
  color: var(--orange-500);
}

/* Stats */
.alerts-stats {
  display: flex;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: var(--surface-50);
  border-bottom: 1px solid var(--surface-border);
  overflow: visible; /* Asegurar que los badges no se corten */
}

.stat-item {
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 4px;
  transition: background 0.15s;
}

.stat-item:hover {
  background: var(--surface-200);
}

.stat-item.stat-active {
  background: var(--primary-100);
}

/* Lista */
.alerts-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
}

.alert-item {
  padding: 0.75rem;
  border-radius: 6px;
  border-left: 3px solid transparent;
  cursor: pointer;
  transition: background 0.15s;
  margin-bottom: 0.5rem;
}

.alert-item:hover {
  background: var(--surface-hover);
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

.alert-info {
  border-left-color: var(--gray-400);
}

.alert-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.alert-title {
  font-weight: 600;
  color: var(--text-color);
  flex: 1;
}

.alert-chapter {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  background: var(--surface-100);
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
}

.alert-description {
  margin: 0 0 0.5rem 0;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.alert-footer {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.alert-confidence,
.alert-category {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.alert-actions {
  margin-left: auto;
  display: flex;
  gap: 0.25rem;
  opacity: 0;
  transition: opacity 0.15s;
}

.alert-item:hover .alert-actions {
  opacity: 1;
}

/* Dark mode */
.dark .alerts-stats {
  background: var(--surface-800);
}

.dark .alert-chapter {
  background: var(--surface-700);
}

.dark .stat-item:hover {
  background: var(--surface-700);
}

.dark .stat-item.stat-active {
  background: var(--primary-900);
}

/* Sequential mode dialog */
:deep(.sequential-dialog) {
  border-radius: 12px;
  overflow: hidden;
}

:deep(.sequential-dialog .p-dialog-header) {
  display: none;
}

:deep(.sequential-dialog .p-dialog-content) {
  padding: 0 !important;
  height: 100%;
}

.dark :deep(.sequential-dialog) {
  background: var(--surface-900);
}
</style>
