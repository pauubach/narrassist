import type { Ref } from 'vue'
import { api } from '@/services/apiClient'

interface DialogueAttributionApi {
  text: string
  speaker_name?: string | null
  speaker_id?: number | null
  confidence?: string | null
  method?: string | null
  start_char: number
  end_char: number
}

interface UseDocumentViewerDialoguesOptions<TDialogue> {
  projectId: number
  chapterDialogues: Ref<Map<number, TDialogue[]>>
  chaptersLoadingDialogues: Ref<Set<number>>
  mapDialogue: (dialogue: DialogueAttributionApi, chapterNumber: number) => TDialogue
}

export function useDocumentViewerDialogues<TDialogue>(options: UseDocumentViewerDialoguesOptions<TDialogue>) {
  const loadChapterDialogues = async (chapterNumber: number) => {
    if (options.chapterDialogues.value.has(chapterNumber)) return

    options.chaptersLoadingDialogues.value.add(chapterNumber)
    try {
      const data = await api.getRaw<{ success: boolean; data?: { attributions?: DialogueAttributionApi[] } }>(
        `/api/projects/${options.projectId}/chapters/${chapterNumber}/dialogue-attributions`,
      )

      if (data.success && data.data?.attributions) {
        const transformed = data.data.attributions.map((dialogue) =>
          options.mapDialogue(dialogue, chapterNumber),
        )
        options.chapterDialogues.value.set(chapterNumber, transformed)
      }
    } finally {
      options.chaptersLoadingDialogues.value.delete(chapterNumber)
    }
  }

  return {
    loadChapterDialogues,
  }
}
