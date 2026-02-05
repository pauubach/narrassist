import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'
import type { ThemeMode } from '@/types'
import { api } from '@/services/apiClient'

// Tauri imports (only available in Tauri environment)
let tauriListen: ((event: string, handler: (event: { payload: unknown }) => void) => Promise<() => void>) | null = null
let tauriInvoke: ((cmd: string) => Promise<string>) | null = null

// Dynamic import for Tauri (to avoid errors when running in browser)
if (typeof window !== 'undefined' && '__TAURI__' in window) {
  import('@tauri-apps/api/event').then(module => {
    tauriListen = module.listen
  })
  import('@tauri-apps/api/core').then(module => {
    tauriInvoke = module.invoke
  })
}

export const useAppStore = defineStore('app', () => {
  // Estado
  const backendConnected = ref(false)
  const backendVersion = ref<string | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const backendError = ref<string | null>(null)
  const theme = ref<ThemeMode>('auto')
  const isDark = ref(false)
  let retryInterval: number | null = null

  // Inicializar tema desde localStorage
  const savedTheme = localStorage.getItem('narrative_assistant_theme') as ThemeMode | null
  if (savedTheme) {
    theme.value = savedTheme
  }

  // Detectar preferencia del sistema
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)')

  const updateTheme = () => {
    if (theme.value === 'auto') {
      isDark.value = prefersDark.matches
    } else {
      isDark.value = theme.value === 'dark'
    }

    // PrimeVue 4 usa la clase .dark para dark mode
    document.documentElement.classList.toggle('dark', isDark.value)
  }

  // Inicializar tema
  updateTheme()

  // Escuchar cambios en preferencia del sistema
  prefersDark.addEventListener('change', (e) => {
    if (theme.value === 'auto') {
      isDark.value = e.matches
      document.documentElement.classList.toggle('dark', isDark.value)
    }
  })

  // Watcher para cambios de tema
  watch(theme, () => {
    updateTheme()
    localStorage.setItem('narrative_assistant_theme', theme.value)
  })

  // Getters
  const isReady = computed(() => backendConnected.value && !loading.value)

  // Actions
  async function checkBackendHealth() {
    loading.value = true
    error.value = null

    try {
      const data = await api.getRaw<{ status: string; version?: string }>('/api/health')
      backendConnected.value = true
      backendVersion.value = data.version || null
      backendError.value = null
      stopRetrying() // Stop retrying once connected
    } catch (err) {
      backendConnected.value = false
      backendVersion.value = null
      error.value = err instanceof Error ? err.message : 'Error desconocido'
      console.error('Backend health check failed:', err)
    } finally {
      loading.value = false
    }
  }

  // Start retrying backend connection
  function startRetrying() {
    if (retryInterval) return
    retryInterval = window.setInterval(async () => {
      if (!backendConnected.value) {
        await checkBackendHealth()
      } else {
        stopRetrying()
      }
    }, 3000) // Retry every 3 seconds
  }

  // Stop retrying
  function stopRetrying() {
    if (retryInterval) {
      clearInterval(retryInterval)
      retryInterval = null
    }
  }

  // Initialize Tauri event listener
  async function initTauriListener() {
    if (!tauriListen) return

    try {
      unlisten = await tauriListen('backend-status', (event) => {
        const payload = event.payload as { status: string; message: string }
        console.log('[Tauri] Backend status event:', payload)

        if (payload.status === 'running') {
          backendConnected.value = true
          backendError.value = null
          stopRetrying()
        } else if (payload.status === 'error') {
          backendConnected.value = false
          backendError.value = payload.message
          startRetrying()
        }
      })
    } catch (err) {
      console.error('Failed to listen for Tauri events:', err)
    }
  }

  // Start backend server (Tauri only)
  async function startBackendServer(): Promise<string | null> {
    if (!tauriInvoke) return null

    try {
      const result = await tauriInvoke('start_backend_server')
      return result
    } catch (err) {
      console.error('Failed to start backend server:', err)
      backendError.value = err instanceof Error ? err.message : 'Error iniciando servidor'
      return null
    }
  }

  // Initialize Tauri listener on store creation
  initTauriListener()

  function clearError() {
    error.value = null
  }

  function setTheme(newTheme: ThemeMode) {
    theme.value = newTheme
  }

  function toggleTheme() {
    if (theme.value === 'light') {
      theme.value = 'dark'
    } else if (theme.value === 'dark') {
      theme.value = 'auto'
    } else {
      theme.value = 'light'
    }
  }

  return {
    // State
    backendConnected,
    backendVersion,
    loading,
    error,
    backendError,
    theme,
    isDark,
    // Getters
    isReady,
    // Actions
    checkBackendHealth,
    clearError,
    setTheme,
    toggleTheme,
    startRetrying,
    stopRetrying,
    startBackendServer
  }
})
