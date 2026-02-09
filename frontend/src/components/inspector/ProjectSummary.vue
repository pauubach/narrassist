<script setup lang="ts">
/**
 * ProjectSummary - Resumen del proyecto para el inspector.
 *
 * Se muestra cuando no hay ningún elemento seleccionado.
 * Proporciona una vista rápida de las estadísticas del proyecto.
 */

defineProps<{
  /** Número total de palabras */
  wordCount: number
  /** Número de capítulos */
  chapterCount: number
  /** Número de entidades */
  entityCount: number
  /** Número de alertas */
  alertCount: number
}>()

const emit = defineEmits<{
  /** Cuando se hace click en una estadística */
  (e: 'stat-click', stat: 'words' | 'chapters' | 'entities' | 'alerts'): void
}>()
</script>

<template>
  <div class="project-summary">
    <!-- Stats en grid 2x2 para aprovechar mejor el espacio -->
    <div class="summary-stats">
      <button
        type="button"
        class="stat-card"
        @click="emit('stat-click', 'words')"
      >
        <i class="pi pi-file-edit stat-icon"></i>
        <div class="stat-content">
          <span class="stat-value">{{ wordCount.toLocaleString() }}</span>
          <span class="stat-label">palabras</span>
        </div>
      </button>

      <button
        type="button"
        class="stat-card"
        @click="emit('stat-click', 'chapters')"
      >
        <i class="pi pi-book stat-icon"></i>
        <div class="stat-content">
          <span class="stat-value">{{ chapterCount }}</span>
          <span class="stat-label">capítulos</span>
        </div>
      </button>

      <button
        type="button"
        class="stat-card"
        @click="emit('stat-click', 'entities')"
      >
        <i class="pi pi-users stat-icon"></i>
        <div class="stat-content">
          <span class="stat-value">{{ entityCount }}</span>
          <span class="stat-label">entidades</span>
        </div>
      </button>

      <button
        type="button"
        class="stat-card"
        :class="{ 'stat-card--alert': alertCount > 0 }"
        @click="emit('stat-click', 'alerts')"
      >
        <i class="pi pi-exclamation-triangle stat-icon"></i>
        <div class="stat-content">
          <span class="stat-value">{{ alertCount }}</span>
          <span class="stat-label">alertas</span>
        </div>
      </button>
    </div>

    <!-- Tip de uso -->
    <div class="summary-tip">
      <i class="pi pi-info-circle"></i>
      <span>Selecciona una entidad o alerta para ver sus detalles aquí</span>
    </div>
  </div>
</template>

<style scoped>
.project-summary {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
  padding: var(--ds-space-4);
  width: 100%;
  min-width: 0;
  overflow: hidden;
}

.summary-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--ds-space-2);
}

.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-3);
  background: var(--ds-surface-ground);
  border: 1px solid var(--ds-surface-border);
  border-radius: var(--ds-radius-lg);
  cursor: pointer;
  transition: all var(--ds-transition-fast);
  text-align: center;
  min-height: 80px;
}

.stat-card:hover {
  background: var(--ds-surface-hover);
  border-color: var(--ds-color-primary-light);
}

.stat-card--alert {
  border-color: var(--ds-color-warning-light);
}

.stat-card--alert:hover {
  border-color: var(--ds-color-warning);
}

.stat-icon {
  font-size: 1.25rem;
  color: var(--ds-color-text-secondary);
}

.stat-card--alert .stat-icon {
  color: var(--ds-color-warning);
}

.stat-content {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: var(--ds-font-size-lg);
  font-weight: var(--ds-font-weight-bold);
  color: var(--ds-color-text);
  line-height: 1.2;
}

.stat-label {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.summary-tip {
  display: flex;
  align-items: flex-start;
  gap: var(--ds-space-2);
  padding: var(--ds-space-3);
  background: var(--ds-surface-section);
  border-radius: var(--ds-radius-md);
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
  line-height: 1.4;
}

.summary-tip i {
  flex-shrink: 0;
  margin-top: 0.125rem;
}
</style>
