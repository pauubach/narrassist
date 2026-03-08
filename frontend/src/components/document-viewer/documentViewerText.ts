export type SectionHeadingLevel = 'h2' | 'h3' | 'h4' | 'h5'

export function getTitleOffset(content: string, title: string): number {
  if (!content || !title) return 0

  const firstNewline = content.indexOf('\n')
  if (firstNewline === -1) return 0

  const firstLine = content.substring(0, firstNewline).trim()
  if (firstLine.length > 100) return 0

  const normalize = (value: string) => value.toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9\s]/g, '')
    .replace(/\s+/g, ' ')
    .trim()

  const normalizedTitle = normalize(title)
  const normalizedFirstLine = normalize(firstLine)
  const isTitleLine =
    normalizedFirstLine.includes(normalizedTitle) ||
    normalizedTitle.includes(normalizedFirstLine) ||
    /^cap[ií]tulo\s+\d+/i.test(firstLine) ||
    /^chapter\s+\d+/i.test(firstLine) ||
    /^parte\s+\d+/i.test(firstLine) ||
    /^[IVXLCDM]+[.:\s]/i.test(firstLine) ||
    /^\d+\.\s+\S/.test(firstLine)

  if (!isTitleLine) return 0

  let offset = firstNewline
  let index = firstNewline
  while (index < content.length && content[index] === '\n') {
    offset++
    index++
  }
  return offset
}

export function removeLeadingTitle(content: string, title: string): string {
  const offset = getTitleOffset(content, title)
  return offset > 0 ? content.substring(offset) : content
}

export function findClosestTextOccurrence(
  haystack: string,
  needle: string,
  expectedIndex?: number,
): number {
  if (!needle) return -1

  const firstIndex = haystack.indexOf(needle)
  if (firstIndex === -1) return -1
  if (expectedIndex === undefined || expectedIndex < 0) return firstIndex

  let bestIndex = firstIndex
  let bestDistance = Math.abs(firstIndex - expectedIndex)
  let currentIndex = firstIndex

  while (currentIndex !== -1) {
    const distance = Math.abs(currentIndex - expectedIndex)
    if (distance < bestDistance) {
      bestDistance = distance
      bestIndex = currentIndex
    }
    currentIndex = haystack.indexOf(needle, currentIndex + 1)
  }

  return bestIndex
}

export function replaceOutsideHtmlTags(
  input: string,
  pattern: RegExp,
  replacer: (match: string) => string,
): string {
  return input
    .split(/(<[^>]+>)/g)
    .map((segment) => {
      if (!segment) return segment
      if (segment.startsWith('<') && segment.endsWith('>')) return segment
      const safePattern = new RegExp(pattern.source, pattern.flags)
      return segment.replace(safePattern, replacer)
    })
    .join('')
}

export function detectSectionHeading(text: string): { level: SectionHeadingLevel } | null {
  const trimmed = text.trim()

  if (trimmed.length < 3 || trimmed.length > 70) return null
  if (/[.,;:!?]$/.test(trimmed)) return null

  if (
    /^(PARTE|SECCIÓN|SECCION|LIBRO|ACTO|CAPÍTULO|CAPITULO)\s+/i.test(trimmed) ||
    /^[IVXLCDM]+[.:\s]/i.test(trimmed) ||
    (trimmed === trimmed.toUpperCase() && trimmed.length > 3 && /[A-Z]/.test(trimmed))
  ) {
    return { level: 'h2' }
  }

  if (
    /^\d+\.\s+[A-ZÁÉÍÓÚÑ]/.test(trimmed) ||
    /^\d+\.\d+\s+[A-ZÁÉÍÓÚÑ]/.test(trimmed)
  ) {
    return { level: 'h3' }
  }

  if (
    /^[a-z]\)\s+[A-ZÁÉÍÓÚÑ]/.test(trimmed) ||
    /^\d+\.\d+\.\d+\s+/.test(trimmed) ||
    /^[-–—]\s+[A-ZÁÉÍÓÚÑ]/.test(trimmed)
  ) {
    return { level: 'h4' }
  }

  if (
    /^[ivx]+\)\s+/i.test(trimmed) ||
    /^\d+\.\d+\.\d+\.\d+\s+/.test(trimmed)
  ) {
    return { level: 'h5' }
  }

  if (/^[a-záéíóúñ]/.test(trimmed)) return null

  return null
}

export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

export function escapeRegex(text: string | undefined | null): string {
  if (!text) return ''
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export function cleanExcerptForSearch(text: string): string {
  return text
    .replace(/^[.…]+\s*/g, '')
    .replace(/\s*[.…]+$/g, '')
    .replace(/[""'«»]/g, '"')
    .replace(/\s+/g, ' ')
    .trim()
}

export function hexToRgba(hex: string, alpha: number): string {
  const cleanHex = hex.replace('#', '')
  const fullHex = cleanHex.length === 3
    ? cleanHex.split('').map((char) => char + char).join('')
    : cleanHex

  const r = parseInt(fullHex.substring(0, 2), 16)
  const g = parseInt(fullHex.substring(2, 4), 16)
  const b = parseInt(fullHex.substring(4, 6), 16)

  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}
