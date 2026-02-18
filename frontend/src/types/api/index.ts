/**
 * API Types - Re-exports
 *
 * Todos los tipos que coinciden con el backend.
 */

export * from './entities'
export * from './alerts'
export * from './projects'
export * from './timeline'
export * from './collections'

/** Respuesta estándar de la API */
export interface ApiResponse<T = unknown> {
  success: boolean
  data?: T
  error?: string
  message?: string
}
