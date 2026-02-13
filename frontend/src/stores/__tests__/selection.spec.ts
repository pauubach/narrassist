import { setActivePinia, createPinia } from 'pinia'
import { useSelectionStore } from '../selection'
import type { Entity, Alert } from '@/types'

// Mock entities - usando los tipos correctos del dominio
const mockEntity1: Entity = {
  id: 1,
  projectId: 1,
  name: 'Ana García',
  type: 'character',
  mentionCount: 5,
  aliases: ['Ana', 'Anita'],
  importance: 'main',
  isActive: true,
  firstMentionChapter: 1,
  mergedFromIds: [],
}

const mockEntity2: Entity = {
  id: 2,
  projectId: 1,
  name: 'Madrid',
  type: 'location',
  mentionCount: 3,
  aliases: [],
  importance: 'secondary',
  isActive: true,
  firstMentionChapter: 1,
  mergedFromIds: [],
}

const mockEntity3: Entity = {
  id: 3,
  projectId: 1,
  name: 'Pedro Lopez',
  type: 'character',
  mentionCount: 2,
  aliases: ['Pedro'],
  importance: 'secondary',
  isActive: true,
  firstMentionChapter: 2,
  mergedFromIds: [],
}

// Mock alerts - usando los tipos correctos del dominio
const mockAlert1: Alert = {
  id: 1,
  projectId: 1,
  category: 'attribute',
  severity: 'high',
  title: 'Character age inconsistency',
  description: 'Ana is 25 in chapter 1 but 30 in chapter 2',
  chapter: 2,
  status: 'active',
  entityIds: [1],
  confidence: 0.95,
  createdAt: new Date()
}

const _mockAlert2: Alert = {
  id: 2,
  projectId: 1,
  category: 'location',
  severity: 'medium',
  title: 'Location continuity error',
  description: 'Madrid described differently',
  chapter: 3,
  status: 'active',
  entityIds: [2],
  confidence: 0.85,
  createdAt: new Date()
}

describe('selectionStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('initial state', () => {
    it('should start with no selection', () => {
      const store = useSelectionStore()
      expect(store.primary).toBeNull()
      expect(store.secondary).toEqual([])
      expect(store.hasSelection).toBe(false)
    })

    it('should not have multi-select mode enabled', () => {
      const store = useSelectionStore()
      expect(store.multiSelectMode).toBe(false)
    })

    it('should not have text selection', () => {
      const store = useSelectionStore()
      expect(store.textSelection).toBeNull()
    })

    it('should not have hovered element', () => {
      const store = useSelectionStore()
      expect(store.hovered).toBeNull()
    })
  })

  describe('selectEntity', () => {
    it('should select an entity as primary', () => {
      const store = useSelectionStore()
      store.selectEntity(mockEntity1)

      expect(store.primary).not.toBeNull()
      expect(store.primary?.type).toBe('entity')
      expect(store.primary?.id).toBe(1)
      expect(store.primary?.data).toEqual(mockEntity1)
    })

    it('should replace previous selection', () => {
      const store = useSelectionStore()
      store.selectEntity(mockEntity1)
      store.selectEntity(mockEntity2)

      expect(store.primary?.id).toBe(2)
      expect(store.count).toBe(1)
    })

    it('should clear secondary selections on new select', () => {
      const store = useSelectionStore()
      store.setMultiSelectMode(true)
      store.selectEntity(mockEntity1)
      store.selectEntity(mockEntity2)
      store.setMultiSelectMode(false)
      store.selectEntity(mockEntity3)

      expect(store.secondary).toHaveLength(0)
    })
  })

  describe('selectAlert', () => {
    it('should select an alert as primary', () => {
      const store = useSelectionStore()
      store.selectAlert(mockAlert1)

      expect(store.primary?.type).toBe('alert')
      expect(store.primary?.id).toBe(1)
    })
  })

  describe('selectedEntityIds computed', () => {
    it('should return empty array when no entities selected', () => {
      const store = useSelectionStore()
      expect(store.selectedEntityIds).toEqual([])
    })

    it('should return primary entity id', () => {
      const store = useSelectionStore()
      store.selectEntity(mockEntity1)
      expect(store.selectedEntityIds).toContain(1)
    })

    it('should return all entity ids including secondary', () => {
      const store = useSelectionStore()
      store.setMultiSelectMode(true)
      store.selectEntity(mockEntity1)
      store.selectEntity(mockEntity2)

      expect(store.selectedEntityIds).toContain(1)
      expect(store.selectedEntityIds).toContain(2)
    })

    it('should not include alert ids', () => {
      const store = useSelectionStore()
      store.selectAlert(mockAlert1)
      expect(store.selectedEntityIds).toEqual([])
    })
  })

  describe('selectedAlertIds computed', () => {
    it('should return alert ids', () => {
      const store = useSelectionStore()
      store.selectAlert(mockAlert1)
      expect(store.selectedAlertIds).toContain(1)
    })

    it('should not include entity ids', () => {
      const store = useSelectionStore()
      store.selectEntity(mockEntity1)
      expect(store.selectedAlertIds).toEqual([])
    })
  })

  describe('multiSelectMode', () => {
    it('should add to secondary when enabled', () => {
      const store = useSelectionStore()
      store.selectEntity(mockEntity1)
      store.setMultiSelectMode(true)
      store.selectEntity(mockEntity2)

      expect(store.primary?.id).toBe(1)
      expect(store.secondary).toHaveLength(1)
      expect(store.secondary[0].id).toBe(2)
    })

    it('should clear secondary when disabled', () => {
      const store = useSelectionStore()
      store.selectEntity(mockEntity1)
      store.setMultiSelectMode(true)
      store.selectEntity(mockEntity2)
      store.setMultiSelectMode(false)

      expect(store.secondary).toHaveLength(0)
      expect(store.primary?.id).toBe(1)
    })

    it('should not add duplicates to secondary', () => {
      const store = useSelectionStore()
      store.selectEntity(mockEntity1)
      store.setMultiSelectMode(true)
      store.selectEntity(mockEntity1) // Same entity

      expect(store.secondary).toHaveLength(0)
    })
  })

  describe('isSelected', () => {
    it('should return true for primary selection', () => {
      const store = useSelectionStore()
      store.selectEntity(mockEntity1)
      expect(store.isSelected('entity', 1)).toBe(true)
    })

    it('should return true for secondary selection', () => {
      const store = useSelectionStore()
      store.selectEntity(mockEntity1)
      store.setMultiSelectMode(true)
      store.selectEntity(mockEntity2)

      expect(store.isSelected('entity', 2)).toBe(true)
    })

    it('should return false for unselected items', () => {
      const store = useSelectionStore()
      store.selectEntity(mockEntity1)
      expect(store.isSelected('entity', 999)).toBe(false)
    })

    it('should return false for different type with same id', () => {
      const store = useSelectionStore()
      store.selectEntity(mockEntity1)
      expect(store.isSelected('alert', 1)).toBe(false)
    })
  })

  describe('toggle', () => {
    it('should select if not already selected', () => {
      const store = useSelectionStore()
      store.toggle('entity', 1, mockEntity1)
      expect(store.isSelected('entity', 1)).toBe(true)
    })

    it('should deselect primary and promote secondary', () => {
      const store = useSelectionStore()
      // Use selectEntities to have multiple selections without multiSelectMode clearing them
      store.selectEntities([mockEntity1, mockEntity2])

      // Now toggle off the primary (entity1)
      store.toggle('entity', 1)

      // entity2 should be promoted to primary
      expect(store.primary?.id).toBe(2)
    })

    it('should remove from secondary when toggled off', () => {
      const store = useSelectionStore()
      store.selectEntity(mockEntity1)
      store.setMultiSelectMode(true)
      store.selectEntity(mockEntity2)

      store.toggle('entity', 2)

      expect(store.secondary).toHaveLength(0)
      expect(store.primary?.id).toBe(1)
    })
  })

  describe('setTextSelection', () => {
    it('should set text selection', () => {
      const store = useSelectionStore()
      const selection = {
        start: 0,
        end: 10,
        text: 'Hello test',
        chapter: 'Chapter 1'
      }

      store.setTextSelection(selection)
      expect(store.textSelection).toEqual(selection)
    })

    it('should clear text selection with null', () => {
      const store = useSelectionStore()
      store.setTextSelection({ start: 0, end: 10, text: 'test' })
      store.setTextSelection(null)
      expect(store.textSelection).toBeNull()
    })
  })

  describe('setHovered', () => {
    it('should set hovered element', () => {
      const store = useSelectionStore()
      store.setHovered('entity', 1, mockEntity1)

      expect(store.hovered).not.toBeNull()
      expect(store.hovered?.type).toBe('entity')
      expect(store.hovered?.id).toBe(1)
    })

    it('should clear hovered with null type', () => {
      const store = useSelectionStore()
      store.setHovered('entity', 1)
      store.setHovered(null)
      expect(store.hovered).toBeNull()
    })
  })

  describe('clearPrimary', () => {
    it('should clear only primary selection', () => {
      const store = useSelectionStore()
      store.selectEntity(mockEntity1)
      store.setMultiSelectMode(true)
      store.selectEntity(mockEntity2)
      store.setMultiSelectMode(false)

      store.clearPrimary()

      expect(store.primary).toBeNull()
    })
  })

  describe('clearAll', () => {
    it('should clear all selections', () => {
      const store = useSelectionStore()
      store.selectEntity(mockEntity1)
      store.setMultiSelectMode(true)
      store.selectEntity(mockEntity2)
      store.setTextSelection({ start: 0, end: 10, text: 'test' })
      store.setHovered('entity', 3)

      store.clearAll()

      expect(store.primary).toBeNull()
      expect(store.secondary).toHaveLength(0)
      expect(store.textSelection).toBeNull()
      expect(store.hovered).toBeNull()
      expect(store.multiSelectMode).toBe(false)
    })
  })

  describe('clearType', () => {
    it('should clear only entity selections', () => {
      const store = useSelectionStore()
      store.selectEntity(mockEntity1)

      store.clearType('entity')

      expect(store.primary).toBeNull()
    })

    it('should not affect other types', () => {
      const store = useSelectionStore()
      store.selectAlert(mockAlert1)

      store.clearType('entity')

      expect(store.primary?.type).toBe('alert')
    })
  })

  describe('selectEntities (bulk)', () => {
    it('should select multiple entities', () => {
      const store = useSelectionStore()
      store.selectEntities([mockEntity1, mockEntity2, mockEntity3])

      expect(store.primary?.id).toBe(1)
      expect(store.secondary).toHaveLength(2)
      expect(store.count).toBe(3)
    })

    it('should clear when empty array passed', () => {
      const store = useSelectionStore()
      store.selectEntity(mockEntity1)
      store.selectEntities([])

      expect(store.selectedEntityIds).toHaveLength(0)
    })
  })

  describe('getSelectedEntities', () => {
    it('should return all selected entities', () => {
      const store = useSelectionStore()
      store.selectEntities([mockEntity1, mockEntity2])

      const entities = store.getSelectedEntities()

      expect(entities).toHaveLength(2)
      expect(entities[0].name).toBe('Ana García')
      expect(entities[1].name).toBe('Madrid')
    })
  })

  describe('getSelectedAlerts', () => {
    it('should return all selected alerts', () => {
      const store = useSelectionStore()
      store.selectAlert(mockAlert1)

      const alerts = store.getSelectedAlerts()

      expect(alerts).toHaveLength(1)
      expect(alerts[0].title).toBe('Character age inconsistency')
    })
  })

  describe('hasSelection computed', () => {
    it('should return false when no selection', () => {
      const store = useSelectionStore()
      expect(store.hasSelection).toBe(false)
    })

    it('should return true when has primary', () => {
      const store = useSelectionStore()
      store.selectEntity(mockEntity1)
      expect(store.hasSelection).toBe(true)
    })
  })

  describe('hasMultipleSelections computed', () => {
    it('should return false with only primary', () => {
      const store = useSelectionStore()
      store.selectEntity(mockEntity1)
      expect(store.hasMultipleSelections).toBe(false)
    })

    it('should return true with secondary selections', () => {
      const store = useSelectionStore()
      store.selectEntities([mockEntity1, mockEntity2])
      expect(store.hasMultipleSelections).toBe(true)
    })
  })

  describe('count computed', () => {
    it('should count all selections', () => {
      const store = useSelectionStore()
      expect(store.count).toBe(0)

      store.selectEntity(mockEntity1)
      expect(store.count).toBe(1)

      store.setMultiSelectMode(true)
      store.selectEntity(mockEntity2)
      expect(store.count).toBe(2)
    })
  })
})
