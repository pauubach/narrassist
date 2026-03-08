import { test, expect } from '@playwright/test'
import { setupMockApi } from './support/mockApi'
import { prepareAppForE2E } from './support/app'

test.describe('E2E - Exportación e importación editorial', () => {
  test.beforeEach(async ({ page }) => {
    await prepareAppForE2E(page)
    await setupMockApi(page)
  })

  test('exporta documento con preview y trabajo editorial .narrassist', async ({ page }) => {
    await page.goto('/projects/1')

    await expect(page.getByRole('heading', { name: 'Proyecto E2E Principal' })).toBeVisible()
    await page.getByTestId('open-export-dialog').click()

    const exportDialog = page.getByRole('dialog', { name: /Exportar - Proyecto E2E Principal/i })
    await expect(exportDialog).toBeVisible()

    await exportDialog.getByTestId('document-preview-button').click()
    await expect(exportDialog.getByText(/Páginas estimadas:/i)).toBeVisible()
    await expect(exportDialog.getByText(/18 págs\./i)).toBeVisible()

    const documentDownloadPromise = page.waitForEvent('download')
    await exportDialog.getByTestId('document-export-button').click()
    const documentDownload = await documentDownloadPromise

    expect(documentDownload.suggestedFilename()).toMatch(/informe_Proyecto_1\.docx/i)
    await expect(page.getByText(/Documento exportado como/i)).toBeVisible()

    const editorialDownloadPromise = page.waitForEvent('download')
    await exportDialog.getByTestId('editorial-export-button').click()
    const editorialDownload = await editorialDownloadPromise

    expect(editorialDownload.suggestedFilename()).toMatch(/trabajo_editorial_proyecto_1\.narrassist/i)
    await expect(page.getByText(/Trabajo editorial exportado/i)).toBeVisible()
  })

  test('importa trabajo editorial con preview y confirmación', async ({ page }) => {
    await page.goto('/projects/1')

    await page.getByTestId('open-export-dialog').click()
    const exportDialog = page.getByRole('dialog', { name: /Exportar - Proyecto E2E Principal/i })
    await exportDialog.getByTestId('editorial-import-button').click()

    const importDialog = page.getByRole('dialog', { name: /Importar Trabajo Editorial/i })
    await expect(importDialog).toBeVisible()

    await importDialog.locator('input[type=\"file\"]').setInputFiles({
      name: 'flujo-editorial.narrassist',
      mimeType: 'application/octet-stream',
      buffer: Buffer.from('mock editorial import package', 'utf-8'),
    })

    await importDialog.getByTestId('import-preview-button').click()

    await expect(importDialog.getByText(/Resumen de importacion/i)).toBeVisible()
    await expect(importDialog.getByText(/7 cambios a aplicar/i)).toBeVisible()

    await importDialog.getByTestId('import-confirm-button').click()

    await expect(importDialog.getByText(/Importacion completada/i)).toBeVisible()
    await expect(importDialog.getByText(/2 fusiones aplicadas/i)).toBeVisible()
    await expect(page.getByText(/El trabajo editorial se ha importado correctamente/i)).toBeVisible()
  })

  test('muestra error claro si falla el preview de importación', async ({ page }) => {
    await page.route('**/api/projects/1/import-work/preview', async route => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'El archivo editorial está dañado' }),
      })
    })

    await page.goto('/projects/1')

    await page.getByTestId('open-export-dialog').click()
    const exportDialog = page.getByRole('dialog', { name: /Exportar - Proyecto E2E Principal/i })
    await exportDialog.getByTestId('editorial-import-button').click()

    const importDialog = page.getByRole('dialog', { name: /Importar Trabajo Editorial/i })
    await importDialog.locator('input[type=\"file\"]').setInputFiles({
      name: 'flujo-editorial-roto.narrassist',
      mimeType: 'application/octet-stream',
      buffer: Buffer.from('broken import package', 'utf-8'),
    })

    await importDialog.getByTestId('import-preview-button').click()

    await expect(page.getByText(/El archivo editorial está dañado/i)).toBeVisible()
    await expect(importDialog.getByText(/Resumen de importacion/i)).toHaveCount(0)
  })
})
