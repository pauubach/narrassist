import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Alert, Chapter } from '@/types'
import { initializeProjectDetail } from './projectDetailBootstrap'

function makeChapter(overrides: Partial<Chapter> = {}): Chapter {
  return {
    id: 1,
    projectId: 7,
    chapterNumber: 1,
    title: 'Capitulo 1',
    content: 'Texto',
    positionStart: 0,
    positionEnd: 10,
    wordCount: 1,
    ...overrides,
  }
}

function makeAlert(overrides: Partial<Alert> = {}): Alert {
  return {
    id: 11,
    projectId: 7,
    category: 'attribute',
    severity: 'medium',
    status: 'active',
    alertType: 'pov_shift',
    title: 'Alerta',
    description: 'Descripcion',
    chapter: 1,
    spanStart: 42,
    excerpt: 'Fragmento',
    entityIds: [],
    confidence: 0.9,
    createdAt: new Date(),
    ...overrides,
  }
}

describe('initializeProjectDetail', () => {
  let alerts: Alert[]
  let chapters: Chapter[]
  let project: { id: number } | null
  let activeTab: string

  const setError = vi.fn()
  const setLoading = vi.fn()
  const setInitialEntityId = vi.fn()
  const fetchProject = vi.fn(async () => {
    project = { id: 7 }
  })
  const loadExecutedPhases = vi.fn().mockResolvedValue(undefined)
  const checkAnalysisStatus = vi.fn().mockResolvedValue(false)
  const reset = vi.fn(() => {
    activeTab = 'text'
  })
  const setActiveTab = vi.fn((tab: string) => {
    activeTab = tab
  })
  const navigateToTextPosition = vi.fn()
  const selectAlert = vi.fn()
  const loadChapters = vi.fn(async () => {
    chapters = [makeChapter()]
  })
  const loadEntities = vi.fn().mockResolvedValue(undefined)
  const loadAlerts = vi.fn(async () => {
    alerts = [makeAlert()]
  })
  const loadRelationships = vi.fn().mockResolvedValue(undefined)
  const loadChapterSummaries = vi.fn().mockResolvedValue(undefined)
  const startAnalysisPolling = vi.fn()
  const setActiveProjectId = vi.fn()

  beforeEach(() => {
    alerts = []
    chapters = []
    project = null
    activeTab = 'text'
    vi.clearAllMocks()
    fetchProject.mockImplementation(async () => {
      project = { id: 7 }
    })
    loadChapters.mockImplementation(async () => {
      chapters = [makeChapter()]
    })
    loadAlerts.mockImplementation(async () => {
      alerts = [makeAlert()]
    })
    checkAnalysisStatus.mockResolvedValue(false)
  })

  function createOptions(overrides: Partial<Parameters<typeof initializeProjectDetail>[0]> = {}) {
    return {
      projectIdParam: '7',
      query: {},
      getProject: () => project,
      getAlerts: () => alerts,
      getChapters: () => chapters,
      setError,
      setLoading,
      setInitialEntityId,
      projectsStore: {
        error: null,
        fetchProject,
      },
      analysisStore: {
        setActiveProjectId,
        loadExecutedPhases,
        checkAnalysisStatus,
      },
      workspaceStore: {
        get activeTab() {
          return activeTab
        },
        reset,
        setActiveTab,
        navigateToTextPosition,
      },
      selectionStore: {
        selectAlert,
      },
      loadChapters,
      loadEntities,
      loadAlerts,
      loadRelationships,
      loadChapterSummaries,
      startAnalysisPolling,
      ...overrides,
    }
  }

  it('rejects invalid project ids early', async () => {
    const result = await initializeProjectDetail(createOptions({ projectIdParam: 'abc' }))

    expect(result).toBeNull()
    expect(setError).toHaveBeenCalledWith('ID de proyecto invalido')
    expect(setLoading).toHaveBeenCalledWith(false)
    expect(fetchProject).not.toHaveBeenCalled()
  })

  it('ensures alert route navigation waits for alerts even outside alerts tab', async () => {
    const result = await initializeProjectDetail(createOptions({
      query: {
        tab: 'summary',
        alert: '11',
      },
    }))

    expect(result).toBe(7)
    expect(setActiveTab).toHaveBeenCalledWith('summary')
    expect(loadAlerts).toHaveBeenCalled()
    expect(navigateToTextPosition).toHaveBeenCalledWith(42, 'Fragmento', 1)
    expect(selectAlert).toHaveBeenCalledWith(expect.objectContaining({ id: 11 }))
  })

  it('starts polling when the backend reports an active analysis', async () => {
    checkAnalysisStatus.mockResolvedValueOnce(true)

    const result = await initializeProjectDetail(createOptions())

    expect(result).toBe(7)
    expect(startAnalysisPolling).toHaveBeenCalled()
    expect(setActiveProjectId).toHaveBeenCalledWith(7)
  })
})
