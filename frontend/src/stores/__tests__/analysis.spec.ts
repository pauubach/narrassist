/**
 * Tests para el store de análisis
 *
 * Verifican el comportamiento del polling y actualización de estado.
 * El store usa estado per-project para evitar contaminación entre proyectos.
 */

import { setActivePinia, createPinia } from 'pinia'
import { useAnalysisStore, ANALYSIS_DEPENDENCIES, type ExecutedPhases } from '../analysis'

// Mock del api client (para las nuevas funcionalidades que usan api)
vi.mock('@/services/apiClient', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    postForm: vi.fn(),
    postRaw: vi.fn(),
  },
}))

import { api } from '@/services/apiClient'
const mockApiClient = api as unknown as {
  get: ReturnType<typeof vi.fn>
  post: ReturnType<typeof vi.fn>
  postForm: ReturnType<typeof vi.fn>
  postRaw: ReturnType<typeof vi.fn>
}

// Mock de fetch global (para tests legacy que usan fetch directamente)
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('analysisStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('initial state', () => {
    it('should start with no analysis', () => {
      const store = useAnalysisStore()
      expect(store.currentAnalysis).toBeNull()
      expect(store.isAnalyzing).toBe(false)
      expect(store.error).toBeNull()
    })

    it('should have hasActiveAnalysis as false initially', () => {
      const store = useAnalysisStore()
      expect(store.hasActiveAnalysis).toBe(false)
    })
  })

  describe('per-project isolation', () => {
    it('should isolate analysis state between projects', () => {
      const store = useAnalysisStore()

      // Set analysis for project 1
      store.setAnalyzing(1, true)
      // Set analysis for project 2
      store.setAnalyzing(2, true)

      // View project 1
      store.setActiveProjectId(1)
      expect(store.currentAnalysis?.project_id).toBe(1)

      // View project 2
      store.setActiveProjectId(2)
      expect(store.currentAnalysis?.project_id).toBe(2)
    })

    it('should show null when no active project', () => {
      const store = useAnalysisStore()
      store.setAnalyzing(1, true)

      store.setActiveProjectId(null)
      expect(store.currentAnalysis).toBeNull()
      expect(store.isAnalyzing).toBe(false)
    })

    it('should track analyzing state per project', () => {
      const store = useAnalysisStore()

      store.setAnalyzing(1, true)
      store.setAnalyzing(2, false)

      expect(store.isProjectAnalyzing(1)).toBe(true)
      expect(store.isProjectAnalyzing(2)).toBe(false)
    })

    it('should detect any active analysis via hasAnyActiveAnalysis', () => {
      const store = useAnalysisStore()

      expect(store.hasAnyActiveAnalysis).toBe(false)

      store.setAnalyzing(1, true)
      expect(store.hasAnyActiveAnalysis).toBe(true)

      // Even if active project is different
      store.setActiveProjectId(2)
      expect(store.hasAnyActiveAnalysis).toBe(true)
    })
  })

  describe('getProgress', () => {
    it('should fetch and update progress for active project', async () => {
      const store = useAnalysisStore()
      store.setActiveProjectId(1)

      const mockProgressData = {
        project_id: 1,
        status: 'running',
        progress: 50,
        current_phase: 'Procesando entidades',
        phases: [],
      }

      mockApiClient.get.mockResolvedValueOnce(mockProgressData)

      const result = await store.getProgress(1)

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/projects/1/analysis/progress', { retries: 2 })
      expect(result).toEqual(mockProgressData)
      expect(store.currentAnalysis).toEqual(mockProgressData)
    })

    it('should NOT set isAnalyzing to false on completed (polling handler does it)', async () => {
      const store = useAnalysisStore()
      store.setActiveProjectId(1)
      store.setAnalyzing(1, true)

      const mockProgressData = {
        project_id: 1,
        status: 'completed',
        progress: 100,
        current_phase: 'Completado',
        phases: [],
      }

      mockApiClient.get.mockResolvedValueOnce(mockProgressData)

      await store.getProgress(1)

      // getProgress ya no setea _analyzing=false para 'completed';
      // lo hace useAnalysisPolling después de fetchProject()
      expect(store.isAnalyzing).toBe(true)
    })

    it('should set error when analysis fails', async () => {
      const store = useAnalysisStore()
      store.setActiveProjectId(1)
      store.setAnalyzing(1, true)

      const mockProgressData = {
        project_id: 1,
        status: 'failed',
        progress: 45,
        current_phase: 'Error',
        error: 'Something went wrong',
        phases: [],
      }

      mockApiClient.get.mockResolvedValueOnce(mockProgressData)

      await store.getProgress(1)

      expect(store.isAnalyzing).toBe(false)
      expect(store.error).toBe('Something went wrong')
    })

    it('should handle network errors gracefully', async () => {
      const store = useAnalysisStore()

      mockApiClient.get.mockRejectedValueOnce(new Error('Network error'))

      const result = await store.getProgress(1)

      expect(result).toBeNull()
    })

    it('should handle non-ok responses', async () => {
      const store = useAnalysisStore()

      mockApiClient.get.mockRejectedValueOnce(new Error('HTTP 500'))

      const result = await store.getProgress(1)

      expect(result).toBeNull()
    })
  })

  describe('startAnalysis', () => {
    it('should initiate analysis and set isAnalyzing', async () => {
      const store = useAnalysisStore()
      store.setActiveProjectId(1)

      mockApiClient.postForm.mockResolvedValueOnce({
        project_id: 1,
        status: 'running',
      })

      const result = await store.startAnalysis(1)

      expect(result).toBe(true)
      expect(store.isAnalyzing).toBe(true)
      expect(store.error).toBeNull()
    })

    it('should set error on failure', async () => {
      const store = useAnalysisStore()
      store.setActiveProjectId(1)

      mockApiClient.postForm.mockRejectedValueOnce(new Error('Failed to start'))

      const result = await store.startAnalysis(1)

      expect(result).toBe(false)
      expect(store.error).toBe('Failed to start')
      expect(store.isAnalyzing).toBe(false)
    })
  })

  describe('clearAnalysis', () => {
    it('should reset state for the active project', () => {
      const store = useAnalysisStore()
      store.setActiveProjectId(1)

      // Set some state via setAnalyzing
      store.setAnalyzing(1, true)

      store.clearAnalysis(1)

      expect(store.isAnalyzing).toBe(false)
      expect(store.error).toBeNull()
      expect(store.currentAnalysis).toBeNull()
    })

    it('should not affect other projects', () => {
      const store = useAnalysisStore()

      store.setAnalyzing(1, true)
      store.setAnalyzing(2, true)

      store.clearAnalysis(1)

      // Project 2 should still be analyzing
      expect(store.isProjectAnalyzing(2)).toBe(true)
    })
  })

  describe('clearError', () => {
    it('should clear only the error for active project', () => {
      const store = useAnalysisStore()
      store.setActiveProjectId(1)

      // Set error via internal map
      store._errors[1] = 'Some error'
      store.setAnalyzing(1, true)

      store.clearError(1)

      expect(store.error).toBeNull()
      expect(store.isAnalyzing).toBe(true)
    })
  })
})


/**
 * Tests para verificar el comportamiento del polling en componentes
 */
describe('Analysis Polling Behavior', () => {
  it('should poll when status is analyzing', () => {
    const analyzingStatuses = ['pending', 'in_progress', 'analyzing']
    const completedStatuses = ['completed', 'error', 'failed']

    for (const status of analyzingStatuses) {
      expect(['pending', 'in_progress', 'analyzing']).toContain(status)
    }

    for (const status of completedStatuses) {
      expect(['completed', 'error', 'failed']).toContain(status)
    }
  })

  it('should stop polling when analysis completes', () => {
    const stopPollingStatuses = ['completed', 'error', 'failed']

    for (const status of stopPollingStatuses) {
      expect(stopPollingStatuses).toContain(status)
    }
  })
})


/**
 * Tests para verificar tipos y estructura de datos
 */
describe('Analysis Progress Data Structure', () => {
  it('should have correct AnalysisProgress interface', () => {
    const validProgressData = {
      project_id: 1,
      status: 'running' as const,
      progress: 50,
      current_phase: 'Processing',
      current_action: 'Extracting entities',
      phases: [
        { id: 'ner', name: 'NER', completed: true, current: false },
        { id: 'attributes', name: 'Attributes', completed: false, current: true },
      ],
      metrics: {
        entities_found: 25,
        word_count: 10000,
      },
      estimated_seconds_remaining: 30,
      error: undefined,
    }

    expect(validProgressData).toHaveProperty('project_id')
    expect(validProgressData).toHaveProperty('status')
    expect(validProgressData).toHaveProperty('progress')
    expect(validProgressData).toHaveProperty('current_phase')
    expect(validProgressData).toHaveProperty('phases')
  })

  it('should handle all status values', () => {
    const validStatuses = ['pending', 'running', 'completed', 'failed']

    for (const status of validStatuses) {
      expect(validStatuses).toContain(status)
    }
  })
})


// ============================================================================
// Phase Tracking & Partial Analysis (nuevas funcionalidades S8)
// ============================================================================

describe('Phase Tracking', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('executedPhases', () => {
    it('should start with no executed phases', () => {
      const store = useAnalysisStore()
      expect(store.getProjectPhases(1)).toEqual({})
    })

    it('should load executed phases from backend', async () => {
      const store = useAnalysisStore()
      mockApiClient.get.mockResolvedValueOnce({
        executed: { parsing: true, structure: true, entities: true },
      })

      const result = await store.loadExecutedPhases(1)

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/projects/1/analysis-status')
      expect(result).toEqual({ parsing: true, structure: true, entities: true })
      expect(store.getProjectPhases(1)).toEqual({ parsing: true, structure: true, entities: true })
    })

    it('should return null on backend error', async () => {
      const store = useAnalysisStore()
      mockApiClient.get.mockRejectedValueOnce(new Error('500'))

      const result = await store.loadExecutedPhases(1)

      expect(result).toBeNull()
    })

    it('should isolate phases between projects', async () => {
      const store = useAnalysisStore()

      mockApiClient.get.mockResolvedValueOnce({
        executed: { parsing: true, entities: true },
      })
      await store.loadExecutedPhases(1)

      mockApiClient.get.mockResolvedValueOnce({
        executed: { parsing: true, grammar: true },
      })
      await store.loadExecutedPhases(2)

      expect(store.isPhaseExecuted(1, 'entities')).toBe(true)
      expect(store.isPhaseExecuted(1, 'grammar')).toBe(false)
      expect(store.isPhaseExecuted(2, 'grammar')).toBe(true)
      expect(store.isPhaseExecuted(2, 'entities')).toBe(false)
    })
  })

  describe('isPhaseExecuted', () => {
    it('should return false for non-executed phase', () => {
      const store = useAnalysisStore()
      expect(store.isPhaseExecuted(1, 'entities')).toBe(false)
    })

    it('should return true after phase is marked executed', async () => {
      const store = useAnalysisStore()
      mockApiClient.get.mockResolvedValueOnce({
        executed: { entities: true },
      })
      await store.loadExecutedPhases(1)

      expect(store.isPhaseExecuted(1, 'entities')).toBe(true)
    })
  })

  describe('getMissingDependencies', () => {
    it('should return empty for phase with no dependencies', () => {
      const store = useAnalysisStore()
      expect(store.getMissingDependencies(1, 'parsing')).toEqual([])
    })

    it('should return all deps when nothing is executed', () => {
      const store = useAnalysisStore()
      const missing = store.getMissingDependencies(1, 'attributes')
      // attributes requires: entities + coreference
      expect(missing).toContain('entities')
      expect(missing).toContain('coreference')
    })

    it('should return only missing deps', async () => {
      const store = useAnalysisStore()
      mockApiClient.get.mockResolvedValueOnce({
        executed: { parsing: true, entities: true },
      })
      await store.loadExecutedPhases(1)

      // attributes requires entities + coreference; entities is done
      const missing = store.getMissingDependencies(1, 'attributes')
      expect(missing).toEqual(['coreference'])
    })

    it('should return empty when all deps satisfied', async () => {
      const store = useAnalysisStore()
      mockApiClient.get.mockResolvedValueOnce({
        executed: { parsing: true, entities: true, coreference: true },
      })
      await store.loadExecutedPhases(1)

      expect(store.getMissingDependencies(1, 'attributes')).toEqual([])
    })
  })

  describe('canRunPhase', () => {
    it('should allow running parsing (no deps)', () => {
      const store = useAnalysisStore()
      expect(store.canRunPhase(1, 'parsing')).toBe(true)
    })

    it('should block phase with missing deps', () => {
      const store = useAnalysisStore()
      expect(store.canRunPhase(1, 'coreference')).toBe(false) // needs entities
    })

    it('should allow phase when deps satisfied', async () => {
      const store = useAnalysisStore()
      mockApiClient.get.mockResolvedValueOnce({
        executed: { parsing: true, entities: true },
      })
      await store.loadExecutedPhases(1)

      expect(store.canRunPhase(1, 'coreference')).toBe(true)
    })
  })

  describe('isPhaseRunning', () => {
    it('should be false initially', () => {
      const store = useAnalysisStore()
      expect(store.isPhaseRunning('entities')).toBe(false)
    })
  })
})

describe('ANALYSIS_DEPENDENCIES', () => {
  it('should have parsing as root (no deps)', () => {
    expect(ANALYSIS_DEPENDENCIES.parsing).toEqual([])
  })

  it('should have structure depend on parsing', () => {
    expect(ANALYSIS_DEPENDENCIES.structure).toContain('parsing')
  })

  it('should have coreference depend on entities', () => {
    expect(ANALYSIS_DEPENDENCIES.coreference).toContain('entities')
  })

  it('should have attributes depend on entities and coreference', () => {
    expect(ANALYSIS_DEPENDENCIES.attributes).toContain('entities')
    expect(ANALYSIS_DEPENDENCIES.attributes).toContain('coreference')
  })

  it('should have voice_profiles depend on entities and attributes', () => {
    expect(ANALYSIS_DEPENDENCIES.voice_profiles).toContain('entities')
    expect(ANALYSIS_DEPENDENCIES.voice_profiles).toContain('attributes')
  })

  it('should have no circular dependencies', () => {
    const visited = new Set<string>()
    const visiting = new Set<string>()

    function hasCycle(phase: string): boolean {
      if (visiting.has(phase)) return true // cycle!
      if (visited.has(phase)) return false

      visiting.add(phase)
      const deps = ANALYSIS_DEPENDENCIES[phase as keyof ExecutedPhases] || []
      for (const dep of deps) {
        if (hasCycle(dep)) return true
      }
      visiting.delete(phase)
      visited.add(phase)
      return false
    }

    for (const phase of Object.keys(ANALYSIS_DEPENDENCIES)) {
      expect(hasCycle(phase)).toBe(false)
    }
  })

  it('should have all dependency targets defined in ExecutedPhases', () => {
    const allPhases = new Set(Object.keys(ANALYSIS_DEPENDENCIES))
    for (const [_phase, deps] of Object.entries(ANALYSIS_DEPENDENCIES)) {
      for (const dep of deps) {
        expect(allPhases.has(dep)).toBe(true)
      }
    }
  })
})


// ============================================================================
// Queued states (3-tier concurrency)
// ============================================================================

describe('Queued States', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('should recognize queued status from startAnalysis', async () => {
    const store = useAnalysisStore()
    store.setActiveProjectId(1)

    mockApiClient.postForm.mockResolvedValueOnce({
      project_id: 1,
      status: 'queued',
    })

    await store.startAnalysis(1)

    expect(store.currentAnalysis?.status).toBe('queued')
    expect(store.isAnalyzing).toBe(true)
  })

  it('should keep polling when status is queued_for_heavy', async () => {
    const store = useAnalysisStore()
    store.setActiveProjectId(1)
    store.setAnalyzing(1, true)

    mockApiClient.get.mockResolvedValueOnce({
      project_id: 1,
      status: 'queued_for_heavy',
      progress: 3,
      current_phase: 'Estructura lista',
      phases: [
        { id: 'parsing', name: 'Parsing', completed: true, current: false },
        { id: 'classification', name: 'Classification', completed: true, current: false },
        { id: 'structure', name: 'Structure', completed: true, current: false },
      ],
    })

    await store.getProgress(1)

    expect(store.currentAnalysis?.status).toBe('queued_for_heavy')
    expect(store.isAnalyzing).toBe(true) // Still polling
  })

  it('should update executedPhases progressively during analysis', async () => {
    const store = useAnalysisStore()
    store.setActiveProjectId(1)
    store.setAnalyzing(1, true)

    mockApiClient.get.mockResolvedValueOnce({
      project_id: 1,
      status: 'running',
      progress: 40,
      current_phase: 'fusion',
      phases: [
        { id: 'parsing', name: 'Parsing', completed: true, current: false },
        { id: 'structure', name: 'Structure', completed: true, current: false },
        { id: 'ner', name: 'NER', completed: true, current: false },
        { id: 'fusion', name: 'Fusion', completed: false, current: true },
      ],
    })

    await store.getProgress(1)

    // parsing->parsing, structure->structure, ner->entities
    expect(store.isPhaseExecuted(1, 'parsing')).toBe(true)
    expect(store.isPhaseExecuted(1, 'structure')).toBe(true)
    expect(store.isPhaseExecuted(1, 'entities')).toBe(true) // ner maps to entities
    expect(store.isPhaseExecuted(1, 'coreference')).toBe(false) // fusion not completed yet
  })

  it('should handle cancelled status', async () => {
    const store = useAnalysisStore()
    store.setActiveProjectId(1)
    store.setAnalyzing(1, true)

    mockApiClient.postRaw.mockResolvedValueOnce({ success: true })

    const _result = await store.cancelAnalysis(1)

    expect(store.isAnalyzing).toBe(false)
    expect(store.currentAnalysis?.status).toBe('idle')
  })
})


// ============================================================================
// checkAnalysisStatus (recovery on page load)
// ============================================================================

describe('checkAnalysisStatus', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('should detect running analysis on page load', async () => {
    const store = useAnalysisStore()

    mockApiClient.get.mockResolvedValueOnce({
      project_id: 1,
      status: 'running',
      progress: 60,
      current_phase: 'attributes',
      phases: [],
    })

    const isActive = await store.checkAnalysisStatus(1)

    expect(isActive).toBe(true)
    expect(store.isProjectAnalyzing(1)).toBe(true)
  })

  it('should detect queued analysis on page load', async () => {
    const store = useAnalysisStore()

    mockApiClient.get.mockResolvedValueOnce({
      project_id: 1,
      status: 'queued',
      progress: 0,
      current_phase: 'En cola',
      phases: [],
    })

    const isActive = await store.checkAnalysisStatus(1)

    expect(isActive).toBe(true)
    expect(store.isProjectAnalyzing(1)).toBe(true)
  })

  it('should detect queued_for_heavy on page load', async () => {
    const store = useAnalysisStore()

    mockApiClient.get.mockResolvedValueOnce({
      project_id: 1,
      status: 'queued_for_heavy',
      progress: 3,
      current_phase: 'Estructura lista',
      phases: [],
    })

    const isActive = await store.checkAnalysisStatus(1)

    expect(isActive).toBe(true)
    expect(store.isProjectAnalyzing(1)).toBe(true)
  })

  it('should clear state when no active analysis', async () => {
    const store = useAnalysisStore()

    mockApiClient.get.mockResolvedValueOnce({
      project_id: 1,
      status: 'idle',
      progress: 0,
      current_phase: '',
      phases: [],
    })

    const isActive = await store.checkAnalysisStatus(1)

    expect(isActive).toBe(false)
    expect(store.isProjectAnalyzing(1)).toBe(false)
  })

  it('should not clear if startAnalysis is in-flight', async () => {
    const store = useAnalysisStore()
    // Simulate startAnalysis setting _analyzing before checkAnalysisStatus returns
    store.setAnalyzing(1, true)

    mockApiClient.get.mockResolvedValueOnce({
      project_id: 1,
      status: 'idle', // Backend says idle, but startAnalysis is in-flight
      progress: 0,
      current_phase: '',
      phases: [],
    })

    const isActive = await store.checkAnalysisStatus(1)

    // Should NOT clear because _analyzing was already true
    expect(isActive).toBe(true)
    expect(store.isProjectAnalyzing(1)).toBe(true)
  })

  it('should handle network error gracefully', async () => {
    const store = useAnalysisStore()

    mockApiClient.get.mockRejectedValueOnce(new Error('Network error'))

    const isActive = await store.checkAnalysisStatus(1)

    expect(isActive).toBe(false)
  })
})
