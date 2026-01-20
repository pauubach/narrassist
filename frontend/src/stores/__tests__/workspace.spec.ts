import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useWorkspaceStore, TAB_LAYOUT_CONFIG } from '../workspace'

describe('workspaceStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('initial state', () => {
    it('should start with text tab active', () => {
      const store = useWorkspaceStore()
      expect(store.activeTab).toBe('text')
    })

    it('should have left panel expanded by default', () => {
      const store = useWorkspaceStore()
      expect(store.leftPanel.expanded).toBe(true)
      expect(store.leftPanel.width).toBe(280)
    })

    it('should have right panel expanded by default', () => {
      const store = useWorkspaceStore()
      expect(store.rightPanel.expanded).toBe(true)
      expect(store.rightPanel.width).toBe(320)
    })
  })

  describe('setActiveTab', () => {
    it('should change the active tab', () => {
      const store = useWorkspaceStore()
      store.setActiveTab('entities')
      expect(store.activeTab).toBe('entities')
    })

    it('should add previous tab to navigation history', () => {
      const store = useWorkspaceStore()
      store.setActiveTab('entities')
      expect(store.navigationHistory).toHaveLength(1)
      expect(store.navigationHistory[0].tab).toBe('text')
    })

    it('should not add to history when addToHistory is false', () => {
      const store = useWorkspaceStore()
      store.setActiveTab('entities', false)
      expect(store.navigationHistory).toHaveLength(0)
    })

    it('should not change if already on that tab', () => {
      const store = useWorkspaceStore()
      store.setActiveTab('text')
      expect(store.navigationHistory).toHaveLength(0)
    })
  })

  describe('goBack', () => {
    it('should return to previous tab', () => {
      const store = useWorkspaceStore()
      store.setActiveTab('entities')
      store.setActiveTab('alerts')
      store.goBack()
      expect(store.activeTab).toBe('entities')
    })

    it('should reduce navigation history', () => {
      const store = useWorkspaceStore()
      store.setActiveTab('entities')
      store.goBack()
      expect(store.navigationHistory).toHaveLength(0)
    })
  })

  describe('TAB_LAYOUT_CONFIG', () => {
    it('should show both panels for text tab', () => {
      expect(TAB_LAYOUT_CONFIG.text.showLeftPanel).toBe(true)
      expect(TAB_LAYOUT_CONFIG.text.showRightPanel).toBe(true)
      expect(TAB_LAYOUT_CONFIG.text.sidebarTabs).toEqual(['chapters', 'alerts', 'characters'])
    })

    it('should hide both panels for entities tab (full-width)', () => {
      expect(TAB_LAYOUT_CONFIG.entities.showLeftPanel).toBe(false)
      expect(TAB_LAYOUT_CONFIG.entities.showRightPanel).toBe(false)
      expect(TAB_LAYOUT_CONFIG.entities.sidebarTabs).toEqual([])
    })

    it('should hide left panel for relationships tab', () => {
      expect(TAB_LAYOUT_CONFIG.relationships.showLeftPanel).toBe(false)
      expect(TAB_LAYOUT_CONFIG.relationships.showRightPanel).toBe(true)
    })

    it('should show left panel for alerts tab (sidebar with filters)', () => {
      expect(TAB_LAYOUT_CONFIG.alerts.showLeftPanel).toBe(true)
      expect(TAB_LAYOUT_CONFIG.alerts.showRightPanel).toBe(true)
    })

    it('should hide both panels for summary tab (full-width)', () => {
      expect(TAB_LAYOUT_CONFIG.summary.showLeftPanel).toBe(false)
      expect(TAB_LAYOUT_CONFIG.summary.showRightPanel).toBe(false)
    })
  })

  describe('shouldShowLeftPanel computed', () => {
    it('should return true when on text tab', () => {
      const store = useWorkspaceStore()
      store.setActiveTab('text', false)
      expect(store.shouldShowLeftPanel).toBe(true)
    })

    it('should return false when on entities tab', () => {
      const store = useWorkspaceStore()
      store.setActiveTab('entities', false)
      expect(store.shouldShowLeftPanel).toBe(false)
    })

    it('should return false when on summary tab', () => {
      const store = useWorkspaceStore()
      store.setActiveTab('summary', false)
      expect(store.shouldShowLeftPanel).toBe(false)
    })
  })

  describe('shouldShowRightPanel computed', () => {
    it('should return true when on text tab', () => {
      const store = useWorkspaceStore()
      store.setActiveTab('text', false)
      expect(store.shouldShowRightPanel).toBe(true)
    })

    it('should return false when on entities tab (full-width view)', () => {
      const store = useWorkspaceStore()
      store.setActiveTab('entities', false)
      expect(store.shouldShowRightPanel).toBe(false)
    })

    it('should return false when on summary tab', () => {
      const store = useWorkspaceStore()
      store.setActiveTab('summary', false)
      expect(store.shouldShowRightPanel).toBe(false)
    })
  })

  describe('availableSidebarTabs computed', () => {
    it('should return all sidebar tabs for text tab', () => {
      const store = useWorkspaceStore()
      store.setActiveTab('text', false)
      expect(store.availableSidebarTabs).toEqual(['chapters', 'alerts', 'characters'])
    })

    it('should return empty array for entities tab', () => {
      const store = useWorkspaceStore()
      store.setActiveTab('entities', false)
      expect(store.availableSidebarTabs).toEqual([])
    })
  })

  describe('panel width actions', () => {
    it('should set left panel width within bounds', () => {
      const store = useWorkspaceStore()
      store.setLeftPanelWidth(300)
      expect(store.leftPanel.width).toBe(300)
    })

    it('should clamp left panel width to min', () => {
      const store = useWorkspaceStore()
      store.setLeftPanelWidth(100)
      expect(store.leftPanel.width).toBe(store.leftPanel.minWidth)
    })

    it('should clamp left panel width to max', () => {
      const store = useWorkspaceStore()
      store.setLeftPanelWidth(600)
      expect(store.leftPanel.width).toBe(store.leftPanel.maxWidth)
    })

    it('should set right panel width within bounds', () => {
      const store = useWorkspaceStore()
      store.setRightPanelWidth(400)
      expect(store.rightPanel.width).toBe(400)
    })
  })

  describe('toggle panels', () => {
    it('should toggle left panel', () => {
      const store = useWorkspaceStore()
      expect(store.leftPanel.expanded).toBe(true)
      store.toggleLeftPanel()
      expect(store.leftPanel.expanded).toBe(false)
      store.toggleLeftPanel()
      expect(store.leftPanel.expanded).toBe(true)
    })

    it('should toggle right panel', () => {
      const store = useWorkspaceStore()
      expect(store.rightPanel.expanded).toBe(true)
      store.toggleRightPanel()
      expect(store.rightPanel.expanded).toBe(false)
    })
  })

  describe('focusMode', () => {
    it('should collapse both panels', () => {
      const store = useWorkspaceStore()
      store.focusMode()
      expect(store.leftPanel.expanded).toBe(false)
      expect(store.rightPanel.expanded).toBe(false)
    })
  })

  describe('normalMode', () => {
    it('should expand both panels', () => {
      const store = useWorkspaceStore()
      store.focusMode()
      store.normalMode()
      expect(store.leftPanel.expanded).toBe(true)
      expect(store.rightPanel.expanded).toBe(true)
    })
  })

  describe('reset', () => {
    it('should reset to initial state', () => {
      const store = useWorkspaceStore()
      store.setActiveTab('alerts')
      store.setLeftPanelWidth(350)
      store.toggleRightPanel()

      store.reset()

      expect(store.activeTab).toBe('text')
      expect(store.leftPanel.width).toBe(280)
      expect(store.rightPanel.expanded).toBe(true)
      expect(store.navigationHistory).toHaveLength(0)
    })
  })
})
