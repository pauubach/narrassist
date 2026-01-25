import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiUrl } from '@/config/api'

export interface ModelStatus {
  installed: boolean
  display_name: string
  size_mb: number
  path?: string
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

export const useSystemStore = defineStore('system', () => {
  const backendConnected = ref(false)
  const backendVersion = ref('unknown')

  // Model status
  const modelsStatus = ref<ModelsStatus | null>(null)
  const modelsLoading = ref(false)
  const modelsDownloading = ref(false)
  const modelsError = ref<string | null>(null)

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
      } else {
        backendConnected.value = false
      }
    } catch (error) {
      backendConnected.value = false
    }
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

  // Check backend status on store creation
  checkBackendStatus()

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

  return {
    // State
    backendConnected,
    backendVersion,
    modelsStatus,
    modelsLoading,
    modelsDownloading,
    modelsError,

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
    checkModelsStatus,
    downloadModels,
    installDependencies,
    stopPolling
  }
})
