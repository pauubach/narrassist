import { ref } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const {
  apiGetRawMock,
  exportCorrectedDocumentBlobMock,
  downloadBlobMock,
  downloadTextFileMock,
} = vi.hoisted(() => ({
  apiGetRawMock: vi.fn(),
  exportCorrectedDocumentBlobMock: vi.fn(),
  downloadBlobMock: vi.fn(),
  downloadTextFileMock: vi.fn(),
}))

vi.mock('@/services/apiClient', () => ({
  api: {
    getRaw: apiGetRawMock,
  },
}))

vi.mock('@/services/projectExports', () => ({
  exportCorrectedDocumentBlob: exportCorrectedDocumentBlobMock,
}))

vi.mock('@/utils/fileDownload', () => ({
  downloadBlob: downloadBlobMock,
  downloadTextFile: downloadTextFileMock,
}))

import { useProjectDetailExports } from './useProjectDetailExports'

describe('useProjectDetailExports', () => {
  const project = ref({ id: 7, name: 'Novela' })
  const setError = vi.fn()
  const addToast = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    exportCorrectedDocumentBlobMock.mockResolvedValue({
      blob: new Blob(['docx']),
      filename: 'corregido.docx',
      response: new Response(),
    })
    apiGetRawMock.mockResolvedValue({
      success: true,
      data: { content: '# Guía' },
    })
  })

  it('opens the export dialog explicitly', () => {
    const exportsState = useProjectDetailExports({ project, setError, addToast })

    expect(exportsState.showExportDialog.value).toBe(false)
    exportsState.openExportDialog()
    expect(exportsState.showExportDialog.value).toBe(true)
  })

  it('exports corrected document through projectExports', async () => {
    const exportsState = useProjectDetailExports({ project, setError, addToast })

    await exportsState.handleExportCorrected()

    expect(exportCorrectedDocumentBlobMock).toHaveBeenCalledWith(7, {
      min_confidence: 0.5,
      as_track_changes: true,
    })
    expect(downloadBlobMock).toHaveBeenCalledWith(expect.any(Blob), 'corregido.docx')
    expect(addToast).not.toHaveBeenCalled()
  })

  it('shows a toast if corrected document export fails', async () => {
    exportCorrectedDocumentBlobMock.mockRejectedValueOnce(new Error('boom'))

    const exportsState = useProjectDetailExports({ project, setError, addToast })
    await exportsState.handleExportCorrected()

    expect(addToast).toHaveBeenCalledWith({
      severity: 'error',
      summary: 'No se pudo exportar',
      detail: 'boom',
      life: 5000,
    })
  })

  it('exports the style guide as markdown and resets loading', async () => {
    const exportsState = useProjectDetailExports({ project, setError, addToast })

    await exportsState.quickExportStyleGuide()

    expect(apiGetRawMock).toHaveBeenCalledWith('/api/projects/7/style-guide?format=markdown')
    expect(downloadTextFileMock).toHaveBeenCalledWith('# Guía', expect.stringMatching(/^guia_estilo_Novela_\d+\.md$/), 'text/markdown')
    expect(exportsState.exportingStyleGuide.value).toBe(false)
    expect(setError).not.toHaveBeenCalled()
  })

  it('reports style guide export failures through setError', async () => {
    apiGetRawMock.mockResolvedValueOnce({ success: false, error: 'sin datos' })

    const exportsState = useProjectDetailExports({ project, setError, addToast })
    await exportsState.quickExportStyleGuide()

    expect(setError).toHaveBeenCalledWith('No se pudo exportar la gu\u00eda de estilo')
    expect(exportsState.exportingStyleGuide.value).toBe(false)
  })
})
