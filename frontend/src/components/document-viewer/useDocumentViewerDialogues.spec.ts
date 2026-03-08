import { ref } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { apiGetRawMock } = vi.hoisted(() => ({
  apiGetRawMock: vi.fn(),
}))

vi.mock('@/services/apiClient', () => ({
  api: {
    getRaw: apiGetRawMock,
  },
}))

import { useDocumentViewerDialogues } from './useDocumentViewerDialogues'

describe('useDocumentViewerDialogues', () => {
  const chapterDialogues = ref(new Map<number, { text: string; chapterNumber: number }[]>())
  const chaptersLoadingDialogues = ref(new Set<number>())

  beforeEach(() => {
    vi.clearAllMocks()
    chapterDialogues.value.clear()
    chaptersLoadingDialogues.value.clear()
  })

  it('loads and maps dialogue attributions for a chapter', async () => {
    apiGetRawMock.mockResolvedValueOnce({
      success: true,
      data: {
        attributions: [
          {
            text: 'Hola',
            speaker_name: 'Alicia',
            speaker_id: 9,
            confidence: 'high',
            method: 'rules',
            start_char: 10,
            end_char: 20,
          },
        ],
      },
    })

    const state = useDocumentViewerDialogues({
      projectId: 7,
      chapterDialogues,
      chaptersLoadingDialogues,
      mapDialogue: (dialogue, chapterNumber) => ({
        text: `${dialogue.text}:${dialogue.speaker_name}`,
        chapterNumber,
      }),
    })

    await state.loadChapterDialogues(3)

    expect(apiGetRawMock).toHaveBeenCalledWith('/api/projects/7/chapters/3/dialogue-attributions')
    expect(chapterDialogues.value.get(3)).toEqual([{ text: 'Hola:Alicia', chapterNumber: 3 }])
    expect(chaptersLoadingDialogues.value.size).toBe(0)
  })

  it('does not refetch dialogues already cached', async () => {
    chapterDialogues.value.set(2, [{ text: 'cached', chapterNumber: 2 }])

    const state = useDocumentViewerDialogues({
      projectId: 7,
      chapterDialogues,
      chaptersLoadingDialogues,
      mapDialogue: (dialogue, chapterNumber) => ({
        text: dialogue.text,
        chapterNumber,
      }),
    })

    await state.loadChapterDialogues(2)

    expect(apiGetRawMock).not.toHaveBeenCalled()
  })
})
