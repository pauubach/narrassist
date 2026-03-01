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
  const modelOperations = ref<Record<string, 'installing' | 'uninstalling'>>({})
  let ollamaDownloadPollTimer: ReturnType<typeof setInterval> | null = null

  // Download queue: backend only allows one download at a time
  let downloadChain: Promise<void> = Promise.resolve()

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
        label: 'Instalar motor',
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
      not_installed: 'Necesitas instalar el analizador semántico',
      not_running: 'El analizador está instalado pero no se ha iniciado',
      no_models: 'El analizador está listo, pero necesitas instalar un motor de análisis',
      ready: (() => {
        const count = systemCapabilities.value?.ollama.models.length || 0
        return count === 1 ? '1 motor disponible' : `${count} motores disponibles`
      })(),
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
        toast.add({ severity: 'info', summary: 'Instalando analizador', detail: 'Descargando e instalando...', life: 5000 })
        await new Promise(resolve => setTimeout(resolve, 5000))
        await reloadCapabilities()
        if (systemCapabilities.value?.ollama?.installed) {
          toast.add({ severity: 'success', summary: 'Analizador instalado', detail: 'Ahora puedes iniciar el analizador', life: 3000 })
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
          toast.add({ severity: 'warn', summary: 'Analizador no instalado', detail: 'Necesitas instalar el analizador sem\u00E1ntico primero', life: 5000 })
        } else {
          toast.add({ severity: 'error', summary: 'Error al iniciar', detail: result.error || 'No se pudo iniciar el analizador', life: 5000 })
        }
      }
    } catch (error) {
      console.error('Error starting Ollama:', error)
      toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo iniciar el analizador semántico', life: 3000 })
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
    // Descargar los modelos que faltan según el nivel configurado
    try {
      const result = await api.getRaw<{ data: { missing_models: string[]; ready: boolean } }>('/api/services/llm/readiness')
      const missing = result?.data?.missing_models || []
      if (missing.length > 0) {
        let success = false
        for (const model of missing) {
          success = await downloadModel(model)
        }
        return success
      }
      // Si no faltan modelos, ya estamos listos
      return true
    } catch {
      // Si el endpoint no está disponible, descargar el modelo core por defecto
      return downloadModel('qwen3')
    }
  }

  async function downloadModel(modelName: string): Promise<boolean> {
    const normalized = modelName.split(':')[0]
    modelOperations.value[normalized] = 'installing'

    // Chain downloads sequentially — backend only allows one at a time
    let result = false
    downloadChain = downloadChain.then(async () => {
      result = await downloadModelNow(normalized)
    })
    await downloadChain
    return result
  }

  /** Internal: actually starts the download (no queue check). */
  async function downloadModelNow(normalized: string): Promise<boolean> {
    modelDownloading.value = true
    modelOperations.value[normalized] = 'installing'
    ollamaDownloadProgress.value = null
    toast.add({
      severity: 'info',
      summary: 'Descargando motor de análisis',
      detail: 'Esto puede tardar varios minutos...',
      life: 5000,
    })

    try {
      const result = await api.postRaw<{ success: boolean; error?: string }>(`/api/ollama/pull/${normalized}`)
      if (!result.success) {
        toast.add({ severity: 'error', summary: 'Error', detail: result.error || 'No se pudo iniciar la descarga', life: 5000 })
        modelDownloading.value = false
        delete modelOperations.value[normalized]
        return false
      }

      let pollCount = 0
      const ok = await new Promise<boolean>((resolve) => {
        ollamaDownloadPollTimer = setInterval(async () => {
          pollCount++
          if (pollCount > 900) {
            stopOllamaDownloadPolling()
            toast.add({ severity: 'error', summary: 'Timeout', detail: 'La descarga tard\u00F3 demasiado', life: 5000 })
            resolve(false)
            return
          }

          try {
            const statusResult = await api.getRaw<any>('/api/ollama/status')
            const dp = statusResult.data?.download_progress
            if (dp) {
              ollamaDownloadProgress.value = dp
            }

            const downloadedModels: string[] = statusResult.data?.downloaded_models || []
            if (dp?.status === 'complete' || (!statusResult.data?.is_downloading && downloadedModels.includes(normalized))) {
              stopOllamaDownloadPolling()
              await reloadCapabilities()
              toast.add({ severity: 'success', summary: 'Motor instalado', detail: 'Motor de análisis disponible', life: 3000 })
              resolve(true)
              return
            }

            if (dp?.status === 'error') {
              stopOllamaDownloadPolling()
              toast.add({ severity: 'error', summary: 'Error', detail: dp.error || 'Error descargando motor de análisis', life: 5000 })
              resolve(false)
              return
            }
          } catch {
            // Ignore poll errors
          }
        }, 1000)
      })

      ollamaDownloadProgress.value = null
      modelDownloading.value = false
      delete modelOperations.value[normalized]
      return ok
    } catch {
      toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo descargar el motor de análisis', life: 3000 })
      modelDownloading.value = false
      delete modelOperations.value[normalized]
      return false
    }
  }

  async function installModel(modelName: string): Promise<boolean> {
    return downloadModel(modelName)
  }

  async function uninstallModel(modelName: string): Promise<boolean> {
    const normalized = modelName.split(':')[0]
    modelOperations.value[normalized] = 'uninstalling'
    try {
      const result = await api.del<{ success: boolean; error?: string; data?: { remaining_models?: string[] } }>(`/api/ollama/model/${normalized}`)
      if (!result.success) {
        toast.add({
          severity: 'warn',
          summary: 'No se pudo desinstalar',
          detail: result.error || `No se pudo desinstalar ${normalized}`,
          life: 4500,
        })
        return false
      }

      await reloadCapabilities()
      toast.add({
        severity: 'success',
        summary: 'Motor desinstalado',
        detail: 'Motor de análisis eliminado correctamente',
        life: 3000,
      })
      return true
    } catch {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: `No se pudo desinstalar ${normalized}`,
        life: 4500,
      })
      return false
    } finally {
      delete modelOperations.value[normalized]
    }
  }

  function isModelBusy(modelName: string): boolean {
    const normalized = modelName.split(':')[0]
    return Boolean(modelOperations.value[normalized])
  }

  function getModelOperationLabel(modelName: string): string | null {
    const normalized = modelName.split(':')[0]
    const operation = modelOperations.value[normalized]
    if (operation === 'installing') return 'Instalando motor...'
    if (operation === 'uninstalling') return 'Desinstalando motor...'
    return null
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
    modelOperations,
    isModelBusy,
    getModelOperationLabel,
    installOllama,
    startOllama,
    openOllamaDownload,
    installModel,
    uninstallModel,
    downloadModel,
    downloadDefaultModel,
    cleanup,
  }
}
