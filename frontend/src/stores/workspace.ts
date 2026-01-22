/**
 * Store para el workspace de edición
 *
 * Gestiona el estado del espacio de trabajo:
 * - Pestaña activa (Texto, Entidades, Relaciones, Alertas, Resumen)
 * - Estado de los paneles (expandido/colapsado)
 * - Scroll y navegación
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export type WorkspaceTab = 'text' | 'entities' | 'relationships' | 'alerts' | 'timeline' | 'style' | 'summary'

export type SidebarTab = 'chapters' | 'alerts' | 'characters' | 'assistant'

export interface PanelState {
  expanded: boolean
  width: number
  minWidth: number
  maxWidth: number
}

/** Configuración de layout por cada workspace tab */
export interface TabLayoutConfig {
  showLeftPanel: boolean
  showRightPanel: boolean
  sidebarTabs: SidebarTab[]
  defaultSidebarTab?: SidebarTab
  /** Ancho preferido del panel derecho para este tab */
  rightPanelWidth?: number
}

/** Configuración de paneles para cada tab - define qué paneles se muestran */
export const TAB_LAYOUT_CONFIG: Record<WorkspaceTab, TabLayoutConfig> = {
  text: {
    showLeftPanel: true,
    showRightPanel: true,
    sidebarTabs: ['chapters', 'alerts', 'characters', 'assistant'],
    defaultSidebarTab: 'chapters'
  },
  entities: {
    showLeftPanel: false,
    showRightPanel: false,  // La ficha de entidad se muestra en el panel central
    sidebarTabs: []
  },
  relationships: {
    showLeftPanel: false,
    showRightPanel: true,  // Colapsable para detalles de relación
    sidebarTabs: []
  },
  alerts: {
    showLeftPanel: true,
    showRightPanel: true,
    sidebarTabs: ['alerts'],  // Solo alertas, sin capítulos
    defaultSidebarTab: 'alerts'
  },
  timeline: {
    showLeftPanel: false,
    showRightPanel: false,  // Timeline full-width
    sidebarTabs: []
  },
  style: {
    showLeftPanel: false,
    showRightPanel: false,  // Estilo full-width
    sidebarTabs: []
  },
  summary: {
    showLeftPanel: false,
    showRightPanel: false,  // Dashboard full-width
    sidebarTabs: []
  }
}

export const useWorkspaceStore = defineStore('workspace', () => {
  // ============================================================================
  // Estado
  // ============================================================================

  /** Pestaña activa */
  const activeTab = ref<WorkspaceTab>('text')

  /** Estado del panel izquierdo (lista de elementos) */
  const leftPanel = ref<PanelState>({
    expanded: true,
    width: 280,
    minWidth: 200,
    maxWidth: 400
  })

  /** Estado del panel derecho (detalles/propiedades) */
  const rightPanel = ref<PanelState>({
    expanded: true,
    width: 320,
    minWidth: 250,
    maxWidth: 500
  })

  /** Posición de scroll del texto (para restaurar al cambiar de pestaña) */
  const textScrollPosition = ref(0)

  /** Capítulo visible actualmente */
  const currentChapter = ref<number | null>(null)

  /** Si está en modo de pantalla completa para el texto */
  const fullscreenText = ref(false)

  /** Historial de navegación para el botón "atrás" */
  const navigationHistory = ref<Array<{ tab: WorkspaceTab; context?: string }>>([])

  /** Filtro de severidad para la pestaña de alertas */
  const alertSeverityFilter = ref<string | null>(null)

  /** Entidad seleccionada para ver sus menciones */
  const selectedEntityForMentions = ref<number | null>(null)

  /** Posición del texto a la que hacer scroll (start_char) */
  const scrollToPosition = ref<number | null>(null)

  /** Texto a resaltar al hacer scroll */
  const scrollToText = ref<string | null>(null)

  /** ID del capítulo al que hacer scroll (para navegación directa) */
  const scrollToChapterId = ref<number | null>(null)

  // ============================================================================
  // Getters
  // ============================================================================

  /** Ancho disponible para el contenido central */
  const centerWidth = computed(() => {
    const leftW = leftPanel.value.expanded ? leftPanel.value.width : 0
    const rightW = rightPanel.value.expanded ? rightPanel.value.width : 0
    return `calc(100% - ${leftW}px - ${rightW}px)`
  })

  /** Si hay historial para volver atrás */
  const canGoBack = computed(() => navigationHistory.value.length > 0)

  /** Configuración de layout para el tab activo */
  const currentLayoutConfig = computed(() => TAB_LAYOUT_CONFIG[activeTab.value])

  /** Si el panel izquierdo debe mostrarse según el tab activo */
  const shouldShowLeftPanel = computed(() => currentLayoutConfig.value.showLeftPanel)

  /** Si el panel derecho debe mostrarse según el tab activo */
  const shouldShowRightPanel = computed(() => currentLayoutConfig.value.showRightPanel)

  /** Tabs disponibles en el sidebar para el tab activo */
  const availableSidebarTabs = computed(() => currentLayoutConfig.value.sidebarTabs)

  /** Configuración de pestañas */
  const tabs = computed(() => [
    { id: 'text' as WorkspaceTab, label: 'Texto', icon: 'pi pi-file-edit' },
    { id: 'entities' as WorkspaceTab, label: 'Entidades', icon: 'pi pi-users' },
    { id: 'relationships' as WorkspaceTab, label: 'Relaciones', icon: 'pi pi-share-alt' },
    { id: 'alerts' as WorkspaceTab, label: 'Alertas', icon: 'pi pi-exclamation-triangle' },
    { id: 'timeline' as WorkspaceTab, label: 'Timeline', icon: 'pi pi-clock' },
    { id: 'style' as WorkspaceTab, label: 'Estilo', icon: 'pi pi-pencil' },
    { id: 'summary' as WorkspaceTab, label: 'Resumen', icon: 'pi pi-chart-bar' }
  ])

  // ============================================================================
  // Acciones
  // ============================================================================

  /**
   * Cambia a una pestaña
   */
  function setActiveTab(tab: WorkspaceTab, addToHistory = true) {
    if (activeTab.value === tab) return

    if (addToHistory) {
      navigationHistory.value.push({ tab: activeTab.value })
      // Limitar historial a 20 elementos
      if (navigationHistory.value.length > 20) {
        navigationHistory.value.shift()
      }
    }

    activeTab.value = tab
  }

  /**
   * Vuelve a la pestaña anterior
   */
  function goBack() {
    const prev = navigationHistory.value.pop()
    if (prev) {
      setActiveTab(prev.tab, false)
    }
  }

  /**
   * Expande/colapsa el panel izquierdo
   */
  function toggleLeftPanel() {
    leftPanel.value.expanded = !leftPanel.value.expanded
  }

  /**
   * Expande/colapsa el panel derecho
   */
  function toggleRightPanel() {
    rightPanel.value.expanded = !rightPanel.value.expanded
  }

  /**
   * Establece el ancho del panel izquierdo
   */
  function setLeftPanelWidth(width: number) {
    leftPanel.value.width = Math.max(
      leftPanel.value.minWidth,
      Math.min(leftPanel.value.maxWidth, width)
    )
  }

  /**
   * Ajusta el ancho del panel izquierdo por un delta
   */
  function adjustLeftPanelWidth(delta: number) {
    setLeftPanelWidth(leftPanel.value.width + delta)
  }

  /**
   * Establece el ancho del panel derecho
   */
  function setRightPanelWidth(width: number) {
    rightPanel.value.width = Math.max(
      rightPanel.value.minWidth,
      Math.min(rightPanel.value.maxWidth, width)
    )
  }

  /**
   * Ajusta el ancho del panel derecho por un delta
   */
  function adjustRightPanelWidth(delta: number) {
    // Para el panel derecho, el delta es inverso (mover izquierda = aumentar)
    setRightPanelWidth(rightPanel.value.width - delta)
  }

  /**
   * Guarda la posición de scroll del texto
   */
  function saveTextScroll(position: number) {
    textScrollPosition.value = position
  }

  /**
   * Establece el capítulo actual
   */
  function setCurrentChapter(chapter: number | null) {
    currentChapter.value = chapter
  }

  /**
   * Activa/desactiva el modo pantalla completa para el texto
   */
  function toggleFullscreenText() {
    fullscreenText.value = !fullscreenText.value
  }

  /**
   * Colapsa ambos paneles (para enfocarse en el texto)
   */
  function focusMode() {
    leftPanel.value.expanded = false
    rightPanel.value.expanded = false
  }

  /**
   * Expande ambos paneles
   */
  function normalMode() {
    leftPanel.value.expanded = true
    rightPanel.value.expanded = true
  }

  /**
   * Establece el filtro de severidad para alertas
   */
  function setAlertSeverityFilter(severity: string | null) {
    alertSeverityFilter.value = severity
  }

  /**
   * Navega a las menciones de una entidad en el texto
   */
  function navigateToEntityMentions(entityId: number) {
    selectedEntityForMentions.value = entityId
    setActiveTab('text')
  }

  /**
   * Navega a una posición específica en el texto
   * @param position Posición de carácter (dentro del capítulo si chapterId se proporciona, sino global)
   * @param text Texto a resaltar (opcional, para mejor precisión)
   * @param chapterId ID del capítulo (opcional, para navegación directa)
   */
  function navigateToTextPosition(position: number, text?: string, chapterId?: number | null) {
    scrollToPosition.value = position
    scrollToText.value = text || null
    scrollToChapterId.value = chapterId || null
    setActiveTab('text')
  }

  /**
   * Limpia la posición de scroll pendiente
   */
  function clearScrollToPosition() {
    scrollToPosition.value = null
    scrollToText.value = null
    scrollToChapterId.value = null
  }

  /**
   * Resetea el workspace al estado inicial
   */
  function reset() {
    activeTab.value = 'text'
    leftPanel.value = {
      expanded: true,
      width: 280,
      minWidth: 200,
      maxWidth: 400
    }
    rightPanel.value = {
      expanded: true,
      width: 320,
      minWidth: 250,
      maxWidth: 500
    }
    textScrollPosition.value = 0
    currentChapter.value = null
    fullscreenText.value = false
    navigationHistory.value = []
    alertSeverityFilter.value = null
    selectedEntityForMentions.value = null
    scrollToPosition.value = null
    scrollToText.value = null
    scrollToChapterId.value = null
  }

  return {
    // Estado
    activeTab,
    leftPanel,
    rightPanel,
    textScrollPosition,
    currentChapter,
    fullscreenText,
    navigationHistory,
    alertSeverityFilter,
    selectedEntityForMentions,
    scrollToPosition,
    scrollToText,
    scrollToChapterId,

    // Getters
    centerWidth,
    canGoBack,
    tabs,
    currentLayoutConfig,
    shouldShowLeftPanel,
    shouldShowRightPanel,
    availableSidebarTabs,

    // Acciones
    setActiveTab,
    goBack,
    toggleLeftPanel,
    toggleRightPanel,
    setLeftPanelWidth,
    setRightPanelWidth,
    adjustLeftPanelWidth,
    adjustRightPanelWidth,
    saveTextScroll,
    setCurrentChapter,
    toggleFullscreenText,
    focusMode,
    normalMode,
    setAlertSeverityFilter,
    navigateToEntityMentions,
    navigateToTextPosition,
    clearScrollToPosition,
    reset
  }
})
