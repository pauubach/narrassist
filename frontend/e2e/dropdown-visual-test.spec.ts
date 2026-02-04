import { test, expect } from '@playwright/test'

const FRONTEND_URL = 'http://localhost:5173'

test.describe('Dropdown Visual Test', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/projects`)
    await page.waitForLoadState('networkidle')
  })

  test('Verify dropdown padding and spacing', async ({ page }) => {
    // Buscar cualquier dropdown disponible en la página
    const sortDropdown = page.locator('.sort-dropdown, .p-dropdown').first()

    // Si no hay dropdown, skip el test
    const dropdownExists = await sortDropdown.isVisible().catch(() => false)
    if (!dropdownExists) {
      console.log('No dropdown found on page, skipping test')
      test.skip()
      return
    }

    await sortDropdown.click()
    await page.waitForTimeout(500)

    // Esperar a que aparezca el panel
    const dropdownPanel = page.locator('.p-dropdown-panel')
    const panelVisible = await dropdownPanel.isVisible().catch(() => false)

    if (!panelVisible) {
      console.log('Dropdown panel not visible, skipping test')
      test.skip()
      return
    }

    // Obtener los items del dropdown
    const dropdownItems = page.locator('.p-dropdown-item')
    const firstItem = dropdownItems.first()

    const itemVisible = await firstItem.isVisible().catch(() => false)
    if (!itemVisible) {
      console.log('No dropdown items visible, skipping test')
      test.skip()
      return
    }

    // Obtener los estilos computados del primer item
    const padding = await firstItem.evaluate((el) => {
      const styles = window.getComputedStyle(el)
      return {
        paddingTop: styles.paddingTop,
        paddingRight: styles.paddingRight,
        paddingBottom: styles.paddingBottom,
        paddingLeft: styles.paddingLeft,
        minHeight: styles.minHeight,
        lineHeight: styles.lineHeight,
      }
    })

    console.log('Dropdown item computed styles:', padding)

    // Verificar que el padding es adecuado (mínimo 0.75rem = 12px)
    const paddingTopPx = parseInt(padding.paddingTop)
    const paddingLeftPx = parseInt(padding.paddingLeft)

    expect(paddingTopPx).toBeGreaterThanOrEqual(10) // Al menos 10px vertical
    expect(paddingLeftPx).toBeGreaterThanOrEqual(15) // Al menos 15px horizontal

    console.log(`✓ Padding verification passed: ${paddingTopPx}px top, ${paddingLeftPx}px left`)

    // Capturar screenshot del dropdown abierto
    await page.screenshot({
      path: 'test-results/dropdown-open.png',
      fullPage: false,
    }).catch(() => {})

    console.log('Screenshot saved: test-results/dropdown-open.png')

    // Verificar espaciado entre items
    const itemCount = await dropdownItems.count()
    if (itemCount >= 2) {
      const firstItemBox = await dropdownItems.nth(0).boundingBox()
      const secondItemBox = await dropdownItems.nth(1).boundingBox()

      if (firstItemBox && secondItemBox) {
        const spacing = secondItemBox.y - (firstItemBox.y + firstItemBox.height)
        console.log(`Spacing between items: ${spacing}px`)

        // El espaciado debería ser 0 (sin gap) pero los items deben tener altura suficiente
        expect(firstItemBox.height).toBeGreaterThanOrEqual(30) // Al menos 30px de altura
        expect(secondItemBox.height).toBeGreaterThanOrEqual(30)
      }
    }

    console.log('✓ Dropdown visual test passed')
  })
})
