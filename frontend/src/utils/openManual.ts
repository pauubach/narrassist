/**
 * Open user manual in new window/tab
 *
 * The manual is built from docs/ via MkDocs and served as static HTML at /docs/
 */
export function openManual(chapter?: string) {
  const baseUrl = '/docs/index.html'
  const url = chapter ? `/docs/user-manual/${chapter}/` : baseUrl

  // Open in new window/tab
  window.open(url, '_blank', 'noopener,noreferrer')
}

/**
 * Manual chapter shortcuts (MkDocs generates folders from filenames)
 */
export const manualChapters = {
  introduction: '01-introduction',
  firstAnalysis: '02-first-analysis',
  entities: '03-entities',
  alerts: '04-alerts',
  timeline: '05-timeline-events',
  collections: '06-collections-sagas',
  settings: '07-settings',
  useCases: '08-use-cases',
} as const

/**
 * Open specific manual chapter
 */
export function openManualChapter(chapter: keyof typeof manualChapters) {
  openManual(manualChapters[chapter])
}
