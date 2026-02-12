<template>
  <Dialog
    :visible="visible"
    modal
    header="Importar Trabajo Editorial"
    :style="{ width: '650px' }"
    @update:visible="emit('update:visible', $event)"
  >
    <!-- Step 1: Upload -->
    <div v-if="step === 'upload'" class="import-step">
      <p class="import-description">
        Selecciona un archivo <strong>.narrassist</strong> exportado por otro corrector.
        Solo se importan metadatos (decisiones, fusiones, atributos), no texto del manuscrito.
      </p>

      <FileUpload
        mode="basic"
        accept=".narrassist"
        :auto="false"
        choose-label="Seleccionar archivo"
        class="import-upload"
        @select="onFileSelect"
      />

      <div v-if="selectedFile" class="selected-file">
        <i class="pi pi-file"></i>
        <span>{{ selectedFile.name }}</span>
        <Tag :value="formatFileSize(selectedFile.size)" severity="secondary" />
      </div>

      <div class="import-actions">
        <Button
          label="Cancelar"
          severity="secondary"
          text
          @click="emit('update:visible', false)"
        />
        <Button
          label="Analizar archivo"
          icon="pi pi-search"
          :loading="loadingPreview"
          :disabled="!selectedFile"
          @click="uploadAndPreview"
        />
      </div>
    </div>

    <!-- Step 2: Preview -->
    <div v-if="step === 'preview' && preview" class="import-step">
      <!-- Warnings -->
      <div v-if="preview.warnings.length > 0" class="import-warnings">
        <div v-for="(warn, i) in preview.warnings" :key="i" class="warning-item">
          <i class="pi pi-exclamation-triangle"></i>
          <span>{{ warn }}</span>
        </div>
      </div>

      <!-- Stats summary -->
      <div class="preview-summary">
        <div class="summary-header">
          <span class="summary-title">Resumen de importacion</span>
          <Tag
            v-if="preview.total_to_apply > 0"
            :value="`${preview.total_to_apply} cambios a aplicar`"
            severity="success"
          />
          <Tag
            v-else
            value="Nada nuevo que importar"
            severity="secondary"
          />
        </div>

        <!-- Sections -->
        <div class="preview-sections">
          <div class="preview-section-row">
            <Checkbox v-model="importSections.entityMerges" :binary="true" input-id="impMerges" />
            <label for="impMerges">
              <strong>Fusiones de entidades</strong>
              <span class="section-stats">
                {{ preview.entity_merges.to_apply }} nuevas,
                {{ preview.entity_merges.already_done }} ya hechas
              </span>
            </label>
          </div>

          <div class="preview-section-row">
            <Checkbox v-model="importSections.alertDecisions" :binary="true" input-id="impAlerts" />
            <label for="impAlerts">
              <strong>Decisiones de alertas</strong>
              <span class="section-stats">
                {{ preview.alert_decisions.to_apply }} nuevas,
                {{ preview.alert_decisions.already_done }} ya hechas
              </span>
            </label>
          </div>

          <div class="preview-section-row">
            <Checkbox v-model="importSections.verifiedAttributes" :binary="true" input-id="impAttrs" />
            <label for="impAttrs">
              <strong>Atributos verificados</strong>
              <span class="section-stats">
                {{ preview.verified_attributes.to_apply }} nuevos,
                {{ preview.verified_attributes.already_done }} ya hechos
              </span>
            </label>
          </div>

          <div class="preview-section-row">
            <Checkbox v-model="importSections.suppressionRules" :binary="true" input-id="impRules" />
            <label for="impRules">
              <strong>Reglas de supresion</strong>
              <span class="section-stats">
                {{ preview.suppression_rules.to_add }} nuevas,
                {{ preview.suppression_rules.already_exist }} existentes
              </span>
            </label>
          </div>
        </div>
      </div>

      <!-- Conflicts -->
      <div v-if="preview.conflicts.length > 0" class="conflicts-section">
        <div class="conflicts-header">
          <i class="pi pi-exclamation-circle"></i>
          <span>{{ preview.conflicts.length }} conflicto(s) detectado(s)</span>
        </div>
        <div class="conflicts-list">
          <div
            v-for="conflict in preview.conflicts"
            :key="conflict.item_key"
            class="conflict-item"
          >
            <div class="conflict-description">
              <Tag :value="conflict.section" severity="secondary" />
              <span>{{ conflict.description }}</span>
            </div>
            <div class="conflict-values">
              <span class="conflict-local">Local: <strong>{{ conflict.local_value }}</strong></span>
              <span class="conflict-arrow">vs</span>
              <span class="conflict-imported">Importado: <strong>{{ conflict.imported_value }}</strong></span>
            </div>
            <div class="conflict-resolution">
              <Tag
                :value="conflict.resolution === 'imported_wins' ? 'Se aplica importado' : 'Se mantiene local'"
                :severity="conflict.resolution === 'imported_wins' ? 'warn' : 'info'"
              />
            </div>
          </div>
        </div>
      </div>

      <div class="import-actions">
        <Button
          label="Volver"
          severity="secondary"
          text
          icon="pi pi-arrow-left"
          @click="step = 'upload'"
        />
        <Button
          label="Aplicar cambios"
          icon="pi pi-check"
          :loading="loadingConfirm"
          :disabled="preview.total_to_apply === 0"
          @click="confirmImport"
        />
      </div>
    </div>

    <!-- Step 3: Done -->
    <div v-if="step === 'done'" class="import-step import-done">
      <i class="pi pi-check-circle done-icon"></i>
      <h3>Importacion completada</h3>
      <div v-if="confirmStats" class="done-stats">
        <p v-if="confirmStats.entity_merges_applied > 0">
          {{ confirmStats.entity_merges_applied }} fusiones aplicadas
        </p>
        <p v-if="confirmStats.alert_decisions_applied > 0">
          {{ confirmStats.alert_decisions_applied }} decisiones de alertas aplicadas
        </p>
        <p v-if="confirmStats.verified_attributes_applied > 0">
          {{ confirmStats.verified_attributes_applied }} atributos verificados
        </p>
        <p v-if="confirmStats.suppression_rules_added > 0">
          {{ confirmStats.suppression_rules_added }} reglas de supresion anadidas
        </p>
      </div>
      <Button
        label="Cerrar"
        @click="closeAndReset"
      />
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import FileUpload from 'primevue/fileupload'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { apiUrl } from '@/config/api'

const props = defineProps<{
  visible: boolean
  projectId: number
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'imported': []
}>()

const toast = useToast()

// State
const step = ref<'upload' | 'preview' | 'done'>('upload')
const selectedFile = ref<File | null>(null)
const loadingPreview = ref(false)
const loadingConfirm = ref(false)
const preview = ref<ImportPreview | null>(null)
const importData = ref<Record<string, unknown> | null>(null)
const confirmStats = ref<ConfirmStats | null>(null)

const importSections = ref({
  entityMerges: true,
  alertDecisions: true,
  verifiedAttributes: true,
  suppressionRules: true,
})

// Types
interface ImportPreview {
  project_fingerprint_match: boolean
  warnings: string[]
  entity_merges: { to_apply: number; already_done: number; conflicts: number }
  alert_decisions: { to_apply: number; already_done: number; conflicts: number }
  verified_attributes: { to_apply: number; already_done: number; conflicts: number }
  suppression_rules: { to_add: number; already_exist: number }
  conflicts: ImportConflict[]
  total_to_apply: number
  total_conflicts: number
  import_data: Record<string, unknown>
}

interface ImportConflict {
  section: string
  item_key: string
  description: string
  local_value: string
  imported_value: string
  local_timestamp: string
  imported_timestamp: string
  resolution: string
}

interface ConfirmStats {
  entity_merges_applied: number
  alert_decisions_applied: number
  verified_attributes_applied: number
  suppression_rules_added: number
  conflicts_resolved: number
}

// Helpers
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function onFileSelect(event: { files: File[] }) {
  if (event.files && event.files.length > 0) {
    selectedFile.value = event.files[0]
  }
}

async function uploadAndPreview() {
  if (!selectedFile.value) return
  loadingPreview.value = true

  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)

    const response = await fetch(
      apiUrl(`/api/projects/${props.projectId}/import-work/preview`),
      { method: 'POST', body: formData }
    )

    const data = await response.json()

    if (!data.success) {
      throw new Error(data.error || 'Error al analizar archivo')
    }

    preview.value = data.data
    importData.value = data.data.import_data
    step.value = 'preview'
  } catch (error) {
    console.error('Error previewing import:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error instanceof Error ? error.message : 'No se pudo analizar el archivo',
      life: 5000,
    })
  } finally {
    loadingPreview.value = false
  }
}

async function confirmImport() {
  if (!importData.value) return
  loadingConfirm.value = true

  try {
    const response = await fetch(
      apiUrl(`/api/projects/${props.projectId}/import-work/confirm`),
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          import_data: importData.value,
          import_entity_merges: importSections.value.entityMerges,
          import_alert_decisions: importSections.value.alertDecisions,
          import_verified_attributes: importSections.value.verifiedAttributes,
          import_suppression_rules: importSections.value.suppressionRules,
          conflict_overrides: null,
        }),
      }
    )

    const data = await response.json()

    if (!data.success) {
      throw new Error(data.error || 'Error al importar')
    }

    confirmStats.value = data.data
    step.value = 'done'
    emit('imported')
  } catch (error) {
    console.error('Error confirming import:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error instanceof Error ? error.message : 'No se pudo completar la importacion',
      life: 5000,
    })
  } finally {
    loadingConfirm.value = false
  }
}

function closeAndReset() {
  step.value = 'upload'
  selectedFile.value = null
  preview.value = null
  importData.value = null
  confirmStats.value = null
  importSections.value = {
    entityMerges: true,
    alertDecisions: true,
    verifiedAttributes: true,
    suppressionRules: true,
  }
  emit('update:visible', false)
}
</script>

<style scoped>
.import-step {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.import-description {
  color: var(--text-color-secondary);
  font-size: 0.95rem;
  line-height: 1.5;
}

.import-upload {
  width: 100%;
}

.selected-file {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: var(--surface-100);
  border-radius: 6px;
  font-size: 0.9rem;
}

.dark .selected-file {
  background: var(--surface-700);
}

.selected-file i {
  color: var(--primary-color);
}

.import-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--surface-border);
}

/* Warnings */
.import-warnings {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.warning-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: var(--orange-50);
  border: 1px solid var(--orange-200);
  border-radius: 6px;
  font-size: 0.85rem;
  color: var(--orange-700);
}

.dark .warning-item {
  background: var(--orange-900);
  border-color: var(--orange-700);
  color: var(--orange-300);
}

/* Preview summary */
.preview-summary {
  background: var(--surface-50);
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  padding: 1rem;
}

.dark .preview-summary {
  background: var(--surface-700);
}

.summary-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.summary-title {
  font-weight: 600;
  font-size: 0.95rem;
}

.preview-sections {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.preview-section-row {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.preview-section-row label {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  cursor: pointer;
}

.section-stats {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

/* Conflicts */
.conflicts-section {
  border: 1px solid var(--red-200);
  border-radius: 8px;
  overflow: hidden;
}

.dark .conflicts-section {
  border-color: var(--red-700);
}

.conflicts-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: var(--red-50);
  color: var(--red-700);
  font-weight: 600;
  font-size: 0.9rem;
}

.dark .conflicts-header {
  background: var(--red-900);
  color: var(--red-300);
}

.conflicts-list {
  display: flex;
  flex-direction: column;
}

.conflict-item {
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--surface-border);
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.conflict-description {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}

.conflict-values {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

.conflict-arrow {
  font-weight: 600;
  color: var(--text-color-secondary);
}

.conflict-resolution {
  display: flex;
  justify-content: flex-end;
}

/* Done step */
.import-done {
  align-items: center;
  text-align: center;
  padding: 1rem 0;
}

.done-icon {
  font-size: 3rem;
  color: var(--green-500);
}

.done-stats {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.9rem;
  color: var(--text-color-secondary);
}

.done-stats p {
  margin: 0;
}
</style>
