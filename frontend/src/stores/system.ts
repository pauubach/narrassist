import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
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
  install_progress?: string | null  // ME-04: granular install phase description
  needs_restart?: boolean  // HI-04: frozen mode requires app restart
  // Python status fields
  python_available?: boolean
  python_version?: string | null
  python_path?: string | null
  python_error?: string | null
}

export interface SystemCapabilities {
  detection_status?: 'complete' | 'uncertain'
  detection_warnings?: string[]
  hardware: {
    gpu: { type: string; name: string; memory_gb: number | null; device_id: number } | null
    gpu_type: string
    has_gpu: boolean
    has_high_vram: boolean
    has_cupy: boolean
    gpu_blocked: { name: string; compute_capability: number; min_required: number } | null
    cpu: { name: string }
  }
  embeddings_available: boolean
  ollama: {
    installed: boolean
    available: boolean
    hardware_supported?: boolean  // HI-05: tri-axis
    models: Array<{ name: string; size: number; modified: string }>
    recommended_models: string[]
    init_status?: string
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

export interface LLMReadiness {
  ready: boolean
  ollama_installed: boolean
  ollama_running: boolean
  configured_level: string
  missing_models: string[]
  available_models: string[]
  has_any_model: boolean
}

interface BackendHealthStatus {
  status: string
  version?: string
  backend_loaded?: boolean
  timestamp?: string
}

export interface NLPMethod {
  name: string
  description: string
  weight?: number
  available: boolean
  hardware_supported?: boolean   // HI-05: can this hardware run it?
  requires_ollama?: boolean      // HI-05: needs Ollama service?
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
  let retryInterval: number | null = null

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

  // LLM readiness (auto-download tracking)
  const llmDownloadingModels = ref<string[]>([])

  // HI-02: Structured auto-config error tracking
  const autoConfigErrors = ref<string[]>([])

  // HI-03: LLM download visibility
  const isLlmDownloading = computed(() => llmDownloadingModels.value.length > 0)
  let llmHeartbeatTimer: ReturnType<typeof setInterval> | null = null
  let llmHeartbeatWarned = false
  let backendHealthWarned = false
  let modelProgressPollErrorCount = 0

  function startLlmHeartbeat() {
    if (llmHeartbeatTimer) return
    llmHeartbeatTimer = setInterval(async () => {
      try {
        const result = await api.getRaw<{ data: LLMReadiness }>('/api/services/llm/readiness')
        const data = result?.data
        if (data?.ready || !data?.missing_models?.length) {
          llmDownloadingModels.value = []
          stopLlmHeartbeat()
        }
        llmHeartbeatWarned = false
      } catch (error) {
        if (!llmHeartbeatWarned) {
          const msg = error instanceof Error ? error.message : String(error)
          console.warn('[autoConfig] No se pudo comprobar el estado de los motores en segundo plano:', msg)
          autoConfigErrors.value.push(`LLM heartbeat: ${msg}`)
          llmHeartbeatWarned = true
        }
      }
    }, 10000)
  }

  function stopLlmHeartbeat() {
    if (llmHeartbeatTimer) {
      clearInterval(llmHeartbeatTimer)
      llmHeartbeatTimer = null
    }
  }

  // HI-04: Restart detection
  const needsRestart = computed(() => modelsStatus.value?.needs_restart === true)

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
  // ME-04: Granular install progress from backend
  const installProgress = computed(() => modelsStatus.value?.install_progress ?? null)

  // Python availability
  const pythonAvailable = computed(() => modelsStatus.value?.python_available ?? true)
  const pythonVersion = computed(() => modelsStatus.value?.python_version ?? null)
  const pythonError = computed(() => modelsStatus.value?.python_error ?? null)

  function applyBackendHealthStatus(data: BackendHealthStatus) {
    backendConnected.value = data.status === 'ok'
    backendVersion.value = data.version || 'unknown'
    backendHealthWarned = false
    if (backendConnected.value) {
      backendReady.value = true
      backendStarting.value = false
      backendStartupError.value = null
    }
  }

  async function checkBackendStatus() {
    try {
      const data = await api.getRaw<BackendHealthStatus>('/api/health', { timeout: 5000 })
      applyBackendHealthStatus(data)
    } catch (error) {
      backendConnected.value = false
      if (!backendHealthWarned) {
        const msg = error instanceof Error ? error.message : String(error)
        console.warn('[system] Health check no disponible, reintentando:', msg)
        backendHealthWarned = true
      }
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
    let warned = false

    while (Date.now() - startTime < timeoutMs) {
      try {
        const data = await api.getRaw<BackendHealthStatus>('/api/health', { timeout: 5000 })
        applyBackendHealthStatus(data)
        warned = false
        return backendConnected.value
      } catch (error) {
        // Backend no disponible todavia, reintentar
        if (!warned) {
          const msg = error instanceof Error ? error.message : String(error)
          console.warn('[system] Esperando a que el motor de analisis responda:', msg)
          warned = true
        }
      }
      await new Promise(resolve => setTimeout(resolve, delay))
      delay = Math.min(delay + 250, 2000) // incrementar hasta 2s max
    }

    // Timeout
    backendStarting.value = false
    backendStartupError.value = 'El motor de análisis no se inició a tiempo. Reinicia la aplicación.'
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
      modelsError.value = error instanceof Error ? error.message : 'Error de comunicación interna'
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
      modelsError.value = error instanceof Error ? error.message : 'Error de comunicación interna'
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

      if (!response) {
        modelProgressPollErrorCount += 1
        if (modelProgressPollErrorCount === 1) {
          console.warn('[models] El progreso de descarga no respondio, reintentando...')
        }
        if (modelProgressPollErrorCount >= 8) {
          modelsError.value = 'No pudimos actualizar el progreso de la descarga. El sistema puede seguir ocupado; espera unos segundos y reintenta.'
          stopPolling()
          modelsDownloading.value = false
        }
        return
      }

      if (response) {
        modelProgressPollErrorCount = 0
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
    } catch (error) {
      modelProgressPollErrorCount += 1
      if (modelProgressPollErrorCount === 1) {
        const msg = error instanceof Error ? error.message : String(error)
        console.warn('[models] No se pudo consultar el progreso de descarga:', msg)
      }
      if (modelProgressPollErrorCount >= 8) {
        modelsError.value = 'No pudimos actualizar el progreso de la descarga. El sistema puede seguir ocupado; espera unos segundos y reintenta.'
        stopPolling()
        modelsDownloading.value = false
      }
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
    modelProgressPollErrorCount = 0
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
      modelsError.value = error instanceof Error ? error.message : 'Error de comunicación interna'
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
            if (pollCount === 1) {
              console.warn('[languagetool] Error temporal comprobando instalacion, reintentando...')
            }
            // Show connection issue to user via progress UI
            if (pollCount > 5 && !ltInstallProgress.value) {
              ltInstallProgress.value = {
                phase: 'error',
                phase_label: 'Error',
                percentage: 0,
                detail: 'Se perdió la comunicación con el motor de análisis. Reinicia la aplicación.',
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
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      console.warn('[languagetool] Error iniciando instalacion:', msg)
      ltInstallProgress.value = {
        phase: 'error',
        phase_label: 'Error',
        percentage: 0,
        detail: 'No se pudo iniciar la instalacion del corrector avanzado. El sistema puede seguir ocupado; espera unos segundos y vuelve a intentarlo.',
        error: 'install_start_failed',
      }
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
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      console.warn('[languagetool] No se pudo iniciar el corrector avanzado:', msg)
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

  // =========================================================================
  // Auto-config on startup (PP-3b)
  // =========================================================================

  /**
   * Auto-configura hardware y servicios al primer arranque.
   * - Aplica config recomendada si no hay settings previos
   * - Inicia Ollama si está instalado pero no corriendo
   * - Descarga modelo por defecto si Ollama está listo pero sin modelos
   * Ejecutar en background después de que modelos NLP estén listos.
   */
  let _autoConfigRunning = false
  async function autoConfigOnStartup(): Promise<void> {
    // Guard idempotente: evitar ejecución concurrente (HI-22)
    if (_autoConfigRunning) return
    _autoConfigRunning = true
    try {
      // Asegurar que capabilities están cargadas
      const caps = await loadCapabilities()
      if (!caps) return

      // 1. Aplicar config recomendada si es primera vez
      const savedSettings = localStorage.getItem('narrative_assistant_settings')
      if (!savedSettings) {
        const methods = caps.nlp_methods
        const enabledMethods: Record<string, string[]> = {
          coreference: [], ner: [], grammar: [], spelling: [], character_knowledge: [],
        }

        for (const category of ['coreference', 'ner', 'grammar', 'spelling', 'character_knowledge'] as const) {
          const catMethods = methods[category]
          if (catMethods) {
            for (const [key, method] of Object.entries(catMethods)) {
              if (method.available && method.default_enabled) {
                enabledMethods[category].push(key)
              }
            }
          }
        }

        const defaultSettings = { enabledNLPMethods: enabledMethods }
        localStorage.setItem('narrative_assistant_settings', JSON.stringify(defaultSettings))
        window.dispatchEvent(new CustomEvent('settings-changed', { detail: defaultSettings }))
      }

      // 2. Auto-iniciar Ollama si está instalado pero no corriendo
      const ollama = caps.ollama
      if (ollama?.installed && !ollama?.available) {
        try {
          await api.postRaw('/api/ollama/start')
          // Esperar a que arranque
          await new Promise(r => setTimeout(r, 3000))
          await refreshCapabilities()
        } catch (e) {
          // HI-02: log structured warning instead of silent swallow
          const msg = e instanceof Error ? e.message : String(e)
          console.warn('[autoConfig] Ollama start failed:', msg)
          autoConfigErrors.value.push(`Ollama start: ${msg}`)
        }
      }

      // 3. Verificar readiness LLM y descargar modelos faltantes
      // Nota: las descargas son asíncronas (fire-and-forget desde aquí).
      // El ModelSetupDialog usa su propio flujo con polling para esperar.
      const updatedCaps = systemCapabilities.value
      if (updatedCaps?.ollama?.available) {
        try {
          const readiness = await api.getRaw<{ data: LLMReadiness }>('/api/services/llm/readiness')
          const data = readiness?.data
          if (data && !data.ready && data.missing_models?.length > 0) {
            llmDownloadingModels.value = data.missing_models
            // CR-06: descargas gestionadas por ModelSetupDialog — no iniciar aquí
            // para evitar doble orquestación y toasts de error espurios.
            // HI-03: start heartbeat to track background LLM downloads
            startLlmHeartbeat()
          }
        } catch (e) {
          // HI-02: log structured warning instead of silent swallow
          const msg = e instanceof Error ? e.message : String(e)
          console.warn('[autoConfig] LLM readiness check failed:', msg)
          autoConfigErrors.value.push(`LLM readiness: ${msg}`)
          // HI-03: don't clear llmDownloadingModels here — heartbeat handles it
        }
      }
    } catch (e) {
      // HI-02: log structured warning for outer auto-config failure
      const msg = e instanceof Error ? e.message : String(e)
      console.warn('[autoConfig] autoConfigOnStartup failed:', msg)
      autoConfigErrors.value.push(`autoConfig: ${msg}`)
    } finally {
      _autoConfigRunning = false
    }
  }

  // ── Backend retry ─────────────────────────────────────
  function startRetrying() {
    if (retryInterval) return
    retryInterval = window.setInterval(async () => {
      if (!backendConnected.value) {
        await checkBackendStatus()
      } else {
        stopRetrying()
      }
    }, 3000)
  }

  function stopRetrying() {
    if (retryInterval) {
      clearInterval(retryInterval)
      retryInterval = null
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
    installProgress,
    pythonAvailable,
    pythonVersion,
    pythonError,

    // Actions
    checkBackendStatus,
    waitForBackend,
    startRetrying,
    stopRetrying,
    checkModelsStatus,
    downloadModels,
    installDependencies,
    loadCapabilities,
    refreshCapabilities,
    stopPolling,

    // LanguageTool actions
    installLanguageTool,
    startLanguageTool,
    stopLTPolling,

    // LLM readiness
    llmDownloadingModels,
    isLlmDownloading,      // HI-03
    startLlmHeartbeat,     // HI-03
    stopLlmHeartbeat,      // HI-03

    // HI-02: structured auto-config errors
    autoConfigErrors,

    // HI-04: restart detection
    needsRestart,

    // Auto-config
    autoConfigOnStartup,
  }
})
