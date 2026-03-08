import { ref, type Ref } from 'vue'
import { api } from '@/services/apiClient'
import { exportCorrectedDocumentBlob } from '@/services/projectExports'
import { downloadBlob, downloadTextFile } from '@/utils/fileDownload'

type ToastAdd = (message: {
  severity: 'error'
  summary: string
  detail?: string
  life: number
}) => void

interface ProjectExportTarget {
  id: number
  name: string
}

interface UseProjectDetailExportsOptions {
  project: Ref<ProjectExportTarget | null | undefined>
  setError: (message: string) => void
  addToast: ToastAdd
}

export function useProjectDetailExports(options: UseProjectDetailExportsOptions) {
  const showExportDialog = ref(false)
  const exportingStyleGuide = ref(false)

  const openExportDialog = () => {
    showExportDialog.value = true
  }

  const handleExportCorrected = async () => {
    const project = options.project.value
    if (!project) return

    try {
      const { blob, filename } = await exportCorrectedDocumentBlob(project.id, {
        min_confidence: 0.5,
        as_track_changes: true,
      })
      downloadBlob(blob, filename || 'documento_corregido.docx')
    } catch (err) {
      options.addToast({
        severity: 'error',
        summary: 'No se pudo exportar',
        detail: err instanceof Error ? err.message : 'Error al exportar documento corregido',
        life: 5000,
      })
    }
  }

  const quickExportStyleGuide = async () => {
    const project = options.project.value
    if (!project) return

    exportingStyleGuide.value = true

    try {
      const data = await api.getRaw<{ success: boolean; data?: { content: string }; error?: string }>(
        `/api/projects/${project.id}/style-guide?format=markdown`,
      )

      if (data.success && data.data?.content) {
        const filename = `guia_estilo_${project.name}_${Date.now()}.md`
        downloadTextFile(data.data.content, filename, 'text/markdown')
      } else {
        throw new Error(data.error || 'No se pudo completar la operación. Si persiste, reinicia la aplicación.')
      }
    } catch (err) {
      options.setError('No se pudo exportar la guía de estilo')
    } finally {
      exportingStyleGuide.value = false
    }
  }

  return {
    showExportDialog,
    exportingStyleGuide,
    openExportDialog,
    handleExportCorrected,
    quickExportStyleGuide,
  }
}
