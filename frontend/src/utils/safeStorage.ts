/**
 * Safe localStorage wrapper with quota error handling.
 *
 * Prevents silent failures when localStorage quota is exceeded
 * or access is denied (private browsing, security policies).
 */

/**
 * Safely write to localStorage. Returns true on success, false on failure.
 * Logs a warning on quota exceeded instead of throwing.
 */
export function safeSetItem(key: string, value: string): boolean {
  try {
    localStorage.setItem(key, value)
    return true
  } catch (e) {
    if (e instanceof DOMException && (e.name === 'QuotaExceededError' || e.code === 22)) {
      console.warn(`[safeStorage] Quota exceeded writing key "${key}" (${value.length} chars)`)
    } else {
      console.warn(`[safeStorage] Failed to write key "${key}":`, e)
    }
    return false
  }
}

/**
 * Safely read from localStorage. Returns null on failure (same as missing key).
 */
export function safeGetItem(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch (e) {
    console.warn(`[safeStorage] Failed to read key "${key}":`, e)
    return null
  }
}
