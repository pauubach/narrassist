<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useSystemStore } from '@/stores/system'
import Dialog from 'primevue/dialog'
import ProgressBar from 'primevue/progressbar'

const systemStore = useSystemStore()

const visible = ref(false)
const downloadProgress = ref(0)
const currentModel = ref('')
const downloadPhase = ref<'checking' | 'downloading' | 'completed' | 'error'>('checking')

// Check models on mount and start download automatically if needed
onMounted(async () => {
  downloadPhase.value = 'checking'
  await systemStore.checkModelsStatus()

  if (!systemStore.modelsReady) {
    visible.value = true
    downloadPhase.value = 'downloading'
    // Start download automatically - no user action needed
    startAutomaticDownload()
  }
})

// Watch for model status changes
watch(() => systemStore.modelsReady, (ready) => {
  if (ready && visible.value) {
    downloadPhase.value = 'completed'
    downloadProgress.value = 100
    // Close dialog after showing success briefly
    setTimeout(() => {
      visible.value = false
    }, 2000)
  }
})

// Simulate realistic progress while downloading
let progressInterval: ReturnType<typeof setInterval> | null = null

function startProgressSimulation() {
  downloadProgress.value = 0

  progressInterval = setInterval(() => {
    if (downloadProgress.value < 95) {
      // Simulate realistic download progress
      const increment = Math.random() * 2 + 0.5
      downloadProgress.value = Math.min(95, downloadProgress.value + increment)

      // Update current model based on progress
      if (downloadProgress.value < 50) {
        currentModel.value = 'spaCy (modelo de lenguaje)'
      } else {
        currentModel.value = 'Embeddings (analisis semantico)'
      }
    }
  }, 500)
}

function stopProgressSimulation() {
  if (progressInterval) {
    clearInterval(progressInterval)
    progressInterval = null
  }
}

// Watch for download completion
watch(() => systemStore.modelsDownloading, (downloading) => {
  if (downloading) {
    startProgressSimulation()
  } else {
    stopProgressSimulation()
    if (systemStore.modelsReady) {
      downloadProgress.value = 100
    }
  }
})

// Watch for errors
watch(() => systemStore.modelsError, (error) => {
  if (error) {
    downloadPhase.value = 'error'
    stopProgressSimulation()
  }
})

const missingModels = computed(() => {
  if (!systemStore.modelsStatus?.nlp_models) return []

  return Object.entries(systemStore.modelsStatus.nlp_models)
    .filter(([_, info]) => !info.installed)
    .map(([name, info]) => ({
      name,
      displayName: info.display_name,
      sizeMb: info.size_mb
    }))
})

const totalDownloadSize = computed(() => {
  return missingModels.value.reduce((sum, m) => sum + m.sizeMb, 0)
})

async function startAutomaticDownload() {
  await systemStore.downloadModels()
}

function retryDownload() {
  downloadPhase.value = 'downloading'
  systemStore.modelsError = null
  startAutomaticDownload()
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    :closable="false"
    :modal="true"
    :draggable="false"
    header="Configuracion inicial"
    class="model-setup-dialog"
    :style="{ width: '500px' }"
  >
    <div class="dialog-content">
      <!-- Checking state -->
      <template v-if="downloadPhase === 'checking'">
        <div class="checking-state">
          <i class="pi pi-spin pi-spinner checking-spinner"></i>
          <p>Verificando configuracion...</p>
        </div>
      </template>

      <!-- Downloading state (automatic) -->
      <template v-else-if="downloadPhase === 'downloading'">
        <div class="download-progress">
          <div class="download-header">
            <i class="pi pi-download download-icon"></i>
            <div>
              <h3>Preparando Narrative Assistant</h3>
              <p class="subtitle">Descargando modelos de analisis de texto</p>
            </div>
          </div>

          <div class="progress-section">
            <div class="progress-info">
              <span class="current-model">{{ currentModel || 'Iniciando descarga...' }}</span>
              <span class="progress-percent">{{ Math.round(downloadProgress) }}%</span>
            </div>
            <ProgressBar
              :value="downloadProgress"
              :showValue="false"
              class="progress-bar"
            />
          </div>

          <div class="models-list">
            <div v-for="model in missingModels" :key="model.name" class="model-item">
              <i class="pi" :class="downloadProgress > (model.name === 'spacy' ? 50 : 100) ? 'pi-check-circle text-green' : 'pi-circle'"></i>
              <span class="model-name">{{ model.displayName }}</span>
              <span class="model-size">~{{ model.sizeMb }} MB</span>
            </div>
          </div>

          <p class="download-note">
            <i class="pi pi-info-circle"></i>
            Esta descarga solo se realiza una vez. Tamano total: ~{{ totalDownloadSize }} MB
          </p>
        </div>
      </template>

      <!-- Completed state -->
      <template v-else-if="downloadPhase === 'completed'">
        <div class="download-complete">
          <i class="pi pi-check-circle complete-icon"></i>
          <h3>Listo para usar</h3>
          <p>Narrative Assistant esta preparado.</p>
        </div>
      </template>

      <!-- Error state -->
      <template v-else-if="downloadPhase === 'error'">
        <div class="error-state">
          <i class="pi pi-exclamation-triangle error-icon"></i>
          <h3>Error en la descarga</h3>
          <p class="error-message">{{ systemStore.modelsError }}</p>
          <p class="error-hint">
            Verifica tu conexion a internet e intenta de nuevo.
          </p>
          <button class="retry-button" @click="retryDownload">
            <i class="pi pi-refresh"></i>
            Reintentar
          </button>
        </div>
      </template>
    </div>
  </Dialog>
</template>

<style scoped>
.dialog-content {
  padding: 0.5rem 0;
}

.checking-state {
  text-align: center;
  padding: 2rem;
}

.checking-spinner {
  font-size: 2rem;
  color: var(--p-primary-color);
  margin-bottom: 1rem;
}

.download-progress {
  padding: 0.5rem;
}

.download-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.download-icon {
  font-size: 2.5rem;
  color: var(--p-primary-color);
}

.download-header h3 {
  margin: 0 0 0.25rem 0;
  font-size: 1.25rem;
}

.download-header .subtitle {
  margin: 0;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
}

.progress-section {
  margin-bottom: 1.5rem;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
}

.current-model {
  color: var(--p-text-color);
}

.progress-percent {
  color: var(--p-primary-color);
  font-weight: 600;
}

.progress-bar {
  height: 8px;
}

.models-list {
  background: var(--p-surface-100);
  border-radius: 8px;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
}

.model-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0;
  font-size: 0.875rem;
}

.model-item:not(:last-child) {
  border-bottom: 1px solid var(--p-surface-200);
}

.model-item i {
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
}

.model-item i.text-green {
  color: var(--p-green-500);
}

.model-name {
  flex: 1;
}

.model-size {
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
}

.download-note {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
  margin: 0;
}

.download-note i {
  font-size: 0.875rem;
}

.download-complete {
  text-align: center;
  padding: 2rem 1rem;
}

.complete-icon {
  font-size: 4rem;
  color: var(--p-green-500);
  margin-bottom: 1rem;
}

.download-complete h3 {
  margin: 0 0 0.5rem 0;
  color: var(--p-green-700);
}

.download-complete p {
  margin: 0;
  color: var(--p-text-muted-color);
}

.error-state {
  text-align: center;
  padding: 1.5rem;
}

.error-icon {
  font-size: 3rem;
  color: var(--p-red-500);
  margin-bottom: 1rem;
}

.error-state h3 {
  margin: 0 0 0.5rem 0;
  color: var(--p-red-700);
}

.error-message {
  background: var(--p-red-50);
  color: var(--p-red-700);
  padding: 0.75rem 1rem;
  border-radius: 6px;
  margin: 1rem 0;
  font-size: 0.875rem;
}

.error-hint {
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
  margin-bottom: 1rem;
}

.retry-button {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: var(--p-primary-color);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: background 0.2s;
}

.retry-button:hover {
  background: var(--p-primary-600);
}

/* Dark mode */
.dark .models-list {
  background: var(--p-surface-800);
}

.dark .model-item:not(:last-child) {
  border-bottom-color: var(--p-surface-700);
}

.dark .download-complete h3 {
  color: var(--p-green-400);
}

.dark .error-state h3 {
  color: var(--p-red-400);
}

.dark .error-message {
  background: var(--p-red-900);
  color: var(--p-red-300);
}
</style>
