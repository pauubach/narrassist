import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/services/apiClient'

export interface AnalysisProgress {
  project_id: number
  status: 'pending' | 'running' | 'queued' | 'queued_for_heavy' | 'completed' | 'failed' | 'error' | 'idle' | 'cancelled'
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

/**
 * Estado de fases ejecutadas para un proyecto.
 * Permite mostrar tabs condicionales según qué análisis se han ejecutado.
 */
export interface ExecutedPhases {
  // Parsing y estructura
  parsing: boolean
  structure: boolean
  // Extracción
  entities: boolean
  coreference: boolean
  attributes: boolean
  // Relaciones e interacciones
  relationships: boolean
  interactions: boolean
  // Calidad
  spelling: boolean
  grammar: boolean
  register: boolean
  pacing: boolean
  coherence: boolean
  // Análisis avanzado
  temporal: boolean
  emotional: boolean
  sentiment: boolean
  focalization: boolean
  voice_profiles: boolean
}

/**
 * Mapa de dependencias entre análisis.
 * Un análisis no puede ejecutarse si sus dependencias no están completas.
 */
export const ANALYSIS_DEPENDENCIES: Record<keyof ExecutedPhases, (keyof ExecutedPhases)[]> = {
  parsing: [],
  structure: ['parsing'],
  entities: ['parsing'],
  coreference: ['entities'],
  attributes: ['entities', 'coreference'],
  relationships: ['entities', 'coreference'],
  interactions: ['entities'],
  spelling: ['parsing'],
  grammar: ['parsing'],
  register: ['parsing'],
  pacing: ['structure'],
  coherence: ['entities', 'structure'],
  temporal: ['parsing'],
  emotional: ['entities'],
  sentiment: ['parsing'],
  focalization: ['entities', 'structure'],
  voice_profiles: ['entities', 'attributes'],
}

/**
 * Nombres legibles para mostrar en la UI.
 */
export const PHASE_LABELS: Record<keyof ExecutedPhases, string> = {
  parsing: 'Análisis inicial',
  structure: 'Detección de estructura',
  entities: 'Extracción de entidades',
  coreference: 'Resolución de correferencias',
  attributes: 'Extracción de atributos',
  relationships: 'Detección de relaciones',
  interactions: 'Detección de interacciones',
  spelling: 'Ortografía',
  grammar: 'Gramática',
  register: 'Análisis de registro',
  pacing: 'Análisis de ritmo',
  coherence: 'Coherencia narrativa',
  temporal: 'Marcadores temporales',
  emotional: 'Análisis emocional',
  sentiment: 'Arcos de sentimiento',
  focalization: 'Focalización',
  voice_profiles: 'Perfiles de voz',
}

/**
 * Mapeo de tabs del workspace a las fases de análisis que requieren.
 * Si una tab no está en el mapa, no requiere análisis específico.
 */
export type WorkspaceTab = 'text' | 'entities' | 'relationships' | 'alerts' | 'timeline' | 'style' | 'glossary' | 'summary'

export const TAB_REQUIRED_PHASES: Partial<Record<WorkspaceTab, keyof ExecutedPhases>> = {
  // text: 'parsing', // Siempre disponible tras análisis inicial
  entities: 'entities',
  // relationships depende de coreference (fusión de entidades), disponible tras NER+fusion
  relationships: 'coreference',
  // alerts: se generan progresivamente, siempre mostramos las disponibles
  // timeline depende de structure (identificación de capítulos)
  timeline: 'structure',
  // style depende de grammar (incluye análisis de estilo y registro)
  style: 'grammar',
  // summary: siempre disponible
}

/**
 * Descripción de qué contenido se verá cuando se ejecute la fase.
 */
export const TAB_PHASE_DESCRIPTIONS: Partial<Record<WorkspaceTab, string>> = {
  entities: 'Extrae personajes, lugares, objetos y otros elementos de tu documento.',
  relationships: 'Detecta las relaciones entre personajes y entidades.',
  timeline: 'Analiza marcadores temporales y construye la línea temporal del documento.',
  style: 'Analiza el registro, gramática y estilo del texto.',
}

/**
 * Mapeo de IDs de fases del backend a keys de ExecutedPhases del frontend.
 * El backend usa IDs simplificados, el frontend usa keys más detallados.
 */
const BACKEND_PHASE_TO_FRONTEND: Record<string, keyof ExecutedPhases | null> = {
  parsing: 'parsing',
  classification: null, // Clasificación no tiene fase frontend propia
  structure: 'structure',
  ner: 'entities',
  fusion: 'coreference',
  attributes: 'attributes',
  consistency: 'coherence',
  grammar: 'grammar',
  alerts: null, // Las alertas no son una "fase" en el sentido del frontend
  relationships: 'relationships',
  voice: 'voice_profiles',
  prose: 'register',
  health: null, // Salud narrativa es un resumen, no una fase específica
}

export const useAnalysisStore = defineStore('analysis', () => {
  // ============================================================================
  // Estado interno por proyecto (evita contaminar datos entre proyectos)
  // ============================================================================
  const _analyses = ref<Record<number, AnalysisProgress>>({})
  const _analyzing = ref<Record<number, boolean>>({})
  const _errors = ref<Record<number, string | null>>({})
  const _activeProjectId = ref<number | null>(null)

  /**
   * Estado de fases ejecutadas por proyecto.
   * Se carga al abrir un proyecto y se actualiza tras cada análisis.
   */
  const executedPhases = ref<Record<number, Partial<ExecutedPhases>>>({})

  /**
   * Fases actualmente en ejecución (para mostrar loading).
   */
  const runningPhases = ref<Set<keyof ExecutedPhases>>(new Set())

  // ============================================================================
  // Computed: vista del proyecto activo (backward-compatible)
  // StatusBar y otros componentes leen estos sin necesitar projectId
  // ============================================================================
  const currentAnalysis = computed<AnalysisProgress | null>(() =>
    _activeProjectId.value != null ? (_analyses.value[_activeProjectId.value] ?? null) : null
  )
  const isAnalyzing = computed<boolean>(() =>
    _activeProjectId.value != null ? (_analyzing.value[_activeProjectId.value] ?? false) : false
  )
  const error = computed<string | null>(() =>
    _activeProjectId.value != null ? (_errors.value[_activeProjectId.value] ?? null) : null
  )

  // Getters
  const hasActiveAnalysis = computed(() => isAnalyzing.value && currentAnalysis.value !== null)
  const hasAnyActiveAnalysis = computed(() => Object.values(_analyzing.value).some(v => v))
  const progressPercentage = computed(() => currentAnalysis.value?.progress || 0)

  // ============================================================================
  // Gestión del proyecto activo
  // ============================================================================

  /**
   * Establece qué proyecto es el "activo" para los computed globales.
   * Llamar al entrar a ProjectDetailView.
   */
  function setActiveProjectId(projectId: number | null) {
    _activeProjectId.value = projectId
  }

  // ============================================================================
  // Consultas por proyecto (para uso externo)
  // ============================================================================

  function isProjectAnalyzing(projectId: number): boolean {
    return _analyzing.value[projectId] ?? false
  }

  function getProjectProgress(projectId: number): number {
    return _analyses.value[projectId]?.progress ?? 0
  }

  // ============================================================================
  // Actions
  // ============================================================================

  async function startAnalysis(projectId: number, file?: File) {
    _analyzing.value[projectId] = true
    delete _errors.value[projectId]

    try {
      const formData = new FormData()
      if (file) {
        formData.append('file', file)
      }

      const response = await api.postForm<{ project_id: number; status: string }>(`/api/projects/${projectId}/analyze`, formData)
      const isQueued = response?.status === 'queued'
      // Re-assert _analyzing after await (checkAnalysisStatus may have cleared it during the await)
      _analyzing.value[projectId] = true
      _analyses.value[projectId] = {
        project_id: projectId,
        status: isQueued ? 'queued' : 'running',
        progress: 0,
        current_phase: isQueued ? 'En cola — esperando análisis anterior' : 'Iniciando...',
        phases: []
      }
      return true
    } catch (err) {
      _errors.value[projectId] = err instanceof Error ? err.message : 'Error desconocido'
      _analyzing.value[projectId] = false
      console.error('Failed to start analysis:', err)
      return false
    }
  }

  async function cancelAnalysis(projectId: number): Promise<boolean> {
    try {
      await api.postRaw<{ success: boolean }>(`/api/projects/${projectId}/analysis/cancel`, {})
      _analyzing.value[projectId] = false
      if (_analyses.value[projectId]) {
        _analyses.value[projectId].status = 'idle'
        _analyses.value[projectId].current_phase = 'Análisis cancelado'
      }
      return true
    } catch (err) {
      console.error('Failed to cancel analysis:', err)
      return false
    }
  }

  async function getProgress(projectId: number) {
    try {
      const progressData = await api.get<AnalysisProgress>(`/api/projects/${projectId}/analysis/progress`)
      _analyses.value[projectId] = progressData

      // Actualizar executedPhases progresivamente según fases completadas
      if (progressData.phases && Array.isArray(progressData.phases)) {
        if (!executedPhases.value[projectId]) {
          executedPhases.value[projectId] = {}
        }
        for (const phase of progressData.phases) {
          if (phase.completed) {
            const frontendKey = BACKEND_PHASE_TO_FRONTEND[phase.id]
            if (frontendKey) {
              executedPhases.value[projectId][frontendKey] = true
            }
          }
        }
      }

      // Actualizar estado
      if (progressData.status === 'completed' || progressData.progress >= 100) {
        _analyzing.value[projectId] = false
      } else if (progressData.status === 'error' || progressData.status === 'failed') {
        _analyzing.value[projectId] = false
        _errors.value[projectId] = progressData.error || 'Análisis fallido'
      } else if (progressData.status === 'queued' || progressData.status === 'queued_for_heavy') {
        // Queued: keep as "analyzing" so polling continues
        _analyzing.value[projectId] = true
      }

      return progressData
    } catch (err) {
      console.error('Error fetching progress:', err)
      return null
    }
  }

  function clearAnalysis(projectId?: number) {
    const id = projectId ?? _activeProjectId.value
    if (id != null) {
      delete _analyses.value[id]
      delete _analyzing.value[id]
      delete _errors.value[id]
    }
  }

  function clearError(projectId?: number) {
    const id = projectId ?? _activeProjectId.value
    if (id != null) {
      delete _errors.value[id]
    }
  }

  /**
   * Marca el inicio de un análisis (para cuando se llama desde fuera del store)
   */
  function setAnalyzing(projectId: number, analyzing: boolean) {
    _analyzing.value[projectId] = analyzing
    if (analyzing) {
      _analyses.value[projectId] = {
        project_id: projectId,
        status: 'running',
        progress: 0,
        current_phase: 'Iniciando análisis...',
        phases: []
      }
      delete _errors.value[projectId]
    } else {
      delete _analyses.value[projectId]
    }
  }

  /**
   * Verifica si hay un análisis en curso para un proyecto
   * Útil al cargar la página para recuperar el estado
   * IMPORTANTE: Limpia el estado si no hay análisis activo
   */
  async function checkAnalysisStatus(projectId: number): Promise<boolean> {
    try {
      // If already marked as analyzing (e.g., startAnalysis was called concurrently),
      // don't clear — just query backend to update progress data
      const alreadyActive = _analyzing.value[projectId] === true

      const progressData = await api.get<AnalysisProgress>(`/api/projects/${projectId}/analysis/progress`)
      const status = progressData.status
      if (status === 'running' || status === 'pending' || status === 'queued' || status === 'queued_for_heavy') {
        _analyses.value[projectId] = progressData
        _analyzing.value[projectId] = true
        return true
      }

      // Backend says idle — but if startAnalysis is in-flight, don't clear
      if (alreadyActive) {
        return true
      }

      clearAnalysis(projectId)
      return false
    } catch {
      if (_analyzing.value[projectId] === true) {
        return true
      }
      clearAnalysis(projectId)
      return false
    }
  }

  // ============================================================================
  // Métodos para fases ejecutadas
  // ============================================================================

  /**
   * Obtiene las fases ejecutadas para un proyecto desde el backend.
   */
  async function loadExecutedPhases(projectId: number): Promise<Partial<ExecutedPhases> | null> {
    try {
      const data = await api.get<{ executed: Partial<ExecutedPhases> }>(`/api/projects/${projectId}/analysis-status`)
      if (data?.executed) {
        executedPhases.value[projectId] = data.executed
        return data.executed
      }
      return null
    } catch {
      return null
    }
  }

  /**
   * Verifica si una fase específica fue ejecutada para un proyecto.
   */
  function isPhaseExecuted(projectId: number, phase: keyof ExecutedPhases): boolean {
    return executedPhases.value[projectId]?.[phase] ?? false
  }

  /**
   * Obtiene las dependencias faltantes para ejecutar una fase.
   */
  function getMissingDependencies(projectId: number, phase: keyof ExecutedPhases): (keyof ExecutedPhases)[] {
    const deps = ANALYSIS_DEPENDENCIES[phase]
    return deps.filter(dep => !isPhaseExecuted(projectId, dep))
  }

  /**
   * Verifica si una fase puede ejecutarse (todas sus dependencias están completas).
   */
  function canRunPhase(projectId: number, phase: keyof ExecutedPhases): boolean {
    return getMissingDependencies(projectId, phase).length === 0
  }

  /**
   * Ejecuta un análisis parcial (solo ciertas fases).
   */
  async function runPartialAnalysis(
    projectId: number,
    phases: (keyof ExecutedPhases)[],
    force: boolean = false
  ): Promise<boolean> {
    // Añadir a fases en ejecución
    phases.forEach(p => runningPhases.value.add(p))

    _analyzing.value[projectId] = true
    _analyses.value[projectId] = {
      project_id: projectId,
      status: 'running',
      progress: 0,
      current_phase: PHASE_LABELS[phases[0]] || 'Analizando...',
      phases: phases.map(p => ({
        id: p,
        name: PHASE_LABELS[p],
        completed: false,
        current: p === phases[0]
      }))
    }
    delete _errors.value[projectId]

    try {
      await api.post(`/api/projects/${projectId}/analyze`, { phases, force })
      await loadExecutedPhases(projectId)
      return true
    } catch (err) {
      _errors.value[projectId] = err instanceof Error ? err.message : 'Error desconocido'
      console.error('Error in partial analysis:', err)
      return false
    } finally {
      // Quitar de fases en ejecución
      phases.forEach(p => runningPhases.value.delete(p))
      // Limpiar estado si no quedan fases corriendo
      if (runningPhases.value.size === 0) {
        _analyzing.value[projectId] = false
        delete _analyses.value[projectId]
      }
    }
  }

  /**
   * Verifica si una fase está actualmente ejecutándose.
   */
  function isPhaseRunning(phase: keyof ExecutedPhases): boolean {
    return runningPhases.value.has(phase)
  }

  /**
   * Obtiene todas las fases ejecutadas de un proyecto.
   */
  function getProjectPhases(projectId: number): Partial<ExecutedPhases> {
    return executedPhases.value[projectId] ?? {}
  }

  return {
    // State (computed: sigue el proyecto activo)
    currentAnalysis,
    isAnalyzing,
    error,
    executedPhases,
    runningPhases,
    // Internal maps (para uso avanzado/testing)
    _analyses,
    _analyzing,
    _errors,
    _activeProjectId,
    // Getters
    hasActiveAnalysis,
    hasAnyActiveAnalysis,
    progressPercentage,
    // Actions
    setActiveProjectId,
    startAnalysis,
    cancelAnalysis,
    getProgress,
    clearAnalysis,
    clearError,
    setAnalyzing,
    checkAnalysisStatus,
    // Per-project queries
    isProjectAnalyzing,
    getProjectProgress,
    // Phase tracking
    loadExecutedPhases,
    isPhaseExecuted,
    getMissingDependencies,
    canRunPhase,
    runPartialAnalysis,
    isPhaseRunning,
    getProjectPhases,
  }
})
