/**
 * Evita que happy-dom eleve como "uncaught" errores esperados de navegación
 * cuando DOMPurify inspecciona etiquetas <iframe> durante tests de sanitización.
 */
if (typeof window !== 'undefined') {
  window.addEventListener('error', (event) => {
    const err = event.error
    if (
      err instanceof DOMException &&
      err.name === 'NotSupportedError' &&
      String(err.message).includes('Failed to load iframe page')
    ) {
      event.preventDefault()
    }
  })
}
