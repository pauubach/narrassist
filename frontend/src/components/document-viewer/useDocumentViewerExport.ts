import { ref, type Ref } from 'vue'
import type { Chapter } from '@/types'
import { exportDocumentBlob } from '@/services/projectExports'
import { downloadBlob, downloadJsonFile } from '@/utils/fileDownload'

type ToastAdd = (message: {
  severity: 'success' | 'error'
  summary: string
  detail: string
  life: number
}) => void

interface UseDocumentViewerExportOptions {
  projectId: number
  documentTitle: Ref<string | undefined>
  chapters: Ref<Chapter[]>
  entities: Ref<unknown[]>
  totalWords: Ref<number>
  addToast: ToastAdd
}

export function useDocumentViewerExport(options: UseDocumentViewerExportOptions) {
  const showExportDialog = ref(false)
  const exportFormat = ref<'docx' | 'pdf' | 'json'>('docx')
  const exportLoading = ref(false)

  const exportDocument = () => {
    showExportDialog.value = true
  }

  const doExport = async () => {
    exportLoading.value = true
    try {
      if (exportFormat.value === 'json') {
        const exportData = {
          project_id: options.projectId,
          title: options.documentTitle.value || 'Documento',
          exported_at: new Date().toISOString(),
          chapters: options.chapters.value.map(chapter => ({
            id: chapter.id,
            title: chapter.title,
            chapter_number: chapter.chapterNumber,
            word_count: chapter.wordCount,
            content: chapter.content,
          })),
          entities: options.entities.value,
          total_words: options.totalWords.value,
        }

        downloadJsonFile(exportData, `${options.documentTitle.value || 'documento'}_export.json`)
      } else {
        const { blob, filename } = await exportDocumentBlob(options.projectId, {
          format: exportFormat.value,
          include_characters: true,
          include_alerts: true,
          include_timeline: true,
          include_relationships: true,
          include_style_guide: true,
        })

        const ext = exportFormat.value === 'pdf' ? 'pdf' : 'docx'
        downloadBlob(blob, filename || `${options.documentTitle.value || 'documento'}_informe.${ext}`)
      }

      showExportDialog.value = false
    } catch (err) {
      options.addToast({
        severity: 'error',
        summary: 'Error',
        detail: 'Error al exportar el documento',
        life: 5000,
      })
    } finally {
      exportLoading.value = false
    }
  }

  return {
    showExportDialog,
    exportFormat,
    exportLoading,
    exportDocument,
    doExport,
  }
}
