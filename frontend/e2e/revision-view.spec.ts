import { test, expect } from '@playwright/test'
import { setupMockApi } from './support/mockApi'
import { prepareAppForE2E } from './support/app'

test.describe('E2E - RevisionView (Revision Intelligence)', () => {
  test.beforeEach(async ({ page }) => {
    await prepareAppForE2E(page)
    await setupMockApi(page)
  })

  test('navigates to revision view from project detail', async ({ page }) => {
    await page.goto('/projects/1')

    // Click on "Revision Intelligence" button/link
    await page.getByRole('button', { name: /Revision Intelligence|Revisar/i }).click()

    await expect(page).toHaveURL(/\/projects\/1\/revision/)
    await expect(page).toHaveTitle(/Revision Intelligence/)
  })

  test('displays revision dashboard with back navigation', async ({ page }) => {
    await page.goto('/projects/1/revision')

    // Check back button exists
    const backButton = page.getByRole('button', { name: /Volver al proyecto/i })
    await expect(backButton).toBeVisible()
    await expect(backButton).toHaveAttribute('aria-label', /Volver/i)

    // Check dashboard is rendered
    await expect(page.locator('.revision-dashboard')).toBeVisible()
  })

  test('back button navigates to project alerts tab', async ({ page }) => {
    await page.goto('/projects/1/revision')

    await page.getByRole('button', { name: /Volver al proyecto/i }).click()

    await expect(page).toHaveURL('/projects/1?tab=alerts')
  })

  test('displays revision statistics and metrics', async ({ page }) => {
    await page.goto('/projects/1/revision')

    // Wait for dashboard to load
    await expect(page.locator('.revision-dashboard')).toBeVisible()

    // Check for key metrics
    await expect(page.getByText(/Alertas pendientes|Pending alerts/i)).toBeVisible()
    await expect(page.getByText(/Alertas resueltas|Resolved alerts/i)).toBeVisible()
    await expect(page.getByText(/Tasa de resolución|Resolution rate/i)).toBeVisible()
  })

  test('displays alert prioritization panel', async ({ page }) => {
    await page.goto('/projects/1/revision')

    await expect(page.locator('[data-testid="alert-prioritization"]')).toBeVisible()
    await expect(page.getByText(/Prioridad alta|High priority/i)).toBeVisible()
  })

  test('allows filtering alerts by severity in revision mode', async ({ page }) => {
    await page.goto('/projects/1/revision')

    // Click severity filter
    await page.getByRole('button', { name: /Severidad|Severity/i }).click()
    await page.getByRole('option', { name: /Alta|High/i }).click()

    // Verify filtered alerts
    const alerts = page.locator('.revision-alert-item')
    await expect(alerts.first()).toBeVisible()

    // All visible alerts should be high severity
    const severityBadges = page.locator('.severity-badge.high')
    expect(await severityBadges.count()).toBeGreaterThan(0)
  })

  test('displays alert context and suggested fixes', async ({ page }) => {
    await page.goto('/projects/1/revision')

    // Click on first alert
    await page.locator('.revision-alert-item').first().click()

    // Check context is shown
    await expect(page.getByText(/Contexto|Context/i)).toBeVisible()
    await expect(page.locator('.alert-context-text')).toBeVisible()

    // Check suggested fix
    await expect(page.getByText(/Sugerencia|Suggestion/i)).toBeVisible()
  })

  test('allows accepting a suggested fix', async ({ page }) => {
    await page.goto('/projects/1/revision')

    await page.locator('.revision-alert-item').first().click()

    const acceptButton = page.getByRole('button', { name: /Aceptar sugerencia|Accept/i })
    await expect(acceptButton).toBeVisible()
    await acceptButton.click()

    // Verify confirmation
    await expect(page.getByText(/Cambio aplicado|Change applied/i)).toBeVisible()
  })

  test('allows rejecting a suggested fix', async ({ page }) => {
    await page.goto('/projects/1/revision')

    await page.locator('.revision-alert-item').first().click()

    const rejectButton = page.getByRole('button', { name: /Rechazar|Reject|Ignorar/i })
    await expect(rejectButton).toBeVisible()
    await rejectButton.click()

    // Verify rejection
    await expect(page.getByText(/Sugerencia rechazada|Rejected/i)).toBeVisible()
  })

  test('displays revision history timeline', async ({ page }) => {
    await page.goto('/projects/1/revision')

    // Navigate to history tab
    await page.getByRole('tab', { name: /Historial|History/i }).click()

    await expect(page.locator('.revision-history-timeline')).toBeVisible()
    await expect(page.locator('.history-item')).toHaveCount(3, { timeout: 5000 })
  })

  test('allows undoing a revision action', async ({ page }) => {
    await page.goto('/projects/1/revision')

    // Accept a fix first
    await page.locator('.revision-alert-item').first().click()
    await page.getByRole('button', { name: /Aceptar/i }).click()

    // Then undo it
    const undoButton = page.getByRole('button', { name: /Deshacer|Undo/i })
    await expect(undoButton).toBeVisible()
    await undoButton.click()

    await expect(page.getByText(/Acción deshecha|Action undone/i)).toBeVisible()
  })

  test('displays batch actions for multiple alerts', async ({ page }) => {
    await page.goto('/projects/1/revision')

    // Select multiple alerts
    await page.locator('.revision-alert-item input[type="checkbox"]').nth(0).check()
    await page.locator('.revision-alert-item input[type="checkbox"]').nth(1).check()

    // Check batch actions appear
    await expect(page.getByRole('button', { name: /Aceptar seleccionadas|Accept selected/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /Rechazar seleccionadas|Reject selected/i })).toBeVisible()
  })

  test('supports keyboard navigation in revision mode', async ({ page }) => {
    await page.goto('/projects/1/revision')

    // Focus first alert
    await page.locator('.revision-alert-item').first().focus()

    // Press Enter to select
    await page.keyboard.press('Enter')
    await expect(page.locator('.alert-detail-panel')).toBeVisible()

    // Press Escape to close
    await page.keyboard.press('Escape')
    await expect(page.locator('.alert-detail-panel')).not.toBeVisible()
  })

  test('displays progress indicator for batch operations', async ({ page }) => {
    await page.goto('/projects/1/revision')

    // Select all alerts
    await page.getByRole('checkbox', { name: /Seleccionar todas|Select all/i }).check()

    // Click batch accept
    await page.getByRole('button', { name: /Aceptar seleccionadas/i }).click()

    // Verify progress indicator
    await expect(page.locator('.p-progressbar')).toBeVisible()
    await expect(page.getByText(/Procesando|Processing/i)).toBeVisible()
  })

  test('handles errors gracefully when accepting fails', async ({ page }) => {
    await prepareAppForE2E(page)
    await setupMockApi(page, { failRevisionAccept: true })

    await page.goto('/projects/1/revision')

    await page.locator('.revision-alert-item').first().click()
    await page.getByRole('button', { name: /Aceptar/i }).click()

    // Verify error message
    await expect(page.getByText(/Error al aplicar cambio|Failed to apply/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /Reintentar|Retry/i })).toBeVisible()
  })

  test('displays revision analytics and insights', async ({ page }) => {
    await page.goto('/projects/1/revision')

    // Navigate to analytics tab
    await page.getByRole('tab', { name: /Análisis|Analytics/i }).click()

    // Check for charts
    await expect(page.locator('canvas')).toBeVisible() // Chart.js canvas
    await expect(page.getByText(/Tipos de alerta más comunes|Most common alert types/i)).toBeVisible()
  })

  test('exports revision report', async ({ page }) => {
    await page.goto('/projects/1/revision')

    const downloadPromise = page.waitForEvent('download')

    await page.getByRole('button', { name: /Exportar informe|Export report/i }).click()
    await page.getByRole('option', { name: /PDF/i }).click()

    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/revision-report.*\.pdf/)
  })

  test('maintains state when navigating away and back', async ({ page }) => {
    await page.goto('/projects/1/revision')

    // Apply a filter
    await page.getByRole('button', { name: /Severidad/i }).click()
    await page.getByRole('option', { name: /Alta/i }).click()

    // Navigate away
    await page.getByRole('button', { name: /Volver/i }).click()

    // Navigate back
    await page.getByRole('button', { name: /Revision Intelligence/i }).click()

    // Verify filter is still applied
    const activeFilter = page.locator('.filter-badge', { hasText: /Alta/i })
    await expect(activeFilter).toBeVisible()
  })

  test('responsive layout on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/projects/1/revision')

    // Verify mobile layout
    await expect(page.locator('.revision-view')).toHaveCSS('max-width', '900px')

    // Alert list should be full width
    const alertList = page.locator('.revision-alert-list')
    await expect(alertList).toBeVisible()
  })

  test('accessibility - ARIA labels and keyboard support', async ({ page }) => {
    await page.goto('/projects/1/revision')

    // Check ARIA labels
    const backButton = page.getByRole('button', { name: /Volver/i })
    await expect(backButton).toHaveAttribute('aria-label')

    // Check focus management
    await page.keyboard.press('Tab')
    const focusedElement = await page.evaluate(() => document.activeElement?.tagName)
    expect(['BUTTON', 'A', 'INPUT']).toContain(focusedElement)
  })
})
