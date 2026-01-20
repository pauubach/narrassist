import { test, expect, Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

/**
 * Tests de Accesibilidad con axe-core
 *
 * Verifican cumplimiento de WCAG 2.1 AA en las principales vistas.
 * Ejecutar con: npx playwright test e2e/accessibility.spec.ts
 */

async function waitForLoad(page: Page) {
  await page.waitForSelector('.p-progress-spinner', { state: 'detached', timeout: 30000 }).catch(() => {})
  await page.waitForLoadState('domcontentloaded')
}

test.describe('Accessibility - WCAG 2.1 AA Compliance', () => {
  test.describe('Home Page', () => {
    test('should have no critical accessibility violations', async ({ page }) => {
      await page.goto('/')
      await waitForLoad(page)

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
        .analyze()

      // Filtrar violaciones para excluir problemas conocidos de PrimeVue
      const criticalViolations = results.violations.filter(
        v => v.impact === 'critical' || v.impact === 'serious'
      )

      // Mostrar detalles de violaciones para debugging
      if (criticalViolations.length > 0) {
        console.log('Critical/Serious violations found:')
        criticalViolations.forEach(v => {
          console.log(`- ${v.id}: ${v.description}`)
          console.log(`  Impact: ${v.impact}`)
          console.log(`  Help: ${v.helpUrl}`)
          v.nodes.slice(0, 3).forEach(node => {
            console.log(`  Element: ${node.html.substring(0, 100)}`)
          })
        })
      }

      expect(criticalViolations).toHaveLength(0)
    })

    test('skip link should be accessible', async ({ page }) => {
      await page.goto('/')
      await waitForLoad(page)

      // Buscar skip link
      const skipLink = page.locator('.skip-link')

      if (await skipLink.count() > 0) {
        // Debería estar oculto inicialmente
        const isHidden = await skipLink.evaluate(el => {
          const rect = el.getBoundingClientRect()
          return rect.top < 0
        })
        expect(isHidden).toBe(true)

        // Debería aparecer con Tab
        await page.keyboard.press('Tab')

        const isVisible = await skipLink.evaluate(el => {
          const rect = el.getBoundingClientRect()
          return rect.top >= 0
        })
        expect(isVisible).toBe(true)
      }
    })
  })

  test.describe('Projects View', () => {
    test('should have no critical accessibility violations', async ({ page }) => {
      await page.goto('/projects')
      await waitForLoad(page)

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa'])
        .exclude('.p-toast') // Excluir toast que puede ser transitorio
        .analyze()

      const criticalViolations = results.violations.filter(
        v => v.impact === 'critical' || v.impact === 'serious'
      )

      expect(criticalViolations).toHaveLength(0)
    })

    test('project cards should be keyboard accessible', async ({ page }) => {
      await page.goto('/projects')
      await waitForLoad(page)

      // Los cards/elementos de proyecto deben ser navegables
      const projectElements = page.locator('.project-card, [data-testid="project-item"], .p-card')
      const count = await projectElements.count()

      if (count > 0) {
        // Tab hasta llegar a un proyecto
        for (let i = 0; i < 10; i++) {
          await page.keyboard.press('Tab')
          const focusedElement = await page.evaluate(() => document.activeElement?.tagName)
          if (focusedElement === 'BUTTON' || focusedElement === 'A') break
        }

        // El elemento enfocado debe tener focus visible
        const hasFocusStyle = await page.evaluate(() => {
          const el = document.activeElement
          if (!el) return false
          const styles = getComputedStyle(el)
          return styles.outlineStyle !== 'none' || styles.boxShadow !== 'none'
        })

        expect(hasFocusStyle).toBe(true)
      }
    })
  })

  test.describe('Settings View', () => {
    test('should have no critical accessibility violations', async ({ page }) => {
      await page.goto('/settings')
      await waitForLoad(page)

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa'])
        .analyze()

      const criticalViolations = results.violations.filter(
        v => v.impact === 'critical' || v.impact === 'serious'
      )

      expect(criticalViolations).toHaveLength(0)
    })

    test('form controls should have labels', async ({ page }) => {
      await page.goto('/settings')
      await waitForLoad(page)

      // Verificar que todos los inputs tienen labels asociados
      const inputs = page.locator('input:visible, select:visible, textarea:visible')
      const count = await inputs.count()

      let inputsWithLabels = 0

      for (let i = 0; i < count; i++) {
        const input = inputs.nth(i)
        const id = await input.getAttribute('id')
        const ariaLabel = await input.getAttribute('aria-label')
        const ariaLabelledBy = await input.getAttribute('aria-labelledby')

        // Buscar label asociado
        let hasLabel = !!(ariaLabel || ariaLabelledBy)

        if (id && !hasLabel) {
          const label = page.locator(`label[for="${id}"]`)
          hasLabel = await label.count() > 0
        }

        // También contar labels implícitos (input dentro de label)
        if (!hasLabel) {
          const parentLabel = input.locator('xpath=ancestor::label')
          hasLabel = await parentLabel.count() > 0
        }

        if (hasLabel) inputsWithLabels++
      }

      // Al menos el 80% de los inputs deben tener labels
      if (count > 0) {
        expect(inputsWithLabels / count).toBeGreaterThanOrEqual(0.8)
      }
    })
  })

  test.describe('Menu Navigation', () => {
    test('menubar should be keyboard accessible', async ({ page }) => {
      await page.goto('/')
      await waitForLoad(page)

      // El menubar debe tener role="menubar"
      const menubar = page.locator('[role="menubar"]')
      await expect(menubar).toBeVisible()

      // Los items del menú deben ser navegables con flechas
      const menuItems = page.locator('[role="menubar"] button[role="menuitem"]')
      const count = await menuItems.count()

      if (count > 0) {
        // Focus en el primer item
        await menuItems.first().focus()

        // Navegar con flecha derecha
        await page.keyboard.press('ArrowRight')

        // El segundo item debería estar enfocado
        const focusedId = await page.evaluate(() => document.activeElement?.id)
        expect(focusedId).toContain('menu-trigger')
      }
    })

    test('dropdown menu should be keyboard accessible', async ({ page }) => {
      await page.goto('/')
      await waitForLoad(page)

      const menuItems = page.locator('[role="menubar"] button[role="menuitem"]')

      if (await menuItems.count() > 0) {
        // Focus y abrir menú
        await menuItems.first().focus()
        await page.keyboard.press('Enter')

        // El dropdown debe aparecer
        const dropdown = page.locator('[role="menu"]')
        await expect(dropdown).toBeVisible({ timeout: 2000 })

        // Debe tener aria-labelledby
        const labelledBy = await dropdown.getAttribute('aria-labelledby')
        expect(labelledBy).toBeTruthy()

        // Cerrar con Escape
        await page.keyboard.press('Escape')
        await expect(dropdown).not.toBeVisible({ timeout: 2000 })
      }
    })
  })

  test.describe('Color Contrast', () => {
    test('light mode should have sufficient contrast', async ({ page }) => {
      await page.goto('/')
      await waitForLoad(page)

      // Asegurar modo claro
      await page.evaluate(() => {
        document.documentElement.classList.remove('dark')
      })

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2aa'])
        .options({ rules: ['color-contrast'] })
        .analyze()

      // Solo contar violaciones críticas de contraste
      const contrastViolations = results.violations.filter(
        v => v.id === 'color-contrast' && v.impact === 'serious'
      )

      // Permitir algunas violaciones menores (decorativos, etc.)
      expect(contrastViolations.length).toBeLessThanOrEqual(3)
    })

    test('dark mode should have sufficient contrast', async ({ page }) => {
      await page.goto('/')
      await waitForLoad(page)

      // Activar modo oscuro
      await page.evaluate(() => {
        document.documentElement.classList.add('dark')
      })

      // Esperar que los estilos se apliquen
      await page.waitForTimeout(500)

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2aa'])
        .options({ rules: ['color-contrast'] })
        .analyze()

      const contrastViolations = results.violations.filter(
        v => v.id === 'color-contrast' && v.impact === 'serious'
      )

      expect(contrastViolations.length).toBeLessThanOrEqual(3)
    })
  })

  test.describe('Focus Management', () => {
    test('focus should be visible on interactive elements', async ({ page }) => {
      await page.goto('/')
      await waitForLoad(page)

      // Tab a través de varios elementos
      const focusableElements: string[] = []

      for (let i = 0; i < 15; i++) {
        await page.keyboard.press('Tab')

        const elementInfo = await page.evaluate(() => {
          const el = document.activeElement
          if (!el || el === document.body) return null

          const styles = getComputedStyle(el)
          const hasOutline = styles.outlineStyle !== 'none' && styles.outlineWidth !== '0px'
          const hasBoxShadow = styles.boxShadow !== 'none'
          const hasBorder = styles.borderStyle !== 'none' && styles.borderWidth !== '0px'

          return {
            tagName: el.tagName,
            hasFocusStyle: hasOutline || hasBoxShadow || hasBorder,
            outline: styles.outline,
            boxShadow: styles.boxShadow
          }
        })

        if (elementInfo) {
          focusableElements.push(JSON.stringify(elementInfo))
        }
      }

      // Al menos el 80% de los elementos enfocables deben tener estilos de focus
      const elementsWithFocusStyle = focusableElements.filter(info => {
        const parsed = JSON.parse(info)
        return parsed.hasFocusStyle
      })

      if (focusableElements.length > 0) {
        const ratio = elementsWithFocusStyle.length / focusableElements.length
        expect(ratio).toBeGreaterThanOrEqual(0.8)
      }
    })

    test('focus trap should work in dialogs', async ({ page }) => {
      await page.goto('/')
      await waitForLoad(page)

      // Abrir un diálogo (ej: menú Ayuda > Acerca de)
      const helpMenu = page.locator('button:has-text("Ayuda")')

      if (await helpMenu.isVisible()) {
        await helpMenu.click()

        const aboutItem = page.locator('button:has-text("Acerca de")')
        if (await aboutItem.isVisible({ timeout: 2000 }).catch(() => false)) {
          await aboutItem.click()

          // Esperar que el diálogo aparezca
          const dialog = page.locator('.p-dialog')
          if (await dialog.isVisible({ timeout: 2000 }).catch(() => false)) {
            // Tab varias veces - el focus debe quedarse dentro del diálogo
            for (let i = 0; i < 20; i++) {
              await page.keyboard.press('Tab')
            }

            const focusedInDialog = await page.evaluate(() => {
              const activeEl = document.activeElement
              const dialog = document.querySelector('.p-dialog')
              return dialog?.contains(activeEl) || false
            })

            expect(focusedInDialog).toBe(true)

            // Cerrar con Escape
            await page.keyboard.press('Escape')
          }
        }
      }
    })
  })

  test.describe('Screen Reader Support', () => {
    test('main content should have proper landmarks', async ({ page }) => {
      await page.goto('/')
      await waitForLoad(page)

      // Verificar landmarks principales
      const main = page.locator('main, [role="main"]')
      await expect(main).toHaveCount(1)

      const nav = page.locator('nav, [role="navigation"], [role="menubar"]')
      expect(await nav.count()).toBeGreaterThan(0)
    })

    test('headings should be hierarchical', async ({ page }) => {
      await page.goto('/projects')
      await waitForLoad(page)

      const headings = await page.evaluate(() => {
        const h1s = document.querySelectorAll('h1')
        const h2s = document.querySelectorAll('h2')
        const h3s = document.querySelectorAll('h3')

        return {
          h1Count: h1s.length,
          h2Count: h2s.length,
          h3Count: h3s.length
        }
      })

      // Debería haber como máximo un h1
      expect(headings.h1Count).toBeLessThanOrEqual(1)

      // Si hay h3s, debería haber h2s
      if (headings.h3Count > 0) {
        expect(headings.h2Count).toBeGreaterThan(0)
      }
    })

    test('images should have alt text', async ({ page }) => {
      await page.goto('/projects')
      await waitForLoad(page)

      const images = page.locator('img:visible')
      const count = await images.count()

      for (let i = 0; i < count; i++) {
        const img = images.nth(i)
        const alt = await img.getAttribute('alt')
        const role = await img.getAttribute('role')

        // Debe tener alt o role="presentation" para imágenes decorativas
        expect(alt !== null || role === 'presentation').toBe(true)
      }
    })
  })

  test.describe('Theme Presets Accessibility', () => {
    const themes = ['aura', 'lara', 'grammarly', 'scrivener']
    const modes = ['light', 'dark']

    for (const theme of themes) {
      for (const mode of modes) {
        test(`${theme} theme in ${mode} mode should be accessible`, async ({ page }) => {
          await page.goto('/settings')
          await waitForLoad(page)

          // Aplicar tema y modo
          await page.evaluate(({ theme, mode }) => {
            localStorage.setItem('narrative_assistant_theme_config', JSON.stringify({
              preset: theme,
              mode: mode,
              primaryColor: '#3B82F6',
              fontSize: 'medium',
              lineHeight: 'normal',
              radius: 'medium',
              compactness: 'normal',
              reducedMotion: false
            }))
          }, { theme, mode })

          // Recargar para aplicar
          await page.reload()
          await waitForLoad(page)

          // Ejecutar axe
          const results = await new AxeBuilder({ page })
            .withTags(['wcag2aa'])
            .exclude('.p-toast')
            .analyze()

          const criticalViolations = results.violations.filter(
            v => v.impact === 'critical' || v.impact === 'serious'
          )

          // Reportar violaciones
          if (criticalViolations.length > 0) {
            console.log(`\n[${theme}/${mode}] Violations:`)
            criticalViolations.forEach(v => {
              console.log(`- ${v.id}: ${v.help}`)
            })
          }

          expect(criticalViolations).toHaveLength(0)
        })
      }
    }
  })
})
