<template>
  <Dialog
    :visible="visible"
    modal
    :header="'Exportar - ' + projectName"
    :style="{ width: '600px' }"
    @update:visible="emit('update:visible', $event)"
  >
    <div class="export-dialog-content">
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
                @click="reportFormat = 'markdown'"
                size="small"
              />
              <Button
                label="JSON"
                :outlined="reportFormat !== 'json'"
                @click="reportFormat = 'json'"
                size="small"
              />
            </div>
          </div>

          <Button
            label="Exportar informe"
            icon="pi pi-download"
            @click="exportReport"
            :loading="loadingReport"
            class="export-button"
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
            Fichas detalladas de los personajes principales con atributos y menciones.
          </p>

          <div class="export-checkboxes">
            <div class="checkbox-item">
              <Checkbox v-model="characterOptions.onlyMain" :binary="true" inputId="onlyMain" />
              <label for="onlyMain">Solo personajes principales</label>
            </div>
            <div class="checkbox-item">
              <Checkbox v-model="characterOptions.includeAttributes" :binary="true" inputId="includeAttr" />
              <label for="includeAttr">Incluir atributos</label>
            </div>
            <div class="checkbox-item">
              <Checkbox v-model="characterOptions.includeMentions" :binary="true" inputId="includeMent" />
              <label for="includeMent">Incluir menciones destacadas</label>
            </div>
          </div>

          <div class="format-selector">
            <label>Formato:</label>
            <div class="format-buttons">
              <Button
                label="Markdown"
                :outlined="characterFormat !== 'markdown'"
                @click="characterFormat = 'markdown'"
                size="small"
              />
              <Button
                label="JSON"
                :outlined="characterFormat !== 'json'"
                @click="characterFormat = 'json'"
                size="small"
              />
            </div>
          </div>

          <Button
            label="Exportar fichas"
            icon="pi pi-download"
            @click="exportCharacterSheets"
            :loading="loadingCharacters"
            class="export-button"
          />
        </template>
      </Card>

      <!-- Hoja de Estilo -->
      <Card class="export-option">
        <template #title>
          <div class="export-title">
            <i class="pi pi-book"></i>
            <span>Hoja de Estilo</span>
          </div>
        </template>
        <template #content>
          <p class="export-description">
            Decisiones editoriales, grafías preferidas y guía de estilo del manuscrito.
          </p>

          <div class="format-selector">
            <label>Formato:</label>
            <div class="format-buttons">
              <Button
                label="Markdown"
                :outlined="styleFormat !== 'markdown'"
                @click="styleFormat = 'markdown'"
                size="small"
              />
            </div>
          </div>

          <Button
            label="Exportar hoja de estilo"
            icon="pi pi-download"
            @click="exportStyleGuide"
            :loading="loadingStyle"
            class="export-button"
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
              <Checkbox v-model="alertOptions.includePending" :binary="true" inputId="pendingAlerts" />
              <label for="pendingAlerts">Incluir pendientes</label>
            </div>
            <div class="checkbox-item">
              <Checkbox v-model="alertOptions.includeResolved" :binary="true" inputId="resolvedAlerts" />
              <label for="resolvedAlerts">Incluir resueltas</label>
            </div>
          </div>

          <div class="format-selector">
            <label>Formato:</label>
            <div class="format-buttons">
              <Button
                label="JSON"
                :outlined="alertFormat !== 'json'"
                @click="alertFormat = 'json'"
                size="small"
              />
              <Button
                label="CSV"
                :outlined="alertFormat !== 'csv'"
                @click="alertFormat = 'csv'"
                size="small"
              />
            </div>
          </div>

          <Button
            label="Exportar alertas"
            icon="pi pi-download"
            @click="exportAlerts"
            :loading="loadingAlerts"
            class="export-button"
          />
        </template>
      </Card>
    </div>

    <template #footer>
      <Button label="Cerrar" severity="secondary" @click="() => emit('update:visible', false)" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Dialog from 'primevue/dialog'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import { useToast } from 'primevue/usetoast'

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
const loadingReport = ref(false)
const loadingCharacters = ref(false)
const loadingStyle = ref(false)
const loadingAlerts = ref(false)

// Formatos seleccionados
const reportFormat = ref<'markdown' | 'json'>('markdown')
const characterFormat = ref<'markdown' | 'json'>('markdown')
const styleFormat = ref<'markdown'>('markdown')
const alertFormat = ref<'json' | 'csv'>('json')

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

const exportReport = async () => {
  loadingReport.value = true
  try {
    const response = await fetch(`http://localhost:8008/api/projects/${props.projectId}/export/report?format=${reportFormat.value}`)

    if (!response.ok) {
      throw new Error('Error al exportar informe')
    }

    const data = await response.json()

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

    const response = await fetch(`http://localhost:8008/api/projects/${props.projectId}/export/characters?${params}`)

    if (!response.ok) {
      throw new Error('Error al exportar fichas')
    }

    const data = await response.json()

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

const exportStyleGuide = async () => {
  loadingStyle.value = true
  try {
    const response = await fetch(`http://localhost:8008/api/projects/${props.projectId}/export/style-guide`)

    if (!response.ok) {
      throw new Error('Error al exportar hoja de estilo')
    }

    const data = await response.json()

    if (data.success) {
      const content = data.data.content
      const filename = `hoja_estilo_${props.projectName}_${Date.now()}.md`

      downloadFile(content, filename, 'text/markdown')

      toast.add({
        severity: 'success',
        summary: 'Exportación exitosa',
        detail: `Hoja de estilo exportada como ${filename}`,
        life: 3000
      })
    } else {
      throw new Error(data.error || 'Error desconocido')
    }
  } catch (error) {
    console.error('Error exporting style guide:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo exportar la hoja de estilo',
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

    const response = await fetch(`http://localhost:8008/api/projects/${props.projectId}/export/alerts?${params}`)

    if (!response.ok) {
      throw new Error('Error al exportar alertas')
    }

    const data = await response.json()

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
</style>
