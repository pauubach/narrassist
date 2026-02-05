<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useSelectionStore } from '@/stores/selection'
import { useEntityUtils } from '@/composables/useEntityUtils'
import DsInput from '@/components/ds/DsInput.vue'
import DsListItem from '@/components/ds/DsListItem.vue'
import DsBadge from '@/components/ds/DsBadge.vue'
import DsEmptyState from '@/components/ds/DsEmptyState.vue'
import DsLoadingState from '@/components/ds/DsLoadingState.vue'
import type { Entity, EntityType } from '@/types'

/**
 * EntityPanel - Panel lateral con lista de entidades filtrable.
 *
 * Muestra entidades agrupadas por tipo o importancia con búsqueda.
 */

const props = defineProps<{
  /** Lista de entidades */
  entities: Entity[]
  /** Si está cargando */
  loading?: boolean
  /** Agrupación: por tipo o por importancia */
  groupBy?: 'type' | 'importance' | 'none'
}>()

const emit = defineEmits<{
  select: [entity: Entity]
  'context-menu': [event: MouseEvent, entity: Entity]
}>()

const selectionStore = useSelectionStore()
const { getTypeConfig, getImportanceConfig, filterEntities, sortEntities, groupEntitiesByType } =
  useEntityUtils()

const searchQuery = ref('')
const activeFilter = ref<EntityType | 'all'>('all')

// Tipos disponibles para filtrar
const typeFilters = computed(() => {
  const types = new Set(props.entities.map((e) => e.type))
  return [
    { value: 'all' as const, label: 'Todos', count: props.entities.length },
    ...Array.from(types).map((type) => ({
      value: type,
      label: getTypeConfig(type).label,
      count: props.entities.filter((e) => e.type === type).length,
    })),
  ]
})

// Entidades filtradas y ordenadas
const filteredEntities = computed(() => {
  let result = props.entities

  // Filtrar por tipo
  if (activeFilter.value !== 'all') {
    result = result.filter((e) => e.type === activeFilter.value)
  }

  // Filtrar por búsqueda
  result = filterEntities(result, searchQuery.value)

  // Ordenar
  return sortEntities(result)
})

// Entidades agrupadas
const groupedEntities = computed(() => {
  if (props.groupBy === 'type') {
    return groupEntitiesByType(filteredEntities.value)
  }
  return null
})

function handleSelect(entity: Entity) {
  selectionStore.selectEntity(entity)
  emit('select', entity)
}

function handleContextMenu(event: MouseEvent, entity: Entity) {
  event.preventDefault()
  emit('context-menu', event, entity)
}

function isSelected(entity: Entity): boolean {
  return selectionStore.isSelected('entity', entity.id)
}

// Limpiar búsqueda al cambiar filtro
watch(activeFilter, () => {
  searchQuery.value = ''
})
</script>

<template>
  <div class="entity-panel">
    <!-- Header con búsqueda -->
    <div class="entity-panel__header">
      <DsInput
        v-model="searchQuery"
        placeholder="Buscar entidades..."
        icon="pi pi-search"
        size="sm"
        clearable
      />
    </div>

    <!-- Filtros por tipo -->
    <div class="entity-panel__filters">
      <button
        v-for="filter in typeFilters"
        :key="filter.value"
        type="button"
        class="entity-panel__filter"
        :class="{ 'entity-panel__filter--active': activeFilter === filter.value }"
        @click="activeFilter = filter.value"
      >
        {{ filter.label }}
        <span class="entity-panel__filter-count">{{ filter.count }}</span>
      </button>
    </div>

    <!-- Loading state -->
    <DsLoadingState v-if="loading" message="Cargando entidades..." size="sm" />

    <!-- Empty state -->
    <DsEmptyState
      v-else-if="filteredEntities.length === 0"
      icon="pi pi-users"
      :title="searchQuery ? 'Sin resultados' : 'Sin entidades'"
      :description="
        searchQuery ? 'Prueba con otros términos de búsqueda' : 'Analiza el documento para extraer entidades'
      "
      size="sm"
    />

    <!-- Lista de entidades -->
    <div v-else class="entity-panel__list">
      <!-- Sin agrupación -->
      <template v-if="!groupedEntities">
        <DsListItem
          v-for="entity in filteredEntities"
          :key="entity.id"
          :title="entity.name"
          :subtitle="getTypeConfig(entity.type).label"
          clickable
          :selected="isSelected(entity)"
          density="compact"
          @click="handleSelect(entity)"
          @contextmenu="handleContextMenu($event, entity)"
        >
          <template #prefix>
            <DsBadge :entity-type="entity.type" variant="subtle" size="sm">
              <i :class="getTypeConfig(entity.type).icon" />
            </DsBadge>
          </template>
          <template #suffix>
            <span class="entity-panel__mentions">{{ entity.mentionCount }}</span>
          </template>
        </DsListItem>
      </template>

      <!-- Con agrupación por tipo -->
      <template v-else>
        <div v-for="[type, groupItems] in groupedEntities" :key="type" class="entity-panel__group">
          <div class="entity-panel__group-header">
            <i :class="getTypeConfig(type).icon" />
            <span>{{ getTypeConfig(type).labelPlural }}</span>
            <span class="entity-panel__group-count">{{ groupItems.length }}</span>
          </div>
          <DsListItem
            v-for="entity in groupItems"
            :key="entity.id"
            :title="entity.name"
            clickable
            :selected="isSelected(entity)"
            density="compact"
            @click="handleSelect(entity)"
            @contextmenu="handleContextMenu($event, entity)"
          >
            <template #prefix>
              <DsBadge
                :color="getImportanceConfig(entity.importance).weight === 3 ? 'primary' : 'secondary'"
                variant="subtle"
                size="sm"
              >
                <i :class="getImportanceConfig(entity.importance).icon" />
              </DsBadge>
            </template>
            <template #suffix>
              <span class="entity-panel__mentions">{{ entity.mentionCount }}</span>
            </template>
          </DsListItem>
        </div>
      </template>
    </div>

    <!-- Footer con stats -->
    <div class="entity-panel__footer">
      <span>{{ filteredEntities.length }} de {{ entities.length }} entidades</span>
    </div>
  </div>
</template>

<style scoped>
.entity-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.entity-panel__header {
  padding: var(--ds-space-3);
  border-bottom: 1px solid var(--ds-surface-border);
}

.entity-panel__filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-1);
  padding: var(--ds-space-2) var(--ds-space-3);
  border-bottom: 1px solid var(--ds-surface-border);
}

.entity-panel__filter {
  display: inline-flex;
  align-items: center;
  gap: var(--ds-space-1);
  padding: var(--ds-space-1) var(--ds-space-2);
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  background: transparent;
  border: 1px solid var(--ds-surface-border);
  border-radius: var(--ds-radius-full);
  cursor: pointer;
  transition: var(--ds-transition-fast);
}

.entity-panel__filter:hover {
  background-color: var(--ds-surface-hover);
}

.entity-panel__filter--active {
  color: var(--ds-color-primary);
  border-color: var(--ds-color-primary);
  background-color: var(--ds-color-primary-light);
}

.entity-panel__filter-count {
  font-weight: var(--ds-font-weight-semibold);
}

.entity-panel__list {
  flex: 1;
  overflow-y: auto;
  padding: var(--ds-space-2) 0;
}

.entity-panel__group {
  margin-bottom: var(--ds-space-2);
}

.entity-panel__group-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2) var(--ds-space-3);
  font-size: var(--ds-font-size-xs);
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.entity-panel__group-count {
  margin-left: auto;
  padding: var(--ds-space-0-5) var(--ds-space-1-5);
  font-size: var(--ds-font-size-xs);
  background-color: var(--ds-surface-hover);
  border-radius: var(--ds-radius-full);
}

.entity-panel__mentions {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-muted);
}

.entity-panel__footer {
  padding: var(--ds-space-2) var(--ds-space-3);
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-muted);
  text-align: center;
  border-top: 1px solid var(--ds-surface-border);
}
</style>
