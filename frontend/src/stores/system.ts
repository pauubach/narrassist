import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiUrl } from '@/config/api'
import { api } from '@/services/apiClient'

export interface ModelStatus {
  type: string
  installed: boolean
  display_name: string
  size_mb: number
  path?: string
}

// LanguageTool install progress
export interface LTInstallProgress {
  phase: string
  phase_label: string
  percentage: number
  detail: string
  error?: string
}

export type LTState = 'not_installed' | 'installing' | 'installed_not_running' | 'running'

// Download progress info for real-time updates
export interface DownloadProgressInfo {
  model_type: string
  phase: string
  bytes_downloaded: number
  bytes_total: number
  percent: number
  speed_bps: number
  speed_mbps: number
  eta_seconds: number | null
  error: string | null
}

export interface ModelsStatus {
  nlp_models: Record<string, ModelStatus>
  ollama: {
    installed: boolean
    models: string[]
  }
  all_required_installed: boolean
  backend_loaded?: boolean
  dependencies_needed?: boolean
  dependencies_status?: Record<string, boolean>
  all_installed?: boolean
  installing?: boolean
  // Python status fields
  python_available?: boolean
  python_version?: string | null
  python_path?: string | null
  python_error?: string | null
}

export interface SystemCapabilities {
  hardware: {
    gpu: { type: string; name: string; memory_gb: number | null; device_id: number } | null
    gpu_type: string
    has_gpu: boolean
    has_high_vram: boolean
    has_cupy: boolean
    gpu_blocked: { name: string; compute_capability: number; min_required: number } | null
    cpu: { name: string }
  }
  ollama: {
    installed: boolean
    available: boolean
    models: Array<{ name: string; size: number; modified: string }>
    recommended_models: string[]
  }
  languagetool?: {
    installed: boolean
    running: boolean
    installing: boolean
    java_available: boolean
  }
  nlp_methods: {
    coreference: Record<string, NLPMethod>
    ner: Record<string, NLPMethod>
    grammar: Record<string, NLPMethod>
    spelling?: Record<string, NLPMethod>
    character_knowledge?: Record<string, NLPMethod>
  }
  recommended_config: {
    device_preference: string
    spacy_gpu_enabled: boolean
    embeddings_gpu_enabled: boolean
    batch_size: number
  }
}

export interface NLPMethod {
  name: string
  description: string
  weight?: number
  available: boolean
  default_enabled: boolean
  requires_gpu: boolean
  recommended_gpu: boolean
}

export const useSystemStore = defineStore('system', () => {
  const backendConnected = ref(false)
  const backendVersion = ref('unknown')
  /** true una vez que el backend responde al health check por primera vez */
  const backendReady = ref(false)
  /** true mientras se espera la primera respuesta del backend */
  const backendStarting = ref(true)
  /** Error de timeout si el backend no responde a tiempo */
  const backendStartupError = ref<string | null>(null)

  // Model status
  const modelsStatus = ref<ModelsStatus | null>(null)
  const modelsLoading = ref(false)
  const modelsDownloading = ref(false)
  const modelsError = ref<string | null>(null)

  // Download progress (real-time)
  const downloadProgress = ref<Record<string, DownloadProgressInfo>>({})
  const modelSizes = ref<Record<string, number>>({
    spacy: 540 * 1024 * 1024,
    embeddings: 470 * 1024 * 1024,
    transformer_ner: 500 * 1024 * 1024,
    total: 1510 * 1024 * 1024,
  })

  // System capabilities (cached - loaded once at startup)
  const systemCapabilities = ref<SystemCapabilities | null>(null)
  const capabilitiesLoading = ref(false)

  // LanguageTool state (centralized)
  const ltInstalling = ref(false)
  const ltStarting = ref(false)
  const ltInstallProgress = ref<LTInstallProgress | null>(null)
  let ltPollTimer: ReturnType<typeof setInterval> | null = null

  // Computed: LanguageTool state
  const ltState = computed<LTState>(() => {
    const lt = systemCapabilities.value?.languagetool
    if (!lt) return 'not_installed'
    if (lt.installing || ltInstalling.value) return 'installing'
    if (!lt.installed) return 'not_installed'
    if (!lt.running) return 'installed_not_running'
    return 'running'
  })

  // Computed: are all required models installed?
  const modelsReady = computed(() => modelsStatus.value?.all_required_installed ?? false)
  const dependenciesInstalling = computed(() => modelsStatus.value?.installing ?? false)
  const dependenciesNeeded = computed(() => modelsStatus.value?.dependencies_needed ?? false)
  const backendLoaded = computed(() => modelsStatus.value?.backend_loaded ?? false)

  // Python availability
  const pythonAvailable = computed(() => modelsStatus.value?.python_available ?? true)
  const pythonVersion = computed(() => modelsStatus.value?.python_version ?? null)
  const pythonError = computed(() => modelsStatus.value?.python_error ?? null)

  async function checkBackendStatus() {
    try {
      const response = await fetch(apiUrl('/api/health'))
      if (response.ok) {
        const data = await response.json()
        backendConnected.value = data.status === 'ok'
        backendVersion.value = data.version || 'unknown'
        if (!backendReady.value) {
          backendReady.value = true
          backendStarting.value = false
          backendStartupError.value = null
        }
      } else {
        backendConnected.value = false
      }
    } catch (_error) {
      backendConnected.value = false
    }
  }

  /**
   * Espera a que el backend responda al health check.
   * Reintenta con backoff hasta que responde o se supera el timeout.
   * @param timeoutMs - Tiempo máximo de espera (default: 60s)
   * @returns true si el backend respondió, false si timeout
   */
  async function waitForBackend(timeoutMs = 60000): Promise<boolean> {
    if (backendReady.value) return true

    backendStarting.value = true
    backendStartupError.value = null
    const startTime = Date.now()
    let delay = 500 // empezar con 500ms, incrementar hasta 2s

    while (Date.now() - startTime < timeoutMs) {
      try {
        const response = await fetch(apiUrl('/api/health'))
        if (response.ok) {
          const data = await response.json()
          backendConnected.value = data.status === 'ok'
          backendVersion.value = data.version || 'unknown'
          backendReady.value = true
          backendStarting.value = false
          return true
        }
      } catch {
        // Backend no disponible todavia, reintentar
      }
      await new Promise(resolve => setTimeout(resolve, delay))
      delay = Math.min(delay + 250, 2000) // incrementar hasta 2s max
    }

    // Timeout
    backendStarting.value = false
    backendStartupError.value = 'El servidor no respondio a tiempo. Intenta reiniciar la aplicacion.'
    return false
  }

  async function checkModelsStatus(): Promise<ModelsStatus | null> {
    modelsLoading.value = true
    modelsError.value = null

    try {
      const data = await api.get<ModelsStatus>('/api/models/status')
      modelsStatus.value = data
      return data
    } catch (error) {
      modelsError.value = error instanceof Error ? error.message : 'Network error'
    } finally {
      modelsLoading.value = false
    }
    return null
  }

  async function downloadModels(models: string[] = ['spacy', 'embeddings', 'transformer_ner'], force = false): Promise<boolean> {
    modelsDownloading.value = true
    modelsError.value = null

    try {
      await api.post('/api/models/download', { models, force })
      pollModelsStatus()
      return true
    } catch (error) {
      modelsError.value = error instanceof Error ? error.message : 'Network error'
    } finally {
      modelsDownloading.value = false
    }
    return false
  }

  // Poll models status and download progress while downloading
  let pollInterval: number | null = null
  let progressPollInterval: number | null = null

  async function checkDownloadProgress(): Promise<void> {
    try {
      const response = await api.tryGet<{
        active_downloads: Record<string, DownloadProgressInfo>
        has_active: boolean
        model_sizes: Record<string, number>
      }>('/api/models/download/progress')

      if (response) {
        downloadProgress.value = response.active_downloads || {}
        if (response.model_sizes) {
          modelSizes.value = response.model_sizes
        }

        // Detect finished downloads: no active downloads but entries exist
        if (!response.has_active && Object.keys(response.active_downloads || {}).length > 0) {
          const errorDownloads = Object.entries(response.active_downloads || {})
            .filter(([, info]) => info.phase === 'error')
          const allCompleted = Object.values(response.active_downloads || {})
            .every((info) => info.phase === 'completed')

          if (allCompleted) {
            // All downloads completed successfully
            stopPolling()
            modelsDownloading.value = false
          } else if (errorDownloads.length > 0) {
            // Some downloads failed — check if required models are OK
            // (refresh models status to get all_required_installed)
            const status = await checkModelsStatus()
            if (status?.all_required_installed) {
              // Required models OK, optional ones failed — warn but don't block
              const failedNames = errorDownloads.map(([name]) => name).join(', ')
              console.warn(`Optional model download failed: ${failedNames}`)
              stopPolling()
              modelsDownloading.value = false
            } else {
              // Required models missing — show error
              const failedNames = errorDownloads.map(([name]) => name).join(', ')
              modelsError.value = `Error descargando modelo(s): ${failedNames}. Verifica tu conexión e intenta de nuevo.`
              stopPolling()
              modelsDownloading.value = false
            }
          }
        }
      }
    } catch {
      // Ignore errors in progress polling
    }
  }

  function pollModelsStatus() {
    if (pollInterval) return

    // Poll status every 3 seconds
    pollInterval = window.setInterval(async () => {
      const status = await checkModelsStatus()
      if (status?.all_required_installed) {
        // All models ready, stop polling
        stopPolling()
        modelsDownloading.value = false
      }
    }, 3000)

    // Poll progress every 500ms for smooth updates
    if (!progressPollInterval) {
      progressPollInterval = window.setInterval(async () => {
        await checkDownloadProgress()
      }, 500)
    }
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
    if (progressPollInterval) {
      clearInterval(progressPollInterval)
      progressPollInterval = null
    }
    downloadProgress.value = {}
  }

  // No auto-check en creación del store.
  // El ModelSetupDialog llama a waitForBackend() que hace el health check con reintentos.

  /**
   * Carga las capacidades del sistema (hardware, Ollama, LanguageTool, NLP).
   * Se cachea en el store - solo hace fetch si no hay datos previos o si se fuerza.
   */
  async function loadCapabilities(force = false): Promise<SystemCapabilities | null> {
    if (systemCapabilities.value && !force) return systemCapabilities.value

    capabilitiesLoading.value = true
    try {
      systemCapabilities.value = await api.get<SystemCapabilities>('/api/system/capabilities')
      return systemCapabilities.value
    } catch (error) {
      console.error('Error loading system capabilities:', error)
    } finally {
      capabilitiesLoading.value = false
    }
    return null
  }

  /**
   * Refresca solo la parte de capabilities que puede cambiar (Ollama, LT status).
   * No muestra loading spinner, actualiza silenciosamente.
   */
  async function refreshCapabilities(): Promise<void> {
    const data = await api.tryGet<SystemCapabilities>('/api/system/capabilities')
    if (data) systemCapabilities.value = data
  }

  async function installDependencies(): Promise<boolean> {
    modelsError.value = null

    try {
      await api.post('/api/dependencies/install')
      pollModelsStatus()
      return true
    } catch (error) {
      modelsError.value = error instanceof Error ? error.message : 'Network error'
    }
    return false
  }

  // =========================================================================
  // LanguageTool actions (centralized)
  // =========================================================================

  /**
   * Install LanguageTool (Java + LT server).
   * Starts installation and polls for progress until complete.
   */
  async function installLanguageTool(): Promise<boolean> {
    ltInstalling.value = true
    ltInstallProgress.value = null
    let pollCount = 0

    try {
      const result = await api.postRaw<{ success: boolean }>('/api/languagetool/install')

      if (!result.success) {
        ltInstalling.value = false
        return false
      }

      // Start polling for progress
      return new Promise((resolve) => {
        ltPollTimer = setInterval(async () => {
          pollCount++
          // Timeout after 10 minutes (600 * 1s)
          if (pollCount > 600) {
            stopLTPolling()
            ltInstalling.value = false
            ltInstallProgress.value = null
            resolve(false)
            return
          }

          try {
            const data = await api.get<{
              status: string
              is_installing?: boolean
              install_progress?: LTInstallProgress
            }>('/api/languagetool/status')

            // Update progress if available
            if (data?.install_progress) {
              ltInstallProgress.value = data.install_progress
            }

            // Success: installation finished and LT is ready
            if (data?.status === 'installed_not_running' || data?.status === 'running') {
              stopLTPolling()
              await refreshCapabilities()
              ltInstalling.value = false
              ltInstallProgress.value = null
              resolve(true)
              return
            }

            // Failure: progress reports an error
            if (data?.install_progress?.error) {
              stopLTPolling()
              ltInstalling.value = false
              // Keep ltInstallProgress so the UI can show the error briefly
              resolve(false)
              return
            }

            // Failure: install thread finished (not installing) but
            // status reverted to not_installed — give 3s grace period
            // to avoid race with thread startup.
            if (
              data?.status === 'not_installed' &&
              !data?.is_installing &&
              pollCount > 3
            ) {
              stopLTPolling()
              ltInstalling.value = false
              ltInstallProgress.value = null
              resolve(false)
              return
            }
          } catch {
            // Show connection issue to user via progress UI
            if (pollCount > 5 && !ltInstallProgress.value) {
              ltInstallProgress.value = {
                phase: 'error',
                phase_label: 'Error de conexión',
                percentage: 0,
                detail: 'No se pudo conectar con el servidor. Reinicia la aplicación.',
                error: 'connection_lost',
              }
              stopLTPolling()
              ltInstalling.value = false
              resolve(false)
              return
            }
          }
        }, 1000)
      })
    } catch {
      ltInstalling.value = false
      return false
    }
  }

  /**
   * Start LanguageTool server.
   */
  async function startLanguageTool(): Promise<boolean> {
    ltStarting.value = true
    try {
      await api.postRaw('/api/languagetool/start')
      // Dar tiempo a que LT arranque
      await new Promise(r => setTimeout(r, 3000))
      await refreshCapabilities()
      // Verificar que realmente esté corriendo
      return systemCapabilities.value?.languagetool?.running ?? false
    } catch {
      return false
    } finally {
      ltStarting.value = false
    }
  }

  /**
   * Stop LanguageTool polling timer.
   */
  function stopLTPolling() {
    if (ltPollTimer) {
      clearInterval(ltPollTimer)
      ltPollTimer = null
    }
  }

  return {
    // State
    backendConnected,
    backendVersion,
    backendReady,
    backendStarting,
    backendStartupError,
    modelsStatus,
    modelsLoading,
    modelsDownloading,
    modelsError,
    systemCapabilities,
    capabilitiesLoading,

    // Download progress (real-time)
    downloadProgress,
    modelSizes,

    // LanguageTool state
    ltInstalling,
    ltStarting,
    ltInstallProgress,
    ltState,

    // Computed
    modelsReady,
    dependenciesInstalling,
    dependenciesNeeded,
    backendLoaded,
    pythonAvailable,
    pythonVersion,
    pythonError,

    // Actions
    checkBackendStatus,
    waitForBackend,
    checkModelsStatus,
    downloadModels,
    installDependencies,
    loadCapabilities,
    refreshCapabilities,
    stopPolling,

    // LanguageTool actions
    installLanguageTool,
    startLanguageTool,
    stopLTPolling
  }
})
