/**
 * Logger dual: intercepta console.* para enviar copia a archivo.
 *
 * Funcionamiento:
 * - Monkey-patches console.log/warn/error/debug/info
 * - El console original sigue funcionando (para DevTools/browser)
 * - Cada mensaje se envía también al backend → frontend.log
 * - Buffer con flush cada 3s o al cerrar pestaña
 *
 * Activar en main.ts:
 *   import { installConsoleInterceptor } from '@/services/logger'
 *   installConsoleInterceptor()
 *
 * Helper DRY para catch blocks:
 *   import { logError } from '@/services/logger'
 *   catch (err) { logError('Entities', 'Error loading entities:', err) }
 */

import { apiUrl } from '@/config/api'

type LogLevel = 'debug' | 'info' | 'warn' | 'error'

interface LogEntry {
  level: LogLevel
  message: string
  timestamp: number
}

const FLUSH_INTERVAL_MS = 3000
const MAX_BUFFER_SIZE = 100

const buffer: LogEntry[] = []
let flushTimer: ReturnType<typeof setInterval> | null = null
let flushing = false
let installed = false

// Save original console methods BEFORE patching
const _origLog = console.log.bind(console)
const _origWarn = console.warn.bind(console)
const _origError = console.error.bind(console)
const _origDebug = console.debug.bind(console)
const _origInfo = console.info.bind(console)

function startFlushTimer() {
  if (flushTimer) return
  flushTimer = setInterval(flush, FLUSH_INTERVAL_MS)

  if (typeof window !== 'undefined') {
    window.addEventListener('beforeunload', flush)
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') flush()
    })
  }
}

function enqueue(level: LogLevel, message: string) {
  buffer.push({ level, message, timestamp: Date.now() })
  if (buffer.length >= MAX_BUFFER_SIZE) {
    flush()
  }
}

function flush() {
  if (flushing || buffer.length === 0) return
  const entries = buffer.splice(0)
  flushing = true

  fetch(apiUrl('/api/logs/frontend'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ entries }),
    keepalive: true,
  })
    .catch(() => {
      // Backend not available — drop silently (console already has the logs)
    })
    .finally(() => {
      flushing = false
    })
}

function formatArgs(args: unknown[]): string {
  return args
    .map((a) => {
      if (typeof a === 'string') return a
      if (a instanceof Error) return `${a.name}: ${a.message}`
      try {
        return JSON.stringify(a)
      } catch {
        return String(a)
      }
    })
    .join(' ')
}

/**
 * Instala el interceptor global de console.
 * Llamar una sola vez en main.ts al arrancar la app.
 */
export function installConsoleInterceptor() {
  if (installed) return
  installed = true

  console.log = (...args: unknown[]) => {
    _origLog(...args)
    enqueue('info', formatArgs(args))
    startFlushTimer()
  }

  console.warn = (...args: unknown[]) => {
    _origWarn(...args)
    enqueue('warn', formatArgs(args))
    startFlushTimer()
  }

  console.error = (...args: unknown[]) => {
    _origError(...args)
    enqueue('error', formatArgs(args))
    startFlushTimer()
  }

  console.debug = (...args: unknown[]) => {
    _origDebug(...args)
    enqueue('debug', formatArgs(args))
    startFlushTimer()
  }

  console.info = (...args: unknown[]) => {
    _origInfo(...args)
    enqueue('info', formatArgs(args))
    startFlushTimer()
  }

  // Log that interceptor is active
  _origLog('[Logger] Console interceptor installed — logs will be sent to frontend.log')
  enqueue('info', '[Logger] Console interceptor installed')
  startFlushTimer()
}

/**
 * Helper DRY para catch blocks.
 * Combina console.error + contexto legible.
 *
 * @example
 *   catch (err) { logError('Entities', 'Error loading entities:', err) }
 *   // Output: [Entities] Error loading entities: TypeError: ...
 */
export function logError(tag: string, message: string, err?: unknown) {
  const errStr = err instanceof Error ? `${err.name}: ${err.message}` : err !== undefined ? String(err) : ''
  const full = errStr ? `[${tag}] ${message} ${errStr}` : `[${tag}] ${message}`
  console.error(full)
}

/** Force immediate flush of buffered entries */
export function flushLogs() {
  flush()
}
