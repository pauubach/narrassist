import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiRequest, rawRequest } from './httpTransport'

describe('httpTransport', () => {
  const originalFetch = globalThis.fetch

  afterEach(() => {
    globalThis.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it('rawRequest delegates to fetch without altering the input', async () => {
    const response = new Response(null, { status: 204 })
    const fetchMock = vi.fn().mockResolvedValue(response)
    globalThis.fetch = fetchMock

    const init: RequestInit = { method: 'DELETE' }
    const result = await rawRequest('http://localhost/test', init)

    expect(fetchMock).toHaveBeenCalledWith('http://localhost/test', init)
    expect(result).toBe(response)
  })

  it('apiRequest resolves the API path through apiUrl before delegating', async () => {
    const response = new Response(JSON.stringify({ ok: true }), { status: 200 })
    const fetchMock = vi.fn().mockResolvedValue(response)
    globalThis.fetch = fetchMock

    await apiRequest('/api/health', { method: 'GET' })

    expect(fetchMock).toHaveBeenCalledWith('/api/health', { method: 'GET' })
  })
})
