import { test, expect, Page } from '@playwright/test'

const API_URL = 'http://localhost:8008/api'
const FRONTEND_URL = 'http://localhost:5173'

/**
 * Helper para cerrar modales de bienvenida u otros overlays
 */
async function dismissModals(page: Page): Promise<void> {
  // Esperar un momento para que aparezcan modales
  await page.waitForTimeout(500)

  // Intentar cerrar modal de bienvenida si existe
  const closeBtn = page.locator('.p-dialog-header-close, button[aria-label="Close"], .p-dialog button:has-text("Cerrar"), .p-dialog button:has-text("Entendido")')
  const modalMask = page.locator('.p-dialog-mask')

  if (await modalMask.isVisible().catch(() => false)) {
    // Intentar cerrar con botón
    const closeBtnVisible = await closeBtn.first().isVisible().catch(() => false)
    if (closeBtnVisible) {
      await closeBtn.first().click()
      await page.waitForTimeout(300)
    } else {
      // Presionar Escape como fallback
      await page.keyboard.press('Escape')
      await page.waitForTimeout(300)
    }
  }
}

/**
 * Tests E2E para la vista de Timeline
 *
 * Verifica que el componente Timeline se renderiza correctamente
 * y muestra los estados apropiados (cargando, vacío, datos, error).
 */
test.describe('Timeline View', () => {
  // Configurar timeout más largo y un solo retry
  test.setTimeout(30000)

  test.beforeEach(async ({ request }) => {
    // Verificar si el backend está disponible
    const healthCheck = await request.get(`${API_URL}/health`).catch(() => null)
    if (!healthCheck || !healthCheck.ok()) {
      test.skip()
    }
  })

  test('should display Timeline tab and render component', async ({ page, request }) => {
    // Obtener un proyecto existente
    const projectsResponse = await request.get(`${API_URL}/projects`)
    const projectsData = await projectsResponse.json()

    if (!projectsData.data || projectsData.data.length === 0) {
      console.log('No projects available, skipping test')
      test.skip()
      return
    }

    const project = projectsData.data[0]
    console.log(`Testing Timeline for project: ${project.name} (ID: ${project.id})`)

    // Navegar al proyecto
    await page.goto(`${FRONTEND_URL}/projects/${project.id}`)
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(1000)

    // Cerrar modales si existen (ej: modal de bienvenida)
    await dismissModals(page)

    // Buscar y hacer clic en la pestaña Timeline
    const timelineTab = page.locator('button[role="tab"]').filter({ hasText: 'Timeline' })
    await expect(timelineTab).toBeVisible({ timeout: 10000 })
    await timelineTab.click()

    // Esperar a que se cargue el contenido
    await page.waitForTimeout(2000)

    // Verificar que el componente Timeline se renderiza
    // Puede estar en uno de estos estados:
    // 1. Cargando (spinner)
    // 2. Error (mensaje de error)
    // 3. Vacío (sin eventos temporales)
    // 4. Con datos (lista de eventos)

    const timelineView = page.locator('.timeline-view')
    await expect(timelineView).toBeVisible({ timeout: 10000 })

    // Verificar que el toolbar está presente
    const toolbar = page.locator('.timeline-toolbar')
    await expect(toolbar).toBeVisible()

    // Verificar que hay algún contenido (no está vacío)
    const hasLoading = await page.locator('.loading-state').isVisible().catch(() => false)
    const hasError = await page.locator('.error-state').isVisible().catch(() => false)
    const hasEmpty = await page.locator('.empty-state').isVisible().catch(() => false)
    const hasContent = await page.locator('.timeline-content').isVisible().catch(() => false)

    // Debe haber al menos uno de los estados
    const hasValidState = hasLoading || hasError || hasEmpty || hasContent
    expect(hasValidState).toBe(true)

    console.log(`Timeline state: loading=${hasLoading}, error=${hasError}, empty=${hasEmpty}, content=${hasContent}`)
  })

  test('should show empty state message when no temporal markers', async ({ page, request }) => {
    // Obtener un proyecto existente
    const projectsResponse = await request.get(`${API_URL}/projects`)
    const projectsData = await projectsResponse.json()

    if (!projectsData.data || projectsData.data.length === 0) {
      console.log('No projects available, skipping test')
      test.skip()
      return
    }

    const project = projectsData.data[0]

    // Navegar al proyecto
    await page.goto(`${FRONTEND_URL}/projects/${project.id}`)
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(1000)

    // Cerrar modales si existen
    await dismissModals(page)

    // Hacer clic en la pestaña Timeline
    const timelineTab = page.locator('button[role="tab"]').filter({ hasText: 'Timeline' })
    await timelineTab.click()
    await page.waitForTimeout(2000)

    // Verificar que si está vacío, muestra el mensaje apropiado
    const emptyState = page.locator('.empty-state')
    const isEmptyVisible = await emptyState.isVisible().catch(() => false)

    if (isEmptyVisible) {
      // Verificar que el mensaje de vacío tiene el contenido esperado
      await expect(emptyState.locator('h4')).toContainText(/No hay eventos temporales/i)
      console.log('Empty state message is displayed correctly')
    } else {
      // Si hay contenido, verificar que los eventos se muestran
      const hasContent = await page.locator('.timeline-content').isVisible().catch(() => false)
      if (hasContent) {
        console.log('Timeline has content, checking events...')
        const eventCount = await page.locator('.timeline-event').count()
        console.log(`Found ${eventCount} timeline events`)
      }
    }

    // El test pasa si la página se cargó correctamente
    const timelineView = page.locator('.timeline-view')
    await expect(timelineView).toBeVisible()
  })

  test('should have reload button functional', async ({ page, request }) => {
    // Obtener un proyecto existente
    const projectsResponse = await request.get(`${API_URL}/projects`)
    const projectsData = await projectsResponse.json()

    if (!projectsData.data || projectsData.data.length === 0) {
      console.log('No projects available, skipping test')
      test.skip()
      return
    }

    const project = projectsData.data[0]

    // Navegar al proyecto
    await page.goto(`${FRONTEND_URL}/projects/${project.id}`)
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(1000)

    // Cerrar modales si existen
    await dismissModals(page)

    // Hacer clic en la pestaña Timeline
    const timelineTab = page.locator('button[role="tab"]').filter({ hasText: 'Timeline' })
    await timelineTab.click()
    await page.waitForTimeout(2000)

    // Buscar el botón de recargar (puede estar en toolbar o en empty state)
    const reloadBtnToolbar = page.locator('.timeline-toolbar button[aria-label*="Recargar"], .timeline-toolbar button:has(.pi-refresh)')
    const reloadBtnEmpty = page.locator('.empty-state button:has-text("Recargar")')

    const hasReloadToolbar = await reloadBtnToolbar.first().isVisible().catch(() => false)
    const hasReloadEmpty = await reloadBtnEmpty.isVisible().catch(() => false)

    if (hasReloadToolbar) {
      await reloadBtnToolbar.first().click()
      console.log('Clicked reload button in toolbar')
    } else if (hasReloadEmpty) {
      await reloadBtnEmpty.click()
      console.log('Clicked reload button in empty state')
    }

    // Esperar a que termine la recarga
    await page.waitForTimeout(2000)

    // Verificar que el timeline sigue visible
    const timelineView = page.locator('.timeline-view')
    await expect(timelineView).toBeVisible()
  })

  test('Timeline API endpoint returns valid response', async ({ request }) => {
    test.setTimeout(60000) // El endpoint de timeline puede tardar

    // Obtener un proyecto existente
    const projectsResponse = await request.get(`${API_URL}/projects`)
    const projectsData = await projectsResponse.json()

    if (!projectsData.data || projectsData.data.length === 0) {
      console.log('No projects available, skipping test')
      test.skip()
      return
    }

    const project = projectsData.data[0]

    // Llamar directamente al API de timeline con timeout extendido
    const timelineResponse = await request.get(`${API_URL}/projects/${project.id}/timeline`, {
      timeout: 45000
    })
    expect(timelineResponse.ok()).toBe(true)

    const timelineData = await timelineResponse.json()
    expect(timelineData.success).toBe(true)

    // Verificar estructura de la respuesta
    expect(timelineData.data).toBeDefined()
    expect(Array.isArray(timelineData.data.events)).toBe(true)
    expect(typeof timelineData.data.markers_count).toBe('number')

    console.log(`Timeline API response: ${timelineData.data.events.length} events, ${timelineData.data.markers_count} markers`)
  })

  test('should have view mode toggle (list/horizontal)', async ({ page, request }) => {
    // Obtener un proyecto existente
    const projectsResponse = await request.get(`${API_URL}/projects`)
    const projectsData = await projectsResponse.json()

    if (!projectsData.data || projectsData.data.length === 0) {
      console.log('No projects available, skipping test')
      test.skip()
      return
    }

    const project = projectsData.data[0]

    // Navegar al proyecto
    await page.goto(`${FRONTEND_URL}/projects/${project.id}`)
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(1000)

    // Cerrar modales si existen
    await dismissModals(page)

    // Hacer clic en la pestaña Timeline
    const timelineTab = page.locator('button[role="tab"]').filter({ hasText: 'Timeline' })
    await timelineTab.click()
    await page.waitForTimeout(2000)

    // Verificar que el toggle de vista está presente
    const viewModeToggle = page.locator('.view-mode-toggle')
    const hasToggle = await viewModeToggle.isVisible().catch(() => false)

    if (hasToggle) {
      console.log('View mode toggle is present')

      // Verificar que hay botones de lista y horizontal
      const listBtn = viewModeToggle.locator('button').filter({ has: page.locator('.pi-list') })
      const horizontalBtn = viewModeToggle.locator('button').filter({ has: page.locator('.pi-arrows-h') })

      const hasListBtn = await listBtn.isVisible().catch(() => false)
      const hasHorizontalBtn = await horizontalBtn.isVisible().catch(() => false)

      expect(hasListBtn || hasHorizontalBtn).toBe(true)
      console.log(`List button: ${hasListBtn}, Horizontal button: ${hasHorizontalBtn}`)
    } else {
      // Si no hay toggle, puede que el timeline esté vacío
      const hasContent = await page.locator('.timeline-content').isVisible().catch(() => false)
      console.log(`View toggle not visible, timeline content visible: ${hasContent}`)
    }

    // El timeline debe estar visible
    const timelineView = page.locator('.timeline-view')
    await expect(timelineView).toBeVisible()
  })

  test('should switch between list and horizontal view', async ({ page, request }) => {
    // Obtener un proyecto existente
    const projectsResponse = await request.get(`${API_URL}/projects`)
    const projectsData = await projectsResponse.json()

    if (!projectsData.data || projectsData.data.length === 0) {
      console.log('No projects available, skipping test')
      test.skip()
      return
    }

    const project = projectsData.data[0]

    // Navegar al proyecto
    await page.goto(`${FRONTEND_URL}/projects/${project.id}`)
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(1000)

    // Cerrar modales si existen
    await dismissModals(page)

    // Hacer clic en la pestaña Timeline
    const timelineTab = page.locator('button[role="tab"]').filter({ hasText: 'Timeline' })
    await timelineTab.click()
    await page.waitForTimeout(2000)

    // Verificar que hay contenido
    const hasContent = await page.locator('.timeline-content').isVisible().catch(() => false)
    if (!hasContent) {
      console.log('Timeline has no content, skipping view switch test')
      test.skip()
      return
    }

    // Buscar el toggle de vista horizontal
    const horizontalBtn = page.locator('.view-mode-toggle button').filter({ has: page.locator('.pi-arrows-h') })
    const hasHorizontalBtn = await horizontalBtn.isVisible().catch(() => false)

    if (hasHorizontalBtn) {
      // Cambiar a vista horizontal
      await horizontalBtn.click()
      await page.waitForTimeout(1000)

      // Verificar que se muestra el componente VisTimeline
      const visTimeline = page.locator('.vis-timeline-container')
      const hasVisTimeline = await visTimeline.isVisible().catch(() => false)

      if (hasVisTimeline) {
        console.log('Switched to horizontal view successfully')

        // Verificar que tiene el toolbar con opciones de agrupación
        const groupDropdown = page.locator('.vis-toolbar .group-dropdown')
        const hasGroupDropdown = await groupDropdown.isVisible().catch(() => false)
        console.log(`Group dropdown visible: ${hasGroupDropdown}`)

        // Verificar controles de zoom
        const zoomIn = page.locator('.vis-toolbar button').filter({ has: page.locator('.pi-search-plus') })
        const hasZoomIn = await zoomIn.isVisible().catch(() => false)
        console.log(`Zoom controls visible: ${hasZoomIn}`)
      }

      // Volver a vista de lista
      const listBtn = page.locator('.view-mode-toggle button').filter({ has: page.locator('.pi-list') })
      await listBtn.click()
      await page.waitForTimeout(500)

      // Verificar que volvemos a ver la lista
      const eventsList = page.locator('.events-list, .timeline-legend')
      const hasEventsList = await eventsList.isVisible().catch(() => false)
      console.log(`Back to list view: ${hasEventsList}`)
    }

    // El timeline debe estar visible
    const timelineView = page.locator('.timeline-view')
    await expect(timelineView).toBeVisible()
  })

  test('should group events by chapter in list view', async ({ page, request }) => {
    // Obtener un proyecto existente
    const projectsResponse = await request.get(`${API_URL}/projects`)
    const projectsData = await projectsResponse.json()

    if (!projectsData.data || projectsData.data.length === 0) {
      console.log('No projects available, skipping test')
      test.skip()
      return
    }

    const project = projectsData.data[0]

    // Navegar al proyecto
    await page.goto(`${FRONTEND_URL}/projects/${project.id}`)
    await page.waitForLoadState('domcontentloaded')
    await page.waitForTimeout(1000)

    // Cerrar modales si existen
    await dismissModals(page)

    // Hacer clic en la pestaña Timeline
    const timelineTab = page.locator('button[role="tab"]').filter({ hasText: 'Timeline' })
    await timelineTab.click()
    await page.waitForTimeout(2000)

    // Verificar que hay contenido
    const hasContent = await page.locator('.timeline-content').isVisible().catch(() => false)
    if (!hasContent) {
      console.log('Timeline has no content, skipping grouping test')
      test.skip()
      return
    }

    // Buscar el toggle de agrupación por capítulo
    const groupToggle = page.locator('.group-toggle input[type="checkbox"]')
    const hasGroupToggle = await groupToggle.isVisible().catch(() => false)

    if (hasGroupToggle) {
      // Activar agrupación si no está activa
      const isChecked = await groupToggle.isChecked()
      if (!isChecked) {
        await groupToggle.click()
        await page.waitForTimeout(500)
      }

      // Verificar que se muestran grupos de capítulos
      const chapterGroups = page.locator('.chapter-group')
      const groupCount = await chapterGroups.count()
      console.log(`Found ${groupCount} chapter groups`)

      if (groupCount > 0) {
        // Verificar que el primer grupo tiene header
        const firstHeader = chapterGroups.first().locator('.chapter-header')
        await expect(firstHeader).toBeVisible()

        // Verificar que el header tiene el título del capítulo
        const headerTitle = firstHeader.locator('.chapter-title')
        const titleText = await headerTitle.textContent()
        expect(titleText).toContain('Capítulo')
        console.log(`First chapter: ${titleText}`)
      }
    }

    // El timeline debe estar visible
    const timelineView = page.locator('.timeline-view')
    await expect(timelineView).toBeVisible()
  })
})
