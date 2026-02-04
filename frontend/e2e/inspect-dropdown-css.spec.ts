import { test } from '@playwright/test'

const FRONTEND_URL = 'http://localhost:5173'

test('Inspect dropdown CSS', async ({ page }) => {
  await page.goto(`${FRONTEND_URL}/projects`)
  await page.waitForLoadState('networkidle')

  // Abrir el dropdown
  const sortDropdown = page.locator('.sort-dropdown')
  await sortDropdown.click()
  await page.waitForTimeout(500)

  // Obtener el primer item
  const dropdownItem = page.locator('.p-dropdown-item').first()
  await dropdownItem.waitFor({ state: 'visible' })

  // Obtener TODOS los estilos aplicados incluyendo los que tienen !important
  const cssInfo = await dropdownItem.evaluate((el) => {
    const styles = window.getComputedStyle(el)

    // Obtener todas las reglas CSS que afectan a este elemento
    const rules: any[] = []
    const sheets = Array.from(document.styleSheets)

    sheets.forEach((sheet) => {
      try {
        const cssRules = Array.from(sheet.cssRules || [])
        cssRules.forEach((rule: any) => {
          if (rule.style && el.matches(rule.selectorText)) {
            rules.push({
              selector: rule.selectorText,
              padding: rule.style.padding,
              paddingTop: rule.style.paddingTop,
              paddingLeft: rule.style.paddingLeft,
              important: rule.style.cssText.includes('!important')
            })
          }
        })
      } catch (e) {
        // CORS error, skip
      }
    })

    return {
      computedPadding: {
        top: styles.paddingTop,
        left: styles.paddingLeft
      },
      classList: Array.from(el.classList),
      dataAttributes: Object.fromEntries(
        Array.from(el.attributes)
          .filter(attr => attr.name.startsWith('data-'))
          .map(attr => [attr.name, attr.value])
      ),
      matchingRules: rules.filter(r => r.padding || r.paddingTop || r.paddingLeft)
    }
  })

  console.log('=== CSS INSPECTION ===')
  console.log('Computed padding:', cssInfo.computedPadding)
  console.log('Classes:', cssInfo.classList)
  console.log('Data attributes:', cssInfo.dataAttributes)
  console.log('Matching CSS rules:', JSON.stringify(cssInfo.matchingRules, null, 2))
})
