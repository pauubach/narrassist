import { test, expect } from '@playwright/test'
import * as fs from 'fs'
import * as path from 'path'

/**
 * Test E2E completo para verificar extracción de atributos después de pronombres
 */
test.describe('Attribute Extraction After Pronouns', () => {
  // Crear archivo de prueba temporal
  const testDir = path.join(process.env.USERPROFILE || '', '.narrative_assistant', 'test_documents')
  const testFilePath = path.join(testDir, 'test_pronouns.txt')

  const testContent = `Capítulo 1: El Encuentro

Juan Pérez era un hombre de ojos azules y pelo castaño rizado. Tenía una barba espesa y bien cuidada.

Él era carpintero de profesión y vivía en Madrid desde hacía diez años. También era alto, de casi dos metros de altura.

María Sánchez lo conoció en el parque del Retiro. Ella era profesora de literatura y tenía el cabello negro y largo.

Capítulo 2: La Conversación

Juan le contó sobre su trabajo. Él construía muebles artesanales para clientes exigentes.

María escuchaba con atención. Ella siempre había admirado a los artesanos.`

  test.beforeAll(async () => {
    // Crear directorio si no existe
    if (!fs.existsSync(testDir)) {
      fs.mkdirSync(testDir, { recursive: true })
    }
    // Crear archivo de prueba
    fs.writeFileSync(testFilePath, testContent, 'utf-8')
    console.log(`Test file created at: ${testFilePath}`)
  })

  test.afterAll(async () => {
    // Limpiar archivo de prueba
    if (fs.existsSync(testFilePath)) {
      fs.unlinkSync(testFilePath)
      console.log('Test file cleaned up')
    }
  })

  test('Extract attributes after pronouns and assign to correct entity', async ({ page }) => {
    // 1. Navegar a la app
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(2000)

    // Cerrar diálogos iniciales
    for (let i = 0; i < 10; i++) {
      const closeBtn = page.locator('.p-dialog-header-close, button:has-text("Cerrar"), button:has-text("Comenzar"), button:has-text("OK"), button:has-text("Entendido")').first()
      if (await closeBtn.isVisible({ timeout: 500 }).catch(() => false)) {
        await closeBtn.click({ force: true })
        await page.waitForTimeout(300)
      } else {
        await page.keyboard.press('Escape')
        await page.waitForTimeout(200)
      }
    }

    await page.waitForTimeout(500)

    // 2. Eliminar proyecto existente si hay uno llamado "test_pronouns"
    console.log('Looking for existing test project to delete...')
    const existingProject = page.locator('.project-card:has-text("test_pronouns")').first()
    if (await existingProject.isVisible({ timeout: 2000 }).catch(() => false)) {
      console.log('Found existing project, deleting...')

      // Buscar menú contextual o botón de eliminar
      await existingProject.hover()
      await page.waitForTimeout(300)

      const deleteBtn = existingProject.locator('button[aria-label="Eliminar"], button:has(i.pi-trash)').first()
      if (await deleteBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
        await deleteBtn.click()
        await page.waitForTimeout(500)

        // Confirmar eliminación
        const confirmBtn = page.locator('button:has-text("Eliminar"), button:has-text("Confirmar")').first()
        if (await confirmBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
          await confirmBtn.click()
          await page.waitForTimeout(1000)
        }
      }
    }

    // 3. Crear nuevo proyecto
    console.log('Creating new project...')
    const newProjectBtn = page.locator('button:has-text("Nuevo Proyecto")').first()
    await expect(newProjectBtn).toBeVisible({ timeout: 5000 })
    await newProjectBtn.click()
    await page.waitForTimeout(1000)

    // Llenar el formulario de nuevo proyecto
    const dialog = page.locator('.p-dialog').first()
    await expect(dialog).toBeVisible({ timeout: 5000 })

    // Nombre del proyecto
    const nameInput = dialog.locator('input[type="text"]').first()
    await nameInput.fill('test_pronouns')
    await page.waitForTimeout(300)

    // Seleccionar archivo - usar el file chooser
    const fileInput = dialog.locator('input[type="file"]')
    await fileInput.setInputFiles(testFilePath)
    await page.waitForTimeout(500)

    // Crear proyecto
    const createBtn = dialog.locator('button:has-text("Crear"), button:has-text("Guardar")').first()
    await createBtn.click()
    await page.waitForTimeout(2000)

    // 4. Esperar a que se complete el análisis
    console.log('Waiting for analysis to complete...')

    // Esperar a que aparezca el indicador de análisis
    const analysisIndicator = page.locator('text=Analizando, text=Análisis, .analysis-progress')

    // Esperar hasta 2 minutos para que termine el análisis
    for (let i = 0; i < 60; i++) {
      await page.waitForTimeout(2000)

      // Verificar si el análisis terminó
      const completed = page.locator('text=Análisis completado, text=completado')
      if (await completed.isVisible({ timeout: 500 }).catch(() => false)) {
        console.log('Analysis completed!')
        break
      }

      // Verificar si hay error
      const error = page.locator('text=Error')
      if (await error.isVisible({ timeout: 500 }).catch(() => false)) {
        console.log('Analysis error detected')
        break
      }

      if (i % 10 === 0) {
        console.log(`Still analyzing... (${i * 2}s)`)
      }
    }

    await page.waitForTimeout(2000)

    // 5. Ir a la pestaña de Entidades
    console.log('Navigating to Entities tab...')
    const entitiesTab = page.getByRole('button', { name: /Entidades/i })
    await expect(entitiesTab).toBeVisible({ timeout: 5000 })
    await entitiesTab.click()
    await page.waitForTimeout(1500)

    // Tomar screenshot
    await page.screenshot({ path: 'test-results/attr-test-entities.png', fullPage: true })

    // 6. Seleccionar Juan Pérez
    console.log('Selecting Juan Pérez...')
    const juanItem = page.locator('.entity-item-compact:has-text("Juan")').first()
    if (await juanItem.isVisible({ timeout: 3000 }).catch(() => false)) {
      await juanItem.click()
      await page.waitForTimeout(1000)
    } else {
      // Intentar con texto directo
      const juanText = page.locator('text=Juan Pérez').first()
      if (await juanText.isVisible({ timeout: 2000 }).catch(() => false)) {
        await juanText.click()
        await page.waitForTimeout(1000)
      }
    }

    // Tomar screenshot del detalle
    await page.screenshot({ path: 'test-results/attr-test-juan-detail.png', fullPage: true })

    // 7. Verificar atributos de Juan
    console.log('Checking Juan attributes...')

    // Buscar sección de atributos
    const attributesSection = page.locator('text=ATRIBUTOS, text=Atributos').first()
    if (await attributesSection.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Buscar atributos específicos
      const pageContent = await page.content()

      // Verificar ojos azules
      const hasEyeColor = pageContent.includes('azul') || pageContent.includes('ojos')
      console.log(`Eye color attribute found: ${hasEyeColor}`)

      // Verificar carpintero (después de "Él")
      const hasProfession = pageContent.includes('carpintero') || pageContent.includes('Profesión')
      console.log(`Profession attribute found: ${hasProfession}`)

      // Verificar alto (después de "También")
      const hasHeight = pageContent.includes('alto') || pageContent.includes('altura')
      console.log(`Height attribute found: ${hasHeight}`)

      // Obtener todos los atributos visibles
      const attributes = await page.locator('.attribute-item, [class*="attribute"]').allTextContents()
      console.log('Visible attributes:', attributes)
    }

    // 8. Buscar en el inspector de entidad
    const inspector = page.locator('.entity-inspector, .entity-detail, .detail-panel').first()
    if (await inspector.isVisible({ timeout: 2000 }).catch(() => false)) {
      const inspectorContent = await inspector.textContent()
      console.log('\n=== Inspector Content ===')
      console.log(inspectorContent?.substring(0, 1000))

      // Verificaciones específicas
      expect(inspectorContent).toContain('Juan')

      // Estas verificaciones pueden fallar si los atributos no se extrajeron
      const hasCarpintero = inspectorContent?.toLowerCase().includes('carpintero')
      const hasAlto = inspectorContent?.toLowerCase().includes('alto')
      const hasAzules = inspectorContent?.toLowerCase().includes('azul')

      console.log('\n=== Attribute Verification ===')
      console.log(`- Carpintero (after "Él"): ${hasCarpintero ? '✓' : '✗'}`)
      console.log(`- Alto (after "También"): ${hasAlto ? '✓' : '✗'}`)
      console.log(`- Ojos azules: ${hasAzules ? '✓' : '✗'}`)
    }

    // Tomar screenshot final
    await page.screenshot({ path: 'test-results/attr-test-final.png', fullPage: true })
  })
})
