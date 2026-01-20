<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useSystemStore } from '@/stores/system'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import ProgressBar from 'primevue/progressbar'

const systemStore = useSystemStore()

const visible = ref(false)
const downloadStarted = ref(false)
const downloadProgress = ref(0)

// Check models on mount
onMounted(async () => {
  await systemStore.checkModelsStatus()
  if (!systemStore.modelsReady) {
    visible.value = true
  }
})

// Watch for model status changes
watch(() => systemStore.modelsReady, (ready) => {
  if (ready && visible.value) {
    // Models are ready, close dialog after a brief delay
    setTimeout(() => {
      visible.value = false
      downloadStarted.value = false
    }, 1500)
  }
})

// Simulate progress while downloading
watch(() => systemStore.modelsDownloading, (downloading) => {
  if (downloading) {
    downloadProgress.value = 0
    const interval = setInterval(() => {
      if (downloadProgress.value < 95) {
        downloadProgress.value += Math.random() * 5
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

function skipForNow() {
  visible.value = false
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    :closable="!downloadStarted"
    :modal="true"
    :draggable="false"
    header="Configuracion inicial"
    class="model-setup-dialog"
    :style="{ width: '500px' }"
  >
    <div class="dialog-content">
      <!-- Initial state: show what needs to be downloaded -->
      <template v-if="!downloadStarted && !systemStore.modelsReady">
        <div class="info-section">
          <i class="pi pi-download info-icon"></i>
          <h3>Descargar modelos necesarios</h3>
          <p>
            Narrative Assistant necesita descargar modelos de procesamiento de lenguaje
            para funcionar. Esta descarga solo se realiza una vez.
          </p>
        </div>

        <div class="models-list">
          <div v-for="model in missingModels" :key="model.name" class="model-item">
            <i class="pi pi-box"></i>
            <span class="model-name">{{ model.displayName }}</span>
            <span class="model-size">~{{ model.sizeMb }} MB</span>
          </div>
        </div>

        <div class="total-size">
          <strong>Total a descargar:</strong> ~{{ totalDownloadSize }} MB
        </div>

        <div class="actions">
          <Button
            label="Descargar ahora"
            icon="pi pi-download"
            @click="startDownload"
            :loading="systemStore.modelsLoading"
          />
          <Button
            label="Omitir por ahora"
            severity="secondary"
            text
            @click="skipForNow"
          />
        </div>

        <p class="note">
          <i class="pi pi-info-circle"></i>
          Sin estos modelos, algunas funciones no estaran disponibles.
        </p>
      </template>

      <!-- Downloading state -->
      <template v-else-if="downloadStarted && !systemStore.modelsReady">
        <div class="download-progress">
          <i class="pi pi-spin pi-spinner download-spinner"></i>
          <h3>Descargando modelos...</h3>
          <p>Por favor, no cierres la aplicacion.</p>

          <ProgressBar
            :value="downloadProgress"
            :showValue="false"
            class="progress-bar"
          />

          <p class="progress-text">
            {{ Math.round(downloadProgress) }}% completado
          </p>
        </div>
      </template>

      <!-- Completed state -->
      <template v-else-if="systemStore.modelsReady">
        <div class="download-complete">
          <i class="pi pi-check-circle complete-icon"></i>
          <h3>Modelos instalados correctamente</h3>
          <p>Narrative Assistant esta listo para usar.</p>
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

.models-list {
  background: var(--p-surface-100);
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
}

.model-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0;
}

.model-item:not(:last-child) {
  border-bottom: 1px solid var(--p-surface-200);
}

.model-item i {
  color: var(--p-text-muted-color);
}

.model-name {
  flex: 1;
  font-weight: 500;
}

.model-size {
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
}

.total-size {
  text-align: right;
  margin-bottom: 1.5rem;
  color: var(--p-text-muted-color);
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  align-items: center;
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
.dark .models-list {
  background: var(--p-surface-800);
}

.dark .model-item:not(:last-child) {
  border-bottom-color: var(--p-surface-700);
}

.dark .download-complete h3 {
  color: var(--p-green-400);
}

.dark .error-message {
  background: var(--p-red-900);
  color: var(--p-red-300);
}
</style>
