import { test, expect } from '@playwright/test'
import { setupMockApi } from './support/mockApi'
import { prepareAppForE2E } from './support/app'

test.describe('E2E - Concurrency and Race Conditions', () => {
  test.beforeEach(async ({ page }) => {
    await prepareAppForE2E(page)
    await setupMockApi(page)
  })

  test('handles simultaneous edits to same entity', async ({ browser }) => {
    const context1 = await browser.newContext()
    const context2 = await browser.newContext()

    const page1 = await context1.newPage()
    const page2 = await context2.newPage()

    await Promise.all([
      prepareAppForE2E(page1),
      prepareAppForE2E(page2)
    ])

    await Promise.all([
      setupMockApi(page1),
      setupMockApi(page2)
    ])

    // Both users navigate to same entity
    await Promise.all([
      page1.goto('/projects/1?tab=entities'),
      page2.goto('/projects/1?tab=entities')
    ])

    // Both edit same entity
    await page1.locator('.entity-item').first().click()
    await page2.locator('.entity-item').first().click()

    await page1.getByLabel(/Nombre/i).fill('User 1 Edit')
    await page2.getByLabel(/Nombre/i).fill('User 2 Edit')

    // Save simultaneously
    await Promise.all([
      page1.getByRole('button', { name: /Guardar/i }).click(),
      page2.waitForTimeout(100).then(() => page2.getByRole('button', { name: /Guardar/i }).click())
    ])

    // Should show conflict warning
    await expect(page2.getByText(/Conflicto|modificado por otro usuario/i)).toBeVisible()

    await context1.close()
    await context2.close()
  })

  test('handles alert resolved while viewing details', async ({ page }) => {
    await page.goto('/projects/1?tab=alerts')

    await page.locator('.alert-item').first().click()

    // Simulate another user resolving the alert
    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('alert-updated', {
        detail: { alertId: 1, status: 'resolved' }
      }))
    })

    await expect(page.getByText(/Alerta actualizada|Alert updated/i)).toBeVisible()
  })

  test('handles project deleted while viewing', async ({ page }) => {
    await page.goto('/projects/1')

    // Simulate project deletion
    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('project-deleted', { detail: { projectId: 1 } }))
    })

    await expect(page.getByText(/Proyecto eliminado|Project deleted/i)).toBeVisible()
    await expect(page).toHaveURL('/projects')
  })

  test('handles analysis in progress when requesting new analysis', async ({ page }) => {
    await page.goto('/projects/1')

    await page.getByRole('button', { name: /Analizar/i }).click()

    // Try to start another analysis
    await page.getByRole('button', { name: /Analizar/i }).click()

    await expect(page.getByText(/Análisis en curso|Analysis in progress/i)).toBeVisible()
  })

  test('queues actions during offline and executes on reconnect', async ({ page }) => {
    await page.goto('/projects/1?tab=alerts')

    // Go offline
    await page.context().setOffline(true)

    // Try to resolve 3 alerts
    for (let i = 0; i < 3; i++) {
      await page.locator('.alert-item').nth(i).locator('button[aria-label*="Resolver"]').click()
    }

    await expect(page.getByText(/3.*en cola|3.*queued/i)).toBeVisible()

    // Go online
    await page.context().setOffline(false)

    await expect(page.getByText(/3.*completadas|3.*completed/i)).toBeVisible({ timeout: 5000 })
  })

  test('handles rapid navigation without race conditions', async ({ page }) => {
    await page.goto('/projects')

    // Rapidly navigate
    for (let i = 0; i < 5; i++) {
      await page.goto('/projects/1?tab=alerts')
      await page.goto('/projects/1?tab=entities')
      await page.goto('/projects')
    }

    // Should not crash
    await expect(page.locator('.project-card').first()).toBeVisible()
  })
})
