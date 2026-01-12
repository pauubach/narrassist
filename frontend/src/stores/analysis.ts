import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export interface AnalysisProgress {
  project_id: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  current_phase: string
  current_action?: string
  phases: Array<{
    id: string
    name: string
    completed: boolean
    current: boolean
    duration?: number
  }>
  metrics?: {
    chapters_found?: number
    entities_found?: number
    word_count?: number
    alerts_generated?: number
  }
  estimated_seconds_remaining?: number
  error?: string
}

export const useAnalysisStore = defineStore('analysis', () => {
  // Estado
  const currentAnalysis = ref<AnalysisProgress | null>(null)
  const isAnalyzing = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const hasActiveAnalysis = computed(() => isAnalyzing.value && currentAnalysis.value !== null)
  const progressPercentage = computed(() => currentAnalysis.value?.progress || 0)

  // Actions
  async function startAnalysis(projectId: number, file?: File) {
    isAnalyzing.value = true
    error.value = null

    try {
      const formData = new FormData()
      if (file) {
        formData.append('file', file)
      }

      const response = await fetch(`/api/projects/${projectId}/analyze`, {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      if (data.success) {
        currentAnalysis.value = {
          project_id: projectId,
          status: 'running',
          progress: 0,
          current_phase: 'Iniciando...',
          phases: []
        }
        return true
      } else {
        throw new Error(data.error || 'Error iniciando análisis')
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Error desconocido'
      isAnalyzing.value = false
      console.error('Failed to start analysis:', err)
      return false
    }
  }

  async function getProgress(projectId: number) {
    try {
      const response = await fetch(`/api/projects/${projectId}/analysis/progress`)

      if (!response.ok) {
        throw new Error('Error obteniendo progreso')
      }

      const data = await response.json()
      if (data.success && data.data) {
        currentAnalysis.value = data.data

        // Actualizar estado
        if (data.data.status === 'completed' || data.data.progress >= 100) {
          isAnalyzing.value = false
        } else if (data.data.status === 'error' || data.data.status === 'failed') {
          isAnalyzing.value = false
          error.value = data.data.error || 'Análisis fallido'
        }

        return data.data
      }
    } catch (err) {
      console.error('Error fetching progress:', err)
      return null
    }
  }

  function clearAnalysis() {
    currentAnalysis.value = null
    isAnalyzing.value = false
    error.value = null
  }

  function clearError() {
    error.value = null
  }

  return {
    // State
    currentAnalysis,
    isAnalyzing,
    error,
    // Getters
    hasActiveAnalysis,
    progressPercentage,
    // Actions
    startAnalysis,
    getProgress,
    clearAnalysis,
    clearError
  }
})
