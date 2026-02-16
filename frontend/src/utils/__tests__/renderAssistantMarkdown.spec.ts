import { renderAssistantMarkdown } from '../renderAssistantMarkdown'

describe('renderAssistantMarkdown', () => {
  it('renders paragraphs and line breaks', () => {
    const result = renderAssistantMarkdown('Primera linea\nSegunda linea')
    expect(result).toBe('<p>Primera linea<br>Segunda linea</p>')
  })

  it('renders unordered and ordered lists', () => {
    const markdown = '- Uno\n- Dos\n\n1. Tres\n2. Cuatro'
    const result = renderAssistantMarkdown(markdown)
    expect(result).toContain('<ul><li>Uno</li><li>Dos</li></ul>')
    expect(result).toContain('<ol><li>Tres</li><li>Cuatro</li></ol>')
  })

  it('renders inline formatting and safe links', () => {
    const markdown = '**Negrita** y *cursiva* con `codigo` y [enlace](https://example.com)'
    const result = renderAssistantMarkdown(markdown)
    expect(result).toContain('<strong>Negrita</strong>')
    expect(result).toContain('<em>cursiva</em>')
    expect(result).toContain('<code>codigo</code>')
    expect(result).toContain('href="https://example.com"')
  })

  it('does not render non-http links as HTML anchors', () => {
    const result = renderAssistantMarkdown('[malo](javascript:alert(1))')
    expect(result).not.toContain('<a ')
    expect(result).toContain('[malo](javascript:alert(1))')
  })

  it('escapes raw html tags', () => {
    const result = renderAssistantMarkdown('<img src=x onerror=alert(1)>')
    expect(result).toContain('&lt;img src=x onerror=alert(1)&gt;')
    expect(result).not.toContain('<img')
  })
})
