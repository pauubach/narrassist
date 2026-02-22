import { test, expect } from '@playwright/test'
import { setupMockApi } from './support/mockApi'
import { prepareAppForE2E } from './support/app'

const VIEWPORTS = {
  mobile: { width: 375, height: 667 },
  mobileLandscape: { width: 667, height: 375 },
  tablet: { width: 768, height: 1024 },
  tabletLandscape: { width: 1024, height: 768 },
  desktop: { width: 1920, height: 1080 }
}

test.describe('E2E - Responsive Design (Complete)', () => {
  test.beforeEach(async ({ page }) => {
    await prepareAppForE2E(page)
    await setupMockApi(page)
  })

  for (const [name, viewport] of Object.entries(VIEWPORTS)) {
    test(`renders correctly on ${name}`, async ({ page }) => {
      await page.setViewportSize(viewport)
      await page.goto('/projects')

      await expect(page.locator('body')).toBeVisible()
      await expect(page.locator('.project-card').first()).toBeVisible()
    })
  }

  test('sidebar collapses on mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile)
    await page.goto('/projects/1?tab=alerts')

    await page.locator('.alert-item').first().click()

    const sidebar = page.locator('.alert-sidebar')
    await expect(sidebar).toHaveCSS('position', /absolute|fixed/)
  })

  test('navigation becomes hamburger menu on mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile)
    await page.goto('/projects')

    await expect(page.getByRole('button', { name: /Menu|Menú/i })).toBeVisible()
  })

  test('touch gestures work on mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile)
    await page.goto('/projects/1?tab=alerts')

    // Swipe to dismiss alert sidebar
    const sidebar = page.locator('.alert-sidebar')
    await sidebar.hover()
    await page.mouse.down()
    await page.mouse.move(300, 0)
    await page.mouse.up()

    await expect(sidebar).not.toBeVisible()
  })

  test('handles orientation change', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile)
    await page.goto('/projects/1')

    // Rotate to landscape
    await page.setViewportSize(VIEWPORTS.mobileLandscape)

    await expect(page.locator('.project-detail')).toBeVisible()
  })

  test('pinch zoom disabled on mobile', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.mobile)
    await page.goto('/projects')

    const metaViewport = await page.locator('meta[name="viewport"]').getAttribute('content')
    expect(metaViewport).toContain('user-scalable=no')
  })

  test('breakpoints apply correctly', async ({ page }) => {
    await page.setViewportSize(VIEWPORTS.tablet)
    await page.goto('/projects/1?tab=alerts')

    const grid = page.locator('.alert-grid')
    const gridTemplateColumns = await grid.evaluate(el =>
      window.getComputedStyle(el).gridTemplateColumns
    )

    expect(gridTemplateColumns).not.toBe('1fr') // Should be multi-column on tablet
  })
})
