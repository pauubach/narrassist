/**
 * API Client - Narrative Assistant
 *
 * Cliente HTTP centralizado para comunicación con el backend.
 * Reemplaza las llamadas raw fetch() en los stores.
 */

import { ref, readonly } from 'vue'
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

// ── Monitor de conexión ──────────────────────────────────────
// Detecta cuando el backend no responde y expone un estado reactivo
// para que la UI muestre un banner único en vez de N toasts.

const _backendDown = ref(false)
/** true cuando el backend no responde (múltiples fallos consecutivos) */
export const backendDown = readonly(_backendDown)

const _recoveryAttempts = ref(0)
/** Número de intentos de recuperación fallidos (para escalar el mensaje en UI) */
export const recoveryAttempts = readonly(_recoveryAttempts)

/**
 * Señaliza que el backend respondió correctamente (resetea el contador de fallos).
 * Útil para conexiones que no pasan por monitoredFetch (ej: SSE EventSource).
 */
export function signalBackendAlive() {
  onRequestSuccess()
}

const CONNECTION_FAIL_THRESHOLD = 3
let consecutiveFailures = 0
let recoveryTimer: ReturnType<typeof setInterval> | null = null

function onRequestSuccess() {
  if (consecutiveFailures > 0 || _backendDown.value) {
    consecutiveFailures = 0
    _backendDown.value = false
    _recoveryAttempts.value = 0
    stopRecoveryPolling()
  }
}

function onConnectionFailure() {
  consecutiveFailures++
  if (consecutiveFailures >= CONNECTION_FAIL_THRESHOLD && !_backendDown.value) {
    _backendDown.value = true
    console.warn(`[API] Backend no disponible (${consecutiveFailures} fallos consecutivos)`)
    startRecoveryPolling()
  }
}

function startRecoveryPolling() {
  if (recoveryTimer) return
  recoveryTimer = setInterval(async () => {
    try {
      const res = await fetch(apiUrl('/api/health'), { signal: AbortSignal.timeout(5000) })
      if (res.ok) {
        onRequestSuccess()
        console.info('[API] Backend recuperado')
      }
    } catch {
      _recoveryAttempts.value++
    }
  }, 5000)
}

function stopRecoveryPolling() {
  if (recoveryTimer) {
    clearInterval(recoveryTimer)
    recoveryTimer = null
  }
}

/** Returns true if this error is a connection/timeout failure (not a server error) */
export function isConnectionError(err: unknown): boolean {
  if (err instanceof TypeError && (err.message.includes('fetch') || err.message.includes('network'))) return true
  if (err instanceof DOMException && err.name === 'AbortError') return true
  if (typeof err === 'string' && err.includes('no respondió')) return true
  return false
}

/** Opciones para peticiones */
interface RequestOptions {
  /** Timeout en ms (default: 30000) */
  timeout?: number
  /** Headers adicionales */
  headers?: Record<string, string>
  /** Signal para cancelación */
  signal?: AbortSignal
  /** Number of retries on connection error (default: 0, max: 3). Only for GET requests. */
  retries?: number
}

/**
 * Wrapper de fetch que alimenta el monitor de conexión.
 * Si backendDown=true, los componentes pueden mostrar un banner
 * en vez de múltiples toasts de error individuales.
 */
async function monitoredFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  try {
    const response = await fetch(input, init)
    onRequestSuccess()
    return response
  } catch (err) {
    if (isConnectionError(err)) {
      onConnectionFailure()
    }
    throw err
  }
}

/**
 * monitoredFetch with retry + exponential backoff for transient connection errors.
 * Creates a fresh timeout signal per attempt to avoid stale AbortSignals.
 */
async function monitoredFetchWithRetry(
  input: RequestInfo | URL,
  init: RequestInit | undefined,
  retries: number,
  timeoutMs?: number,
  userSignal?: AbortSignal,
): Promise<Response> {
  const maxRetries = Math.min(retries, 3)
  let lastError: unknown
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      // Create a fresh timeout signal per attempt (prevents stale signal after timeout)
      const attemptInit = timeoutMs
        ? { ...init, signal: createTimeoutSignal(timeoutMs, userSignal) }
        : init
      return await monitoredFetch(input, attemptInit)
    } catch (err) {
      lastError = err
      if (isConnectionError(err) && attempt < maxRetries) {
        // Exponential backoff: 2s, 4s, 8s (longer for slow local inference)
        await new Promise(r => setTimeout(r, 2000 * Math.pow(2, attempt)))
        continue
      }
      throw err
    }
  }
  throw lastError // unreachable, but satisfies TS
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
      data.error || 'Error interno',
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
  const reason = `Sin respuesta tras ${Math.round(timeoutMs / 1000)}s`

  const timer = setTimeout(() => controller.abort(reason), timeoutMs)

  // Si hay un signal existente, abortar cuando este se aborte
  if (existingSignal) {
    existingSignal.addEventListener('abort', () => {
      clearTimeout(timer)
      controller.abort(existingSignal.reason)
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
  const { timeout = 30000, headers = {}, signal, retries = 0 } = options

  const response = retries > 0
    ? await monitoredFetchWithRetry(apiUrl(path), { method: 'GET', headers }, retries, timeout, signal)
    : await monitoredFetch(apiUrl(path), { method: 'GET', headers, signal: createTimeoutSignal(timeout, signal) })

  return parseResponse<T>(response)
}

/**
 * GET request sin wrapper ApiResponse (para health checks, etc).
 */
async function getRaw<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { timeout = 30000, headers = {}, signal, retries = 0 } = options

  const response = retries > 0
    ? await monitoredFetchWithRetry(apiUrl(path), { method: 'GET', headers }, retries, timeout, signal)
    : await monitoredFetch(apiUrl(path), { method: 'GET', headers, signal: createTimeoutSignal(timeout, signal) })

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

  const response = await monitoredFetch(apiUrl(path), {
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

  const response = await monitoredFetch(apiUrl(path), {
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
  const { timeout = 30000, headers = {}, signal, retries = 0 } = options

  const fetchInit: RequestInit = {
    method: 'POST',
    headers: body !== undefined ? { 'Content-Type': 'application/json', ...headers } : headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  }

  const response = retries > 0
    ? await monitoredFetchWithRetry(apiUrl(path), fetchInit, retries, timeout, signal)
    : await monitoredFetch(apiUrl(path), { ...fetchInit, signal: createTimeoutSignal(timeout, signal) })
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

  const response = await monitoredFetch(apiUrl(path), {
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

  const response = await monitoredFetch(apiUrl(path), {
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

  const response = await monitoredFetch(apiUrl(path), {
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

  const response = await monitoredFetch(apiUrl(path), {
    method: 'DELETE',
    headers,
    signal: abortSignal,
  })

  return parseRawResponse<T>(response)
}

/**
 * GET con check de envelope { success, data, error }.
 * Reemplaza el patrón repetido:
 *   const data = await api.getRaw<{ success: boolean; data: T; error?: string }>(url)
 *   if (data.success) { result = data.data } else { throw new Error(data.error) }
 *
 * @example
 *   const report = await api.getChecked<HealthReport>('/api/projects/1/narrative-health')
 */
async function getChecked<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const raw = await getRaw<{ success: boolean; data: T; error?: string }>(path, options)
  if (!raw.success) {
    throw new ApiError(raw.error || 'Error interno', 200, raw.error)
  }
  return raw.data
}

/**
 * POST con check de envelope { success, data, error }.
 *
 * @example
 *   const result = await api.postChecked<Result>('/api/projects/1/analyze', { phases })
 */
async function postChecked<T>(
  path: string,
  body?: Record<string, unknown>,
  options: RequestOptions = {},
): Promise<T> {
  const raw = await postRaw<{ success: boolean; data: T; error?: string }>(path, body, options)
  if (!raw.success) {
    throw new ApiError(raw.error || 'Error interno', 200, raw.error)
  }
  return raw.data
}

export const api = {
  get,
  getRaw,
  getChecked,
  post,
  postForm,
  postRaw,
  postChecked,
  tryGet,
  put,
  putRaw,
  patch,
  del,
} as const
