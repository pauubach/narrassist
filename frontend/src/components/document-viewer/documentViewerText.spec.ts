import { describe, expect, it } from 'vitest'
import {
  cleanExcerptForSearch,
  detectSectionHeading,
  escapeHtml,
  escapeRegex,
  findClosestTextOccurrence,
  getTitleOffset,
  hexToRgba,
  removeLeadingTitle,
  replaceOutsideHtmlTags,
} from './documentViewerText'

describe('documentViewerText helpers', () => {
  it('detects and removes duplicated chapter titles', () => {
    const content = 'Capítulo 1. El despertar\n\nTexto del capítulo'

    expect(getTitleOffset(content, 'Capítulo 1. El despertar')).toBeGreaterThan(0)
    expect(removeLeadingTitle(content, 'Capítulo 1. El despertar')).toBe('Texto del capítulo')
  })

  it('finds the closest occurrence when a preferred offset exists', () => {
    const haystack = 'Ana llegó. Ana volvió. Ana salió.'
    const needle = 'Ana'

    expect(findClosestTextOccurrence(haystack, needle, 12)).toBe(haystack.indexOf('Ana', 11))
  })

  it('replaces text outside html tags only', () => {
    const result = replaceOutsideHtmlTags(
      '<span>Ana</span> y Ana',
      /Ana/g,
      (match) => `[${match}]`,
    )

    expect(result).toBe('<span>[Ana]</span> y [Ana]')
  })

  it('detects common section heading shapes', () => {
    expect(detectSectionHeading('PARTE I')).toEqual({ level: 'h2' })
    expect(detectSectionHeading('1. El conflicto')).toEqual({ level: 'h3' })
    expect(detectSectionHeading('a) Alternativa')).toEqual({ level: 'h4' })
  })

  it('escapes html and regex metacharacters', () => {
    expect(escapeHtml('<Ana & "Pedro">')).toBe('&lt;Ana &amp; &quot;Pedro&quot;&gt;')
    expect(escapeRegex('Ana.*(Pedro)')).toBe('Ana\\.\\*\\(Pedro\\)')
  })

  it('normalizes excerpts and colors', () => {
    expect(cleanExcerptForSearch('...  «Texto   con   ruido» ...')).toBe('"Texto con ruido"')
    expect(hexToRgba('#abc', 0.5)).toBe('rgba(170, 187, 204, 0.5)')
  })
})
