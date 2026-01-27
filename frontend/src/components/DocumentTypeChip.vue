<template>
  <div class="document-type-chip" v-if="documentType">
    <button
      class="chip-button"
      :style="{ '--chip-color': documentType.type_color }"
      @click="togglePopover"
    >
      <i :class="documentType.type_icon"></i>
      <span class="chip-label">{{ documentType.type_name }}</span>
      <span v-if="documentType.subtype_name" class="chip-subtype">
        ({{ documentType.subtype_name }})
      </span>
      <i class="pi pi-chevron-down chip-arrow"></i>
    </button>

    <OverlayPanel ref="popoverRef">
        <div class="type-selector-panel">
          <div class="panel-header">
            <span>Tipo de documento</span>
            <small v-if="!documentType.confirmed" class="not-confirmed">
              Sin confirmar
            </small>
          </div>

          <!-- Warning if mismatch detected -->
          <div v-if="documentType.has_mismatch" class="mismatch-warning">
            <i class="pi pi-info-circle"></i>
            <span>
              El sistema detecta que podría ser
              <strong>{{ getTypeName(documentType.detected_type) }}</strong>
            </span>
            <Button
              label="Cambiar"
              size="small"
              text
              @click="documentType.detected_type && selectType(documentType.detected_type)"
            />
          </div>

          <!-- Type list -->
          <div class="types-list">
            <button
              v-for="type in documentTypes"
              :key="type.code"
              class="type-option"
              :class="{ selected: type.code === documentType.type }"
              @click="selectType(type.code)"
            >
              <i :class="type.icon" :style="{ color: type.color }"></i>
              <div class="type-info">
                <span class="type-name">{{ type.name }}</span>
                <span class="type-desc">{{ type.description }}</span>
              </div>
              <i v-if="type.code === documentType.type" class="pi pi-check"></i>
            </button>
          </div>

          <!-- Subtype selector (if type has subtypes) -->
          <div v-if="selectedTypeSubtypes.length > 0" class="subtypes-section">
            <div class="subtypes-header">Subtipo</div>
            <Dropdown
              v-model="selectedSubtype"
              :options="selectedTypeSubtypes"
              optionLabel="name"
              optionValue="code"
              placeholder="Seleccionar subtipo"
              class="subtypes-dropdown"
              @change="onSubtypeChange"
            />
          </div>
        </div>
    </OverlayPanel>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import OverlayPanel from 'primevue/overlaypanel'
import Dropdown from 'primevue/dropdown'
import Button from 'primevue/button'

interface DocumentType {
  type: string
  type_name: string
  type_icon: string
  type_color: string
  subtype: string | null
  subtype_name: string | null
  confirmed: boolean
  detected_type: string | null
  has_mismatch: boolean
}

interface TypeInfo {
  code: string
  name: string
  description: string
  icon: string
  color: string
  subtypes: Array<{ code: string; name: string }>
}

const props = defineProps<{
  projectId: number
}>()

const emit = defineEmits<{
  (e: 'type-changed', type: string, subtype: string | null): void
}>()

const popoverRef = ref<InstanceType<typeof OverlayPanel> | null>(null)
const documentType = ref<DocumentType | null>(null)
const documentTypes = ref<TypeInfo[]>([])
const selectedSubtype = ref<string | null>(null)
const loading = ref(false)

// Get subtypes for currently selected type
const selectedTypeSubtypes = computed(() => {
  if (!documentType.value) return []
  const type = documentTypes.value.find(t => t.code === documentType.value?.type)
  return type?.subtypes || []
})

const togglePopover = (event: Event) => {
  popoverRef.value?.toggle(event)
}

const getTypeName = (typeCode: string | null): string => {
  if (!typeCode) return ''
  const type = documentTypes.value.find(t => t.code === typeCode)
  return type?.name || typeCode
}

const selectType = async (typeCode: string) => {
  if (!documentType.value || loading.value) return

  loading.value = true
  try {
    const response = await fetch(`/api/projects/${props.projectId}/document-type`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        document_type: typeCode,
        document_subtype: null,
      }),
    })

    const data = await response.json()
    if (data.success) {
      documentType.value = data.data.document_type
      selectedSubtype.value = null
      emit('type-changed', typeCode, null)
      popoverRef.value?.hide()
    }
  } catch (err) {
    console.error('Error updating document type:', err)
  } finally {
    loading.value = false
  }
}

const onSubtypeChange = async () => {
  if (!documentType.value || !selectedSubtype.value || loading.value) return

  loading.value = true
  try {
    const response = await fetch(`/api/projects/${props.projectId}/document-type`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        document_type: documentType.value.type,
        document_subtype: selectedSubtype.value,
      }),
    })

    const data = await response.json()
    if (data.success) {
      documentType.value = data.data.document_type
      if (documentType.value) {
        emit('type-changed', documentType.value.type, selectedSubtype.value)
      }
    }
  } catch (err) {
    console.error('Error updating document subtype:', err)
  } finally {
    loading.value = false
  }
}

const loadDocumentType = async () => {
  try {
    const response = await fetch(`/api/projects/${props.projectId}/document-type`)
    const data = await response.json()
    if (data.success) {
      documentType.value = data.data
      selectedSubtype.value = data.data.subtype
    }
  } catch (err) {
    console.error('Error loading document type:', err)
  }
}

const loadDocumentTypes = async () => {
  try {
    const response = await fetch('/api/document-types')
    const data = await response.json()
    if (data.success) {
      documentTypes.value = data.data
    }
  } catch (err) {
    console.error('Error loading document types:', err)
  }
}

// Watch for project changes
watch(() => props.projectId, () => {
  if (props.projectId) {
    loadDocumentType()
  }
})

onMounted(() => {
  loadDocumentTypes()
  if (props.projectId) {
    loadDocumentType()
  }
})
</script>

<style scoped>
.document-type-chip {
  display: inline-flex;
}

.chip-button {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0.625rem;
  border: 1px solid var(--chip-color, var(--surface-border));
  border-radius: 1rem;
  background: color-mix(in srgb, var(--chip-color, var(--primary-color)) 10%, transparent);
  color: var(--chip-color, var(--primary-color));
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.chip-button:hover {
  background: color-mix(in srgb, var(--chip-color, var(--primary-color)) 20%, transparent);
}

.chip-button i:first-child {
  font-size: 0.875rem;
}

.chip-label {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chip-subtype {
  font-size: 0.75rem;
  opacity: 0.8;
}

.chip-arrow {
  font-size: 0.625rem;
  opacity: 0.7;
}

/* Panel styles */
.type-selector-panel {
  width: 320px;
  max-height: 400px;
  overflow-y: auto;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--surface-border);
  font-weight: 600;
  font-size: 0.875rem;
}

.not-confirmed {
  font-weight: 400;
  color: var(--orange-500);
}

.mismatch-warning {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: var(--yellow-50);
  border-bottom: 1px solid var(--surface-border);
  font-size: 0.8125rem;
  color: var(--yellow-900);
}

.mismatch-warning i {
  color: var(--yellow-600);
}

.types-list {
  padding: 0.5rem;
}

.type-option {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  width: 100%;
  padding: 0.625rem 0.75rem;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s;
}

.type-option:hover {
  background: var(--surface-hover);
}

.type-option.selected {
  background: var(--primary-50);
}

.type-option > i:first-child {
  font-size: 1.125rem;
  margin-top: 0.125rem;
}

.type-info {
  flex: 1;
  min-width: 0;
}

.type-name {
  display: block;
  font-weight: 500;
  font-size: 0.875rem;
  color: var(--text-color);
}

.type-desc {
  display: block;
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  margin-top: 0.125rem;
  line-height: 1.3;
}

.type-option > i:last-child {
  color: var(--primary-color);
  font-size: 0.875rem;
  margin-top: 0.25rem;
}

.subtypes-section {
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--surface-border);
}

.subtypes-header {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-color-secondary);
  margin-bottom: 0.5rem;
  text-transform: uppercase;
}

.subtypes-dropdown {
  width: 100%;
}

/* Dark mode */
.dark .mismatch-warning {
  background: var(--yellow-900);
  color: var(--yellow-100);
}

.dark .type-option.selected {
  background: var(--primary-900);
}
</style>
