import { test, expect } from '@playwright/test'
import { setupMockApi } from './support/mockApi'
import { prepareAppForE2E } from './support/app'

test.describe('E2E - Form Validation (Advanced)', () => {
  test.beforeEach(async ({ page }) => {
    await prepareAppForE2E(page)
    await setupMockApi(page)
  })

  test.describe('Project Creation Form', () => {
    test('validates required name field', async ({ page }) => {
      await page.goto('/projects')
      await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()

      // Try to submit without name
      await page.getByRole('button', { name: /Crear/i }).click()

      await expect(page.getByText(/nombre.*obligatorio|name.*required/i)).toBeVisible()
    })

    test('validates name minimum length (3 chars)', async ({ page }) => {
      await page.goto('/projects')
      await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()

      await page.getByLabel(/Nombre/i).fill('AB')
      await page.getByRole('button', { name: /Crear/i }).click()

      await expect(page.getByText(/mínimo 3 caracteres|at least 3/i)).toBeVisible()
    })

    test('validates name maximum length (100 chars)', async ({ page }) => {
      await page.goto('/projects')
      await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()

      const longName = 'A'.repeat(101)
      await page.getByLabel(/Nombre/i).fill(longName)

      // Should truncate or show error
      const value = await page.getByLabel(/Nombre/i).inputValue()
      expect(value.length).toBeLessThanOrEqual(100)

      await page.getByRole('button', { name: /Crear/i }).click()
      await expect(page.getByText(/máximo 100 caracteres|max 100/i)).toBeVisible()
    })

    test('validates name with only whitespace', async ({ page }) => {
      await page.goto('/projects')
      await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()

      await page.getByLabel(/Nombre/i).fill('   ')
      await page.getByRole('button', { name: /Crear/i }).click()

      await expect(page.getByText(/nombre.*obligatorio|cannot be empty/i)).toBeVisible()
    })

    test('sanitizes HTML in name field', async ({ page }) => {
      await page.goto('/projects')
      await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()

      await page.getByLabel(/Nombre/i).fill('<script>alert("XSS")</script>Proyecto')
      await page.locator('input[type="file"]').setInputFiles({
        name: 'test.txt',
        mimeType: 'text/plain',
        buffer: Buffer.from('Content')
      })
      await page.getByRole('button', { name: /Crear/i }).click()

      // Verify XSS is prevented
      await expect(page).toHaveURL(/\/projects\/\d+/)

      // Project name should be sanitized (no script tag execution)
      const alerts = await page.locator('text=alert("XSS")').count()
      expect(alerts).toBe(0)
    })

    test('validates special characters in name', async ({ page }) => {
      await page.goto('/projects')
      await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()

      // These should be allowed
      await page.getByLabel(/Nombre/i).fill('Proyecto: La Saga - Parte 1 (2024)')
      await page.locator('input[type="file"]').setInputFiles({
        name: 'test.txt',
        mimeType: 'text/plain',
        buffer: Buffer.from('Content')
      })
      await page.getByRole('button', { name: /Crear/i }).click()

      // Should succeed
      await expect(page).toHaveURL(/\/projects\/\d+/)
    })

    test('validates file upload required', async ({ page }) => {
      await page.goto('/projects')
      await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()

      await page.getByLabel(/Nombre/i).fill('Test Project')
      await page.getByRole('button', { name: /Crear/i }).click()

      await expect(page.getByText(/seleccionar.*archivo|file.*required/i)).toBeVisible()
    })

    test('validates file type (accepts .txt, .docx, .pdf, .epub)', async ({ page }) => {
      await page.goto('/projects')
      await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()

      await page.getByLabel(/Nombre/i).fill('Test')

      // Try invalid file type
      await page.locator('input[type="file"]').setInputFiles({
        name: 'script.js',
        mimeType: 'application/javascript',
        buffer: Buffer.from('alert(1)')
      })

      await expect(page.getByText(/tipo.*archivo.*válido|invalid file type/i)).toBeVisible()
    })

    test('validates file size maximum (100MB)', async ({ page }) => {
      await page.goto('/projects')
      await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()

      await page.getByLabel(/Nombre/i).fill('Test')

      // Try 120MB file
      await page.locator('input[type="file"]').setInputFiles({
        name: 'huge.txt',
        mimeType: 'text/plain',
        buffer: Buffer.alloc(120 * 1024 * 1024)
      })

      await expect(page.getByText(/archivo.*grande|exceeds.*100MB/i)).toBeVisible()
    })

    test('validates empty file', async ({ page }) => {
      await page.goto('/projects')
      await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()

      await page.getByLabel(/Nombre/i).fill('Test')

      await page.locator('input[type="file"]').setInputFiles({
        name: 'empty.txt',
        mimeType: 'text/plain',
        buffer: Buffer.alloc(0) // 0 bytes
      })

      await expect(page.getByText(/archivo.*vacío|file is empty/i)).toBeVisible()
    })

    test('validates file with virus (simulated)', async ({ page }) => {
      await setupMockApi(page, { virusDetected: true })

      await page.goto('/projects')
      await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()

      await page.getByLabel(/Nombre/i).fill('Test')
      await page.locator('input[type="file"]').setInputFiles({
        name: 'malware.txt',
        mimeType: 'text/plain',
        buffer: Buffer.from('EICAR test file')
      })
      await page.getByRole('button', { name: /Crear/i }).click()

      await expect(page.getByText(/archivo.*peligroso|malware detected/i)).toBeVisible()
    })

    test('shows inline validation on blur', async ({ page }) => {
      await page.goto('/projects')
      await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()

      const nameInput = page.getByLabel(/Nombre/i)

      // Type invalid, then blur
      await nameInput.fill('AB')
      await nameInput.blur()

      // Should show error immediately
      await expect(page.getByText(/mínimo 3/i)).toBeVisible()
    })

    test('clears validation error when input becomes valid', async ({ page }) => {
      await page.goto('/projects')
      await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()

      const nameInput = page.getByLabel(/Nombre/i)

      // Trigger error
      await nameInput.fill('AB')
      await nameInput.blur()
      await expect(page.getByText(/mínimo 3/i)).toBeVisible()

      // Fix error
      await nameInput.fill('ABC')
      await nameInput.blur()

      // Error should clear
      await expect(page.getByText(/mínimo 3/i)).not.toBeVisible()
    })

    test('disables submit button when form is invalid', async ({ page }) => {
      await page.goto('/projects')
      await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()

      const submitButton = page.getByRole('button', { name: /Crear/i })

      // Should be disabled initially
      await expect(submitButton).toBeDisabled()

      // Fill valid data
      await page.getByLabel(/Nombre/i).fill('Valid Project')
      await page.locator('input[type="file"]').setInputFiles({
        name: 'test.txt',
        mimeType: 'text/plain',
        buffer: Buffer.from('Content')
      })

      // Should enable
      await expect(submitButton).toBeEnabled()
    })
  })

  test.describe('Entity Edit Form', () => {
    test('validates entity name required', async ({ page }) => {
      await page.goto('/projects/1?tab=entities')

      await page.locator('.entity-item').first().click()

      const nameInput = page.getByLabel(/Nombre/i)
      await nameInput.clear()
      await page.getByRole('button', { name: /Guardar/i }).click()

      await expect(page.getByText(/nombre.*obligatorio/i)).toBeVisible()
    })

    test('validates entity name unique within type', async ({ page }) => {
      await page.goto('/projects/1?tab=entities')

      await page.locator('.entity-item').first().click()

      // Try to use name of another entity
      await page.getByLabel(/Nombre/i).fill('Existing Character Name')
      await page.getByRole('button', { name: /Guardar/i }).click()

      await expect(page.getByText(/nombre.*existe|already exists/i)).toBeVisible()
    })

    test('validates entity attributes format', async ({ page }) => {
      await page.goto('/projects/1?tab=entities')

      await page.locator('.entity-item').first().click()

      // Invalid age
      await page.getByLabel(/Edad/i).fill('-5')
      await page.getByRole('button', { name: /Guardar/i }).click()

      await expect(page.getByText(/edad.*válida|invalid age/i)).toBeVisible()
    })
  })

  test.describe('Collection Form', () => {
    test('validates collection name length', async ({ page }) => {
      await page.goto('/collections')

      await page.getByRole('button', { name: /Nueva Colección/i }).click()

      // Too short
      await page.getByLabel(/Nombre/i).fill('A')
      await page.getByRole('button', { name: /Crear/i }).click()

      await expect(page.getByText(/mínimo.*caracteres/i)).toBeVisible()
    })

    test('validates collection description max length (500 chars)', async ({ page }) => {
      await page.goto('/collections')

      await page.getByRole('button', { name: /Nueva Colección/i }).click()

      const longDesc = 'A'.repeat(501)
      await page.getByLabel(/Descripción/i).fill(longDesc)

      const value = await page.getByLabel(/Descripción/i).inputValue()
      expect(value.length).toBeLessThanOrEqual(500)
    })

    test('prevents HTML injection in description', async ({ page }) => {
      await page.goto('/collections')

      await page.getByRole('button', { name: /Nueva Colección/i }).click()

      await page.getByLabel(/Nombre/i).fill('Test Collection')
      await page.getByLabel(/Descripción/i).fill('<img src=x onerror=alert(1)>')
      await page.getByRole('button', { name: /Crear/i }).click()

      // Should not execute script
      const alerts = await page.locator('text=alert(1)').count()
      expect(alerts).toBe(0)
    })
  })

  test.describe('Settings Form', () => {
    test('validates numeric inputs (batch size)', async ({ page }) => {
      await page.goto('/settings')

      const batchInput = page.getByLabel(/Batch.*size|Tamaño de lote/i)
      await batchInput.fill('abc')

      // Should not accept non-numeric
      const value = await batchInput.inputValue()
      expect(value).toMatch(/^\d*$/)
    })

    test('validates batch size range (1-256)', async ({ page }) => {
      await page.goto('/settings')

      const batchInput = page.getByLabel(/Batch.*size/i)

      // Too small
      await batchInput.fill('0')
      await batchInput.blur()
      await expect(page.getByText(/mínimo 1|at least 1/i)).toBeVisible()

      // Too large
      await batchInput.fill('300')
      await batchInput.blur()
      await expect(page.getByText(/máximo 256|max 256/i)).toBeVisible()
    })

    test('validates Ollama host URL format', async ({ page }) => {
      await page.goto('/settings')

      const hostInput = page.getByLabel(/Ollama.*host|Host de Ollama/i)

      // Invalid URL
      await hostInput.fill('not-a-url')
      await hostInput.blur()

      await expect(page.getByText(/URL.*válida|valid URL/i)).toBeVisible()
    })

    test('validates Ollama host scheme (http/https only)', async ({ page }) => {
      await page.goto('/settings')

      const hostInput = page.getByLabel(/Ollama.*host/i)

      await hostInput.fill('ftp://localhost:11434')
      await hostInput.blur()

      await expect(page.getByText(/http.*https|protocolo inválido/i)).toBeVisible()
    })
  })

  test.describe('Real-time Validation', () => {
    test('validates as user types (debounced)', async ({ page }) => {
      await page.goto('/projects')
      await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()

      const nameInput = page.getByLabel(/Nombre/i)

      // Type slowly
      await nameInput.type('A')
      await page.waitForTimeout(500)
      await expect(page.getByText(/mínimo 3/i)).toBeVisible()

      await nameInput.type('BC')
      await page.waitForTimeout(500)
      await expect(page.getByText(/mínimo 3/i)).not.toBeVisible()
    })

    test('shows character counter for limited fields', async ({ page }) => {
      await page.goto('/collections')
      await page.getByRole('button', { name: /Nueva Colección/i }).click()

      const descInput = page.getByLabel(/Descripción/i)
      await descInput.fill('Test description')

      await expect(page.getByText(/\d+\/500/)).toBeVisible() // Character counter
    })

    test('updates counter in real-time', async ({ page }) => {
      await page.goto('/collections')
      await page.getByRole('button', { name: /Nueva Colección/i }).click()

      const descInput = page.getByLabel(/Descripción/i)

      await descInput.fill('A')
      await expect(page.getByText(/1\/500/)).toBeVisible()

      await descInput.fill('AB')
      await expect(page.getByText(/2\/500/)).toBeVisible()
    })

    test('turns counter red when approaching limit', async ({ page }) => {
      await page.goto('/collections')
      await page.getByRole('button', { name: /Nueva Colección/i }).click()

      const descInput = page.getByLabel(/Descripción/i)

      await descInput.fill('A'.repeat(490))

      const counter = page.locator('.char-counter')
      await expect(counter).toHaveClass(/warning|danger/)
    })
  })

  test.describe('Accessibility', () => {
    test('associates error messages with inputs via aria-describedby', async ({ page }) => {
      await page.goto('/projects')
      await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()

      await page.getByRole('button', { name: /Crear/i }).click()

      const nameInput = page.getByLabel(/Nombre/i)
      const describedBy = await nameInput.getAttribute('aria-describedby')
      expect(describedBy).toBeTruthy()

      const errorMessage = page.locator(`#${describedBy}`)
      await expect(errorMessage).toBeVisible()
    })

    test('marks invalid fields with aria-invalid', async ({ page }) => {
      await page.goto('/projects')
      await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()

      await page.getByRole('button', { name: /Crear/i }).click()

      const nameInput = page.getByLabel(/Nombre/i)
      await expect(nameInput).toHaveAttribute('aria-invalid', 'true')
    })

    test('announces validation errors to screen readers', async ({ page }) => {
      await page.goto('/projects')
      await page.getByRole('button', { name: /Nuevo Proyecto/i }).click()

      await page.getByRole('button', { name: /Crear/i }).click()

      const errorRegion = page.locator('[role="alert"]')
      await expect(errorRegion).toBeVisible()
    })
  })
})
