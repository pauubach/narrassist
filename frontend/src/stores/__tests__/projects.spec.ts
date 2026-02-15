/**
 * Tests para el store de proyectos
 *
 * Verifican CRUD, estado reactivo, computeds y manejo de errores.
 * El store depende de api client y transformers, ambos mockeados.
 */

import { setActivePinia, createPinia } from 'pinia'
import { useProjectsStore } from '../projects'
import type { Project as _Project } from '@/types'

// ── Mocks ────────────────────────────────────────────────────

// Mock del api client
vi.mock('@/services/apiClient', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    postForm: vi.fn(),
    put: vi.fn(),
    del: vi.fn(),
  },
}))

// Mock de ensureBackendReady (no-op en tests)
vi.mock('@/composables/useBackendReady', () => ({
  ensureBackendReady: vi.fn().mockResolvedValue(undefined),
}))

// Mock de transformers (pass-through con campos requeridos)
vi.mock('@/types/transformers', () => ({
  transformProject: vi.fn((p: Record<string, unknown>) => ({
    id: p.id,
    name: p.name,
    description: p.description ?? '',
    documentFormat: p.document_format ?? 'docx',
    createdAt: new Date(p.created_at as string || '2025-01-01'),
    lastModified: new Date(p.last_modified as string || '2025-01-01'),
    analysisStatus: p.analysis_status ?? 'pending',
    analysisProgress: p.analysis_progress ?? 0,
    wordCount: p.word_count ?? 0,
    chapterCount: p.chapter_count ?? 0,
    entityCount: p.entity_count ?? 0,
    openAlertsCount: p.open_alerts_count ?? 0,
  })),
  transformProjects: vi.fn((list: Record<string, unknown>[]) =>
    list.map((p) => ({
      id: p.id,
      name: p.name,
      description: p.description ?? '',
      documentFormat: p.document_format ?? 'docx',
      createdAt: new Date(p.created_at as string || '2025-01-01'),
      lastModified: new Date(p.last_modified as string || '2025-01-01'),
      analysisStatus: p.analysis_status ?? 'pending',
      analysisProgress: p.analysis_progress ?? 0,
      wordCount: p.word_count ?? 0,
      chapterCount: p.chapter_count ?? 0,
      entityCount: p.entity_count ?? 0,
      openAlertsCount: p.open_alerts_count ?? 0,
    })),
  ),
}))

import { api } from '@/services/apiClient'

const mockApi = api as unknown as {
  get: ReturnType<typeof vi.fn>
  post: ReturnType<typeof vi.fn>
  postForm: ReturnType<typeof vi.fn>
  put: ReturnType<typeof vi.fn>
  del: ReturnType<typeof vi.fn>
}

// ── Helpers ──────────────────────────────────────────────────

function makeApiProject(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    name: 'Test Project',
    description: 'A test project',
    document_format: 'docx',
    created_at: '2025-06-01T10:00:00',
    last_modified: '2025-06-15T14:30:00',
    analysis_status: 'completed',
    analysis_progress: 100,
    word_count: 50000,
    chapter_count: 12,
    entity_count: 35,
    open_alerts_count: 8,
    ...overrides,
  }
}

// ── Tests ────────────────────────────────────────────────────

describe('projectsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // ── Initial state ────────────────────────────────────────

  describe('initial state', () => {
    it('should start with empty projects', () => {
      const store = useProjectsStore()
      expect(store.projects).toEqual([])
      expect(store.currentProject).toBeNull()
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('should have correct computed defaults', () => {
      const store = useProjectsStore()
      expect(store.projectCount).toBe(0)
      expect(store.hasProjects).toBe(false)
      expect(store.recentProjects).toEqual([])
    })
  })

  // ── fetchProjects ────────────────────────────────────────

  describe('fetchProjects', () => {
    it('should fetch and transform projects', async () => {
      const apiProjects = [
        makeApiProject({ id: 1, name: 'Novel A' }),
        makeApiProject({ id: 2, name: 'Novel B' }),
      ]
      mockApi.get.mockResolvedValueOnce(apiProjects)

      const store = useProjectsStore()
      await store.fetchProjects()

      expect(mockApi.get).toHaveBeenCalledWith('/api/projects')
      expect(store.projects).toHaveLength(2)
      expect(store.projects[0].name).toBe('Novel A')
      expect(store.projects[1].name).toBe('Novel B')
      expect(store.projectCount).toBe(2)
      expect(store.hasProjects).toBe(true)
    })

    it('should set loading during fetch', async () => {
      let resolvePromise: (v: unknown[]) => void
      mockApi.get.mockReturnValueOnce(new Promise(r => { resolvePromise = r }))

      const store = useProjectsStore()
      const fetchPromise = store.fetchProjects()

      expect(store.loading).toBe(true)

      resolvePromise!([])
      await fetchPromise

      expect(store.loading).toBe(false)
    })

    it('should handle errors gracefully', async () => {
      mockApi.get.mockRejectedValueOnce(new Error('Network timeout'))

      const store = useProjectsStore()
      await store.fetchProjects()

      expect(store.error).toBe('Network timeout')
      expect(store.projects).toEqual([])
      expect(store.loading).toBe(false)
    })

    it('should handle non-Error thrown values', async () => {
      mockApi.get.mockRejectedValueOnce('unexpected string error')

      const store = useProjectsStore()
      await store.fetchProjects()

      expect(store.error).toBe('No se pudo completar la operación. Recarga la página si persiste.')
    })

    it('should clear previous error on new fetch', async () => {
      mockApi.get.mockRejectedValueOnce(new Error('First error'))

      const store = useProjectsStore()
      await store.fetchProjects()
      expect(store.error).toBe('First error')

      mockApi.get.mockResolvedValueOnce([])
      await store.fetchProjects()
      expect(store.error).toBeNull()
    })
  })

  // ── fetchProject (single) ────────────────────────────────

  describe('fetchProject', () => {
    it('should fetch and set currentProject', async () => {
      const apiProject = makeApiProject({ id: 5, name: 'My Novel' })
      mockApi.get.mockResolvedValueOnce(apiProject)

      const store = useProjectsStore()
      await store.fetchProject(5)

      expect(mockApi.get).toHaveBeenCalledWith('/api/projects/5')
      expect(store.currentProject).not.toBeNull()
      expect(store.currentProject!.id).toBe(5)
      expect(store.currentProject!.name).toBe('My Novel')
    })

    it('should update existing project in list', async () => {
      // Pre-populate with an old version
      const store = useProjectsStore()
      mockApi.get.mockResolvedValueOnce([
        makeApiProject({ id: 5, name: 'Old Name', word_count: 1000 }),
      ])
      await store.fetchProjects()
      expect(store.projects[0].wordCount).toBe(1000)

      // Fetch updated version
      mockApi.get.mockResolvedValueOnce(
        makeApiProject({ id: 5, name: 'New Name', word_count: 5000 }),
      )
      await store.fetchProject(5)

      expect(store.projects[0].name).toBe('New Name')
      expect(store.projects[0].wordCount).toBe(5000)
    })

    it('should not crash if project not in list', async () => {
      const store = useProjectsStore()
      mockApi.get.mockResolvedValueOnce(makeApiProject({ id: 99 }))

      await store.fetchProject(99)

      expect(store.currentProject!.id).toBe(99)
      expect(store.projects).toHaveLength(0) // Not added to list
    })

    it('should set error on failure', async () => {
      mockApi.get.mockRejectedValueOnce(new Error('Not found'))

      const store = useProjectsStore()
      await store.fetchProject(1)

      expect(store.error).toBe('Not found')
      expect(store.currentProject).toBeNull()
    })
  })

  // ── createProject ────────────────────────────────────────

  describe('createProject', () => {
    it('should create project and add to list', async () => {
      const apiProject = makeApiProject({ id: 10, name: 'New Novel' })
      mockApi.postForm.mockResolvedValueOnce(apiProject)

      const store = useProjectsStore()
      const result = await store.createProject('New Novel', 'A description')

      expect(mockApi.postForm).toHaveBeenCalledWith('/api/projects', expect.any(FormData))
      expect(result).not.toBeNull()
      expect(result!.name).toBe('New Novel')
      expect(store.projects).toHaveLength(1)
      expect(store.currentProject!.id).toBe(10)
    })

    it('should include file in FormData when provided', async () => {
      mockApi.postForm.mockResolvedValueOnce(makeApiProject())

      const store = useProjectsStore()
      const file = new File(['content'], 'test.docx', { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' })
      await store.createProject('With File', 'desc', file)

      const formDataArg = mockApi.postForm.mock.calls[0][1] as FormData
      expect(formDataArg.get('name')).toBe('With File')
      expect(formDataArg.get('description')).toBe('desc')
      expect(formDataArg.get('file')).toBe(file)
    })

    it('should not include optional fields when not provided', async () => {
      mockApi.postForm.mockResolvedValueOnce(makeApiProject())

      const store = useProjectsStore()
      await store.createProject('Minimal')

      const formDataArg = mockApi.postForm.mock.calls[0][1] as FormData
      expect(formDataArg.get('name')).toBe('Minimal')
      expect(formDataArg.get('description')).toBeNull()
      expect(formDataArg.get('file')).toBeNull()
    })

    it('should set error and re-throw on failure', async () => {
      mockApi.postForm.mockRejectedValueOnce(new Error('Upload failed'))

      const store = useProjectsStore()

      await expect(store.createProject('Fail')).rejects.toThrow('Upload failed')
      expect(store.error).toBe('Upload failed')
      expect(store.projects).toHaveLength(0)
    })
  })

  // ── updateProjectProgress ────────────────────────────────

  describe('updateProjectProgress', () => {
    it('should update progress for existing project', async () => {
      const store = useProjectsStore()
      mockApi.get.mockResolvedValueOnce([makeApiProject({ id: 1, analysis_progress: 0 })])
      await store.fetchProjects()

      store.updateProjectProgress(1, 75, 'running')

      expect(store.projects[0].analysisProgress).toBe(75)
      expect(store.projects[0].analysisStatus).toBe('running')
    })

    it('should not crash for non-existent project', () => {
      const store = useProjectsStore()
      // Should not throw
      store.updateProjectProgress(999, 50, 'running')
      expect(store.projects).toHaveLength(0)
    })

    it('should preserve other project fields', async () => {
      const store = useProjectsStore()
      mockApi.get.mockResolvedValueOnce([
        makeApiProject({ id: 1, name: 'My Novel', word_count: 50000 }),
      ])
      await store.fetchProjects()

      store.updateProjectProgress(1, 80, 'running')

      expect(store.projects[0].name).toBe('My Novel')
      expect(store.projects[0].wordCount).toBe(50000)
    })
  })

  // ── Computed: recentProjects ─────────────────────────────

  describe('recentProjects', () => {
    it('should return up to 5 most recent projects', async () => {
      const store = useProjectsStore()
      const projects = Array.from({ length: 8 }, (_, i) =>
        makeApiProject({
          id: i + 1,
          name: `Project ${i + 1}`,
          last_modified: `2025-0${Math.min(i + 1, 9)}-01T00:00:00`,
        }),
      )
      mockApi.get.mockResolvedValueOnce(projects)
      await store.fetchProjects()

      expect(store.recentProjects).toHaveLength(5)
      // Most recent first (August > July > ... > April)
      expect(store.recentProjects[0].name).toBe('Project 8')
      expect(store.recentProjects[4].name).toBe('Project 4')
    })

    it('should return all if fewer than 5', async () => {
      const store = useProjectsStore()
      mockApi.get.mockResolvedValueOnce([makeApiProject({ id: 1 }), makeApiProject({ id: 2 })])
      await store.fetchProjects()

      expect(store.recentProjects).toHaveLength(2)
    })
  })

  // ── clearCurrentProject ─────────────────────────────────

  describe('clearCurrentProject', () => {
    it('should set currentProject to null', async () => {
      mockApi.get.mockResolvedValueOnce(makeApiProject({ id: 1 }))
      const store = useProjectsStore()
      await store.fetchProject(1)
      expect(store.currentProject).not.toBeNull()

      store.clearCurrentProject()
      expect(store.currentProject).toBeNull()
    })
  })
})
