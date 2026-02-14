import { test, expect } from '@playwright/test'
import { setupMockApi } from './support/mockApi'
import { prepareAppForE2E, openAssistantPanel } from './support/app'

test.describe('E2E Comprehensive Workflow (Normal Flow)', () => {
  test.beforeEach(async ({ page }) => {
    await prepareAppForE2E(page)
    await setupMockApi(page)
  })

  test('shows projects list and supports search', async ({ page }) => {
    await page.goto('/projects')

    await expect(page.getByRole('heading', { name: 'Proyectos' })).toBeVisible()
    await expect(page.locator('.project-card')).toHaveCount(2)

    const search = page.getByPlaceholder('Buscar proyectos...')
    await search.fill('Principal')

    await expect(page.locator('.project-card')).toHaveCount(1)
    await expect(page.getByText('Proyecto E2E Principal')).toBeVisible()
  })

  test('creates a new project with validation and redirects to detail', async ({ page }) => {
    await page.goto('/projects')

    await page.getByRole('button', { name: 'Nuevo Proyecto' }).click()
    await page.getByRole('button', { name: 'Crear y Analizar' }).click()

    await expect(page.getByText('El nombre es obligatorio')).toBeVisible()
    await expect(page.getByText('Debes seleccionar un archivo')).toBeVisible()

    await page.getByLabel('Nombre del proyecto *').fill('Proyecto validado E2E')
    await page.locator('input[type="file"]').setInputFiles({
      name: 'manuscrito.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('Capítulo 1\nTexto de prueba para flujo E2E.', 'utf-8'),
    })

    await page.getByRole('button', { name: 'Crear y Analizar' }).click()

    await expect(page).toHaveURL(/\/projects\/\d+/)
    await expect(page.getByRole('heading', { name: /Proyecto \d+/ })).toBeVisible()

    const match = page.url().match(/\/projects\/(\d+)/)
    expect(match).not.toBeNull()
    const newProjectId = Number(match?.[1] ?? 0)
    expect(newProjectId).toBeGreaterThan(0)

    await page.getByRole('button', { name: /Volver a proyectos|Proyectos/i }).first().click()
    await expect(page).toHaveURL(/\/projects$/)

    const search = page.getByPlaceholder('Buscar proyectos...')
    const projectName = `Proyecto ${newProjectId}`
    await search.fill(projectName)

    await expect(page.locator('.project-card')).toHaveCount(1)
    await expect(page.getByText(projectName)).toBeVisible()
  })

  test('navigates workspace tabs and uses assistant chat', async ({ page }) => {
    await page.goto('/projects/1')

    await expect(page.getByRole('heading', { name: 'Proyecto E2E Principal' })).toBeVisible()

    await page.getByRole('tab', { name: /Entidades/i }).click()
    await expect(page.getByText('Juan Pérez').first()).toBeVisible()

    await page.getByRole('tab', { name: /Alertas|Revisión/i }).click()
    await expect(page.locator('.alerts-tab .alert-item').first()).toBeVisible()

    await openAssistantPanel(page)
    const chatInput = page.getByPlaceholder('Escribe tu pregunta...')
    await chatInput.fill('¿Cuántas veces aparece Juan?')
    await chatInput.press('Enter')

    await expect(page.getByText('¿Cuántas veces aparece Juan?').first()).toBeVisible()
    await expect(page.getByText('Respuesta simulada para:')).toBeVisible()

    await page.locator('.assistant-panel .clear-btn').click()
    await expect(page.getByText('Pregunta sobre tu manuscrito')).toBeVisible()
  })

  test('resolves alerts from alert tab and refreshes list', async ({ page }) => {
    await page.goto('/projects/1?tab=alerts')

    await expect(page.locator('.alerts-tab')).toBeVisible()
    const alerts = page.locator('.alert-item')
    await expect(alerts).toHaveCount(2)

    const firstAlert = alerts.first()
    await firstAlert.locator('button').filter({ has: page.locator('.pi-check') }).click()

    await expect(alerts).toHaveCount(1)
  })
})
