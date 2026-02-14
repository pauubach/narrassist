import type { Page } from '@playwright/test'

export async function prepareAppForE2E(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem('narrative_assistant_tutorial_completed', 'true')
    sessionStorage.setItem('narrative_assistant_tutorial_shown', 'true')
    localStorage.setItem('narrative_assistant_theme', 'light')

    // Evitar residuos de runs anteriores.
    for (const key of Object.keys(localStorage)) {
      if (key.startsWith('chat_history_')) localStorage.removeItem(key)
    }
  })
}

export async function openAssistantPanel(page: Page) {
  const setupDialog = page.getByRole('dialog', { name: /Configuración inicial|Narrative Assistant/i })
  if (await setupDialog.count()) {
    await setupDialog.first().waitFor({ state: 'hidden', timeout: 10_000 }).catch(() => undefined)
  }

  await page.getByRole('tablist', { name: /Secciones del workspace/i }).first()
    .waitFor({ state: 'visible', timeout: 20_000 })

  const textTab = page.getByRole('tab', { name: /Texto/i })
  if (await textTab.count()) {
    await textTab.first().click()
  }

  const triggers = [
    page.locator('.sidebar-tab-btn[aria-label="Asistente"]').first(),
    page.getByRole('tab', { name: /Asistente/i }).first(),
    page.getByRole('button', { name: /Asistente/i }).first(),
  ]

  for (const trigger of triggers) {
    if (await trigger.count()) {
      try {
        await trigger.click({ timeout: 3_000 })
        return
      } catch {
        // Intentamos siguiente trigger disponible.
      }
    }
  }

  throw new Error('Assistant trigger not found in UI')
}
