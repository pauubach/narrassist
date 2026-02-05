/**
 * useAnalysisStream - Composable para consumir el stream SSE de análisis.
 *
 * Proporciona una interfaz reactiva para:
 * - Iniciar análisis y conectarse al stream
 * - Recibir actualizaciones de progreso en tiempo real
 * - Manejar reconexión automática
 * - Cancelar análisis en curso
 */

import { ref, computed, onUnmounted } from 'vue'
import { API_BASE } from '@/config/api'
import { useNotifications } from './useNotifications'

export interface AnalysisPhase {
  id: string
  name: string
  completed: boolean
  current: boolean
}

export interface AnalysisProgress {
  projectId: number
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  phase: string
  action: string
  current_phase?: string
  phases: AnalysisPhase[]
  estimatedSecondsRemaining?: number
  error?: string
  stats?: Record<string, number>
}

export interface UseAnalysisStreamOptions {
  /** URL base de la API */
  baseUrl?: string
  /** Reintentar conexión automáticamente */
  autoReconnect?: boolean
  /** Máximo de reintentos */
  maxRetries?: number
  /** Delay base entre reintentos (ms) */
  retryDelay?: number
}

const defaultOptions: UseAnalysisStreamOptions = {
  baseUrl: API_BASE,
  autoReconnect: true,
  maxRetries: 3,
  retryDelay: 1000,
}

export function useAnalysisStream(options: UseAnalysisStreamOptions = {}) {
  const config = { ...defaultOptions, ...options }

  // Notificaciones
  const { notifyAnalysisComplete, notifyAnalysisError } = useNotifications()

  // Estado
  const isConnected = ref(false)
  const isAnalyzing = ref(false)
  const progress = ref<AnalysisProgress | null>(null)
  const error = ref<string | null>(null)
  const retryCount = ref(0)

  // EventSource instance
  let eventSource: EventSource | null = null
  let projectId: number | null = null
  let projectName: string | null = null

  // Getters
  const progressPercent = computed(() => progress.value?.progress ?? 0)
  const currentPhase = computed(() => progress.value?.phase ?? '')
  const currentAction = computed(() => progress.value?.action ?? '')
  const isComplete = computed(() => progress.value?.status === 'completed')
  const isFailed = computed(() => progress.value?.status === 'failed')
  const phases = computed(() => progress.value?.phases ?? [])
  const estimatedTime = computed(() => {
    const seconds = progress.value?.estimatedSecondsRemaining
    if (!seconds) return null
    if (seconds < 60) return `${Math.round(seconds)}s`
    return `${Math.round(seconds / 60)}m`
  })

  /**
   * Inicia el análisis de un proyecto
   */
  async function startAnalysis(id: number, file?: File, name?: string): Promise<boolean> {
    projectId = id
    projectName = name || null
    error.value = null
    retryCount.value = 0

    try {
      // Iniciar análisis en el servidor
      const formData = new FormData()
      if (file) {
        formData.append('file', file)
      }

      const response = await fetch(`${config.baseUrl}/api/projects/${id}/analyze`, {
        method: 'POST',
        body: file ? formData : undefined,
      })

      const result = await response.json()

      if (!result.success) {
        error.value = result.error || 'Error al iniciar análisis'
        return false
      }

      // Conectar al stream SSE
      connectToStream(id)
      isAnalyzing.value = true

      return true
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Error de conexión'
      return false
    }
  }

  /**
   * Conecta al stream SSE de progreso
   */
  function connectToStream(id: number) {
    // Cerrar conexión existente
    disconnect()

    const url = `${config.baseUrl}/api/projects/${id}/analysis/stream`
    eventSource = new EventSource(url)

    eventSource.onopen = () => {
      isConnected.value = true
      retryCount.value = 0
    }

    // Evento de progreso
    eventSource.addEventListener('progress', (event) => {
      try {
        const data = JSON.parse(event.data)
        progress.value = {
          projectId: data.project_id,
          status: data.status,
          progress: data.progress,
          phase: data.phase,
          action: data.action,
          phases: data.phases || [],
          estimatedSecondsRemaining: data.estimated_seconds_remaining,
        }
      } catch (e) {
        console.error('Error parsing progress event:', e)
      }
    })

    // Evento de completado
    eventSource.addEventListener('complete', (event) => {
      try {
        const data = JSON.parse(event.data)
        progress.value = {
          projectId: data.project_id,
          status: 'completed',
          progress: 100,
          phase: 'Análisis completado',
          action: '',
          phases: progress.value?.phases ?? [],
          stats: data.stats,
        }
        isAnalyzing.value = false
        disconnect()

        // Notificar al usuario
        notifyAnalysisComplete(projectName || undefined)
      } catch (e) {
        console.error('Error parsing complete event:', e)
      }
    })

    // Evento de error
    eventSource.addEventListener('error', (event) => {
      // Puede ser un evento de error del servidor o de conexión
      if (event instanceof MessageEvent) {
        try {
          const data = JSON.parse(event.data)
          error.value = data.error || 'Error durante el análisis'
          progress.value = {
            ...progress.value!,
            status: 'failed',
            error: data.error,
          }
          // Notificar error al usuario
          notifyAnalysisError(data.error)
        } catch {
          error.value = 'Error durante el análisis'
          notifyAnalysisError()
        }
      }
      isAnalyzing.value = false
      handleConnectionError()
    })

    // Keepalive (solo para debug)
    eventSource.addEventListener('keepalive', () => {
      // Conexión activa
    })

    // Error de conexión
    eventSource.onerror = () => {
      isConnected.value = false
      handleConnectionError()
    }
  }

  /**
   * Maneja errores de conexión con reconexión automática
   */
  function handleConnectionError() {
    if (!config.autoReconnect || !projectId) return
    if (retryCount.value >= config.maxRetries!) {
      error.value = 'No se pudo reconectar al servidor'
      isAnalyzing.value = false
      return
    }

    retryCount.value++
    const delay = config.retryDelay! * Math.pow(2, retryCount.value - 1) // Exponential backoff

    setTimeout(() => {
      if (isAnalyzing.value && projectId) {
        connectToStream(projectId)
      }
    }, delay)
  }

  /**
   * Desconecta del stream
   */
  function disconnect() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    isConnected.value = false
  }

  /**
   * Cancela el análisis en curso
   */
  async function cancelAnalysis(): Promise<boolean> {
    if (!projectId) return false

    try {
      // Llamar al endpoint de cancelación
      const response = await fetch(
        `${config.baseUrl}/api/projects/${projectId}/analysis/cancel`,
        { method: 'POST' }
      )
      const data = await response.json()

      if (data.success) {
        disconnect()
        isAnalyzing.value = false
        if (progress.value) {
          progress.value.status = 'cancelled'
          progress.value.current_phase = 'Análisis cancelado'
        }
        return true
      } else {
        error.value = data.error || 'Error al cancelar el análisis'
        return false
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Error al cancelar'
      // Desconectar de todos modos
      disconnect()
      isAnalyzing.value = false
      return false
    }
  }

  /**
   * Resetea el estado
   */
  function reset() {
    disconnect()
    isAnalyzing.value = false
    progress.value = null
    error.value = null
    retryCount.value = 0
    projectId = null
    projectName = null
  }

  /**
   * Consulta el estado actual del análisis (polling fallback)
   */
  async function checkProgress(id: number): Promise<AnalysisProgress | null> {
    try {
      const response = await fetch(`${config.baseUrl}/api/projects/${id}/analysis/progress`)
      const result = await response.json()

      if (result.success && result.data) {
        const data = result.data
        return {
          projectId: data.project_id,
          status: data.status,
          progress: data.progress,
          phase: data.current_phase,
          action: data.current_action,
          phases: data.phases || [],
          estimatedSecondsRemaining: data.estimated_seconds_remaining,
        }
      }
      return null
    } catch {
      return null
    }
  }

  // Cleanup al desmontar
  onUnmounted(() => {
    disconnect()
  })

  return {
    // Estado
    isConnected,
    isAnalyzing,
    progress,
    error,

    // Getters
    progressPercent,
    currentPhase,
    currentAction,
    isComplete,
    isFailed,
    phases,
    estimatedTime,

    // Acciones
    startAnalysis,
    connectToStream,
    disconnect,
    cancelAnalysis,
    reset,
    checkProgress,
  }
}
