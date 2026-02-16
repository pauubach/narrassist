/**
 * Renderiza Markdown simple del asistente a HTML seguro.
 *
 * Soporta:
 * - párrafos y saltos de línea
 * - listas con viñetas y numeradas
 * - negrita, cursiva y código inline
 * - títulos (h1-h3) y blockquotes
 * - enlaces http/https
 */

import DOMPurify from 'dompurify'

const ALLOWED_TAGS = [
  'p', 'br', 'strong', 'em', 'code', 'ul', 'ol', 'li',
  'h1', 'h2', 'h3', 'blockquote', 'a',
]

const ALLOWED_ATTR = ['href', 'target', 'rel']

function escapeHtml(input: string): string {
  return input
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function renderInline(text: string): string {
  let out = escapeHtml(text)

  // Enlaces [texto](https://url)
  out = out.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_m, label: string, url: string) => {
    const safeUrl = url.replace(/"/g, '&quot;')
    return `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${label}</a>`
  })

  // Código inline
  out = out.replace(/`([^`\n]+)`/g, '<code>$1</code>')

  // Negrita
  out = out.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')

  // Cursiva
  out = out.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1<em>$2</em>')

  return out
}

/**
 * Convierte markdown simple a HTML seguro para renderizar con v-html.
 */
export function renderAssistantMarkdown(markdown: string): string {
  const raw = (markdown || '').replace(/\r\n?/g, '\n').trim()
  if (!raw) return ''

  const lines = raw.split('\n')
  const blocks: string[] = []
  const paragraphBuffer: string[] = []
  let listType: 'ul' | 'ol' | null = null

  const flushParagraph = () => {
    if (paragraphBuffer.length === 0) return
    const html = paragraphBuffer.map(renderInline).join('<br>')
    blocks.push(`<p>${html}</p>`)
    paragraphBuffer.length = 0
  }

  const flushList = () => {
    if (!listType) return
    blocks.push(`</${listType}>`)
    listType = null
  }

  const openListIfNeeded = (nextType: 'ul' | 'ol') => {
    if (listType === nextType) return
    flushList()
    blocks.push(`<${nextType}>`)
    listType = nextType
  }

  for (const line of lines) {
    const trimmed = line.trim()

    if (!trimmed) {
      flushParagraph()
      flushList()
      continue
    }

    const h3 = trimmed.match(/^###\s+(.+)$/)
    const h2 = trimmed.match(/^##\s+(.+)$/)
    const h1 = trimmed.match(/^#\s+(.+)$/)
    if (h3 || h2 || h1) {
      flushParagraph()
      flushList()
      const tag = h3 ? 'h3' : h2 ? 'h2' : 'h1'
      const content = renderInline((h3 || h2 || h1)![1])
      blocks.push(`<${tag}>${content}</${tag}>`)
      continue
    }

    const ul = trimmed.match(/^[-*+]\s+(.+)$/)
    if (ul) {
      flushParagraph()
      openListIfNeeded('ul')
      blocks.push(`<li>${renderInline(ul[1])}</li>`)
      continue
    }

    const ol = trimmed.match(/^\d+[.)]\s+(.+)$/)
    if (ol) {
      flushParagraph()
      openListIfNeeded('ol')
      blocks.push(`<li>${renderInline(ol[1])}</li>`)
      continue
    }

    const quote = trimmed.match(/^>\s?(.+)$/)
    if (quote) {
      flushParagraph()
      flushList()
      blocks.push(`<blockquote>${renderInline(quote[1])}</blockquote>`)
      continue
    }

    paragraphBuffer.push(trimmed)
  }

  flushParagraph()
  flushList()

  const html = blocks.join('')
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ALLOW_DATA_ATTR: false,
  })
}
