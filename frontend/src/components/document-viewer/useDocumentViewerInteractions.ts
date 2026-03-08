import type { Ref } from 'vue'
import type { Chapter } from '@/types'

interface TextSelectionPayload {
  start: number
  end: number
  text: string
  chapter: string
  chapterNumber: number
}

interface SelectionStoreLike {
  setTextSelection: (selection: TextSelectionPayload | null) => void
}

interface UseDocumentViewerInteractionsOptions {
  viewerContainer: Ref<HTMLElement | null>
  chapters: Ref<Chapter[]>
  selectionStore: SelectionStoreLike
  emitEntityClick: (entityId: number) => void
  emitAnnotationClick: (annotationId: number) => void
}

export function useDocumentViewerInteractions(options: UseDocumentViewerInteractionsOptions) {
  const handleMouseUp = () => {
    const selection = window.getSelection()
    if (!selection || selection.isCollapsed) {
      options.selectionStore.setTextSelection(null)
      return
    }

    const selectedText = selection.toString().trim()
    if (!selectedText) {
      options.selectionStore.setTextSelection(null)
      return
    }

    const range = selection.getRangeAt(0)
    const container = range.commonAncestorContainer

    let chapterElement: HTMLElement | null = null
    let node: Node | null = container
    while (node && node !== options.viewerContainer.value) {
      if (node instanceof HTMLElement && node.classList.contains('chapter-section')) {
        chapterElement = node
        break
      }
      node = node.parentNode
    }

    if (!chapterElement) {
      options.selectionStore.setTextSelection(null)
      return
    }

    const chapterId = parseInt(chapterElement.dataset.chapterId || '0', 10)
    const chapter = options.chapters.value.find((item) => item.id === chapterId)
    if (!chapter) {
      options.selectionStore.setTextSelection(null)
      return
    }

    const chapterTextElement = chapterElement.querySelector('.chapter-text')
    if (!chapterTextElement) {
      options.selectionStore.setTextSelection(null)
      return
    }

    const rangeToStart = document.createRange()
    rangeToStart.setStart(chapterTextElement, 0)
    rangeToStart.setEnd(range.startContainer, range.startOffset)

    const textBeforeSelection = rangeToStart.toString()
    const offsetInChapter = textBeforeSelection.length
    const globalStart = (chapter.positionStart ?? 0) + offsetInChapter
    const globalEnd = globalStart + selectedText.length

    options.selectionStore.setTextSelection({
      start: globalStart,
      end: globalEnd,
      text: selectedText,
      chapter: chapter.title,
      chapterNumber: chapter.chapterNumber,
    })
  }

  const handleDocumentClick = (event: MouseEvent) => {
    const target = event.target as HTMLElement

    if (target.classList.contains('entity-highlight')) {
      const entityId = target.dataset.entityId
      if (entityId) {
        options.emitEntityClick(parseInt(entityId, 10))
      }
      return
    }

    if (target.classList.contains('annotation')) {
      const annotationId = target.dataset.annotationId
      if (annotationId) {
        options.emitAnnotationClick(parseInt(annotationId, 10))
      }
    }
  }

  return {
    handleMouseUp,
    handleDocumentClick,
  }
}
