import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiUrl } from '@/config/api'

export interface ModelStatus {
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
    } catch (error) {
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
      const response = await fetch(apiUrl('/api/models/status'))
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          modelsStatus.value = data.data
          return data.data
        } else {
          modelsError.value = data.error || 'Error checking models'
        }
      } else {
        modelsError.value = 'Failed to check models status'
      }
    } catch (error) {
      modelsError.value = error instanceof Error ? error.message : 'Network error'
    } finally {
      modelsLoading.value = false
    }
    return null
  }

  async function downloadModels(models: string[] = ['spacy', 'embeddings'], force = false): Promise<boolean> {
    modelsDownloading.value = true
    modelsError.value = null

    try {
      const response = await fetch(apiUrl('/api/models/download'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ models, force })
      })

      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          // Start polling for status
          pollModelsStatus()
          return true
        } else {
          modelsError.value = data.error || 'Error starting download'
        }
      } else {
        // Try to get error detail from response
        try {
          const errorData = await response.json()
          modelsError.value = errorData.detail || `Failed to start model download (${response.status})`
        } catch {
          modelsError.value = `Failed to start model download (${response.status})`
        }
      }
    } catch (error) {
      modelsError.value = error instanceof Error ? error.message : 'Network error'
    } finally {
      modelsDownloading.value = false
    }
    return false
  }

  // Poll models status while downloading
  let pollInterval: number | null = null

  function pollModelsStatus() {
    if (pollInterval) return

    pollInterval = window.setInterval(async () => {
      const status = await checkModelsStatus()
      if (status?.all_required_installed) {
        // All models ready, stop polling
        if (pollInterval) {
          clearInterval(pollInterval)
          pollInterval = null
        }
        modelsDownloading.value = false
      }
    }, 3000) // Check every 3 seconds
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
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
      const response = await fetch(apiUrl('/api/system/capabilities'))
      if (response.ok) {
        const result = await response.json()
        if (result.success && result.data) {
          systemCapabilities.value = result.data
          return result.data
        }
      }
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
    try {
      const response = await fetch(apiUrl('/api/system/capabilities'))
      if (response.ok) {
        const result = await response.json()
        if (result.success && result.data) {
          systemCapabilities.value = result.data
        }
      }
    } catch {
      // Silent refresh, don't report errors
    }
  }

  async function installDependencies(): Promise<boolean> {
    modelsError.value = null
    
    try {
      const response = await fetch(apiUrl('/api/dependencies/install'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.success) {
          // Start polling for status
          pollModelsStatus()
          return true
        } else {
          modelsError.value = data.error || 'Error installing dependencies'
        }
      } else {
        modelsError.value = 'Failed to install dependencies'
      }
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
      const resp = await fetch(apiUrl('/api/languagetool/install'), { method: 'POST' })
      const result = await resp.json()

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
            const statusResp = await fetch(apiUrl('/api/languagetool/status'))
            const statusResult = await statusResp.json()
            const data = statusResult.data
            const status = data?.status

            // Update progress if available
            if (data?.install_progress) {
              ltInstallProgress.value = data.install_progress
            }

            // Wait for a definitive installed state
            if (status === 'installed_not_running' || status === 'running') {
              stopLTPolling()
              // Refresh capabilities BEFORE clearing flag to avoid UI flash
              await refreshCapabilities()
              ltInstalling.value = false
              ltInstallProgress.value = null
              resolve(true)
            }
          } catch {
            // Ignore polling errors
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
      await fetch(apiUrl('/api/languagetool/start'), { method: 'POST' })
      await new Promise(r => setTimeout(r, 2000))
      await refreshCapabilities()
      return true
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
