import { test, expect } from '@playwright/test'

/**
 * Tests E2E para la configuración de Ollama en Settings
 */
test.describe('Ollama Settings', () => {
  test.beforeEach(async ({ page }) => {
    // Navegar a la página de configuración
    await page.goto('/settings')
    await page.waitForLoadState('networkidle')
  })

  test('should display Ollama status section', async ({ page }) => {
    // Buscar la sección de análisis semántico
    const analysisSection = page.locator('#analisis')
    await expect(analysisSection).toBeVisible()

    // Verificar que hay información sobre el analizador (usando heading específico)
    await expect(page.getByRole('heading', { name: /Analizador Semántico/i })).toBeVisible()
  })

  test('should show Ollama action button based on status', async ({ page }) => {
    // Esperar a que se carguen las capacidades del sistema
    await page.waitForTimeout(2000)

    // Verificar estado actual de Ollama
    const capabilitiesResponse = await page.request.get('http://localhost:8008/api/system/capabilities')
    const capabilities = await capabilitiesResponse.json()

    // Buscar elemento visible basado en el estado
    if (capabilities.data.ollama.available && capabilities.data.ollama.models?.length > 0) {
      // Estado "ready": muestra la barra con "Analizador listo"
      const readyBar = page.locator('.ollama-ready-bar')
      await expect(readyBar).toBeVisible({ timeout: 10000 })
      await expect(readyBar).toContainText(/Analizador listo/)
    } else {
      // Otros estados: muestra un botón de acción
      const ollamaButton = page.locator('.nlp-category').first().locator('button').filter({
        hasText: /Iniciar analizador|Configurar analizador|Descargar modelo/i
      }).first()
      await expect(ollamaButton).toBeVisible({ timeout: 10000 })
    }
  })

  test('should detect Ollama installation status via API', async ({ page }) => {
    // Hacer una petición directa a la API para verificar
    const response = await page.request.get('http://localhost:8008/api/system/capabilities')
    expect(response.ok()).toBeTruthy()

    const data = await response.json()
    expect(data.success).toBe(true)
    expect(data.data).toHaveProperty('ollama')
    expect(data.data.ollama).toHaveProperty('installed')
    expect(data.data.ollama).toHaveProperty('available')

    console.log('Ollama status:', {
      installed: data.data.ollama.installed,
      available: data.data.ollama.available,
      models: data.data.ollama.models
    })
  })

  test('should start Ollama when clicking button (if installed)', async ({ page }) => {
    // Primero verificar el estado actual de Ollama
    const capabilitiesResponse = await page.request.get('http://localhost:8008/api/system/capabilities')
    const capabilities = await capabilitiesResponse.json()

    if (!capabilities.data.ollama.installed) {
      console.log('Ollama no está instalado - saltando test de inicio')
      test.skip()
      return
    }

    // Si ya está corriendo, verificar que el estado muestra "Analizador listo"
    if (capabilities.data.ollama.available) {
      console.log('Ollama ya está corriendo')
      const readyBar = page.locator('.ollama-ready-bar')
      await expect(readyBar).toBeVisible({ timeout: 10000 })
      await expect(readyBar).toContainText(/Analizador listo/)
      return
    }

    // Si está instalado pero no corriendo, probar iniciar
    console.log('Intentando iniciar Ollama...')

    // Buscar el botón de iniciar dentro de la sección de análisis
    const analysisSection = page.locator('#analisis')
    const startButton = analysisSection.locator('button').filter({ hasText: /Iniciar analizador/i })
    await expect(startButton).toBeVisible({ timeout: 10000 })

    // Escuchar la petición de inicio
    const startPromise = page.waitForResponse(
      response => response.url().includes('/api/ollama/start') && response.status() === 200,
      { timeout: 70000 } // Ollama puede tardar hasta 60 segundos
    )

    // Click en iniciar
    await startButton.click()

    // Esperar respuesta del servidor
    const startResponse = await startPromise
    const startResult = await startResponse.json()

    console.log('Respuesta de inicio:', startResult)

    expect(startResult.success).toBe(true)

    // Esperar a que se actualice el estado (hay un delay de 2 segundos + recarga)
    await page.waitForTimeout(3000)

    // Verificar que el estado cambió
    const newCapabilitiesResponse = await page.request.get('http://localhost:8008/api/system/capabilities')
    const newCapabilities = await newCapabilitiesResponse.json()

    console.log('Nuevo estado de Ollama:', {
      installed: newCapabilities.data.ollama.installed,
      available: newCapabilities.data.ollama.available,
      models: newCapabilities.data.ollama.models
    })

    // Ollama debería estar disponible ahora
    expect(newCapabilities.data.ollama.available).toBe(true)
  })

  test('should show toast notification after starting Ollama', async ({ page }) => {
    // Verificar que Ollama está instalado y no corriendo
    const capabilitiesResponse = await page.request.get('http://localhost:8008/api/system/capabilities')
    const capabilities = await capabilitiesResponse.json()

    if (!capabilities.data.ollama.installed || capabilities.data.ollama.available) {
      console.log('Test no aplicable - Ollama no instalado o ya corriendo')
      test.skip()
      return
    }

    // Buscar el botón de iniciar dentro de la sección de análisis
    const analysisSection = page.locator('#analisis')
    const startButton = analysisSection.locator('button').filter({ hasText: /Iniciar analizador/i })
    await expect(startButton).toBeVisible()

    // Click en iniciar
    await startButton.click()

    // Esperar el toast de éxito
    const toast = page.locator('.p-toast-message')
    await expect(toast).toBeVisible({ timeout: 70000 })

    // Verificar que es un mensaje de éxito
    await expect(toast).toContainText(/Analizador iniciado|ya está corriendo/i)
  })

  test('should verify UI state updates after Ollama starts', async ({ page }) => {
    // Este test verifica que la UI se actualiza correctamente
    const capabilitiesResponse = await page.request.get('http://localhost:8008/api/system/capabilities')
    const capabilities = await capabilitiesResponse.json()

    if (!capabilities.data.ollama.installed) {
      test.skip()
      return
    }

    // Esperar a que carguen las capacidades
    await page.waitForTimeout(2000)

    if (capabilities.data.ollama.available && capabilities.data.ollama.models?.length > 0) {
      // Si está corriendo y tiene modelos, debería mostrar la barra "Analizador listo"
      const readyBar = page.locator('.ollama-ready-bar')
      await expect(readyBar).toBeVisible({ timeout: 10000 })
      await expect(readyBar).toContainText(/Analizador listo/)
    } else if (capabilities.data.ollama.available) {
      // Corriendo pero sin modelos
      const downloadButton = page.locator('.nlp-category').first().locator('button').filter({ hasText: /Descargar modelo/i })
      await expect(downloadButton).toBeVisible({ timeout: 10000 })
    } else {
      // Si no está corriendo, debería mostrar "Iniciar analizador"
      const startButton = page.locator('.nlp-category').first().locator('button').filter({ hasText: /Iniciar analizador/i })
      await expect(startButton).toBeVisible({ timeout: 10000 })
    }
  })

  test('should check Ollama API endpoint directly', async ({ page }) => {
    // Test de la API directamente
    const statusResponse = await page.request.get('http://localhost:8008/api/ollama/status')

    if (statusResponse.ok()) {
      const statusData = await statusResponse.json()
      console.log('Estado de Ollama (API):', statusData)
      expect(statusData).toHaveProperty('success')
    }
  })
})
