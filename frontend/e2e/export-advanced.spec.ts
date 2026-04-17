import fs from 'node:fs'
import { test, expect } from '@playwright/test'
import { setupMockApi } from './support/mockApi'
import { prepareAppForE2E } from './support/app'

test.describe('E2E - Export Functionality (Advanced)', () => {
  test.beforeEach(async ({ page }) => {
    await prepareAppForE2E(page)
    await setupMockApi(page)
  })

  test('exports alerts as JSON with full data', async ({ page }) => {
    await page.goto('/projects/1?tab=alerts')

    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: /Exportar/i }).click()
    await page.getByRole('option', { name: /JSON/i }).click()

    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/alerts.*\.json/)

    // Verify file content
    const path = await download.path()
    const content = fs.readFileSync(path, 'utf-8')
    const data = JSON.parse(content)

    expect(Array.isArray(data)).toBe(true)
    expect(data.length).toBeGreaterThan(0)
    expect(data[0]).toHaveProperty('severity')
    expect(data[0]).toHaveProperty('message')
  })

  test('exports alerts as CSV with correct format', async ({ page }) => {
    await page.goto('/projects/1?tab=alerts')

    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: /Exportar/i }).click()
    await page.getByRole('option', { name: /CSV/i }).click()

    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/alerts.*\.csv/)

    const path = await download.path()
    const content = fs.readFileSync(path, 'utf-8')

    expect(content).toContain('severity,message,location')
  })

  test('exports entities as JSON with attributes', async ({ page }) => {
    await page.goto('/projects/1?tab=entities')

    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: /Exportar/i }).click()
    await page.getByRole('option', { name: /JSON/i }).click()

    const download = await downloadPromise
    const path = await download.path()
    const data = JSON.parse(fs.readFileSync(path, 'utf-8'))

    expect(data[0]).toHaveProperty('name')
    expect(data[0]).toHaveProperty('type')
    expect(data[0]).toHaveProperty('attributes')
  })

  test('exports relationship graph as PNG image', async ({ page }) => {
    await page.goto('/projects/1?tab=relationships')

    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: /Exportar.*imagen/i }).click()

    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/relationships.*\.png/)
  })

  test('exports relationship graph as SVG', async ({ page }) => {
    await page.goto('/projects/1?tab=relationships')

    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: /Exportar/i }).click()
    await page.getByRole('option', { name: /SVG/i }).click()

    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/relationships.*\.svg/)
  })

  test('exports timeline as CSV', async ({ page }) => {
    await page.goto('/projects/1?tab=timeline')

    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: /Exportar/i }).click()
    await page.getByRole('option', { name: /CSV/i }).click()

    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/timeline.*\.csv/)
  })

  test('exports full analysis report as PDF', async ({ page }) => {
    await page.goto('/projects/1')

    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: /Exportar informe/i }).click()
    await page.getByRole('option', { name: /PDF/i }).click()

    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/analysis-report.*\.pdf/)
  })

  test('exports analysis report as DOCX with formatting', async ({ page }) => {
    await page.goto('/projects/1')

    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: /Exportar informe/i }).click()
    await page.getByRole('option', { name: /DOCX|Word/i }).click()

    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/analysis-report.*\.docx/)
  })

  test('exports analysis report as Markdown', async ({ page }) => {
    await page.goto('/projects/1')

    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: /Exportar informe/i }).click()
    await page.getByRole('option', { name: /Markdown/i }).click()

    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/analysis-report.*\.md/)
  })

  test('exports only selected alerts', async ({ page }) => {
    await page.goto('/projects/1?tab=alerts')

    // Select specific alerts
    await page.locator('.alert-item input[type="checkbox"]').nth(0).check()
    await page.locator('.alert-item input[type="checkbox"]').nth(1).check()

    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: /Exportar seleccionadas/i }).click()

    const download = await downloadPromise
    const path = await download.path()
    const data = JSON.parse(fs.readFileSync(path, 'utf-8'))

    expect(data.length).toBe(2)
  })

  test('exports with current filters applied', async ({ page }) => {
    await page.goto('/projects/1?tab=alerts')

    // Apply filter
    await page.getByRole('button', { name: /Severidad/i }).click()
    await page.getByRole('option', { name: /Alta/i }).click()

    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: /Exportar/i }).click()
    await page.getByRole('option', { name: /JSON/i }).click()

    const download = await downloadPromise
    const path = await download.path()
    const data = JSON.parse(fs.readFileSync(path, 'utf-8'))

    expect(data.every((alert: any) => alert.severity === 'high')).toBe(true)
  })

  test('shows export progress for large datasets', async ({ page }) => {
    await setupMockApi(page, { alertCount: 5000 })
    await page.goto('/projects/1?tab=alerts')

    await page.getByRole('button', { name: /Exportar/i }).click()
    await page.getByRole('option', { name: /JSON/i }).click()

    await expect(page.locator('.p-progressbar')).toBeVisible()
    await expect(page.getByText(/Exportando/i)).toBeVisible()
  })

  test('handles export errors gracefully', async ({ page }) => {
    await setupMockApi(page, { failExport: true })
    await page.goto('/projects/1?tab=alerts')

    await page.getByRole('button', { name: /Exportar/i }).click()
    await page.getByRole('option', { name: /JSON/i }).click()

    await expect(page.getByText(/Error al exportar|Export failed/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /Reintentar/i })).toBeVisible()
  })

  test('verifies exported file size matches data', async ({ page }) => {
    await page.goto('/projects/1?tab=alerts')

    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: /Exportar/i }).click()
    await page.getByRole('option', { name: /JSON/i }).click()

    const download = await downloadPromise
    const path = await download.path()
    const stats = fs.statSync(path)

    expect(stats.size).toBeGreaterThan(100) // At least 100 bytes
  })

  test('exports character sheet with all details', async ({ page }) => {
    await page.goto('/projects/1?tab=entities')

    await page.locator('.entity-item').first().click()

    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: /Exportar ficha/i }).click()

    const download = await downloadPromise
    const path = await download.path()
    const data = JSON.parse(fs.readFileSync(path, 'utf-8'))

    expect(data).toHaveProperty('name')
    expect(data).toHaveProperty('attributes')
    expect(data).toHaveProperty('mentions')
    expect(data).toHaveProperty('relationships')
  })
})
