import type { ComputedRef, Ref } from 'vue'
import type { Router } from 'vue-router'
import type { SidebarTab } from '@/stores/workspace'
import type { Alert, AlertSource, Chapter, ChatReference, DialogueAttribution, Entity } from '@/types'

export type ProjectDetailInspectorTab = 'summary' | 'chapters' | 'dialogue' | 'contextual'

interface WorkspaceStoreLike {
  activeTab: string
  leftPanel: { expanded: boolean }
  setActiveTab: (tab: any) => void
  setCurrentChapter: (chapterId: number | null) => void
  navigateToTextPosition: (position: number, text?: string, chapterId?: number | null) => void
  clearAlertHighlights: () => void
  highlightAlertSources: (alertId: number, ranges: Array<{
    startChar: number
    endChar: number
    text?: string
    chapterId?: number | null
    color?: string
    label?: string
  }>) => void
  setAlertSeverityFilter: (severity: string) => void
  setAlertCategoryFilter: (category: Alert['category']) => void
  navigateToEntityMentions: (entityId: number) => void
  toggleLeftPanel: () => void
}

interface SelectionStoreLike {
  selectAlert: (alert: Alert) => void
  selectEntity: (entity: Entity) => void
}

interface ProjectDetailNavigationOptions {
  router: Router
  chapters: Ref<Chapter[]>
  entities: Ref<Entity[]>
  rightInspectorTab: Ref<ProjectDetailInspectorTab>
  activeChapterId: Ref<number | null>
  highlightedEntityId: Ref<number | null>
  scrollToChapterId: Ref<number | null>
  initialEntityId: Ref<number | null>
  sidebarTab: Ref<SidebarTab>
  searchQuery: Ref<string>
  currentChapter: ComputedRef<Chapter | null>
  workspaceStore: WorkspaceStoreLike
  selectionStore: SelectionStoreLike
  scrollToDialogue: (attribution: DialogueAttribution) => void
}

function resolveChapterId(chapters: Chapter[], chapterNumber: number | undefined | null): number | null {
  if (chapterNumber === undefined || chapterNumber === null) return null
  return chapters.find((chapter) => chapter.chapterNumber === chapterNumber)?.id ?? null
}

export function useProjectDetailNavigation(options: ProjectDetailNavigationOptions) {
  let chapterVisibleTimeout: ReturnType<typeof setTimeout> | null = null

  const scheduleScrollToChapter = (chapterId: number) => {
    options.scrollToChapterId.value = chapterId
    setTimeout(() => {
      options.scrollToChapterId.value = null
    }, 500)
  }

  const goBack = () => {
    options.router.push({ name: 'projects' })
  }

  const onChapterSelect = (chapterId: number) => {
    options.activeChapterId.value = chapterId
    options.workspaceStore.setActiveTab('text')
    scheduleScrollToChapter(chapterId)
  }

  const onSectionSelect = (chapterId: number, _sectionId: number, startChar: number) => {
    options.activeChapterId.value = chapterId
    options.workspaceStore.navigateToTextPosition(startChar)
  }

  const onChapterVisible = (chapterId: number) => {
    if (chapterVisibleTimeout) {
      clearTimeout(chapterVisibleTimeout)
    }
    chapterVisibleTimeout = setTimeout(() => {
      options.activeChapterId.value = chapterId
      options.workspaceStore.setCurrentChapter(chapterId)
    }, 400)
  }

  const onEntityClick = (entityId: number) => {
    options.highlightedEntityId.value = entityId
    const entity = options.entities.value.find((item) => item.id === entityId)
    if (entity) {
      options.selectionStore.selectEntity(entity)
    }
  }

  const onEntitySelect = (entityOrId: Entity | number) => {
    const entityId = typeof entityOrId === 'number' ? entityOrId : entityOrId.id
    const entity = typeof entityOrId === 'number'
      ? options.entities.value.find((item) => item.id === entityOrId)
      : entityOrId

    options.highlightedEntityId.value = entityId
    if (entity) {
      options.selectionStore.selectEntity(entity)
    }
  }

  const onEntityEdit = (entity: Entity) => {
    options.initialEntityId.value = entity.id
    options.workspaceStore.setActiveTab('entities')
  }

  const onAlertSelect = (alert: Alert) => {
    options.selectionStore.selectAlert(alert)
  }

  const onAlertClickFromText = (alert: Alert) => {
    options.selectionStore.selectAlert(alert)
    options.rightInspectorTab.value = 'contextual'
  }

  const onAlertNavigate = (alert: Alert, source?: AlertSource) => {
    const sources = alert.extraData?.sources
    if (sources && sources.length > 1 && !source) {
      const colors = ['#ef4444', '#3b82f6']
      const ranges = sources.map((entry: AlertSource, idx: number) => ({
        startChar: entry.startChar,
        endChar: entry.endChar,
        text: entry.excerpt,
        chapterId: resolveChapterId(options.chapters.value, entry.chapter),
        color: colors[idx % colors.length],
        label: entry.value,
      }))
      options.workspaceStore.highlightAlertSources(alert.id, ranges)
      return
    }

    const targetChapter = source?.chapter ?? alert.chapter
    const targetPosition = source?.startChar ?? alert.spanStart
    const targetExcerpt = source?.excerpt ?? alert.excerpt

    if (targetPosition !== undefined) {
      options.workspaceStore.clearAlertHighlights()
      options.workspaceStore.navigateToTextPosition(
        targetPosition,
        targetExcerpt || undefined,
        resolveChapterId(options.chapters.value, targetChapter),
      )
      return
    }

    const chapterId = resolveChapterId(options.chapters.value, targetChapter)
    if (chapterId !== null) {
      options.activeChapterId.value = chapterId
      options.workspaceStore.setActiveTab('text')
      scheduleScrollToChapter(chapterId)
    }
  }

  const onAlertNavigateToPosition = (
    alert: Alert | null,
    startChar: number,
    _endChar: number,
    text?: string,
  ) => {
    if (!alert) return
    options.workspaceStore.clearAlertHighlights()
    options.workspaceStore.navigateToTextPosition(
      startChar,
      text,
      resolveChapterId(options.chapters.value, alert.chapter),
    )
  }

  const navigateToAlerts = () => {
    options.workspaceStore.setActiveTab('alerts')
  }

  const handleFilterSeverity = (severity: string) => {
    options.workspaceStore.setAlertSeverityFilter(severity)
    options.workspaceStore.setActiveTab('alerts')
  }

  const handleStatClick = (stat: 'words' | 'chapters' | 'entities' | 'alerts') => {
    switch (stat) {
      case 'entities':
        options.workspaceStore.setActiveTab('entities')
        break
      case 'alerts':
        options.workspaceStore.setActiveTab('alerts')
        break
      case 'chapters':
        options.workspaceStore.setActiveTab('text')
        options.sidebarTab.value = 'chapters'
        break
      default:
        options.workspaceStore.setActiveTab('text')
        break
    }
  }

  const handleViewAlerts = () => {
    options.workspaceStore.setActiveTab('alerts')
  }

  const handleFilterAlerts = (category: Alert['category']) => {
    options.workspaceStore.setAlertCategoryFilter(category)
    options.workspaceStore.setActiveTab('alerts')
  }

  const onAlertClick = (alert: Alert) => {
    options.selectionStore.selectAlert(alert)
    options.workspaceStore.setActiveTab('text')
    options.rightInspectorTab.value = 'contextual'
  }

  const handleGoToMentions = (entity: Entity) => {
    options.workspaceStore.navigateToEntityMentions(entity.id)
    options.highlightedEntityId.value = entity.id
  }

  const onBackToDocumentSummary = () => {
    options.activeChapterId.value = null
    options.workspaceStore.setCurrentChapter(null)
  }

  const onGoToChapterStart = () => {
    if (options.currentChapter.value) {
      scheduleScrollToChapter(options.currentChapter.value.id)
    }
  }

  const onViewChapterAlerts = () => {
    options.sidebarTab.value = 'alerts'
    if (!options.workspaceStore.leftPanel.expanded) {
      options.workspaceStore.toggleLeftPanel()
    }
  }

  const onNavigateToChapter = (chapterNumber: number) => {
    const chapterId = resolveChapterId(options.chapters.value, chapterNumber)
    if (chapterId !== null) {
      options.activeChapterId.value = chapterId
      options.workspaceStore.setActiveTab('text')
      scheduleScrollToChapter(chapterId)
    }
  }

  const onNavigateToEvent = (startChar: number, _endChar: number) => {
    if (!options.currentChapter.value) return
    options.workspaceStore.clearAlertHighlights()
    options.workspaceStore.navigateToTextPosition(startChar, undefined, options.currentChapter.value.id)
  }

  const onInspectorDialogueSelected = (attribution: DialogueAttribution) => {
    options.workspaceStore.setActiveTab('text')
    options.rightInspectorTab.value = 'dialogue'
    options.scrollToDialogue(attribution)
  }

  const onSearchSimilarText = (text: string) => {
    options.searchQuery.value = text
    options.sidebarTab.value = 'search'
  }

  const onSearchResultNavigate = (position: number, text: string, chapterId?: number) => {
    options.workspaceStore.navigateToTextPosition(position, text, chapterId)
  }

  const onAskAiAboutSelection = (_text: string) => {
    options.sidebarTab.value = 'assistant'
  }

  const onChatReferenceNavigate = (ref: ChatReference) => {
    options.workspaceStore.clearAlertHighlights()
    options.workspaceStore.navigateToTextPosition(
      ref.startChar,
      ref.excerpt,
      resolveChapterId(options.chapters.value, ref.chapter),
    )
  }

  const handleNavigateToCharacter = (entityId: number) => {
    options.initialEntityId.value = entityId
    options.workspaceStore.setActiveTab('entities')
  }

  return {
    sidebarTab: options.sidebarTab,
    searchQuery: options.searchQuery,
    goBack,
    onChapterSelect,
    onSectionSelect,
    onChapterVisible,
    onEntityClick,
    onEntitySelect,
    onEntityEdit,
    onAlertSelect,
    onAlertClickFromText,
    onAlertNavigate,
    onAlertNavigateToPosition,
    navigateToAlerts,
    handleFilterSeverity,
    handleStatClick,
    handleViewAlerts,
    handleFilterAlerts,
    onAlertClick,
    handleGoToMentions,
    onBackToDocumentSummary,
    onGoToChapterStart,
    onViewChapterAlerts,
    onNavigateToChapter,
    onNavigateToEvent,
    onInspectorDialogueSelected,
    onSearchSimilarText,
    onSearchResultNavigate,
    onAskAiAboutSelection,
    onChatReferenceNavigate,
    handleNavigateToCharacter,
  }
}
