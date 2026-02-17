<template>
  <Dialog
    v-model:visible="visible"
    header="Exportar Eventos"
    :style="{ width: '500px' }"
    modal
  >
    <div class="export-form">
      <!-- Formato -->
      <div class="field">
        <label>Formato</label>
        <SelectButton
          v-model="exportFormat"
          :options="formatOptions"
          option-label="label"
          option-value="value"
        />
        <small v-if="exportFormat === 'csv'" class="format-hint">
          <i class="pi pi-info-circle"></i>
          CSV optimizado para Excel en Windows (UTF-8 con BOM)
        </small>
      </div>

      <!-- Filtros -->
      <div class="field">
        <label>Tier</label>
        <Select
          v-model="tierFilter"
          :options="tierOptions"
          option-label="label"
          option-value="value"
          placeholder="Todos los tiers"
          show-clear
        />
      </div>

      <div class="field">
        <label>Tipos de eventos (opcional)</label>
        <MultiSelect
          v-model="selectedEventTypes"
          :options="eventTypeOptions"
          option-label="label"
          option-value="value"
          placeholder="Todos los tipos"
          display="chip"
          :max-selected-labels="3"
        />
      </div>

      <div class="field">
        <label class="checkbox-label">
          <Checkbox v-model="criticalOnly" binary />
          <span>Solo eventos críticos sin resolver</span>
        </label>
      </div>

      <!-- Rango de capítulos -->
      <div class="field">
        <label>Rango de capítulos (opcional)</label>
        <div class="chapter-range">
          <InputNumber v-model="chapterStart" placeholder="Desde" :min="1" />
          <span>-</span>
          <InputNumber v-model="chapterEnd" placeholder="Hasta" :min="1" />
        </div>
      </div>
    </div>

    <template #footer>
      <Button
        label="Exportar"
        icon="pi pi-download"
        :loading="exporting"
        @click="handleExport"
      />
      <Button
        label="Cancelar"
        text
        @click="visible = false"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import MultiSelect from 'primevue/multiselect'
import Checkbox from 'primevue/checkbox'
import InputNumber from 'primevue/inputnumber'
import { useToast } from 'primevue/usetoast'

const props = defineProps<{
  projectId: number
}>()

const visible = defineModel<boolean>('visible', { required: true })
const toast = useToast()

const exportFormat = ref<'csv' | 'json'>('csv')
const tierFilter = ref<string | null>(null)
const selectedEventTypes = ref<string[]>([])
const criticalOnly = ref(false)
const chapterStart = ref<number | null>(null)
const chapterEnd = ref<number | null>(null)
const exporting = ref(false)

const formatOptions = [
  { label: 'CSV (Excel)', value: 'csv' },
  { label: 'JSON', value: 'json' }
]

const tierOptions = [
  { label: 'Tier 1 (Críticos)', value: '1' },
  { label: 'Tier 2 (Enriquecimiento)', value: '2' },
  { label: 'Tier 3 (Género)', value: '3' }
]

const eventTypeOptions = [
  { label: 'Promesas', value: 'promise' },
  { label: 'Promesas rotas', value: 'broken_promise' },
  { label: 'Heridas', value: 'injury' },
  { label: 'Curaciones', value: 'healing' },
  { label: 'Adquisiciones', value: 'acquisition' },
  { label: 'Pérdidas', value: 'loss' },
  { label: 'Confesiones', value: 'confession' },
  { label: 'Mentiras', value: 'lie' },
  { label: 'Flashback inicio', value: 'flashback_start' },
  { label: 'Flashback fin', value: 'flashback_end' },
  { label: 'Salto temporal', value: 'time_skip' },
  { label: 'Traiciones', value: 'betrayal' },
  { label: 'Alianzas', value: 'alliance' },
  { label: 'Revelaciones', value: 'revelation' },
  { label: 'Decisiones', value: 'decision' },
  { label: 'Primer encuentro', value: 'first_meeting' },
  { label: 'Conflictos', value: 'conflict_start' },
  { label: 'Muertes', value: 'death' }
]

async function handleExport() {
  exporting.value = true
  try {
    const params = new URLSearchParams()
    params.set('format', exportFormat.value)
    if (tierFilter.value) params.set('tier_filter', tierFilter.value)
    if (selectedEventTypes.value.length > 0) {
      params.set('event_types', selectedEventTypes.value.join(','))
    }
    if (criticalOnly.value) params.set('critical_only', 'true')
    if (chapterStart.value) params.set('chapter_start', chapterStart.value.toString())
    if (chapterEnd.value) params.set('chapter_end', chapterEnd.value.toString())

    const url = `/api/projects/${props.projectId}/events/export?${params}`

    const response = await fetch(url)

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Error desconocido' }))
      throw new Error(errorData.detail || `HTTP ${response.status}`)
    }

    if (exportFormat.value === 'csv') {
      // Download CSV
      const blob = await response.blob()
      const downloadUrl = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = downloadUrl
      a.download = `eventos_proyecto_${props.projectId}.csv`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(downloadUrl)
    } else {
      // Download JSON
      const data = await response.json()
      const blob = new Blob([JSON.stringify(data.data, null, 2)], {
        type: 'application/json'
      })
      const downloadUrl = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = downloadUrl
      a.download = `eventos_proyecto_${props.projectId}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(downloadUrl)
    }

    toast.add({
      severity: 'success',
      summary: 'Eventos exportados',
      detail: `Se ha descargado el archivo ${exportFormat.value.toUpperCase()}`,
      life: 3000
    })

    visible.value = false
  } catch (error) {
    console.error('Error exporting events:', error)
    toast.add({
      severity: 'error',
      summary: 'Error al exportar',
      detail: error instanceof Error ? error.message : 'Error desconocido',
      life: 5000
    })
  } finally {
    exporting.value = false
  }
}
</script>

<style scoped>
.export-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--text-color);
}

.format-hint {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  color: var(--text-color-secondary);
  font-size: 0.8125rem;
  margin-top: 0.25rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-weight: normal;
}

.chapter-range {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.chapter-range span {
  font-weight: 600;
  color: var(--text-color-secondary);
}
</style>
