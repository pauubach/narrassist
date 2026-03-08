import type { Alert, Chapter } from '@/types'

const VALID_PROJECT_TABS = new Set([
  'text',
  'entities',
  'relationships',
  'alerts',
  'timeline',
  'style',
  'glossary',
  'summary',
])

interface QueryParams {
  tab?: string
  entity?: string
  alert?: string
  scrollPos?: string
  scrollChapter?: string
}

interface ProjectLike {
  id: number
  wordCount?: number
  chapterCount?: number
}

interface ProjectDetailBootstrapOptions {
  projectIdParam: string | undefined
  query: QueryParams
  getProject: () => ProjectLike | null | undefined
  getAlerts: () => Alert[]
  getChapters: () => Chapter[]
  setError: (message: string) => void
  setLoading: (loading: boolean) => void
  setInitialEntityId: (entityId: number | null) => void
  projectsStore: {
    error?: string | null
    fetchProject: (projectId: number) => Promise<void>
  }
  analysisStore: {
    setActiveProjectId: (projectId: number) => void
    loadExecutedPhases: (projectId: number) => Promise<unknown>
    checkAnalysisStatus: (projectId: number) => Promise<boolean>
  }
  workspaceStore: {
    activeTab: string
    reset: () => void
    setActiveTab: (tab: any) => void
    navigateToTextPosition: (position: number, text?: string, chapterId?: number | null) => void
  }
  selectionStore: {
    selectAlert: (alert: Alert) => void
  }
  loadChapters: (projectId: number, project?: { wordCount: number; chapterCount: number }, forceReload?: boolean) => Promise<void>
  loadEntities: (projectId: number) => Promise<void>
  loadAlerts: (projectId: number) => Promise<void>
  loadRelationships: (projectId: number) => Promise<void>
  loadChapterSummaries: (projectId: number) => Promise<void>
  startAnalysisPolling: () => void
}

export function parsePositiveInt(value: string | undefined): number | null {
  if (!value) return null
  const parsed = Number.parseInt(value, 10)
  return Number.isNaN(parsed) ? null : parsed
}

function findChapterIdByNumber(chapters: Chapter[], chapterNumber: number | undefined | null): number | null {
  if (chapterNumber === undefined || chapterNumber === null) return null
  return chapters.find((chapter) => chapter.chapterNumber === chapterNumber)?.id ?? null
}

export async function initializeProjectDetail(options: ProjectDetailBootstrapOptions): Promise<number | null> {
  const projectId = parsePositiveInt(options.projectIdParam)
  if (projectId === null) {
    options.setError('ID de proyecto invalido')
    options.setLoading(false)
    return null
  }

  let alertsLoadPromise: Promise<void> | null = null

  const ensureAlertsLoaded = () => {
    if (!alertsLoadPromise) {
      alertsLoadPromise = options.loadAlerts(projectId)
    }
    return alertsLoadPromise
  }

  try {
    options.analysisStore.setActiveProjectId(projectId)
    options.workspaceStore.reset()

    if (options.query.tab && VALID_PROJECT_TABS.has(options.query.tab)) {
      options.workspaceStore.setActiveTab(options.query.tab)
    }

    const entityId = parsePositiveInt(options.query.entity)
    if (entityId !== null) {
      options.setInitialEntityId(entityId)
    }

    const fallbackProject = options.getProject()
    const chapterFallback =
      fallbackProject &&
      typeof fallbackProject.wordCount === 'number' &&
      typeof fallbackProject.chapterCount === 'number'
        ? {
            wordCount: fallbackProject.wordCount,
            chapterCount: fallbackProject.chapterCount,
          }
        : undefined

    await Promise.all([
      options.projectsStore.fetchProject(projectId),
      options.analysisStore.loadExecutedPhases(projectId),
      options.loadChapters(projectId, chapterFallback),
    ])

    options.setLoading(false)

    const activeTab = options.workspaceStore.activeTab
    if (activeTab === 'alerts') {
      await ensureAlertsLoaded()
      void Promise.all([
        options.loadEntities(projectId),
        options.loadRelationships(projectId),
        options.loadChapterSummaries(projectId),
      ])
    } else if (activeTab === 'entities') {
      await options.loadEntities(projectId)
      alertsLoadPromise = options.loadAlerts(projectId)
      void Promise.all([
        alertsLoadPromise,
        options.loadRelationships(projectId),
        options.loadChapterSummaries(projectId),
      ])
    } else if (activeTab === 'relationships') {
      await Promise.all([options.loadEntities(projectId), options.loadRelationships(projectId)])
      alertsLoadPromise = options.loadAlerts(projectId)
      void Promise.all([
        alertsLoadPromise,
        options.loadChapterSummaries(projectId),
      ])
    } else {
      alertsLoadPromise = options.loadAlerts(projectId)
      void Promise.all([
        options.loadEntities(projectId),
        alertsLoadPromise,
        options.loadRelationships(projectId),
        options.loadChapterSummaries(projectId),
      ])
    }

    const alertId = parsePositiveInt(options.query.alert)
    if (alertId !== null) {
      await ensureAlertsLoaded()
      const targetAlert = options.getAlerts().find((alert) => alert.id === alertId)
      if (targetAlert && targetAlert.spanStart !== undefined) {
        const chapterId = findChapterIdByNumber(options.getChapters(), targetAlert.chapter)
        options.workspaceStore.navigateToTextPosition(
          targetAlert.spanStart,
          targetAlert.excerpt || undefined,
          chapterId,
        )
        options.selectionStore.selectAlert(targetAlert)
      }
    }

    const scrollPos = parsePositiveInt(options.query.scrollPos)
    if (scrollPos !== null) {
      const scrollChapter = parsePositiveInt(options.query.scrollChapter)
      const chapterId = findChapterIdByNumber(options.getChapters(), scrollChapter)
      options.workspaceStore.navigateToTextPosition(scrollPos, undefined, chapterId)
    }

    const hasActiveAnalysis = await options.analysisStore.checkAnalysisStatus(projectId)
    if (hasActiveAnalysis) {
      options.startAnalysisPolling()
    }

    options.setLoading(false)
    return projectId
  } catch {
    options.setError(options.projectsStore.error || 'Error cargando proyecto')
    options.setLoading(false)
    return null
  }
}
