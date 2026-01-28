<script setup lang="ts">
/**
 * CorrectionConfigPanel - Panel de configuracion de correcciones
 *
 * Permite configurar los detectores de correcciones para el proyecto:
 * - Preset rapido (novela, tecnico, juridico, etc.)
 * - Ajustes de tipografia (guiones, comillas)
 * - Sensibilidad de repeticiones
 * - Region del espanol
 * - Detectores habilitados/deshabilitados
 */

import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Select from 'primevue/select'
import MultiSelect from 'primevue/multiselect'
import ToggleSwitch from 'primevue/toggleswitch'
import Slider from 'primevue/slider'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import Divider from 'primevue/divider'
import SelectButton from 'primevue/selectbutton'
import { useToast } from 'primevue/usetoast'

const props = defineProps<{
  projectId: number
}>()

const emit = defineEmits<{
  (e: 'config-changed', config: CorrectionConfig): void
}>()

const toast = useToast()

// Types
interface CorrectionConfig {
  profile: {
    document_field: string
    secondary_fields: string[]
    register: string
    audience: string
    region: string
    allow_mixed_register: boolean
  }
  typography: {
    enabled: boolean
    dialogue_dash: string
    quote_style: string
    check_spacing: boolean
    check_ellipsis: boolean
  }
  repetition: {
    enabled: boolean
    min_distance: number
    sensitivity: string
    ignore_dialogue: boolean
  }
  agreement: {
    enabled: boolean
    check_gender: boolean
    check_number: boolean
  }
  regional: {
    enabled: boolean
    target_region: string
    detect_mixed_variants: boolean
  }
  terminology: {
    enabled: boolean
  }
  use_llm_review: boolean
}

interface Preset {
  id: string
  name: string
  description: string
  config: CorrectionConfig
}

interface DetectionResult {
  detected: boolean
  suggested_preset: string
  suggested_config: CorrectionConfig
  detection: {
    field: string
    field_label: string
    register: string
    region: string
    has_dialogues: boolean
  }
  reasons: string[]
  confidence: number
}

// Default config - used before API response
const defaultConfig: CorrectionConfig = {
  profile: {
    document_field: 'literary',
    secondary_fields: [],
    register: 'neutral',
    audience: 'general',
    region: 'es_ES',
    allow_mixed_register: false
  },
  typography: {
    enabled: true,
    dialogue_dash: 'em',
    quote_style: 'angular',
    check_spacing: true,
    check_ellipsis: true
  },
  repetition: {
    enabled: true,
    min_distance: 50,
    sensitivity: 'medium',
    ignore_dialogue: true
  },
  agreement: {
    enabled: true,
    check_gender: true,
    check_number: true
  },
  regional: {
    enabled: true,
    target_region: 'es_ES',
    detect_mixed_variants: true
  },
  terminology: {
    enabled: true
  },
  use_llm_review: false
}

// State
const loading = ref(false)
const saving = ref(false)
const detecting = ref(false)
const hasCustomConfig = ref(false)
const config = ref<CorrectionConfig>({ ...defaultConfig })
const presets = ref<Preset[]>([])
const selectedPreset = ref<string>('default')
const detectionResult = ref<DetectionResult | null>(null)
const showDetectionBanner = ref(false)

// Options
const regionOptions = [
  { value: 'es_ES', label: 'España' },
  { value: 'es_MX', label: 'México' },
  { value: 'es_AR', label: 'Argentina' },
  { value: 'es_CO', label: 'Colombia' },
]

const fieldOptions = [
  { value: 'legal', label: 'Jurídico' },
  { value: 'medical', label: 'Médico' },
  { value: 'technical', label: 'Técnico' },
  { value: 'academic', label: 'Académico' },
  { value: 'business', label: 'Empresarial' },
  { value: 'journalistic', label: 'Periodístico' },
  { value: 'culinary', label: 'Gastronómico' },
]

const dashOptions = [
  { value: 'em', label: 'Raya (—)' },
  { value: 'en', label: 'Semiraya (–)' },
  { value: 'hyphen', label: 'Guión (-)' },
]

const quoteOptions = [
  { value: 'angular', label: 'Latinas « »' },
  { value: 'curly', label: 'Inglesas " "' },
  { value: 'straight', label: 'Rectas " "' },
]

const sensitivityOptions = [
  { value: 'low', label: 'Baja' },
  { value: 'medium', label: 'Media' },
  { value: 'high', label: 'Alta' },
]

// Computed
const isModified = computed(() => {
  if (!config.value || !selectedPreset.value) return false
  const preset = presets.value.find(p => p.id === selectedPreset.value)
  if (!preset) return false
  return JSON.stringify(config.value) !== JSON.stringify(preset.config)
})

const distanceLabel = computed(() => {
  if (!config.value) return ''
  const dist = config.value.repetition.min_distance
  if (dist <= 30) return 'Muy estricto'
  if (dist <= 50) return 'Estricto'
  if (dist <= 80) return 'Moderado'
  if (dist <= 120) return 'Permisivo'
  return 'Muy permisivo'
})

// Load data
onMounted(async () => {
  await Promise.all([
    loadPresets(),
    loadConfig(),
  ])
  // Auto-detect if no custom config
  if (!hasCustomConfig.value) {
    await detectProfile()
  }
})

watch(() => props.projectId, async () => {
  await loadConfig()
})

async function loadPresets() {
  try {
    const response = await fetch('http://localhost:8008/api/correction-presets')
    const data = await response.json()
    if (data.success) {
      presets.value = data.data.presets
    }
  } catch (error) {
    console.error('Error loading presets:', error)
  }
}

async function loadConfig() {
  loading.value = true
  try {
    const response = await fetch(`http://localhost:8008/api/projects/${props.projectId}/correction-config`)
    const data = await response.json()
    if (data.success && data.data.config) {
      // Merge with defaults to ensure all fields exist
      config.value = {
        ...defaultConfig,
        ...data.data.config,
        profile: { ...defaultConfig.profile, ...data.data.config.profile },
        typography: { ...defaultConfig.typography, ...data.data.config.typography },
        repetition: { ...defaultConfig.repetition, ...data.data.config.repetition },
        agreement: { ...defaultConfig.agreement, ...data.data.config.agreement },
        regional: { ...defaultConfig.regional, ...data.data.config.regional },
        terminology: { ...defaultConfig.terminology, ...data.data.config.terminology },
      }
      hasCustomConfig.value = data.data.hasCustomConfig ?? false
      // Load saved preset selection
      if (data.data.selectedPreset) {
        selectedPreset.value = data.data.selectedPreset
      }
    }
  } catch (error) {
    console.error('Error loading config:', error)
    // Keep default config on error
  } finally {
    loading.value = false
  }
}

async function detectProfile() {
  detecting.value = true
  try {
    const response = await fetch(`http://localhost:8008/api/projects/${props.projectId}/correction-config/detect`, {
      method: 'POST'
    })
    const data = await response.json()
    if (data.success && data.data.detected) {
      detectionResult.value = data.data
      showDetectionBanner.value = true
    }
  } catch (error) {
    console.error('Error detecting profile:', error)
  } finally {
    detecting.value = false
  }
}

async function applyDetectedConfig() {
  if (!detectionResult.value) return

  config.value = detectionResult.value.suggested_config
  selectedPreset.value = detectionResult.value.suggested_preset
  showDetectionBanner.value = false

  await saveConfig()

  toast.add({
    severity: 'success',
    summary: 'Configuración aplicada',
    detail: `Se aplicó el perfil "${getPresetLabel(selectedPreset.value)}"`,
    life: 3000
  })
}

function dismissDetection() {
  showDetectionBanner.value = false
}

async function applyPreset(presetId: string) {
  const preset = presets.value.find(p => p.id === presetId)
  if (!preset) return

  selectedPreset.value = presetId
  config.value = JSON.parse(JSON.stringify(preset.config))

  await saveConfig()
}

async function saveConfig() {
  if (!config.value) return

  saving.value = true
  try {
    const response = await fetch(`http://localhost:8008/api/projects/${props.projectId}/correction-config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        config: config.value,
        selectedPreset: selectedPreset.value
      })
    })
    const data = await response.json()
    if (data.success) {
      hasCustomConfig.value = true
      emit('config-changed', config.value)
      toast.add({
        severity: 'success',
        summary: 'Guardado',
        detail: 'Configuración de correcciones guardada',
        life: 2000
      })
    }
  } catch (error) {
    console.error('Error saving config:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo guardar la configuración',
      life: 3000
    })
  } finally {
    saving.value = false
  }
}

async function resetConfig() {
  try {
    const response = await fetch(`http://localhost:8008/api/projects/${props.projectId}/correction-config`, {
      method: 'DELETE'
    })
    const data = await response.json()
    if (data.success) {
      config.value = data.data.config
      hasCustomConfig.value = false
      selectedPreset.value = 'default'
      toast.add({
        severity: 'info',
        summary: 'Configuración restablecida',
        detail: 'Se restauró la configuración por defecto',
        life: 3000
      })
    }
  } catch (error) {
    console.error('Error resetting config:', error)
  }
}

function getPresetLabel(presetId: string): string {
  const preset = presets.value.find(p => p.id === presetId)
  return preset?.name || presetId
}

function getSensitivityColor(sensitivity: string): 'success' | 'info' | 'warn' {
  if (sensitivity === 'low') return 'success'
  if (sensitivity === 'medium') return 'info'
  return 'warn'
}

// Debounced auto-save with flush on unmount
let saveTimeout: ReturnType<typeof setTimeout> | null = null
let hasPendingChanges = false

function scheduleAutoSave() {
  hasPendingChanges = true
  if (saveTimeout) clearTimeout(saveTimeout)
  saveTimeout = setTimeout(() => {
    hasPendingChanges = false
    saveConfig()
  }, 1000)
}

// Flush pending saves when component unmounts (e.g., user changes tab)
onBeforeUnmount(() => {
  if (saveTimeout) {
    clearTimeout(saveTimeout)
    saveTimeout = null
  }
  if (hasPendingChanges) {
    // Save immediately without waiting
    saveConfig()
  }
})
</script>

<template>
  <div class="correction-config-panel">
    <!-- Detection Banner -->
    <Message
      v-if="showDetectionBanner && detectionResult"
      severity="info"
      :closable="true"
      class="detection-banner"
      @close="dismissDetection"
    >
      <div class="detection-content">
        <div class="detection-info">
          <i class="pi pi-sparkles"></i>
          <div>
            <strong>Perfil detectado: {{ detectionResult.detection.field_label }}</strong>
            <p>{{ detectionResult.reasons.join(' - ') }}</p>
          </div>
        </div>
        <Button
          label="Aplicar"
          icon="pi pi-check"
          size="small"
          @click="applyDetectedConfig"
        />
      </div>
    </Message>

    <!-- Preset Selection -->
    <Card class="preset-card">
      <template #title>
        <div class="card-header">
          <span><i class="pi pi-sliders-h"></i> Perfil de corrección</span>
          <Button
            v-if="hasCustomConfig"
            label="Restablecer"
            icon="pi pi-refresh"
            text
            size="small"
            @click="resetConfig"
          />
        </div>
      </template>
      <template #content>
        <div class="preset-grid">
          <button
            v-for="preset in presets"
            :key="preset.id"
            class="preset-btn"
            :class="{ active: selectedPreset === preset.id }"
            @click="applyPreset(preset.id)"
          >
            <span class="preset-name">{{ preset.name }}</span>
            <span class="preset-desc">{{ preset.description }}</span>
          </button>
        </div>
        <Tag v-if="isModified" severity="warn" class="modified-tag">
          <i class="pi pi-pencil"></i> Personalizado
        </Tag>
      </template>
    </Card>

    <!-- Detailed Config -->
    <div class="config-sections" :class="{ 'loading-overlay': loading }">
      <!-- Typography -->
      <Card class="config-card">
        <template #title>
          <div class="card-header">
            <span><i class="pi pi-align-left"></i> Tipografía</span>
            <ToggleSwitch v-model="config.typography.enabled" @change="scheduleAutoSave" />
          </div>
        </template>
        <template v-if="config.typography.enabled" #content>
          <div class="config-row">
            <label>Guiones de diálogo</label>
            <SelectButton
              v-model="config.typography.dialogue_dash"
              :options="dashOptions"
              option-label="label"
              option-value="value"
              @change="scheduleAutoSave"
            />
          </div>
          <div class="config-row">
            <label>Estilo de comillas</label>
            <SelectButton
              v-model="config.typography.quote_style"
              :options="quoteOptions"
              option-label="label"
              option-value="value"
              @change="scheduleAutoSave"
            />
          </div>
        </template>
      </Card>

      <!-- Repetitions -->
      <Card class="config-card">
        <template #title>
          <div class="card-header">
            <span><i class="pi pi-copy"></i> Repeticiones</span>
            <ToggleSwitch v-model="config.repetition.enabled" @change="scheduleAutoSave" />
          </div>
        </template>
        <template v-if="config.repetition.enabled" #content>
          <div class="config-row">
            <label>Sensibilidad</label>
            <SelectButton
              v-model="config.repetition.sensitivity"
              :options="sensitivityOptions"
              option-label="label"
              option-value="value"
              @change="scheduleAutoSave"
            />
          </div>
          <div class="config-row">
            <label>
              Distancia mínima: {{ config.repetition.min_distance }} palabras
              <Tag :severity="getSensitivityColor(config.repetition.sensitivity)" size="small">
                {{ distanceLabel }}
              </Tag>
            </label>
            <Slider
              v-model="config.repetition.min_distance"
              :min="20"
              :max="200"
              :step="10"
              class="distance-slider"
              @change="scheduleAutoSave"
            />
          </div>
          <div class="config-row inline">
            <ToggleSwitch v-model="config.repetition.ignore_dialogue" @change="scheduleAutoSave" />
            <label>Ignorar repeticiones en diálogos</label>
          </div>
        </template>
      </Card>

      <!-- Regional -->
      <Card class="config-card">
        <template #title>
          <div class="card-header">
            <span><i class="pi pi-globe"></i> Vocabulario regional</span>
            <ToggleSwitch v-model="config.regional.enabled" @change="scheduleAutoSave" />
          </div>
        </template>
        <template v-if="config.regional.enabled" #content>
          <div class="config-row">
            <label>Variante del español</label>
            <Select
              v-model="config.regional.target_region"
              :options="regionOptions"
              option-label="label"
              option-value="value"
              @change="scheduleAutoSave"
            />
          </div>
          <div class="config-row inline">
            <ToggleSwitch v-model="config.regional.detect_mixed_variants" @change="scheduleAutoSave" />
            <label>Detectar mezcla de variantes</label>
          </div>
        </template>
      </Card>

      <!-- Specialized Fields -->
      <Card class="config-card">
        <template #title>
          <div class="card-header">
            <span><i class="pi pi-briefcase"></i> Campos especializados</span>
          </div>
        </template>
        <template #content>
          <div class="config-row">
            <label>Campos adicionales del documento</label>
            <p class="field-help">
              Selecciona campos adicionales si el texto mezcla terminología de diferentes áreas
              (ej: un texto jurídico sobre negligencia médica).
            </p>
            <MultiSelect
              v-model="config.profile.secondary_fields"
              :options="fieldOptions"
              option-label="label"
              option-value="value"
              placeholder="Seleccionar campos..."
              display="chip"
              class="field-multiselect"
              @change="scheduleAutoSave"
            />
          </div>
        </template>
      </Card>

      <!-- Other detectors -->
      <Card class="config-card">
        <template #title>
          <span><i class="pi pi-list-check"></i> Otros detectores</span>
        </template>
        <template #content>
          <div class="detector-toggles">
            <div class="detector-toggle">
              <ToggleSwitch v-model="config.agreement.enabled" @change="scheduleAutoSave" />
              <div class="detector-info">
                <label>Concordancia gramatical</label>
                <span>Género y número</span>
              </div>
            </div>
            <div class="detector-toggle">
              <ToggleSwitch v-model="config.terminology.enabled" @change="scheduleAutoSave" />
              <div class="detector-info">
                <label>Terminología</label>
                <span>Consistencia de términos</span>
              </div>
            </div>
            <div class="detector-toggle">
              <ToggleSwitch v-model="config.use_llm_review" @change="scheduleAutoSave" />
              <div class="detector-info">
                <label>Revisión con IA</label>
                <span>Filtrar falsos positivos (requiere Ollama)</span>
              </div>
            </div>
          </div>
        </template>
      </Card>
    </div>
  </div>
</template>

<style scoped>
.correction-config-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.detection-banner {
  margin: 0;
}

.detection-banner :deep(.p-message-wrapper) {
  padding: 0.75rem 1rem;
}

.detection-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  width: 100%;
}

.detection-info {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.detection-info i {
  font-size: 1.25rem;
  color: var(--p-primary-color);
}

.detection-info p {
  margin: 0.25rem 0 0 0;
  font-size: 0.85rem;
  opacity: 0.8;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.card-header span {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.preset-card :deep(.p-card-title) {
  font-size: 1rem;
  padding-bottom: 0.5rem;
}

.preset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 0.5rem;
}

.preset-btn {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 0.75rem;
  border: 1px solid var(--p-surface-300);
  border-radius: var(--p-border-radius);
  background: var(--p-surface-0);
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: left;
}

.preset-btn:hover {
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 5%, var(--p-surface-0));
}

.preset-btn.active {
  border-color: var(--p-primary-color);
  background: color-mix(in srgb, var(--p-primary-color) 10%, var(--p-surface-0));
}

:global(.dark) .preset-btn {
  background: var(--p-surface-800);
  border-color: var(--p-surface-600);
}

:global(.dark) .preset-btn:hover,
:global(.dark) .preset-btn.active {
  background: var(--p-surface-700);
}

.preset-name {
  font-weight: 600;
  font-size: 0.9rem;
}

.preset-desc {
  font-size: 0.75rem;
  color: var(--p-text-secondary-color);
  margin-top: 0.25rem;
}

.modified-tag {
  margin-top: 0.75rem;
}

.config-sections {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.config-card :deep(.p-card-title) {
  font-size: 0.95rem;
  padding-bottom: 0.25rem;
}

.config-card :deep(.p-card-content) {
  padding-top: 0.5rem;
}

.config-row {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.config-row:last-child {
  margin-bottom: 0;
}

.config-row.inline {
  flex-direction: row;
  align-items: center;
}

.config-row label {
  font-size: 0.85rem;
  color: var(--p-text-color);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.distance-slider {
  width: 100%;
}

.field-help {
  font-size: 0.8rem;
  color: var(--p-text-secondary-color);
  margin: 0 0 0.5rem 0;
  line-height: 1.4;
}

.field-multiselect {
  width: 100%;
}

.detector-toggles {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.detector-toggle {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.detector-info {
  display: flex;
  flex-direction: column;
}

.detector-info label {
  font-size: 0.9rem;
  font-weight: 500;
}

.detector-info span {
  font-size: 0.8rem;
  color: var(--p-text-secondary-color);
}

.loading-overlay {
  opacity: 0.6;
  pointer-events: none;
}

/* Dark mode styles */
:global(.dark) .correction-config-panel {
  color: var(--p-text-color);
}

:global(.dark) .config-card,
:global(.dark) .preset-card {
  background: var(--p-surface-800);
  border-color: var(--p-surface-700);
}

:global(.dark) .config-card :deep(.p-card),
:global(.dark) .preset-card :deep(.p-card) {
  background: var(--p-surface-800);
  border-color: var(--p-surface-700);
}

:global(.dark) .config-card :deep(.p-card-title),
:global(.dark) .preset-card :deep(.p-card-title) {
  color: var(--p-text-color);
}

:global(.dark) .config-card :deep(.p-card-content),
:global(.dark) .preset-card :deep(.p-card-content) {
  color: var(--p-text-color);
}

:global(.dark) .config-row label {
  color: var(--p-text-color);
}

:global(.dark) .detector-info label {
  color: var(--p-text-color);
}

:global(.dark) .detector-info span {
  color: var(--p-text-secondary-color);
}

:global(.dark) .preset-name {
  color: var(--p-text-color);
}

:global(.dark) .preset-desc {
  color: var(--p-text-secondary-color);
}

:global(.dark) .card-header span {
  color: var(--p-text-color);
}

:global(.dark) .card-header span i {
  color: var(--p-text-secondary-color);
}

:global(.dark) .field-help {
  color: var(--p-text-secondary-color);
}

/* Dark mode form components are now handled by global primevue-overrides.css */

/* Dark mode - Tags */
:global(.dark) .modified-tag {
  background: var(--p-surface-700);
  color: var(--p-text-color);
}
</style>
