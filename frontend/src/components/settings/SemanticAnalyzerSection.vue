<template>
  <div class="nlp-category">
    <div class="category-header">
      <h4>
        <i class="pi pi-microchip-ai"></i> Analizador Semántico
        <!-- Hardware inline badge -->
        <Tag
          v-if="systemCapabilities"
          v-tooltip.top="hardwareTooltip"
          :value="hardwareBadgeLabel"
          :severity="systemCapabilities.hardware.has_gpu ? 'success' : 'secondary'"
          class="hardware-inline-badge"
        />
        <!-- Status inline badge -->
        <Tag
          v-if="systemCapabilities && ollama.ollamaState.value === 'ready'"
          :value="ollama.ollamaStatusMessage.value"
          severity="success"
          class="ollama-inline-badge"
        />
      </h4>
      <span class="category-desc">Motor de análisis avanzado del significado y contexto</span>
    </div>

    <!-- Banner durante auto-configuración -->
    <div v-if="systemCapabilities && ollama.ollamaState.value === 'configuring'" class="ollama-action-card ollama-state-configuring">
      <div class="ollama-action-content">
        <i class="pi pi-spin pi-spinner"></i>
        <div class="ollama-action-text">
          <strong>Configurando análisis inteligente</strong>
          <span>{{ ollama.ollamaStatusMessage.value }}</span>
          <span class="ollama-hint">Esto solo ocurre la primera vez</span>
        </div>
      </div>
    </div>

    <!-- Banner de acción cuando el analizador NO está listo (y no está configurando) -->
    <div v-else-if="systemCapabilities && ollama.ollamaState.value !== 'ready'" class="ollama-action-card" :class="'ollama-state-' + ollama.ollamaState.value">
      <div class="ollama-action-content">
        <i
          :class="[
            ollama.ollamaState.value === 'no_models' ? 'pi pi-info-circle' : 'pi pi-exclamation-triangle'
          ]"
        ></i>
        <div class="ollama-action-text">
          <strong>{{
            ollama.ollamaState.value === 'not_installed' ? 'Análisis inteligente no disponible' :
            ollama.ollamaState.value === 'not_running' ? 'Análisis inteligente no iniciado' :
            'Sin motores de análisis'
          }}</strong>
          <span>{{ ollama.ollamaStatusMessage.value }}</span>
        </div>
        <Button
          v-if="!ollama.modelDownloading.value"
          :label="ollama.ollamaActionConfig.value.label"
          :icon="ollama.ollamaActionConfig.value.icon"
          :severity="ollama.ollamaActionConfig.value.severity"
          size="small"
          :loading="ollama.ollamaStarting.value"
          @click="ollama.ollamaActionConfig.value.action"
        />
      </div>
      <!-- Barra de progreso de descarga de modelo -->
      <DsDownloadProgress
        v-if="ollama.modelDownloading.value"
        label="Descargando motor de análisis..."
        :percentage="ollama.ollamaDownloadProgress.value?.percentage ?? null"
        class="ollama-progress-wrapper"
      />
    </div>

    <!-- Nivel de calidad (Rápida / Completa / Experta) -->
    <div v-if="ollama.ollamaState.value === 'ready'" class="quality-level-section">
      <div class="setting-info" style="margin-bottom: 0.75rem;">
        <label class="setting-label">Nivel de análisis</label>
        <p class="setting-description">
          Más motores = mayor precisión pero más tiempo
        </p>
      </div>
      <div class="quality-level-cards">
        <div
          v-for="level in qualityLevels"
          :key="level.value"
          v-tooltip.top="level.reason || ''"
          class="quality-level-card"
          :class="{
            selected: ctx.settings.value.qualityLevel === level.value,
            disabled: !level.available,
            recommended: level.recommended,
          }"
          @click="level.available ? $emit('selectQualityLevel', level.value) : undefined"
        >
          <div class="quality-level-header">
            <i :class="level.icon"></i>
            <strong>{{ level.label }}</strong>
            <Tag v-if="level.recommended" value="Recomendado" severity="success" class="recommended-badge" />
          </div>
          <p class="quality-level-desc">{{ level.description }}</p>
          <span v-if="level.estimate" class="quality-level-time">{{ level.estimate }}</span>
        </div>
      </div>
    </div>

    <!-- Slider de sensibilidad -->
    <div v-if="ollama.ollamaState.value === 'ready'" class="setting-item">
      <div class="setting-info">
        <label class="setting-label">Sensibilidad de detección</label>
        <p class="setting-description">
          {{ llmSensitivityLabel }}
        </p>
      </div>
      <div class="setting-control" style="min-width: 200px;">
        <Slider
          v-model="ctx.settings.value.llmSensitivity"
          :min="1"
          :max="10"
          :step="1"
          aria-label="Sensibilidad de detección del analizador semántico"
          @change="$emit('llmSensitivityChange')"
        />
        <span class="slider-value">{{ ctx.settings.value.llmSensitivity ?? 5 }}</span>
      </div>
    </div>

    <!-- Motores activos (colapsable) -->
    <div v-if="ollama.ollamaState.value === 'ready'" class="setting-item motors-section">
      <div class="setting-info" style="cursor: pointer;" @click="showMotors = !showMotors">
        <label class="setting-label">
          <i :class="showMotors ? 'pi pi-chevron-down' : 'pi pi-chevron-right'" style="font-size: 0.8em; margin-right: 0.3em;"></i>
          Motores activos
        </label>
        <p class="setting-description">
          {{ activeMotorsCount }} motor{{ activeMotorsCount !== 1 ? 'es' : '' }} configurado{{ activeMotorsCount !== 1 ? 's' : '' }}
        </p>
      </div>
    </div>
    <div v-if="showMotors && ollama.ollamaState.value === 'ready'" class="motors-list">
      <div class="motor-item">
        <i class="pi pi-globe"></i>
        <div>
          <strong>Motor de idioma</strong>
          <span>Comprensión profunda del español</span>
        </div>
        <Tag value="Activo" severity="success" />
      </div>
      <div v-if="ctx.settings.value.qualityLevel !== 'rapida'" class="motor-item">
        <i class="pi pi-users"></i>
        <div>
          <strong>Motor de personajes</strong>
          <span>Análisis narrativo, voz y estilo</span>
        </div>
        <Tag value="Activo" severity="success" />
      </div>
      <div v-if="ctx.settings.value.qualityLevel === 'experta'" class="motor-item">
        <i class="pi pi-cog"></i>
        <div>
          <strong>Motor de razonamiento</strong>
          <span>Lógica temporal y causal</span>
        </div>
        <Tag value="Activo" severity="success" />
      </div>
    </div>

    <!-- Download progress (when changing quality level) -->
    <DsDownloadProgress
      v-if="qualityLevelDownloading"
      label="Descargando motores de análisis..."
      :percentage="ollama.ollamaDownloadProgress.value?.percentage ?? null"
      class="ollama-progress-wrapper"
      style="margin-top: 0.5rem;"
    />
  </div>
</template>

<script setup lang="ts">
import { inject, ref, computed } from 'vue'
import Slider from 'primevue/slider'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import DsDownloadProgress from '@/components/ds/DsDownloadProgress.vue'
import { settingsKey, ollamaKey } from './settingsInjection'
import { useSystemStore } from '@/stores/system'

const props = defineProps<{
  qualityLevels: Array<{
    value: string
    label: string
    description: string
    icon: string
    available: boolean
    recommended: boolean
    reason: string | null
    estimate: string | null
  }>
  qualityLevelDownloading: boolean
  loadingCapabilities: boolean
}>()

defineEmits<{
  selectQualityLevel: [level: string]
  llmSensitivityChange: []
}>()

const ctx = inject(settingsKey)!
const ollama = inject(ollamaKey)!
const systemStore = useSystemStore()

const showMotors = ref(false)

const systemCapabilities = computed(() => systemStore.systemCapabilities)

const activeMotorsCount = computed(() => {
  const level = ctx.settings.value.qualityLevel || 'rapida'
  if (level === 'experta') return 3
  if (level === 'completa') return 2
  return 1
})

const llmSensitivityLabel = computed(() => {
  const val = ctx.settings.value.llmSensitivity ?? 5
  if (val <= 3) return 'Menos alertas, más precisas (pocos falsos positivos)'
  if (val >= 8) return 'Más alertas, posibles falsos positivos'
  return 'Equilibrio entre precisión y cobertura'
})

const hardwareBadgeLabel = computed(() => {
  if (!systemCapabilities.value) return ''
  const hw = systemCapabilities.value.hardware
  if (hw.has_gpu) return hw.gpu?.name || 'GPU'
  return 'CPU'
})

const hardwareTooltip = computed(() => {
  if (!systemCapabilities.value) return ''
  const hw = systemCapabilities.value.hardware
  if (hw.has_gpu) {
    const mem = hw.gpu?.memory_gb ? ` (${hw.gpu.memory_gb.toFixed(1)} GB)` : ''
    return `Aceleración por hardware: ${hw.gpu?.name}${mem}`
  }
  if (hw.gpu_blocked) {
    return `${hw.gpu_blocked.name} no compatible (Compute Capability ${hw.gpu_blocked.compute_capability}, se requiere ${hw.gpu_blocked.min_required}+). Usando CPU.`
  }
  return `Modo CPU: ${hw.cpu.name}`
})
</script>
