/**
 * API Client - Narrative Assistant
 *
 * Cliente HTTP centralizado para comunicación con el backend.
 * Reemplaza las llamadas raw fetch() en los stores.
 */

import { apiUrl } from '@/config/api'
import type { ApiResponse } from '@/types/api'

/** Error específico de la API con detalles del backend */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly detail?: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/** Opciones para peticiones */
interface RequestOptions {
  /** Timeout en ms (default: 30000) */
  timeout?: number
  /** Headers adicionales */
  headers?: Record<string, string>
  /** Signal para cancelación */
  signal?: AbortSignal
}

/**
 * Parsea la respuesta HTTP y extrae los datos.
 * Lanza ApiError si la respuesta no es exitosa.
 */
async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail: string | undefined
    try {
      const errorData = await response.json()
      detail = errorData.detail || errorData.error || undefined
    } catch {
      // No se pudo parsear el body de error
    }
    throw new ApiError(
      detail || `HTTP ${response.status}: ${response.statusText}`,
      response.status,
      detail,
    )
  }

  const data: ApiResponse<T> = await response.json()

  if (!data.success) {
    throw new ApiError(
      data.error || 'Error desconocido del servidor',
      response.status,
      data.error,
    )
  }

  return data.data as T
}

/**
 * Parsea respuesta sin verificar data.success (para endpoints que devuelven
 * directamente sin el wrapper ApiResponse, como /api/health).
 */
async function parseRawResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new ApiError(
      `HTTP ${response.status}: ${response.statusText}`,
      response.status,
    )
  }
  return await response.json()
}

/**
 * Crea un AbortSignal con timeout.
 */
function createTimeoutSignal(timeoutMs: number, existingSignal?: AbortSignal): AbortSignal {
  const controller = new AbortController()

  const timer = setTimeout(() => controller.abort(), timeoutMs)

  // Si hay un signal existente, abortar cuando este se aborte
  if (existingSignal) {
    existingSignal.addEventListener('abort', () => {
      clearTimeout(timer)
      controller.abort()
    })
  }

  // Limpiar timer si se aborta antes del timeout
  controller.signal.addEventListener('abort', () => clearTimeout(timer))

  return controller.signal
}

/**
 * GET request que devuelve datos tipados.
 *
 * @example
 * const projects = await api.get<ApiProject[]>('/api/projects')
 */
async function get<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { timeout = 30000, headers = {}, signal } = options
  const abortSignal = createTimeoutSignal(timeout, signal)

  const response = await fetch(apiUrl(path), {
    method: 'GET',
    headers,
    signal: abortSignal,
  })

  return parseResponse<T>(response)
}

/**
 * GET request sin wrapper ApiResponse (para health checks, etc).
 */
async function getRaw<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { timeout = 30000, headers = {}, signal } = options
  const abortSignal = createTimeoutSignal(timeout, signal)

  const response = await fetch(apiUrl(path), {
    method: 'GET',
    headers,
    signal: abortSignal,
  })

  return parseRawResponse<T>(response)
}

/**
 * POST request con body JSON.
 *
 * @example
 * const result = await api.post<AnalysisResult>('/api/projects/1/analyze', { phases: ['ner'] })
 */
async function post<T>(
  path: string,
  body?: Record<string, unknown> | unknown[],
  options: RequestOptions = {},
): Promise<T> {
  const { timeout = 30000, headers = {}, signal } = options
  const abortSignal = createTimeoutSignal(timeout, signal)

  const response = await fetch(apiUrl(path), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal: abortSignal,
  })

  return parseResponse<T>(response)
}

/**
 * POST request con FormData (para uploads).
 *
 * @example
 * const formData = new FormData()
 * formData.append('file', file)
 * const project = await api.postForm<ApiProject>('/api/projects', formData)
 */
async function postForm<T>(
  path: string,
  formData: FormData,
  options: RequestOptions = {},
): Promise<T> {
  const { timeout = 60000, headers = {}, signal } = options
  const abortSignal = createTimeoutSignal(timeout, signal)

  const response = await fetch(apiUrl(path), {
    method: 'POST',
    headers, // No Content-Type - el browser lo pone con boundary
    body: formData,
    signal: abortSignal,
  })

  return parseResponse<T>(response)
}

/**
 * GET request que puede fallar silenciosamente (devuelve null en error).
 * Útil para polling y refreshes opcionales.
 */
async function tryGet<T>(path: string, options: RequestOptions = {}): Promise<T | null> {
  try {
    return await get<T>(path, options)
  } catch {
    return null
  }
}

/**
 * POST sin verificar success (para endpoints como /api/languagetool/start).
 */
async function postRaw<T>(
  path: string,
  body?: Record<string, unknown>,
  options: RequestOptions = {},
): Promise<T> {
  const { timeout = 30000, headers = {}, signal } = options
  const abortSignal = createTimeoutSignal(timeout, signal)

  const fetchOptions: RequestInit = {
    method: 'POST',
    headers: body !== undefined ? { 'Content-Type': 'application/json', ...headers } : headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal: abortSignal,
  }

  const response = await fetch(apiUrl(path), fetchOptions)
  return parseRawResponse<T>(response)
}

/**
 * PUT request con body JSON.
 *
 * @example
 * await api.put('/api/projects/1/entities/5', { name: 'Nuevo nombre' })
 */
async function put<T>(
  path: string,
  body?: Record<string, unknown> | unknown[],
  options: RequestOptions = {},
): Promise<T> {
  const { timeout = 30000, headers = {}, signal } = options
  const abortSignal = createTimeoutSignal(timeout, signal)

  const response = await fetch(apiUrl(path), {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal: abortSignal,
  })

  return parseResponse<T>(response)
}

/**
 * PUT sin wrapper ApiResponse.
 */
async function putRaw<T>(
  path: string,
  body?: Record<string, unknown> | unknown[],
  options: RequestOptions = {},
): Promise<T> {
  const { timeout = 30000, headers = {}, signal } = options
  const abortSignal = createTimeoutSignal(timeout, signal)

  const response = await fetch(apiUrl(path), {
    method: 'PUT',
    headers: body !== undefined ? { 'Content-Type': 'application/json', ...headers } : headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal: abortSignal,
  })

  return parseRawResponse<T>(response)
}

/**
 * PATCH request con body JSON.
 *
 * @example
 * await api.patch('/api/entity-filters/system-patterns/1', { is_active: false })
 */
async function patch<T>(
  path: string,
  body?: Record<string, unknown>,
  options: RequestOptions = {},
): Promise<T> {
  const { timeout = 30000, headers = {}, signal } = options
  const abortSignal = createTimeoutSignal(timeout, signal)

  const response = await fetch(apiUrl(path), {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal: abortSignal,
  })

  return parseRawResponse<T>(response)
}

/**
 * DELETE request.
 *
 * @example
 * await api.del('/api/projects/1')
 */
async function del<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { timeout = 30000, headers = {}, signal } = options
  const abortSignal = createTimeoutSignal(timeout, signal)

  const response = await fetch(apiUrl(path), {
    method: 'DELETE',
    headers,
    signal: abortSignal,
  })

  return parseRawResponse<T>(response)
}

export const api = {
  get,
  getRaw,
  post,
  postForm,
  postRaw,
  tryGet,
  put,
  putRaw,
  patch,
  del,
} as const
