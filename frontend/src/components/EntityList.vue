<template>
  <div class="entity-list">
    <!-- Header con filtros (solo mostrar si hay título o botones de acción) -->
    <div v-if="showTitle || showRefresh || showExpandButton" class="list-header">
      <div class="header-left">
        <h3 v-if="showTitle">Entidades</h3>
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
      <!-- Búsqueda con icono a la derecha -->
      <div class="search-wrapper">
        <InputText
          v-model="searchQuery"
          placeholder="Buscar entidades..."
          class="search-input"
        />
        <i class="pi pi-search search-icon" />
      </div>

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
            <i :class="getEntityIcon(entity.entity_type)" class="entity-icon"></i>
          </div>
          <div class="entity-info">
            <div class="entity-name">{{ entity.canonical_name }}</div>
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
            <span class="stat-item" v-tooltip.top="'Menciones'">
              <i class="pi pi-hashtag"></i>
              {{ entity.mention_count || 0 }}
            </span>
            <span
              v-if="entity.first_mention_chapter"
              class="stat-item"
              v-tooltip.top="'Primera mención'"
            >
              <i class="pi pi-book"></i>
              Cap. {{ entity.first_mention_chapter }}
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Dropdown from 'primevue/dropdown'
import Badge from 'primevue/badge'
import Tag from 'primevue/tag'
import ProgressSpinner from 'primevue/progressspinner'
import Paginator from 'primevue/paginator'
import Menu from 'primevue/menu'
import type { Entity, EntityImportance } from '../types/index'

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
  clickable?: boolean
  selectedEntityId?: number | null
  initialType?: string
  itemsPerPage?: number
}>(), {
  loading: false,
  compact: false,
  showTitle: true,
  showFilters: true,
  showActions: true,
  showPagination: true,
  showRefresh: false,
  showExpandButton: false,
  clickable: true,
  selectedEntityId: null,
  initialType: 'all',
  itemsPerPage: 20
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
const selectedType = ref(props.initialType)
const sortBy = ref('mention_count')
const expanded = ref(true)
const currentPage = ref(0)
const entityMenu = ref()
const selectedMenuEntity = ref<Entity | null>(null)

// Definición de todos los tipos de entidades posibles
const allEntityTypes = [
  { label: 'Personajes', value: 'CHARACTER', icon: 'pi pi-user' },
  { label: 'Lugares', value: 'LOCATION', icon: 'pi pi-map-marker' },
  { label: 'Organizaciones', value: 'ORGANIZATION', icon: 'pi pi-building' },
  { label: 'Objetos', value: 'OBJECT', icon: 'pi pi-box' },
  { label: 'Eventos', value: 'EVENT', icon: 'pi pi-calendar' },
  { label: 'Animales', value: 'ANIMAL', icon: 'pi pi-heart' },
  { label: 'Criaturas', value: 'CREATURE', icon: 'pi pi-moon' },
  { label: 'Edificios', value: 'BUILDING', icon: 'pi pi-home' },
  { label: 'Regiones', value: 'REGION', icon: 'pi pi-globe' },
  { label: 'Vehículos', value: 'VEHICLE', icon: 'pi pi-car' },
  { label: 'Facciones', value: 'FACTION', icon: 'pi pi-flag' },
  { label: 'Familias', value: 'FAMILY', icon: 'pi pi-users' },
  { label: 'Períodos', value: 'TIME_PERIOD', icon: 'pi pi-clock' },
  { label: 'Conceptos', value: 'CONCEPT', icon: 'pi pi-lightbulb' },
  { label: 'Religiones', value: 'RELIGION', icon: 'pi pi-star' },
  { label: 'Otros', value: 'OTHER', icon: 'pi pi-tag' }
]

// Computed: solo mostrar tipos de entidades que existen en el proyecto
const entityTypes = computed(() => {
  const existingTypes = new Set(props.entities.map(e => e.entity_type))
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

// Computed
const filteredEntities = computed(() => {
  let filtered = props.entities

  // Filtrar por tipo
  if (selectedType.value !== 'all') {
    filtered = filtered.filter(e => e.entity_type === selectedType.value)
  }

  // Filtrar por búsqueda
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(e => {
      const nameMatch = e.canonical_name.toLowerCase().includes(query)
      const aliasMatch = e.aliases?.some(a => a.toLowerCase().includes(query))
      return nameMatch || aliasMatch
    })
  }

  // Ordenar
  return [...filtered].sort((a, b) => {
    switch (sortBy.value) {
      case 'name_asc':
        return a.canonical_name.localeCompare(b.canonical_name)
      case 'name_desc':
        return b.canonical_name.localeCompare(a.canonical_name)
      case 'first_mention':
        return (a.first_mention_chapter || 999) - (b.first_mention_chapter || 999)
      case 'importance':
        const importanceOrder = { 'critical': 5, 'high': 4, 'medium': 3, 'low': 2, 'minimal': 1 }
        return (importanceOrder[b.importance as keyof typeof importanceOrder] || 0) -
               (importanceOrder[a.importance as keyof typeof importanceOrder] || 0)
      case 'mention_count':
      default:
        return (b.mention_count || 0) - (a.mention_count || 0)
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
  return props.entities.filter(e => e.entity_type === type).length
}

const getEntityIcon = (type: string): string => {
  const icons: Record<string, string> = {
    'CHARACTER': 'pi pi-user',
    'LOCATION': 'pi pi-map-marker',
    'ORGANIZATION': 'pi pi-building',
    'OBJECT': 'pi pi-box',
    'EVENT': 'pi pi-calendar'
  }
  return icons[type] || 'pi pi-tag'
}

const getImportanceSeverity = (importance: string): string => {
  const severities: Record<string, string> = {
    'critical': 'danger',
    'high': 'warning',
    'medium': 'info',
    'low': 'secondary',
    'minimal': 'contrast'
  }
  return severities[importance] || 'secondary'
}

const getImportanceLabel = (importance: string): string => {
  const labels: Record<string, string> = {
    'critical': 'Crítica',
    'high': 'Alta',
    'medium': 'Media',
    'low': 'Baja',
    'minimal': 'Mínima'
  }
  return labels[importance] || importance
}

// Watchers
watch(() => props.entities, () => {
  currentPage.value = 0
})
</script>

<style scoped>
.entity-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: white;
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
  background: white;
  border: 1px solid var(--surface-200);
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

.entity-name {
  font-weight: 600;
  font-size: 0.9375rem;
  color: var(--text-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

/* Scrollbar styling */
.entities-container::-webkit-scrollbar {
  width: 6px;
}

.entities-container::-webkit-scrollbar-track {
  background: var(--surface-50);
}

.entities-container::-webkit-scrollbar-thumb {
  background: var(--surface-300);
  border-radius: 3px;
}

.entities-container::-webkit-scrollbar-thumb:hover {
  background: var(--surface-400);
}
</style>
