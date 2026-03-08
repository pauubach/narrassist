import { computed, ref } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useDocumentViewerExport } from './useDocumentViewerExport'

const { exportDocumentBlobMock, downloadBlobMock, downloadJsonFileMock } = vi.hoisted(() => ({
  exportDocumentBlobMock: vi.fn(),
  downloadBlobMock: vi.fn(),
  downloadJsonFileMock: vi.fn(),
}))

vi.mock('@/services/projectExports', () => ({
  exportDocumentBlob: exportDocumentBlobMock,
}))

vi.mock('@/utils/fileDownload', () => ({
  downloadBlob: downloadBlobMock,
  downloadJsonFile: downloadJsonFileMock,
}))

describe('useDocumentViewerExport', () => {
  const chapters = ref([
    {
      id: 1,
      projectId: 9,
      chapterNumber: 1,
      title: 'Capítulo 1',
      content: 'Contenido',
      positionStart: 0,
      positionEnd: 9,
      wordCount: 1,
    },
  ])
  const entities = ref([{ id: 3, name: 'Alicia' }])
  const totalWords = ref(42)
  const addToast = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    exportDocumentBlobMock.mockResolvedValue({
      blob: new Blob(['binary']),
      filename: 'documento.docx',
      response: new Response(),
    })
  })

  it('exports JSON locally and closes the dialog', async () => {
    const exportState = useDocumentViewerExport({
      projectId: 9,
      documentTitle: computed(() => 'Manuscrito'),
      chapters,
      entities,
      totalWords,
      addToast,
    })

    exportState.showExportDialog.value = true
    exportState.exportFormat.value = 'json'
    await exportState.doExport()

    expect(downloadJsonFileMock).toHaveBeenCalledWith(expect.objectContaining({
      project_id: 9,
      title: 'Manuscrito',
      chapters: expect.any(Array),
      entities: entities.value,
      total_words: 42,
    }), 'Manuscrito_export.json')
    expect(exportDocumentBlobMock).not.toHaveBeenCalled()
    expect(exportState.showExportDialog.value).toBe(false)
    expect(addToast).not.toHaveBeenCalled()
  })

  it('exports binary formats through projectExports', async () => {
    const exportState = useDocumentViewerExport({
      projectId: 9,
      documentTitle: computed(() => 'Manuscrito'),
      chapters,
      entities,
      totalWords,
      addToast,
    })

    exportState.showExportDialog.value = true
    exportState.exportFormat.value = 'pdf'
    await exportState.doExport()

    expect(exportDocumentBlobMock).toHaveBeenCalledWith(9, {
      format: 'pdf',
      include_characters: true,
      include_alerts: true,
      include_timeline: true,
      include_relationships: true,
      include_style_guide: true,
    })
    expect(downloadBlobMock).toHaveBeenCalledWith(expect.any(Blob), 'documento.docx')
    expect(exportState.showExportDialog.value).toBe(false)
  })

  it('reports export errors through toast and keeps loading consistent', async () => {
    exportDocumentBlobMock.mockRejectedValueOnce(new Error('Boom'))

    const exportState = useDocumentViewerExport({
      projectId: 9,
      documentTitle: computed(() => 'Manuscrito'),
      chapters,
      entities,
      totalWords,
      addToast,
    })

    exportState.exportFormat.value = 'docx'
    await exportState.doExport()

    expect(addToast).toHaveBeenCalledWith({
      severity: 'error',
      summary: 'Error',
      detail: 'Error al exportar el documento',
      life: 5000,
    })
    expect(exportState.exportLoading.value).toBe(false)
  })
})
