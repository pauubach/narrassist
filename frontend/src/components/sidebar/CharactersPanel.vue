<script setup lang="ts">
import { computed } from 'vue'
import type { Entity } from '@/types'
import { useSelectionStore } from '@/stores/selection'
import { useEntityUtils } from '@/composables/useEntityUtils'

/**
 * CharactersPanel - Panel de personajes principales para el sidebar.
 *
 * Muestra los personajes ordenados por número de menciones.
 * Soporta selección y resaltado del personaje activo.
 */

const props = defineProps<{
  /** Lista de entidades (se filtran solo personajes) */
  entities: Entity[]
  /** Máximo de personajes a mostrar */
  maxItems?: number
}>()

const emit = defineEmits<{
  /** Cuando se selecciona un personaje */
  (e: 'select', entity: Entity): void
  /** Cuando se hace doble click (ver ficha completa) */
  (e: 'view-details', entity: Entity): void
}>()

const selectionStore = useSelectionStore()
const { getEntityIcon } = useEntityUtils()

/** Personajes ordenados por menciones */
const topCharacters = computed(() => {
  const max = props.maxItems ?? 10
  return props.entities
    .filter(e => e.type === 'character' && e.isActive)
    .sort((a, b) => b.mentionCount - a.mentionCount)
    .slice(0, max)
})

/** Total de personajes */
const totalCount = computed(() =>
  props.entities.filter(e => e.type === 'character' && e.isActive).length
)

function isSelected(entityId: number): boolean {
  return selectionStore.selectedEntityIds.includes(entityId)
}

function handleClick(entity: Entity) {
  emit('select', entity)
}

function handleDoubleClick(entity: Entity) {
  emit('view-details', entity)
}
</script>

<template>
  <div class="characters-panel">
    <div class="panel-header">
      <span class="panel-title">Personajes</span>
      <span class="panel-count">{{ totalCount }}</span>
    </div>

    <div v-if="topCharacters.length === 0" class="empty-state">
      <i class="pi pi-users"></i>
      <span>Sin personajes</span>
    </div>

    <div v-else class="characters-list">
      <button
        v-for="char in topCharacters"
        :key="char.id"
        type="button"
        class="character-item"
        :class="{ 'character-item--active': isSelected(char.id) }"
        @click="handleClick(char)"
        @dblclick="handleDoubleClick(char)"
      >
        <i :class="getEntityIcon(char.type)" class="character-icon"></i>
        <span class="character-name">{{ char.name }}</span>
        <span class="character-mentions">{{ char.mentionCount }}</span>
      </button>
    </div>

    <div v-if="totalCount > (maxItems ?? 10)" class="show-more">
      <span>+{{ totalCount - (maxItems ?? 10) }} más</span>
    </div>
  </div>
</template>

<style scoped>
.characters-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--ds-space-3);
  border-bottom: 1px solid var(--ds-surface-border);
}

.panel-title {
  font-weight: var(--ds-font-weight-semibold);
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
}

.panel-count {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  background: var(--ds-surface-hover);
  padding: 2px 8px;
  border-radius: var(--ds-radius-full);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-6);
  color: var(--ds-color-text-secondary);
}

.empty-state i {
  font-size: 2rem;
  opacity: 0.5;
}

.characters-list {
  display: flex;
  flex-direction: column;
  padding: var(--ds-space-2);
  overflow-y: auto;
  flex: 1;
}

.character-item {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2) var(--ds-space-3);
  border: none;
  background: transparent;
  border-radius: var(--ds-radius-md);
  cursor: pointer;
  transition: background-color var(--ds-transition-fast);
  width: 100%;
  text-align: left;
}

.character-item:hover {
  background: var(--ds-surface-hover);
}

.character-item--active {
  background: var(--ds-color-primary-soft);
}

.character-item--active:hover {
  background: var(--ds-color-primary-soft);
}

.character-icon {
  font-size: 0.875rem;
  color: var(--ds-color-text-secondary);
  width: 1.25rem;
  text-align: center;
}

.character-item--active .character-icon {
  color: var(--ds-color-primary);
}

.character-name {
  flex: 1;
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.character-item--active .character-name {
  font-weight: var(--ds-font-weight-medium);
  color: var(--ds-color-primary);
}

.character-mentions {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.show-more {
  padding: var(--ds-space-2) var(--ds-space-3);
  text-align: center;
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  border-top: 1px solid var(--ds-surface-border);
}
</style>
