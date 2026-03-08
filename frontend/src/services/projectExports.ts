import { api, type BlobResponse } from '@/services/apiClient'

type QueryValue = string | number | boolean | null | undefined
type QueryParams = Record<string, QueryValue | QueryValue[]>

function buildQuery(params: QueryParams): string {
  const searchParams = new URLSearchParams()

  for (const [key, value] of Object.entries(params)) {
    if (value == null) continue
    if (Array.isArray(value)) {
      if (value.length === 0) continue
      searchParams.set(key, value.map((item) => String(item)).join(','))
      continue
    }
    searchParams.set(key, String(value))
  }

  const query = searchParams.toString()
  return query ? `?${query}` : ''
}

export function exportDocumentBlob(projectId: number, params: QueryParams): Promise<BlobResponse> {
  return api.getBlob(`/api/projects/${projectId}/export/document${buildQuery(params)}`)
}

export function exportCorrectedDocumentBlob(projectId: number, params: QueryParams): Promise<BlobResponse> {
  return api.getBlob(`/api/projects/${projectId}/export/corrected${buildQuery(params)}`)
}

export function exportScrivenerBlob(projectId: number, params: QueryParams): Promise<BlobResponse> {
  return api.getBlob(`/api/projects/${projectId}/export/scrivener${buildQuery(params)}`)
}

export function exportEventsBlob(projectId: number, params: QueryParams): Promise<BlobResponse> {
  return api.getBlob(`/api/projects/${projectId}/events/export${buildQuery(params)}`)
}

export function exportEditorialWorkBlob(projectId: number): Promise<BlobResponse> {
  return api.postBlob(`/api/projects/${projectId}/export-work`)
}
