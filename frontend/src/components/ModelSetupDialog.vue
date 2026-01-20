<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useSystemStore } from '@/stores/system'
import Dialog from 'primevue/dialog'
import ProgressBar from 'primevue/progressbar'

const systemStore = useSystemStore()

const visible = ref(false)
const downloadStarted = ref(false)
const downloadProgress = ref(0)

// Check models on mount and start download automatically if needed
onMounted(async () => {
  await systemStore.checkModelsStatus()
  if (!systemStore.modelsReady) {
    visible.value = true
    // Start download automatically
    startDownload()
  }
})

// Watch for model status changes
watch(() => systemStore.modelsReady, (ready) => {
  if (ready && visible.value) {
    // Models are ready, close dialog after a brief delay
    setTimeout(() => {
      visible.value = false
      downloadStarted.value = false
    }, 2000)
  }
})

// Simulate progress while downloading
watch(() => systemStore.modelsDownloading, (downloading) => {
  if (downloading) {
    downloadProgress.value = 0
    const interval = setInterval(() => {
      if (downloadProgress.value < 95) {
        downloadProgress.value += Math.random() * 3
      }
      if (!systemStore.modelsDownloading) {
        clearInterval(interval)
        downloadProgress.value = 100
      }
    }, 500)
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

async function startDownload() {
  downloadStarted.value = true
  await systemStore.downloadModels()
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
    :style="{ width: '450px' }"
  >
    <div class="dialog-content">
      <!-- Downloading state (automatic) -->
      <template v-if="downloadStarted && !systemStore.modelsReady">
        <div class="download-progress">
          <i class="pi pi-spin pi-spinner download-spinner"></i>
          <h3>Descargando modelos...</h3>
          <p>Preparando Narrative Assistant para su primer uso.</p>

          <div class="models-downloading">
            <div v-for="model in missingModels" :key="model.name" class="model-item-small">
              <i class="pi pi-box"></i>
              <span>{{ model.displayName }}</span>
              <span class="model-size">~{{ model.sizeMb }} MB</span>
            </div>
          </div>

          <ProgressBar
            :value="downloadProgress"
            :showValue="false"
            class="progress-bar"
          />

          <p class="progress-text">
            {{ Math.round(downloadProgress) }}% - Total: ~{{ totalDownloadSize }} MB
          </p>

          <p class="note">
            <i class="pi pi-info-circle"></i>
            Esta descarga solo se realiza una vez.
          </p>
        </div>
      </template>

      <!-- Completed state -->
      <template v-else-if="systemStore.modelsReady">
        <div class="download-complete">
          <i class="pi pi-check-circle complete-icon"></i>
          <h3>Listo para usar</h3>
          <p>Los modelos se han instalado correctamente.</p>
        </div>
      </template>

      <!-- Error state -->
      <template v-if="systemStore.modelsError">
        <div class="error-message">
          <i class="pi pi-exclamation-triangle"></i>
          <span>{{ systemStore.modelsError }}</span>
        </div>
      </template>
    </div>
  </Dialog>
</template>

<style scoped>
.dialog-content {
  padding: 1rem 0;
}

.info-section {
  text-align: center;
  margin-bottom: 1.5rem;
}

.info-icon {
  font-size: 3rem;
  color: var(--p-primary-color);
  margin-bottom: 1rem;
}

.info-section h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.25rem;
}

.info-section p {
  color: var(--p-text-muted-color);
  margin: 0;
  line-height: 1.5;
}

.models-downloading {
  background: var(--p-surface-100);
  border-radius: 6px;
  padding: 0.75rem;
  margin-bottom: 1rem;
}

.model-item-small {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0;
  font-size: 0.875rem;
}

.model-item-small i {
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
}

.model-item-small span:first-of-type {
  flex: 1;
}

.model-size {
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
}

.note {
  margin-top: 1rem;
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  justify-content: center;
}

.download-progress {
  text-align: center;
  padding: 1rem;
}

.download-spinner {
  font-size: 3rem;
  color: var(--p-primary-color);
  margin-bottom: 1rem;
}

.download-progress h3 {
  margin: 0 0 0.5rem 0;
}

.download-progress p {
  color: var(--p-text-muted-color);
  margin: 0 0 1.5rem 0;
}

.progress-bar {
  height: 8px;
  margin-bottom: 0.5rem;
}

.progress-text {
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
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

.error-message {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: var(--p-red-50);
  color: var(--p-red-700);
  border-radius: 6px;
  margin-top: 1rem;
}

/* Dark mode */
.dark .models-downloading {
  background: var(--p-surface-800);
}

.dark .download-complete h3 {
  color: var(--p-green-400);
}

.dark .error-message {
  background: var(--p-red-900);
  color: var(--p-red-300);
}
</style>
