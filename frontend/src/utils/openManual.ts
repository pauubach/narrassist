/**
 * Open user manual in new window/tab
 *
 * The manual is built from docs_site/ and served as static HTML at /docs/
 */
export function openManual(chapter?: string) {
  const baseUrl = '/docs/index.html'
  const url = chapter ? `/docs/user-manual/${chapter}.html` : baseUrl

  // Open in new window/tab
  window.open(url, '_blank', 'noopener,noreferrer')
}

/**
 * Manual chapter shortcuts
 */
export const manualChapters = {
  introduction: 'introduction',
  firstAnalysis: 'first-analysis',
  entities: 'entities',
  alerts: 'alerts',
  timeline: 'timeline-events',
  collections: 'collections-sagas',
  settings: 'settings',
  useCases: 'use-cases',
} as const

/**
 * Open specific manual chapter
 */
export function openManualChapter(chapter: keyof typeof manualChapters) {
  openManual(manualChapters[chapter])
}
