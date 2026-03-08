import { ref } from 'vue'
import { defineStore } from 'pinia'
import { useSystemStore } from './system'

// Tauri imports (only available in Tauri environment)
let tauriListen: ((event: string, handler: (event: { payload: unknown }) => void) => Promise<() => void>) | null = null
let tauriInvoke: ((cmd: string) => Promise<string>) | null = null
const isTauriRuntime =
  typeof window !== 'undefined' && ('__TAURI__' in window || '__TAURI_INTERNALS__' in window)
let tauriApisReady: Promise<void> | null = null

function ensureTauriApis(): Promise<void> {
  if (!isTauriRuntime) return Promise.resolve()
  if (!tauriApisReady) {
    tauriApisReady = Promise.all([
      import('@tauri-apps/api/event'),
      import('@tauri-apps/api/core'),
    ]).then(([eventModule, coreModule]) => {
      tauriListen = eventModule.listen
      tauriInvoke = coreModule.invoke
    })
  }
  return tauriApisReady
}

export const useAppStore = defineStore('app', () => {
  const listenerInitialized = ref(false)

  async function initTauriListener() {
    if (listenerInitialized.value) return

    await ensureTauriApis()
    if (!tauriListen) return

    try {
      await tauriListen('backend-status', (event) => {
        const payload = event.payload as { status: string; message: string }

        const systemStore = useSystemStore()
        if (payload.status === 'running') {
          systemStore.backendConnected = true
          systemStore.backendStartupError = null
        } else if (payload.status === 'starting' || payload.status === 'restarting') {
          systemStore.backendConnected = false
          systemStore.backendStartupError = null
        } else if (payload.status === 'error') {
          systemStore.backendConnected = false
          systemStore.backendStartupError = payload.message
          systemStore.startRetrying()
        }
      })
      listenerInitialized.value = true
    } catch (err) {
      console.error('Failed to listen for Tauri events:', err)
    }
  }

  async function startBackendServer(): Promise<string | null> {
    await ensureTauriApis()
    if (!tauriInvoke) return null

    try {
      const result = await tauriInvoke('start_backend_server')
      return result
    } catch (err) {
      console.error('Failed to start backend server:', err)
      const systemStore = useSystemStore()
      systemStore.backendStartupError = err instanceof Error ? err.message : 'Error iniciando el motor de analisis'
      return null
    }
  }

  initTauriListener()

  return {
    startBackendServer,
  }
})
