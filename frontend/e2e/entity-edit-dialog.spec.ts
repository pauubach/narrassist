import { test, expect } from '@playwright/test'

/**
 * Test para verificar estilos del diálogo de edición de entidad en Scrivener Dark
 */
test.describe('Entity Edit Dialog - Scrivener Dark', () => {
  test('Check SelectButton and Chips styling', async ({ page }) => {
    // Configurar tema Scrivener dark
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')

    // Cerrar diálogos iniciales
    for (let i = 0; i < 3; i++) {
      const closeBtn = page.locator('.p-dialog-header-close, button:has-text("Cerrar"), button:has-text("Comenzar")').first()
      if (await closeBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
        await closeBtn.click()
        await page.waitForTimeout(300)
      }
    }

    // Aplicar tema
    await page.evaluate(() => {
      localStorage.setItem('narrative_assistant_theme_preset', 'scrivener')
      localStorage.setItem('narrative_assistant_theme', 'dark')
      document.documentElement.classList.add('scrivener-theme', 'dark')
    })

    await page.reload()
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(1000)

    // Cerrar diálogos después del reload
    for (let i = 0; i < 3; i++) {
      const closeBtn = page.locator('.p-dialog-header-close, button:has-text("Cerrar"), button:has-text("Comenzar")').first()
      if (await closeBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
        await closeBtn.click()
        await page.waitForTimeout(300)
      }
    }

    await page.evaluate(() => {
      document.documentElement.classList.add('scrivener-theme', 'dark')
    })

    // Ir a un proyecto (si hay alguno)
    const projectCard = page.locator('.project-card').first()
    if (await projectCard.isVisible({ timeout: 3000 }).catch(() => false)) {
      await projectCard.click()
      await page.waitForTimeout(2000)

      // Ir a la pestaña de entidades
      const entitiesTab = page.locator('text=Entidades').first()
      if (await entitiesTab.isVisible({ timeout: 2000 }).catch(() => false)) {
        await entitiesTab.click()
        await page.waitForTimeout(1000)

        // Buscar una entidad para editar
        const entityRow = page.locator('.entity-row, .entity-item, tr').first()
        if (await entityRow.isVisible({ timeout: 2000 }).catch(() => false)) {
          // Click derecho o buscar botón de editar
          const editBtn = entityRow.locator('button[aria-label="Editar"], button:has(i.pi-pencil)').first()
          if (await editBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
            await editBtn.click()
            await page.waitForTimeout(1000)
          }
        }
      }
    }

    // Si no hay proyecto, crear uno con el diálogo de nuevo proyecto para ver el estilo
    const newProjectBtn = page.locator('button:has-text("Nuevo Proyecto")').first()
    if (await newProjectBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await newProjectBtn.click()
      await page.waitForTimeout(1000)
    }

    // Tomar screenshot del estado actual
    await page.screenshot({
      path: 'test-results/entity-edit-dialog-scrivener.png',
      fullPage: true
    })

    // Inspeccionar SelectButton si existe
    const selectButton = page.locator('.p-selectbutton').first()
    if (await selectButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      const btnStyles = await selectButton.locator('.p-button').first().evaluate(el => {
        const styles = window.getComputedStyle(el)
        return {
          backgroundColor: styles.backgroundColor,
          borderColor: styles.borderColor,
          color: styles.color,
        }
      })
      console.log('SelectButton styles:', btnStyles)
    }

    // Inspeccionar Chips si existe
    const chips = page.locator('.p-chips').first()
    if (await chips.isVisible({ timeout: 2000 }).catch(() => false)) {
      const chipsStyles = await chips.evaluate(el => {
        const container = el.querySelector('.p-chips-multiple-container')
        if (container) {
          const styles = window.getComputedStyle(container)
          return {
            backgroundColor: styles.backgroundColor,
            borderColor: styles.borderColor,
          }
        }
        return null
      })
      console.log('Chips styles:', chipsStyles)
    }
  })
})
