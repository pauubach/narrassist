import { isAlreadyDownloadingError } from '../useOllamaManagement'

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

