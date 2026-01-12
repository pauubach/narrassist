<template>
  <Dialog
    :visible="visible"
    modal
    header="Fusionar Entidades"
    :style="{ width: '700px' }"
    @update:visible="$emit('update:visible', $event)"
  >
    <div class="merge-dialog">
      <!-- Explicación -->
      <Message severity="info" :closable="false">
        <p>
          Fusiona múltiples entidades en una sola. Todas las menciones, aliases y atributos
          serán transferidos a la entidad principal seleccionada.
        </p>
      </Message>

      <!-- Paso 1: Selección de entidades -->
      <div v-if="step === 1" class="step-content">
        <h3>Paso 1: Selecciona las entidades a fusionar</h3>

        <!-- Búsqueda de entidades -->
        <span class="p-input-icon-left search-wrapper">
          <i class="pi pi-search" />
          <InputText
            v-model="searchQuery"
            placeholder="Buscar entidades..."
            class="w-full"
          />
        </span>

        <!-- Lista de entidades disponibles -->
        <div class="entities-selection">
          <div
            v-for="entity in filteredAvailableEntities"
            :key="entity.id"
            class="entity-item"
            :class="{ 'selected': isSelected(entity.id) }"
            @click="toggleEntity(entity)"
          >
            <Checkbox :modelValue="isSelected(entity.id)" :binary="true" />
            <div class="entity-icon-wrapper">
              <i :class="getEntityIcon(entity.entity_type)"></i>
            </div>
            <div class="entity-info">
              <span class="entity-name">{{ entity.canonical_name }}</span>
              <span class="entity-type">{{ getTypeLabel(entity.entity_type) }}</span>
            </div>
            <div class="entity-stats">
              <span class="stat">{{ entity.mention_count || 0 }} menciones</span>
            </div>
          </div>

          <div v-if="filteredAvailableEntities.length === 0" class="empty-state">
            <p>No se encontraron entidades</p>
          </div>
        </div>

        <!-- Entidades seleccionadas -->
        <div v-if="selectedEntities.length > 0" class="selected-summary">
          <strong>{{ selectedEntities.length }} entidades seleccionadas</strong>
          <div class="selected-chips">
            <Chip
              v-for="entity in selectedEntities"
              :key="entity.id"
              :label="entity.canonical_name"
              removable
              @remove="removeEntity(entity.id)"
            />
          </div>
        </div>
      </div>

      <!-- Paso 2: Seleccionar entidad principal -->
      <div v-if="step === 2" class="step-content">
        <h3>Paso 2: Selecciona la entidad principal</h3>
        <p class="step-description">
          Esta será la entidad resultante. Sus datos se conservarán y se combinarán con los datos
          de las demás entidades.
        </p>

        <div class="entities-selection">
          <div
            v-for="entity in selectedEntities"
            :key="entity.id"
            class="entity-item entity-clickable"
            :class="{ 'primary': primaryEntityId === entity.id }"
            @click="primaryEntityId = entity.id"
          >
            <RadioButton
              v-model="primaryEntityId"
              :value="entity.id"
              name="primaryEntity"
            />
            <div class="entity-icon-wrapper">
              <i :class="getEntityIcon(entity.entity_type)"></i>
            </div>
            <div class="entity-info">
              <span class="entity-name">{{ entity.canonical_name }}</span>
              <div class="entity-details">
                <span class="detail-item">
                  <i class="pi pi-hashtag"></i>
                  {{ entity.mention_count || 0 }} menciones
                </span>
                <span v-if="entity.aliases?.length" class="detail-item">
                  <i class="pi pi-tag"></i>
                  {{ entity.aliases.length }} alias(es)
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Paso 3: Confirmación -->
      <div v-if="step === 3" class="step-content">
        <h3>Paso 3: Revisa y confirma</h3>

        <div class="merge-preview">
          <!-- Entidad resultante -->
          <div class="result-entity">
            <h4>Entidad resultante:</h4>
            <div class="entity-card primary-card">
              <div class="entity-icon-wrapper large">
                <i :class="getEntityIcon(primaryEntity?.entity_type || '')"></i>
              </div>
              <div class="entity-info">
                <span class="entity-name large">{{ primaryEntity?.canonical_name }}</span>
                <Tag :severity="getTypeSeverity(primaryEntity?.entity_type || '')">
                  {{ getTypeLabel(primaryEntity?.entity_type || '') }}
                </Tag>
              </div>
            </div>
          </div>

          <Divider />

          <!-- Entidades a absorber -->
          <div class="merge-entities">
            <h4>Se fusionarán estas entidades:</h4>
            <div class="entities-to-merge">
              <div
                v-for="entity in entitiesToMerge"
                :key="entity.id"
                class="entity-card secondary-card"
              >
                <i class="pi pi-arrow-right merge-arrow"></i>
                <span class="entity-name">{{ entity.canonical_name }}</span>
                <span class="entity-stats">
                  {{ entity.mention_count || 0 }} menciones
                </span>
              </div>
            </div>
          </div>

          <Divider />

          <!-- Resumen de cambios -->
          <div class="merge-summary">
            <h4>Resumen de cambios:</h4>
            <div class="summary-items">
              <div class="summary-item">
                <i class="pi pi-hashtag"></i>
                <span>Total de menciones: <strong>{{ totalMentions }}</strong></span>
              </div>
              <div class="summary-item">
                <i class="pi pi-tag"></i>
                <span>Aliases a combinar: <strong>{{ totalAliases }}</strong></span>
              </div>
              <div class="summary-item">
                <i class="pi pi-trash"></i>
                <span>Entidades a eliminar: <strong>{{ selectedEntities.length - 1 }}</strong></span>
              </div>
            </div>
          </div>

          <!-- Advertencia -->
          <Message severity="warn" :closable="false">
            <strong>Advertencia:</strong> Esta acción no se puede deshacer. Las entidades fusionadas
            serán eliminadas permanentemente.
          </Message>
        </div>
      </div>

      <!-- Indicador de progreso -->
      <div class="steps-indicator">
        <div
          v-for="i in 3"
          :key="i"
          class="step-dot"
          :class="{ 'active': step === i, 'completed': step > i }"
        >
          {{ i }}
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <div class="footer-left">
          <Button
            v-if="step > 1"
            label="Anterior"
            icon="pi pi-arrow-left"
            text
            @click="previousStep"
          />
        </div>
        <div class="footer-right">
          <Button
            label="Cancelar"
            icon="pi pi-times"
            text
            @click="cancel"
          />
          <Button
            v-if="step < 3"
            label="Siguiente"
            icon="pi pi-arrow-right"
            iconPos="right"
            @click="nextStep"
            :disabled="!canProceed"
          />
          <Button
            v-else
            label="Fusionar"
            icon="pi pi-check"
            severity="danger"
            @click="confirmMerge"
            :loading="merging"
          />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Checkbox from 'primevue/checkbox'
import RadioButton from 'primevue/radiobutton'
import Chip from 'primevue/chip'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import Divider from 'primevue/divider'

interface Entity {
  id: number
  project_id: number
  canonical_name: string
  entity_type: string
  aliases?: string[]
  importance: string
  mention_count?: number
  first_mention_chapter?: number
}

const props = defineProps<{
  visible: boolean
  projectId: number
  availableEntities: Entity[]
  preselectedEntities?: Entity[]
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'merge': [primaryId: number, entityIds: number[]]
  'cancel': []
}>()

// Estado
const step = ref(1)
const searchQuery = ref('')
const selectedEntityIds = ref<Set<number>>(new Set())
const primaryEntityId = ref<number | null>(null)
const merging = ref(false)

// Inicializar con entidades preseleccionadas
watch(() => props.preselectedEntities, (entities) => {
  if (entities && entities.length > 0) {
    selectedEntityIds.value = new Set(entities.map(e => e.id))
  }
}, { immediate: true })

// Computed
const filteredAvailableEntities = computed(() => {
  let filtered = props.availableEntities

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(e =>
      e.canonical_name.toLowerCase().includes(query) ||
      e.aliases?.some(a => a.toLowerCase().includes(query))
    )
  }

  return filtered
})

const selectedEntities = computed(() => {
  return props.availableEntities.filter(e => selectedEntityIds.value.has(e.id))
})

const primaryEntity = computed(() => {
  return selectedEntities.value.find(e => e.id === primaryEntityId.value)
})

const entitiesToMerge = computed(() => {
  return selectedEntities.value.filter(e => e.id !== primaryEntityId.value)
})

const totalMentions = computed(() => {
  return selectedEntities.value.reduce((sum, e) => sum + (e.mention_count || 0), 0)
})

const totalAliases = computed(() => {
  return selectedEntities.value.reduce((sum, e) => sum + (e.aliases?.length || 0), 0)
})

const canProceed = computed(() => {
  if (step.value === 1) {
    return selectedEntities.value.length >= 2
  }
  if (step.value === 2) {
    return primaryEntityId.value !== null
  }
  return true
})

// Funciones
const isSelected = (id: number): boolean => {
  return selectedEntityIds.value.has(id)
}

const toggleEntity = (entity: Entity) => {
  if (selectedEntityIds.value.has(entity.id)) {
    selectedEntityIds.value.delete(entity.id)
  } else {
    selectedEntityIds.value.add(entity.id)
  }
}

const removeEntity = (id: number) => {
  selectedEntityIds.value.delete(id)
}

const nextStep = () => {
  if (!canProceed.value) return

  step.value++

  // Al pasar al paso 2, preseleccionar la entidad con más menciones
  if (step.value === 2 && !primaryEntityId.value) {
    const mostMentioned = [...selectedEntities.value].sort(
      (a, b) => (b.mention_count || 0) - (a.mention_count || 0)
    )[0]
    if (mostMentioned) {
      primaryEntityId.value = mostMentioned.id
    }
  }
}

const previousStep = () => {
  step.value--
}

const confirmMerge = async () => {
  if (!primaryEntityId.value) return

  merging.value = true

  try {
    // Emitir evento con la entidad principal y las IDs a fusionar
    const idsToMerge = Array.from(selectedEntityIds.value).filter(
      id => id !== primaryEntityId.value
    )

    emit('merge', primaryEntityId.value, idsToMerge)
  } finally {
    merging.value = false
  }
}

const cancel = () => {
  emit('cancel')
  emit('update:visible', false)
  resetDialog()
}

const resetDialog = () => {
  step.value = 1
  searchQuery.value = ''
  selectedEntityIds.value = new Set()
  primaryEntityId.value = null
}

// Helpers
const getEntityIcon = (type: string): string => {
  const icons: Record<string, string> = {
    'CHARACTER': 'pi pi-user',
    'LOCATION': 'pi pi-map-marker',
    'ORGANIZATION': 'pi pi-building',
    'OBJECT': 'pi pi-box',
    'EVENT': 'pi pi-calendar'
  }
  return icons[type] || 'pi pi-tag'
}

const getTypeLabel = (type: string): string => {
  const labels: Record<string, string> = {
    'CHARACTER': 'Personaje',
    'LOCATION': 'Lugar',
    'ORGANIZATION': 'Organización',
    'OBJECT': 'Objeto',
    'EVENT': 'Evento'
  }
  return labels[type] || type
}

const getTypeSeverity = (type: string): string => {
  const severities: Record<string, string> = {
    'CHARACTER': 'success',
    'LOCATION': 'danger',
    'ORGANIZATION': 'info',
    'OBJECT': 'warning',
    'EVENT': 'secondary'
  }
  return severities[type] || 'secondary'
}

// Watch para resetear al cerrar
watch(() => props.visible, (isVisible) => {
  if (!isVisible) {
    resetDialog()
  }
})
</script>

<style scoped>
.merge-dialog {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 0.5rem 0;
}

.step-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-height: 400px;
}

.step-content h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-color);
}

.step-description {
  margin: 0;
  color: var(--text-color-secondary);
  font-size: 0.875rem;
}

.search-wrapper {
  width: 100%;
}

.entities-selection {
  flex: 1;
  overflow-y: auto;
  max-height: 300px;
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  padding: 0.5rem;
}

.entity-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border-radius: 6px;
  margin-bottom: 0.5rem;
  border: 1px solid transparent;
  transition: all 0.2s;
  cursor: pointer;
}

.entity-item:hover {
  background: var(--surface-50);
  border-color: var(--surface-200);
}

.entity-item.selected {
  background: var(--primary-50);
  border-color: var(--primary-200);
}

.entity-item.entity-clickable:hover {
  transform: translateX(4px);
}

.entity-item.primary {
  background: var(--primary-100);
  border-color: var(--primary-color);
}

.entity-icon-wrapper {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-50);
  border-radius: 50%;
  flex-shrink: 0;
}

.entity-icon-wrapper.large {
  width: 48px;
  height: 48px;
}

.entity-icon-wrapper i {
  font-size: 1.125rem;
  color: var(--primary-color);
}

.entity-icon-wrapper.large i {
  font-size: 1.5rem;
}

.entity-info {
  flex: 1;
  min-width: 0;
}

.entity-name {
  font-weight: 600;
  font-size: 0.9375rem;
  color: var(--text-color);
  display: block;
}

.entity-name.large {
  font-size: 1.125rem;
}

.entity-type {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.entity-details {
  display: flex;
  gap: 1rem;
  margin-top: 0.25rem;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.entity-stats {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.stat {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: var(--text-color-secondary);
}

.selected-summary {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 6px;
}

.selected-summary strong {
  color: var(--text-color);
}

.selected-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

/* Paso 3 - Preview */
.merge-preview {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.merge-preview h4 {
  margin: 0 0 0.75rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-color);
}

.entity-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  border-radius: 8px;
  border: 2px solid;
}

.entity-card.primary-card {
  background: var(--primary-50);
  border-color: var(--primary-color);
}

.entity-card.secondary-card {
  background: var(--surface-50);
  border-color: var(--surface-200);
  margin-bottom: 0.5rem;
}

.merge-arrow {
  color: var(--primary-color);
  font-size: 1rem;
}

.merge-summary {
  background: var(--surface-50);
  padding: 1rem;
  border-radius: 6px;
}

.summary-items {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.9375rem;
}

.summary-item i {
  color: var(--primary-color);
}

.summary-item strong {
  color: var(--text-color);
  font-weight: 600;
}

/* Indicador de pasos */
.steps-indicator {
  display: flex;
  justify-content: center;
  gap: 1rem;
  padding-top: 0.5rem;
}

.step-dot {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--surface-200);
  color: var(--text-color-secondary);
  font-weight: 600;
  font-size: 0.875rem;
  transition: all 0.3s;
}

.step-dot.active {
  background: var(--primary-color);
  color: white;
  transform: scale(1.1);
}

.step-dot.completed {
  background: var(--green-500);
  color: white;
}

/* Footer */
.dialog-footer {
  display: flex;
  justify-content: space-between;
  width: 100%;
}

.footer-left,
.footer-right {
  display: flex;
  gap: 0.5rem;
}

.w-full {
  width: 100%;
}

/* Scrollbar */
.entities-selection::-webkit-scrollbar {
  width: 6px;
}

.entities-selection::-webkit-scrollbar-track {
  background: var(--surface-50);
}

.entities-selection::-webkit-scrollbar-thumb {
  background: var(--surface-300);
  border-radius: 3px;
}
</style>
