<template>
  <Dialog
    :visible="visible"
    modal
    :header="'Exportar - ' + projectName"
    :style="{ width: '700px' }"
    @update:visible="emit('update:visible', $event)"
  >
    <div class="export-dialog-content">
      <!-- Documento Completo (DOCX/PDF) -->
      <Card class="export-option document-export-card">
        <template #title>
          <div class="export-title">
            <i class="pi pi-file-word"></i>
            <span>Documento Completo</span>
            <Tag value="Nuevo" severity="success" class="new-tag" />
          </div>
        </template>
        <template #content>
          <p class="export-description">
            Informe profesional completo en Word o PDF con portada, índice y todas las secciones del análisis.
          </p>

          <!-- Secciones a incluir -->
          <div class="sections-selector">
            <span class="sections-label">Secciones a incluir:</span>
            <div class="sections-grid">
              <div class="checkbox-item">
                <Checkbox v-model="documentOptions.includeCharacters" :binary="true" input-id="docCharacters" />
                <label for="docCharacters">
                  <i class="pi pi-users"></i>
                  Personajes
                </label>
              </div>
              <div class="checkbox-item">
                <Checkbox v-model="documentOptions.includeAlerts" :binary="true" input-id="docAlerts" />
                <label for="docAlerts">
                  <i class="pi pi-exclamation-triangle"></i>
                  Alertas
                </label>
              </div>
              <div class="checkbox-item">
                <Checkbox v-model="documentOptions.includeTimeline" :binary="true" input-id="docTimeline" />
                <label for="docTimeline">
                  <i class="pi pi-clock"></i>
                  Timeline
                </label>
              </div>
              <div class="checkbox-item">
                <Checkbox v-model="documentOptions.includeRelationships" :binary="true" input-id="docRelationships" />
                <label for="docRelationships">
                  <i class="pi pi-sitemap"></i>
                  Relaciones
                </label>
              </div>
              <div class="checkbox-item">
                <Checkbox v-model="documentOptions.includeStyleGuide" :binary="true" input-id="docStyleGuide" />
                <label for="docStyleGuide">
                  <i class="pi pi-book"></i>
                  Guia de estilo
                </label>
              </div>
            </div>
          </div>

          <!-- Opciones de filtrado -->
          <div class="filter-options">
            <div class="checkbox-item">
              <Checkbox v-model="documentOptions.onlyMainCharacters" :binary="true" input-id="docOnlyMain" />
              <label for="docOnlyMain">Solo personajes principales</label>
            </div>
            <div class="checkbox-item">
              <Checkbox v-model="documentOptions.onlyOpenAlerts" :binary="true" input-id="docOnlyOpen" />
              <label for="docOnlyOpen">Solo alertas abiertas</label>
            </div>
          </div>

          <!-- Preview -->
          <div v-if="documentPreview" class="document-preview">
            <div class="preview-row">
              <span class="preview-label">Páginas estimadas:</span>
              <Tag :value="documentPreview.estimated_pages + ' págs.'" severity="info" />
            </div>
            <div class="preview-row">
              <span class="preview-label">Contenido:</span>
              <div class="preview-content-tags">
                <Tag
                  v-if="documentPreview.sections?.characters?.count > 0"
                  :value="documentPreview.sections.characters.count + ' personajes'"
                  severity="secondary"
                />
                <Tag
                  v-if="documentPreview.sections?.alerts?.count > 0"
                  :value="documentPreview.sections.alerts.count + ' alertas'"
                  severity="secondary"
                />
                <Tag
                  v-if="documentPreview.sections?.timeline?.event_count > 0"
                  :value="documentPreview.sections.timeline.event_count + ' eventos'"
                  severity="secondary"
                />
                <Tag
                  v-if="documentPreview.sections?.relationships?.count > 0"
                  :value="documentPreview.sections.relationships.count + ' relaciones'"
                  severity="secondary"
                />
              </div>
            </div>
          </div>

          <div class="format-selector">
            <label>Formato:</label>
            <div class="format-buttons">
              <Button
                label="DOCX (Word)"
                icon="pi pi-file-word"
                :outlined="documentFormat !== 'docx'"
                size="small"
                @click="documentFormat = 'docx'"
              />
              <Button
                label="PDF"
                icon="pi pi-file-pdf"
                :outlined="documentFormat !== 'pdf'"
                size="small"
                @click="documentFormat = 'pdf'"
              />
            </div>
          </div>

          <div class="export-actions">
            <Button
              label="Vista previa"
              icon="pi pi-eye"
              severity="secondary"
              :loading="loadingDocPreview"
              size="small"
              @click="loadDocumentPreview"
            />
            <Button
              label="Exportar documento"
              icon="pi pi-download"
              :loading="loadingDocument"
              class="flex-grow-1"
              @click="exportDocument"
            />
          </div>
        </template>
      </Card>

      <!-- Informe de Análisis -->
      <Card class="export-option">
        <template #title>
          <div class="export-title">
            <i class="pi pi-file-edit"></i>
            <span>Informe de Análisis</span>
          </div>
        </template>
        <template #content>
          <p class="export-description">
            Resumen completo del manuscrito incluyendo estadísticas, alertas y entidades detectadas.
          </p>

          <div class="format-selector">
            <label>Formato:</label>
            <div class="format-buttons">
              <Button
                label="Markdown"
                :outlined="reportFormat !== 'markdown'"
                size="small"
                @click="reportFormat = 'markdown'"
              />
              <Button
                label="JSON"
                :outlined="reportFormat !== 'json'"
                size="small"
                @click="reportFormat = 'json'"
              />
            </div>
          </div>

          <Button
            label="Exportar informe"
            icon="pi pi-download"
            :loading="loadingReport"
            class="export-button"
            @click="exportReport"
          />
        </template>
      </Card>

      <!-- Fichas de Personajes -->
      <Card class="export-option">
        <template #title>
          <div class="export-title">
            <i class="pi pi-users"></i>
            <span>Fichas de Personajes</span>
          </div>
        </template>
        <template #content>
          <p class="export-description">
            Fichas detalladas de los personajes principales con atributos y apariciones.
          </p>

          <div class="export-checkboxes">
            <div class="checkbox-item">
              <Checkbox v-model="characterOptions.onlyMain" :binary="true" input-id="onlyMain" />
              <label for="onlyMain">Solo personajes principales</label>
            </div>
            <div class="checkbox-item">
              <Checkbox v-model="characterOptions.includeAttributes" :binary="true" input-id="includeAttr" />
              <label for="includeAttr">Incluir atributos</label>
            </div>
            <div class="checkbox-item">
              <Checkbox v-model="characterOptions.includeMentions" :binary="true" input-id="includeMent" />
              <label for="includeMent">Incluir apariciones destacadas</label>
            </div>
          </div>

          <div class="format-selector">
            <label>Formato:</label>
            <div class="format-buttons">
              <Button
                label="Markdown"
                :outlined="characterFormat !== 'markdown'"
                size="small"
                @click="characterFormat = 'markdown'"
              />
              <Button
                label="JSON"
                :outlined="characterFormat !== 'json'"
                size="small"
                @click="characterFormat = 'json'"
              />
            </div>
          </div>

          <Button
            label="Exportar fichas"
            icon="pi pi-download"
            :loading="loadingCharacters"
            class="export-button"
            @click="exportCharacterSheets"
          />
        </template>
      </Card>

      <!-- Hoja de Estilo / Style Guide -->
      <Card class="export-option style-guide-card">
        <template #title>
          <div class="export-title">
            <i class="pi pi-book"></i>
            <span>Guía de Estilo</span>
            <Button
              v-if="!showStylePreview"
              v-tooltip="'Ver preview'"
              icon="pi pi-eye"
              text
              rounded
              size="small"
              :loading="loadingPreview"
              class="preview-btn"
              @click="loadStylePreview"
            />
            <Button
              v-else
              v-tooltip="'Ocultar preview'"
              icon="pi pi-eye-slash"
              text
              rounded
              size="small"
              class="preview-btn"
              @click="showStylePreview = false"
            />
          </div>
        </template>
        <template #content>
          <p class="export-description">
            Decisiones editoriales, grafías preferidas, personajes canónicos y análisis estilístico del manuscrito.
          </p>

          <!-- Preview Section -->
          <div v-if="showStylePreview && stylePreview" class="style-preview">
            <div class="preview-header">
              <span class="preview-title">Preview de la Guía</span>
              <Tag :value="`${stylePreview.total_entities} entidades`" severity="info" />
            </div>

            <div class="preview-stats">
              <div class="preview-stat">
                <i class="pi pi-users"></i>
                <span>{{ stylePreview.characters_count }} personajes</span>
              </div>
              <div class="preview-stat">
                <i class="pi pi-map-marker"></i>
                <span>{{ stylePreview.locations_count }} ubicaciones</span>
              </div>
              <div class="preview-stat">
                <i class="pi pi-building"></i>
                <span>{{ stylePreview.organizations_count }} organizaciones</span>
              </div>
              <div v-if="stylePreview.total_spelling_variants > 0" class="preview-stat">
                <i class="pi pi-pencil"></i>
                <span>{{ stylePreview.total_spelling_variants }} variantes de grafía</span>
              </div>
            </div>

            <!-- Personajes destacados -->
            <div v-if="stylePreview.characters_preview?.length" class="preview-section">
              <span class="preview-section-title">Personajes principales:</span>
              <div class="preview-chips">
                <Tag
                  v-for="char in stylePreview.characters_preview.slice(0, 5)"
                  :key="char.name"
                  :value="char.name"
                  :severity="char.importance === 'principal' || char.importance === 'high' ? 'success' : 'secondary'"
                />
              </div>
            </div>

            <!-- Análisis estilístico -->
            <div v-if="stylePreview.style_summary" class="preview-section">
              <span class="preview-section-title">Análisis estilístico:</span>
              <div class="preview-style-info">
                <span><strong>Palabras:</strong> {{ stylePreview.style_summary.total_words?.toLocaleString() }}</span>
                <span><strong>Diálogos:</strong> {{ getDialogueStyleLabel(stylePreview.style_summary.dialogue_style) }}</span>
                <span v-if="stylePreview.style_summary.consistency_issues_count > 0" class="issues-warning">
                  <i class="pi pi-exclamation-triangle"></i>
                  {{ stylePreview.style_summary.consistency_issues_count }} inconsistencias
                </span>
              </div>
            </div>
          </div>

          <div class="format-selector">
            <label>Formato:</label>
            <div class="format-buttons">
              <Button
                label="Markdown"
                :outlined="styleFormat !== 'markdown'"
                size="small"
                @click="styleFormat = 'markdown'"
              />
              <Button
                label="JSON"
                :outlined="styleFormat !== 'json'"
                size="small"
                @click="styleFormat = 'json'"
              />
              <Button
                label="PDF"
                :outlined="styleFormat !== 'pdf'"
                size="small"
                @click="styleFormat = 'pdf'"
              />
            </div>
          </div>

          <Button
            label="Exportar guía de estilo"
            icon="pi pi-download"
            :loading="loadingStyle"
            class="export-button"
            @click="exportStyleGuide"
          />
        </template>
      </Card>

      <!-- Solo Alertas -->
      <Card class="export-option">
        <template #title>
          <div class="export-title">
            <i class="pi pi-exclamation-triangle"></i>
            <span>Solo Alertas</span>
          </div>
        </template>
        <template #content>
          <p class="export-description">
            Lista filtrable de alertas para análisis externo o compartir con el equipo.
          </p>

          <div class="export-checkboxes">
            <div class="checkbox-item">
              <Checkbox v-model="alertOptions.includePending" :binary="true" input-id="pendingAlerts" />
              <label for="pendingAlerts">Incluir pendientes</label>
            </div>
            <div class="checkbox-item">
              <Checkbox v-model="alertOptions.includeResolved" :binary="true" input-id="resolvedAlerts" />
              <label for="resolvedAlerts">Incluir resueltas</label>
            </div>
          </div>

          <div class="format-selector">
            <label>Formato:</label>
            <div class="format-buttons">
              <Button
                label="JSON"
                :outlined="alertFormat !== 'json'"
                size="small"
                @click="alertFormat = 'json'"
              />
              <Button
                label="CSV"
                :outlined="alertFormat !== 'csv'"
                size="small"
                @click="alertFormat = 'csv'"
              />
            </div>
          </div>

          <Button
            label="Exportar alertas"
            icon="pi pi-download"
            :loading="loadingAlerts"
            class="export-button"
            @click="exportAlerts"
          />
        </template>
      </Card>

      <!-- Documento con Correcciones (Track Changes) -->
      <Card class="export-option">
        <template #title>
          <div class="export-title">
            <i class="pi pi-file-edit"></i>
            <span>Documento con Correcciones</span>
          </div>
        </template>
        <template #content>
          <p class="export-description">
            Exporta el manuscrito Word con las correcciones aplicadas como revisiones (Track Changes) o directamente.
          </p>

          <div class="corrected-options">
            <span class="sections-label">Categorías a incluir:</span>
            <div class="sections-grid">
              <div v-for="cat in correctionCategories" :key="cat.value" class="checkbox-item">
                <Checkbox v-model="correctedOptions.categories" :value="cat.value" :input-id="'corr-' + cat.value" />
                <label :for="'corr-' + cat.value">{{ cat.label }}</label>
              </div>
            </div>
          </div>

          <div class="confidence-slider">
            <label>Confianza mínima: <strong>{{ correctedOptions.minConfidence }}%</strong></label>
            <Slider v-model="correctedOptions.minConfidence" :min="10" :max="100" :step="5" />
          </div>

          <div class="export-checkboxes">
            <div class="checkbox-item">
              <Checkbox v-model="correctedOptions.asTrackChanges" :binary="true" input-id="corrTrackChanges" />
              <label for="corrTrackChanges">Como revisiones (Track Changes)</label>
            </div>
          </div>

          <Button
            label="Exportar documento corregido"
            icon="pi pi-download"
            :loading="loadingCorrected"
            class="export-button"
            @click="exportCorrected"
          />
        </template>
      </Card>

      <!-- Trabajo Editorial (.narrassist) -->
      <Card class="export-option editorial-work-card">
        <template #title>
          <div class="export-title">
            <i class="pi pi-briefcase"></i>
            <span>Trabajo Editorial</span>
            <Tag value="Editorial" severity="warn" class="new-tag" />
          </div>
        </template>
        <template #content>
          <p class="export-description">
            Comparte decisiones editoriales (fusiones, descartes, atributos verificados) entre correctores sin transferir el manuscrito.
          </p>

          <div class="editorial-work-actions">
            <Button
              label="Exportar trabajo (.narrassist)"
              icon="pi pi-upload"
              :loading="loadingEditorialExport"
              class="flex-grow-1"
              @click="exportEditorialWork"
            />
            <Button
              label="Importar trabajo"
              icon="pi pi-download"
              severity="secondary"
              @click="showImportDialog = true"
            />
          </div>
        </template>
      </Card>

      <!-- Scrivener Export Card -->
      <Card class="export-card">
        <template #title>
          <i class="pi pi-folder"></i> Exportar a Scrivener
        </template>
        <template #subtitle>
          Genera un paquete .scriv compatible con Scrivener 3
        </template>
        <template #content>
          <div class="scrivener-options">
            <div class="option-row">
              <Checkbox v-model="scrivenerOptions.includeCharacterNotes" binary input-id="scriv-chars" />
              <label for="scriv-chars">Incluir fichas de personaje</label>
            </div>
            <div class="option-row">
              <Checkbox v-model="scrivenerOptions.includeAlertsAsNotes" binary input-id="scriv-alerts" />
              <label for="scriv-alerts">Incluir alertas como notas</label>
            </div>
            <div class="option-row">
              <Checkbox v-model="scrivenerOptions.includeEntityKeywords" binary input-id="scriv-keywords" />
              <label for="scriv-keywords">Incluir entidades como keywords</label>
            </div>
          </div>
          <Button
            label="Exportar .scriv"
            icon="pi pi-download"
            :loading="loadingScrivener"
            class="export-button"
            @click="exportScrivener"
          />
        </template>
      </Card>
    </div>

    <!-- Import Work Dialog -->
    <ImportWorkDialog
      v-model:visible="showImportDialog"
      :project-id="projectId"
      @imported="onWorkImported"
    />
  </Dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Dialog from 'primevue/dialog'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Slider from 'primevue/slider'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { apiUrl } from '@/config/api'
import { api } from '@/services/apiClient'
import ImportWorkDialog from './ImportWorkDialog.vue'

const props = defineProps<{
  visible: boolean
  projectId: number
  projectName: string
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const toast = useToast()

// Estados de carga
const loadingDocument = ref(false)
const loadingDocPreview = ref(false)
const loadingReport = ref(false)
const loadingCharacters = ref(false)
const loadingStyle = ref(false)
const loadingAlerts = ref(false)
const loadingPreview = ref(false)
const loadingCorrected = ref(false)
const loadingScrivener = ref(false)
const loadingEditorialExport = ref(false)
const showImportDialog = ref(false)

// Formatos seleccionados
const documentFormat = ref<'docx' | 'pdf'>('docx')
const reportFormat = ref<'markdown' | 'json'>('markdown')
const characterFormat = ref<'markdown' | 'json'>('markdown')
const styleFormat = ref<'markdown' | 'json' | 'pdf'>('markdown')
const alertFormat = ref<'json' | 'csv'>('json')

// Opciones de Scrivener
const scrivenerOptions = ref({
  includeCharacterNotes: true,
  includeAlertsAsNotes: true,
  includeEntityKeywords: true,
})

// Opciones de documento corregido
const correctionCategories = [
  { value: 'typography', label: 'Tipografía' },
  { value: 'grammar', label: 'Gramática' },
  { value: 'agreement', label: 'Concordancia' },
  { value: 'repetition', label: 'Repeticiones' },
  { value: 'terminology', label: 'Terminología' },
  { value: 'clarity', label: 'Claridad' },
  { value: 'regional', label: 'Regionalismos' },
]

const correctedOptions = ref({
  categories: ['typography', 'grammar', 'agreement', 'repetition', 'terminology', 'clarity', 'regional'],
  minConfidence: 50,
  asTrackChanges: true,
})

// Opciones de documento completo
const documentOptions = ref({
  includeCharacters: true,
  includeAlerts: true,
  includeTimeline: true,
  includeRelationships: true,
  includeStyleGuide: true,
  onlyMainCharacters: true,
  onlyOpenAlerts: true
})

// Preview del documento
const documentPreview = ref<{
  project_name: string
  description: string
  estimated_pages: number
  sections: {
    statistics: { included: boolean; word_count: number; chapter_count: number; entity_count: number; alert_count: number }
    characters: { included: boolean; count: number; names: string[] }
    alerts: { included: boolean; count: number; by_severity: { critical: number; error: number; warning: number; info: number } }
    timeline: { included: boolean; event_count: number }
    relationships: { included: boolean; count: number }
    style_guide: { included: boolean; available: boolean }
  }
} | null>(null)

// Style Guide preview
const showStylePreview = ref(false)
const stylePreview = ref<{
  project_name: string
  generated_date: string
  total_entities: number
  total_spelling_variants: number
  characters_count: number
  locations_count: number
  organizations_count: number
  has_style_analysis: boolean
  spelling_decisions_preview: Array<{ canonical_form: string; variants_count: number }>
  characters_preview: Array<{ name: string; importance: string; aliases_count: number }>
  style_summary: {
    dialogue_style: string
    number_style: string
    total_words: number
    total_sentences: number
    consistency_issues_count: number
    recommendations_count: number
  } | null
} | null>(null)

// Helper para labels de estilo de diálogos
const getDialogueStyleLabel = (style: string): string => {
  const labels: Record<string, string> = {
    'raya': 'Raya española',
    'guillemets': 'Comillas angulares',
    'quotes': 'Comillas inglesas',
    'mixed': 'Mixto'
  }
  return labels[style] || style
}

// Opciones de exportación
const characterOptions = ref({
  onlyMain: true,
  includeAttributes: true,
  includeMentions: true
})

const alertOptions = ref({
  includePending: true,
  includeResolved: false
})

const downloadFile = (content: string, filename: string, mimeType: string) => {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

const downloadBlob = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

const loadDocumentPreview = async () => {
  loadingDocPreview.value = true
  try {
    const params = new URLSearchParams({
      include_characters: documentOptions.value.includeCharacters.toString(),
      include_alerts: documentOptions.value.includeAlerts.toString(),
      include_timeline: documentOptions.value.includeTimeline.toString(),
      include_relationships: documentOptions.value.includeRelationships.toString(),
      include_style_guide: documentOptions.value.includeStyleGuide.toString(),
      only_main_characters: documentOptions.value.onlyMainCharacters.toString(),
      only_open_alerts: documentOptions.value.onlyOpenAlerts.toString()
    })

    const data = await api.getRaw<{ success: boolean; data?: any; error?: string }>(`/api/projects/${props.projectId}/export/document/preview?${params}`)

    if (data.success) {
      documentPreview.value = data.data
    } else {
      throw new Error(data.error || 'Error desconocido')
    }
  } catch (error) {
    console.error('Error loading document preview:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo cargar la vista previa del documento',
      life: 3000
    })
  } finally {
    loadingDocPreview.value = false
  }
}

const exportDocument = async () => {
  loadingDocument.value = true
  try {
    const params = new URLSearchParams({
      format: documentFormat.value,
      include_characters: documentOptions.value.includeCharacters.toString(),
      include_alerts: documentOptions.value.includeAlerts.toString(),
      include_timeline: documentOptions.value.includeTimeline.toString(),
      include_relationships: documentOptions.value.includeRelationships.toString(),
      include_style_guide: documentOptions.value.includeStyleGuide.toString(),
      only_main_characters: documentOptions.value.onlyMainCharacters.toString(),
      only_open_alerts: documentOptions.value.onlyOpenAlerts.toString()
    })

    const response = await fetch(apiUrl(`/api/projects/${props.projectId}/export/document?${params}`))

    if (!response.ok) {
      // Intentar leer el error como JSON
      const errorData = await response.json().catch(() => null)
      throw new Error(errorData?.error || 'Error al exportar documento')
    }

    // El servidor devuelve el archivo directamente como blob
    const blob = await response.blob()

    // Obtener nombre del archivo del header Content-Disposition
    const contentDisposition = response.headers.get('Content-Disposition')
    let filename = `informe_${props.projectName}.${documentFormat.value}`
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="?([^"]+)"?/)
      if (match) {
        filename = match[1]
      }
    }

    downloadBlob(blob, filename)

    toast.add({
      severity: 'success',
      summary: 'Exportacion exitosa',
      detail: `Documento exportado como ${filename}`,
      life: 3000
    })
  } catch (error) {
    console.error('Error exporting document:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error instanceof Error ? error.message : 'No se pudo exportar el documento',
      life: 5000
    })
  } finally {
    loadingDocument.value = false
  }
}

const exportReport = async () => {
  loadingReport.value = true
  try {
    const data = await api.getRaw<{ success: boolean; data?: any; error?: string }>(`/api/projects/${props.projectId}/export/report?format=${reportFormat.value}`)

    if (data.success) {
      const content = reportFormat.value === 'json'
        ? JSON.stringify(data.data, null, 2)
        : data.data.content

      const extension = reportFormat.value === 'json' ? 'json' : 'md'
      const mimeType = reportFormat.value === 'json' ? 'application/json' : 'text/markdown'
      const filename = `informe_${props.projectName}_${Date.now()}.${extension}`

      downloadFile(content, filename, mimeType)

      toast.add({
        severity: 'success',
        summary: 'Exportación exitosa',
        detail: `Informe exportado como ${filename}`,
        life: 3000
      })
    } else {
      throw new Error(data.error || 'Error desconocido')
    }
  } catch (error) {
    console.error('Error exporting report:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo exportar el informe',
      life: 3000
    })
  } finally {
    loadingReport.value = false
  }
}

const exportCharacterSheets = async () => {
  loadingCharacters.value = true
  try {
    const params = new URLSearchParams({
      format: characterFormat.value,
      only_main: characterOptions.value.onlyMain.toString(),
      include_attributes: characterOptions.value.includeAttributes.toString(),
      include_mentions: characterOptions.value.includeMentions.toString()
    })

    const data = await api.getRaw<{ success: boolean; data?: any; error?: string }>(`/api/projects/${props.projectId}/export/characters?${params}`)

    if (data.success) {
      const content = characterFormat.value === 'json'
        ? JSON.stringify(data.data, null, 2)
        : data.data.content

      const extension = characterFormat.value === 'json' ? 'json' : 'md'
      const mimeType = characterFormat.value === 'json' ? 'application/json' : 'text/markdown'
      const filename = `fichas_personajes_${props.projectName}_${Date.now()}.${extension}`

      downloadFile(content, filename, mimeType)

      toast.add({
        severity: 'success',
        summary: 'Exportación exitosa',
        detail: `Fichas exportadas como ${filename}`,
        life: 3000
      })
    } else {
      throw new Error(data.error || 'Error desconocido')
    }
  } catch (error) {
    console.error('Error exporting character sheets:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo exportar las fichas de personajes',
      life: 3000
    })
  } finally {
    loadingCharacters.value = false
  }
}

const loadStylePreview = async () => {
  loadingPreview.value = true
  try {
    const data = await api.getRaw<{ success: boolean; data?: any; error?: string }>(`/api/projects/${props.projectId}/style-guide?preview=true`)

    if (data.success && data.data.preview) {
      stylePreview.value = data.data.preview
      showStylePreview.value = true
    } else {
      throw new Error(data.error || 'Error desconocido')
    }
  } catch (error) {
    console.error('Error loading style preview:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo cargar el preview de la guía de estilo',
      life: 3000
    })
  } finally {
    loadingPreview.value = false
  }
}

const exportStyleGuide = async () => {
  loadingStyle.value = true
  try {
    const data = await api.getRaw<{ success: boolean; data?: any; error?: string }>(`/api/projects/${props.projectId}/style-guide?format=${styleFormat.value}`)

    if (data.success) {
      const format = data.data.format

      if (format === 'pdf') {
        // PDF viene como base64, decodificar y descargar
        const pdfContent = data.data.content
        const byteCharacters = atob(pdfContent)
        const byteNumbers = new Array(byteCharacters.length)
        for (let i = 0; i < byteCharacters.length; i++) {
          byteNumbers[i] = byteCharacters.charCodeAt(i)
        }
        const byteArray = new Uint8Array(byteNumbers)
        const blob = new Blob([byteArray], { type: 'application/pdf' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `guia_estilo_${props.projectName}_${Date.now()}.pdf`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)

        toast.add({
          severity: 'success',
          summary: 'Exportación exitosa',
          detail: `Guía de estilo exportada como PDF`,
          life: 3000
        })
      } else {
        // Markdown o JSON
        const content = format === 'markdown'
          ? data.data.content
          : JSON.stringify(data.data.content, null, 2)

        const extension = format === 'markdown' ? 'md' : 'json'
        const mimeType = format === 'markdown' ? 'text/markdown' : 'application/json'
        const filename = `guia_estilo_${props.projectName}_${Date.now()}.${extension}`

        downloadFile(content, filename, mimeType)

        toast.add({
          severity: 'success',
          summary: 'Exportación exitosa',
          detail: `Guía de estilo exportada como ${filename}`,
          life: 3000
        })
      }
    } else {
      // Manejar caso donde PDF no está disponible pero hay fallback
      if (data.data?.fallback_format === 'markdown' && data.data?.content) {
        toast.add({
          severity: 'warn',
          summary: 'PDF no disponible',
          detail: 'Se exportará en formato Markdown. ' + (data.error || ''),
          life: 5000
        })

        const filename = `guia_estilo_${props.projectName}_${Date.now()}.md`
        downloadFile(data.data.content, filename, 'text/markdown')
      } else {
        throw new Error(data.error || 'Error desconocido')
      }
    }
  } catch (error) {
    console.error('Error exporting style guide:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo exportar la guía de estilo',
      life: 3000
    })
  } finally {
    loadingStyle.value = false
  }
}

const exportAlerts = async () => {
  loadingAlerts.value = true
  try {
    const params = new URLSearchParams({
      format: alertFormat.value,
      include_pending: alertOptions.value.includePending.toString(),
      include_resolved: alertOptions.value.includeResolved.toString()
    })

    const data = await api.getRaw<{ success: boolean; data?: any; error?: string }>(`/api/projects/${props.projectId}/export/alerts?${params}`)

    if (data.success) {
      const content = alertFormat.value === 'json'
        ? JSON.stringify(data.data, null, 2)
        : data.data.content

      const extension = alertFormat.value
      const mimeType = alertFormat.value === 'json' ? 'application/json' : 'text/csv'
      const filename = `alertas_${props.projectName}_${Date.now()}.${extension}`

      downloadFile(content, filename, mimeType)

      toast.add({
        severity: 'success',
        summary: 'Exportación exitosa',
        detail: `Alertas exportadas como ${filename}`,
        life: 3000
      })
    } else {
      throw new Error(data.error || 'Error desconocido')
    }
  } catch (error) {
    console.error('Error exporting alerts:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo exportar las alertas',
      life: 3000
    })
  } finally {
    loadingAlerts.value = false
  }
}

async function exportCorrected() {
  loadingCorrected.value = true
  try {
    const params = new URLSearchParams({
      min_confidence: (correctedOptions.value.minConfidence / 100).toString(),
      as_track_changes: correctedOptions.value.asTrackChanges.toString(),
    })
    if (correctedOptions.value.categories.length < correctionCategories.length) {
      params.set('categories', correctedOptions.value.categories.join(','))
    }

    const response = await fetch(
      apiUrl(`/api/projects/${props.projectId}/export/corrected?${params}`)
    )

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.error || `HTTP ${response.status}`)
    }

    const blob = await response.blob()
    const contentDisposition = response.headers.get('Content-Disposition')
    let filename = `${props.projectName}_corregido.docx`
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="?([^"]+)"?/)
      if (match) filename = match[1]
    }

    downloadBlob(blob, filename)

    toast.add({
      severity: 'success',
      summary: 'Exportación exitosa',
      detail: `Descargado: ${filename}`,
      life: 3000,
    })
  } catch (error) {
    console.error('Error exporting corrected document:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error instanceof Error ? error.message : 'No se pudo exportar el documento corregido',
      life: 5000,
    })
  } finally {
    loadingCorrected.value = false
  }
}

async function exportScrivener() {
  loadingScrivener.value = true
  try {
    const params = new URLSearchParams({
      include_character_notes: String(scrivenerOptions.value.includeCharacterNotes),
      include_alerts_as_notes: String(scrivenerOptions.value.includeAlertsAsNotes),
      include_entity_keywords: String(scrivenerOptions.value.includeEntityKeywords),
    })

    const response = await fetch(
      apiUrl(`/api/projects/${props.projectId}/export/scrivener?${params}`)
    )

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const blob = await response.blob()
    const safeName = props.projectName.replace(/[^a-zA-Z0-9 _.-]/g, '').trim() || 'Proyecto'
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${safeName}.scriv.zip`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    toast.add({
      severity: 'success',
      summary: 'Exportación exitosa',
      detail: `Descargado: ${safeName}.scriv.zip`,
      life: 3000,
    })
  } catch (error) {
    console.error('Error exporting to Scrivener:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo exportar a Scrivener',
      life: 3000,
    })
  } finally {
    loadingScrivener.value = false
  }
}

async function exportEditorialWork() {
  loadingEditorialExport.value = true
  try {
    const response = await fetch(
      apiUrl(`/api/projects/${props.projectId}/export-work`),
      { method: 'POST' }
    )

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.error || `HTTP ${response.status}`)
    }

    const blob = await response.blob()
    const contentDisposition = response.headers.get('Content-Disposition')
    let filename = `trabajo_editorial_${props.projectName}.narrassist`
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="?([^"]+)"?/)
      if (match) filename = match[1]
    }

    downloadBlob(blob, filename)

    toast.add({
      severity: 'success',
      summary: 'Exportacion exitosa',
      detail: `Trabajo editorial exportado: ${filename}`,
      life: 3000,
    })
  } catch (error) {
    console.error('Error exporting editorial work:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error instanceof Error ? error.message : 'No se pudo exportar el trabajo editorial',
      life: 5000,
    })
  } finally {
    loadingEditorialExport.value = false
  }
}

function onWorkImported() {
  toast.add({
    severity: 'success',
    summary: 'Importacion completada',
    detail: 'El trabajo editorial se ha importado correctamente',
    life: 3000,
  })
}
</script>

<style scoped>
.export-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.export-option {
  border: 1px solid var(--surface-border);
}

.export-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.1rem;
}

.export-title i {
  color: var(--primary-color);
}

.export-description {
  color: var(--text-color-secondary);
  font-size: 0.95rem;
  margin-bottom: 1rem;
}

.format-selector {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.format-selector label {
  font-weight: 500;
  min-width: 70px;
}

.format-buttons {
  display: flex;
  gap: 0.5rem;
}

.export-checkboxes {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.checkbox-item label {
  cursor: pointer;
  user-select: none;
}

.export-button {
  width: 100%;
}

/* Corrected document options */
.corrected-options {
  margin-bottom: 1rem;
}

.confidence-slider {
  margin-bottom: 1rem;
}

.confidence-slider label {
  display: block;
  font-size: 0.9rem;
  margin-bottom: 0.5rem;
}

/* Style Guide Preview */
.style-guide-card .export-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.preview-btn {
  margin-left: auto;
}

.style-preview {
  background: var(--surface-50);
  border: 1px solid var(--surface-border);
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.preview-title {
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--text-color);
}

.preview-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.preview-stat {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--text-color-secondary);
}

.preview-stat i {
  color: var(--primary-color);
  font-size: 0.9rem;
}

.preview-section {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--surface-border);
}

.preview-section-title {
  display: block;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-color-secondary);
  margin-bottom: 0.5rem;
}

.preview-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.preview-style-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.85rem;
}

.preview-style-info span {
  color: var(--text-color-secondary);
}

.issues-warning {
  color: var(--orange-500) !important;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.issues-warning i {
  font-size: 0.85rem;
}

/* Dark mode adjustments */
.dark .style-preview {
  background: var(--surface-700);
}

/* Document Export Card */
.document-export-card {
  background: linear-gradient(135deg, var(--surface-50) 0%, var(--primary-50) 100%);
  border: 2px solid var(--primary-200);
}

.dark .document-export-card {
  background: linear-gradient(135deg, var(--surface-700) 0%, var(--surface-800) 100%);
  border: 2px solid var(--primary-700);
}

.new-tag {
  margin-left: auto;
  font-size: 0.7rem;
}

.sections-selector {
  margin-bottom: 1rem;
}

.sections-label {
  display: block;
  font-weight: 500;
  margin-bottom: 0.5rem;
  color: var(--text-color);
}

.sections-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem;
}

.sections-grid .checkbox-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.sections-grid .checkbox-item label {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  cursor: pointer;
  font-size: 0.9rem;
}

.sections-grid .checkbox-item label i {
  color: var(--primary-color);
  font-size: 0.85rem;
}

.filter-options {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
  padding: 0.75rem;
  background: var(--surface-100);
  border-radius: 6px;
}

.dark .filter-options {
  background: var(--surface-800);
}

.document-preview {
  background: var(--surface-100);
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  padding: 0.75rem;
  margin-bottom: 1rem;
}

.dark .document-preview {
  background: var(--surface-800);
}

.preview-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.preview-row:last-child {
  margin-bottom: 0;
}

.preview-label {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  min-width: 120px;
}

.preview-content-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.export-actions {
  display: flex;
  gap: 0.75rem;
}

.flex-grow-1 {
  flex-grow: 1;
}

/* Editorial Work Card */
.editorial-work-card {
  border: 2px solid var(--orange-200);
  background: linear-gradient(135deg, var(--surface-50) 0%, var(--orange-50) 100%);
}

.dark .editorial-work-card {
  border: 2px solid var(--orange-700);
  background: linear-gradient(135deg, var(--surface-700) 0%, var(--surface-800) 100%);
}

.editorial-work-actions {
  display: flex;
  gap: 0.75rem;
}
</style>
