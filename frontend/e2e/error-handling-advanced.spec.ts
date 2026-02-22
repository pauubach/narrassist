import { test, expect } from '@playwright/test'
import { setupMockApi } from './support/mockApi'
import { prepareAppForE2E } from './support/app'

test.describe('E2E - Advanced Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await prepareAppForE2E(page)
  })

  test('handles network timeout (30s+)', async ({ page }) => {
    await setupMockApi(page, { timeoutDelay: 35000 })

    await page.goto('/projects')

    // Should show timeout error
    await expect(page.getByText(/Timeout|Tiempo agotado|demasiado tiempo/i)).toBeVisible({ timeout: 40000 })
    await expect(page.getByRole('button', { name: /Reintentar/i })).toBeVisible()
  })

  test('handles API 500 Internal Server Error', async ({ page }) => {
    await setupMockApi(page, { apiError: 500 })

    await page.goto('/projects')

    await expect(page.getByText(/Error del servidor|Internal Server Error|HTTP 500/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /Reintentar/i })).toBeVisible()
  })

  test('handles API 404 Not Found', async ({ page }) => {
    await setupMockApi(page)

    await page.goto('/projects/99999')

    await expect(page.getByText(/No encontrado|Not Found|404/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /Volver/i })).toBeVisible()
  })

  test('handles API 403 Forbidden', async ({ page }) => {
    await setupMockApi(page, { apiError: 403 })

    await page.goto('/projects/1')

    await expect(page.getByText(/Acceso denegado|Forbidden|sin permisos/i)).toBeVisible()
  })

  test('handles API 401 Unauthorized', async ({ page }) => {
    await setupMockApi(page, { apiError: 401 })

    await page.goto('/projects')

    await expect(page.getByText(/No autorizado|Unauthorized|sesión expirada/i)).toBeVisible()
  })

  test('handles malformed JSON response', async ({ page }) => {
    await setupMockApi(page, { malformedJson: true })

    await page.goto('/projects')

    await expect(page.getByText(/Error de formato|JSON inválido|respuesta inesperada/i)).toBeVisible()
  })

  test('handles empty response body', async ({ page }) => {
    await setupMockApi(page, { emptyResponse: true })

    await page.goto('/projects')

    await expect(page.getByText(/Sin datos|No data|respuesta vacía/i)).toBeVisible()
  })

  test('handles partial response (incomplete data)', async ({ page }) => {
    await setupMockApi(page, { partialResponse: true })

    await page.goto('/projects/1')

    // Should show warning about incomplete data
    await expect(page.getByText(/Datos incompletos|Partial data|algunos campos faltantes/i)).toBeVisible()
  })

  test('handles network disconnection mid-request', async ({ page }) => {
    await setupMockApi(page)

    await page.goto('/projects/1')

    // Simulate network going offline
    await page.context().setOffline(true)

    // Try to perform action that requires network
    await page.getByRole('button', { name: /Analizar/i }).click()

    await expect(page.getByText(/Sin conexión|Offline|red no disponible/i)).toBeVisible()
  })

  test('recovers automatically when network comes back online', async ({ page }) => {
    await setupMockApi(page)

    await page.goto('/projects')

    // Go offline
    await page.context().setOffline(true)
    await page.reload()

    await expect(page.getByText(/Sin conexión|Offline/i)).toBeVisible()

    // Go back online
    await page.context().setOffline(false)
    await page.getByRole('button', { name: /Reintentar/i }).click()

    // Should recover
    await expect(page.locator('.project-card').first()).toBeVisible()
  })

  test('shows offline indicator in status bar', async ({ page }) => {
    await setupMockApi(page)
    await page.goto('/projects')

    await page.context().setOffline(true)

    // Wait a bit for detection
    await page.waitForTimeout(1000)

    await expect(page.locator('.offline-indicator')).toBeVisible()
  })

  test('queues actions when offline and executes on reconnect', async ({ page }) => {
    await setupMockApi(page)
    await page.goto('/projects/1?tab=alerts')

    // Go offline
    await page.context().setOffline(true)

    // Try to resolve alert
    await page.locator('.alert-item').first().locator('button[aria-label*="Resolver"]').click()

    // Should show queued message
    await expect(page.getByText(/Acción en cola|Queued|se ejecutará cuando vuelva la conexión/i)).toBeVisible()

    // Go back online
    await page.context().setOffline(false)

    // Should auto-execute
    await expect(page.getByText(/Acción ejecutada|Completed/i)).toBeVisible({ timeout: 5000 })
  })

  test('retries failed requests with exponential backoff', async ({ page }) => {
    await setupMockApi(page, { failRequestsCount: 2 }) // Fail first 2 attempts

    await page.goto('/projects')

    // Should eventually succeed after retries
    await expect(page.locator('.project-card').first()).toBeVisible({ timeout: 15000 })
  })

  test('handles CORS errors gracefully', async ({ page }) => {
    await setupMockApi(page, { corsError: true })

    await page.goto('/projects')

    await expect(page.getByText(/Error de CORS|Cross-origin|bloqueado por navegador/i)).toBeVisible()
  })

  test('handles SSL certificate errors', async ({ page }) => {
    await setupMockApi(page, { sslError: true })

    await page.goto('/projects')

    await expect(page.getByText(/Certificado|SSL|conexión segura/i)).toBeVisible()
  })

  test('displays user-friendly error messages', async ({ page }) => {
    await setupMockApi(page, { apiError: 500 })

    await page.goto('/projects')

    // Should NOT show technical error
    const errorMessage = page.getByText(/Error/)
    await expect(errorMessage).not.toContainText(/stack trace|undefined|null/)

    // Should show user-friendly message
    await expect(page.getByText(/Intenta de nuevo|contacta soporte|problema temporal/i)).toBeVisible()
  })

  test('allows reporting errors to support', async ({ page }) => {
    await setupMockApi(page, { apiError: 500 })

    await page.goto('/projects')

    await expect(page.getByRole('button', { name: /Reportar error|Contactar soporte/i })).toBeVisible()
  })

  test('handles API rate limiting (429)', async ({ page }) => {
    await setupMockApi(page, { apiError: 429 })

    await page.goto('/projects')

    await expect(page.getByText(/Demasiadas peticiones|Rate limit|intenta más tarde/i)).toBeVisible()
    await expect(page.getByText(/Espera \d+ segundos/i)).toBeVisible()
  })

  test('shows countdown timer for rate limit', async ({ page }) => {
    await setupMockApi(page, { apiError: 429, retryAfter: 10 })

    await page.goto('/projects')

    // Should show countdown
    await expect(page.getByText(/10|9|8/)).toBeVisible({ timeout: 2000 })
  })

  test('handles upload errors (file too large)', async ({ page }) => {
    await setupMockApi(page)
    await page.goto('/projects')

    await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()

    await page.getByLabel(/Nombre/i).fill('Test Project')

    // Try to upload 150MB file
    await page.locator('input[type="file"]').setInputFiles({
      name: 'huge-manuscript.txt',
      mimeType: 'text/plain',
      buffer: Buffer.alloc(150 * 1024 * 1024) // 150MB
    })

    await expect(page.getByText(/Archivo demasiado grande|exceeds|máximo 100MB/i)).toBeVisible()
  })

  test('handles upload errors (unsupported file type)', async ({ page }) => {
    await setupMockApi(page)
    await page.goto('/projects')

    await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()

    await page.locator('input[type="file"]').setInputFiles({
      name: 'script.exe',
      mimeType: 'application/x-msdownload',
      buffer: Buffer.from('fake exe content')
    })

    await expect(page.getByText(/Tipo de archivo no soportado|formato inválido/i)).toBeVisible()
  })

  test('handles concurrent modification conflicts (409)', async ({ page }) => {
    await setupMockApi(page, { apiError: 409 })

    await page.goto('/projects/1?tab=entities')

    // Try to edit entity
    await page.locator('.entity-item').first().click()
    await page.getByLabel(/Nombre/i).fill('Updated Name')
    await page.getByRole('button', { name: /Guardar/i }).click()

    await expect(page.getByText(/Conflicto|modificado por otro usuario|recarga/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /Recargar/i })).toBeVisible()
  })

  test('handles stale data with reload prompt', async ({ page }) => {
    await setupMockApi(page, { staleData: true })

    await page.goto('/projects/1')

    // After 5 minutes of inactivity, should prompt
    await page.waitForTimeout(1000) // Simulate time passing

    await expect(page.getByText(/Datos desactualizados|hay nueva versión/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /Recargar/i })).toBeVisible()
  })

  test('handles analysis failures with detailed error info', async ({ page }) => {
    await setupMockApi(page, { analysisError: 'NLP model not loaded' })

    await page.goto('/projects')

    await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()
    await page.getByLabel(/Nombre/i).fill('Test')
    await page.locator('input[type="file"]').setInputFiles({
      name: 'test.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('Test content')
    })
    await page.getByRole('button', { name: /Crear/i }).click()

    // Should show specific error
    await expect(page.getByText(/Modelo NLP no cargado|NLP model/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /Ver detalles/i })).toBeVisible()
  })

  test('expands error details accordion', async ({ page }) => {
    await setupMockApi(page, { analysisError: 'Stack trace here' })

    await page.goto('/projects/1')
    await page.getByRole('button', { name: /Analizar/i }).click()

    await page.getByRole('button', { name: /Ver detalles/i }).click()

    // Should show technical details
    await expect(page.locator('.error-details')).toBeVisible()
    await expect(page.getByText(/Stack trace/i)).toBeVisible()
  })

  test('copies error details to clipboard', async ({ page }) => {
    await setupMockApi(page, { analysisError: 'Test error' })

    await page.goto('/projects/1')
    await page.getByRole('button', { name: /Analizar/i }).click()

    await page.getByRole('button', { name: /Ver detalles/i }).click()
    await page.getByRole('button', { name: /Copiar|Copy/i }).click()

    await expect(page.getByText(/Copiado/i)).toBeVisible()

    // Verify clipboard
    const clipboardText = await page.evaluate(() => navigator.clipboard.readText())
    expect(clipboardText).toContain('Test error')
  })

  test('handles localStorage quota exceeded', async ({ page }) => {
    await page.goto('/projects')

    // Fill localStorage
    await page.evaluate(() => {
      try {
        for (let i = 0; i < 10000; i++) {
          localStorage.setItem(`test-key-${i}`, 'x'.repeat(1000))
        }
      } catch (e) {
        // Quota exceeded
      }
    })

    // Try to save settings
    await page.goto('/settings')
    await page.getByLabel(/Tema/i).selectOption('dark')

    await expect(page.getByText(/Espacio insuficiente|storage quota|limpia caché/i)).toBeVisible()
  })

  test('handles IndexedDB errors gracefully', async ({ page }) => {
    // Mock IndexedDB failure
    await page.addInitScript(() => {
      Object.defineProperty(window, 'indexedDB', {
        value: {
          open: () => {
            throw new Error('IndexedDB not available')
          }
        }
      })
    })

    await page.goto('/projects')

    // Should fallback to in-memory or show warning
    await expect(page.getByText(/Base de datos no disponible|modo limitado/i)).toBeVisible()
  })
})

test.describe('E2E - Error Recovery Flows', () => {
  test.beforeEach(async ({ page }) => {
    await prepareAppForE2E(page)
  })

  test('recovers from analysis failure by retrying', async ({ page }) => {
    await setupMockApi(page, { failAnalysisOnce: true })

    await page.goto('/projects')
    await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()
    await page.getByLabel(/Nombre/i).fill('Test')
    await page.locator('input[type="file"]').setInputFiles({
      name: 'test.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('Content')
    })
    await page.getByRole('button', { name: /Crear/i }).click()

    // First attempt fails
    await expect(page.getByText(/Error/i)).toBeVisible()

    // Retry
    await page.getByRole('button', { name: /Reintentar/i }).click()

    // Should succeed
    await expect(page).toHaveURL(/\/projects\/\d+/)
  })

  test('auto-saves draft on analysis failure', async ({ page }) => {
    await setupMockApi(page, { analysisError: 'Timeout' })

    await page.goto('/projects')
    await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()
    await page.getByLabel(/Nombre/i).fill('Draft Project')
    await page.locator('input[type="file"]').setInputFiles({
      name: 'test.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('Content')
    })
    await page.getByRole('button', { name: /Crear/i }).click()

    // Analysis fails
    await expect(page.getByText(/Error/i)).toBeVisible()

    // Should show draft saved
    await expect(page.getByText(/Borrador guardado|Draft saved/i)).toBeVisible()

    // Navigate away and back
    await page.goto('/projects')

    // Should be able to resume
    await expect(page.getByText(/Borrador|Draft/i)).toBeVisible()
  })
})
