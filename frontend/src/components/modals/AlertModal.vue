<script setup lang="ts">
import { computed } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Badge from 'primevue/badge'
import type { Alert, Entity, Chapter } from '@/types'
import { useAlertUtils } from '@/composables/useAlertUtils'
import { useWorkspaceStore } from '@/stores/workspace'
import AlertDiffView from '@/components/alerts/AlertDiffView.vue'

/**
 * AlertModal - Modal de detalle completo de una alerta
 *
 * Muestra toda la información de una alerta incluyendo:
 * - Título y severidad
 * - Descripción detallada
 * - Explicación
 * - Sugerencia de corrección
 * - Entidad y capítulo relacionados
 * - Acciones (resolver, descartar)
 */

const props = defineProps<{
  /** Alerta a mostrar */
  alert: Alert | null
  /** Si el modal está visible */
  visible: boolean
  /** Entidad relacionada (si existe) */
  relatedEntity?: Entity | null
  /** Capítulo relacionado (si existe) */
  relatedChapter?: Chapter | null
}>()

const emit = defineEmits<{
  /** Cuando se cierra el modal */
  (e: 'update:visible', value: boolean): void
  /** Cuando se hace click en la entidad relacionada */
  (e: 'entityClick', entity: Entity): void
  /** Cuando se quiere ir a la ubicación en el texto */
  (e: 'goToLocation'): void
  /** Cuando se resuelve la alerta */
  (e: 'resolve'): void
  /** Cuando se descarta la alerta */
  (e: 'dismiss'): void
}>()

const workspaceStore = useWorkspaceStore()
const { getSeverityColor, getSeverityLabel, getCategoryConfig } = useAlertUtils()

const goToLocation = () => {
  if (!props.alert || props.alert.spanStart === undefined) return
  workspaceStore.navigateToTextPosition(
    props.alert.spanStart,
    props.alert.excerpt || undefined,
    props.relatedChapter?.id ?? null,
  )
  emit('update:visible', false)
}

// Computed
const severityColor = computed(() => (props.alert ? getSeverityColor(props.alert.severity) : '#888'))
const severityLabel = computed(() => (props.alert ? getSeverityLabel(props.alert.severity) : ''))
const categoryConfig = computed(() => (props.alert ? getCategoryConfig(props.alert.category) : null))

const hasExplanation = computed(() => props.alert && props.alert.explanation)
const hasSuggestion = computed(() => props.alert && props.alert.suggestion)
const hasPosition = computed(
  () => props.alert && props.alert.spanStart !== undefined && props.alert.spanEnd !== undefined
)

const isActive = computed(() => props.alert?.status === 'active')

const statusLabel = computed(() => {
  if (!props.alert) return ''
  const labels: Record<string, string> = {
    active: 'Activa',
    resolved: 'Resuelta',
    dismissed: 'Descartada'
  }
  return labels[props.alert.status] || props.alert.status
})

const statusSeverity = computed(() => {
  if (!props.alert) return 'secondary'
  const map: Record<string, 'warn' | 'success' | 'secondary'> = {
    active: 'warn',
    resolved: 'success',
    dismissed: 'secondary'
  }
  return map[props.alert.status] || 'secondary'
})

// Helpers
function close() {
  emit('update:visible', false)
}

function getSeverityBadge(severity: string): 'danger' | 'warn' | 'info' | 'secondary' | undefined {
  const map: Record<string, 'danger' | 'warn' | 'info' | 'secondary'> = {
    critical: 'danger',
    high: 'warn',
    medium: 'warn',
    low: 'info',
    info: 'secondary'
  }
  return map[severity]
}

function formatDate(date: Date): string {
  return date.toLocaleDateString('es-ES', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    :closable="true"
    :draggable="false"
    :style="{ width: '650px', maxWidth: '95vw' }"
    class="alert-modal"
    @update:visible="emit('update:visible', $event)"
  >
    <template #header>
      <div class="modal-header">
        <div class="severity-indicator" :style="{ backgroundColor: severityColor }">
          <i class="pi pi-exclamation-triangle"></i>
        </div>
        <div class="header-content">
          <h2>{{ alert?.title }}</h2>
          <div class="header-badges">
            <Badge :value="severityLabel" :severity="getSeverityBadge(alert?.severity || 'info')" />
            <Badge
              v-if="categoryConfig"
              :value="categoryConfig.label"
              severity="secondary"
            />
            <Badge :value="statusLabel" :severity="statusSeverity" />
          </div>
        </div>
      </div>
    </template>

    <div v-if="alert" class="modal-body">
      <!-- Descripción -->
      <section class="section">
        <h3><i class="pi pi-info-circle"></i> Descripción</h3>
        <p class="description">{{ alert.description }}</p>
      </section>

      <!-- Explicación -->
      <section v-if="hasExplanation" class="section">
        <h3><i class="pi pi-file-edit"></i> Explicación</h3>
        <div class="explanation-box">
          <p>{{ alert.explanation }}</p>
        </div>
      </section>

      <!-- Vista comparativa: cuando hay excerpt Y suggestion -->
      <section v-if="alert.excerpt && alert.suggestion" class="section">
        <h3><i class="pi pi-arrows-h"></i> Original vs Propuesta</h3>
        <AlertDiffView
          :excerpt="alert.excerpt"
          :suggestion="alert.suggestion"
          layout="stacked"
        />
      </section>

      <!-- Solo sugerencia (sin excerpt) -->
      <section v-else-if="hasSuggestion" class="section">
        <h3><i class="pi pi-lightbulb"></i> Sugerencia</h3>
        <div class="suggestion-box">
          <i class="pi pi-check"></i>
          <p>{{ alert.suggestion }}</p>
        </div>
      </section>

      <!-- Contexto -->
      <section class="section context-section">
        <h3><i class="pi pi-link"></i> Contexto</h3>
        <div class="context-grid">
          <!-- Entidad relacionada -->
          <button
            v-if="relatedEntity"
            type="button"
            class="context-card"
            @click="emit('entityClick', relatedEntity)"
          >
            <i class="pi pi-user"></i>
            <div class="context-info">
              <span class="context-label">Entidad</span>
              <span class="context-value">{{ relatedEntity.name }}</span>
            </div>
            <i class="pi pi-chevron-right"></i>
          </button>

          <!-- Capítulo relacionado -->
          <div v-if="relatedChapter" class="context-card static">
            <i class="pi pi-book"></i>
            <div class="context-info">
              <span class="context-label">Capítulo</span>
              <span class="context-value">{{ relatedChapter.title }}</span>
            </div>
          </div>

          <!-- Posición en el texto -->
          <button
            v-if="hasPosition"
            type="button"
            class="context-card"
            @click="goToLocation"
          >
            <i class="pi pi-map-marker"></i>
            <div class="context-info">
              <span class="context-label">Posición</span>
              <span class="context-value">{{ alert.spanStart }} - {{ alert.spanEnd }}</span>
            </div>
            <i class="pi pi-chevron-right"></i>
          </button>
        </div>
      </section>

      <!-- Metadatos -->
      <section class="section metadata-section">
        <div class="metadata-item">
          <span class="meta-label">Confianza:</span>
          <span class="meta-value">{{ Math.round(alert.confidence * 100) }}%</span>
        </div>
        <div class="metadata-item">
          <span class="meta-label">Creada:</span>
          <span class="meta-value">{{ formatDate(alert.createdAt) }}</span>
        </div>
        <div v-if="alert.resolvedAt" class="metadata-item">
          <span class="meta-label">Resuelta:</span>
          <span class="meta-value">{{ formatDate(alert.resolvedAt) }}</span>
        </div>
      </section>
    </div>

    <template #footer>
      <div class="modal-footer">
        <Button
          v-if="hasPosition"
          label="Ir al texto"
          icon="pi pi-map-marker"
          text
          @click="goToLocation"
        />
        <div v-if="isActive" class="action-buttons">
          <Button
            label="Descartar"
            icon="pi pi-times"
            severity="secondary"
            text
            @click="emit('dismiss')"
          />
          <Button
            label="Resolver"
            icon="pi pi-check"
            severity="success"
            @click="emit('resolve')"
          />
        </div>
        <Button v-else label="Cerrar" @click="close" />
      </div>
    </template>
  </Dialog>
</template>

<style scoped>
.modal-header {
  display: flex;
  align-items: flex-start;
  gap: var(--ds-space-4);
}

.severity-indicator {
  width: 48px;
  height: 48px;
  border-radius: var(--ds-radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1.5rem;
  flex-shrink: 0;
}

.header-content {
  flex: 1;
  min-width: 0;
}

.header-content h2 {
  margin: 0 0 var(--ds-space-2) 0;
  font-size: var(--ds-font-size-lg);
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-text);
}

.header-badges {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-2);
}

.modal-body {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-6);
}

.section {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3);
}

.section h3 {
  margin: 0;
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-text-secondary);
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.section h3 i {
  font-size: 0.875rem;
}

.description {
  margin: 0;
  font-size: var(--ds-font-size-base);
  color: var(--ds-color-text);
  line-height: 1.6;
}

.explanation-box {
  padding: var(--ds-space-3);
  background: var(--ds-surface-section);
  border-radius: var(--ds-radius-md);
  border-left: 3px solid var(--ds-color-info);
}

.explanation-box p {
  margin: 0;
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
  line-height: 1.5;
}

.suggestion-box {
  display: flex;
  align-items: flex-start;
  gap: var(--ds-space-3);
  padding: var(--ds-space-3);
  background: var(--ds-surface-section);
  border-radius: var(--ds-radius-md);
  border-left: 3px solid var(--ds-color-success);
}

.suggestion-box i {
  color: var(--ds-color-success);
  font-size: 0.875rem;
  margin-top: 2px;
}

.suggestion-box p {
  margin: 0;
  flex: 1;
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
  line-height: 1.5;
}

.context-grid {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.context-card {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
  padding: var(--ds-space-3);
  background: var(--ds-surface-section);
  border: 1px solid var(--ds-surface-border);
  border-radius: var(--ds-radius-md);
  cursor: pointer;
  transition: all var(--ds-transition-fast);
  text-align: left;
  width: 100%;
}

.context-card:not(.static):hover {
  background: var(--ds-surface-hover);
  border-color: var(--ds-color-primary);
}

.context-card.static {
  cursor: default;
}

.context-card > i:first-child {
  font-size: 1.25rem;
  color: var(--ds-color-text-secondary);
}

.context-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.context-label {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.context-value {
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-medium);
  color: var(--ds-color-text);
}

.context-card > i:last-child {
  font-size: 0.875rem;
  color: var(--ds-color-text-secondary);
}

.metadata-section {
  flex-direction: row;
  flex-wrap: wrap;
  gap: var(--ds-space-4);
  padding-top: var(--ds-space-4);
  border-top: 1px solid var(--ds-surface-border);
}

.metadata-item {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.meta-label {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.meta-value {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text);
}

.modal-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.action-buttons {
  display: flex;
  gap: var(--ds-space-2);
}
</style>
