/**
 * Tests para el store de sistema
 *
 * Verifican health check, estado del backend, modelos, capabilities
 * y LanguageTool state machine.
 */

import { setActivePinia, createPinia } from 'pinia'
import { useSystemStore, type LTState as _LTState, type ModelsStatus, type SystemCapabilities } from '../system'

// ── Mocks ────────────────────────────────────────────────────

vi.mock('@/services/apiClient', () => ({
  api: {
    get: vi.fn(),
    getRaw: vi.fn(),
    post: vi.fn(),
    postRaw: vi.fn(),
    tryGet: vi.fn(),
  },
}))

import { api } from '@/services/apiClient'
const mockApi = api as unknown as {
  get: ReturnType<typeof vi.fn>
  getRaw: ReturnType<typeof vi.fn>
  post: ReturnType<typeof vi.fn>
  postRaw: ReturnType<typeof vi.fn>
  tryGet: ReturnType<typeof vi.fn>
}

// ── Tests ────────────────────────────────────────────────────

describe('systemStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  // ── Initial state ──────────────────────────────────────

  describe('initial state', () => {
    it('should start disconnected', () => {
      const store = useSystemStore()
      expect(store.backendConnected).toBe(false)
      expect(store.backendVersion).toBe('unknown')
      expect(store.backendReady).toBe(false)
      expect(store.backendStarting).toBe(true)
      expect(store.backendStartupError).toBeNull()
    })

    it('should have no models status', () => {
      const store = useSystemStore()
      expect(store.modelsStatus).toBeNull()
      expect(store.modelsLoading).toBe(false)
      expect(store.modelsDownloading).toBe(false)
      expect(store.modelsError).toBeNull()
    })

    it('should have correct computed defaults', () => {
      const store = useSystemStore()
      expect(store.modelsReady).toBe(false)
      expect(store.dependenciesInstalling).toBe(false)
      expect(store.dependenciesNeeded).toBe(false)
      expect(store.backendLoaded).toBe(false)
      expect(store.pythonAvailable).toBe(true) // defaults to true
    })

    it('should have no capabilities', () => {
      const store = useSystemStore()
      expect(store.systemCapabilities).toBeNull()
      expect(store.capabilitiesLoading).toBe(false)
    })

    it('should have LT in not_installed state', () => {
      const store = useSystemStore()
      expect(store.ltState).toBe('not_installed')
      expect(store.ltInstalling).toBe(false)
      expect(store.ltStarting).toBe(false)
    })
  })

  // ── checkBackendStatus ─────────────────────────────────

  describe('checkBackendStatus', () => {
    it('should set connected on successful health check', async () => {
      mockApi.getRaw.mockResolvedValueOnce({ status: 'ok', version: '0.7.22' })

      const store = useSystemStore()
      await store.checkBackendStatus()

      expect(store.backendConnected).toBe(true)
      expect(store.backendVersion).toBe('0.7.22')
      expect(store.backendReady).toBe(true)
      expect(store.backendStarting).toBe(false)
    })

    it('should set disconnected on failed health check', async () => {
      mockApi.getRaw.mockRejectedValueOnce(new Error('Connection refused'))

      const store = useSystemStore()
      await store.checkBackendStatus()

      expect(store.backendConnected).toBe(false)
    })

    it('should set disconnected on non-ok health payload', async () => {
      mockApi.getRaw.mockResolvedValueOnce({ status: 'error' })

      const store = useSystemStore()
      await store.checkBackendStatus()

      expect(store.backendConnected).toBe(false)
    })

    it('should handle missing version in response', async () => {
      mockApi.getRaw.mockResolvedValueOnce({ status: 'ok' })

      const store = useSystemStore()
      await store.checkBackendStatus()

      expect(store.backendVersion).toBe('unknown')
    })
  })

  // ── checkModelsStatus ──────────────────────────────────

  describe('checkModelsStatus', () => {
    it('should fetch and store models status', async () => {
      const modelsData: ModelsStatus = {
        nlp_models: {
          spacy: { type: 'spacy', installed: true, display_name: 'spaCy', size_mb: 540 },
          embeddings: { type: 'embeddings', installed: true, display_name: 'Embeddings', size_mb: 470 },
        },
        ollama: { installed: true, models: ['llama3.2'] },
        all_required_installed: true,
      }

      mockApi.get.mockResolvedValueOnce(modelsData)

      const store = useSystemStore()
      const result = await store.checkModelsStatus()

      expect(mockApi.get).toHaveBeenCalledWith('/api/models/status')
      expect(result).toEqual(modelsData)
      expect(store.modelsStatus).toEqual(modelsData)
      expect(store.modelsReady).toBe(true)
    })

    it('should set loading during fetch', async () => {
      let resolvePromise: (v: ModelsStatus) => void
      mockApi.get.mockReturnValueOnce(new Promise(r => { resolvePromise = r }))

      const store = useSystemStore()
      const promise = store.checkModelsStatus()

      expect(store.modelsLoading).toBe(true)

      resolvePromise!({
        nlp_models: {},
        ollama: { installed: false, models: [] },
        all_required_installed: false,
      })
      await promise

      expect(store.modelsLoading).toBe(false)
    })

    it('should handle errors', async () => {
      mockApi.get.mockRejectedValueOnce(new Error('Server error'))

      const store = useSystemStore()
      const result = await store.checkModelsStatus()

      expect(result).toBeNull()
      expect(store.modelsError).toBe('Server error')
      expect(store.modelsLoading).toBe(false)
    })
  })

  // ── Computed: modelsReady / dependencies ────────────────

  describe('computed: model state', () => {
    it('modelsReady should reflect all_required_installed', async () => {
      const store = useSystemStore()

      mockApi.get.mockResolvedValueOnce({
        nlp_models: {},
        ollama: { installed: false, models: [] },
        all_required_installed: false,
      })
      await store.checkModelsStatus()
      expect(store.modelsReady).toBe(false)

      mockApi.get.mockResolvedValueOnce({
        nlp_models: {},
        ollama: { installed: true, models: ['llama3.2'] },
        all_required_installed: true,
      })
      await store.checkModelsStatus()
      expect(store.modelsReady).toBe(true)
    })

    it('dependenciesNeeded should reflect backend response', async () => {
      const store = useSystemStore()

      mockApi.get.mockResolvedValueOnce({
        nlp_models: {},
        ollama: { installed: false, models: [] },
        all_required_installed: false,
        dependencies_needed: true,
      })
      await store.checkModelsStatus()

      expect(store.dependenciesNeeded).toBe(true)
    })

    it('pythonAvailable should default to true if not set', () => {
      const store = useSystemStore()
      expect(store.pythonAvailable).toBe(true)
    })

    it('pythonAvailable should reflect backend response', async () => {
      const store = useSystemStore()

      mockApi.get.mockResolvedValueOnce({
        nlp_models: {},
        ollama: { installed: false, models: [] },
        all_required_installed: false,
        python_available: false,
        python_error: 'Python not found',
      })
      await store.checkModelsStatus()

      expect(store.pythonAvailable).toBe(false)
      expect(store.pythonError).toBe('Python not found')
    })
  })

  // ── loadCapabilities ───────────────────────────────────

  describe('loadCapabilities', () => {
    const mockCapabilities: SystemCapabilities = {
      hardware: {
        gpu: null,
        gpu_type: 'none',
        has_gpu: false,
        has_high_vram: false,
        has_cupy: false,
        gpu_blocked: null,
        cpu: { name: 'Intel Xeon E3-1505M' },
      },
      embeddings_available: true,
      ollama: {
        installed: true,
        available: true,
        models: [{ name: 'llama3.2', size: 2000000000, modified: '2025-01-01' }],
        recommended_models: ['llama3.2', 'qwen2.5'],
      },
      nlp_methods: {
        coreference: {},
        ner: {},
        grammar: {},
      },
      recommended_config: {
        device_preference: 'cpu',
        spacy_gpu_enabled: false,
        embeddings_gpu_enabled: false,
        batch_size: 16,
      },
    }

    it('should fetch and cache capabilities', async () => {
      mockApi.get.mockResolvedValueOnce(mockCapabilities)

      const store = useSystemStore()
      const result = await store.loadCapabilities()

      expect(mockApi.get).toHaveBeenCalledWith('/api/system/capabilities')
      expect(result).toEqual(mockCapabilities)
      expect(store.systemCapabilities).toEqual(mockCapabilities)
    })

    it('should use cache on second call', async () => {
      mockApi.get.mockResolvedValueOnce(mockCapabilities)

      const store = useSystemStore()
      await store.loadCapabilities()
      const result = await store.loadCapabilities()

      expect(mockApi.get).toHaveBeenCalledTimes(1) // Not called again
      expect(result).toEqual(mockCapabilities)
    })

    it('should force refresh when requested', async () => {
      mockApi.get.mockResolvedValue(mockCapabilities)

      const store = useSystemStore()
      await store.loadCapabilities()
      await store.loadCapabilities(true)

      expect(mockApi.get).toHaveBeenCalledTimes(2)
    })

    it('should set loading during fetch', async () => {
      let resolvePromise: (v: SystemCapabilities) => void
      mockApi.get.mockReturnValueOnce(new Promise(r => { resolvePromise = r }))

      const store = useSystemStore()
      const promise = store.loadCapabilities()

      expect(store.capabilitiesLoading).toBe(true)

      resolvePromise!(mockCapabilities)
      await promise

      expect(store.capabilitiesLoading).toBe(false)
    })

    it('should return null on error', async () => {
      mockApi.get.mockRejectedValueOnce(new Error('Network'))

      const store = useSystemStore()
      const result = await store.loadCapabilities()

      expect(result).toBeNull()
      expect(store.capabilitiesLoading).toBe(false)
    })
  })

  // ── ltState computed ───────────────────────────────────

  describe('ltState computed', () => {
    it('should be not_installed when no capabilities', () => {
      const store = useSystemStore()
      expect(store.ltState).toBe('not_installed')
    })

    it('should be not_installed when LT not in capabilities', async () => {
      mockApi.get.mockResolvedValueOnce({
        hardware: { gpu: null, gpu_type: 'none', has_gpu: false, has_high_vram: false, has_cupy: false, gpu_blocked: null, cpu: { name: 'test' } },
        ollama: { installed: false, available: false, models: [], recommended_models: [] },
        nlp_methods: { coreference: {}, ner: {}, grammar: {} },
        recommended_config: { device_preference: 'cpu', spacy_gpu_enabled: false, embeddings_gpu_enabled: false, batch_size: 16 },
      })

      const store = useSystemStore()
      await store.loadCapabilities()

      expect(store.ltState).toBe('not_installed')
    })

    it('should be installing when ltInstalling is true (with capabilities)', async () => {
      mockApi.get.mockResolvedValueOnce({
        hardware: { gpu: null, gpu_type: 'none', has_gpu: false, has_high_vram: false, has_cupy: false, gpu_blocked: null, cpu: { name: 'test' } },
        ollama: { installed: false, available: false, models: [], recommended_models: [] },
        languagetool: { installed: false, running: false, installing: false, java_available: false },
        nlp_methods: { coreference: {}, ner: {}, grammar: {} },
        recommended_config: { device_preference: 'cpu', spacy_gpu_enabled: false, embeddings_gpu_enabled: false, batch_size: 16 },
      })

      const store = useSystemStore()
      await store.loadCapabilities()
      store.ltInstalling = true
      expect(store.ltState).toBe('installing')
    })

    it('should be installed_not_running when installed but not running', async () => {
      mockApi.get.mockResolvedValueOnce({
        hardware: { gpu: null, gpu_type: 'none', has_gpu: false, has_high_vram: false, has_cupy: false, gpu_blocked: null, cpu: { name: 'test' } },
        ollama: { installed: false, available: false, models: [], recommended_models: [] },
        languagetool: { installed: true, running: false, installing: false, java_available: true },
        nlp_methods: { coreference: {}, ner: {}, grammar: {} },
        recommended_config: { device_preference: 'cpu', spacy_gpu_enabled: false, embeddings_gpu_enabled: false, batch_size: 16 },
      })

      const store = useSystemStore()
      await store.loadCapabilities()

      expect(store.ltState).toBe('installed_not_running')
    })

    it('should be running when installed and running', async () => {
      mockApi.get.mockResolvedValueOnce({
        hardware: { gpu: null, gpu_type: 'none', has_gpu: false, has_high_vram: false, has_cupy: false, gpu_blocked: null, cpu: { name: 'test' } },
        ollama: { installed: false, available: false, models: [], recommended_models: [] },
        languagetool: { installed: true, running: true, installing: false, java_available: true },
        nlp_methods: { coreference: {}, ner: {}, grammar: {} },
        recommended_config: { device_preference: 'cpu', spacy_gpu_enabled: false, embeddings_gpu_enabled: false, batch_size: 16 },
      })

      const store = useSystemStore()
      await store.loadCapabilities()

      expect(store.ltState).toBe('running')
    })
  })

  // ── downloadModels ─────────────────────────────────────

  describe('downloadModels', () => {
    it('should trigger download and start polling', async () => {
      mockApi.post.mockResolvedValueOnce({})

      const store = useSystemStore()
      const result = await store.downloadModels(['spacy', 'embeddings'])

      expect(mockApi.post).toHaveBeenCalledWith('/api/models/download', {
        models: ['spacy', 'embeddings'],
        force: false,
      })
      expect(result).toBe(true)
    })

    it('should handle download errors', async () => {
      mockApi.post.mockRejectedValueOnce(new Error('Download failed'))

      const store = useSystemStore()
      const result = await store.downloadModels()

      expect(result).toBe(false)
      expect(store.modelsError).toBe('Download failed')
    })

    it('should surface actionable error when progress polling keeps failing', async () => {
      mockApi.post.mockResolvedValueOnce({})
      mockApi.tryGet.mockResolvedValue(null)
      mockApi.get.mockResolvedValue({
        nlp_models: {},
        ollama: { installed: false, models: [] },
        all_required_installed: false,
      })

      const store = useSystemStore()
      const result = await store.downloadModels(['spacy'])
      expect(result).toBe(true)

      await vi.advanceTimersByTimeAsync(4500)

      expect(store.modelsError).toContain('No pudimos actualizar el progreso de la descarga')
      store.stopPolling()
    })
  })

  describe('installLanguageTool', () => {
    it('should expose actionable error if install startup fails', async () => {
      mockApi.postRaw.mockRejectedValueOnce(new Error('Install start failed'))

      const store = useSystemStore()
      const result = await store.installLanguageTool()

      expect(result).toBe(false)
      expect(store.ltInstalling).toBe(false)
      expect(store.ltInstallProgress?.error).toBe('install_start_failed')
      expect(store.ltInstallProgress?.detail).toContain('El sistema puede seguir ocupado')
    })
  })

  // ── stopPolling ────────────────────────────────────────


  describe('prepareAdvancedServicesOnStartup', () => {
    const baseCaps: SystemCapabilities = {
      hardware: {
        gpu: null,
        gpu_type: 'none',
        has_gpu: false,
        has_high_vram: false,
        has_cupy: false,
        gpu_blocked: null,
        cpu: { name: 'test' },
      },
      embeddings_available: true,
      ollama: {
        installed: true,
        available: true,
        models: [],
        recommended_models: [],
      },
      languagetool: {
        installed: true,
        running: true,
        installing: false,
        java_available: true,
      },
      nlp_methods: {
        coreference: {},
        ner: {},
        grammar: {},
      },
      recommended_config: {
        device_preference: 'cpu',
        spacy_gpu_enabled: false,
        embeddings_gpu_enabled: false,
        batch_size: 16,
      },
    }

    it('instala LanguageTool si falta y devuelve warning si falla', async () => {
      const capsMissingLt = {
        ...baseCaps,
        languagetool: { ...baseCaps.languagetool!, installed: false, running: false },
      }
      mockApi.get
        .mockResolvedValueOnce(capsMissingLt)
        .mockResolvedValueOnce(capsMissingLt)
        .mockResolvedValueOnce(capsMissingLt)
      mockApi.postRaw.mockResolvedValueOnce({ success: false })

      const store = useSystemStore()
      const result = await store.prepareAdvancedServicesOnStartup()

      expect(mockApi.postRaw).toHaveBeenCalledWith('/api/languagetool/install')
      expect(result.languagetoolReady).toBe(false)
      expect(result.warnings[0]).toContain('corrector avanzado')
    })

    it('inicia LanguageTool si esta instalado pero parado', async () => {
      const capsStoppedLt = {
        ...baseCaps,
        languagetool: { ...baseCaps.languagetool!, installed: true, running: false },
      }
      mockApi.get
        .mockResolvedValueOnce(capsStoppedLt)
        .mockResolvedValueOnce(baseCaps)
        .mockResolvedValueOnce(baseCaps)
      mockApi.tryGet.mockResolvedValueOnce(baseCaps)
      mockApi.postRaw.mockResolvedValueOnce({ success: true })

      const store = useSystemStore()
      const resultPromise = store.prepareAdvancedServicesOnStartup()
      await vi.advanceTimersByTimeAsync(3000)
      const result = await resultPromise

      expect(mockApi.postRaw).toHaveBeenCalledWith('/api/languagetool/start')
      expect(result.languagetoolReady).toBe(true)
      expect(result.warnings).toEqual([])
    })

    it('instala Ollama si falta y lo inicia si luego sigue parado', async () => {
      const capsMissingOllama = {
        ...baseCaps,
        ollama: { ...baseCaps.ollama, installed: false, available: false },
      }
      const capsInstalledButStopped = {
        ...baseCaps,
        ollama: { ...baseCaps.ollama, installed: true, available: false },
      }
      mockApi.get
        .mockResolvedValueOnce(capsMissingOllama)
        .mockResolvedValueOnce(capsInstalledButStopped)
        .mockResolvedValueOnce(baseCaps)
        .mockResolvedValueOnce(baseCaps)
      mockApi.postRaw
        .mockResolvedValueOnce({ success: true })
        .mockResolvedValueOnce({ success: true })

      const store = useSystemStore()
      const resultPromise = store.prepareAdvancedServicesOnStartup()
      await vi.advanceTimersByTimeAsync(3000)
      await Promise.resolve()
      await vi.advanceTimersByTimeAsync(2000)
      const result = await resultPromise

      expect(mockApi.postRaw).toHaveBeenNthCalledWith(1, '/api/ollama/install')
      expect(mockApi.postRaw).toHaveBeenNthCalledWith(2, '/api/ollama/start')
      expect(result.ollamaReady).toBe(true)
      expect(result.warnings).toEqual([])
    }, 10000)

    it('devuelve warning si Ollama no puede iniciarse', async () => {
      const capsStoppedOllama = {
        ...baseCaps,
        ollama: { ...baseCaps.ollama, installed: true, available: false },
      }
      mockApi.get
        .mockResolvedValueOnce(capsStoppedOllama)
        .mockResolvedValueOnce(capsStoppedOllama)
      mockApi.postRaw.mockResolvedValueOnce({ success: false })

      const store = useSystemStore()
      const result = await store.prepareAdvancedServicesOnStartup()

      expect(mockApi.postRaw).toHaveBeenCalledWith('/api/ollama/start')
      expect(result.ollamaReady).toBe(false)
      expect(result.warnings[0]).toContain('analizador inteligente')
    })
  })

  describe('stopPolling', () => {
    it('should clear download progress', () => {
      const store = useSystemStore()
      store.downloadProgress = { spacy: { model_type: 'spacy', phase: 'downloading', bytes_downloaded: 100, bytes_total: 500, percent: 20, speed_bps: 1000, speed_mbps: 0.001, eta_seconds: 10, error: null } }

      store.stopPolling()

      expect(store.downloadProgress).toEqual({})
    })
  })

  // ── refreshCapabilities ────────────────────────────────

  describe('refreshCapabilities', () => {
    it('should silently update capabilities', async () => {
      const newCaps = {
        hardware: { gpu: null, gpu_type: 'none', has_gpu: false, has_high_vram: false, has_cupy: false, gpu_blocked: null, cpu: { name: 'test' } },
        ollama: { installed: true, available: true, models: [], recommended_models: [] },
        nlp_methods: { coreference: {}, ner: {}, grammar: {} },
        recommended_config: { device_preference: 'cpu', spacy_gpu_enabled: false, embeddings_gpu_enabled: false, batch_size: 16 },
      }
      mockApi.tryGet.mockResolvedValueOnce(newCaps)

      const store = useSystemStore()
      await store.refreshCapabilities()

      expect(store.systemCapabilities).toEqual(newCaps)
      // No loading spinner shown
      expect(store.capabilitiesLoading).toBe(false)
    })

    it('should not crash on null response', async () => {
      mockApi.tryGet.mockResolvedValueOnce(null)

      const store = useSystemStore()
      await store.refreshCapabilities()

      expect(store.systemCapabilities).toBeNull()
    })
  })
})
