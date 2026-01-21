/**
 * API Configuration - Narrative Assistant
 *
 * Centralizes API base URL configuration.
 * In development with Vite proxy, relative URLs work.
 * In production Tauri app, we need absolute URLs to localhost:8008.
 */

// The sidecar runs on port 8008
const SIDECAR_PORT = 8008

// Detect if we're in production Tauri environment
// Vite sets import.meta.env.DEV = true in development
const isProduction = !import.meta.env.DEV

/**
 * Base URL for API calls.
 * - Development: '' (empty, uses Vite proxy)
 * - Production: 'http://localhost:8008' (direct to sidecar)
 */
export const API_BASE = isProduction ? `http://localhost:${SIDECAR_PORT}` : ''

/**
 * Build full API URL from endpoint path.
 * @param path - API endpoint path (e.g., '/api/projects')
 * @returns Full URL for the API call
 */
export function apiUrl(path: string): string {
  // Ensure path starts with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE}${normalizedPath}`
}
