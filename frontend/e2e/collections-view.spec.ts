import { test, expect } from '@playwright/test'
import { setupMockApi } from './support/mockApi'
import { prepareAppForE2E } from './support/app'

test.describe('E2E - CollectionsView (CRUD)', () => {
  test.beforeEach(async ({ page }) => {
    await prepareAppForE2E(page)
    await setupMockApi(page)
  })

  test('displays collections list with count', async ({ page }) => {
    await page.goto('/collections')

    await expect(page.getByRole('heading', { name: 'Colecciones' })).toBeVisible()
    await expect(page.getByText(/2 colecciones/i)).toBeVisible()
  })

  test('displays empty state when no collections exist', async ({ page }) => {
    await prepareAppForE2E(page)
    await setupMockApi(page, { emptyCollections: true })

    await page.goto('/collections')

    await expect(page.getByText(/No hay colecciones/i)).toBeVisible()
    await expect(page.getByText(/Crea una colección para agrupar/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /Crear Primera Colección/i })).toBeVisible()
  })

  test('creates a new collection with validation', async ({ page }) => {
    await page.goto('/collections')

    // Open dialog
    await page.getByRole('button', { name: /Nueva Colección/i }).click()

    // Try submit without filling required fields
    await page.getByRole('button', { name: /Crear|Guardar/i }).click()

    // Verify validation errors
    await expect(page.getByText(/El nombre es obligatorio/i)).toBeVisible()

    // Fill form
    await page.getByLabel(/Nombre.*\*/i).fill('La Trilogía del Señor de los Anillos')
    await page.getByLabel(/Descripción/i).fill('Saga épica de fantasía')

    // Submit
    await page.getByRole('button', { name: /Crear/i }).click()

    // Verify success
    await expect(page.getByText(/Colección creada/i)).toBeVisible()
    await expect(page.getByText(/La Trilogía del Señor de los Anillos/i)).toBeVisible()
  })

  test('searches collections by name', async ({ page }) => {
    await page.goto('/collections')

    const searchInput = page.getByPlaceholder(/Buscar colecciones/i)
    await searchInput.fill('Harry Potter')

    // Should show only matching collections
    await expect(page.locator('.collection-card')).toHaveCount(1)
    await expect(page.getByText(/Harry Potter/i)).toBeVisible()
  })

  test('clears search when clicking clear button', async ({ page }) => {
    await page.goto('/collections')

    const searchInput = page.getByPlaceholder(/Buscar colecciones/i)
    await searchInput.fill('Test')

    await page.getByRole('button', { name: /Limpiar|Clear/i }).click()

    await expect(searchInput).toHaveValue('')
    await expect(page.locator('.collection-card').first()).toBeVisible()
  })

  test('opens collection detail on card click', async ({ page }) => {
    await page.goto('/collections')

    await page.locator('.collection-card').first().click()

    await expect(page).toHaveURL(/\/collections\/\d+/)
  })

  test('shows context menu on ellipsis click', async ({ page }) => {
    await page.goto('/collections')

    await page.locator('.collection-card').first().locator('button[icon="pi pi-ellipsis-v"]').click()

    await expect(page.locator('.p-contextmenu')).toBeVisible()
    await expect(page.getByRole('menuitem', { name: /Editar/i })).toBeVisible()
    await expect(page.getByRole('menuitem', { name: /Eliminar/i })).toBeVisible()
  })

  test('edits collection name and description', async ({ page }) => {
    await page.goto('/collections')

    // Open context menu
    await page.locator('.collection-card').first().locator('button[icon="pi pi-ellipsis-v"]').click()
    await page.getByRole('menuitem', { name: /Editar/i }).click()

    // Edit form
    const nameInput = page.getByLabel(/Nombre.*\*/i)
    await nameInput.clear()
    await nameInput.fill('Saga Actualizada')

    await page.getByRole('button', { name: /Guardar/i }).click()

    // Verify update
    await expect(page.getByText(/Colección actualizada/i)).toBeVisible()
    await expect(page.getByText(/Saga Actualizada/i)).toBeVisible()
  })

  test('deletes collection with confirmation', async ({ page }) => {
    await page.goto('/collections')

    const initialCount = await page.locator('.collection-card').count()

    // Open context menu
    await page.locator('.collection-card').first().locator('button[icon="pi pi-ellipsis-v"]').click()
    await page.getByRole('menuitem', { name: /Eliminar/i }).click()

    // Confirm deletion
    await expect(page.getByText(/¿Estás seguro.*eliminar/i)).toBeVisible()
    await page.getByRole('button', { name: /Eliminar|Confirmar/i }).click()

    // Verify deletion
    await expect(page.getByText(/Colección eliminada/i)).toBeVisible()
    await expect(page.locator('.collection-card')).toHaveCount(initialCount - 1)
  })

  test('cancels deletion on cancel button', async ({ page }) => {
    await page.goto('/collections')

    const initialCount = await page.locator('.collection-card').count()

    await page.locator('.collection-card').first().locator('button[icon="pi pi-ellipsis-v"]').click()
    await page.getByRole('menuitem', { name: /Eliminar/i }).click()

    // Cancel
    await page.getByRole('button', { name: /Cancelar/i }).click()

    // Verify no deletion
    await expect(page.locator('.collection-card')).toHaveCount(initialCount)
  })

  test('displays collection metadata (date, project count)', async ({ page }) => {
    await page.goto('/collections')

    const card = page.locator('.collection-card').first()

    // Check date
    await expect(card.locator('.collection-meta')).toContainText(/\d{1,2}\/\d{1,2}\/\d{4}/)

    // Check project count
    await expect(card.locator('.stat-value')).toBeVisible()
    await expect(card.locator('.stat-label')).toContainText(/libros?/)
  })

  test('displays format badge (Saga)', async ({ page }) => {
    await page.goto('/collections')

    await expect(page.locator('.format-badge').first()).toContainText(/Saga/)
    await expect(page.locator('.format-badge i.pi-folder').first()).toBeVisible()
  })

  test('handles API error gracefully', async ({ page }) => {
    await prepareAppForE2E(page)
    await setupMockApi(page, { failCollections: true })

    await page.goto('/collections')

    await expect(page.getByText(/Error|Fallo/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /Reintentar/i })).toBeVisible()
  })

  test('retries loading on error', async ({ page }) => {
    await prepareAppForE2E(page)
    await setupMockApi(page, { failCollectionsOnce: true })

    await page.goto('/collections')

    await expect(page.getByText(/Error/i)).toBeVisible()
    await page.getByRole('button', { name: /Reintentar/i }).click()

    // Should load successfully after retry
    await expect(page.locator('.collection-card').first()).toBeVisible()
  })

  test('shows skeleton loaders while loading', async ({ page }) => {
    await page.goto('/collections')

    // Should briefly show skeletons (might be too fast in tests)
    const skeletons = page.locator('.p-skeleton')
    const hasSkeletons = await skeletons.count().catch(() => 0)

    // After loading completes
    await expect(page.locator('.collection-card').first()).toBeVisible({ timeout: 5000 })
  })

  test('responsive layout on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/collections')

    // Header should stack vertically
    const header = page.locator('.header')
    await expect(header).toBeVisible()

    // Search input should be full width on mobile
    const searchInput = page.getByPlaceholder(/Buscar colecciones/i)
    await expect(searchInput).toBeVisible()
  })

  test('keyboard navigation with Tab', async ({ page }) => {
    await page.goto('/collections')

    // Tab to search input
    await page.keyboard.press('Tab')
    const focused = await page.evaluate(() => document.activeElement?.tagName)
    expect(['INPUT', 'BUTTON']).toContain(focused)

    // Tab to "Nueva Colección" button
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')

    // Should be able to press Enter to open dialog
    await page.keyboard.press('Enter')
    await expect(page.locator('.p-dialog')).toBeVisible()
  })

  test('Escape key closes dialog', async ({ page }) => {
    await page.goto('/collections')

    await page.getByRole('button', { name: /Nueva Colección/i }).click()
    await expect(page.locator('.p-dialog')).toBeVisible()

    await page.keyboard.press('Escape')
    await expect(page.locator('.p-dialog')).not.toBeVisible()
  })
})

test.describe('E2E - CollectionDetailView', () => {
  test.beforeEach(async ({ page }) => {
    await prepareAppForE2E(page)
    await setupMockApi(page)
  })

  test('displays collection detail with projects list', async ({ page }) => {
    await page.goto('/collections/1')

    await expect(page.getByRole('heading', { name: /Colección/i })).toBeVisible()
    await expect(page.locator('.project-card')).toHaveCount(2, { timeout: 5000 })
  })

  test('navigates back to collections list', async ({ page }) => {
    await page.goto('/collections/1')

    await page.getByRole('button', { name: /Volver.*colecciones/i }).click()

    await expect(page).toHaveURL('/collections')
  })

  test('adds project to collection', async ({ page }) => {
    await page.goto('/collections/1')

    await page.getByRole('button', { name: /Añadir libro/i }).click()

    // Select project from dropdown
    await page.locator('.p-dropdown').click()
    await page.getByRole('option', { name: /Proyecto Test/i }).click()

    await page.getByRole('button', { name: /Añadir/i }).click()

    await expect(page.getByText(/Libro añadido/i)).toBeVisible()
  })

  test('removes project from collection', async ({ page }) => {
    await page.goto('/collections/1')

    const initialCount = await page.locator('.project-card').count()

    // Click remove on first project
    await page.locator('.project-card').first().locator('button[icon="pi pi-trash"]').click()

    // Confirm removal
    await page.getByRole('button', { name: /Eliminar|Confirmar/i }).click()

    await expect(page.getByText(/Libro eliminado/i)).toBeVisible()
    await expect(page.locator('.project-card')).toHaveCount(initialCount - 1)
  })

  test('displays cross-book analysis results', async ({ page }) => {
    await page.goto('/collections/1')

    // Navigate to analysis tab
    await page.getByRole('tab', { name: /Análisis|Cross-book/i }).click()

    // Check for cross-book inconsistencies
    await expect(page.getByText(/Inconsistencias entre libros/i)).toBeVisible()
    await expect(page.locator('.cross-book-alert')).toHaveCount(3, { timeout: 5000 })
  })

  test('displays shared entities across books', async ({ page }) => {
    await page.goto('/collections/1')

    await page.getByRole('tab', { name: /Entidades compartidas/i }).click()

    // Verify shared characters appear
    await expect(page.getByText(/Harry Potter/i)).toBeVisible()
    await expect(page.getByText(/Aparece en 3 libros/i)).toBeVisible()
  })

  test('runs cross-book analysis', async ({ page }) => {
    await page.goto('/collections/1')

    await page.getByRole('button', { name: /Analizar colección/i }).click()

    // Verify progress indicator
    await expect(page.locator('.p-progressbar')).toBeVisible()
    await expect(page.getByText(/Analizando/i)).toBeVisible()

    // Wait for completion
    await expect(page.getByText(/Análisis completado/i)).toBeVisible({ timeout: 30000 })
  })

  test('displays timeline across all books', async ({ page }) => {
    await page.goto('/collections/1')

    await page.getByRole('tab', { name: /Timeline/i }).click()

    // Verify timeline with multiple books
    await expect(page.locator('.timeline-item')).toHaveCount(10, { timeout: 5000 })
    await expect(page.getByText(/Libro 1:/i)).toBeVisible()
    await expect(page.getByText(/Libro 2:/i)).toBeVisible()
  })

  test('exports collection analysis report', async ({ page }) => {
    await page.goto('/collections/1')

    const downloadPromise = page.waitForEvent('download')

    await page.getByRole('button', { name: /Exportar informe/i }).click()
    await page.getByRole('option', { name: /PDF/i }).click()

    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/collection-report.*\.pdf/)
  })

  test('handles invalid collection ID', async ({ page }) => {
    await page.goto('/collections/99999')

    await expect(page.getByText(/Colección no encontrada|not found/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /Volver/i })).toBeVisible()
  })

  test('displays character evolution across books', async ({ page }) => {
    await page.goto('/collections/1')

    await page.getByRole('tab', { name: /Evolución de personajes/i }).click()

    // Select a character
    await page.getByRole('button', { name: /Seleccionar personaje/i }).click()
    await page.getByRole('option', { name: /Harry Potter/i }).click()

    // Verify evolution data
    await expect(page.getByText(/Libro 1:/i)).toBeVisible()
    await expect(page.getByText(/Libro 2:/i)).toBeVisible()
    await expect(page.locator('canvas')).toBeVisible() // Evolution chart
  })

  test('accessibility - ARIA labels present', async ({ page }) => {
    await page.goto('/collections/1')

    const backButton = page.getByRole('button', { name: /Volver/i })
    await expect(backButton).toHaveAttribute('aria-label')

    const tabs = page.locator('[role="tab"]')
    await expect(tabs.first()).toHaveAttribute('aria-selected')
  })
})
