/**
 * Tests para la función escapeHtml del DocumentViewer.
 *
 * Replica la lógica de sanitización HTML usada en DocumentViewer.vue
 * para verificar que contenido malicioso en manuscritos se neutraliza
 * antes de renderizarse con v-html.
 */

import { describe, it, expect } from 'vitest'

/**
 * Replica de la función escapeHtml de DocumentViewer.vue (línea 818).
 * Se prueba aquí de forma aislada para verificar la lógica de escape.
 */
function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

describe('escapeHtml (XSS prevention)', () => {
  it('should escape <script> tags', () => {
    const result = escapeHtml('<script>alert("xss")</script>')
    expect(result).not.toContain('<script>')
    expect(result).toContain('&lt;script&gt;')
  })

  it('should escape <img onerror> payloads', () => {
    const result = escapeHtml('<img src=x onerror="alert(1)">')
    expect(result).not.toContain('<img')
    expect(result).toContain('&lt;img')
  })

  it('should escape angle brackets', () => {
    const result = escapeHtml('a < b > c')
    expect(result).toContain('&lt;')
    expect(result).toContain('&gt;')
  })

  it('should escape ampersands', () => {
    const result = escapeHtml('Tom & Jerry')
    expect(result).toContain('&amp;')
  })

  it('should handle quotes safely in text context', () => {
    // textContent→innerHTML no necesita escapar comillas en nodos de texto,
    // ya que no hay contexto de atributo HTML donde sean peligrosas
    const result = escapeHtml('He said "hello"')
    expect(result).toContain('hello')
  })

  it('should preserve normal text unchanged', () => {
    const result = escapeHtml('María corrió por el parque.')
    expect(result).toBe('María corrió por el parque.')
  })

  it('should handle empty string', () => {
    expect(escapeHtml('')).toBe('')
  })

  it('should escape nested HTML payloads', () => {
    const result = escapeHtml('<div onmouseover="alert(1)"><b>click</b></div>')
    expect(result).not.toContain('<div')
    expect(result).not.toContain('<b>')
  })

  it('should escape event handler attributes', () => {
    const result = escapeHtml('<a href="javascript:alert(1)">link</a>')
    // El tag <a> queda neutralizado (no se renderiza como enlace)
    expect(result).not.toContain('<a ')
    expect(result).toContain('&lt;a')
  })

  it('should handle manuscript text with embedded HTML', () => {
    const manuscript = `El detective leyó el código fuente:
<script>document.cookie</script>
"Esto es lo que enviaron", dijo.`

    const result = escapeHtml(manuscript)
    expect(result).not.toContain('<script>')
    expect(result).toContain('&lt;script&gt;')
    // Normal text preserved
    expect(result).toContain('El detective')
  })
})
