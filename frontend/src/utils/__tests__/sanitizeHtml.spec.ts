/**
 * Tests for the sanitizeHtml defense-in-depth utility.
 */

import { sanitizeHtml } from '../sanitizeHtml'

describe('sanitizeHtml', () => {
  it('allows safe highlight markup', () => {
    const input = '<p>Hello <mark class="entity-highlight" data-entity-id="1">world</mark></p>'
    expect(sanitizeHtml(input)).toBe(input)
  })

  it('allows annotation spans with data attributes', () => {
    const input = '<span class="annotation spelling-error" data-annotation-id="42" title="Suggestion">texto</span>'
    expect(sanitizeHtml(input)).toBe(input)
  })

  it('allows dialogue highlight spans', () => {
    const input = '<span class="dialogue-highlight" data-speaker-id="5" data-speaker-name="María">Hola</span>'
    expect(sanitizeHtml(input)).toBe(input)
  })

  it('strips script tags', () => {
    const input = '<p>Safe</p><script>alert("xss")</script>'
    expect(sanitizeHtml(input)).toBe('<p>Safe</p>')
  })

  it('strips event handlers', () => {
    const input = '<span onmouseover="alert(1)">text</span>'
    expect(sanitizeHtml(input)).toBe('<span>text</span>')
  })

  it('strips iframe tags', () => {
    const input = '<p>Text</p><iframe src="evil.com"></iframe>'
    expect(sanitizeHtml(input)).toBe('<p>Text</p>')
  })

  it('strips disallowed attributes', () => {
    const input = '<span onclick="alert(1)" href="javascript:void(0)">x</span>'
    const result = sanitizeHtml(input)
    expect(result).not.toContain('onclick')
    expect(result).not.toContain('href')
    expect(result).toBe('<span>x</span>')
  })

  it('allows br and div tags', () => {
    const input = '<div class="section-h3">Title</div><p>Line1<br>Line2</p>'
    expect(sanitizeHtml(input)).toBe(input)
  })

  it('preserves escaped HTML entities in text', () => {
    const input = '<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>'
    expect(sanitizeHtml(input)).toBe(input)
  })

  it('handles empty string', () => {
    expect(sanitizeHtml('')).toBe('')
  })

  it('strips img tags with onerror', () => {
    const input = '<img src=x onerror="alert(1)">'
    expect(sanitizeHtml(input)).toBe('')
  })
})
