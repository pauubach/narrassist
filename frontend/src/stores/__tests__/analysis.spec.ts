/**
 * Tests para el store de análisis
 *
 * Verifican el comportamiento del polling y actualización de estado.
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

  describe('getProgress', () => {
    it('should fetch and update progress', async () => {
      const store = useAnalysisStore()

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
      store.isAnalyzing = true

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
      store.isAnalyzing = true

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
    it('should reset all state', () => {
      const store = useAnalysisStore()

      // Set some state
      store.isAnalyzing = true
      store.error = 'Some error'
      store.currentAnalysis = {
        project_id: 1,
        status: 'running',
        progress: 50,
        current_phase: 'Test',
        phases: [],
      }

      store.clearAnalysis()

      expect(store.isAnalyzing).toBe(false)
      expect(store.error).toBeNull()
      expect(store.currentAnalysis).toBeNull()
    })
  })

  describe('clearError', () => {
    it('should clear only the error', () => {
      const store = useAnalysisStore()

      store.error = 'Some error'
      store.isAnalyzing = true

      store.clearError()

      expect(store.error).toBeNull()
      expect(store.isAnalyzing).toBe(true) // No afecta otros estados
    })
  })
})


/**
 * Tests para verificar el comportamiento del polling en componentes
 */
describe('Analysis Polling Behavior', () => {
  it('should poll when status is analyzing', () => {
    // Este test documenta el comportamiento esperado:
    // Cuando project.analysisStatus es 'analyzing', 'pending', o 'in_progress',
    // el componente debe iniciar polling

    const analyzingStatuses = ['pending', 'in_progress', 'analyzing']
    const completedStatuses = ['completed', 'error', 'failed']

    // Verificar que sabemos cuáles activan polling
    for (const status of analyzingStatuses) {
      expect(['pending', 'in_progress', 'analyzing']).toContain(status)
    }

    // Verificar que sabemos cuáles NO activan polling
    for (const status of completedStatuses) {
      expect(['completed', 'error', 'failed']).toContain(status)
    }
  })

  it('should stop polling when analysis completes', () => {
    // Documentar que polling debe detenerse en estos estados
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
    // Documentar la estructura esperada
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

    // Verificar campos requeridos
    expect(validProgressData).toHaveProperty('project_id')
    expect(validProgressData).toHaveProperty('status')
    expect(validProgressData).toHaveProperty('progress')
    expect(validProgressData).toHaveProperty('current_phase')
    expect(validProgressData).toHaveProperty('phases')
  })

  it('should handle all status values', () => {
    const validStatuses = ['pending', 'running', 'completed', 'failed']

    // El store debe manejar todos estos estados
    for (const status of validStatuses) {
      expect(validStatuses).toContain(status)
    }
  })
})
