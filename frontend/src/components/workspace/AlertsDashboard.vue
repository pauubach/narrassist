<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import MultiSelect from 'primevue/multiselect'
import Dialog from 'primevue/dialog'
import Menu from 'primevue/menu'
import type { MenuItem } from 'primevue/menuitem'
import DsBadge from '@/components/ds/DsBadge.vue'
import DsEmptyState from '@/components/ds/DsEmptyState.vue'
import ChapterRangeSelector from '@/components/alerts/ChapterRangeSelector.vue'
import AlertsAnalytics from '@/components/alerts/AlertsAnalytics.vue'
import SequentialCorrectionMode from './SequentialCorrectionMode.vue'
import type { Alert, AlertSeverity, AlertStatus, AlertSource } from '@/types'
import { useAlertUtils, META_CATEGORIES, type MetaCategoryKey } from '@/composables/useAlertUtils'
import { useSequentialMode } from '@/composables/useSequentialMode'
import { useWorkspaceStore } from '@/stores/workspace'
import { useToast } from 'primevue/usetoast'

/**
 * AlertsDashboard - Panel central del tab Alertas.
 *
 * Muestra toolbar de filtros, meta-categorías, analytics y acciones.
 * La lista de alertas se muestra en el sidebar (AlertsPanel).
 * El detalle se muestra en el panel derecho (AlertInspector).
 */

interface Props {
  alerts: Alert[]
  projectId?: number
  loading?: boolean
  chapters?: Array<{ id: number; chapterNumber: number; title: string }>
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
  'alert-navigate': [alert: Alert, source?: AlertSource]
  'resolve-all': []
  'refresh': []
  'open-correction-config': []
  /** Emite las alertas filtradas para que el parent las pase al sidebar */
  'filter-change': [filtered: Alert[]]
}>()

const toast = useToast()
const { getSeverityLabel, getCategoryConfig } = useAlertUtils()
const workspaceStore = useWorkspaceStore()

// Sequential mode
const sequentialMode = useSequentialMode(
  () => props.alerts,
  () => props.projectId,
  (alertId: number, newStatus: AlertStatus) => {
    const alert = props.alerts.find(a => a.id === alertId)
    if (alert) {
      alert.status = newStatus
    }
  }
)

// Estado para diálogos
const showResolveAllDialog = ref(false)
const exportMenuRef = ref<InstanceType<typeof Menu> | null>(null)

// Menú de export
const exportMenuItems: MenuItem[] = [
  {
    label: 'Exportar CSV',
    icon: 'pi pi-file',
    command: () => exportAlerts('csv')
  },
  {
    label: 'Exportar JSON',
    icon: 'pi pi-code',
    command: () => exportAlerts('json')
  }
]

function toggleExportMenu(event: Event) {
  exportMenuRef.value?.toggle(event)
}

// Meta-categorías
const selectedMetaCategory = ref<MetaCategoryKey | null>(null)

const metaCategoryCounts = computed(() => {
  const active = props.alerts.filter(a => a.status === 'active')
  return {
    errors: active.filter(a => META_CATEGORIES.errors.categories.includes(a.category)).length,
    inconsistencies: active.filter(a => META_CATEGORIES.inconsistencies.categories.includes(a.category)).length,
    suggestions: active.filter(a => META_CATEGORIES.suggestions.categories.includes(a.category)).length,
  }
})

function toggleMetaCategory(key: MetaCategoryKey) {
  if (selectedMetaCategory.value === key) {
    selectedMetaCategory.value = null
    selectedCategories.value = []
  } else {
    selectedMetaCategory.value = key
    selectedCategories.value = [...META_CATEGORIES[key].categories]
  }
}

// Estado de filtros
const searchQuery = ref('')
const searchInputRef = ref<InstanceType<typeof InputText> | null>(null)
const selectedSeverities = ref<AlertSeverity[]>([])

// Sincronizar con el filtro de severidad del store
watch(() => workspaceStore.alertSeverityFilter, (newFilter) => {
  if (newFilter) {
    selectedSeverities.value = [newFilter as AlertSeverity]
    workspaceStore.setAlertSeverityFilter(null)
  }
}, { immediate: true })

onMounted(() => {
  if (workspaceStore.alertSeverityFilter) {
    selectedSeverities.value = [workspaceStore.alertSeverityFilter as AlertSeverity]
    workspaceStore.setAlertSeverityFilter(null)
  }
})

const selectedCategories = ref<string[]>([])
const selectedStatuses = ref<string[]>(['active'])
const chapterRange = ref<{ min: number | null; max: number | null }>({ min: null, max: null })
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

const confidenceOptions = [
  { label: 'Cualquier confianza', value: null },
  { label: '> 90%', value: 90 },
  { label: '> 80%', value: 80 },
  { label: '> 70%', value: 70 }
]

// Alertas filtradas (un solo pase)
const filteredAlerts = computed(() => {
  const query = searchQuery.value?.toLowerCase()
  const hasSearch = !!query
  const hasSeverityFilter = selectedSeverities.value.length > 0
  const hasCategoryFilter = selectedCategories.value.length > 0
  const hasStatusFilter = selectedStatuses.value.length > 0
  const hasChapterRange = chapterRange.value.min != null || chapterRange.value.max != null
  const hasConfidenceFilter = minConfidence.value !== null
  const { min: chapterMin, max: chapterMax } = chapterRange.value

  const result = props.alerts.filter(a => {
    if (hasSearch && !(a.title.toLowerCase().includes(query!) || a.description?.toLowerCase().includes(query!))) {
      return false
    }
    if (hasSeverityFilter && !selectedSeverities.value.includes(a.severity)) {
      return false
    }
    if (hasCategoryFilter && (!a.category || !selectedCategories.value.includes(a.category))) {
      return false
    }
    if (hasStatusFilter && !selectedStatuses.value.includes(a.status)) {
      return false
    }
    if (hasChapterRange) {
      if (a.chapter == null) return false
      if (chapterMin != null && a.chapter < chapterMin) return false
      if (chapterMax != null && a.chapter > chapterMax) return false
    }
    if (hasConfidenceFilter && (a.confidence ?? 0) < minConfidence.value!) {
      return false
    }
    return true
  })

  const severityOrder = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
  return result.sort((a, b) => {
    const severityDiff = severityOrder[a.severity] - severityOrder[b.severity]
    if (severityDiff !== 0) return severityDiff
    return (a.chapter ?? 999) - (b.chapter ?? 999)
  })
})

// Emitir alertas filtradas al parent cuando cambian
watch(filteredAlerts, (filtered) => {
  emit('filter-change', filtered)
}, { immediate: true })

// Estadísticas (un solo pase)
const stats = computed(() => {
  const bySeverity: Record<string, number> = {}
  let active = 0

  for (const alert of props.alerts) {
    bySeverity[alert.severity] = (bySeverity[alert.severity] || 0) + 1
    if (alert.status === 'active') active++
  }

  return {
    total: props.alerts.length,
    filtered: filteredAlerts.value.length,
    bySeverity,
    active
  }
})

// Helpers
function getCategoryLabel(category: string): string {
  return getCategoryConfig(category as any).label
}

function clearFilters() {
  searchQuery.value = ''
  selectedSeverities.value = []
  selectedCategories.value = []
  selectedStatuses.value = ['active']
  chapterRange.value = { min: null, max: null }
  minConfidence.value = null
  selectedMetaCategory.value = null
}

const hasActiveFilters = computed(() =>
  searchQuery.value || selectedSeverities.value.length || selectedCategories.value.length
    || chapterRange.value.min != null || chapterRange.value.max != null || minConfidence.value !== null
)

function handleResolveAll() {
  showResolveAllDialog.value = true
}

function confirmResolveAll() {
  showResolveAllDialog.value = false
  emit('resolve-all')
}

function handleNavigateFromSequential(source?: AlertSource) {
  const alert = sequentialMode.currentAlert.value
  if (alert) {
    emit('alert-navigate', alert, source)
    sequentialMode.exit()
  }
}

function exportAlerts(format: 'json' | 'csv' = 'csv') {
  if (!props.alerts || props.alerts.length === 0) {
    toast.add({ severity: 'warn', summary: 'Sin datos', detail: 'No hay alertas para exportar', life: 4000 })
    return
  }

  try {
    if (format === 'csv') {
      const headers = ['ID', 'Severidad', 'Categoría', 'Estado', 'Capítulo', 'Título', 'Descripción', 'Confianza', 'Fecha']
      const rows = props.alerts.map(a => [
        a.id,
        a.severity,
        a.category || '',
        a.status,
        a.chapter || '',
        `"${(a.title || '').replace(/"/g, '""')}"`,
        `"${(a.description || '').replace(/"/g, '""')}"`,
        a.confidence ? (a.confidence * 100).toFixed(0) + '%' : '',
        a.createdAt || ''
      ])

      const csvContent = [
        headers.join(','),
        ...rows.map(row => row.join(','))
      ].join('\n')

      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `alertas_proyecto_${props.projectId}.csv`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      toast.add({ severity: 'success', summary: 'Exportado', detail: `${props.alerts.length} alertas exportadas (CSV)`, life: 3000 })
    } else {
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
      const link = document.createElement('a')
      link.href = url
      link.download = `alertas_proyecto_${props.projectId}.json`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      toast.add({ severity: 'success', summary: 'Exportado', detail: `${props.alerts.length} alertas exportadas (JSON)`, life: 3000 })
    }
  } catch (err) {
    console.error('Error exporting alerts:', err)
    toast.add({ severity: 'error', summary: 'Error', detail: 'Error al exportar alertas', life: 5000 })
  }
}

function focusSearch() {
  const el = (searchInputRef.value as any)?.$el as HTMLElement | undefined
  el?.focus()
}

defineExpose({ focusSearch })
</script>

<template>
  <div class="alerts-dashboard" role="region" aria-label="Dashboard de alertas">
    <!-- Toolbar -->
    <div class="dashboard-toolbar" role="search" aria-label="Filtros de alertas">
      <div class="toolbar-row">
        <span class="p-input-icon-right search-wrapper">
          <InputText
            ref="searchInputRef"
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
          class="filter-select"
          :max-selected-labels="2"
        />

        <MultiSelect
          v-if="categoryOptions.length > 0"
          v-model="selectedCategories"
          :options="categoryOptions"
          option-label="label"
          option-value="value"
          placeholder="Categoría"
          class="filter-select"
          :max-selected-labels="2"
        />

        <ChapterRangeSelector
          :chapters="props.chapters"
          :project-id="props.projectId"
          @range-change="chapterRange = $event"
        />

        <Select
          v-model="minConfidence"
          :options="confidenceOptions"
          option-label="label"
          option-value="value"
          placeholder="Confianza"
          class="filter-select"
        />

        <MultiSelect
          v-model="selectedStatuses"
          :options="statusOptions"
          option-label="label"
          option-value="value"
          placeholder="Estado"
          class="filter-select"
        />
      </div>

      <div class="toolbar-actions">
        <Button
          v-if="hasActiveFilters"
          label="Limpiar"
          icon="pi pi-times"
          text
          size="small"
          @click="clearFilters"
        />

        <span class="results-count" aria-live="polite" role="status">
          {{ stats.filtered }} de {{ stats.total }}
          <span v-if="stats.active > 0" class="active-count">
            ({{ stats.active }} activas)
          </span>
        </span>

        <div class="toolbar-spacer"></div>

        <Button
          v-tooltip="'Configurar detectores'"
          icon="pi pi-sliders-h"
          text
          rounded
          size="small"
          @click="emit('open-correction-config')"
        />

        <Button
          v-tooltip="'Actualizar'"
          icon="pi pi-refresh"
          text
          rounded
          size="small"
          @click="emit('refresh')"
        />

        <Button
          v-tooltip="'Exportar alertas'"
          icon="pi pi-download"
          text
          rounded
          size="small"
          :disabled="alerts.length === 0"
          @click="toggleExportMenu"
        />
        <Menu ref="exportMenuRef" :model="exportMenuItems" :popup="true" />

        <Button
          v-tooltip="'Resolver todas las activas'"
          icon="pi pi-check-circle"
          text
          rounded
          size="small"
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

    <!-- Contenido principal con scroll -->
    <div class="dashboard-content">
      <!-- Meta-categorías -->
      <div class="meta-categories" role="group" aria-label="Grupos de alertas">
        <button
          v-for="(meta, key) in META_CATEGORIES"
          :key="key"
          class="meta-card"
          :class="{ 'meta-card--active': selectedMetaCategory === key }"
          :aria-pressed="selectedMetaCategory === (key as MetaCategoryKey)"
          @click="toggleMetaCategory(key as MetaCategoryKey)"
        >
          <div class="meta-card-top">
            <i :class="meta.icon" class="meta-icon" :style="{ color: meta.color }"></i>
            <span class="meta-count">{{ metaCategoryCounts[key as MetaCategoryKey] }}</span>
          </div>
          <span class="meta-label">{{ meta.label }}</span>
        </button>
      </div>

      <!-- Severity badges compactos -->
      <div class="severity-row" role="group" aria-label="Estadísticas por severidad">
        <button
          v-for="severity in (['critical', 'high', 'medium', 'low', 'info'] as AlertSeverity[])"
          :key="severity"
          class="severity-item"
          :class="{ 'severity-item--active': selectedSeverities.includes(severity) }"
          @click="selectedSeverities = selectedSeverities.includes(severity)
            ? selectedSeverities.filter(s => s !== severity)
            : [...selectedSeverities, severity]"
        >
          <DsBadge :severity="severity" size="sm">
            {{ stats.bySeverity[severity] || 0 }}
          </DsBadge>
        </button>
      </div>

      <!-- Analytics (2 columnas) -->
      <div v-if="stats.active > 0" class="analytics-grid">
        <AlertsAnalytics :alerts="alerts" :chapter-count="props.chapters?.length || 0" />
      </div>

      <!-- Empty state cuando no hay alertas -->
      <DsEmptyState
        v-if="alerts.length === 0 && !loading"
        :icon="analysisExecuted ? 'pi pi-check-circle' : 'pi pi-clock'"
        :title="analysisExecuted ? 'Sin alertas' : 'Análisis pendiente'"
        :description="!analysisExecuted
          ? 'Las alertas se generarán cuando se complete el análisis del documento'
          : 'No hay alertas en este proyecto'"
        class="dashboard-empty"
      />

      <!-- Hint para seleccionar alerta en sidebar -->
      <div v-else-if="!loading" class="sidebar-hint">
        <i class="pi pi-arrow-left"></i>
        <span>Selecciona una alerta en el panel izquierdo para ver el detalle</span>
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
      :content-style="{ padding: 0, height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }"
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
.alerts-dashboard {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

/* ── Toolbar ── */
.dashboard-toolbar {
  padding: var(--ds-space-3) var(--ds-space-4);
  background: var(--surface-card);
  border-bottom: 1px solid var(--surface-border);
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.toolbar-row {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  flex-wrap: wrap;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
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
  width: 200px;
  padding-right: 2.5rem;
}

.search-wrapper .pi-search {
  position: absolute;
  right: 1rem;
  color: var(--text-color-secondary);
  pointer-events: none;
}

.filter-select {
  min-width: 120px;
}

.results-count {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
  white-space: nowrap;
}

.active-count {
  color: var(--orange-500);
}

/* ── Content scrollable ── */
.dashboard-content {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  padding: var(--ds-space-4);
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
}

/* ── Meta-categorías ── */
.meta-categories {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--ds-space-3);
}

.meta-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--ds-space-1);
  padding: var(--ds-space-4) var(--ds-space-3);
  border-radius: var(--ds-radius-lg, 8px);
  border: 1px solid var(--surface-200);
  background: var(--surface-card);
  cursor: pointer;
  transition: all var(--ds-transition-fast);
}

.meta-card:hover {
  background: var(--surface-hover);
  border-color: var(--surface-300);
}

.meta-card--active {
  border-color: var(--ds-color-primary);
  background: var(--primary-50, rgba(59, 130, 246, 0.05));
  box-shadow: 0 0 0 1px var(--ds-color-primary);
}

.meta-card--active:hover {
  background: var(--primary-100, rgba(59, 130, 246, 0.1));
}

.meta-card-top {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.meta-icon {
  font-size: 1.25rem;
}

.meta-count {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--ds-color-text);
  line-height: 1;
}

.meta-label {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: var(--ds-font-weight-semibold);
}

/* ── Severity row ── */
.severity-row {
  display: flex;
  gap: var(--ds-space-2);
  flex-wrap: wrap;
}

.severity-item {
  cursor: pointer;
  padding: var(--ds-space-1);
  border: none;
  background: transparent;
  border-radius: var(--ds-radius-md, 6px);
  transition: background var(--ds-transition-fast);
}

.severity-item:hover {
  background: var(--surface-200);
}

.severity-item--active {
  background: var(--primary-100, rgba(59, 130, 246, 0.1));
}

/* ── Analytics ── */
.analytics-grid {
  /* AlertsAnalytics already has its own internal layout */
}

/* ── Empty / hint ── */
.dashboard-empty {
  flex: 1;
}

.sidebar-hint {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-3) var(--ds-space-4);
  background: var(--surface-50);
  border-radius: var(--ds-radius-md, 6px);
  border: 1px dashed var(--surface-300);
  color: var(--ds-color-text-secondary);
  font-size: var(--ds-font-size-sm);
}

.sidebar-hint i {
  font-size: 1rem;
  color: var(--ds-color-primary);
}

/* ── Sequential mode dialog ── */
:deep(.sequential-dialog) {
  border-radius: var(--ds-radius-lg, 8px);
  overflow: hidden;
}

:deep(.sequential-dialog .p-dialog-header) {
  display: none;
}

:deep(.sequential-dialog .p-dialog-content) {
  padding: 0 !important;
  height: 100%;
}

/* ── Dark mode ── */
:global(.dark) .meta-card {
  border-color: var(--surface-600);
  background: var(--surface-800);
}

:global(.dark) .meta-card:hover {
  background: var(--surface-700);
  border-color: var(--surface-500);
}

:global(.dark) .meta-card--active {
  border-color: var(--ds-color-primary);
  background: color-mix(in srgb, var(--primary-900) 40%, transparent);
}

:global(.dark) .meta-card--active:hover {
  background: color-mix(in srgb, var(--primary-800) 40%, transparent);
}

:global(.dark) .severity-item:hover {
  background: var(--surface-700);
}

:global(.dark) .severity-item--active {
  background: color-mix(in srgb, var(--primary-900) 40%, transparent);
}

:global(.dark) .sidebar-hint {
  background: var(--surface-800);
  border-color: var(--surface-600);
}

:global(.dark) :deep(.sequential-dialog) {
  background: var(--surface-900);
}
</style>
