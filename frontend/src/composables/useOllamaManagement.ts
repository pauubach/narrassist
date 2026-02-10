/**
 * Composable: Ollama lifecycle management (install, start, download model).
 *
 * Encapsulates the Ollama state machine (not_installed → not_running → no_models → ready)
 * and all related API calls, download polling, and toast notifications.
 */

import { ref, computed } from 'vue'
import { api } from '@/services/apiClient'
import { useToast } from 'primevue/usetoast'
import { useSystemStore } from '@/stores/system'

// ── Types ──────────────────────────────────────────────────

export type OllamaState = 'not_installed' | 'not_running' | 'no_models' | 'ready'

// ── Composable ─────────────────────────────────────────────

export function useOllamaManagement() {
  const toast = useToast()
  const systemStore = useSystemStore()

  const systemCapabilities = computed(() => systemStore.systemCapabilities)

  // UI state
  const ollamaStarting = ref(false)
  const modelDownloading = ref(false)
  const ollamaDownloadProgress = ref<{ percentage: number; status: string; error?: string } | null>(null)
  let ollamaDownloadPollTimer: ReturnType<typeof setInterval> | null = null

  // ── State machine ───────────────────────────────────────

  const ollamaState = computed<OllamaState>(() => {
    if (!systemCapabilities.value) return 'not_installed'
    const ollama = systemCapabilities.value.ollama
    if (!ollama.installed) return 'not_installed'
    if (!ollama.available) return 'not_running'
    if (ollama.models.length === 0) return 'no_models'
    return 'ready'
  })

  const ollamaActionConfig = computed(() => {
    const configs: Record<OllamaState, { label: string; icon: string; severity: string; action: () => void }> = {
      not_installed: {
        label: 'Instalar analizador',
        icon: 'pi pi-download',
        severity: 'warning',
        action: installOllama,
      },
      not_running: {
        label: 'Iniciar analizador',
        icon: 'pi pi-play',
        severity: 'warning',
        action: startOllama,
      },
      no_models: {
        label: 'Descargar modelo',
        icon: 'pi pi-download',
        severity: 'info',
        action: downloadDefaultModel,
      },
      ready: {
        label: 'Listo',
        icon: 'pi pi-check',
        severity: 'success',
        action: () => {},
      },
    }
    return configs[ollamaState.value]
  })

  const ollamaStatusMessage = computed(() => {
    const messages: Record<OllamaState, string> = {
      not_installed: 'Necesitas instalar el motor de an\u00E1lisis sem\u00E1ntico',
      not_running: 'El analizador est\u00E1 instalado pero no se ha iniciado',
      no_models: 'El analizador est\u00E1 listo, pero necesitas descargar un modelo',
      ready: `${systemCapabilities.value?.ollama.models.length || 0} modelo(s) disponible(s)`,
    }
    return messages[ollamaState.value]
  })

  // ── Helpers ─────────────────────────────────────────────

  async function reloadCapabilities() {
    await systemStore.loadCapabilities(true)
  }

  function stopOllamaDownloadPolling() {
    if (ollamaDownloadPollTimer) {
      clearInterval(ollamaDownloadPollTimer)
      ollamaDownloadPollTimer = null
    }
  }

  // ── Install ─────────────────────────────────────────────

  async function installOllama() {
    ollamaStarting.value = true
    try {
      const result = await api.postRaw<{ success: boolean }>('/api/ollama/install')
      if (result.success) {
        toast.add({ severity: 'info', summary: 'Instalando Ollama', detail: 'Descargando e instalando...', life: 5000 })
        await new Promise(resolve => setTimeout(resolve, 5000))
        await reloadCapabilities()
        if (systemCapabilities.value?.ollama?.installed) {
          toast.add({ severity: 'success', summary: 'Ollama instalado', detail: 'Ahora puedes iniciar el analizador', life: 3000 })
        }
      } else {
        openOllamaDownload()
      }
    } catch {
      openOllamaDownload()
    } finally {
      ollamaStarting.value = false
    }
  }

  // ── Start ───────────────────────────────────────────────

  async function startOllama() {
    ollamaStarting.value = true
    try {
      const result = await api.postRaw<{ success: boolean; data?: any; error?: string }>('/api/ollama/start')

      if (result.success) {
        await new Promise(resolve => setTimeout(resolve, 2000))
        await reloadCapabilities()

        if (systemCapabilities.value?.ollama?.available) {
          toast.add({ severity: 'success', summary: 'Analizador iniciado', detail: 'El analizador sem\u00E1ntico est\u00E1 ahora disponible', life: 3000 })
        } else {
          toast.add({ severity: 'warn', summary: 'Estado incierto', detail: 'El analizador puede estar iniciando. Recarga la p\u00E1gina en unos segundos.', life: 5000 })
        }
      } else {
        if (result.data?.action_required === 'install') {
          toast.add({ severity: 'warn', summary: 'Analizador no instalado', detail: 'Necesitas instalar el motor de an\u00E1lisis primero', life: 5000 })
        } else {
          toast.add({ severity: 'error', summary: 'Error al iniciar', detail: result.error || 'No se pudo iniciar el analizador', life: 5000 })
        }
      }
    } catch (error) {
      console.error('Error starting Ollama:', error)
      toast.add({ severity: 'error', summary: 'Error de conexi\u00F3n', detail: 'No se pudo conectar con el servidor', life: 3000 })
    } finally {
      ollamaStarting.value = false
    }
  }

  // ── Browser fallback ────────────────────────────────────

  function openOllamaDownload() {
    window.open('https://ollama.com/download', '_blank')
    toast.add({ severity: 'info', summary: 'Configuraci\u00F3n del analizador', detail: 'Despu\u00E9s de instalar, vuelve aqu\u00ED y haz clic en "Iniciar analizador"', life: 5000 })
  }

  // ── Download model ──────────────────────────────────────

  async function downloadDefaultModel() {
    modelDownloading.value = true
    ollamaDownloadProgress.value = null
    toast.add({ severity: 'info', summary: 'Descargando modelo', detail: 'Descargando modelo de an\u00E1lisis (~2GB). Esto puede tardar varios minutos...', life: 5000 })

    try {
      const result = await api.postRaw<{ success: boolean; error?: string }>('/api/ollama/pull/llama3.2')
      if (!result.success) {
        toast.add({ severity: 'error', summary: 'Error', detail: result.error || 'No se pudo iniciar la descarga', life: 5000 })
        modelDownloading.value = false
        return
      }

      let pollCount = 0
      ollamaDownloadPollTimer = setInterval(async () => {
        pollCount++
        if (pollCount > 900) {
          stopOllamaDownloadPolling()
          modelDownloading.value = false
          ollamaDownloadProgress.value = null
          toast.add({ severity: 'error', summary: 'Timeout', detail: 'La descarga tard\u00F3 demasiado', life: 5000 })
          return
        }

        try {
          const statusResult = await api.getRaw<any>('/api/ollama/status')
          const dp = statusResult.data?.download_progress
          if (dp) {
            ollamaDownloadProgress.value = dp
          }

          if (dp?.status === 'complete' || (!statusResult.data?.is_downloading && statusResult.data?.downloaded_models?.includes('llama3.2'))) {
            stopOllamaDownloadPolling()
            ollamaDownloadProgress.value = null
            modelDownloading.value = false
            await reloadCapabilities()
            toast.add({ severity: 'success', summary: 'Modelo descargado', detail: 'An\u00E1lisis sem\u00E1ntico disponible', life: 3000 })
            return
          }

          if (dp?.status === 'error') {
            stopOllamaDownloadPolling()
            ollamaDownloadProgress.value = null
            modelDownloading.value = false
            toast.add({ severity: 'error', summary: 'Error', detail: dp.error || 'Error descargando modelo', life: 5000 })
            return
          }
        } catch {
          // Ignore poll errors
        }
      }, 1000)
    } catch {
      toast.add({ severity: 'error', summary: 'Error de conexi\u00F3n', detail: 'No se pudo conectar con el servidor', life: 3000 })
      modelDownloading.value = false
    }
  }

  // ── Cleanup ─────────────────────────────────────────────

  function cleanup() {
    stopOllamaDownloadPolling()
  }

  return {
    ollamaState,
    ollamaActionConfig,
    ollamaStatusMessage,
    ollamaStarting,
    modelDownloading,
    ollamaDownloadProgress,
    installOllama,
    startOllama,
    openOllamaDownload,
    downloadDefaultModel,
    cleanup,
  }
}
