import { describe, it, expect, vi } from 'vitest'
import { ref } from 'vue'
import { useDocumentViewerKeyboardNavigation } from './useDocumentViewerKeyboardNavigation'

describe('useDocumentViewerKeyboardNavigation', () => {
  it('navega al siguiente y anterior highlight', () => {
    const navigateToHighlight = vi.fn()
    const ranges = ref([{ chapterId: 1 }, { chapterId: 2 }, { chapterId: 3 }])

    const state = useDocumentViewerKeyboardNavigation({
      getRanges: () => ranges.value,
      isDialoguePanelOpen: () => false,
      closeDialoguePanel: vi.fn(),
      navigateToHighlight,
    })

    state.navigateToNextHighlight()
    expect(state.currentHighlightIndex.value).toBe(0)
    expect(navigateToHighlight).toHaveBeenLastCalledWith(0)

    state.navigateToNextHighlight()
    expect(state.currentHighlightIndex.value).toBe(1)
    expect(navigateToHighlight).toHaveBeenLastCalledWith(1)

    state.navigateToPrevHighlight()
    expect(state.currentHighlightIndex.value).toBe(0)
    expect(navigateToHighlight).toHaveBeenLastCalledWith(0)
  })

  it('cierra el panel de diálogos con Escape', () => {
    const closeDialoguePanel = vi.fn()

    const state = useDocumentViewerKeyboardNavigation({
      getRanges: () => [{ chapterId: 1 }],
      isDialoguePanelOpen: () => true,
      closeDialoguePanel,
      navigateToHighlight: vi.fn(),
    })

    const preventDefault = vi.fn()
    state.handleKeyDown({
      key: 'Escape',
      preventDefault,
      target: document.createElement('div'),
    } as unknown as KeyboardEvent)

    expect(preventDefault).toHaveBeenCalled()
    expect(closeDialoguePanel).toHaveBeenCalled()
  })

  it('resetea el índice cuando cambian los highlights', async () => {
    const ranges = ref([{ chapterId: 1 }, { chapterId: 2 }])

    const state = useDocumentViewerKeyboardNavigation({
      getRanges: () => ranges.value,
      isDialoguePanelOpen: () => false,
      closeDialoguePanel: vi.fn(),
      navigateToHighlight: vi.fn(),
    })

    state.navigateToNextHighlight()
    expect(state.currentHighlightIndex.value).toBe(0)

    ranges.value = [{ chapterId: 99 }]
    await Promise.resolve()

    expect(state.currentHighlightIndex.value).toBe(-1)
  })
})
