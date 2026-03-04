import { isAlreadyDownloadingError, MODEL_DOWNLOAD_POLL_MAX_ITERATIONS } from '../useOllamaManagement'

// HI-01: Named constant exported
describe('MODEL_DOWNLOAD_POLL_MAX_ITERATIONS', () => {
  it('is a positive number', () => {
    expect(typeof MODEL_DOWNLOAD_POLL_MAX_ITERATIONS).toBe('number')
    expect(MODEL_DOWNLOAD_POLL_MAX_ITERATIONS).toBeGreaterThan(0)
  })

  it('is at least 60 iterations (1 minute minimum)', () => {
    expect(MODEL_DOWNLOAD_POLL_MAX_ITERATIONS).toBeGreaterThanOrEqual(60)
  })
})

describe('isAlreadyDownloadingError', () => {
  it('detecta mensaje exacto del backend', () => {
    expect(isAlreadyDownloadingError('Ya hay una descarga en curso')).toBe(true)
  })

  it('es case-insensitive', () => {
    expect(isAlreadyDownloadingError('YA HAY UNA DESCARGA EN CURSO')).toBe(true)
  })

  it('no marca otros errores', () => {
    expect(isAlreadyDownloadingError('No se pudo iniciar el asistente de IA')).toBe(false)
  })

  it('maneja null/undefined/empty', () => {
    expect(isAlreadyDownloadingError(undefined)).toBe(false)
    expect(isAlreadyDownloadingError(null)).toBe(false)
    expect(isAlreadyDownloadingError('')).toBe(false)
  })
})

