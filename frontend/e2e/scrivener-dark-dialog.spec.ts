import { test, expect } from '@playwright/test'

/**
 * Test para inspeccionar estilos del diálogo en Scrivener Dark mode
 */
test.describe('Scrivener Dark Theme - Dialog Inspection', () => {
  test('Inspect New Project Dialog styles in Scrivener Dark', async ({ page }) => {
    // Navegar a la página principal
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(2000)

    // Cerrar cualquier diálogo que esté abierto
    const closeDialogButtons = page.locator('.p-dialog-header-close, button:has-text("Cerrar"), button:has-text("Comenzar"), button:has-text("OK")')
    for (let attempt = 0; attempt < 3; attempt++) {
      const closeBtn = closeDialogButtons.first()
      if (await closeBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await closeBtn.click()
        await page.waitForTimeout(500)
      } else {
        break
      }
    }

    // Configurar el tema via localStorage
    await page.evaluate(() => {
      localStorage.setItem('narrative_assistant_theme_preset', 'scrivener')
      localStorage.setItem('narrative_assistant_theme', 'dark')
    })

    // Recargar para aplicar el tema
    await page.reload()
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(1000)

    // Cerrar diálogos de nuevo después del reload
    for (let attempt = 0; attempt < 3; attempt++) {
      const closeBtn = closeDialogButtons.first()
      if (await closeBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await closeBtn.click()
        await page.waitForTimeout(500)
      } else {
        break
      }
    }

    // Añadir clase manualmente si no está aplicada
    await page.evaluate(() => {
      document.documentElement.classList.add('scrivener-theme', 'dark')
    })

    await page.waitForTimeout(500)

    // Verificar que no hay diálogo modal bloqueando
    const modalMask = page.locator('.p-dialog-mask')
    const maskVisible = await modalMask.isVisible({ timeout: 1000 }).catch(() => false)
    if (maskVisible) {
      await page.keyboard.press('Escape')
      await page.waitForTimeout(500)
    }

    // Abrir diálogo de nuevo proyecto
    const newProjectBtn = page.locator('button:has-text("Nuevo Proyecto")').first()
    const btnVisible = await newProjectBtn.isVisible({ timeout: 5000 }).catch(() => false)

    if (btnVisible) {
      await newProjectBtn.click({ force: true })
      await page.waitForTimeout(1500)
    }

    // Buscar el diálogo
    const dialog = page.locator('.p-dialog').first()
    const dialogVisible = await dialog.isVisible({ timeout: 5000 }).catch(() => false)

    if (dialogVisible) {
      console.log('Dialog is visible')

      // Inspeccionar footer
      const footer = dialog.locator('.p-dialog-footer').first()
      if (await footer.isVisible()) {
        const cancelBtn = footer.locator('button').first()

        // Obtener las reglas CSS que aplican al botón
        const cssInfo = await cancelBtn.evaluate(el => {
          const styles = window.getComputedStyle(el)

          // Buscar qué regla CSS está ganando
          let matchingRules: string[] = []
          try {
            const sheets = document.styleSheets
            for (let i = 0; i < sheets.length; i++) {
              try {
                const rules = sheets[i].cssRules
                for (let j = 0; j < rules.length; j++) {
                  const rule = rules[j] as CSSStyleRule
                  if (rule.selectorText && el.matches(rule.selectorText)) {
                    if (rule.style.color) {
                      matchingRules.push(`${rule.selectorText} -> color: ${rule.style.color}`)
                    }
                  }
                }
              } catch (e) {
                // CORS issues with external stylesheets
              }
            }
          } catch (e) {
            matchingRules.push('Error getting rules: ' + e)
          }

          return {
            computedColor: styles.color,
            inlineStyle: el.getAttribute('style'),
            matchingColorRules: matchingRules.slice(-10) // Last 10 matching rules
          }
        })

        console.log('Cancel button CSS info:')
        console.log('  Computed color:', cssInfo.computedColor)
        console.log('  Inline style:', cssInfo.inlineStyle)
        console.log('  Matching color rules:', cssInfo.matchingColorRules)
      }

      // Tomar screenshot
      await page.screenshot({ path: 'test-results/scrivener-dark-dialog-inspection.png', fullPage: true })
      console.log('\nScreenshot saved')
    }
  })
})
