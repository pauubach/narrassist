<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { useGlobalUndo } from '@/composables/useGlobalUndo'
import type { HistoryEntry } from '@/composables/useGlobalUndo'
import { useListKeyboardNav } from '@/composables/useListKeyboardNav'
import SelectButton from 'primevue/selectbutton'

/**
 * HistoryPanel - Panel de historial de acciones en el sidebar.
 *
 * Muestra las acciones recientes del proyecto con opción de deshacerlas.
 * 5ª pestaña del sidebar, colapsada por defecto.
 * Incluye filtros por categoría de acción (entidades, alertas, atributos, relaciones).
 */

const props = defineProps<{
  projectId: number
}>()

const { undoEntry, undoBatch, fetchHistory, fetchUndoableCount, undoing, undoableCount } =
  useGlobalUndo(() => props.projectId)

const { setItemRef: setHistoryRef, getTabindex: getHistoryTabindex, onKeydown: onHistoryKeydown, focusedIndex: historyFocusedIndex } = useListKeyboardNav()

const entries = ref<HistoryEntry[]>([])
const loading = ref(false)
const selectedFilter = ref<string>('all')

// Filtros disponibles
const filterOptions = [
  { label: 'Todas', value: 'all', icon: 'pi pi-list' },
  { label: 'Entidades', value: 'entities', icon: 'pi pi-users' },
  { label: 'Fusiones', value: 'merges', icon: 'pi pi-link' },
  { label: 'Alertas', value: 'alerts', icon: 'pi pi-bell' },
  { label: 'Atributos', value: 'attributes', icon: 'pi pi-tag' },
  { label: 'Relaciones', value: 'relationships', icon: 'pi pi-sitemap' },
]

// Mapeo de tipos de acción a categorías
function getActionCategory(actionType: string): string {
  if (actionType === 'entity_merged') return 'merges'
  if (actionType.startsWith('entity_')) return 'entities'
  if (actionType.startsWith('alert_')) return 'alerts'
  if (actionType.startsWith('attribute_')) return 'attributes'
  if (actionType.startsWith('relationship_')) return 'relationships'
  return 'other'
}

// Entradas filtradas
const filteredEntries = computed(() => {
  if (selectedFilter.value === 'all') {
    return entries.value
  }
  return entries.value.filter(entry => {
    const category = getActionCategory(entry.actionType)
    return category === selectedFilter.value
  })
})

// Contador para el badge del filtro activo
const filteredCount = computed(() => filteredEntries.value.length)

async function loadHistory() {
  loading.value = true
  try {
    entries.value = await fetchHistory({ limit: 50, undoableOnly: false })
  } finally {
    loading.value = false
  }
}

async function handleUndo(entry: HistoryEntry) {
  if (entry.batchId) {
    await undoBatch(entry.batchId)
  } else {
    await undoEntry(entry.id)
  }
  await loadHistory()
}

function getActionIcon(actionType: string): string {
  const icons: Record<string, string> = {
    entity_merged: 'pi pi-link',
    entity_deleted: 'pi pi-trash',
    entity_updated: 'pi pi-pencil',
    alert_resolved: 'pi pi-check',
    alert_dismissed: 'pi pi-times',
    attribute_verified: 'pi pi-verified',
    attribute_added: 'pi pi-plus-circle',
    attribute_changed: 'pi pi-pencil',
    attribute_updated: 'pi pi-pencil',
    attribute_deleted: 'pi pi-minus-circle',
    relationship_created: 'pi pi-plus',
    relationship_updated: 'pi pi-pencil',
    relationship_deleted: 'pi pi-trash',
  }
  return icons[actionType] || 'pi pi-circle'
}

function getActionLabel(actionType: string): string {
  const labels: Record<string, string> = {
    entity_merged: 'Fusión',
    entity_deleted: 'Eliminación',
    entity_updated: 'Edición',
    alert_resolved: 'Resolución',
    alert_dismissed: 'Descarte',
    attribute_verified: 'Verificación',
    attribute_added: 'Nuevo atributo',
    attribute_changed: 'Cambio atributo',
    attribute_updated: 'Cambio atributo',
    attribute_deleted: 'Eliminación atributo',
    relationship_created: 'Nueva relación',
    relationship_updated: 'Edición relación',
    relationship_deleted: 'Eliminación relación',
  }
  return labels[actionType] || actionType
}

function formatTime(dateStr: string): string {
  try {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMin = Math.floor(diffMs / 60000)
    const diffHour = Math.floor(diffMs / 3600000)
    const diffDay = Math.floor(diffMs / 86400000)

    if (diffMin < 1) return 'Ahora'
    if (diffMin < 60) return `Hace ${diffMin} min`
    if (diffHour < 24) return `Hace ${diffHour}h`
    if (diffDay < 7) return `Hace ${diffDay}d`
    return date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' })
  } catch {
    return dateStr
  }
}

// Recargar cuando se deshace algo
function handleUndoComplete() {
  loadHistory()
}

onMounted(() => {
  loadHistory()
  window.addEventListener('history:undo-complete', handleUndoComplete)
})

onUnmounted(() => {
  window.removeEventListener('history:undo-complete', handleUndoComplete)
})

// Recargar si cambia el proyecto
watch(() => props.projectId, () => {
  loadHistory()
})
</script>

<template>
  <div class="history-panel">
    <div class="panel-header">
      <span class="panel-title">Historial</span>
      <span v-if="undoableCount > 0" class="panel-count">{{ undoableCount }}</span>
    </div>

    <!-- Filtros por categoría -->
    <div class="filter-section">
      <SelectButton
        v-model="selectedFilter"
        :options="filterOptions"
        option-label="label"
        option-value="value"
        class="filter-buttons"
        :allow-empty="false"
      >
        <template #option="{ option }">
          <div class="filter-option">
            <i :class="option.icon"></i>
            <span class="filter-label">{{ option.label }}</span>
          </div>
        </template>
      </SelectButton>
      <div v-if="selectedFilter !== 'all'" class="filter-info">
        <span class="filter-count">{{ filteredCount }}</span>
        <span class="filter-text">{{ filteredCount === 1 ? 'acción' : 'acciones' }}</span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <i class="pi pi-spin pi-spinner"></i>
      <span>Cargando...</span>
    </div>

    <!-- Empty -->
    <div v-else-if="entries.length === 0" class="empty-state">
      <i class="pi pi-history"></i>
      <span>Sin acciones recientes</span>
    </div>

    <!-- Empty after filter -->
    <div v-else-if="filteredEntries.length === 0" class="empty-state">
      <i class="pi pi-filter-slash"></i>
      <span>No hay {{ filterOptions.find(f => f.value === selectedFilter)?.label.toLowerCase() }}</span>
    </div>

    <!-- List -->
    <div v-else class="history-list" role="list" aria-label="Historial de acciones" @keydown="onHistoryKeydown">
      <div
        v-for="(entry, index) in filteredEntries"
        :key="entry.id"
        :ref="el => setHistoryRef(el, index)"
        class="history-item"
        role="listitem"
        :tabindex="getHistoryTabindex(index)"
        :class="{
          'history-item--undone': entry.isUndone,
          'history-item--undoable': entry.isUndoable && !entry.isUndone,
        }"
        @focus="historyFocusedIndex = index"
      >
        <div class="history-item__icon">
          <i :class="getActionIcon(entry.actionType)"></i>
        </div>
        <div class="history-item__content">
          <div class="history-item__action">
            <span class="action-label">{{ getActionLabel(entry.actionType) }}</span>
            <span class="action-time">{{ formatTime(entry.createdAt) }}</span>
          </div>
          <div v-if="entry.note" class="history-item__note">{{ entry.note }}</div>
          <div v-if="entry.isUndone" class="history-item__undone-badge">Deshecho</div>
        </div>
        <button
          v-if="entry.isUndoable && !entry.isUndone"
          type="button"
          class="undo-btn"
          :disabled="undoing"
          title="Deshacer esta acción"
          @click.stop="handleUndo(entry)"
        >
          <i class="pi pi-undo"></i>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.history-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--surface-border);
}

.panel-title {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--text-color);
}

.panel-count {
  font-size: 0.75rem;
  background: var(--primary-color);
  color: var(--primary-color-text);
  border-radius: var(--app-radius-lg);
  padding: 0.125rem 0.5rem;
  min-width: 1.25rem;
  text-align: center;
}

/* Filtros */
.filter-section {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--surface-border);
  background: var(--surface-ground);
}

.filter-buttons {
  width: 100%;
}

.filter-buttons :deep(.p-selectbutton) {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.25rem;
}

.filter-buttons :deep(.p-togglebutton) {
  padding: 0.375rem 0.25rem;
  font-size: 0.7rem;
  border: 1px solid var(--surface-border);
  background: var(--surface-card);
  justify-content: center;
}

.filter-buttons :deep(.p-togglebutton.p-highlight) {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: white;
}

.filter-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.125rem;
}

.filter-option i {
  font-size: 0.8rem;
}

.filter-label {
  font-size: 0.65rem;
  white-space: nowrap;
}

.filter-info {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  margin-top: 0.5rem;
  padding: 0.25rem 0.5rem;
  background: var(--primary-50);
  border-radius: var(--app-radius);
  font-size: 0.75rem;
}

.filter-count {
  font-weight: 600;
  color: var(--primary-color);
}

.filter-text {
  color: var(--text-color-secondary);
}

.dark .filter-info {
  background: var(--primary-900);
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 2rem 1rem;
  color: var(--text-color-secondary);
  font-size: 0.85rem;
}

.empty-state i,
.loading-state i {
  font-size: 1.5rem;
  opacity: 0.5;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.25rem 0;
}

.history-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--surface-ground);
  transition: background-color 0.15s;
}

.history-item:hover {
  background-color: var(--surface-hover);
}

.history-item--undone {
  opacity: 0.5;
}

.history-item__icon {
  flex-shrink: 0;
  width: 1.5rem;
  height: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-color-secondary);
  font-size: 0.8rem;
}

.history-item__content {
  flex: 1;
  min-width: 0;
}

.history-item__action {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.action-label {
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--text-color);
}

.action-time {
  font-size: 0.7rem;
  color: var(--text-color-secondary);
  white-space: nowrap;
}

.history-item__note {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  margin-top: 0.125rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-item__undone-badge {
  font-size: 0.65rem;
  color: var(--orange-500);
  font-style: italic;
  margin-top: 0.125rem;
}

.undo-btn {
  flex-shrink: 0;
  background: none;
  border: 1px solid transparent;
  border-radius: var(--app-radius);
  cursor: pointer;
  padding: 0.25rem;
  color: var(--text-color-secondary);
  font-size: 0.8rem;
  transition: all 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
}

.undo-btn:hover {
  color: var(--primary-color);
  border-color: var(--primary-color);
  background: var(--primary-50);
}

.undo-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* Dark mode */
:deep(.dark) .undo-btn:hover {
  background: var(--primary-900);
}
</style>
