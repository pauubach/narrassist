import { ref } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { apiPostRawMock, apiPostFormMock } = vi.hoisted(() => ({
  apiPostRawMock: vi.fn(),
  apiPostFormMock: vi.fn(),
}))

vi.mock('@/services/apiClient', () => ({
  api: {
    postRaw: apiPostRawMock,
    postForm: apiPostFormMock,
  },
}))

import { useProjectDetailAnalysis } from './useProjectDetailAnalysis'

describe('useProjectDetailAnalysis', () => {
  const project = ref({ id: 7, wordCount: 1200, chapterCount: 8 })
  const showReanalyzeDialog = ref(true)
  const selectedAnalysisMode = ref('auto')
  const entities = ref([{ id: 1 } as any])
  const alerts = ref([{ id: 2 } as any])
  const isAnalyzing = ref(false)
  const replaceDocumentInputRef = ref<{ click: ReturnType<typeof vi.fn> } | null>(null)
  const analysisStore = {
    error: null as string | null,
    runPartialAnalysis: vi.fn(),
    setAnalyzing: vi.fn(),
  }
  const projectsStore = {
    fetchProject: vi.fn(),
  }
  const stopAnalysisPolling = vi.fn()
  const loadEntities = vi.fn()
  const loadAlerts = vi.fn()
  const loadChapters = vi.fn()
  const waitForPendingAnalysisSettingsSync = vi.fn()
  const requestNotificationPermission = vi.fn()
  const setError = vi.fn()
  const addToast = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    selectedAnalysisMode.value = 'auto'
    showReanalyzeDialog.value = true
    entities.value = [{ id: 1 } as any]
    alerts.value = [{ id: 2 } as any]
    isAnalyzing.value = false
    replaceDocumentInputRef.value = { click: vi.fn() } as any
    analysisStore.error = null
    analysisStore.runPartialAnalysis.mockResolvedValue(true)
    apiPostRawMock.mockResolvedValue({ success: true })
    apiPostFormMock.mockResolvedValue({
      project_id: 7,
      classification: 'novela',
      confidence: 0.9,
      recommended_full_run: true,
    })
    waitForPendingAnalysisSettingsSync.mockResolvedValue(true)
  })

  const buildComposable = () => useProjectDetailAnalysis({
    project,
    showReanalyzeDialog,
    selectedAnalysisMode,
    entities,
    alerts,
    isAnalyzing,
    replaceDocumentInputRef: replaceDocumentInputRef as any,
    analysisStore,
    projectsStore,
    stopAnalysisPolling,
    loadEntities,
    loadAlerts,
    loadChapters,
    waitForPendingAnalysisSettingsSync,
    requestNotificationPermission,
    setError,
    addToast,
  })

  it('retries timeline through partial analysis when idle', async () => {
    const analysisState = buildComposable()

    await analysisState.retryTimelinePhase()

    expect(waitForPendingAnalysisSettingsSync).toHaveBeenCalledWith(7)
    expect(analysisStore.runPartialAnalysis).toHaveBeenCalledWith(7, ['timeline'], true)
    expect(addToast).toHaveBeenCalledWith(expect.objectContaining({
      severity: 'info',
      summary: 'Cronología en actualización',
    }))
    expect(analysisState.retryingTimeline.value).toBe(false)
  })

  it('does not retry timeline while a full analysis is running', async () => {
    isAnalyzing.value = true
    const analysisState = buildComposable()

    await analysisState.retryTimelinePhase()

    expect(analysisStore.runPartialAnalysis).not.toHaveBeenCalled()
    expect(addToast).toHaveBeenCalledWith(expect.objectContaining({
      severity: 'info',
      summary: 'Análisis en curso',
    }))
  })

  it('starts reanalysis and marks backend-confirmed analyzing state', async () => {
    const analysisState = buildComposable()

    await analysisState.startReanalysis()

    expect(requestNotificationPermission).toHaveBeenCalled()
    expect(stopAnalysisPolling).toHaveBeenCalled()
    expect(apiPostRawMock).toHaveBeenCalledWith('/api/projects/7/reanalyze')
    expect(analysisStore.setAnalyzing).toHaveBeenCalledWith(7, true)
    expect(projectsStore.fetchProject).toHaveBeenCalledWith(7)
    expect(showReanalyzeDialog.value).toBe(false)
    expect(entities.value).toEqual([])
    expect(alerts.value).toEqual([])
    expect(analysisState.reanalyzing.value).toBe(false)
  })

  it('reloads previous data if reanalysis fails', async () => {
    apiPostRawMock.mockRejectedValueOnce(new Error('boom'))
    const analysisState = buildComposable()

    await analysisState.startReanalysis()

    expect(setError).toHaveBeenCalledWith(
      'No se pudo re-analizar el documento. Si persiste, reinicia la aplicación.',
    )
    expect(loadEntities).toHaveBeenCalledWith(7)
    expect(loadAlerts).toHaveBeenCalledWith(7)
    expect(analysisState.reanalyzing.value).toBe(false)
  })

  it('opens the replace document dialog and handles successful replacement', async () => {
    const analysisState = buildComposable()
    analysisState.openUpdateDocumentDialog()
    expect(replaceDocumentInputRef.value?.click).toHaveBeenCalled()

    const file = new File(['contenido'], 'nuevo.docx')
    const input = {
      files: [file],
      value: 'dummy',
    } as unknown as HTMLInputElement

    await analysisState.onReplaceDocumentSelected({ target: input } as unknown as Event)

    expect(apiPostFormMock).toHaveBeenCalledWith(
      '/api/projects/7/document/replace',
      expect.any(FormData),
      { timeout: 120000 },
    )
    expect(projectsStore.fetchProject).toHaveBeenCalledWith(7)
    expect(loadChapters).toHaveBeenCalledWith(7, { id: 7, wordCount: 1200, chapterCount: 8 })
    expect(addToast).toHaveBeenCalledWith(expect.objectContaining({
      severity: 'success',
      summary: 'Manuscrito actualizado',
    }))
    expect(entities.value).toEqual([])
    expect(alerts.value).toEqual([])
    expect(input.value).toBe('')
  })
})
