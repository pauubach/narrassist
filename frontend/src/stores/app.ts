import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'
import type { ThemeMode } from '@/types'

export const useAppStore = defineStore('app', () => {
  // Estado
  const backendConnected = ref(false)
  const backendVersion = ref<string | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
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

  // Getters
  const isReady = computed(() => backendConnected.value && !loading.value)

  // Actions
  async function checkBackendHealth() {
    loading.value = true
    error.value = null

    try {
      const response = await fetch('/api/health')
      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`)
      }

      const data = await response.json()
      backendConnected.value = true
      backendVersion.value = data.version || null
    } catch (err) {
      backendConnected.value = false
      backendVersion.value = null
      error.value = err instanceof Error ? err.message : 'Error desconocido'
      console.error('Backend health check failed:', err)
    } finally {
      loading.value = false
    }
  }

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
    theme,
    isDark,
    // Getters
    isReady,
    // Actions
    checkBackendHealth,
    clearError,
    setTheme,
    toggleTheme
  }
})
