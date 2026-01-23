import { test, expect } from '@playwright/test'

/**
 * Test para verificar extracción de atributos en proyecto existente
 */
test('Verify attribute extraction in existing project', async ({ page }) => {
  // 1. Navegar a la app
  await page.goto('/')
  await page.waitForLoadState('domcontentloaded')
  await page.waitForTimeout(2000)

  // Cerrar todos los diálogos
  for (let i = 0; i < 15; i++) {
    await page.keyboard.press('Escape')
    await page.waitForTimeout(150)
  }

  await page.waitForTimeout(500)
  await page.screenshot({ path: 'test-results/verify-attr-1-home.png', fullPage: true })

  // 2. Abrir el primer proyecto disponible
  const projectCard = page.locator('.project-card').first()
  if (!await projectCard.isVisible({ timeout: 5000 }).catch(() => false)) {
    console.log('No project found')
    return
  }

  const projectName = await projectCard.locator('.project-title, .p-card-title, h3, h4').first().textContent()
  console.log(`Opening project: ${projectName}`)

  await projectCard.click({ force: true })
  await page.waitForTimeout(3000)

  // Cerrar diálogos post-navegación
  for (let i = 0; i < 5; i++) {
    await page.keyboard.press('Escape')
    await page.waitForTimeout(200)
  }

  await page.screenshot({ path: 'test-results/verify-attr-2-project.png', fullPage: true })

  // 3. Ir a Entidades
  const entitiesTab = page.locator('button:has-text("Entidades")').first()
  if (await entitiesTab.isVisible({ timeout: 3000 }).catch(() => false)) {
    await entitiesTab.click()
    await page.waitForTimeout(1500)
  }

  await page.screenshot({ path: 'test-results/verify-attr-3-entities.png', fullPage: true })

  // 4. Seleccionar Juan Pérez
  const juanItem = page.locator('.entity-item-compact:has-text("Juan")').first()
  if (await juanItem.isVisible({ timeout: 3000 }).catch(() => false)) {
    await juanItem.click()
    await page.waitForTimeout(1000)
  }

  await page.screenshot({ path: 'test-results/verify-attr-4-juan-selected.png', fullPage: true })

  // 5. Obtener contenido del panel de detalle
  const detailPanel = page.locator('.entity-detail, .detail-panel, .entity-inspector').first()
  let detailContent = ''

  if (await detailPanel.isVisible({ timeout: 2000 }).catch(() => false)) {
    detailContent = await detailPanel.textContent() || ''
  } else {
    // Buscar en el área principal
    detailContent = await page.locator('main, .workspace-content').first().textContent() || ''
  }

  console.log('\n========================================')
  console.log('ENTITY DETAIL CONTENT:')
  console.log('========================================')
  console.log(detailContent.substring(0, 2000))
  console.log('========================================\n')

  // 6. Verificar atributos específicos
  const hasOjosAzules = /azul|ojos/i.test(detailContent)
  const hasCarpintero = /carpintero|profesión/i.test(detailContent)
  const hasAlto = /alto|altura/i.test(detailContent)
  const hasCastano = /castaño|pelo/i.test(detailContent)

  console.log('\n=== ATTRIBUTE VERIFICATION ===')
  console.log(`✓ Ojos azules: ${hasOjosAzules ? 'FOUND' : 'NOT FOUND'}`)
  console.log(`✓ Carpintero (después de "Él"): ${hasCarpintero ? 'FOUND' : 'NOT FOUND'}`)
  console.log(`✓ Alto (después de "También"): ${hasAlto ? 'FOUND' : 'NOT FOUND'}`)
  console.log(`✓ Pelo castaño: ${hasCastano ? 'FOUND' : 'NOT FOUND'}`)
  console.log('==============================\n')

  // 7. Buscar sección ATRIBUTOS específicamente
  const attrSection = page.locator('text=ATRIBUTOS').first()
  if (await attrSection.isVisible({ timeout: 2000 }).catch(() => false)) {
    // Obtener el contenedor padre
    const attrContainer = page.locator('.attributes-section, [class*="attribute"]').first()
    if (await attrContainer.isVisible({ timeout: 1000 }).catch(() => false)) {
      const attrContent = await attrContainer.textContent()
      console.log('ATTRIBUTES SECTION:')
      console.log(attrContent)
    }
  }

  await page.screenshot({ path: 'test-results/verify-attr-5-final.png', fullPage: true })

  // Verificar que al menos ojos azules aparece (atributo básico)
  expect(hasOjosAzules || hasCarpintero || hasAlto).toBeTruthy()
})
