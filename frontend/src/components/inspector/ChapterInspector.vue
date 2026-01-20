<script setup lang="ts">
import { computed } from 'vue'
import Button from 'primevue/button'
import type { Chapter, Entity, Alert } from '@/types'

/**
 * ChapterInspector - Panel de detalles de capítulo para el inspector.
 *
 * Muestra información del capítulo actualmente visible:
 * - Título y número
 * - Conteo de palabras
 * - Personajes que aparecen
 * - Alertas del capítulo
 */

const props = defineProps<{
  /** Capítulo a mostrar */
  chapter: Chapter
  /** Entidades del proyecto (para mostrar personajes del capítulo) */
  entities?: Entity[]
  /** Alertas del proyecto (para filtrar las del capítulo) */
  alerts?: Alert[]
}>()

const emit = defineEmits<{
  /** Ir al inicio del capítulo */
  (e: 'go-to-start'): void
  /** Ver alertas del capítulo */
  (e: 'view-alerts'): void
  /** Seleccionar un personaje */
  (e: 'select-entity', entity: Entity): void
}>()

/** Alertas de este capítulo */
const chapterAlerts = computed(() => {
  if (!props.alerts) return []
  return props.alerts.filter(a => a.chapter === props.chapter.chapterNumber)
})

/** Contar alertas por severidad */
const alertCounts = computed(() => {
  const counts = { critical: 0, high: 0, medium: 0, low: 0, info: 0 }
  for (const alert of chapterAlerts.value) {
    if (alert.severity in counts) {
      counts[alert.severity as keyof typeof counts]++
    }
  }
  return counts
})

const hasAlerts = computed(() => chapterAlerts.value.length > 0)
</script>

<template>
  <div class="chapter-inspector">
    <!-- Header -->
    <div class="inspector-header">
      <div class="chapter-badge">
        <i class="pi pi-book"></i>
        <span>Capítulo {{ chapter.chapterNumber }}</span>
      </div>
    </div>

    <!-- Contenido -->
    <div class="inspector-body">
      <!-- Título -->
      <div class="chapter-title-section">
        <h3 class="chapter-title">{{ chapter.title || `Capítulo ${chapter.chapterNumber}` }}</h3>
      </div>

      <!-- Estadísticas -->
      <div class="info-section">
        <div class="section-label">Estadísticas</div>
        <div class="stats-grid">
          <div class="stat-item">
            <i class="pi pi-align-left"></i>
            <span class="stat-value">{{ (chapter.wordCount || 0).toLocaleString() }}</span>
            <span class="stat-label">palabras</span>
          </div>
          <!-- paragraphCount no está en el tipo Chapter, quitar esta sección -->
        </div>
      </div>

      <!-- Alertas del capítulo -->
      <div v-if="hasAlerts" class="info-section">
        <div class="section-label">
          <i class="pi pi-exclamation-triangle"></i>
          Alertas en este capítulo
        </div>
        <div class="alerts-summary">
          <div v-if="alertCounts.critical > 0" class="alert-count alert-critical">
            <span class="count">{{ alertCounts.critical }}</span>
            <span class="label">críticas</span>
          </div>
          <div v-if="alertCounts.high > 0" class="alert-count alert-high">
            <span class="count">{{ alertCounts.high }}</span>
            <span class="label">altas</span>
          </div>
          <div v-if="alertCounts.medium > 0" class="alert-count alert-medium">
            <span class="count">{{ alertCounts.medium }}</span>
            <span class="label">medias</span>
          </div>
          <div v-if="alertCounts.low > 0" class="alert-count alert-low">
            <span class="count">{{ alertCounts.low }}</span>
            <span class="label">bajas</span>
          </div>
          <div v-if="alertCounts.info > 0" class="alert-count alert-info">
            <span class="count">{{ alertCounts.info }}</span>
            <span class="label">info</span>
          </div>
        </div>
      </div>

      <!-- Sin alertas -->
      <div v-else class="info-section no-alerts">
        <i class="pi pi-check-circle"></i>
        <span>Sin alertas en este capítulo</span>
      </div>
    </div>

    <!-- Acciones -->
    <div class="inspector-actions">
      <Button
        label="Ir al inicio"
        icon="pi pi-arrow-up"
        size="small"
        outlined
        @click="emit('go-to-start')"
      />
      <Button
        v-if="hasAlerts"
        label="Ver alertas"
        icon="pi pi-list"
        size="small"
        @click="emit('view-alerts')"
      />
    </div>
  </div>
</template>

<style scoped>
.chapter-inspector {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.inspector-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
  padding: var(--ds-space-4);
  border-bottom: 1px solid var(--ds-surface-border);
}

.chapter-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-1) var(--ds-space-3);
  background: var(--ds-color-primary-soft);
  color: var(--ds-color-primary);
  border-radius: var(--ds-radius-full);
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-medium);
}

.chapter-badge i {
  font-size: 0.875rem;
}

.inspector-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--ds-space-4);
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
}

.chapter-title-section {
  padding-bottom: var(--ds-space-2);
  border-bottom: 1px solid var(--ds-surface-border);
}

.chapter-title {
  margin: 0;
  font-size: var(--ds-font-size-lg);
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-text);
  line-height: 1.4;
}

.info-section {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.section-label {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: var(--ds-font-size-xs);
  font-weight: var(--ds-font-weight-medium);
  color: var(--ds-color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.section-label i {
  font-size: 0.875rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--ds-space-2);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--ds-space-3);
  background: var(--ds-surface-ground);
  border-radius: var(--ds-radius-md);
  text-align: center;
}

.stat-item i {
  font-size: 1rem;
  color: var(--ds-color-text-secondary);
  margin-bottom: var(--ds-space-1);
}

.stat-item .stat-value {
  font-size: var(--ds-font-size-lg);
  font-weight: var(--ds-font-weight-bold);
  color: var(--ds-color-text);
}

.stat-item .stat-label {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.alerts-summary {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-2);
}

.alert-count {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
  padding: var(--ds-space-1) var(--ds-space-2);
  border-radius: var(--ds-radius-sm);
  font-size: var(--ds-font-size-sm);
}

.alert-count .count {
  font-weight: var(--ds-font-weight-bold);
}

.alert-count .label {
  font-size: var(--ds-font-size-xs);
}

.alert-critical {
  background: var(--ds-color-error-soft);
  color: var(--ds-color-error);
}

.alert-high {
  background: var(--ds-color-warning-soft);
  color: var(--ds-color-warning);
}

.alert-medium {
  background: var(--ds-alert-medium-bg, #fff3e0);
  color: var(--ds-alert-medium, #e65100);
}

.alert-low {
  background: var(--ds-color-info-soft);
  color: var(--ds-color-info);
}

.alert-info {
  background: var(--ds-surface-hover);
  color: var(--ds-color-text-secondary);
}

.no-alerts {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-3);
  background: var(--ds-color-success-soft);
  border-radius: var(--ds-radius-md);
  color: var(--ds-color-success);
}

.no-alerts i {
  font-size: 1.25rem;
}

.inspector-actions {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
  padding: var(--ds-space-4);
  border-top: 1px solid var(--ds-surface-border);
}
</style>
