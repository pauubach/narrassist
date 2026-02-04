<script setup lang="ts">
import { computed } from 'vue'

/**
 * DsCard - Card con variantes para diferentes contextos.
 *
 * Uso:
 *   <DsCard>Contenido</DsCard>
 *   <DsCard variant="elevated" clickable @click="handleClick">...</DsCard>
 *   <DsCard variant="outlined" selected>...</DsCard>
 */

export interface Props {
  /** Variante visual */
  variant?: 'flat' | 'elevated' | 'outlined'
  /** Si el card es clickeable */
  clickable?: boolean
  /** Si está seleccionado */
  selected?: boolean
  /** Si está deshabilitado */
  disabled?: boolean
  /** Padding interno */
  padding?: 'none' | 'sm' | 'md' | 'lg'
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'flat',
  clickable: false,
  selected: false,
  disabled: false,
  padding: 'md'
})

const emit = defineEmits<{
  click: [event: MouseEvent]
}>()

const classes = computed(() => {
  const base = ['ds-card', `ds-card--${props.variant}`, `ds-card--padding-${props.padding}`]

  if (props.clickable) base.push('ds-card--clickable')
  if (props.selected) base.push('ds-card--selected')
  if (props.disabled) base.push('ds-card--disabled')

  return base
})

function handleClick(event: MouseEvent) {
  if (!props.disabled && props.clickable) {
    emit('click', event)
  }
}

function handleKeydown(event: KeyboardEvent) {
  if (!props.disabled && props.clickable) {
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
    <div v-if="$slots.header" class="ds-card__header">
      <slot name="header" />
    </div>
    <div class="ds-card__body">
      <slot />
    </div>
    <div v-if="$slots.footer" class="ds-card__footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<style scoped>
.ds-card {
  display: flex;
  flex-direction: column;
  background-color: var(--ds-surface-card);
  border-radius: var(--ds-radius-lg);
  transition: var(--ds-transition-base);
}

/* Variants */
.ds-card--flat {
  box-shadow: none;
}

.ds-card--elevated {
  box-shadow: var(--ds-shadow-md);
}

.ds-card--outlined {
  border: 1px solid var(--ds-surface-border);
}

/* Padding */
.ds-card--padding-none .ds-card__body {
  padding: 0;
}

.ds-card--padding-sm .ds-card__body {
  padding: var(--ds-space-3);
}

.ds-card--padding-md .ds-card__body {
  padding: var(--ds-space-4);
}

.ds-card--padding-lg .ds-card__body {
  padding: var(--ds-space-6);
}

/* Header */
.ds-card__header {
  padding: var(--ds-space-4);
  border-bottom: 1px solid var(--ds-surface-border);
}

.ds-card--padding-sm .ds-card__header {
  padding: var(--ds-space-3);
}

.ds-card--padding-lg .ds-card__header {
  padding: var(--ds-space-6);
}

/* Footer */
.ds-card__footer {
  padding: var(--ds-space-4);
  border-top: 1px solid var(--ds-surface-border);
}

.ds-card--padding-sm .ds-card__footer {
  padding: var(--ds-space-3);
}

.ds-card--padding-lg .ds-card__footer {
  padding: var(--ds-space-6);
}

/* Clickable */
.ds-card--clickable {
  cursor: pointer;
}

.ds-card--clickable:hover:not(.ds-card--disabled) {
  box-shadow: var(--ds-shadow-lg);
  transform: translateY(-1px);
}

.ds-card--clickable:focus-visible {
  outline: 2px solid var(--ds-color-primary);
  outline-offset: 2px;
}

/* Selected */
.ds-card--selected {
  border: 2px solid var(--ds-color-primary);
  background-color: var(--ds-surface-hover);
}

/* Disabled */
.ds-card--disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}
</style>
