<script setup lang="ts">
import { computed } from 'vue'

/**
 * DsBadge - Badge unificado con soporte para severidades, tipos de entidad y variantes.
 *
 * Uso:
 *   <DsBadge severity="high">Crítico</DsBadge>
 *   <DsBadge entity-type="character">Personaje</DsBadge>
 *   <DsBadge variant="outline" color="primary">Custom</DsBadge>
 */

export interface Props {
  /** Severidad de alerta (error, warning, info, success) */
  severity?: 'critical' | 'high' | 'medium' | 'low' | 'info'
  /** Tipo de entidad */
  entityType?: 'character' | 'location' | 'object' | 'event' | 'concept' | 'organization' | 'other'
  /** Variante visual */
  variant?: 'filled' | 'outline' | 'subtle'
  /** Color personalizado (usa tokens CSS) */
  color?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'info'
  /** Tamaño */
  size?: 'sm' | 'md' | 'lg'
  /** Icono a mostrar (clase de PrimeIcons) */
  icon?: string
  /** Si es removible */
  removable?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'filled',
  size: 'md'
})

const emit = defineEmits<{
  remove: []
}>()

const classes = computed(() => {
  const base = ['ds-badge', `ds-badge--${props.variant}`, `ds-badge--${props.size}`]

  if (props.severity) {
    base.push(`ds-badge--severity-${props.severity}`)
  } else if (props.entityType) {
    base.push(`ds-badge--entity-${props.entityType}`)
  } else if (props.color) {
    base.push(`ds-badge--${props.color}`)
  }

  if (props.removable) {
    base.push('ds-badge--removable')
  }

  return base
})
</script>

<template>
  <span :class="classes">
    <i v-if="icon" :class="['ds-badge__icon', icon]" />
    <span class="ds-badge__content">
      <slot />
    </span>
    <button
      v-if="removable"
      type="button"
      class="ds-badge__remove"
      aria-label="Eliminar"
      @click="emit('remove')"
    >
      <i class="pi pi-times" />
    </button>
  </span>
</template>

<style scoped>
.ds-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--ds-space-1);
  font-family: var(--ds-font-family);
  font-weight: var(--ds-font-weight-medium);
  border-radius: var(--ds-radius-full);
  white-space: nowrap;
  transition: var(--ds-transition-fast);
}

/* Sizes */
.ds-badge--sm {
  padding: var(--ds-space-0-5) var(--ds-space-2);
  font-size: var(--ds-font-size-xs);
}

.ds-badge--md {
  padding: var(--ds-space-1) var(--ds-space-3);
  font-size: var(--ds-font-size-sm);
}

.ds-badge--lg {
  padding: var(--ds-space-1-5) var(--ds-space-4);
  font-size: var(--ds-font-size-base);
}

/* Filled variant - base colors */
.ds-badge--filled {
  color: white;
}

.ds-badge--filled.ds-badge--primary {
  background-color: var(--ds-color-primary);
}

.ds-badge--filled.ds-badge--secondary {
  background-color: var(--ds-color-secondary);
}

.ds-badge--filled.ds-badge--success {
  background-color: var(--ds-color-success);
}

.ds-badge--filled.ds-badge--warning {
  background-color: var(--ds-color-warning);
  color: var(--ds-color-text);
}

.ds-badge--filled.ds-badge--danger {
  background-color: var(--ds-color-danger);
}

.ds-badge--filled.ds-badge--info {
  background-color: var(--ds-color-info);
}

/* Severity colors - filled */
.ds-badge--filled.ds-badge--severity-critical {
  background-color: var(--ds-alert-critical);
  color: white;
}

.ds-badge--filled.ds-badge--severity-high {
  background-color: var(--ds-alert-high);
  color: white;
}

.ds-badge--filled.ds-badge--severity-medium {
  background-color: var(--ds-alert-medium);
  color: #1a1a1a; /* Texto oscuro para mejor contraste en fondo amarillo */
}

.ds-badge--filled.ds-badge--severity-low {
  background-color: var(--ds-alert-low);
  color: white;
}

.ds-badge--filled.ds-badge--severity-info {
  background-color: var(--ds-alert-info);
  color: white;
}

/* Entity type colors - filled */
.ds-badge--filled.ds-badge--entity-character {
  background-color: var(--ds-entity-character);
}

.ds-badge--filled.ds-badge--entity-location {
  background-color: var(--ds-entity-location);
}

.ds-badge--filled.ds-badge--entity-object {
  background-color: var(--ds-entity-object);
}

.ds-badge--filled.ds-badge--entity-event {
  background-color: var(--ds-entity-event);
}

.ds-badge--filled.ds-badge--entity-concept {
  background-color: var(--ds-entity-concept);
}

.ds-badge--filled.ds-badge--entity-organization {
  background-color: var(--ds-entity-organization, var(--ds-color-info));
}

.ds-badge--filled.ds-badge--entity-other {
  background-color: var(--ds-color-secondary);
}

/* Outline variant - WCAG AA: colores oscuros para garantizar 4.5:1 en fondos claros */
.ds-badge--outline {
  background-color: transparent;
  border: 1px solid currentColor;
}

.ds-badge--outline.ds-badge--primary {
  color: #1d4ed8; /* blue-700: 4.6:1 sobre blanco */
}

.ds-badge--outline.ds-badge--secondary {
  color: #374151; /* gray-700: 9.5:1 sobre blanco */
}

.ds-badge--outline.ds-badge--success {
  color: #15803d; /* green-700: 4.5:1 sobre blanco */
}

.ds-badge--outline.ds-badge--warning {
  color: #a16207; /* yellow-700: 4.6:1 sobre blanco */
}

.ds-badge--outline.ds-badge--danger {
  color: #b91c1c; /* red-700: 5.0:1 sobre blanco */
}

.ds-badge--outline.ds-badge--info {
  color: #1d4ed8; /* blue-700: 4.6:1 sobre blanco */
}

.ds-badge--outline.ds-badge--severity-critical {
  color: #b91c1c; /* red-700 */
}

.ds-badge--outline.ds-badge--severity-high {
  color: #c2410c; /* orange-700: 4.6:1 sobre blanco */
}

.ds-badge--outline.ds-badge--severity-medium {
  color: #a16207; /* yellow-700: 4.6:1 sobre blanco */
}

.ds-badge--outline.ds-badge--severity-low {
  color: #1d4ed8; /* blue-700 */
}

.ds-badge--outline.ds-badge--severity-info {
  color: #374151; /* gray-700 */
}

.ds-badge--outline.ds-badge--entity-character {
  color: #7c3aed; /* violet-600: 4.5:1 sobre blanco */
}

.ds-badge--outline.ds-badge--entity-location {
  color: #0f766e; /* teal-700: 4.8:1 sobre blanco */
}

.ds-badge--outline.ds-badge--entity-object {
  color: #c2410c; /* orange-700: 4.6:1 sobre blanco */
}

.ds-badge--outline.ds-badge--entity-event {
  color: #be123c; /* rose-700: 5.2:1 sobre blanco */
}

.ds-badge--outline.ds-badge--entity-concept {
  color: #374151; /* gray-700 */
}

.ds-badge--outline.ds-badge--entity-organization {
  color: #4338ca; /* indigo-700: 6.3:1 sobre blanco */
}

.ds-badge--outline.ds-badge--entity-other {
  color: #374151; /* gray-700 */
}

/* Subtle variant - WCAG AA: fondo coloreado claro con texto oscuro */
.ds-badge--subtle {
  border: none;
}

.ds-badge--subtle.ds-badge--primary {
  background-color: #dbeafe; /* blue-100 */
  color: #1e40af; /* blue-800: 8.5:1 */
}

.ds-badge--subtle.ds-badge--secondary {
  background-color: #f1f5f9; /* slate-100 */
  color: #334155; /* slate-700: 7.5:1 */
}

.ds-badge--subtle.ds-badge--success {
  background-color: #dcfce7; /* green-100 */
  color: #166534; /* green-800: 7.1:1 */
}

.ds-badge--subtle.ds-badge--warning {
  background-color: #fef3c7; /* amber-100 */
  color: #92400e; /* amber-800: 5.8:1 */
}

.ds-badge--subtle.ds-badge--danger {
  background-color: #fee2e2; /* red-100 */
  color: #991b1b; /* red-800: 6.6:1 */
}

.ds-badge--subtle.ds-badge--info {
  background-color: #dbeafe; /* blue-100 */
  color: #1e40af; /* blue-800 */
}

.ds-badge--subtle.ds-badge--severity-critical {
  background-color: #fee2e2; /* red-100 */
  color: #991b1b; /* red-800 */
}

.ds-badge--subtle.ds-badge--severity-high {
  background-color: #ffedd5; /* orange-100 */
  color: #9a3412; /* orange-800: 5.5:1 */
}

.ds-badge--subtle.ds-badge--severity-medium {
  background-color: #fef3c7; /* amber-100 */
  color: #92400e; /* amber-800 */
}

.ds-badge--subtle.ds-badge--severity-low {
  background-color: #dbeafe; /* blue-100 */
  color: #1e40af; /* blue-800 */
}

.ds-badge--subtle.ds-badge--severity-info {
  background-color: #f1f5f9; /* slate-100 */
  color: #334155; /* slate-700 */
}

.ds-badge--subtle.ds-badge--entity-character {
  background-color: #ede9fe; /* violet-100 */
  color: #5b21b6; /* violet-800: 8.2:1 */
}

.ds-badge--subtle.ds-badge--entity-location {
  background-color: #ccfbf1; /* teal-100 */
  color: #115e59; /* teal-800: 6.5:1 */
}

.ds-badge--subtle.ds-badge--entity-object {
  background-color: #ffedd5; /* orange-100 */
  color: #9a3412; /* orange-800 */
}

.ds-badge--subtle.ds-badge--entity-event {
  background-color: #ffe4e6; /* rose-100 */
  color: #9f1239; /* rose-800: 6.8:1 */
}

.ds-badge--subtle.ds-badge--entity-concept {
  background-color: #f1f5f9; /* slate-100 */
  color: #334155; /* slate-700 */
}

.ds-badge--subtle.ds-badge--entity-organization {
  background-color: #e0e7ff; /* indigo-100 */
  color: #3730a3; /* indigo-800: 8.4:1 */
}

.ds-badge--subtle.ds-badge--entity-other {
  background-color: #f1f5f9; /* slate-100 */
  color: #334155; /* slate-700 */
}

/* Icon */
.ds-badge__icon {
  font-size: 0.85em;
}

/* Remove button */
.ds-badge__remove {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  margin-left: var(--ds-space-1);
  background: transparent;
  border: none;
  cursor: pointer;
  opacity: 0.7;
  transition: var(--ds-transition-fast);
}

.ds-badge__remove:hover {
  opacity: 1;
}

.ds-badge__remove i {
  font-size: 0.75em;
}
</style>
