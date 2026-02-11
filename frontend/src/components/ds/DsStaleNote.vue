<script setup lang="ts">
/**
 * DsStaleNote - Nota discreta inline indicando que los datos pueden estar desactualizados.
 *
 * Se muestra bajo el contenido con estilo neutral (no alarma al usuario).
 */

defineProps<{
  /** Mensaje personalizado */
  message?: string
}>()
</script>

<template>
  <p class="ds-stale-note">
    <i class="pi pi-info-circle" />
    <span>{{ message || 'Algunos datos pueden haber cambiado desde el último análisis.' }}</span>
  </p>
</template>

<style scoped>
.ds-stale-note {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  margin: var(--ds-space-4) 0 0;
  padding: var(--ds-space-2) var(--ds-space-3);
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-muted);
  border-top: 1px solid var(--ds-surface-border, var(--ds-surface-200, #e2e8f0));
}

.ds-stale-note i {
  font-size: 0.75rem;
  opacity: 0.6;
  flex-shrink: 0;
}
</style>
