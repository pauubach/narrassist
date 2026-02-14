import { test, expect, type Page } from '@playwright/test'
import { setupMockApi, type MockApiOptions } from './support/mockApi'
import { prepareAppForE2E, openAssistantPanel } from './support/app'

async function bootstrap(page: Page, options: MockApiOptions = {}) {
  await prepareAppForE2E(page)
  await setupMockApi(page, options)
}

function envInt(name: string, fallback: number): number {
  const raw = process.env[name]
  if (!raw) return fallback
  const parsed = Number(raw)
  if (!Number.isFinite(parsed) || parsed <= 0) return fallback
  return Math.floor(parsed)
}

const LARGE_PROJECT_COUNT = Math.max(3, envInt('E2E_LARGE_PROJECT_COUNT', 120))
const LARGE_PROJECT_TIMEOUT_MS = envInt('E2E_LARGE_PROJECT_TIMEOUT_MS', 90_000)

test.describe('E2E Extreme Cases', () => {
  test('shows API error and recovers on retry', async ({ page }) => {
    await bootstrap(page, { failProjectsOnce: true })
    await page.goto('/projects')

    await expect(page.getByText(/Fallo simulado al listar proyectos|HTTP 500/i)).toBeVisible()
    await page.getByRole('button', { name: 'Reintentar' }).click()

    await expect(page.getByRole('heading', { name: 'Proyectos' })).toBeVisible()
    await expect(page.locator('.project-card').first()).toBeVisible()
  })

  test('handles malformed project id and allows returning to projects', async ({ page }) => {
    await bootstrap(page)
    await page.goto('/projects/abc')

    await expect(page.getByText(/ID de proyecto inválido|Error cargando proyecto/i)).toBeVisible()
    await page.getByRole('button', { name: 'Volver a Proyectos' }).click()
    await expect(page).toHaveURL(/\/projects$/)
  })

  test('runs analysis-required flow for relationships tab', async ({ page }) => {
    await bootstrap(page, {
      executedPhasesOverride: {
        1: {
          coreference: false,
          relationships: false,
        },
      },
    })

    await page.goto('/projects/1')
    await page.getByRole('tab', { name: /Relaciones/i }).click()

    await expect(page.getByText('Análisis no ejecutado')).toBeVisible()
    await page.getByRole('button', { name: 'Ejecutar análisis completo' }).click()

    await expect(page.getByText('Análisis no ejecutado')).toBeHidden()
    await expect(page.locator('.relationship-graph')).toBeVisible()
  })

  test('shows fallback message when LLM returns no response for long prompt', async ({ page }) => {
    await bootstrap(page, { chatFailureTrigger: 'SIN_RESPUESTA' })
    await page.goto('/projects/1')
    await expect(page.getByRole('heading', { name: 'Proyecto E2E Principal' })).toBeVisible()

    await openAssistantPanel(page)
    const input = page.getByPlaceholder('Escribe tu pregunta...')

    const longMessage = `${'Analiza este contexto y dame un resumen detallado. '.repeat(35)} SIN_RESPUESTA`
    await input.fill(longMessage)
    await input.press('Enter')

    await expect(page.getByText('El LLM no generó una respuesta').first()).toBeVisible()
  })

  test('supports large projects list and filtering', async ({ page }) => {
    test.setTimeout(LARGE_PROJECT_TIMEOUT_MS)
    await bootstrap(page, { projectCount: LARGE_PROJECT_COUNT })
    await page.goto('/projects')

    await expect(page.locator('.project-card')).toHaveCount(LARGE_PROJECT_COUNT)

    const targetId = Math.max(3, Math.min(LARGE_PROJECT_COUNT, 119))
    const paddedId = targetId.toString().padStart(3, '0')
    const search = page.getByPlaceholder('Buscar proyectos...')
    await search.fill(`Carga ${paddedId}`)
    await expect(page.locator('.project-card')).toHaveCount(1)
    await expect(page.getByText(`Proyecto Carga ${paddedId}`)).toBeVisible()
  })
})
