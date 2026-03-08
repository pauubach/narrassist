import { nextTick, type Ref } from 'vue'
import type { Chapter } from '@/types'
import type { ApiChapter } from '@/types/api/projects'
import { transformChapters } from '@/types/transformers/projects'
import { api } from '@/services/apiClient'

interface UseDocumentViewerDataOptions<TAnnotation, TDialogue, THighlightedCache> {
  projectId: number
  externalChapters?: Chapter[]
  chapters: Ref<Chapter[]>
  entities: Ref<unknown[]>
  loadedChapters: Ref<Set<number>>
  visibleChapters: Ref<Set<number>>
  chapterAccessOrder: Ref<number[]>
  chapterAnnotations: Ref<Map<number, TAnnotation[]>>
  chapterDialogues: Ref<Map<number, TDialogue[]>>
  highlightedContentCache: Ref<Map<number, THighlightedCache>>
  chaptersLoadingAnnotations: Ref<Set<number>>
  loading: Ref<boolean>
  error: Ref<string | null>
  chapterRefs: Map<number, Element>
  setupIntersectionObserver: () => void
}

export function useDocumentViewerData<TAnnotation, TDialogue, THighlightedCache>(
  options: UseDocumentViewerDataOptions<TAnnotation, TDialogue, THighlightedCache>,
) {
  const resetDocumentState = () => {
    options.loadedChapters.value.clear()
    options.visibleChapters.value.clear()
    options.chapterAccessOrder.value = []
    options.chapterAnnotations.value.clear()
    options.chapterDialogues.value.clear()
    options.highlightedContentCache.value.clear()
    options.chapterRefs.clear()
  }

  const loadDocument = async () => {
    options.loading.value = true
    options.error.value = null
    resetDocumentState()

    try {
      if (options.externalChapters && options.externalChapters.length > 0) {
        options.chapters.value = options.externalChapters
      } else {
        const chaptersData = await api.getRaw<{ success: boolean; data?: ApiChapter[] }>(
          `/api/projects/${options.projectId}/chapters`,
        )

        if (!chaptersData.success) {
          throw new Error('Error cargando capitulos')
        }

        options.chapters.value = transformChapters(chaptersData.data || [])
      }

      if (options.chapters.value.length > 0) {
        options.loadedChapters.value.add(options.chapters.value[0].id)
      }

      const entitiesData = await api.getRaw<{ success: boolean; data?: unknown[] }>(
        `/api/projects/${options.projectId}/entities`,
      )

      if (entitiesData.success) {
        options.entities.value = entitiesData.data || []
      }

      nextTick(() => {
        options.setupIntersectionObserver()
      })
    } catch (err) {
      options.error.value = err instanceof Error ? err.message : 'Error cargando documento'
    } finally {
      options.loading.value = false
    }
  }

  const loadChapterAnnotations = async (chapterNumber: number, forceReload = false) => {
    if (!forceReload && options.chapterAnnotations.value.has(chapterNumber)) return

    options.chaptersLoadingAnnotations.value.add(chapterNumber)
    try {
      const data = await api.getRaw<{ success: boolean; data?: { annotations?: TAnnotation[] } }>(
        `/api/projects/${options.projectId}/chapters/${chapterNumber}/annotations`,
      )

      if (data.success && data.data?.annotations) {
        options.chapterAnnotations.value.set(chapterNumber, data.data.annotations)
      }
    } finally {
      options.chaptersLoadingAnnotations.value.delete(chapterNumber)
    }
  }

  const refreshVisibleChapterAnnotations = async () => {
    const chapterNumbers = options.chapters.value
      .filter((chapter) => options.loadedChapters.value.has(chapter.id))
      .map((chapter) => chapter.chapterNumber)

    if (chapterNumbers.length === 0) return

    options.highlightedContentCache.value.clear()
    await Promise.all(chapterNumbers.map((chapterNumber) => loadChapterAnnotations(chapterNumber, true)))
  }

  return {
    loadDocument,
    loadChapterAnnotations,
    refreshVisibleChapterAnnotations,
  }
}
