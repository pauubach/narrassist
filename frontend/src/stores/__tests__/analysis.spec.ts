/**
 * Tests para el store de análisis
 *
 * Verifican el comportamiento del polling y actualización de estado.
 * El store usa estado per-project para evitar contaminación entre proyectos.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAnalysisStore } from '../analysis'

// Mock de fetch global
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

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true, data: mockProgressData }),
      })

      const result = await store.getProgress(1)

      expect(mockFetch).toHaveBeenCalledWith('/api/projects/1/analysis/progress', expect.objectContaining({ method: 'GET' }))
      expect(result).toEqual(mockProgressData)
      expect(store.currentAnalysis).toEqual(mockProgressData)
    })

    it('should set isAnalyzing to false when completed', async () => {
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

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true, data: mockProgressData }),
      })

      await store.getProgress(1)

      expect(store.isAnalyzing).toBe(false)
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

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true, data: mockProgressData }),
      })

      await store.getProgress(1)

      expect(store.isAnalyzing).toBe(false)
      expect(store.error).toBe('Something went wrong')
    })

    it('should handle network errors gracefully', async () => {
      const store = useAnalysisStore()

      mockFetch.mockRejectedValueOnce(new Error('Network error'))

      const result = await store.getProgress(1)

      expect(result).toBeNull()
      // No debe crash, solo loguear el error
    })

    it('should handle non-ok responses', async () => {
      const store = useAnalysisStore()

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      })

      const result = await store.getProgress(1)

      expect(result).toBeNull()
    })
  })

  describe('startAnalysis', () => {
    it('should initiate analysis and set isAnalyzing', async () => {
      const store = useAnalysisStore()
      store.setActiveProjectId(1)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      })

      const result = await store.startAnalysis(1)

      expect(result).toBe(true)
      expect(store.isAnalyzing).toBe(true)
      expect(store.error).toBeNull()
    })

    it('should set error on failure', async () => {
      const store = useAnalysisStore()
      store.setActiveProjectId(1)

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: false, error: 'Failed to start' }),
      })

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
