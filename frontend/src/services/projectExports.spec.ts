import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  exportCorrectedDocumentBlob,
  exportDocumentBlob,
  exportEditorialWorkBlob,
  exportEventsBlob,
  exportScrivenerBlob,
} from './projectExports'

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    getBlob: vi.fn(),
    postBlob: vi.fn(),
  },
}))

vi.mock('@/services/apiClient', () => ({
  api: apiMock,
}))

describe('projectExports', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.getBlob.mockResolvedValue({ blob: new Blob(), response: new Response() })
    apiMock.postBlob.mockResolvedValue({ blob: new Blob(), response: new Response() })
  })

  it('builds document export queries without null or empty array values', async () => {
    await exportDocumentBlob(9, {
      format: 'docx',
      include_characters: true,
      include_alerts: false,
      categories: ['grammar', 'style'],
      ignored: null,
      empty: [],
    })

    expect(apiMock.getBlob).toHaveBeenCalledWith(
      '/api/projects/9/export/document?format=docx&include_characters=true&include_alerts=false&categories=grammar%2Cstyle',
    )
  })

  it('routes corrected, scrivener and events exports to their specific endpoints', async () => {
    await exportCorrectedDocumentBlob(3, { min_confidence: 70, categories: ['grammar'] })
    await exportScrivenerBlob(3, { include_synopsis: true })
    await exportEventsBlob(3, { format: 'csv' })

    expect(apiMock.getBlob).toHaveBeenNthCalledWith(
      1,
      '/api/projects/3/export/corrected?min_confidence=70&categories=grammar',
    )
    expect(apiMock.getBlob).toHaveBeenNthCalledWith(
      2,
      '/api/projects/3/export/scrivener?include_synopsis=true',
    )
    expect(apiMock.getBlob).toHaveBeenNthCalledWith(
      3,
      '/api/projects/3/events/export?format=csv',
    )
  })

  it('routes editorial work export through postBlob', async () => {
    await exportEditorialWorkBlob(12)

    expect(apiMock.postBlob).toHaveBeenCalledWith('/api/projects/12/export-work')
  })
})
