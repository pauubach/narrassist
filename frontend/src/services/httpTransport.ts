import { apiUrl } from '@/config/api'

export async function rawRequest(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  return fetch(input, init)
}

export async function apiRequest(path: string, init?: RequestInit): Promise<Response> {
  return rawRequest(apiUrl(path), init)
}
