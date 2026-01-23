import { test, expect } from '@playwright/test'

test('Check Juan Pérez attributes specifically', async ({ page }) => {
  await page.goto('/')
  await page.waitForLoadState('domcontentloaded')
  await page.waitForTimeout(2000)

  // Cerrar diálogos
  for (let i = 0; i < 10; i++) {
    await page.keyboard.press('Escape')
    await page.waitForTimeout(150)
  }

  // Abrir proyecto test_pronouns
  const projectCard = page.locator('.project-card:has-text("test_pronouns")').first()
  if (await projectCard.isVisible({ timeout: 3000 }).catch(() => false)) {
    await projectCard.click({ force: true })
    await page.waitForTimeout(2000)
  }

  // Cerrar diálogos
  for (let i = 0; i < 5; i++) {
    await page.keyboard.press('Escape')
    await page.waitForTimeout(150)
  }

  // Ir a Entidades
  const entitiesTab = page.locator('button:has-text("Entidades")').first()
  if (await entitiesTab.isVisible({ timeout: 3000 }).catch(() => false)) {
    await entitiesTab.click()
    await page.waitForTimeout(1500)
  }

  // Seleccionar "Juan Pérez" (no "Juan")
  const juanPerez = page.locator('.entity-item-compact:has-text("Juan Pérez")').first()
  if (await juanPerez.isVisible({ timeout: 3000 }).catch(() => false)) {
    console.log('Found "Juan Pérez" entity, clicking...')
    await juanPerez.click()
    await page.waitForTimeout(1000)
  } else {
    console.log('"Juan Pérez" not found, listing all entities...')
    const entities = await page.locator('.entity-item-compact').allTextContents()
    console.log('Available entities:', entities)
  }

  await page.screenshot({ path: 'test-results/juan-perez-detail.png', fullPage: true })

  // Obtener contenido completo
  const content = await page.locator('main').textContent() || ''
  console.log('\n=== FULL CONTENT ===')
  console.log(content.substring(0, 3000))

  // Verificar si hay sección ATRIBUTOS
  const hasAtributos = content.includes('ATRIBUTOS') || content.includes('Atributos')
  console.log(`\nATRIBUTOS section found: ${hasAtributos}`)

  if (hasAtributos) {
    // Buscar atributos específicos
    console.log('\n=== CHECKING SPECIFIC ATTRIBUTES ===')
    console.log(`- azul/ojos: ${/azul|ojos/i.test(content)}`)
    console.log(`- carpintero: ${/carpintero/i.test(content)}`)
    console.log(`- alto: ${/\balto\b/i.test(content)}`)
    console.log(`- castaño: ${/castaño/i.test(content)}`)
  }
})
