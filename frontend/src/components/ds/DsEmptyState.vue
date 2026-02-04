<script setup lang="ts">
import { computed } from 'vue'

/**
 * DsEmptyState - Estado vacío con ilustración, mensaje y acción.
 *
 * Uso:
 *   <DsEmptyState
 *     icon="pi pi-inbox"
 *     title="Sin entidades"
 *     description="Analiza un documento para extraer entidades"
 *   >
 *     <template #action>
 *       <Button label="Analizar" @click="analyze" />
 *     </template>
 *   </DsEmptyState>
 */

export interface Props {
  /** Icono a mostrar (clase PrimeIcons) */
  icon?: string
  /** Título del estado vacío */
  title: string
  /** Descripción adicional */
  description?: string
  /** Tamaño del componente */
  size?: 'sm' | 'md' | 'lg'
}

const props = withDefaults(defineProps<Props>(), {
  size: 'md'
})

const classes = computed(() => ['ds-empty-state', `ds-empty-state--${props.size}`])
</script>

<template>
  <div :class="classes">
    <div v-if="$slots.illustration" class="ds-empty-state__illustration">
      <slot name="illustration" />
    </div>
    <i v-else-if="icon" :class="['ds-empty-state__icon', icon]" />

    <h3 class="ds-empty-state__title">{{ title }}</h3>
    <p v-if="description" class="ds-empty-state__description">{{ description }}</p>

    <div v-if="$slots.action" class="ds-empty-state__action">
      <slot name="action" />
    </div>
  </div>
</template>

<style scoped>
.ds-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: var(--ds-space-8);
}

/* Sizes */
.ds-empty-state--sm {
  padding: var(--ds-space-4);
}

.ds-empty-state--sm .ds-empty-state__icon {
  font-size: 2rem;
}

.ds-empty-state--sm .ds-empty-state__title {
  font-size: var(--ds-font-size-base);
}

.ds-empty-state--sm .ds-empty-state__description {
  font-size: var(--ds-font-size-sm);
}

.ds-empty-state--md .ds-empty-state__icon {
  font-size: 3rem;
}

.ds-empty-state--md .ds-empty-state__title {
  font-size: var(--ds-font-size-lg);
}

.ds-empty-state--lg {
  padding: var(--ds-space-12);
}

.ds-empty-state--lg .ds-empty-state__icon {
  font-size: 4rem;
}

.ds-empty-state--lg .ds-empty-state__title {
  font-size: var(--ds-font-size-xl);
}

/* Icon */
.ds-empty-state__icon {
  color: var(--ds-color-text-muted);
  margin-bottom: var(--ds-space-4);
  opacity: 0.5;
}

/* Illustration */
.ds-empty-state__illustration {
  margin-bottom: var(--ds-space-4);
  max-width: 200px;
}

.ds-empty-state--sm .ds-empty-state__illustration {
  max-width: 120px;
}

.ds-empty-state--lg .ds-empty-state__illustration {
  max-width: 280px;
}

/* Title */
.ds-empty-state__title {
  margin: 0;
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-text);
}

/* Description */
.ds-empty-state__description {
  margin: var(--ds-space-2) 0 0;
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-muted);
  max-width: 300px;
  line-height: var(--ds-line-height-relaxed);
}

/* Action */
.ds-empty-state__action {
  margin-top: var(--ds-space-6);
}

.ds-empty-state--sm .ds-empty-state__action {
  margin-top: var(--ds-space-4);
}
</style>
