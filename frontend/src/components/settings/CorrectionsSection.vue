<template>
  <!-- Nota informativa -->
  <Message severity="info" :closable="false" class="mb-4">
    <template #default>
      <div class="correction-info-message">
        <p>
          La configuración de correcciones se aplica por proyecto. Aquí puedes seleccionar un preset base
          que se aplicará a nuevos proyectos. Para ajustar la configuración de un proyecto específico,
          accede a sus ajustes desde el panel del proyecto.
        </p>
      </div>
    </template>
  </Message>

  <!-- Preset para nuevos proyectos -->
  <div class="setting-item">
    <div class="setting-info">
      <label class="setting-label">Preset por defecto</label>
      <p class="setting-description">
        Configuración base que se aplicará a nuevos proyectos. Puedes personalizarla después.
      </p>
    </div>
    <div class="setting-control wide">
      <Select
        v-model="defaultCorrectionPreset"
        :options="correctionPresetOptions"
        option-label="name"
        option-value="id"
        placeholder="Selecciona un preset"
        class="w-full"
        inputId="default-correction-preset"
        aria-label="Preset por defecto"
        @change="onDefaultPresetChange"
      >
        <template #option="slotProps">
          <div class="preset-dropdown-option">
            <span class="preset-name">{{ slotProps.option.name }}</span>
            <span class="preset-description">{{ slotProps.option.description }}</span>
          </div>
        </template>
      </Select>
    </div>
  </div>

  <!-- Resumen de configuración actual -->
  <div v-if="defaultCorrectionConfig" class="setting-item column">
    <div class="setting-info">
      <label class="setting-label">Resumen de configuración</label>
      <p class="setting-description">
        Vista previa de la configuración del preset seleccionado
      </p>
    </div>
    <div class="correction-config-summary">
      <div class="config-grid">
        <!-- Perfil de documento -->
        <div class="config-section">
          <h4><i class="pi pi-file"></i> Perfil de documento</h4>
          <div class="config-items">
            <div class="config-item">
              <span class="config-label">Tipo:</span>
              <Tag :value="getFieldLabel(defaultCorrectionConfig.profile?.document_field)" severity="info" />
            </div>
            <div class="config-item">
              <span class="config-label">Registro:</span>
              <Tag :value="getRegisterLabel(defaultCorrectionConfig.profile?.register)" severity="secondary" />
            </div>
            <div class="config-item">
              <span class="config-label">Audiencia:</span>
              <span>{{ getAudienceLabel(defaultCorrectionConfig.profile?.audience) }}</span>
            </div>
          </div>
        </div>

        <!-- Tipografía -->
        <div class="config-section">
          <h4><i class="pi pi-align-left"></i> Tipografía</h4>
          <div class="config-items">
            <div class="config-item">
              <span class="config-label">Habilitado:</span>
              <i :class="defaultCorrectionConfig.typography?.enabled ? 'pi pi-check text-green-500' : 'pi pi-times text-red-500'"></i>
            </div>
            <div class="config-item">
              <span class="config-label">Guiones:</span>
              <span>{{ getDashLabel(defaultCorrectionConfig.typography?.dialogue_dash) }}</span>
            </div>
            <div class="config-item">
              <span class="config-label">Comillas:</span>
              <span>{{ getQuoteLabel(defaultCorrectionConfig.typography?.quote_style) }}</span>
            </div>
          </div>
        </div>

        <!-- Repeticiones -->
        <div class="config-section">
          <h4><i class="pi pi-copy"></i> Repeticiones</h4>
          <div class="config-items">
            <div class="config-item">
              <span class="config-label">Habilitado:</span>
              <i :class="defaultCorrectionConfig.repetition?.enabled ? 'pi pi-check text-green-500' : 'pi pi-times text-red-500'"></i>
            </div>
            <div class="config-item">
              <span class="config-label">Distancia mín:</span>
              <span>{{ defaultCorrectionConfig.repetition?.min_distance }} palabras</span>
            </div>
            <div class="config-item">
              <span class="config-label">Sensibilidad:</span>
              <Tag :value="getSensitivityLabel(defaultCorrectionConfig.repetition?.sensitivity)" :severity="getSensitivitySeverity(defaultCorrectionConfig.repetition?.sensitivity)" />
            </div>
          </div>
        </div>

        <!-- Regional -->
        <div class="config-section">
          <h4><i class="pi pi-globe"></i> Vocabulario regional</h4>
          <div class="config-items">
            <div class="config-item">
              <span class="config-label">Habilitado:</span>
              <i :class="defaultCorrectionConfig.regional?.enabled ? 'pi pi-check text-green-500' : 'pi pi-times text-red-500'"></i>
            </div>
            <div class="config-item">
              <span class="config-label">Región:</span>
              <span>{{ getRegionLabel(defaultCorrectionConfig.regional?.target_region) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Variante regional por defecto -->
  <div class="setting-item">
    <div class="setting-info">
      <label class="setting-label">Variante regional</label>
      <p class="setting-description">
        Variante del español para nuevos proyectos. Cada proyecto puede personalizarse desde su configuración.
      </p>
    </div>
    <div class="setting-control">
      <Select
        v-model="defaultRegion"
        :options="regionOptions"
        option-label="label"
        option-value="value"
        placeholder="Selecciona región"
        inputId="default-region"
        aria-label="Variante regional"
        @change="onDefaultRegionChange"
      />
    </div>
  </div>

  <!-- Revisión con LLM -->
  <div class="setting-item">
    <div class="setting-info">
      <label class="setting-label">Revisión inteligente</label>
      <p class="setting-description">
        Usar la IA para filtrar falsos positivos en las alertas de corrección.
        Requiere el analizador semántico activo.
      </p>
    </div>
    <div class="setting-control">
      <ToggleSwitch
        v-model="useLLMReview"
        inputId="settings-llm-review"
        aria-label="Revisión inteligente"
        @change="onLLMReviewChange"
      />
    </div>
  </div>

  <Divider />

  <!-- Personalización de defaults por tipo -->
  <CorrectionDefaultsManager ref="defaultsManager" />
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import Select from 'primevue/select'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import Divider from 'primevue/divider'
import CorrectionDefaultsManager from './CorrectionDefaultsManager.vue'
import { api } from '@/services/apiClient'
import { safeSetItem, safeGetItem } from '@/utils/safeStorage'
import {
  getFieldLabel, getRegisterLabel, getAudienceLabel,
  getDashLabel, getQuoteLabel,
  getSensitivityLabel, getSensitivitySeverity,
  getRegionLabel,
} from '@/utils/settingsLabels'
import type { CorrectionConfig } from '@/types'
import { logError } from '@/services/logger'

interface CorrectionPresetLocal {
  id: string
  name: string
  description: string
  config: CorrectionConfig
}

interface CorrectionOptions {
  document_fields: Array<{ value: string; label: string }>
  register_levels: Array<{ value: string; label: string }>
  audience_types: Array<{ value: string; label: string }>
  regions: Array<{ value: string; label: string }>
  quote_styles: Array<{ value: string; label: string }>
  dialogue_dashes: Array<{ value: string; label: string }>
  sensitivity_levels: Array<{ value: string; label: string }>
}

const correctionPresetOptions = ref<CorrectionPresetLocal[]>([])
const correctionOptions = ref<CorrectionOptions | null>(null)
const defaultCorrectionPreset = ref<string>('default')
const defaultCorrectionConfig = ref<CorrectionConfig | null>(null)
const defaultRegion = ref<string>('es_ES')
const useLLMReview = ref<boolean>(false)
const defaultsManager = ref()

const regionOptions = computed(() => correctionOptions.value?.regions || [
  { value: 'es_ES', label: 'Espana' },
  { value: 'es_MX', label: 'Mexico' },
  { value: 'es_AR', label: 'Argentina' },
  { value: 'es_CO', label: 'Colombia' },
])

async function loadCorrectionPresets() {
  try {
    const data = await api.getRaw<{ success: boolean; data?: any; error?: string }>('/api/correction-presets')

    if (data.success && data.data) {
      correctionPresetOptions.value = data.data.presets || []
      correctionOptions.value = data.data.options || null

      const savedPreset = safeGetItem('defaultCorrectionPreset')
      if (savedPreset) {
        defaultCorrectionPreset.value = savedPreset
        const preset = correctionPresetOptions.value.find(p => p.id === savedPreset)
        if (preset) {
          defaultCorrectionConfig.value = preset.config
        }
      } else if (correctionPresetOptions.value.length > 0) {
        defaultCorrectionConfig.value = correctionPresetOptions.value[0].config
      }

      const savedRegion = safeGetItem('defaultCorrectionRegion')
      if (savedRegion) {
        defaultRegion.value = savedRegion
      }

      useLLMReview.value = safeGetItem('useLLMReview') === 'true'
    }
  } catch (error) {
    logError('CorrectionsSection', 'Error loading correction presets:', error)
  }
}

function onDefaultPresetChange() {
  const preset = correctionPresetOptions.value.find(p => p.id === defaultCorrectionPreset.value)
  if (preset) {
    defaultCorrectionConfig.value = preset.config
    safeSetItem('defaultCorrectionPreset', preset.id)
  }
}

function onDefaultRegionChange() {
  safeSetItem('defaultCorrectionRegion', defaultRegion.value)
}

function onLLMReviewChange() {
  safeSetItem('useLLMReview', useLLMReview.value.toString())
}

defineExpose({ loadCorrectionPresets })
</script>
