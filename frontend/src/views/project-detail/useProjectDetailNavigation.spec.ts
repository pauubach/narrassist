import { computed, ref } from 'vue'
import { describe, expect, it, vi } from 'vitest'
import type { Alert, Chapter, Entity } from '@/types'
import { useProjectDetailNavigation } from './useProjectDetailNavigation'

function createNavigation() {
  const workspaceStore = {
    activeTab: 'text',
    leftPanel: { expanded: false },
    setActiveTab: vi.fn((tab: string) => {
      workspaceStore.activeTab = tab
    }),
    setCurrentChapter: vi.fn(),
    navigateToTextPosition: vi.fn(),
    clearAlertHighlights: vi.fn(),
    highlightAlertSources: vi.fn(),
    setAlertSeverityFilter: vi.fn(),
    setAlertCategoryFilter: vi.fn(),
    navigateToEntityMentions: vi.fn(),
    toggleLeftPanel: vi.fn(() => {
      workspaceStore.leftPanel.expanded = !workspaceStore.leftPanel.expanded
    }),
  }

  const chapters = ref<Chapter[]>([
    { id: 10, projectId: 1, title: 'Capítulo 1', content: '', chapterNumber: 1, wordCount: 100, positionStart: 0, positionEnd: 100 },
    { id: 20, projectId: 1, title: 'Capítulo 2', content: '', chapterNumber: 2, wordCount: 120, positionStart: 101, positionEnd: 220 },
  ])
  const entities = ref<Entity[]>([
    {
      id: 7,
      projectId: 1,
      name: 'Ana',
      type: 'character',
      mentionCount: 2,
      importance: 'secondary',
      aliases: [],
      isActive: true,
      mergedFromIds: [],
    },
  ])
  const state = {
    rightInspectorTab: ref<'summary' | 'chapters' | 'dialogue' | 'contextual'>('summary'),
    activeChapterId: ref<number | null>(null),
    highlightedEntityId: ref<number | null>(null),
    scrollToChapterId: ref<number | null>(null),
    initialEntityId: ref<number | null>(null),
    sidebarTab: ref<'chapters' | 'alerts' | 'characters' | 'search' | 'assistant' | 'history'>('chapters'),
    searchQuery: ref(''),
  }

  const selectionStore = {
    selectAlert: vi.fn(),
    selectEntity: vi.fn(),
  }

  const navigation = useProjectDetailNavigation({
    router: { push: vi.fn() } as any,
    chapters,
    entities,
    rightInspectorTab: state.rightInspectorTab,
    activeChapterId: state.activeChapterId,
    highlightedEntityId: state.highlightedEntityId,
    scrollToChapterId: state.scrollToChapterId,
    initialEntityId: state.initialEntityId,
    sidebarTab: state.sidebarTab,
    searchQuery: state.searchQuery,
    currentChapter: computed(() => chapters.value[1]),
    workspaceStore,
    selectionStore,
    scrollToDialogue: vi.fn(),
  })

  return { navigation, workspaceStore, selectionStore, state }
}

describe('useProjectDetailNavigation', () => {
  it('resalta todas las fuentes de una alerta multi-source', () => {
    const { navigation, workspaceStore } = createNavigation()

    const alert = {
      id: 99,
      category: 'consistency',
      chapter: 2,
      extraData: {
        sources: [
          { chapter: 1, startChar: 10, endChar: 20, excerpt: 'uno', value: 'A' },
          { chapter: 2, startChar: 40, endChar: 60, excerpt: 'dos', value: 'B' },
        ],
      },
    } as unknown as Alert

    navigation.onAlertNavigate(alert)

    expect(workspaceStore.highlightAlertSources).toHaveBeenCalledWith(99, [
      expect.objectContaining({ chapterId: 10, startChar: 10, endChar: 20, label: 'A' }),
      expect.objectContaining({ chapterId: 20, startChar: 40, endChar: 60, label: 'B' }),
    ])
  })

  it('navega a una alerta simple usando chapterId resuelto', () => {
    const { navigation, workspaceStore } = createNavigation()

    const alert = {
      id: 12,
      chapter: 2,
      spanStart: 130,
      excerpt: 'fragmento',
    } as unknown as Alert

    navigation.onAlertNavigate(alert)

    expect(workspaceStore.clearAlertHighlights).toHaveBeenCalled()
    expect(workspaceStore.navigateToTextPosition).toHaveBeenCalledWith(130, 'fragmento', 20)
  })

  it('cambia a búsqueda lateral al buscar texto similar', () => {
    const { navigation, state } = createNavigation()

    navigation.onSearchSimilarText('voz narrativa')

    expect(state.searchQuery.value).toBe('voz narrativa')
    expect(state.sidebarTab.value).toBe('search')
  })

  it('abre alertas del capítulo expandiendo panel lateral si hace falta', () => {
    const { navigation, workspaceStore, state } = createNavigation()

    navigation.onViewChapterAlerts()

    expect(state.sidebarTab.value).toBe('alerts')
    expect(workspaceStore.toggleLeftPanel).toHaveBeenCalled()
  })
})
