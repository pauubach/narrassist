import { test, expect } from '@playwright/test'
import { setupMockApi } from './support/mockApi'
import { prepareAppForE2E } from './support/app'

test.describe('E2E - Drag and Drop', () => {
  test.beforeEach(async ({ page }) => {
    await prepareAppForE2E(page)
    await setupMockApi(page)
  })

  test('reorders alerts via drag and drop', async ({ page }) => {
    await page.goto('/projects/1?tab=alerts')

    const firstAlert = page.locator('.alert-item[draggable="true"]').first()
    const secondAlert = page.locator('.alert-item[draggable="true"]').nth(1)

    const firstText = await firstAlert.textContent()

    await firstAlert.dragTo(secondAlert)

    const newSecondText = await page.locator('.alert-item').nth(1).textContent()
    expect(newSecondText).toBe(firstText)
  })

  test('reorders entities by dragging', async ({ page }) => {
    await page.goto('/projects/1?tab=entities')

    const first = page.locator('.entity-item[draggable="true"]').first()
    const third = page.locator('.entity-item[draggable="true"]').nth(2)

    await first.dragTo(third)

    const newThirdName = await page.locator('.entity-item').nth(2).locator('.entity-name').textContent()
    const originalFirstName = await first.locator('.entity-name').textContent()

    expect(newThirdName).toBe(originalFirstName)
  })

  test('uploads file via drag and drop', async ({ page }) => {
    await page.goto('/projects')
    await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()

    const dataTransfer = await page.evaluateHandle(() => new DataTransfer())

    await page.dispatchEvent('input[type="file"]', 'drop', { dataTransfer })

    await expect(page.getByText(/archivo seleccionado|file selected/i)).toBeVisible()
  })

  test('shows drop zone highlight on drag over', async ({ page }) => {
    await page.goto('/projects')
    await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()

    const dropzone = page.locator('.file-dropzone')

    await dropzone.dispatchEvent('dragenter')

    await expect(dropzone).toHaveClass(/drag-over|highlight/)
  })

  test('drag handle is keyboard accessible', async ({ page }) => {
    await page.goto('/projects/1?tab=alerts')

    const handle = page.locator('.drag-handle').first()
    await handle.focus()

    await expect(handle).toHaveAttribute('tabindex', '0')
  })
})
