<script setup lang="ts">
import { computed } from 'vue'

/**
 * DsListItem - Item de lista reutilizable con soporte para iconos, badges y acciones.
 *
 * Uso:
 *   <DsListItem title="María García" subtitle="Personaje principal" @click="select">
 *     <template #prefix><DsBadge entity-type="character">P</DsBadge></template>
 *     <template #suffix><i class="pi pi-chevron-right" /></template>
 *   </DsListItem>
 */

export interface Props {
  /** Título principal */
  title: string
  /** Subtítulo opcional */
  subtitle?: string
  /** Descripción larga opcional */
  description?: string
  /** Si es clickeable */
  clickable?: boolean
  /** Si está seleccionado */
  selected?: boolean
  /** Si está activo (hover persistente) */
  active?: boolean
  /** Si está deshabilitado */
  disabled?: boolean
  /** Densidad del item */
  density?: 'compact' | 'default' | 'comfortable'
}

const props = withDefaults(defineProps<Props>(), {
  clickable: false,
  selected: false,
  active: false,
  disabled: false,
  density: 'default'
})

const emit = defineEmits<{
  click: [event: MouseEvent]
}>()

const classes = computed(() => {
  const base = ['ds-list-item', `ds-list-item--${props.density}`]

  if (props.clickable) base.push('ds-list-item--clickable')
  if (props.selected) base.push('ds-list-item--selected')
  if (props.active) base.push('ds-list-item--active')
  if (props.disabled) base.push('ds-list-item--disabled')

  return base
})

function handleClick(event: MouseEvent) {
  if (!props.disabled) {
    emit('click', event)
  }
}

function handleKeydown(event: KeyboardEvent) {
  if (!props.disabled) {
    emit('click', event as unknown as MouseEvent)
  }
}
</script>

<template>
  <div
    :class="classes"
    :tabindex="clickable && !disabled ? 0 : undefined"
    :role="clickable ? 'button' : undefined"
    @click="handleClick"
    @keydown.enter="handleKeydown"
    @keydown.space.prevent="handleKeydown"
  >
    <div v-if="$slots.prefix" class="ds-list-item__prefix">
      <slot name="prefix" />
    </div>

    <div class="ds-list-item__content">
      <span class="ds-list-item__title">{{ title }}</span>
      <span v-if="subtitle" class="ds-list-item__subtitle">{{ subtitle }}</span>
      <p v-if="description" class="ds-list-item__description">{{ description }}</p>
    </div>

    <div v-if="$slots.suffix" class="ds-list-item__suffix">
      <slot name="suffix" />
    </div>
  </div>
</template>

<style scoped>
.ds-list-item {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
  border-radius: var(--ds-radius-md);
  transition: var(--ds-transition-fast);
}

/* Density */
.ds-list-item--compact {
  padding: var(--ds-space-2) var(--ds-space-3);
}

.ds-list-item--default {
  padding: var(--ds-space-3) var(--ds-space-4);
}

.ds-list-item--comfortable {
  padding: var(--ds-space-4) var(--ds-space-5);
}

/* States */
.ds-list-item--clickable {
  cursor: pointer;
}

.ds-list-item--clickable:hover:not(.ds-list-item--disabled) {
  background-color: var(--ds-surface-hover);
}

.ds-list-item--clickable:focus-visible {
  outline: 2px solid var(--ds-color-primary);
  outline-offset: -2px;
}

.ds-list-item--selected {
  background-color: var(--ds-surface-hover);
  border-left: 3px solid var(--ds-color-primary);
}

.ds-list-item--active {
  background-color: var(--ds-surface-hover);
}

.ds-list-item--disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

/* Prefix/Suffix */
.ds-list-item__prefix,
.ds-list-item__suffix {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.ds-list-item__suffix {
  margin-left: auto;
  color: var(--ds-color-text-muted);
}

/* Content */
.ds-list-item__content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-0-5);
}

.ds-list-item__title {
  font-weight: var(--ds-font-weight-medium);
  color: var(--ds-color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ds-list-item__subtitle {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ds-list-item__description {
  margin: 0;
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-muted);
  line-height: var(--ds-line-height-normal);
}

/* Density adjustments for text */
.ds-list-item--compact .ds-list-item__title {
  font-size: var(--ds-font-size-sm);
}

.ds-list-item--compact .ds-list-item__subtitle,
.ds-list-item--compact .ds-list-item__description {
  font-size: var(--ds-font-size-xs);
}

.ds-list-item--comfortable .ds-list-item__title {
  font-size: var(--ds-font-size-lg);
}
</style>
