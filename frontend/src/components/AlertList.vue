<template>
  <div class="alert-list" role="region" aria-label="Lista de alertas">
    <!-- Header con filtros -->
    <div class="list-header">
      <div class="header-left">
        <h3 v-if="showTitle" id="alert-list-heading">Alertas</h3>
        <span v-if="!showTitle" class="alert-count" aria-live="polite">{{ filteredAlerts.length }} alertas</span>
      </div>
      <div class="header-actions">
        <Button
          v-if="showRefresh"
          v-tooltip.bottom="'Recargar'"
          icon="pi pi-refresh"
          text
          rounded
          size="small"
          @click="$emit('refresh')"
        />
      </div>
    </div>

    <!-- Filtros -->
    <div v-if="showFilters" class="filters-section" role="search" aria-label="Filtros de alertas">
      <!-- Búsqueda -->
      <DsInput
        v-model="searchQuery"
        placeholder="Buscar alertas..."
        icon="pi pi-search"
        clearable
        class="search-input"
      />

      <!-- Filtros por severidad -->
      <div class="severity-filters">
        <Button
          v-for="sev in severityLevels"
          :key="sev.value"
          :icon="sev.icon"
          :label="sev.label"
          :severity="selectedSeverity === sev.value ? sev.severity : 'secondary'"
          :outlined="selectedSeverity !== sev.value"
          :aria-pressed="selectedSeverity === sev.value"
          size="small"
          @click="selectSeverity(sev.value)"
        >
          <template #default>
            <i :class="sev.icon"></i>
            <span>{{ sev.label }}</span>
            <Badge v-if="getSeverityCount(sev.value) > 0" :value="getSeverityCount(sev.value)" />
          </template>
        </Button>
      </div>

      <!-- Filtros por categoría -->
      <div class="category-filters">
        <SelectButton
          v-model="selectedCategory"
          :options="categoryOptions"
          option-label="label"
          option-value="value"
        />
      </div>

      <!-- Filtro por estado -->
      <div class="status-filters">
        <SelectButton
          v-model="selectedStatus"
          :options="statusOptions"
          option-label="label"
          option-value="value"
        />
      </div>
    </div>

    <!-- Lista de alertas -->
    <div v-if="loading" class="list-loading" role="status" aria-live="polite">
      <ProgressSpinner style="width: 30px; height: 30px" />
      <small>Cargando alertas...</small>
    </div>

    <div v-else-if="filteredAlerts.length === 0" class="list-empty" role="status">
      <i class="pi pi-check-circle empty-icon"></i>
      <p v-if="searchQuery || selectedSeverity !== 'all' || selectedCategory !== 'all' || selectedStatus !== 'all'">
        No se encontraron alertas con los filtros aplicados
      </p>
      <p v-else>No hay alertas</p>
      <Button
        v-if="searchQuery || selectedSeverity !== 'all' || selectedCategory !== 'all' || selectedStatus !== 'all'"
        label="Limpiar filtros"
        icon="pi pi-filter-slash"
        text
        @click="clearFilters"
      />
    </div>

    <!-- Lista virtualizada para muchos items (>50) sin paginación -->
    <VirtualScroller
      v-else-if="shouldVirtualize"
      :items="filteredAlerts"
      :item-size="compact ? 120 : 180"
      class="alerts-container alerts-virtual"
      :class="{ 'compact': compact }"
      role="list"
      aria-label="Alertas filtradas"
    >
      <template #item="{ item: alert, options }">
        <div
          :key="alert.id"
          class="alert-item"
          role="listitem"
          tabindex="0"
          :aria-label="`${getSeverityLabel(alert.severity)}: ${alert.title}`"
          :class="[
            `alert-${alert.severity}`,
            { 'alert-selected': selectedAlertId === alert.id },
            { 'alert-clickable': clickable },
            { 'alert-odd': options.odd }
          ]"
          @click="onAlertClick(alert)"
          @keydown.enter="onAlertClick(alert)"
        >
          <!-- Severidad indicator -->
          <div class="alert-severity-bar" :class="`severity-${alert.severity}`"></div>

          <!-- Contenido -->
          <div class="alert-content">
            <!-- Header -->
            <div class="alert-header">
              <Tag :severity="getSeverityColor(alert.severity)" class="severity-tag">
                <i :class="getSeverityIcon(alert.severity)"></i>
                {{ alert.severity.toUpperCase() }}
              </Tag>
              <Tag severity="secondary" class="category-tag">
                {{ getCategoryLabel(alert.category) }}
              </Tag>
              <span v-if="alert.chapter" class="alert-chapter">
                <i class="pi pi-book"></i>
                Cap. {{ alert.chapter }}
              </span>
            </div>

            <!-- Título y descripción -->
            <div class="alert-body">
              <h4 class="alert-title">{{ alert.title }}</h4>
              <p class="alert-description">{{ alert.description }}</p>
            </div>

            <!-- Entidades relacionadas -->
            <div v-if="alert.entityIds && alert.entityIds.length > 0" class="alert-entities">
              <i class="pi pi-users"></i>
              <span class="entities-label">Entidades:</span>
              <div class="entity-chips">
                <Chip
                  v-for="entityId in alert.entityIds.slice(0, 3)"
                  :key="entityId"
                  :label="`Entidad #${entityId}`"
                  size="small"
                />
                <span v-if="alert.entityIds.length > 3" class="more-entities">
                  +{{ alert.entityIds.length - 3 }}
                </span>
              </div>
            </div>

            <!-- Footer con acciones -->
            <div class="alert-footer">
              <div class="alert-meta">
                <small class="alert-date">{{ alert.createdAt ? formatDate(alert.createdAt) : '' }}</small>
                <Tag v-if="alert.status" :severity="getStatusSeverity(alert.status)">
                  {{ getStatusLabel(alert.status) }}
                </Tag>
              </div>
              <div v-if="showActions" class="alert-actions">
                <Button
                  label="Ver contexto"
                  icon="pi pi-search"
                  text
                  size="small"
                  @click.stop="$emit('view-context', alert)"
                />
                <Button
                  v-if="isAlertOpenStatus(alert.status)"
                  label="Resolver"
                  icon="pi pi-check"
                  text
                  size="small"
                  @click.stop="$emit('resolve', alert)"
                />
                <Button
                  v-if="isAlertOpenStatus(alert.status)"
                  label="Descartar"
                  icon="pi pi-times"
                  text
                  size="small"
                  severity="secondary"
                  @click.stop="$emit('dismiss', alert)"
                />
              </div>
            </div>
          </div>
        </div>
      </template>
    </VirtualScroller>

    <!-- Lista normal para pocos items o con paginación -->
    <div v-else class="alerts-container" :class="{ 'compact': compact }" role="listbox" aria-label="Alertas filtradas" @keydown="onAlertListKeydown">
      <div
        v-for="(alert, index) in paginatedAlerts"
        :key="alert.id"
        :ref="el => setAlertRef(el, index)"
        class="alert-item"
        role="option"
        :tabindex="getAlertTabindex(index)"
        :aria-selected="alertFocusedIndex === index"
        :aria-label="`${getSeverityLabel(alert.severity)}: ${alert.title}`"
        :class="[
          `alert-${alert.severity}`,
          { 'alert-selected': selectedAlertId === alert.id },
          { 'alert-clickable': clickable }
        ]"
        @click="onAlertClick(alert)"
        @keydown.enter="onAlertClick(alert)"
        @focus="alertFocusedIndex = index"
      >
        <!-- Severidad indicator -->
        <div class="alert-severity-bar" :class="`severity-${alert.severity}`"></div>

        <!-- Contenido -->
        <div class="alert-content">
          <!-- Header -->
          <div class="alert-header">
            <Tag :severity="getSeverityColor(alert.severity)" class="severity-tag">
              <i :class="getSeverityIcon(alert.severity)"></i>
              {{ alert.severity.toUpperCase() }}
            </Tag>
            <Tag severity="secondary" class="category-tag">
              {{ getCategoryLabel(alert.category) }}
            </Tag>
            <span v-if="alert.chapter" class="alert-chapter">
              <i class="pi pi-book"></i>
              Cap. {{ alert.chapter }}
            </span>
          </div>

          <!-- Título y descripción -->
          <div class="alert-body">
            <h4 class="alert-title">{{ alert.title }}</h4>
            <p class="alert-description">{{ alert.description }}</p>
          </div>

          <!-- Entidades relacionadas -->
          <div v-if="alert.entityIds && alert.entityIds.length > 0" class="alert-entities">
            <i class="pi pi-users"></i>
            <span class="entities-label">Entidades:</span>
            <div class="entity-chips">
              <Chip
                v-for="entityId in alert.entityIds.slice(0, 3)"
                :key="entityId"
                :label="`Entidad #${entityId}`"
                size="small"
              />
              <span v-if="alert.entityIds.length > 3" class="more-entities">
                +{{ alert.entityIds.length - 3 }}
              </span>
            </div>
          </div>

          <!-- Footer con acciones -->
          <div class="alert-footer">
            <div class="alert-meta">
              <small class="alert-date">{{ alert.createdAt ? formatDate(alert.createdAt) : '' }}</small>
              <Tag v-if="alert.status" :severity="getStatusSeverity(alert.status)">
                {{ getStatusLabel(alert.status) }}
              </Tag>
            </div>
            <div v-if="showActions" class="alert-actions">
              <Button
                label="Ver contexto"
                icon="pi pi-search"
                text
                size="small"
                @click.stop="$emit('view-context', alert)"
              />
              <Button
                v-if="isAlertOpenStatus(alert.status)"
                label="Resolver"
                icon="pi pi-check"
                text
                size="small"
                @click.stop="$emit('resolve', alert)"
              />
              <Button
                v-if="isAlertOpenStatus(alert.status)"
                label="Descartar"
                icon="pi pi-times"
                text
                size="small"
                severity="secondary"
                @click.stop="$emit('dismiss', alert)"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Paginación -->
    <div v-if="showPagination && totalPages > 1" class="pagination">
      <Paginator
        :rows="itemsPerPage"
        :total-records="filteredAlerts.length"
        @page="onPageChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Button from 'primevue/button'
import DsInput from '@/components/ds/DsInput.vue'
import SelectButton from 'primevue/selectbutton'
import Badge from 'primevue/badge'
import Tag from 'primevue/tag'
import Chip from 'primevue/chip'
import ProgressSpinner from 'primevue/progressspinner'
import Paginator from 'primevue/paginator'
import VirtualScroller from 'primevue/virtualscroller'
import type { Alert } from '@/types'
import { debounce } from '@/composables'
import { useAlertUtils } from '@/composables/useAlertUtils'
import { useListKeyboardNav } from '@/composables/useListKeyboardNav'

// Usar composable centralizado para utilidades de alertas
const {
  getSeverityConfig,
  getCategoryConfig,
  getStatusConfig,
  getSeverityLabel,
} = useAlertUtils()

const { setItemRef: setAlertRef, getTabindex: getAlertTabindex, onKeydown: onAlertListKeydown, focusedIndex: alertFocusedIndex } = useListKeyboardNav()

// Umbral para activar virtualización
const VIRTUALIZATION_THRESHOLD = 50

const props = withDefaults(defineProps<{
  alerts: Alert[]
  loading?: boolean
  compact?: boolean
  showTitle?: boolean
  showFilters?: boolean
  showActions?: boolean
  showPagination?: boolean
  showRefresh?: boolean
  clickable?: boolean
  selectedAlertId?: number | null
  itemsPerPage?: number
}>(), {
  loading: false,
  compact: false,
  showTitle: true,
  showFilters: true,
  showActions: true,
  showPagination: true,
  showRefresh: false,
  clickable: true,
  selectedAlertId: null,
  itemsPerPage: 15
})

const emit = defineEmits<{
  refresh: []
  select: [alert: Alert]
  'view-context': [alert: Alert]
  resolve: [alert: Alert]
  dismiss: [alert: Alert]
}>()

// Estado
const searchQuery = ref('')
const debouncedSearchQuery = ref('') // Query con debounce para filtrado
const selectedSeverity = ref('all')
const selectedCategory = ref('all')
const selectedStatus = ref('all')
const currentPage = ref(0)

// Debounce para búsqueda (300ms de espera)
const updateDebouncedSearch = debounce((query: string) => {
  debouncedSearchQuery.value = query
  currentPage.value = 0
}, 300)

// Watcher para aplicar debounce a la búsqueda
watch(searchQuery, (newQuery) => {
  updateDebouncedSearch(newQuery)
})

// Determina si usar virtualización
const shouldVirtualize = computed(() => {
  return filteredAlerts.value.length > VIRTUALIZATION_THRESHOLD && !props.showPagination
})

// Niveles de severidad (domain values: critical, high, medium, low, info)
const severityLevels = [
  { label: 'Todas', value: 'all', severity: 'secondary', icon: 'pi pi-list' },
  { label: 'Críticas', value: 'critical', severity: 'danger', icon: 'pi pi-exclamation-circle' },
  { label: 'Altas', value: 'high', severity: 'warn', icon: 'pi pi-exclamation-triangle' },
  { label: 'Medias', value: 'medium', severity: 'warn', icon: 'pi pi-info-circle' },
  { label: 'Bajas', value: 'low', severity: 'secondary', icon: 'pi pi-circle' },
  { label: 'Info', value: 'info', severity: 'info', icon: 'pi pi-lightbulb' }
]

// Opciones de categorías (domain values)
const categoryOptions = [
  { label: 'Todas', value: 'all' },
  { label: 'Atributos', value: 'attribute' },
  { label: 'Línea temporal', value: 'timeline' },
  { label: 'Relaciones', value: 'relationship' },
  { label: 'Ubicación', value: 'location' },
  { label: 'Comportamiento', value: 'behavior' },
  { label: 'Conocimiento', value: 'knowledge' },
  { label: 'Estilo', value: 'style' },
  { label: 'Gramática', value: 'grammar' },
  { label: 'Estructura', value: 'structure' },
  { label: 'Tipografía', value: 'typography' },
  { label: 'Puntuación', value: 'punctuation' },
  { label: 'Repeticiones', value: 'repetition' },
  { label: 'Concordancia', value: 'agreement' },
  { label: 'Otros', value: 'other' }
]

// Opciones de estado (domain values: active, dismissed, resolved)
const statusOptions = [
  { label: 'Todas', value: 'all' },
  { label: 'Activas', value: 'active' },
  { label: 'Resueltas', value: 'resolved' },
  { label: 'Descartadas', value: 'dismissed' }
]

// Helper para verificar si una alerta está "activa" (domain: active, or legacy API statuses)
const isAlertOpenStatus = (status: string): boolean => {
  const activeStatuses = ['active', 'new', 'open', 'acknowledged', 'in_progress']
  return activeStatuses.includes(status)
}

// Computed - Optimizado con memoización por etapas y debounced search
// Paso 1: Filtrar por severidad
const severityFilteredAlerts = computed(() => {
  if (selectedSeverity.value === 'all') {
    return props.alerts
  }
  return props.alerts.filter(a => a.severity === selectedSeverity.value)
})

// Paso 2: Filtrar por categoría
const categoryFilteredAlerts = computed(() => {
  if (selectedCategory.value === 'all') {
    return severityFilteredAlerts.value
  }
  return severityFilteredAlerts.value.filter(a => a.category === selectedCategory.value)
})

// Paso 3: Filtrar por estado
const statusFilteredAlerts = computed(() => {
  if (selectedStatus.value === 'all') {
    return categoryFilteredAlerts.value
  }
  // 'active' covers legacy statuses: new, open, acknowledged, in_progress
  if (selectedStatus.value === 'active') {
    return categoryFilteredAlerts.value.filter(a => isAlertOpenStatus(a.status))
  }
  return categoryFilteredAlerts.value.filter(a => a.status === selectedStatus.value)
})

// Paso 4: Filtrar por búsqueda (usa query con debounce)
const filteredAlerts = computed(() => {
  if (!debouncedSearchQuery.value) {
    return statusFilteredAlerts.value
  }
  const query = debouncedSearchQuery.value.toLowerCase()
  return statusFilteredAlerts.value.filter(a =>
    a.title?.toLowerCase().includes(query) ||
    a.description?.toLowerCase().includes(query)
  )
})

const totalPages = computed(() => Math.ceil(filteredAlerts.value.length / props.itemsPerPage))

const paginatedAlerts = computed(() => {
  if (!props.showPagination) return filteredAlerts.value

  const start = currentPage.value * props.itemsPerPage
  const end = start + props.itemsPerPage
  return filteredAlerts.value.slice(start, end)
})

// Funciones
const selectSeverity = (severity: string) => {
  selectedSeverity.value = severity
  currentPage.value = 0
}

const clearFilters = () => {
  searchQuery.value = ''
  selectedSeverity.value = 'all'
  selectedCategory.value = 'all'
  selectedStatus.value = 'all'
  currentPage.value = 0
}

const onPageChange = (event: any) => {
  currentPage.value = event.page
}

const onAlertClick = (alert: Alert) => {
  if (props.clickable) {
    emit('select', alert)
  }
}

const getSeverityCount = (severity: string): number => {
  if (severity === 'all') return props.alerts.length
  return props.alerts.filter(a => a.severity === severity).length
}

// Usar composable para obtener configuración centralizada
const getSeverityColor = (severity: string): string => {
  // Map to PrimeVue Tag severity values
  const primeVueMap: Record<string, string> = {
    'critical': 'danger',
    'high': 'warn',
    'medium': 'warn',
    'low': 'secondary',
    'info': 'info',
  }
  return primeVueMap[severity] || 'secondary'
}

const getSeverityIcon = (severity: string): string => {
  return getSeverityConfig(severity as any).icon
}

const getCategoryLabel = (category: string): string => {
  return getCategoryConfig(category as any).label
}

const getStatusSeverity = (status: string): string => {
  // Map to PrimeVue Tag severity values
  const primeVueMap: Record<string, string> = {
    'active': 'warn',
    'resolved': 'success',
    'dismissed': 'secondary',
  }
  return primeVueMap[status] || 'secondary'
}

const getStatusLabel = (status: string): string => {
  return getStatusConfig(status as any).label
}

const formatDate = (date: Date | string): string => {
  const d = date instanceof Date ? date : new Date(date)
  return d.toLocaleDateString('es-ES', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  })
}

// Watchers
watch(() => props.alerts, () => {
  currentPage.value = 0
})
</script>

<style scoped>
.alert-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--surface-card);
  border-radius: 8px;
  overflow: hidden;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--surface-50);
  border-bottom: 1px solid var(--surface-border);
}

.header-left h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-color);
}

.alert-count {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
  font-weight: 500;
}

.header-actions {
  display: flex;
  gap: 0.25rem;
}

.filters-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem;
  border-bottom: 1px solid var(--surface-border);
}

.search-wrapper {
  width: 100%;
}

.search-input {
  width: 100%;
}

.severity-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.severity-filters :deep(.p-button) {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.category-filters,
.status-filters {
  display: flex;
  justify-content: center;
}

.list-loading,
.list-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1rem;
  gap: 0.75rem;
  color: var(--text-color-secondary);
}

.empty-icon {
  font-size: 2.5rem;
  opacity: 0.5;
  color: var(--green-500);
}

.alerts-container {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.alerts-container.compact .alert-item {
  padding: 0.75rem;
}

.alert-item {
  display: flex;
  position: relative;
  margin-bottom: 1rem;
  border-radius: 8px;
  background: var(--surface-ground);
  border: 1px solid var(--surface-border);
  overflow: hidden;
  transition: all 0.2s;
}

.alert-item.alert-clickable {
  cursor: pointer;
}

.alert-item.alert-clickable:hover {
  border-color: var(--primary-color);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transform: translateX(4px);
}

.alert-item.alert-selected {
  border-color: var(--primary-color);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.alert-severity-bar {
  width: 4px;
  flex-shrink: 0;
}

/* Domain severity colors */
.alert-severity-bar.severity-critical {
  background: var(--ds-alert-critical, var(--red-500));
}

.alert-severity-bar.severity-high {
  background: var(--ds-alert-high, var(--orange-500));
}

.alert-severity-bar.severity-medium {
  background: var(--ds-alert-medium, var(--yellow-500));
}

.alert-severity-bar.severity-low {
  background: var(--ds-alert-low, #80CBC4);
}

.alert-severity-bar.severity-info {
  background: var(--ds-alert-info, var(--blue-500));
}

/* Legacy API severity names (fallback) */
.alert-severity-bar.severity-warning {
  background: var(--ds-alert-high, var(--orange-500));
}

.alert-severity-bar.severity-hint {
  background: var(--ds-alert-low, var(--surface-400));
}

.alert-content {
  flex: 1;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.alert-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.severity-tag {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.alert-chapter {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.alert-body {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.alert-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-color);
}

.alert-description {
  margin: 0;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
  line-height: 1.5;
}

.alert-entities {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  padding: 0.5rem;
  background: var(--surface-50);
  border-radius: 4px;
}

.alert-entities i {
  color: var(--primary-color);
  font-size: 0.875rem;
}

.entities-label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  font-weight: 600;
}

.entity-chips {
  display: flex;
  gap: 0.25rem;
  flex-wrap: wrap;
}

.more-entities {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  padding: 0.25rem 0.5rem;
}

.alert-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--surface-border);
}

.alert-meta {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.alert-date {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.alert-actions {
  display: flex;
  gap: 0.5rem;
}

.pagination {
  padding: 0.75rem;
  border-top: 1px solid var(--surface-border);
  background: var(--surface-50);
}

/* VirtualScroller styling */
.alerts-virtual {
  height: 100%;
}

.alerts-virtual :deep(.p-virtualscroller-content) {
  padding: 1rem;
}

.alert-item.alert-odd {
  background: var(--surface-50);
}

/* Scrollbar styling */
.alerts-container::-webkit-scrollbar,
.alerts-virtual :deep(.p-virtualscroller-content)::-webkit-scrollbar {
  width: 6px;
}

.alerts-container::-webkit-scrollbar-track,
.alerts-virtual :deep(.p-virtualscroller-content)::-webkit-scrollbar-track {
  background: var(--surface-50);
}

.alerts-container::-webkit-scrollbar-thumb,
.alerts-virtual :deep(.p-virtualscroller-content)::-webkit-scrollbar-thumb {
  background: var(--surface-300);
  border-radius: 3px;
}

.alerts-container::-webkit-scrollbar-thumb:hover,
.alerts-virtual :deep(.p-virtualscroller-content)::-webkit-scrollbar-thumb:hover {
  background: var(--surface-400);
}
</style>
