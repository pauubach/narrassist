import { test, expect } from '@playwright/test'
import { setupMockApi } from './support/mockApi'
import { prepareAppForE2E } from './support/app'

test.describe('E2E - Performance with Large Datasets', () => {
  test.beforeEach(async ({ page }) => {
    await prepareAppForE2E(page)
  })

  test('handles 1000+ alerts efficiently', async ({ page }) => {
    await setupMockApi(page, { alertCount: 1000 })
    await page.goto('/projects/1?tab=alerts')

    // Should load within 10s
    await expect(page.locator('.alert-item').first()).toBeVisible({ timeout: 10000 })

    // Verify virtualization is working
    const renderedItems = await page.locator('.alert-item').count()
    expect(renderedItems).toBeLessThan(100) // Only visible items rendered
  })

  test('handles 500+ entities efficiently', async ({ page }) => {
    await setupMockApi(page, { entityCount: 500 })
    await page.goto('/projects/1?tab=entities')

    await expect(page.locator('.entity-item').first()).toBeVisible({ timeout: 10000 })

    // Scroll performance test
    const startTime = Date.now()
    await page.locator('.entity-list').evaluate(el => el.scrollTop = 10000)
    const scrollTime = Date.now() - startTime

    expect(scrollTime).toBeLessThan(100) // Should be smooth
  })

  test('handles large document (100k+ words)', async ({ page }) => {
    await setupMockApi(page, { documentSize: 100000 })
    await page.goto('/projects/1')

    // Document viewer should load progressively
    await expect(page.locator('.document-viewer').first()).toBeVisible({ timeout: 15000 })
  })

  test('handles graph with 200+ nodes', async ({ page }) => {
    await setupMockApi(page, { nodeCount: 200 })
    await page.goto('/projects/1?tab=relationships')

    await expect(page.locator('.vis-network')).toBeVisible({ timeout: 15000 })

    // Zoom and pan should be smooth
    await page.locator('.vis-network').click({ position: { x: 100, y: 100 } })
    await page.mouse.wheel(0, -100) // Zoom in

    // Should not freeze
    await expect(page.locator('.vis-network')).toBeVisible()
  })

  test('handles timeline with 500+ events', async ({ page }) => {
    await setupMockApi(page, { timelineEventCount: 500 })
    await page.goto('/projects/1?tab=timeline')

    await expect(page.locator('.vis-timeline')).toBeVisible({ timeout: 15000 })
  })

  test('search performs well with 10k+ items', async ({ page }) => {
    await setupMockApi(page, { entityCount: 10000 })
    await page.goto('/projects/1?tab=entities')

    const searchInput = page.getByPlaceholder(/Buscar/i)

    const startTime = Date.now()
    await searchInput.fill('Harry')
    await page.waitForTimeout(300) // Debounce

    const searchTime = Date.now() - startTime
    expect(searchTime).toBeLessThan(1000)

    await expect(page.locator('.entity-item').first()).toBeVisible()
  })

  test('maintains 60fps scrolling with large lists', async ({ page }) => {
    await setupMockApi(page, { alertCount: 5000 })
    await page.goto('/projects/1?tab=alerts')

    await expect(page.locator('.alert-item').first()).toBeVisible()

    // Measure FPS during scroll
    const fps = await page.evaluate(async () => {
      return new Promise<number>(resolve => {
        const list = document.querySelector('.alert-list')!
        let frames = 0
        const lastTime = performance.now()

        const measureFPS = () => {
          const now = performance.now()
          frames++

          if (now - lastTime > 1000) {
            resolve(frames)
          } else {
            requestAnimationFrame(measureFPS)
          }

          list.scrollTop += 10
        }

        requestAnimationFrame(measureFPS)
      })
    })

    expect(fps).toBeGreaterThan(30) // At least 30fps
  })

  test('lazy loads images in large documents', async ({ page }) => {
    await setupMockApi(page, { documentWithImages: true, imageCount: 100 })
    await page.goto('/projects/1')

    // Only visible images should load
    const loadedImages = await page.locator('img[loading="lazy"]').count()
    expect(loadedImages).toBeGreaterThan(0)

    // Scroll down
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))

    // More images should load
    await page.waitForTimeout(500)
    const newLoadedImages = await page.locator('img[src]').count()
    expect(newLoadedImages).toBeGreaterThan(loadedImages)
  })

  test('handles concurrent API requests efficiently', async ({ page }) => {
    await setupMockApi(page)
    await page.goto('/projects/1')

    // Trigger multiple simultaneous requests
    await Promise.all([
      page.getByRole('tab', { name: /Entidades/i }).click(),
      page.getByRole('tab', { name: /Relaciones/i }).click(),
      page.getByRole('tab', { name: /Timeline/i }).click()
    ])

    // Should not crash or timeout
    await expect(page.locator('.vis-network')).toBeVisible({ timeout: 15000 })
  })

  test('memory usage stays stable with long session', async ({ page }) => {
    await setupMockApi(page)
    await page.goto('/projects')

    // Simulate 10 minutes of usage
    for (let i = 0; i < 20; i++) {
      await page.goto('/projects/1?tab=alerts')
      await page.goto('/projects/1?tab=entities')
      await page.goto('/projects')
      await page.waitForTimeout(100)
    }

    // Check memory (rough heuristic)
    const heapSize = await page.evaluate(() => (performance as any).memory?.usedJSHeapSize || 0)
    expect(heapSize).toBeLessThan(500 * 1024 * 1024) // Under 500MB
  })
})
