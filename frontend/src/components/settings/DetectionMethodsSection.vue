<template>
  <!-- Correferencia -->
  <div class="nlp-category">
    <div class="category-header">
      <h4><i class="pi pi-link"></i> Seguimiento de referencias</h4>
      <span class="category-desc">Detecta cuándo "él", "la detective" o "María" se refieren al mismo personaje</span>
    </div>
    <div class="methods-grid">
      <MethodCard
        v-for="(method, key) in nlp.getNLPMethodsForCategory('coreference')"
        :key="key"
        category="coreference"
        :method-key="String(key)"
        :method="method"
        :enabled="nlp.isMethodEnabled('coreference', String(key))"
        :system-capabilities="systemCapabilities"
        :gpu-tooltip="nlp.gpuRequirementTooltip.value"
        show-weight
        @toggle="nlp.toggleMethod('coreference', String(key), $event)"
      />
    </div>
  </div>

  <!-- NER -->
  <div class="nlp-category">
    <div class="category-header">
      <h4><i class="pi pi-user"></i> Detección de personajes y lugares</h4>
      <span class="category-desc">Identifica automáticamente nombres de personas, lugares y organizaciones</span>
    </div>
    <div class="methods-grid">
      <MethodCard
        v-for="(method, key) in nlp.getNLPMethodsForCategory('ner')"
        :key="key"
        category="ner"
        :method-key="String(key)"
        :method="method"
        :enabled="nlp.isMethodEnabled('ner', String(key))"
        :system-capabilities="systemCapabilities"
        :gpu-tooltip="nlp.gpuRequirementTooltip.value"
        @toggle="nlp.toggleMethod('ner', String(key), $event)"
      />
    </div>
  </div>

  <!-- Gramática -->
  <div class="nlp-category">
    <div class="category-header">
      <h4><i class="pi pi-check-circle"></i> Corrección gramatical</h4>
      <span class="category-desc">Detecta errores de concordancia, puntuación y otros problemas gramaticales</span>
    </div>

    <!-- LanguageTool status bar -->
    <div v-if="ltState === 'running'" class="ollama-ready-bar" style="margin-bottom: 0.75rem;">
      <div class="ollama-ready-info">
        <i class="pi pi-check-circle"></i>
        <span>Corrector avanzado activo (+2000 reglas)</span>
      </div>
    </div>
    <div v-else class="ollama-action-card" :class="'ollama-state-' + (ltState === 'not_installed' ? 'not_installed' : ltState === 'installing' ? 'no_models' : 'not_running')" style="margin-bottom: 0.75rem;">
      <div class="ollama-action-content">
        <i v-if="ltState !== 'installing'" class="pi pi-exclamation-triangle"></i>
        <i v-else class="pi pi-download"></i>
        <div class="ollama-action-text" style="flex: 1;">
          <strong>{{
            ltState === 'not_installed' ? 'Corrector avanzado no disponible' :
            ltState === 'installing' ? 'Instalando corrector avanzado' :
            'Corrector avanzado no iniciado'
          }}</strong>
          <span>{{ ltStatusMessage }}</span>
          <!-- Barra de progreso para instalación -->
          <DsDownloadProgress
            v-if="ltState === 'installing' && ltInstallProgress"
            :label="ltInstallProgress.phase_label"
            :percentage="ltInstallProgress.percentage > 0 ? ltInstallProgress.percentage : null"
            :detail="ltInstallProgress.detail"
            class="lt-progress-container"
          />
        </div>
        <Button
          v-if="ltState !== 'installing'"
          :label="ltActionConfig.label"
          :icon="ltActionConfig.icon"
          :severity="ltActionConfig.severity"
          size="small"
          :loading="ltInstalling || ltStarting"
          @click="ltActionConfig.action"
        />
      </div>
    </div>

    <div class="methods-grid">
      <MethodCard
        v-for="(method, key) in nlp.getNLPMethodsForCategory('grammar')"
        :key="key"
        category="grammar"
        :method-key="String(key)"
        :method="method"
        :enabled="nlp.isMethodEnabled('grammar', String(key))"
        :system-capabilities="systemCapabilities"
        :gpu-tooltip="nlp.gpuRequirementTooltip.value"
        @toggle="nlp.toggleMethod('grammar', String(key), $event)"
      />
    </div>
  </div>

  <!-- Ortografía (Votación Multi-Método) -->
  <div class="nlp-category">
    <div class="category-header">
      <h4><i class="pi pi-spell-check"></i> Corrección ortográfica</h4>
      <span class="category-desc">Sistema de votación con múltiples correctores para máxima precisión</span>
    </div>
    <div class="methods-grid">
      <MethodCard
        v-for="(method, key) in nlp.getNLPMethodsForCategory('spelling')"
        :key="key"
        category="spelling"
        :method-key="String(key)"
        :method="method"
        :enabled="nlp.isMethodEnabled('spelling', String(key))"
        :system-capabilities="systemCapabilities"
        :gpu-tooltip="nlp.gpuRequirementTooltip.value"
        show-weight
        @toggle="nlp.toggleMethod('spelling', String(key), $event)"
      />
    </div>
  </div>

  <!-- Conocimiento de Personajes -->
  <div class="nlp-category">
    <div class="category-header">
      <h4><i class="pi pi-book"></i> Conocimiento de personajes</h4>
      <span class="category-desc">Extrae qué sabe cada personaje sobre otros y sobre eventos</span>
    </div>
    <div class="knowledge-mode-selector">
      <div
        v-for="(method, key) in nlp.getNLPMethodsForCategory('character_knowledge')"
        :key="key"
        class="knowledge-mode-card"
        :class="{
          disabled: !method.available,
          selected: ctx.settings.value.characterKnowledgeMode === key
        }"
        @click="method.available && nlp.setCharacterKnowledgeMode(String(key))"
      >
        <span class="mode-name">{{ method.name }}</span>
        <p class="mode-description">{{ method.description }}</p>
        <Tag v-if="method.recommended_gpu && !systemCapabilities?.hardware.has_gpu" value="Mejor con aceleración" severity="secondary" class="method-tag" />
        <Tag v-if="method.recommended_gpu && systemCapabilities?.hardware.has_gpu" value="Aceleración recomendada" severity="info" class="method-tag" />
        <Tag v-if="!method.available && method.requires_ollama" value="Requiere iniciar el analizador" severity="warning" class="method-tag" />
        <Tag v-else-if="!method.available && method.hardware_supported === false" value="No compatible con este equipo" severity="danger" class="method-tag" />
        <Tag v-else-if="!method.available" value="No disponible" severity="danger" class="method-tag" />
      </div>
    </div>
  </div>

  <!-- Botón para aplicar configuración recomendada -->
  <div class="setting-item">
    <div class="setting-info">
      <label class="setting-label">Configuración recomendada</label>
      <p class="setting-description">Aplicar configuración óptima según tu hardware detectado</p>
    </div>
    <div class="setting-control">
      <Button
        label="Aplicar recomendada"
        icon="pi pi-sparkles"
        severity="secondary"
        outlined
        size="small"
        :disabled="!systemCapabilities"
        @click="nlp.applyRecommendedConfig"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { inject, computed } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import DsDownloadProgress from '@/components/ds/DsDownloadProgress.vue'
import MethodCard from './MethodCard.vue'
import { settingsKey, nlpMethodsKey } from './settingsInjection'
import { useSystemStore, type LTState } from '@/stores/system'

const props = defineProps<{
  ltActionConfig: { label: string; icon: string; severity: string; action: () => void }
  ltStatusMessage: string
  ltInstalling: boolean
  ltStarting: boolean
  ltInstallProgress: { phase_label: string; percentage: number; detail?: string } | null
  ltState: LTState
}>()

const ctx = inject(settingsKey)!
const nlp = inject(nlpMethodsKey)!
const systemStore = useSystemStore()

const systemCapabilities = computed(() => systemStore.systemCapabilities)
</script>
