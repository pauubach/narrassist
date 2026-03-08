import { ref, watch } from 'vue'

interface AlertHighlightRangeLike {
  chapterId?: number | null
}

interface DocumentViewerKeyboardNavigationOptions<T extends AlertHighlightRangeLike> {
  getRanges: () => T[] | undefined
  isDialoguePanelOpen: () => boolean
  closeDialoguePanel: () => void
  navigateToHighlight: (index: number) => void
}

export function useDocumentViewerKeyboardNavigation<T extends AlertHighlightRangeLike>(
  options: DocumentViewerKeyboardNavigationOptions<T>,
) {
  const currentHighlightIndex = ref<number>(-1)

  const navigateToNextHighlight = () => {
    const ranges = options.getRanges()
    if (!ranges || ranges.length === 0) return

    const nextIndex = (currentHighlightIndex.value + 1) % ranges.length
    currentHighlightIndex.value = nextIndex
    options.navigateToHighlight(nextIndex)
  }

  const navigateToPrevHighlight = () => {
    const ranges = options.getRanges()
    if (!ranges || ranges.length === 0) return

    const prevIndex = currentHighlightIndex.value <= 0
      ? ranges.length - 1
      : currentHighlightIndex.value - 1
    currentHighlightIndex.value = prevIndex
    options.navigateToHighlight(prevIndex)
  }

  const handleKeyDown = (event: KeyboardEvent) => {
    const target = event.target as HTMLElement
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
      return
    }

    const ranges = options.getRanges()

    switch (event.key) {
      case 'ArrowDown':
        if (ranges && ranges.length > 0) {
          event.preventDefault()
          navigateToNextHighlight()
        }
        break
      case 'ArrowUp':
        if (ranges && ranges.length > 0) {
          event.preventDefault()
          navigateToPrevHighlight()
        }
        break
      case 'Escape':
        if (options.isDialoguePanelOpen()) {
          event.preventDefault()
          options.closeDialoguePanel()
        }
        break
    }
  }

  watch(
    () => options.getRanges(),
    () => {
      currentHighlightIndex.value = -1
    },
    { deep: true },
  )

  return {
    currentHighlightIndex,
    navigateToNextHighlight,
    navigateToPrevHighlight,
    handleKeyDown,
  }
}
