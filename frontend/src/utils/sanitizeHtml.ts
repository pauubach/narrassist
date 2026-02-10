/**
 * Defense-in-depth HTML sanitization using DOMPurify.
 *
 * Wraps DOMPurify with a whitelist of tags/attributes used by our
 * highlighting system (DocumentViewer, EchoReportTab, TextHighlighter).
 */

import DOMPurify from 'dompurify'

/** Tags allowed in highlighted content */
const ALLOWED_TAGS = ['span', 'b', 'i', 'em', 'strong', 'mark', 'br', 'p', 'div']

/** Attributes allowed on those tags */
const ALLOWED_ATTR = [
  'class',
  'style',
  'title',
  'data-entity-id',
  'data-entity-type',
  'data-annotation-id',
  'data-speaker-id',
  'data-speaker-name',
  'data-alert-id',
]

/**
 * Sanitize HTML for use in v-html directives.
 *
 * Only allows the tags and attributes used by our highlighting system.
 * Strips everything else (scripts, event handlers, iframes, etc.).
 */
export function sanitizeHtml(dirty: string): string {
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
  })
}
