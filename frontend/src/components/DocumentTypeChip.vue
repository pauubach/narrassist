<template>
  <div v-if="documentType" class="document-type-chip">
    <button
      class="chip-button"
      :style="{ '--chip-color': documentType.type_color }"
      @click="togglePopover"
    >
      <i :class="['pi', documentType.type_icon]"></i>
      <span class="chip-label">{{ documentType.type_name }}</span>
      <span v-if="documentType.subtype_name" class="chip-subtype">
        ({{ documentType.subtype_name }})
      </span>
      <i class="pi pi-chevron-down chip-arrow"></i>
    </button>

    <Popover ref="popoverRef">
      <div class="type-selector-panel">
        <div class="panel-header">
          <span>Tipo de documento</span>
          <small v-if="!documentType.confirmed" class="suggested-badge">
            Sugerido
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

        <!-- Two column selector -->
        <div class="selector-container">
          <!-- Types column -->
          <div class="types-column">
            <div class="column-header">Tipo</div>
            <div class="types-list">
              <button
                v-for="type in documentTypes"
                :key="type.code"
                class="type-option"
                :class="{ selected: type.code === documentType.type }"
                @click="selectType(type.code)"
              >
                <i :class="['pi', type.icon]" :style="{ color: type.color }"></i>
                <span class="type-name">{{ type.name }}</span>
                <i v-if="type.code === documentType.type" class="pi pi-check"></i>
              </button>
            </div>
          </div>

          <!-- Subtypes column -->
          <div v-if="currentTypeSubtypes.length > 0" class="subtypes-column">
            <div class="column-header">Subtipo</div>
            <div class="subtypes-list">
              <button
                v-for="subtype in currentTypeSubtypes"
                :key="subtype.code"
                class="subtype-option"
                :class="{ selected: subtype.code === selectedSubtype }"
                @click="selectSubtype(subtype.code)"
              >
                <span>{{ subtype.name }}</span>
                <i v-if="subtype.code === selectedSubtype" class="pi pi-check"></i>
              </button>
              <!-- Option to clear subtype -->
              <button
                class="subtype-option clear-option"
                :class="{ selected: !selectedSubtype }"
                @click="selectSubtype(null)"
              >
                <span>Sin especificar</span>
                <i v-if="!selectedSubtype" class="pi pi-check"></i>
              </button>
            </div>
          </div>
        </div>

        <!-- Description box -->
        <div v-if="correctionConfig" class="config-description">
          <i class="pi pi-info-circle"></i>
          <div class="description-content">
            <strong>{{ correctionConfig.type_name }}</strong>
            <span v-if="correctionConfig.subtype_name"> / {{ correctionConfig.subtype_name }}</span>
            <div class="config-summary">
              <span v-if="correctionConfig.dialog?.enabled">
                <i class="pi pi-comments"></i> Diálogos
              </span>
              <span v-if="correctionConfig.structure?.timeline_enabled">
                <i class="pi pi-clock"></i> Timeline
              </span>
              <span v-if="correctionConfig.structure?.relationships_enabled">
                <i class="pi pi-users"></i> Relaciones
              </span>
              <span v-if="correctionConfig.readability?.enabled">
                <i class="pi pi-book"></i> Edad {{ correctionConfig.readability.target_age_min }}-{{ correctionConfig.readability.target_age_max }}
              </span>
            </div>
            <div class="repetition-info">
              Repeticiones:
              <span :class="'tolerance-' + correctionConfig.repetition?.tolerance">
                {{ getToleranceLabel(correctionConfig.repetition?.tolerance) }}
              </span>
              <span v-if="correctionConfig.repetition?.flag_lack_of_repetition" class="inverted-flag">
                (avisa si faltan)
              </span>
            </div>
          </div>
        </div>

        <!-- Advanced settings button -->
        <div class="panel-footer">
          <Button
            label="Parámetros de corrección"
            icon="pi pi-cog"
            size="small"
            text
            @click="openCorrectionSettings"
          />
        </div>
      </div>
    </Popover>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import Popover from 'primevue/popover'
import Button from 'primevue/button'
import { api } from '@/services/apiClient'

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

// Importar tipo desde corrections.ts
import type { DetailedCorrectionConfig as CorrectionConfig } from '@/types'

const props = defineProps<{
  projectId: number
}>()

const emit = defineEmits<{
  (e: 'type-changed', type: string, subtype: string | null): void
  (e: 'open-correction-settings'): void
}>()

const popoverRef = ref<InstanceType<typeof Popover> | null>(null)
const documentType = ref<DocumentType | null>(null)
const documentTypes = ref<TypeInfo[]>([])
const selectedSubtype = ref<string | null>(null)
const correctionConfig = ref<CorrectionConfig | null>(null)
const loading = ref(false)

// Computed: subtypes for current type
const currentTypeSubtypes = computed(() => {
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

const getToleranceLabel = (tolerance: string | undefined): string => {
  const labels: Record<string, string> = {
    'very_high': 'Muy alta',
    'high': 'Alta',
    'medium': 'Media',
    'low': 'Baja',
  }
  return labels[tolerance || 'medium'] || 'Media'
}

const selectType = async (typeCode: string) => {
  if (!documentType.value || loading.value) return

  loading.value = true
  try {
    const data = await api.putRaw<any>(`/api/projects/${props.projectId}/document-type`, {
      document_type: typeCode,
      document_subtype: null,
    })

    if (data.success) {
      documentType.value = data.data.document_type
      selectedSubtype.value = null
      emit('type-changed', typeCode, null)
      // Reload correction config
      loadCorrectionConfig()
    }
  } catch (err) {
    console.error('Error updating document type:', err)
  } finally {
    loading.value = false
  }
}

const selectSubtype = async (subtypeCode: string | null) => {
  if (!documentType.value || loading.value) return

  selectedSubtype.value = subtypeCode
  loading.value = true
  try {
    const data = await api.putRaw<any>(`/api/projects/${props.projectId}/document-type`, {
      document_type: documentType.value.type,
      document_subtype: subtypeCode,
    })

    if (data.success && data.data.document_type) {
      documentType.value = data.data.document_type
      emit('type-changed', data.data.document_type.type, subtypeCode)
      // Reload correction config
      loadCorrectionConfig()
    }
  } catch (err) {
    console.error('Error updating document subtype:', err)
  } finally {
    loading.value = false
  }
}

const openCorrectionSettings = () => {
  popoverRef.value?.hide()
  emit('open-correction-settings')
}

const loadDocumentType = async () => {
  try {
    const data = await api.getRaw<any>(`/api/projects/${props.projectId}/document-type`)
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
    // Use new correction config API
    const data = await api.getRaw<any>('/api/correction-config/types')
    if (data.success) {
      documentTypes.value = data.data
    }
  } catch (_err) {
    // Fallback to old API
    try {
      const data = await api.getRaw<any>('/api/document-types')
      if (data.success) {
        documentTypes.value = data.data
      }
    } catch (fallbackErr) {
      console.error('Error loading document types:', fallbackErr)
    }
  }
}

const loadCorrectionConfig = async () => {
  if (!documentType.value) return

  try {
    const typeCode = documentType.value.type
    const subtypeCode = selectedSubtype.value
    const url = subtypeCode
      ? `/api/correction-config/${typeCode}?subtype_code=${subtypeCode}`
      : `/api/correction-config/${typeCode}`

    const data = await api.getRaw<any>(url)
    if (data.success) {
      correctionConfig.value = data.data
    }
  } catch (err) {
    console.error('Error loading correction config:', err)
  }
}

// Watch for project changes
watch(() => props.projectId, () => {
  if (props.projectId) {
    loadDocumentType()
  }
})

// Watch for document type changes to load correction config
watch(documentType, () => {
  if (documentType.value) {
    loadCorrectionConfig()
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
  width: 480px;
  max-height: 500px;
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

.suggested-badge {
  font-weight: 400;
  color: var(--text-color-secondary);
  font-style: italic;
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

/* Two column selector */
.selector-container {
  display: flex;
  border-bottom: 1px solid var(--surface-border);
}

.types-column,
.subtypes-column {
  flex: 1;
  min-width: 0;
}

.types-column {
  border-right: 1px solid var(--surface-border);
}

.column-header {
  padding: 0.5rem 0.75rem;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--text-color-secondary);
  background: var(--surface-ground);
}

.types-list,
.subtypes-list {
  padding: 0.5rem;
  max-height: 250px;
  overflow-y: auto;
}

.type-option,
.subtype-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.5rem 0.625rem;
  border: none;
  background: transparent;
  border-radius: var(--app-radius);
  cursor: pointer;
  text-align: left;
  transition: background 0.15s;
  font-size: 0.8125rem;
}

.type-option:hover,
.subtype-option:hover {
  background: var(--surface-hover);
}

.type-option.selected,
.subtype-option.selected {
  background: var(--primary-50);
}

.type-option > i:first-child {
  font-size: 1rem;
}

.type-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.type-option > i:last-child,
.subtype-option > i:last-child {
  color: var(--primary-color);
  font-size: 0.75rem;
}

.subtype-option span {
  flex: 1;
}

.clear-option {
  font-style: italic;
  color: var(--text-color-secondary);
}

/* Config description */
.config-description {
  display: flex;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: var(--surface-ground);
  border-bottom: 1px solid var(--surface-border);
  font-size: 0.8125rem;
}

.config-description > i {
  color: var(--primary-color);
  margin-top: 0.125rem;
}

.description-content {
  flex: 1;
}

.config-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 0.375rem;
  color: var(--text-color-secondary);
  font-size: 0.75rem;
}

.config-summary span {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.repetition-info {
  margin-top: 0.375rem;
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.tolerance-very_high { color: var(--green-600); }
.tolerance-high { color: var(--teal-600); }
.tolerance-medium { color: var(--yellow-600); }
.tolerance-low { color: var(--red-600); }

.inverted-flag {
  font-style: italic;
  color: var(--orange-600);
}

/* Panel footer */
.panel-footer {
  display: flex;
  justify-content: flex-end;
  padding: 0.5rem 0.75rem;
}

/* Dark mode */
.dark .mismatch-warning {
  background: var(--yellow-900);
  color: var(--yellow-100);
}

.dark .type-option.selected,
.dark .subtype-option.selected {
  background: var(--primary-900);
}

.dark .config-description {
  background: var(--surface-card);
}
</style>
