<template>
  <div class="alert-list">
    <!-- Header con filtros -->
    <div class="list-header">
      <div class="header-left">
        <h3 v-if="showTitle">Alertas</h3>
        <span v-if="!showTitle" class="alert-count">{{ filteredAlerts.length }} alertas</span>
      </div>
      <div class="header-actions">
        <Button
          v-if="showRefresh"
          icon="pi pi-refresh"
          text
          rounded
          size="small"
          @click="$emit('refresh')"
          v-tooltip.bottom="'Recargar'"
        />
      </div>
    </div>

    <!-- Filtros -->
    <div v-if="showFilters" class="filters-section">
      <!-- Búsqueda -->
      <span class="p-input-icon-left search-wrapper">
        <i class="pi pi-search" />
        <InputText
          v-model="searchQuery"
          placeholder="Buscar alertas..."
          class="search-input"
        />
      </span>

      <!-- Filtros por severidad -->
      <div class="severity-filters">
        <Button
          v-for="sev in severityLevels"
          :key="sev.value"
          :icon="sev.icon"
          :label="sev.label"
          :severity="selectedSeverity === sev.value ? sev.severity : 'secondary'"
          :outlined="selectedSeverity !== sev.value"
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
          optionLabel="label"
          optionValue="value"
        />
      </div>

      <!-- Filtro por estado -->
      <div class="status-filters">
        <SelectButton
          v-model="selectedStatus"
          :options="statusOptions"
          optionLabel="label"
          optionValue="value"
        />
      </div>
    </div>

    <!-- Lista de alertas -->
    <div v-if="loading" class="list-loading">
      <ProgressSpinner style="width: 30px; height: 30px" />
      <small>Cargando alertas...</small>
    </div>

    <div v-else-if="filteredAlerts.length === 0" class="list-empty">
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

    <div v-else class="alerts-container" :class="{ 'compact': compact }">
      <div
        v-for="alert in paginatedAlerts"
        :key="alert.id"
        class="alert-item"
        :class="[
          `alert-${alert.severity}`,
          { 'alert-selected': selectedAlertId === alert.id },
          { 'alert-clickable': clickable }
        ]"
        @click="onAlertClick(alert)"
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
          <div v-if="alert.entities && alert.entities.length > 0" class="alert-entities">
            <i class="pi pi-users"></i>
            <span class="entities-label">Entidades:</span>
            <div class="entity-chips">
              <Chip
                v-for="entity in alert.entities.slice(0, 3)"
                :key="entity.id"
                :label="entity.canonical_name"
                size="small"
              />
              <span v-if="alert.entities.length > 3" class="more-entities">
                +{{ alert.entities.length - 3 }}
              </span>
            </div>
          </div>

          <!-- Footer con acciones -->
          <div class="alert-footer">
            <div class="alert-meta">
              <small class="alert-date">{{ formatDate(alert.created_at) }}</small>
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
                v-if="alert.status === 'open'"
                label="Resolver"
                icon="pi pi-check"
                text
                size="small"
                @click.stop="$emit('resolve', alert)"
              />
              <Button
                v-if="alert.status === 'open'"
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
        :totalRecords="filteredAlerts.length"
        @page="onPageChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import SelectButton from 'primevue/selectbutton'
import Badge from 'primevue/badge'
import Tag from 'primevue/tag'
import Chip from 'primevue/chip'
import ProgressSpinner from 'primevue/progressspinner'
import Paginator from 'primevue/paginator'
import type { Alert } from '@/types'

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
const selectedSeverity = ref('all')
const selectedCategory = ref('all')
const selectedStatus = ref('all')
const currentPage = ref(0)

// Niveles de severidad
const severityLevels = [
  { label: 'Todas', value: 'all', severity: 'secondary', icon: 'pi pi-list' },
  { label: 'Críticas', value: 'critical', severity: 'danger', icon: 'pi pi-exclamation-circle' },
  { label: 'Advertencias', value: 'warning', severity: 'warning', icon: 'pi pi-exclamation-triangle' },
  { label: 'Info', value: 'info', severity: 'info', icon: 'pi pi-info-circle' },
  { label: 'Sugerencias', value: 'hint', severity: 'secondary', icon: 'pi pi-lightbulb' }
]

// Opciones de categorías
const categoryOptions = [
  { label: 'Todas', value: 'all' },
  { label: 'Consistencia', value: 'consistency' },
  { label: 'Continuidad', value: 'continuity' },
  { label: 'Caracterización', value: 'characterization' },
  { label: 'Cronología', value: 'chronology' },
  { label: 'Estilo', value: 'style' }
]

// Opciones de estado
const statusOptions = [
  { label: 'Todas', value: 'all' },
  { label: 'Abiertas', value: 'open' },
  { label: 'Resueltas', value: 'resolved' },
  { label: 'Descartadas', value: 'dismissed' }
]

// Computed
const filteredAlerts = computed(() => {
  let filtered = props.alerts

  // Filtrar por severidad
  if (selectedSeverity.value !== 'all') {
    filtered = filtered.filter(a => a.severity === selectedSeverity.value)
  }

  // Filtrar por categoría
  if (selectedCategory.value !== 'all') {
    filtered = filtered.filter(a => a.category === selectedCategory.value)
  }

  // Filtrar por estado
  if (selectedStatus.value !== 'all') {
    filtered = filtered.filter(a => a.status === selectedStatus.value)
  }

  // Filtrar por búsqueda
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(a =>
      a.title.toLowerCase().includes(query) ||
      a.description.toLowerCase().includes(query) ||
      a.entities?.some(e => e.canonical_name.toLowerCase().includes(query))
    )
  }

  return filtered
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

const getSeverityColor = (severity: string): string => {
  const colors: Record<string, string> = {
    'critical': 'danger',
    'warning': 'warning',
    'info': 'info',
    'hint': 'secondary'
  }
  return colors[severity] || 'secondary'
}

const getSeverityIcon = (severity: string): string => {
  const icons: Record<string, string> = {
    'critical': 'pi pi-exclamation-circle',
    'warning': 'pi pi-exclamation-triangle',
    'info': 'pi pi-info-circle',
    'hint': 'pi pi-lightbulb'
  }
  return icons[severity] || 'pi pi-info-circle'
}

const getCategoryLabel = (category: string): string => {
  const labels: Record<string, string> = {
    'consistency': 'Consistencia',
    'continuity': 'Continuidad',
    'characterization': 'Caracterización',
    'chronology': 'Cronología',
    'style': 'Estilo'
  }
  return labels[category] || category
}

const getStatusSeverity = (status: string): string => {
  const severities: Record<string, string> = {
    'open': 'warning',
    'resolved': 'success',
    'dismissed': 'secondary'
  }
  return severities[status] || 'secondary'
}

const getStatusLabel = (status: string): string => {
  const labels: Record<string, string> = {
    'open': 'Abierta',
    'resolved': 'Resuelta',
    'dismissed': 'Descartada'
  }
  return labels[status] || status
}

const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleDateString('es-ES', {
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

.alert-severity-bar.severity-critical {
  background: var(--red-500);
}

.alert-severity-bar.severity-warning {
  background: var(--yellow-500);
}

.alert-severity-bar.severity-info {
  background: var(--blue-500);
}

.alert-severity-bar.severity-hint {
  background: var(--surface-400);
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

/* Scrollbar styling */
.alerts-container::-webkit-scrollbar {
  width: 6px;
}

.alerts-container::-webkit-scrollbar-track {
  background: var(--surface-50);
}

.alerts-container::-webkit-scrollbar-thumb {
  background: var(--surface-300);
  border-radius: 3px;
}

.alerts-container::-webkit-scrollbar-thumb:hover {
  background: var(--surface-400);
}
</style>
