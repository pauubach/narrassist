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
import SuppressionRulesDialog from '@/components/alerts/SuppressionRulesDialog.vue'
import type { Alert, AlertSeverity, AlertStatus, AlertSource } from '@/types'
import { META_CATEGORIES, type MetaCategoryKey } from '@/composables/useAlertUtils'
import { useAlertExport } from '@/composables/useAlertExport'
import { useAlertFiltering, FILTER_PRESETS } from '@/composables/useAlertFiltering'
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
  entities?: Array<{ id: number; name: string }>
  analysisExecuted?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  projectId: 0,
  loading: false,
  chapters: () => [],
  entities: () => [],
  analysisExecuted: true
})

const emit = defineEmits<{
  'alert-select': [alert: Alert]
  'alert-resolve': [alert: Alert]
  'alert-dismiss': [alert: Alert]
  'alert-reopen': [alert: Alert]
  'alert-navigate': [alert: Alert, source?: AlertSource]
  'resolve-all': []
  'batch-resolve-ambiguous': [alerts: Alert[]]
  'refresh': []
  'open-correction-config': []
  /** Emite las alertas filtradas para que el parent las pase al sidebar */
  'filter-change': [filtered: Alert[]]
}>()

const toast = useToast()
const showSuppressionRules = ref(false)
const workspaceStore = useWorkspaceStore()

// Alert filtering composable
const {
  searchQuery,
  selectedSeverities,
  selectedCategories,
  selectedStatuses,
  chapterRange,
  minConfidence,
  selectedMetaCategory,
  selectedAlertTypes,
  selectedEntityIds,
  filteredAlerts,
  stats,
  metaCategoryCounts,
  severityOptions,
  statusOptions,
  confidenceOptions,
  categoryOptions,
  alertTypeOptions,
  entityOptions,
  toggleMetaCategory,
  clearFilters,
  hasActiveFilters,
  syncWithWorkspaceStore,
  applyPreset
} = useAlertFiltering(() => props.alerts, {
  defaultStatuses: ['active'],
  persistKey: 'alert_filters_v1',
  entities: () => props.entities || []
})

// Alert export composable
const { exportAlerts, getExportMenuItems } = useAlertExport(() => props.projectId)

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

// Batch resolve ambiguous
const ambiguousWithSuggestion = computed(() =>
  props.alerts.filter(a =>
    a.alertType === 'ambiguous_attribute' &&
    a.status === 'active' &&
    a.extraData?.suggestedEntityId != null
  )
)
const showBatchAmbiguousDialog = ref(false)

function handleBatchResolveAmbiguous() {
  showBatchAmbiguousDialog.value = true
}

function confirmBatchResolveAmbiguous() {
  showBatchAmbiguousDialog.value = false
  emit('batch-resolve-ambiguous', ambiguousWithSuggestion.value)
}

// Estado para diálogos
const showResolveAllDialog = ref(false)
const exportMenuRef = ref<InstanceType<typeof Menu> | null>(null)
const searchInputRef = ref<InstanceType<typeof InputText> | null>(null)

// Menú de export (usando composable)
const exportMenuItems = computed<MenuItem[]>(() =>
  getExportMenuItems(() => props.alerts)
)

function toggleExportMenu(event: Event) {
  exportMenuRef.value?.toggle(event)
}

// Sincronizar con el store (workspace alert severity filter)
syncWithWorkspaceStore(workspaceStore)

onMounted(() => {
  syncWithWorkspaceStore(workspaceStore)
})

// Preset options derivados de FILTER_PRESETS (F-6: eliminar duplicación)
const presetOptions = [
  { label: 'Filtros rápidos...', value: null },
  ...FILTER_PRESETS.map(p => ({ label: p.label, value: p.key }))
]

const selectedPreset = ref<string | null>(null)

function handlePresetChange(presetKey: string | null) {
  if (presetKey) {
    const preset = FILTER_PRESETS.find(p => p.key === presetKey)
    if (preset) {
      applyPreset(preset)
      // Reset visual state after applying
      selectedPreset.value = null
    }
  }
}

// Emitir alertas filtradas al parent cuando cambian
watch(filteredAlerts, (filtered) => {
  emit('filter-change', filtered)
}, { immediate: true })

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

// exportAlerts ahora viene del composable useAlertExport

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

        <MultiSelect
          v-if="alertTypeOptions.length > 0"
          v-model="selectedAlertTypes"
          :options="alertTypeOptions"
          option-label="label"
          option-value="value"
          placeholder="Tipo de alerta"
          class="filter-select"
          :max-selected-labels="2"
        />

        <MultiSelect
          v-if="entityOptions.length > 0"
          v-model="selectedEntityIds"
          :options="entityOptions"
          option-label="label"
          option-value="value"
          placeholder="Entidad"
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
        <Select
          v-model="selectedPreset"
          :options="presetOptions"
          option-label="label"
          option-value="value"
          placeholder="Filtros rápidos..."
          class="preset-select"
          @change="handlePresetChange($event.value)"
        />

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
          v-tooltip="'Reglas de supresión'"
          icon="pi pi-filter-slash"
          text
          rounded
          size="small"
          @click="showSuppressionRules = true"
        />

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
          v-if="ambiguousWithSuggestion.length > 0"
          v-tooltip="`Resolver ${ambiguousWithSuggestion.length} ambiguas con sugerencia`"
          icon="pi pi-bolt"
          text
          rounded
          size="small"
          severity="warn"
          @click="handleBatchResolveAmbiguous"
        />

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

    <!-- Diálogo de batch resolve ambiguous -->
    <Dialog
      :visible="showBatchAmbiguousDialog"
      header="Resolver alertas ambiguas con sugerencia"
      :modal="true"
      :style="{ width: '450px' }"
      @update:visible="showBatchAmbiguousDialog = $event"
    >
      <p>
        Se resolverán <strong>{{ ambiguousWithSuggestion.length }}</strong> alertas de atributos
        ambiguos usando la sugerencia automática (basada en atributos ya asignados).
      </p>
      <p class="text-secondary text-sm">
        Solo se afectan alertas con candidato recomendado. Puedes revisar cada una después.
      </p>
      <template #footer>
        <Button label="Cancelar" text @click="showBatchAmbiguousDialog = false" />
        <Button label="Resolver con sugerencia" severity="warn" icon="pi pi-bolt" @click="confirmBatchResolveAmbiguous" />
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

    <SuppressionRulesDialog
      :visible="showSuppressionRules"
      :project-id="props.projectId"
      @update:visible="showSuppressionRules = $event"
      @rules-changed="emit('refresh')"
    />
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
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--ds-space-3);
}

@media (max-width: 1200px) {
  .meta-categories {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .meta-categories {
    grid-template-columns: 1fr;
  }
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
