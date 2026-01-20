<script setup lang="ts">
import { computed } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Badge from 'primevue/badge'
import type { Entity, Alert } from '@/types'
import { useEntityUtils } from '@/composables/useEntityUtils'

/**
 * EntityModal - Modal de detalle completo de una entidad
 *
 * Muestra toda la información de una entidad incluyendo:
 * - Nombre y tipo
 * - Aliases
 * - Importancia y descripción
 * - Estadísticas de menciones
 * - Alertas relacionadas
 */

const props = defineProps<{
  /** Entidad a mostrar */
  entity: Entity | null
  /** Si el modal está visible */
  visible: boolean
  /** Alertas relacionadas con esta entidad */
  relatedAlerts?: Alert[]
}>()

const emit = defineEmits<{
  /** Cuando se cierra el modal */
  (e: 'update:visible', value: boolean): void
  /** Cuando se hace click en una alerta */
  (e: 'alertClick', alert: Alert): void
  /** Cuando se quiere ir a las menciones */
  (e: 'goToMentions'): void
  /** Cuando se quiere editar la entidad */
  (e: 'edit'): void
}>()

const { getEntityIcon, getEntityLabel, getEntityColor } = useEntityUtils()

// Computed
const entityIcon = computed(() => (props.entity ? getEntityIcon(props.entity.type) : 'pi-circle'))
const entityLabel = computed(() => (props.entity ? getEntityLabel(props.entity.type) : ''))
const entityColor = computed(() => (props.entity ? getEntityColor(props.entity.type) : '#888'))

const hasAliases = computed(() => props.entity && props.entity.aliases && props.entity.aliases.length > 0)

const importanceLabel = computed(() => {
  if (!props.entity) return ''
  const labels: Record<string, string> = {
    main: 'Principal',
    secondary: 'Secundario',
    minor: 'Menor'
  }
  return labels[props.entity.importance] || props.entity.importance
})

const importanceSeverity = computed(() => {
  if (!props.entity) return 'secondary'
  const map: Record<string, 'success' | 'info' | 'secondary'> = {
    main: 'success',
    secondary: 'info',
    minor: 'secondary'
  }
  return map[props.entity.importance] || 'secondary'
})

// Helpers
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

function close() {
  emit('update:visible', false)
}
</script>

<template>
  <Dialog
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    modal
    :closable="true"
    :draggable="false"
    :style="{ width: '600px', maxWidth: '95vw' }"
    class="entity-modal"
  >
    <template #header>
      <div class="modal-header">
        <div class="entity-icon" :style="{ backgroundColor: entityColor }">
          <i :class="['pi', entityIcon]"></i>
        </div>
        <div class="header-content">
          <h2>{{ entity?.name }}</h2>
          <span class="entity-type">{{ entityLabel }}</span>
        </div>
        <Badge :value="importanceLabel" :severity="importanceSeverity" />
      </div>
    </template>

    <div v-if="entity" class="modal-body">
      <!-- Descripción -->
      <section v-if="entity.description" class="section">
        <h3><i class="pi pi-info-circle"></i> Descripción</h3>
        <p class="description">{{ entity.description }}</p>
      </section>

      <!-- Aliases -->
      <section v-if="hasAliases" class="section">
        <h3><i class="pi pi-tags"></i> Aliases</h3>
        <div class="aliases-list">
          <span v-for="alias in entity.aliases" :key="alias" class="alias-tag">
            {{ alias }}
          </span>
        </div>
      </section>

      <!-- Estadísticas -->
      <section class="section">
        <h3><i class="pi pi-chart-bar"></i> Estadísticas</h3>
        <div class="stats-grid">
          <div class="stat-card">
            <span class="stat-value">{{ entity.mentionCount.toLocaleString() }}</span>
            <span class="stat-label">Apariciones</span>
          </div>
          <div v-if="entity.firstMentionChapter" class="stat-card">
            <span class="stat-value">Cap. {{ entity.firstMentionChapter }}</span>
            <span class="stat-label">Primera aparición</span>
          </div>
          <div v-if="relatedAlerts && relatedAlerts.length > 0" class="stat-card stat-alerts">
            <span class="stat-value">{{ relatedAlerts.length }}</span>
            <span class="stat-label">Alertas</span>
          </div>
        </div>
      </section>

      <!-- Alertas relacionadas -->
      <section v-if="relatedAlerts && relatedAlerts.length > 0" class="section">
        <h3><i class="pi pi-exclamation-triangle"></i> Alertas relacionadas</h3>
        <div class="alerts-list">
          <button
            v-for="alert in relatedAlerts.slice(0, 5)"
            :key="alert.id"
            type="button"
            class="alert-item"
            @click="emit('alertClick', alert)"
          >
            <Badge :value="alert.severity" :severity="getSeverityBadge(alert.severity)" />
            <span class="alert-title">{{ alert.title }}</span>
          </button>
          <span v-if="relatedAlerts.length > 5" class="more-alerts">
            +{{ relatedAlerts.length - 5 }} alertas más
          </span>
        </div>
      </section>
    </div>

    <template #footer>
      <div class="modal-footer">
        <Button
          label="Ver en texto"
          icon="pi pi-search"
          text
          @click="emit('goToMentions')"
        />
        <Button
          label="Editar"
          icon="pi pi-pencil"
          text
          @click="emit('edit')"
        />
        <Button label="Cerrar" @click="close" />
      </div>
    </template>
  </Dialog>
</template>

<style scoped>
.modal-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-4);
}

.entity-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--ds-radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1.5rem;
}

.header-content {
  flex: 1;
}

.header-content h2 {
  margin: 0;
  font-size: var(--ds-font-size-xl);
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-text);
}

.entity-type {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
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

.aliases-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-2);
}

.alias-tag {
  background: var(--ds-surface-hover);
  padding: var(--ds-space-1) var(--ds-space-3);
  border-radius: var(--ds-radius-full);
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  gap: var(--ds-space-3);
}

.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--ds-space-4);
  background: var(--ds-surface-section);
  border-radius: var(--ds-radius-md);
}

.stat-value {
  font-size: var(--ds-font-size-2xl);
  font-weight: var(--ds-font-weight-bold);
  color: var(--ds-color-primary);
}

.stat-label {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.stat-alerts .stat-value {
  color: var(--ds-color-warning);
}

.alerts-list {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.alert-item {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
  padding: var(--ds-space-2) var(--ds-space-3);
  background: transparent;
  border: 1px solid var(--ds-surface-border);
  border-radius: var(--ds-radius-md);
  cursor: pointer;
  transition: background-color var(--ds-transition-fast);
  text-align: left;
}

.alert-item:hover {
  background: var(--ds-surface-hover);
}

.alert-title {
  flex: 1;
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
}

.more-alerts {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  text-align: center;
  padding: var(--ds-space-2);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--ds-space-2);
}
</style>
