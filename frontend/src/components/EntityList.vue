<template>
  <div class="entity-list">
    <!-- Header con filtros (solo mostrar si hay título o botones de acción) -->
    <div v-if="showTitle || showRefresh || showExpandButton" class="list-header">
      <div class="header-left">
        <h3 v-if="showTitle">Entidades</h3>
      </div>
      <div class="header-actions">
        <Button
          v-if="showMergeHistory"
          icon="pi pi-history"
          text
          rounded
          size="small"
          @click="showMergeHistoryDialog = true"
          v-tooltip.bottom="'Historial de fusiones'"
        />
        <Button
          v-if="showRefresh"
          icon="pi pi-refresh"
          text
          rounded
          size="small"
          @click="$emit('refresh')"
          v-tooltip.bottom="'Recargar'"
        />
        <Button
          v-if="showExpandButton"
          :icon="expanded ? 'pi pi-minus' : 'pi pi-plus'"
          text
          rounded
          size="small"
          @click="toggleExpanded"
          v-tooltip.bottom="expanded ? 'Contraer' : 'Expandir'"
        />
      </div>
    </div>

    <!-- Filtros y búsqueda -->
    <div v-if="showFilters" class="filters-section">
      <!-- Búsqueda -->
      <DsInput
        v-model="searchQuery"
        placeholder="Buscar entidades..."
        icon="pi pi-search"
        clearable
        class="search-input"
      />

      <!-- Filtro por tipo -->
      <div class="type-filters">
        <Button
          v-for="type in entityTypes"
          :key="type.value"
          :label="type.label"
          :icon="type.icon"
          :severity="selectedType === type.value ? 'primary' : 'secondary'"
          :outlined="selectedType !== type.value"
          size="small"
          @click="selectType(type.value)"
        >
          <template #default>
            <i :class="type.icon"></i>
            <span>{{ type.label }}</span>
            <Badge v-if="getTypeCount(type.value) > 0" :value="getTypeCount(type.value)" />
          </template>
        </Button>
      </div>

      <!-- Ordenamiento -->
      <Dropdown
        v-model="sortBy"
        :options="sortOptions"
        optionLabel="label"
        optionValue="value"
        placeholder="Ordenar por"
        class="sort-dropdown"
      />
    </div>

    <!-- Lista de entidades -->
    <div v-if="loading" class="list-loading">
      <ProgressSpinner style="width: 30px; height: 30px" />
      <small>Cargando entidades...</small>
    </div>

    <div v-else-if="filteredEntities.length === 0" class="list-empty">
      <i class="pi pi-users empty-icon"></i>
      <p v-if="searchQuery || selectedType !== 'all'">
        No se encontraron entidades con los filtros aplicados
      </p>
      <p v-else>No hay entidades detectadas</p>
      <Button
        v-if="searchQuery || selectedType !== 'all'"
        label="Limpiar filtros"
        icon="pi pi-filter-slash"
        text
        @click="clearFilters"
      />
    </div>

    <!-- Lista virtualizada para muchos items (>50) sin paginación -->
    <VirtualScroller
      v-else-if="shouldVirtualize"
      :items="filteredEntities"
      :itemSize="compact ? 56 : 80"
      class="entities-container entities-virtual"
      :class="{ 'compact': compact }"
    >
      <template #item="{ item: entity, options }">
        <div
          :key="entity.id"
          class="entity-item"
          :class="{
            'entity-selected': selectedEntityId === entity.id,
            'entity-clickable': clickable,
            'entity-odd': options.odd
          }"
          :style="{ height: compact ? '56px' : '80px' }"
          @click="onEntityClick(entity)"
        >
          <!-- Icono y nombre -->
          <div class="entity-main">
            <div class="entity-icon-wrapper">
              <i :class="getEntityIcon(entity.type)" class="entity-icon"></i>
            </div>
            <div class="entity-info">
              <div class="entity-name-row">
                <span class="entity-name">{{ entity.name }}</span>
                <i
                  v-if="entity.mergedFromIds && entity.mergedFromIds.length > 0"
                  class="pi pi-link merged-icon"
                  v-tooltip.top="'Entidad fusionada'"
                ></i>
              </div>
              <div v-if="entity.aliases && entity.aliases.length > 0" class="entity-aliases">
                <span v-for="(alias, idx) in entity.aliases.slice(0, 3)" :key="idx" class="alias-tag">
                  {{ alias }}
                </span>
                <span v-if="entity.aliases.length > 3" class="alias-more">
                  +{{ entity.aliases.length - 3 }}
                </span>
              </div>
            </div>
          </div>

          <!-- Metadata -->
          <div class="entity-meta">
            <Tag :severity="getImportanceSeverity(entity.importance)" class="importance-tag">
              {{ getImportanceLabel(entity.importance) }}
            </Tag>
            <div class="entity-stats">
              <span class="stat-item" v-tooltip.top="'Apariciones'">
                <i class="pi pi-hashtag"></i>
                {{ entity.mentionCount || 0 }}
              </span>
              <span
                v-if="entity.firstMentionChapter"
                class="stat-item"
                v-tooltip.top="'Primera aparición'"
              >
                <i class="pi pi-book"></i>
                Cap. {{ entity.firstMentionChapter }}
              </span>
            </div>
          </div>

          <!-- Acciones -->
          <div v-if="showActions" class="entity-actions">
            <Button
              icon="pi pi-eye"
              text
              rounded
              size="small"
              @click.stop="$emit('view', entity)"
              v-tooltip.left="'Ver detalles'"
            />
            <Button
              icon="pi pi-pencil"
              text
              rounded
              size="small"
              @click.stop="$emit('edit', entity)"
              v-tooltip.left="'Editar'"
            />
            <Button
              icon="pi pi-ellipsis-v"
              text
              rounded
              size="small"
              @click.stop="showEntityMenu($event, entity)"
              v-tooltip.left="'Más acciones'"
            />
          </div>
        </div>
      </template>
    </VirtualScroller>

    <!-- Lista normal para pocos items o con paginación -->
    <div v-else class="entities-container" :class="{ 'compact': compact }">
      <div
        v-for="entity in paginatedEntities"
        :key="entity.id"
        class="entity-item"
        :class="{
          'entity-selected': selectedEntityId === entity.id,
          'entity-clickable': clickable
        }"
        @click="onEntityClick(entity)"
      >
        <!-- Icono y nombre -->
        <div class="entity-main">
          <div class="entity-icon-wrapper">
            <i :class="getEntityIcon(entity.type)" class="entity-icon"></i>
          </div>
          <div class="entity-info">
            <div class="entity-name-row">
              <span class="entity-name">{{ entity.name }}</span>
              <i
                v-if="entity.mergedFromIds && entity.mergedFromIds.length > 0"
                class="pi pi-link merged-icon"
                v-tooltip.top="'Entidad fusionada'"
              ></i>
            </div>
            <div v-if="entity.aliases && entity.aliases.length > 0" class="entity-aliases">
              <span v-for="(alias, idx) in entity.aliases.slice(0, 3)" :key="idx" class="alias-tag">
                {{ alias }}
              </span>
              <span v-if="entity.aliases.length > 3" class="alias-more">
                +{{ entity.aliases.length - 3 }}
              </span>
            </div>
          </div>
        </div>

        <!-- Metadata -->
        <div class="entity-meta">
          <Tag :severity="getImportanceSeverity(entity.importance)" class="importance-tag">
            {{ getImportanceLabel(entity.importance) }}
          </Tag>
          <div class="entity-stats">
            <span class="stat-item" v-tooltip.top="'Apariciones'">
              <i class="pi pi-hashtag"></i>
              {{ entity.mentionCount || 0 }}
            </span>
            <span
              v-if="entity.firstMentionChapter"
              class="stat-item"
              v-tooltip.top="'Primera aparición'"
            >
              <i class="pi pi-book"></i>
              Cap. {{ entity.firstMentionChapter }}
            </span>
          </div>
        </div>

        <!-- Acciones -->
        <div v-if="showActions" class="entity-actions">
          <Button
            icon="pi pi-eye"
            text
            rounded
            size="small"
            @click.stop="$emit('view', entity)"
            v-tooltip.left="'Ver detalles'"
          />
          <Button
            icon="pi pi-pencil"
            text
            rounded
            size="small"
            @click.stop="$emit('edit', entity)"
            v-tooltip.left="'Editar'"
          />
          <Button
            icon="pi pi-ellipsis-v"
            text
            rounded
            size="small"
            @click.stop="showEntityMenu($event, entity)"
            v-tooltip.left="'Más acciones'"
          />
        </div>
      </div>
    </div>

    <!-- Paginación -->
    <div v-if="showPagination && totalPages > 1" class="pagination">
      <Paginator
        :rows="itemsPerPage"
        :totalRecords="filteredEntities.length"
        @page="onPageChange"
      />
    </div>

    <!-- Menú contextual -->
    <Menu ref="entityMenu" :model="entityMenuItems" :popup="true" />

    <!-- Diálogo de historial de fusiones -->
    <Dialog
      v-model:visible="showMergeHistoryDialog"
      header="Historial de Fusiones"
      :style="{ width: '600px' }"
      modal
    >
      <div v-if="loadingMergeHistory" class="loading-history">
        <ProgressSpinner style="width: 30px; height: 30px" />
        <span>Cargando historial...</span>
      </div>

      <div v-else-if="mergeHistory.length === 0" class="empty-history">
        <i class="pi pi-history"></i>
        <p>No hay fusiones registradas</p>
      </div>

      <div v-else class="merge-history-list">
        <div
          v-for="merge in mergeHistory"
          :key="merge.id"
          class="merge-history-item"
          :class="{ 'undone': merge.undone }"
        >
          <div class="merge-info">
            <div class="merge-header">
              <span class="merge-date">{{ formatDate(merge.created_at) }}</span>
              <Tag v-if="merge.undone" severity="secondary" value="Deshecha" />
            </div>
            <div class="merge-details">
              <span class="merge-names">
                {{ merge.source_names?.join(' + ') || 'Entidades fusionadas' }}
              </span>
              <i class="pi pi-arrow-right"></i>
              <span class="merge-result">{{ merge.result_name || 'Entidad resultante' }}</span>
            </div>
          </div>
          <Button
            v-if="!merge.undone"
            icon="pi pi-undo"
            text
            rounded
            size="small"
            severity="warning"
            @click="undoMerge(merge.id)"
            :loading="undoingMerge === merge.id"
            v-tooltip.left="'Deshacer fusión'"
          />
        </div>
      </div>

      <template #footer>
        <Button label="Cerrar" severity="secondary" @click="showMergeHistoryDialog = false" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Button from 'primevue/button'
import DsInput from '@/components/ds/DsInput.vue'
import Dropdown from 'primevue/dropdown'
import Badge from 'primevue/badge'
import Tag from 'primevue/tag'
import ProgressSpinner from 'primevue/progressspinner'
import Paginator from 'primevue/paginator'
import VirtualScroller from 'primevue/virtualscroller'
import Menu from 'primevue/menu'
import Dialog from 'primevue/dialog'
import type { Entity } from '@/types'
import { debounce } from '@/composables'
import { useToast } from 'primevue/usetoast'

// Umbral para activar virtualización (más de 50 items)
const VIRTUALIZATION_THRESHOLD = 50

const toast = useToast()

const props = withDefaults(defineProps<{
  entities: Entity[]
  loading?: boolean
  compact?: boolean
  showTitle?: boolean
  showFilters?: boolean
  showActions?: boolean
  showPagination?: boolean
  showRefresh?: boolean
  showExpandButton?: boolean
  showMergeHistory?: boolean
  clickable?: boolean
  selectedEntityId?: number | null
  initialType?: string
  itemsPerPage?: number
  projectId?: number
}>(), {
  loading: false,
  compact: false,
  showTitle: true,
  showFilters: true,
  showActions: true,
  showPagination: true,
  showRefresh: false,
  showExpandButton: false,
  showMergeHistory: false,
  clickable: true,
  selectedEntityId: null,
  initialType: 'all',
  itemsPerPage: 20,
  projectId: 0
})

const emit = defineEmits<{
  refresh: []
  select: [entity: Entity]
  view: [entity: Entity]
  edit: [entity: Entity]
  merge: [entity: Entity]
  delete: [entity: Entity]
}>()

// Estado
const searchQuery = ref('')
const debouncedSearchQuery = ref('') // Query con debounce para filtrado
const selectedType = ref(props.initialType)
const sortBy = ref('mention_count')
const expanded = ref(true)
const currentPage = ref(0)
const entityMenu = ref()
const selectedMenuEntity = ref<Entity | null>(null)

// Estado del historial de fusiones
const showMergeHistoryDialog = ref(false)
const loadingMergeHistory = ref(false)
const mergeHistory = ref<any[]>([])
const undoingMerge = ref<number | null>(null)

// Debounce para búsqueda (300ms de espera)
const updateDebouncedSearch = debounce((query: string) => {
  debouncedSearchQuery.value = query
  currentPage.value = 0
}, 300)

// Watcher para aplicar debounce a la búsqueda
watch(searchQuery, (newQuery) => {
  updateDebouncedSearch(newQuery)
})

// Determina si usar virtualización basado en el número de items
const shouldVirtualize = computed(() => {
  return filteredEntities.value.length > VIRTUALIZATION_THRESHOLD && !props.showPagination
})

// Definición de todos los tipos de entidades posibles (domain types use lowercase)
const allEntityTypes = [
  { label: 'Personajes', value: 'character', icon: 'pi pi-user' },
  { label: 'Lugares', value: 'location', icon: 'pi pi-map-marker' },
  { label: 'Organizaciones', value: 'organization', icon: 'pi pi-building' },
  { label: 'Objetos', value: 'object', icon: 'pi pi-box' },
  { label: 'Eventos', value: 'event', icon: 'pi pi-calendar' },
  { label: 'Conceptos', value: 'concept', icon: 'pi pi-lightbulb' },
  { label: 'Otros', value: 'other', icon: 'pi pi-tag' }
]

// Computed: solo mostrar tipos de entidades que existen en el proyecto
const entityTypes = computed(() => {
  const existingTypes = new Set(props.entities.map(e => e.type))
  const availableTypes = allEntityTypes.filter(t => existingTypes.has(t.value as any))

  // Siempre incluir "Todas" al principio si hay más de un tipo
  if (availableTypes.length > 1) {
    return [{ label: 'Todos', value: 'all', icon: 'pi pi-list' }, ...availableTypes]
  }
  return availableTypes
})

// Opciones de ordenamiento
const sortOptions = [
  { label: 'Más mencionadas', value: 'mention_count' },
  { label: 'Nombre (A-Z)', value: 'name_asc' },
  { label: 'Nombre (Z-A)', value: 'name_desc' },
  { label: 'Primera aparición', value: 'first_mention' },
  { label: 'Importancia', value: 'importance' }
]

// Menú contextual
const entityMenuItems = computed(() => [
  {
    label: 'Ver detalles',
    icon: 'pi pi-eye',
    command: () => selectedMenuEntity.value && emit('view', selectedMenuEntity.value)
  },
  {
    label: 'Editar',
    icon: 'pi pi-pencil',
    command: () => selectedMenuEntity.value && emit('edit', selectedMenuEntity.value)
  },
  { separator: true },
  {
    label: 'Fusionar con otra',
    icon: 'pi pi-link',
    command: () => selectedMenuEntity.value && emit('merge', selectedMenuEntity.value)
  },
  { separator: true },
  {
    label: 'Eliminar',
    icon: 'pi pi-trash',
    command: () => selectedMenuEntity.value && emit('delete', selectedMenuEntity.value),
    class: 'text-red-500'
  }
])

// Computed - Optimizado con memoización implícita y debounced search
// Paso 1: Filtrar por tipo (solo recalcula si cambia el tipo o las entidades)
const typeFilteredEntities = computed(() => {
  if (selectedType.value === 'all') {
    return props.entities
  }
  return props.entities.filter(e => e.type === selectedType.value)
})

// Paso 2: Filtrar por búsqueda (usa query con debounce)
const searchFilteredEntities = computed(() => {
  if (!debouncedSearchQuery.value) {
    return typeFilteredEntities.value
  }
  const query = debouncedSearchQuery.value.toLowerCase()
  return typeFilteredEntities.value.filter(e => {
    const nameMatch = e.name.toLowerCase().includes(query)
    const aliasMatch = e.aliases?.some(a => a.toLowerCase().includes(query))
    return nameMatch || aliasMatch
  })
})

// Paso 3: Ordenar (solo recalcula si cambia el criterio o los filtros)
const filteredEntities = computed(() => {
  const toSort = searchFilteredEntities.value
  // Usar spread para evitar mutar el array original
  return [...toSort].sort((a, b) => {
    switch (sortBy.value) {
      case 'name_asc':
        return a.name.localeCompare(b.name)
      case 'name_desc':
        return b.name.localeCompare(a.name)
      case 'first_mention':
        return (a.firstMentionChapter || 999) - (b.firstMentionChapter || 999)
      case 'importance':
        const importanceOrder = { 'main': 5, 'secondary': 3, 'minor': 1 }
        return (importanceOrder[b.importance as keyof typeof importanceOrder] || 0) -
               (importanceOrder[a.importance as keyof typeof importanceOrder] || 0)
      case 'mention_count':
      default:
        return (b.mentionCount || 0) - (a.mentionCount || 0)
    }
  })
})

const totalPages = computed(() => Math.ceil(filteredEntities.value.length / props.itemsPerPage))

const paginatedEntities = computed(() => {
  if (!props.showPagination) return filteredEntities.value

  const start = currentPage.value * props.itemsPerPage
  const end = start + props.itemsPerPage
  return filteredEntities.value.slice(start, end)
})

// Funciones
const selectType = (type: string) => {
  selectedType.value = type
  currentPage.value = 0
}

const clearFilters = () => {
  searchQuery.value = ''
  selectedType.value = 'all'
  currentPage.value = 0
}

const toggleExpanded = () => {
  expanded.value = !expanded.value
}

const onPageChange = (event: any) => {
  currentPage.value = event.page
}

const onEntityClick = (entity: Entity) => {
  if (props.clickable) {
    emit('select', entity)
  }
}

const showEntityMenu = (event: Event, entity: Entity) => {
  selectedMenuEntity.value = entity
  entityMenu.value.toggle(event)
}

const getTypeCount = (type: string): number => {
  if (type === 'all') return props.entities.length
  return props.entities.filter(e => e.type === type).length
}

const getEntityIcon = (type: string): string => {
  const icons: Record<string, string> = {
    'character': 'pi pi-user',
    'location': 'pi pi-map-marker',
    'organization': 'pi pi-building',
    'object': 'pi pi-box',
    'event': 'pi pi-calendar',
    'concept': 'pi pi-lightbulb',
    'other': 'pi pi-tag'
  }
  return icons[type] || 'pi pi-tag'
}

const getImportanceSeverity = (importance: string | undefined | null): string => {
  if (!importance) return 'secondary'
  const severities: Record<string, string> = {
    'main': 'success',        // Verde - protagonista/principal
    'secondary': 'info',      // Azul - secundario (más visible que amarillo)
    'minor': 'contrast'       // Contraste - menor (más distintivo que gris)
  }
  return severities[importance] || 'secondary'
}

const getImportanceLabel = (importance: string | undefined | null): string => {
  if (!importance) return 'Sin clasificar'
  const labels: Record<string, string> = {
    'main': 'Principal',
    'secondary': 'Secundario',
    'minor': 'Menor'
  }
  return labels[importance] || 'Sin clasificar'
}

// Watchers
watch(() => props.entities, () => {
  currentPage.value = 0
})

// Historial de fusiones
watch(showMergeHistoryDialog, async (show) => {
  if (show && props.projectId) {
    await loadMergeHistory()
  }
})

const loadMergeHistory = async () => {
  if (!props.projectId) return

  loadingMergeHistory.value = true
  try {
    const response = await fetch(`http://localhost:8008/api/projects/${props.projectId}/entities/merge-history`)
    const data = await response.json()

    if (data.success) {
      mergeHistory.value = data.data.merges || []
    }
  } catch (error) {
    console.error('Error loading merge history:', error)
  } finally {
    loadingMergeHistory.value = false
  }
}

const undoMerge = async (mergeId: number) => {
  if (!props.projectId) return

  undoingMerge.value = mergeId
  try {
    const response = await fetch(`http://localhost:8008/api/projects/${props.projectId}/entities/undo-merge/${mergeId}`, {
      method: 'POST'
    })
    const data = await response.json()

    if (data.success) {
      toast.add({
        severity: 'success',
        summary: 'Fusión deshecha',
        detail: 'Las entidades han sido restauradas',
        life: 3000
      })

      // Recargar historial y emitir evento de refresh
      await loadMergeHistory()
      emit('refresh')
    } else {
      throw new Error(data.error || 'Error desconocido')
    }
  } catch (error) {
    console.error('Error undoing merge:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo deshacer la fusión',
      life: 3000
    })
  } finally {
    undoingMerge.value = null
  }
}

const formatDate = (dateString: string): string => {
  if (!dateString) return ''
  try {
    const date = new Date(dateString)
    return date.toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return dateString
  }
}
</script>

<style scoped>
.entity-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--p-surface-0, white);
  border-radius: 8px;
  overflow: hidden;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--surface-50);
  border-bottom: 1px solid var(--surface-200);
}

.header-left h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-color);
}

.entity-count {
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
  border-bottom: 1px solid var(--surface-200);
}

.search-wrapper {
  position: relative;
  width: 100%;
}

.search-input {
  width: 100%;
  padding-right: 2.5rem;
}

.search-icon {
  position: absolute;
  right: 0.875rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-color-secondary);
  pointer-events: none;
}

.type-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.type-filters :deep(.p-button) {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.sort-dropdown {
  width: 100%;
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
}

.entities-container {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
}

.entities-container.compact .entity-item {
  padding: 0.5rem;
}

.entity-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  border-radius: 6px;
  margin-bottom: 0.5rem;
  background: var(--p-surface-0, white);
  border: 1px solid var(--p-surface-200, #e2e8f0);
  transition: all 0.2s;
}

.entity-item.entity-clickable {
  cursor: pointer;
}

.entity-item.entity-clickable:hover {
  background: var(--surface-50);
  border-color: var(--primary-color);
  transform: translateX(4px);
}

.entity-item.entity-selected {
  background: var(--primary-50);
  border-color: var(--primary-color);
}

.entity-main {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
  min-width: 0;
}

.entity-icon-wrapper {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-50);
  border-radius: 50%;
  flex-shrink: 0;
}

.entity-icon {
  font-size: 1.25rem;
  color: var(--primary-color);
}

.entity-info {
  flex: 1;
  min-width: 0;
}

.entity-name-row {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.entity-name {
  font-weight: 600;
  font-size: 0.9375rem;
  color: var(--text-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.merged-icon {
  font-size: 0.75rem;
  color: var(--blue-500);
  flex-shrink: 0;
}

.entity-aliases {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  margin-top: 0.25rem;
}

.alias-tag {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  background: var(--surface-100);
  border-radius: 12px;
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.alias-more {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  font-weight: 500;
}

.entity-meta {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.importance-tag {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}

/* Asegurar contraste suficiente en los badges de importancia */
:deep(.p-tag.p-tag-success) {
  background: var(--p-green-500);
  color: white;
}

:deep(.p-tag.p-tag-info) {
  background: var(--p-blue-500);
  color: white;
}

:deep(.p-tag.p-tag-contrast) {
  background: var(--p-surface-600);
  color: white;
}

.entity-stats {
  display: flex;
  gap: 0.75rem;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.stat-item i {
  font-size: 0.75rem;
}

.entity-actions {
  display: flex;
  gap: 0.25rem;
  flex-shrink: 0;
}

.pagination {
  padding: 0.75rem;
  border-top: 1px solid var(--surface-200);
  background: var(--surface-50);
}

.text-red-500 {
  color: #ef4444;
}

/* VirtualScroller styling */
.entities-virtual {
  height: 100%;
}

.entities-virtual :deep(.p-virtualscroller-content) {
  padding: 0.5rem;
}

.entity-item.entity-odd {
  background: var(--surface-50);
}

/* Scrollbar styling */
.entities-container::-webkit-scrollbar,
.entities-virtual :deep(.p-virtualscroller-content)::-webkit-scrollbar {
  width: 6px;
}

.entities-container::-webkit-scrollbar-track,
.entities-virtual :deep(.p-virtualscroller-content)::-webkit-scrollbar-track {
  background: var(--surface-50);
}

.entities-container::-webkit-scrollbar-thumb,
.entities-virtual :deep(.p-virtualscroller-content)::-webkit-scrollbar-thumb {
  background: var(--surface-300);
  border-radius: 3px;
}

.entities-container::-webkit-scrollbar-thumb:hover,
.entities-virtual :deep(.p-virtualscroller-content)::-webkit-scrollbar-thumb:hover {
  background: var(--surface-400);
}

/* Merge History Dialog */
.loading-history,
.empty-history {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  gap: 1rem;
  color: var(--text-color-secondary);
}

.empty-history i {
  font-size: 3rem;
  opacity: 0.5;
}

.merge-history-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  max-height: 400px;
  overflow-y: auto;
}

.merge-history-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 8px;
  border: 1px solid var(--surface-200);
  transition: all 0.2s;
}

.merge-history-item.undone {
  opacity: 0.6;
  background: var(--surface-100);
}

.merge-info {
  flex: 1;
  min-width: 0;
}

.merge-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.merge-date {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.merge-details {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.merge-names {
  font-weight: 500;
  color: var(--text-color);
}

.merge-details i {
  color: var(--text-color-secondary);
  font-size: 0.875rem;
}

.merge-result {
  font-weight: 600;
  color: var(--primary-color);
}
</style>
