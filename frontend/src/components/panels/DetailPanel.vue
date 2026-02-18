<script setup lang="ts">
import { computed } from 'vue'
import { useSelectionStore } from '@/stores/selection'
import { useWorkspaceStore } from '@/stores/workspace'
import { useEntityUtils } from '@/composables/useEntityUtils'
import { useAlertUtils } from '@/composables/useAlertUtils'
import DsBadge from '@/components/ds/DsBadge.vue'
import DsCard from '@/components/ds/DsCard.vue'
import DsEmptyState from '@/components/ds/DsEmptyState.vue'
import type { Entity, EntityAttribute, Alert } from '@/types'

/**
 * DetailPanel - Panel derecho que muestra detalles del elemento seleccionado.
 *
 * Muestra ficha de entidad o detalle de alerta según la selección.
 */

const props = defineProps<{
  /** Atributos de la entidad seleccionada */
  entityAttributes?: EntityAttribute[]
  /** Si está cargando detalles */
  loading?: boolean
}>()

const emit = defineEmits<{
  'navigate-to-mention': [entityId: number, chapterId: number]
  'navigate-to-alert': [alert: Alert]
  'edit-entity': [entity: Entity]
  'resolve-alert': [alert: Alert]
  'dismiss-alert': [alert: Alert]
}>()

const selectionStore = useSelectionStore()
const workspaceStore = useWorkspaceStore()
const { getTypeConfig, getImportanceConfig } = useEntityUtils()
const { getSeverityConfig, getCategoryConfig, formatAlertLocation } = useAlertUtils()

// Elemento seleccionado
const selectedEntity = computed<Entity | null>(() => {
  if (selectionStore.primary?.type === 'entity') {
    return selectionStore.primary.data as Entity
  }
  return null
})

const selectedAlert = computed<Alert | null>(() => {
  if (selectionStore.primary?.type === 'alert') {
    return selectionStore.primary.data as Alert
  }
  return null
})

// Sinónimos del thesaurus (para alertas de repetición)
const alertSynonyms = computed<string[]>(() => {
  const syns = selectedAlert.value?.extraData?.synonyms
  return Array.isArray(syns) ? syns : []
})

// Atributos agrupados por categoría
const groupedAttributes = computed(() => {
  if (!props.entityAttributes) return new Map()

  const groups = new Map<string, EntityAttribute[]>()
  for (const attr of props.entityAttributes) {
    const existing = groups.get(attr.category) || []
    existing.push(attr)
    groups.set(attr.category, existing)
  }
  return groups
})

function handleEditEntity() {
  if (selectedEntity.value) {
    emit('edit-entity', selectedEntity.value)
  }
}

function handleNavigateToMention() {
  if (!selectedEntity.value?.firstMentionChapter) return
  // Usar el nombre de la entidad como texto a buscar en el capítulo
  workspaceStore.navigateToTextPosition(
    0, // Posición no conocida, el texto guiará la búsqueda
    selectedEntity.value.name,
    null, // No tenemos chapter ID, solo number — TextTab buscará por posición
  )
}

function handleNavigateToAlert() {
  if (selectedAlert.value) {
    emit('navigate-to-alert', selectedAlert.value)
  }
}

function handleResolveAlert() {
  if (selectedAlert.value) {
    emit('resolve-alert', selectedAlert.value)
  }
}

function handleDismissAlert() {
  if (selectedAlert.value) {
    emit('dismiss-alert', selectedAlert.value)
  }
}

// Get alert message
function getAlertMessage(alert: Alert): string {
  return alert.description || alert.title || ''
}
</script>

<template>
  <div class="detail-panel">
    <!-- Empty state -->
    <DsEmptyState
      v-if="!selectedEntity && !selectedAlert"
      icon="pi pi-info-circle"
      title="Selecciona un elemento"
      description="Haz clic en una entidad o alerta para ver sus detalles"
      size="sm"
    />

    <!-- Entity Detail -->
    <div v-else-if="selectedEntity" class="detail-panel__entity">
      <!-- Header -->
      <div class="detail-panel__header">
        <div class="detail-panel__entity-icon">
          <i :class="getTypeConfig(selectedEntity.type).icon" />
        </div>
        <div class="detail-panel__entity-info">
          <h2 class="detail-panel__title">{{ selectedEntity.name }}</h2>
          <div class="detail-panel__meta">
            <DsBadge :entity-type="selectedEntity.type" variant="subtle" size="sm">
              {{ getTypeConfig(selectedEntity.type).label }}
            </DsBadge>
            <DsBadge
              :color="getImportanceConfig(selectedEntity.importance).weight === 3 ? 'primary' : 'secondary'"
              variant="outline"
              size="sm"
            >
              {{ getImportanceConfig(selectedEntity.importance).label }}
            </DsBadge>
          </div>
        </div>
        <button type="button" class="detail-panel__edit-btn" title="Editar entidad" @click="handleEditEntity">
          <i class="pi pi-pencil" />
        </button>
      </div>

      <!-- Aliases -->
      <section v-if="selectedEntity.aliases?.length" class="detail-panel__section">
        <h3 class="detail-panel__section-title">También conocido como</h3>
        <div class="detail-panel__aliases">
          <DsBadge
            v-for="(alias, index) in selectedEntity.aliases"
            :key="index"
            variant="outline"
            color="secondary"
            size="sm"
          >
            {{ alias }}
          </DsBadge>
        </div>
      </section>

      <!-- Stats -->
      <section class="detail-panel__section">
        <h3 class="detail-panel__section-title">Estadísticas</h3>
        <div class="detail-panel__stats">
          <div class="detail-panel__stat">
            <span class="detail-panel__stat-value">{{ selectedEntity.mentionCount }}</span>
            <span class="detail-panel__stat-label">Apariciones</span>
          </div>
          <div v-if="selectedEntity.firstMentionChapter" class="detail-panel__stat">
            <span class="detail-panel__stat-value">Cap. {{ selectedEntity.firstMentionChapter }}</span>
            <span class="detail-panel__stat-label">Primera aparición</span>
          </div>
        </div>
      </section>

      <!-- Attributes -->
      <section v-if="groupedAttributes.size > 0" class="detail-panel__section">
        <h3 class="detail-panel__section-title">Atributos</h3>
        <div class="detail-panel__attributes">
          <div v-for="[category, attrs] in groupedAttributes" :key="category" class="detail-panel__attr-group">
            <h4 class="detail-panel__attr-category">{{ category }}</h4>
            <div v-for="attr in attrs" :key="attr.id" class="detail-panel__attr">
              <span class="detail-panel__attr-name">{{ attr.name }}</span>
              <span class="detail-panel__attr-value">{{ attr.value }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Actions -->
      <div class="detail-panel__actions">
        <button
          v-if="selectedEntity.firstMentionChapter"
          type="button"
          class="detail-panel__action-btn"
          @click="handleNavigateToMention"
        >
          <i class="pi pi-arrow-right" />
          Ir a primera aparición
        </button>
      </div>
    </div>

    <!-- Alert Detail -->
    <div v-else-if="selectedAlert" class="detail-panel__alert">
      <!-- Header -->
      <div class="detail-panel__header">
        <DsBadge :severity="selectedAlert.severity" size="md">
          {{ getSeverityConfig(selectedAlert.severity).label }}
        </DsBadge>
        <DsBadge variant="outline" color="secondary" size="sm">
          {{ getCategoryConfig(selectedAlert.category).label }}
        </DsBadge>
      </div>

      <!-- Message -->
      <section class="detail-panel__section">
        <h3 class="detail-panel__section-title">Descripción</h3>
        <p class="detail-panel__message">{{ getAlertMessage(selectedAlert) }}</p>
      </section>

      <!-- Suggestion -->
      <section v-if="selectedAlert.suggestion" class="detail-panel__section">
        <h3 class="detail-panel__section-title">Sugerencia</h3>
        <DsCard variant="outlined" padding="sm">
          <p class="detail-panel__suggestion">{{ selectedAlert.suggestion }}</p>
          <!-- Synonym chips (thesaurus) -->
          <div v-if="alertSynonyms.length" class="detail-panel__synonyms">
            <span class="detail-panel__synonyms-label">Alternativas:</span>
            <span
              v-for="syn in alertSynonyms"
              :key="syn"
              class="detail-panel__synonym-chip"
            >{{ syn }}</span>
          </div>
        </DsCard>
      </section>

      <!-- Location -->
      <section class="detail-panel__section">
        <h3 class="detail-panel__section-title">Ubicación</h3>
        <p class="detail-panel__location">
          <i class="pi pi-map-marker" />
          {{ formatAlertLocation(selectedAlert) }}
        </p>
      </section>

      <!-- Actions -->
      <div v-if="selectedAlert.status === 'active'" class="detail-panel__actions">
        <button
          type="button"
          class="detail-panel__action-btn detail-panel__action-btn--primary"
          @click="handleNavigateToAlert"
        >
          <i class="pi pi-arrow-right" />
          Ver en texto
        </button>
        <button
          type="button"
          class="detail-panel__action-btn detail-panel__action-btn--success"
          @click="handleResolveAlert"
        >
          <i class="pi pi-check" />
          Marcar resuelta
        </button>
        <button type="button" class="detail-panel__action-btn" @click="handleDismissAlert">
          <i class="pi pi-times" />
          Descartar
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.detail-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: var(--ds-space-4);
}

.detail-panel__entity,
.detail-panel__alert {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
}

/* Header */
.detail-panel__header {
  display: flex;
  align-items: flex-start;
  gap: var(--ds-space-3);
}

.detail-panel__entity-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  background-color: var(--ds-surface-hover);
  border-radius: var(--ds-radius-lg);
  font-size: 1.5rem;
  color: var(--ds-color-primary);
}

.detail-panel__entity-info {
  flex: 1;
}

.detail-panel__title {
  margin: 0 0 var(--ds-space-2);
  font-size: var(--ds-font-size-lg);
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-text);
}

.detail-panel__meta {
  display: flex;
  gap: var(--ds-space-2);
}

.detail-panel__edit-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  color: var(--ds-color-text-muted);
  background: transparent;
  border: 1px solid var(--ds-surface-border);
  border-radius: var(--ds-radius-md);
  cursor: pointer;
  transition: var(--ds-transition-fast);
}

.detail-panel__edit-btn:hover {
  color: var(--ds-color-primary);
  border-color: var(--ds-color-primary);
}

/* Sections */
.detail-panel__section {
  padding-top: var(--ds-space-3);
  border-top: 1px solid var(--ds-surface-border);
}

.detail-panel__section-title {
  margin: 0 0 var(--ds-space-2);
  font-size: var(--ds-font-size-xs);
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Aliases */
.detail-panel__aliases {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-2);
}

/* Stats */
.detail-panel__stats {
  display: flex;
  gap: var(--ds-space-6);
}

.detail-panel__stat {
  display: flex;
  flex-direction: column;
}

.detail-panel__stat-value {
  font-size: var(--ds-font-size-xl);
  font-weight: var(--ds-font-weight-bold);
  color: var(--ds-color-text);
}

.detail-panel__stat-label {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-muted);
}

/* Attributes */
.detail-panel__attributes {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3);
}

.detail-panel__attr-group {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-1);
}

.detail-panel__attr-category {
  margin: 0;
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-medium);
  color: var(--ds-color-text-secondary);
}

.detail-panel__attr {
  display: flex;
  justify-content: space-between;
  padding: var(--ds-space-1) 0;
  font-size: var(--ds-font-size-sm);
}

.detail-panel__attr-name {
  color: var(--ds-color-text-muted);
}

.detail-panel__attr-value {
  color: var(--ds-color-text);
  font-weight: var(--ds-font-weight-medium);
}

/* Alert specific */
.detail-panel__message,
.detail-panel__suggestion {
  margin: 0;
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
  line-height: var(--ds-line-height-relaxed);
}

.detail-panel__synonyms {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--ds-space-1);
  margin-top: var(--ds-space-2);
}

.detail-panel__synonyms-label {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-muted);
  font-weight: var(--ds-font-weight-medium);
}

.detail-panel__synonym-chip {
  display: inline-block;
  padding: 2px 8px;
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-info);
  background-color: color-mix(in srgb, var(--ds-color-info) 12%, transparent);
  border-radius: var(--ds-radius-full, 9999px);
}

.detail-panel__location {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  margin: 0;
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

/* Actions */
.detail-panel__actions {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
  margin-top: auto;
  padding-top: var(--ds-space-4);
}

.detail-panel__action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2) var(--ds-space-4);
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-medium);
  color: var(--ds-color-text-secondary);
  background: transparent;
  border: 1px solid var(--ds-surface-border);
  border-radius: var(--ds-radius-md);
  cursor: pointer;
  transition: var(--ds-transition-fast);
}

.detail-panel__action-btn:hover {
  background-color: var(--ds-surface-hover);
  color: var(--ds-color-text);
}

.detail-panel__action-btn--primary {
  color: white;
  background-color: var(--ds-color-primary);
  border-color: var(--ds-color-primary);
}

.detail-panel__action-btn--primary:hover {
  background-color: var(--ds-color-primary-dark);
}

.detail-panel__action-btn--success {
  color: var(--ds-color-success);
  border-color: var(--ds-color-success);
}

.detail-panel__action-btn--success:hover {
  background-color: var(--ds-color-success);
  color: white;
}
</style>
