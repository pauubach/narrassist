import { ref, watch } from 'vue'
import { defineStore } from 'pinia'
import type { ThemeMode } from '@/types'
import { useSystemStore } from './system'

// Tauri imports (only available in Tauri environment)
let tauriListen: ((event: string, handler: (event: { payload: unknown }) => void) => Promise<() => void>) | null = null
let tauriInvoke: ((cmd: string) => Promise<string>) | null = null

// Dynamic import for Tauri (to avoid errors when running in browser)
// Tauri 2.0 uses __TAURI_INTERNALS__ (not __TAURI__ unless withGlobalTauri=true)
if (typeof window !== 'undefined' && ('__TAURI__' in window || '__TAURI_INTERNALS__' in window)) {
  import('@tauri-apps/api/event').then(module => {
    tauriListen = module.listen
  })
  import('@tauri-apps/api/core').then(module => {
    tauriInvoke = module.invoke
  })
}

export const useAppStore = defineStore('app', () => {
  // ── Theme ──────────────────────────────────────────────
  const theme = ref<ThemeMode>('auto')
  const isDark = ref(false)

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

  // ── Tauri integration ──────────────────────────────────
  // Tauri events update systemStore (single source of truth for backend state)

  async function initTauriListener() {
    if (!tauriListen) return

    try {
      await tauriListen('backend-status', (event) => {
        const payload = event.payload as { status: string; message: string }
        console.log('[Tauri] Backend status event:', payload)

        const systemStore = useSystemStore()
        if (payload.status === 'running') {
          systemStore.backendConnected = true
          systemStore.backendStartupError = null
        } else if (payload.status === 'error') {
          systemStore.backendConnected = false
          systemStore.backendStartupError = payload.message
          systemStore.startRetrying()
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
      const systemStore = useSystemStore()
      systemStore.backendStartupError = err instanceof Error ? err.message : 'Error iniciando motor de análisis'
      return null
    }
  }

  // Initialize Tauri listener on store creation
  initTauriListener()

  return {
    // Theme
    theme,
    isDark,
    setTheme,
    toggleTheme,
    // Tauri
    startBackendServer
  }
})
