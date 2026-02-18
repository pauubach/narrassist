<script setup lang="ts">
import { ref, computed } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import RadioButton from 'primevue/radiobutton'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'

/**
 * RejectEntityDialog - Diálogo para rechazar entidades como falsos positivos
 *
 * Permite elegir el alcance del rechazo:
 * - Solo este proyecto: La entidad solo se filtrará en el proyecto actual
 * - Todos mis proyectos: La entidad se filtrará en todos los proyectos del usuario
 */

interface Props {
  /** Si el diálogo está visible */
  visible: boolean
  /** Nombre de la entidad a rechazar */
  entityName: string
  /** Tipo de entidad */
  entityType?: string
  /** ID del proyecto actual */
  projectId: number
  /** Número de menciones de la entidad en el documento */
  mentionCount?: number
}

// Umbral para considerar una entidad como "frecuente"
const FREQUENT_ENTITY_THRESHOLD = 5

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'reject': [scope: 'project' | 'global', reason: string]
}>()

// Estado local
const selectedScope = ref<'project' | 'global'>('project')
const reason = ref('')
const isSubmitting = ref(false)

// Computed
const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

// Es una entidad frecuente (aparece muchas veces)
const isFrequentEntity = computed(() => {
  return (props.mentionCount || 0) >= FREQUENT_ENTITY_THRESHOLD
})

// Opciones de alcance
const scopeOptions = [
  {
    value: 'project',
    label: 'Solo este proyecto',
    description: 'La entidad solo se filtrará en este proyecto. Podrá aparecer en otros proyectos.'
  },
  {
    value: 'global',
    label: 'Todos mis proyectos',
    description: 'La entidad se filtrará en todos tus proyectos actuales y futuros.'
  }
]

// Métodos
function onCancel() {
  dialogVisible.value = false
  resetForm()
}

function onConfirm() {
  emit('reject', selectedScope.value, reason.value)
  dialogVisible.value = false
  resetForm()
}

function resetForm() {
  selectedScope.value = 'project'
  reason.value = ''
  isSubmitting.value = false
}

function selectScope(value: string) {
  selectedScope.value = value as 'project' | 'global'
}
</script>

<template>
  <Dialog
    v-model:visible="dialogVisible"
    modal
    :header="`&quot;${entityName}&quot; no es una entidad`"
    :style="{ width: '500px' }"
    :closable="!isSubmitting"
    :draggable="false"
  >
    <div class="reject-entity-content">
      <!-- Advertencia para entidades frecuentes -->
      <Message v-if="isFrequentEntity" severity="warn" :closable="false" class="mb-3">
        <div class="frequent-warning">
          <strong>Esta entidad aparece {{ mentionCount }} veces</strong>
          <p>
            Descartar una entidad frecuente podría indicar un problema con la detección.
            ¿Estás seguro de que no es un personaje o elemento relevante?
          </p>
        </div>
      </Message>

      <div class="scope-selection">
        <label class="scope-label">Aplicar en:</label>

        <div class="scope-options">
          <div
            v-for="option in scopeOptions"
            :key="option.value"
            class="scope-option"
            :class="{ selected: selectedScope === option.value }"
            @click="selectScope(option.value)"
          >
            <RadioButton
              v-model="selectedScope"
              :input-id="`scope-${option.value}`"
              :value="option.value"
              class="scope-radio"
            />
            <div class="scope-content">
              <label :for="`scope-${option.value}`" class="scope-option-label">
                {{ option.label }}
              </label>
              <p class="scope-option-description">{{ option.description }}</p>
            </div>
          </div>
        </div>

        <Message severity="info" :closable="false" class="scope-hint">
          {{ selectedScope === 'global'
            ? 'El sistema no volverá a detectar este texto como entidad en ningún proyecto.'
            : 'El sistema no volverá a detectar este texto como entidad en este proyecto.'
          }}
        </Message>
      </div>

      <div class="reason-input mt-4">
        <label for="reject-reason" class="reason-label">Motivo (opcional)</label>
        <InputText
          id="reject-reason"
          v-model="reason"
          placeholder="¿Por qué rechazas esta entidad?"
          class="w-full"
        />
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <Button
          label="Cancelar"
          severity="secondary"
          text
          :disabled="isSubmitting"
          @click="onCancel"
        />
        <Button
          label="Confirmar"
          severity="danger"
          :loading="isSubmitting"
          @click="onConfirm"
        />
      </div>
    </template>
  </Dialog>
</template>

<style scoped>
.reject-entity-content {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
}

.scope-selection {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.scope-label {
  font-weight: 600;
  color: var(--ds-color-text);
  margin-bottom: var(--ds-space-1);
}

.scope-options {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.scope-option {
  display: flex;
  align-items: flex-start;
  gap: var(--ds-space-3);
  padding: var(--ds-space-3);
  border: 1px solid var(--ds-surface-border);
  border-radius: var(--ds-radius-md);
  cursor: pointer;
  transition: all 0.15s ease;
}

.scope-option:hover {
  border-color: var(--ds-color-primary);
  background-color: var(--ds-surface-hover);
}

.scope-option.selected {
  border-color: var(--ds-color-primary);
  background-color: var(--ds-color-primary-subtle);
}

.scope-radio {
  margin-top: 2px;
}

.scope-content {
  flex: 1;
}

.scope-option-label {
  font-weight: 500;
  color: var(--ds-color-text);
  cursor: pointer;
  display: block;
  margin-bottom: var(--ds-space-1);
}

.scope-option-description {
  font-size: var(--ds-font-sm);
  color: var(--ds-color-text-secondary);
  margin: 0;
  line-height: 1.4;
}

.reason-input {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-1);
}

.reason-label {
  font-size: var(--ds-font-sm);
  color: var(--ds-color-text-secondary);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--ds-space-2);
}

/* Message override */
:deep(.p-message) {
  margin: 0;
}

.scope-hint :deep(.p-message) {
  margin-top: var(--ds-space-1);
}

.frequent-warning {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.frequent-warning strong {
  font-size: 0.95rem;
}

.frequent-warning p {
  margin: 0;
  font-size: 0.85rem;
  opacity: 0.9;
}
</style>
