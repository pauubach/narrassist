import { nextTick, ref } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Chapter } from '@/types'

const { apiGetRawMock, transformChaptersMock } = vi.hoisted(() => ({
  apiGetRawMock: vi.fn(),
  transformChaptersMock: vi.fn(),
}))

vi.mock('@/services/apiClient', () => ({
  api: {
    getRaw: apiGetRawMock,
  },
}))

vi.mock('@/types/transformers/projects', () => ({
  transformChapters: transformChaptersMock,
}))

import { useDocumentViewerData } from './useDocumentViewerData'

describe('useDocumentViewerData', () => {
  const chapters = ref<Chapter[]>([])
  const entities = ref<unknown[]>([])
  const loadedChapters = ref(new Set<number>())
  const visibleChapters = ref(new Set<number>())
  const chapterAccessOrder = ref<number[]>([])
  const chapterAnnotations = ref(new Map<number, { id: number }[]>())
  const chapterDialogues = ref(new Map<number, { id: number }[]>())
  const highlightedContentCache = ref(new Map<number, { content: string }>())
  const chaptersLoadingAnnotations = ref(new Set<number>())
  const loading = ref(false)
  const error = ref<string | null>(null)
  const chapterRefs = new Map<number, Element>()
  const setupIntersectionObserver = vi.fn()

  const externalChapter: Chapter = {
    id: 3,
    projectId: 9,
    chapterNumber: 1,
    title: 'Capitulo 1',
    content: 'Texto',
    positionStart: 0,
    positionEnd: 5,
    wordCount: 1,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    chapters.value = []
    entities.value = []
    loadedChapters.value.clear()
    visibleChapters.value.clear()
    chapterAccessOrder.value = []
    chapterAnnotations.value.clear()
    chapterDialogues.value.clear()
    highlightedContentCache.value.clear()
    chaptersLoadingAnnotations.value.clear()
    loading.value = false
    error.value = null
    chapterRefs.clear()

    transformChaptersMock.mockReturnValue([externalChapter])
    apiGetRawMock.mockResolvedValue({ success: true, data: [] })
  })

  function createComposable(overrides: Partial<Parameters<typeof useDocumentViewerData>[0]> = {}) {
    return useDocumentViewerData({
      projectId: 9,
      externalChapters: undefined,
      chapters,
      entities,
      loadedChapters,
      visibleChapters,
      chapterAccessOrder,
      chapterAnnotations,
      chapterDialogues,
      highlightedContentCache,
      chaptersLoadingAnnotations,
      loading,
      error,
      chapterRefs,
      setupIntersectionObserver,
      ...overrides,
    })
  }

  it('loads external chapters without requesting chapters from the API', async () => {
    apiGetRawMock.mockResolvedValueOnce({ success: true, data: [{ id: 1 }] })

    const state = createComposable({ externalChapters: [externalChapter] })
    await state.loadDocument()
    await nextTick()

    expect(chapters.value).toEqual([externalChapter])
    expect(loadedChapters.value.has(3)).toBe(true)
    expect(apiGetRawMock).toHaveBeenCalledTimes(1)
    expect(apiGetRawMock).toHaveBeenCalledWith('/api/projects/9/entities')
    expect(setupIntersectionObserver).toHaveBeenCalled()
  })

  it('loads chapters and entities from the API when there are no external chapters', async () => {
    apiGetRawMock
      .mockResolvedValueOnce({ success: true, data: [{ id: 1 }] })
      .mockResolvedValueOnce({ success: true, data: [{ id: 8, name: 'Alicia' }] })

    const state = createComposable()
    await state.loadDocument()

    expect(apiGetRawMock).toHaveBeenNthCalledWith(1, '/api/projects/9/chapters')
    expect(apiGetRawMock).toHaveBeenNthCalledWith(2, '/api/projects/9/entities')
    expect(transformChaptersMock).toHaveBeenCalledWith([{ id: 1 }])
    expect(chapters.value).toEqual([externalChapter])
    expect(entities.value).toEqual([{ id: 8, name: 'Alicia' }])
    expect(loading.value).toBe(false)
  })

  it('loads and refreshes visible chapter annotations', async () => {
    chapters.value = [externalChapter]
    loadedChapters.value.add(3)
    highlightedContentCache.value.set(3, { content: 'cached' })
    apiGetRawMock.mockResolvedValue({
      success: true,
      data: { annotations: [{ id: 99 }] },
    })

    const state = createComposable()
    await state.refreshVisibleChapterAnnotations()

    expect(apiGetRawMock).toHaveBeenCalledWith('/api/projects/9/chapters/1/annotations')
    expect(chapterAnnotations.value.get(1)).toEqual([{ id: 99 }])
    expect(highlightedContentCache.value.size).toBe(0)
    expect(chaptersLoadingAnnotations.value.size).toBe(0)
  })
})
