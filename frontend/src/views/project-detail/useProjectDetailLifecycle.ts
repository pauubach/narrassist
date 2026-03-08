import { onMounted, onUnmounted, type Ref, watch } from 'vue'
import type { WorkspaceTab } from '@/stores/workspace'
import type { Alert, Project } from '@/types'

type RightInspectorTab = 'summary' | 'chapters' | 'dialogue' | 'contextual'

interface WorkspaceStoreLike {
  activeTab: WorkspaceTab
  scrollToPosition: number | null
}

interface AnalysisStoreLike {
  loadExecutedPhases: (projectId: number) => Promise<unknown>
  clearTabStale: (projectId: number, tab: WorkspaceTab) => void
}

interface UseProjectDetailLifecycleOptions {
  project: Ref<Pick<Project, 'id' | 'name' | 'wordCount' | 'chapterCount'> | null | undefined>
  workspaceStore: WorkspaceStoreLike
  analysisStore: AnalysisStoreLike
  rightInspectorTab: Ref<RightInspectorTab>
  sidebarTab: Ref<string>
  alerts: Ref<Alert[]>
  isAnalyzing: Ref<boolean>
  loadEntities: (projectId: number, forceReload?: boolean) => Promise<void>
  loadRelationships: (projectId: number, forceReload?: boolean) => Promise<void>
  loadAlerts: (projectId: number, forceReload?: boolean) => Promise<void>
  loadChapters: (
    projectId: number,
    fallbackProject?: Pick<Project, 'wordCount' | 'chapterCount'>,
    forceReload?: boolean,
  ) => Promise<void>
  loadChapterSummaries: (projectId: number, forceReload?: boolean) => Promise<void>
  updateProjectStats: (projectId: number, projectName: string, alerts: Alert[]) => void
  prefetchPanels?: () => void
}

function defaultPrefetchPanels() {
  import('@/components/workspace/AlertsDashboard.vue')
  import('@/components/workspace/EntitiesTab.vue')
  import('@/components/workspace/RelationsTab.vue')
  import('@/components/workspace/StyleTab.vue')
  import('@/components/workspace/GlossaryTab.vue')
  import('@/components/workspace/ResumenTab.vue')
  import('@/components/timeline/TimelineView.vue')
  import('@/components/inspector/AlertInspector.vue')
  import('@/components/inspector/ChapterInspector.vue')
  import('@/components/inspector/TextSelectionInspector.vue')
  import('@/components/sidebar/AssistantPanel.vue')
  import('@/components/sidebar/HistoryPanel.vue')
  import('@/components/sidebar/SemanticSearchPanel.vue')
}

export function useProjectDetailLifecycle(options: UseProjectDetailLifecycleOptions) {
  let statsDebounce: ReturnType<typeof setTimeout> | null = null

  const onAnalysisCompleted = async () => {
    const project = options.project.value
    if (!project) return

    await options.analysisStore.loadExecutedPhases(project.id)

    const activeTab = options.workspaceStore.activeTab
    if (activeTab === 'entities') {
      await options.loadEntities(project.id)
      options.analysisStore.clearTabStale(project.id, 'entities')
    } else if (activeTab === 'relationships') {
      await options.loadEntities(project.id)
      await options.loadRelationships(project.id)
      options.analysisStore.clearTabStale(project.id, 'relationships')
    } else if (activeTab === 'alerts') {
      await options.loadAlerts(project.id)
      options.analysisStore.clearTabStale(project.id, 'alerts')
    }
  }

  const handleSettingsChange = async () => {
    const project = options.project.value
    if (!project) return
    await options.loadAlerts(project.id, true)
  }

  watch(
    () => options.workspaceStore.activeTab,
    async (newTab) => {
      const project = options.project.value
      if (!project) return

      if (newTab !== 'text') {
        options.rightInspectorTab.value = 'summary'
      }

      if (newTab === 'text' && options.workspaceStore.scrollToPosition !== null) {
        await options.loadChapters(project.id, project)
      }

      if (newTab === 'alerts') {
        options.sidebarTab.value = 'alerts'
      }

      if (newTab === 'relationships') {
        await options.loadEntities(project.id)
        await options.loadRelationships(project.id)
        options.analysisStore.clearTabStale(project.id, 'relationships')
      }
    },
  )

  watch(
    () => options.alerts.value.length,
    (newLength, oldLength) => {
      const project = options.project.value
      if (!project || newLength <= 0 || newLength === oldLength) return

      if (statsDebounce) {
        clearTimeout(statsDebounce)
      }
      statsDebounce = setTimeout(() => {
        const latestProject = options.project.value
        if (!latestProject) return
        options.updateProjectStats(latestProject.id, latestProject.name, options.alerts.value)
      }, 500)
    },
  )

  watch(
    () => options.isAnalyzing.value,
    (analyzing, wasAnalyzing) => {
      const project = options.project.value
      if (wasAnalyzing && !analyzing && project) {
        void options.loadChapterSummaries(project.id, true)
      }
    },
  )

  onMounted(() => {
    window.addEventListener('settings-changed', handleSettingsChange)

    const prefetch = options.prefetchPanels ?? defaultPrefetchPanels
    if ('requestIdleCallback' in window) {
      requestIdleCallback(prefetch)
    } else {
      setTimeout(prefetch, 200)
    }
  })

  onUnmounted(() => {
    if (statsDebounce) {
      clearTimeout(statsDebounce)
      statsDebounce = null
    }
    window.removeEventListener('settings-changed', handleSettingsChange)
  })

  return {
    onAnalysisCompleted,
    handleSettingsChange,
  }
}
