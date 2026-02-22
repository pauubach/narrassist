import { test, expect } from '@playwright/test'
import { setupMockApi } from './support/mockApi'
import { prepareAppForE2E } from './support/app'

test.describe('E2E - Keyboard Shortcuts (Complete)', () => {
  test.beforeEach(async ({ page }) => {
    await prepareAppForE2E(page)
    await setupMockApi(page)
  })

  test('Ctrl+S saves current state', async ({ page }) => {
    await page.goto('/projects/1?tab=entities')
    await page.locator('.entity-item').first().click()
    await page.getByLabel(/Nombre/i).fill('Modified Name')

    await page.keyboard.press('Control+S')

    await expect(page.getByText(/Guardado|Saved/i)).toBeVisible()
  })

  test('Ctrl+Z undoes last action', async ({ page }) => {
    await page.goto('/projects/1?tab=alerts')
    await page.locator('.alert-item').first().locator('button[aria-label*="Resolver"]').click()

    await page.keyboard.press('Control+Z')

    // Alert should be back to pending
    await expect(page.locator('.alert-item').first()).toHaveAttribute('data-status', 'pending')
  })

  test('Ctrl+Shift+Z redoes action', async ({ page }) => {
    await page.goto('/projects/1?tab=alerts')
    await page.locator('.alert-item').first().locator('button[aria-label*="Resolver"]').click()
    await page.keyboard.press('Control+Z') // Undo

    await page.keyboard.press('Control+Shift+Z') // Redo

    await expect(page.locator('.alert-item').first()).toHaveAttribute('data-status', 'resolved')
  })

  test('Ctrl+F opens search', async ({ page }) => {
    await page.goto('/projects/1')

    await page.keyboard.press('Control+F')

    await expect(page.locator('.search-bar')).toBeVisible()
    await expect(page.locator('.search-bar input')).toBeFocused()
  })

  test('Ctrl+/ shows keyboard shortcuts panel', async ({ page }) => {
    await page.goto('/projects/1')

    await page.keyboard.press('Control+/')

    await expect(page.getByRole('dialog', { name: /Atajos de teclado|Keyboard shortcuts/i })).toBeVisible()
  })

  test('Alt+P navigates to projects', async ({ page }) => {
    await page.goto('/settings')

    await page.keyboard.press('Alt+P')

    await expect(page).toHaveURL('/projects')
  })

  test('Alt+C opens configuration', async ({ page }) => {
    await page.goto('/projects')

    await page.keyboard.press('Alt+C')

    await expect(page).toHaveURL('/settings')
  })

  test('F1 opens help', async ({ page }) => {
    await page.goto('/projects')

    await page.keyboard.press('F1')

    await expect(page.locator('.help-dialog')).toBeVisible()
  })

  test('Escape closes dialogs', async ({ page }) => {
    await page.goto('/projects')
    await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()

    await page.keyboard.press('Escape')

    await expect(page.locator('.p-dialog')).not.toBeVisible()
  })

  test('Arrow keys navigate list items', async ({ page }) => {
    await page.goto('/projects/1?tab=alerts')

    await page.locator('.alert-item').first().focus()
    await page.keyboard.press('ArrowDown')

    const secondItem = page.locator('.alert-item').nth(1)
    await expect(secondItem).toBeFocused()
  })

  test('Enter activates focused button', async ({ page }) => {
    await page.goto('/projects')

    await page.getByRole('button', { name: /Nuevo Proyecto/i }).focus()
    await page.keyboard.press('Enter')

    await expect(page.locator('.p-dialog')).toBeVisible()
  })

  test('Space activates checkboxes', async ({ page }) => {
    await page.goto('/projects/1?tab=alerts')

    const checkbox = page.locator('.alert-item input[type="checkbox"]').first()
    await checkbox.focus()
    await page.keyboard.press('Space')

    await expect(checkbox).toBeChecked()
  })

  test('Tab cycles through focusable elements', async ({ page }) => {
    await page.goto('/projects')

    await page.keyboard.press('Tab')
    const first = await page.evaluate(() => document.activeElement?.tagName)

    await page.keyboard.press('Tab')
    const second = await page.evaluate(() => document.activeElement?.tagName)

    expect(first).not.toBe(second)
  })

  test('Shift+Tab cycles backwards', async ({ page }) => {
    await page.goto('/projects')

    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    const forward = await page.evaluate(() => document.activeElement?.tagName)

    await page.keyboard.press('Shift+Tab')
    const backward = await page.evaluate(() => document.activeElement?.tagName)

    expect(forward).not.toBe(backward)
  })

  test('Ctrl+A selects all alerts', async ({ page }) => {
    await page.goto('/projects/1?tab=alerts')

    await page.keyboard.press('Control+A')

    const allCheckboxes = await page.locator('.alert-item input[type="checkbox"]').count()
    const checkedCheckboxes = await page.locator('.alert-item input[type="checkbox"]:checked').count()

    expect(checkedCheckboxes).toBe(allCheckboxes)
  })

  test('Delete key removes selected items', async ({ page }) => {
    await page.goto('/projects/1?tab=entities')

    await page.locator('.entity-item').first().click()
    await page.keyboard.press('Delete')

    await expect(page.getByText(/¿Estás seguro.*eliminar/i)).toBeVisible()
  })

  test('Ctrl+E exports current view', async ({ page }) => {
    await page.goto('/projects/1?tab=alerts')

    const downloadPromise = page.waitForEvent('download')
    await page.keyboard.press('Control+E')

    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/alerts.*\.json/)
  })

  test('PageUp/PageDown scroll pages', async ({ page }) => {
    await page.goto('/projects/1?tab=alerts')

    await page.keyboard.press('PageDown')
    await page.waitForTimeout(100)

    const scrollTop = await page.evaluate(() => document.querySelector('.alert-list')?.scrollTop || 0)
    expect(scrollTop).toBeGreaterThan(0)
  })

  test('Home/End jump to start/end', async ({ page }) => {
    await page.goto('/projects/1?tab=alerts')

    await page.keyboard.press('End')
    const endScroll = await page.evaluate(() => document.querySelector('.alert-list')?.scrollTop || 0)

    await page.keyboard.press('Home')
    const homeScroll = await page.evaluate(() => document.querySelector('.alert-list')?.scrollTop || 0)

    expect(endScroll).toBeGreaterThan(homeScroll)
  })
})
