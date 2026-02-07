<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useSystemStore } from '@/stores/system'
import type { DownloadProgressInfo, ModelStatus } from '@/stores/system'
import { useNotifications } from '@/composables/useNotifications'
import Dialog from 'primevue/dialog'
import ProgressBar from 'primevue/progressbar'

const systemStore = useSystemStore()
const { showNotification } = useNotifications()

type DownloadPhase =
  | 'starting'
  | 'checking'
  | 'installing-deps'
  | 'downloading'
  | 'completed'
  | 'error'
  | 'python-missing'
  | 'backend-error'

interface RealProgress {
  percent: number
  bytesDownloaded: number
  bytesTotal: number
  speedMbps: number
  phase: string
  modelType: string | null
  hasRealProgress: boolean
}

const visible = ref(true) // Siempre visible al inicio
const downloadPhase = ref<DownloadPhase>('starting')

// Progreso real desde el backend
const realProgress = computed<RealProgress | null>(() => {
  const progress = systemStore.downloadProgress
  const nlpModels = systemStore.modelsStatus?.nlp_models
  if ((!progress || Object.keys(progress).length === 0) && !nlpModels) return null

  const progressEntries = Object.entries(progress || {}) as [string, DownloadProgressInfo][]
  const progressTypes = new Set(progressEntries.map(([key]) => key))

  let totalBytes = 0
  let downloadedBytes = 0
  let totalSpeed = 0
  let speedCount = 0
  let activeModel: DownloadProgressInfo | null = null

  // Sumar progreso de descargas activas
  for (const [, m] of progressEntries) {
    totalBytes += m.bytes_total
    downloadedBytes += m.bytes_downloaded
    totalSpeed += m.speed_bps
    speedCount++
    if (!activeModel && m.phase !== 'completed' && m.phase !== 'error') {
      activeModel = m
    }
  }

  // Incluir modelos ya instalados que no están en progreso activo
  // (ej: embeddings resuelto del cache HF instantáneamente)
  if (nlpModels) {
    for (const [, info] of Object.entries(nlpModels) as [string, ModelStatus][]) {
      const modelType = info.type ?? ''
      if (info.installed && !progressTypes.has(modelType)) {
        const sizeBytes = (info.size_mb || 0) * 1024 * 1024
        totalBytes += sizeBytes
        downloadedBytes += sizeBytes
      }
    }
  }

  if (totalBytes === 0) return null

  return {
    percent: (downloadedBytes / totalBytes) * 100,
    bytesDownloaded: downloadedBytes,
    bytesTotal: totalBytes,
    speedMbps: speedCount > 0 ? (totalSpeed / speedCount) / (1024 * 1024) : 0,
    phase: activeModel?.phase || 'downloading',
    modelType: activeModel?.model_type || null,
    hasRealProgress: downloadedBytes > 0,
  }
})

// Progreso mostrado (real si está disponible, sino indeterminado)
const displayProgress = computed(() => {
  if (realProgress.value?.hasRealProgress) {
    return Math.round(realProgress.value.percent)
  }
  return null // null = indeterminado
})

// Mapa de nombres funcionales por tipo de modelo
const modelDisplayNames: Record<string, string> = {
  spacy: 'Análisis gramatical y lingüístico',
  embeddings: 'Análisis de similitud y contexto',
  transformer_ner: 'Reconocimiento de personajes y lugares',
}

// Texto del modelo actual basado en progreso real
const currentModel = computed(() => {
  if (!realProgress.value) return 'Iniciando descarga...'

  const phase = realProgress.value.phase
  const modelType = realProgress.value.modelType
  const displayName = modelType ? (modelDisplayNames[modelType] || modelType) : ''

  if (phase === 'connecting') return 'Conectando con el servidor...'
  if (phase === 'installing') return `Instalando ${displayName}...`
  if (phase === 'downloading') return `Descargando ${displayName}...`
  return 'Procesando...'
})

// Info de velocidad y tamaño
const downloadInfo = computed(() => {
  if (!realProgress.value?.hasRealProgress) return null

  const { bytesDownloaded, bytesTotal, speedMbps } = realProgress.value

  const formatBytes = (bytes: number) => {
    if (bytes >= 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
    if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(0)} MB`
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(0)} KB`
    return `${bytes} B`
  }

  return {
    downloaded: formatBytes(bytesDownloaded),
    total: formatBytes(bytesTotal),
    speed: speedMbps > 0 ? `${speedMbps.toFixed(1)} MB/s` : null,
  }
})

// Fase de inicio: esperar a que el backend esté listo, luego verificar modelos
onMounted(async () => {
  downloadPhase.value = 'starting'

  // 1. Esperar a que el backend responda (health check con reintentos)
  const backendOk = await systemStore.waitForBackend(60000) // 60s timeout

  if (!backendOk) {
    // Backend no respondio a tiempo
    downloadPhase.value = 'backend-error'
    return
  }

  // 2. Backend listo - pre-cargar capabilities en background (no bloquea)
  systemStore.loadCapabilities()

  // 3. Verificar estado de modelos
  downloadPhase.value = 'checking'
  await systemStore.checkModelsStatus()

  // Si los modelos estan listos, cerrar el dialogo rapidamente
  if (systemStore.modelsReady) {
    downloadPhase.value = 'completed'
    setTimeout(() => {
      visible.value = false
    }, 800) // breve flash de "Listo"
    return
  }

  // 3. Verificar que Python esta disponible
  if (!systemStore.pythonAvailable) {
    downloadPhase.value = 'python-missing'
    return
  }

  // 4. Instalar dependencias o descargar modelos
  if (systemStore.dependenciesNeeded || !systemStore.backendLoaded) {
    downloadPhase.value = 'installing-deps'
    startDependenciesInstallation()
  } else {
    downloadPhase.value = 'downloading'
    startAutomaticDownload()
  }
})

// Watch for model status changes
watch(() => systemStore.modelsReady, (ready) => {
  if (ready && visible.value) {
    downloadPhase.value = 'completed'
    showNotification({
      title: 'Modelos instalados',
      body: 'Narrative Assistant está listo para usar.',
      severity: 'success',
      playSound: true,
    })
    setTimeout(() => {
      visible.value = false
    }, 2000)
  }
})

watch(() => systemStore.modelsError, (error) => {
  if (error) {
    downloadPhase.value = 'error'
    showNotification({
      title: 'Error en la instalación',
      body: error,
      severity: 'error',
      playSound: true,
    })
  }
})

// Limpiar al desmontar
onBeforeUnmount(() => {
  systemStore.stopPolling()
})

// Orden fijo de tipos de modelo para la UI
const MODEL_TYPE_ORDER = ['spacy', 'embeddings', 'transformer_ner']

// Todos los modelos (instalados y pendientes) en orden de instalación
const allModels = computed(() => {
  const nlpModels = systemStore.modelsStatus?.nlp_models
  if (!nlpModels) return []

  const entries = Object.entries(nlpModels) as [string, ModelStatus][]
  return entries
    .sort(([, a], [, b]) => {
      const ia = MODEL_TYPE_ORDER.indexOf(a.type ?? '')
      const ib = MODEL_TYPE_ORDER.indexOf(b.type ?? '')
      return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib)
    })
    .map(([name, info]) => ({
      name,
      type: info.type ?? name,
      displayName: info.display_name || modelDisplayNames[info.type ?? ''] || name,
      sizeMb: info.size_mb || 0,
      installed: info.installed,
    }))
})

const missingModels = computed(() => allModels.value.filter(m => !m.installed))

// Usar tamaños reales del backend si están disponibles
const totalDownloadSize = computed(() => {
  const sizes = systemStore.modelSizes
  if (sizes && sizes.total > 0) {
    return Math.round(sizes.total / (1024 * 1024)) // Convertir a MB
  }
  return missingModels.value.reduce((sum, m) => sum + m.sizeMb, 0)
})

async function startAutomaticDownload() {
  await systemStore.downloadModels()
}

async function startDependenciesInstallation() {
  await systemStore.installDependencies()
}

// Watch for dependencies installation
watch(() => systemStore.dependenciesInstalling, (installing) => {
  if (!installing && downloadPhase.value === 'installing-deps') {
    // Dependencies installed, check if backend is ready
    setTimeout(async () => {
      await systemStore.checkModelsStatus()
      if (!systemStore.dependenciesNeeded && systemStore.backendLoaded) {
        // Dependencies OK AND backend loaded, now download models
        downloadPhase.value = 'downloading'
        startAutomaticDownload()
      } else if (systemStore.modelsError) {
        downloadPhase.value = 'error'
      } else if (systemStore.dependenciesNeeded || !systemStore.backendLoaded) {
        // Still not ready, show error
        downloadPhase.value = 'error'
        systemStore.modelsError = 'Failed to load backend after installing dependencies. Try restarting the application.'
      }
    }, 2000)
  }
})

function retryDownload() {
  downloadPhase.value = 'downloading'
  systemStore.modelsError = null
  startAutomaticDownload()
}

async function retryStartup() {
  downloadPhase.value = 'starting'
  const backendOk = await systemStore.waitForBackend(60000)
  if (!backendOk) {
    downloadPhase.value = 'backend-error'
    return
  }
  // Backend listo, continuar con verificacion de modelos
  downloadPhase.value = 'checking'
  await systemStore.checkModelsStatus()

  if (systemStore.modelsReady) {
    downloadPhase.value = 'completed'
    setTimeout(() => { visible.value = false }, 800)
    return
  }
  if (!systemStore.pythonAvailable) {
    downloadPhase.value = 'python-missing'
    return
  }
  if (systemStore.dependenciesNeeded || !systemStore.backendLoaded) {
    downloadPhase.value = 'installing-deps'
    startDependenciesInstallation()
  } else {
    downloadPhase.value = 'downloading'
    startAutomaticDownload()
  }
}

// Helpers para estado de modelos individuales (usan model type, no model name)
function getModelPhase(modelType: string): string | undefined {
  const progress = systemStore.downloadProgress as Record<string, DownloadProgressInfo>
  return progress[modelType]?.phase
}

function isModelCompleted(modelType: string): boolean {
  return getModelPhase(modelType) === 'completed'
}

function isModelDownloading(modelType: string): boolean {
  const phase = getModelPhase(modelType)
  return phase === 'downloading' || phase === 'connecting' || phase === 'installing'
}

function isModelPending(modelType: string): boolean {
  // Modelo no instalado, no descargando, no completado: está en cola
  return !getModelPhase(modelType) && downloadPhase.value === 'downloading'
}

async function recheckPython() {
  downloadPhase.value = 'checking'
  await systemStore.checkModelsStatus()

  if (!systemStore.pythonAvailable) {
    downloadPhase.value = 'python-missing'
  } else if (systemStore.dependenciesNeeded || !systemStore.backendLoaded) {
    downloadPhase.value = 'installing-deps'
    startDependenciesInstallation()
  } else if (systemStore.modelsReady) {
    downloadPhase.value = 'completed'
    setTimeout(() => {
      visible.value = false
    }, 2000)
  } else {
    downloadPhase.value = 'downloading'
    startAutomaticDownload()
  }
}
</script>

<template>
  <Dialog
    v-model:visible="visible"
    :closable="false"
    :modal="true"
    :draggable="false"
    :header="downloadPhase === 'starting' ? 'Narrative Assistant' : 'Configuración inicial'"
    class="model-setup-dialog"
    :style="{ width: 'min(500px, 90vw)' }"
  >
    <div class="dialog-content">
      <!-- Starting state - waiting for backend -->
      <template v-if="downloadPhase === 'starting'">
        <div class="checking-state">
          <i class="pi pi-spin pi-spinner checking-spinner"></i>
          <h3 class="starting-title">Iniciándose...</h3>
          <p class="starting-subtitle">Preparando el motor de análisis</p>
        </div>
      </template>

      <!-- Backend error - timeout -->
      <template v-else-if="downloadPhase === 'backend-error'">
        <div class="error-state" role="alert" aria-live="assertive">
          <i class="pi pi-exclamation-triangle error-icon"></i>
          <h3>No se pudo conectar</h3>
          <p class="error-message">{{ systemStore.backendStartupError || 'El servidor no respondió a tiempo.' }}</p>
          <p class="error-hint">
            Intenta cerrar y volver a abrir la aplicación. Si el problema persiste, verifica que no haya otra instancia ejecutándose.
          </p>
          <button class="retry-button" @click="retryStartup">
            <i class="pi pi-refresh"></i>
            Reintentar
          </button>
        </div>
      </template>

      <!-- Checking state -->
      <template v-else-if="downloadPhase === 'checking'">
        <div class="checking-state">
          <i class="pi pi-spin pi-spinner checking-spinner"></i>
          <p>Verificando configuración...</p>
        </div>
      </template>

      <!-- Installing dependencies state -->
      <template v-else-if="downloadPhase === 'installing-deps'">
        <div class="download-progress" role="status" aria-live="polite">
          <div class="download-header">
            <i class="pi pi-cog pi-spin download-icon"></i>
            <div>
              <h3>Instalando componentes</h3>
              <p class="subtitle">Configurando dependencias de Python</p>
            </div>
          </div>

          <div class="progress-section">
            <div class="progress-info">
              <span class="current-model">Instalando numpy, spaCy, transformers...</span>
              <span class="progress-phase">En progreso</span>
            </div>
            <!-- Barra indeterminada para dependencias (no tenemos progreso real) -->
            <ProgressBar
              mode="indeterminate"
              class="progress-bar"
            />
          </div>

          <p class="download-note">
            <i class="pi pi-info-circle"></i>
            Esta instalación solo se realiza una vez. Puede tardar unos minutos.
          </p>
        </div>
      </template>

      <!-- Downloading state (automatic) -->
      <template v-else-if="downloadPhase === 'downloading'">
        <div class="download-progress" role="status" aria-live="polite">
          <div class="download-header">
            <i class="pi pi-download download-icon"></i>
            <div>
              <h3>Completando instalación</h3>
              <p class="subtitle">Descargando modelos de análisis de texto</p>
            </div>
          </div>

          <div class="progress-section">
            <div class="progress-info">
              <span class="current-model">{{ currentModel }}</span>
              <span v-if="displayProgress !== null" class="progress-percent">{{ displayProgress }}%</span>
              <span v-else class="progress-phase">Descargando...</span>
            </div>

            <!-- Barra de progreso: determinada si hay progreso real, indeterminada si no -->
            <ProgressBar
              v-if="displayProgress !== null"
              :value="displayProgress"
              :show-value="false"
              class="progress-bar"
            />
            <ProgressBar
              v-else
              mode="indeterminate"
              class="progress-bar"
            />

            <!-- Info de velocidad y bytes (solo si hay progreso real) -->
            <div v-if="downloadInfo" class="download-stats">
              <span class="download-bytes">{{ downloadInfo.downloaded }} / {{ downloadInfo.total }}</span>
              <span v-if="downloadInfo.speed" class="download-speed">{{ downloadInfo.speed }}</span>
            </div>
          </div>

          <div class="models-list">
            <div v-for="model in allModels" :key="model.type" class="model-item">
              <i
                class="pi" :class="
                  model.installed || isModelCompleted(model.type)
                    ? 'pi-check-circle text-green'
                    : isModelDownloading(model.type)
                      ? 'pi-spin pi-spinner text-blue'
                      : isModelPending(model.type)
                        ? 'pi-clock text-muted'
                        : 'pi-circle'
                "
              ></i>
              <span class="model-name">{{ model.displayName }}</span>
              <span class="model-size">
                <template v-if="model.installed && !isModelDownloading(model.type)">Instalado</template>
                <template v-else-if="isModelPending(model.type)">En cola</template>
                <template v-else>~{{ model.sizeMb }} MB</template>
              </span>
            </div>
          </div>

          <p class="download-note">
            <i class="pi pi-info-circle"></i>
            Esta descarga solo se realiza una vez. Tamaño total: ~{{ totalDownloadSize }} MB
          </p>
        </div>
      </template>

      <!-- Completed state -->
      <template v-else-if="downloadPhase === 'completed'">
        <div class="download-complete">
          <i class="pi pi-check-circle complete-icon"></i>
          <h3>Listo para usar</h3>
          <p>Narrative Assistant está preparado.</p>
        </div>
      </template>

      <!-- Python missing state -->
      <template v-else-if="downloadPhase === 'python-missing'">
        <div class="python-missing-state" role="alert" aria-live="assertive">
          <i class="pi pi-exclamation-circle python-icon"></i>
          <h3>Python 3.10+ requerido</h3>
          <p class="python-message">
            Narrative Assistant necesita Python 3.10 o superior para funcionar correctamente.
          </p>
          <p v-if="systemStore.pythonError" class="error-detail">
            {{ systemStore.pythonError }}
          </p>
          <div class="python-instructions">
            <p><strong>Para instalar Python:</strong></p>
            <ol>
              <li>Descarga Python desde <a href="https://www.python.org/downloads/" target="_blank" class="python-link">python.org/downloads</a></li>
              <li>Ejecuta el instalador y <strong>marca "Add Python to PATH"</strong></li>
              <li>Reinicia Narrative Assistant</li>
            </ol>
          </div>
          <div class="python-actions">
            <a
              href="https://www.python.org/downloads/"
              target="_blank"
              class="download-python-button"
            >
              <i class="pi pi-external-link"></i>
              Descargar Python
            </a>
            <button class="retry-button secondary" @click="recheckPython">
              <i class="pi pi-refresh"></i>
              Verificar de nuevo
            </button>
          </div>
        </div>
      </template>

      <!-- Error state -->
      <template v-else-if="downloadPhase === 'error'">
        <div class="error-state" role="alert" aria-live="assertive">
          <i class="pi pi-exclamation-triangle error-icon"></i>
          <h3>Error en la descarga</h3>
          <p class="error-message">{{ systemStore.modelsError }}</p>
          <p class="error-hint">
            Verifica tu conexión a internet e intenta de nuevo.
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

.starting-title {
  margin: 0 0 0.25rem 0;
  font-size: 1.25rem;
  color: var(--p-text-color);
}

.starting-subtitle {
  margin: 0;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
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

.progress-phase {
  color: var(--p-text-muted-color);
  font-style: italic;
}

.download-stats {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  font-size: 0.8rem;
  color: var(--p-text-muted-color);
}

.download-bytes {
  font-family: monospace;
}

.download-speed {
  color: var(--p-primary-color);
  font-weight: 500;
}

.model-item i.text-blue {
  color: var(--p-primary-color);
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

.model-item i.text-muted {
  color: var(--p-text-muted-color);
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

.retry-button.secondary {
  background: var(--p-surface-200);
  color: var(--p-text-color);
}

.retry-button.secondary:hover {
  background: var(--p-surface-300);
}

/* Python missing state */
.python-missing-state {
  text-align: center;
  padding: 1.5rem;
}

.python-icon {
  font-size: 3.5rem;
  color: var(--p-orange-500);
  margin-bottom: 1rem;
}

.python-missing-state h3 {
  margin: 0 0 0.75rem 0;
  color: var(--p-orange-700);
  font-size: 1.25rem;
}

.python-message {
  color: var(--p-text-color);
  margin: 0 0 0.75rem 0;
  font-size: 0.95rem;
}

.error-detail {
  background: var(--p-orange-50);
  color: var(--p-orange-700);
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  margin: 0.75rem 0;
  font-size: 0.85rem;
  font-family: monospace;
}

.python-instructions {
  text-align: left;
  background: var(--p-surface-100);
  border-radius: 8px;
  padding: 1rem 1.25rem;
  margin: 1rem 0;
}

.python-instructions p {
  margin: 0 0 0.5rem 0;
  font-size: 0.9rem;
}

.python-instructions ol {
  margin: 0;
  padding-left: 1.25rem;
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
}

.python-instructions li {
  margin-bottom: 0.5rem;
}

.python-instructions li:last-child {
  margin-bottom: 0;
}

.python-link {
  color: var(--p-primary-color);
  text-decoration: none;
  font-weight: 500;
}

.python-link:hover {
  text-decoration: underline;
}

.python-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
  margin-top: 1rem;
}

.download-python-button {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  background: var(--p-primary-color);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.875rem;
  text-decoration: none;
  cursor: pointer;
  transition: background 0.2s;
}

.download-python-button:hover {
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

.dark .python-missing-state h3 {
  color: var(--p-orange-400);
}

.dark .error-detail {
  background: var(--p-orange-900);
  color: var(--p-orange-300);
}

.dark .python-instructions {
  background: var(--p-surface-800);
}

.dark .retry-button.secondary {
  background: var(--p-surface-700);
}

.dark .retry-button.secondary:hover {
  background: var(--p-surface-600);
}
</style>
