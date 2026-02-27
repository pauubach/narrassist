import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import EntityInspector from './EntityInspector.vue'
import type { Entity, Alert } from '@/types'

// Mock de composables
vi.mock('@/composables/useEntityUtils', () => ({
  useEntityUtils: () => ({
    getEntityIcon: (type: string) => 'pi pi-user',
    getEntityLabel: (type: string) => {
      const labels: Record<string, string> = {
        character: 'Personaje',
        location: 'Lugar',
        object: 'Objeto',
      }
      return labels[type] || type
    },
    getEntityColor: (type: string) => '#4CAF50',
  }),
}))

vi.mock('@/composables/useMentionNavigation', () => ({
  useMentionNavigation: () => ({
    isActive: { value: false },
    loadMentions: vi.fn(),
    clear: vi.fn(),
    currentIndex: { value: 0 },
    totalMentions: { value: 0 },
    state: { value: { mentions: [] } },
    goNext: vi.fn(),
    goPrev: vi.fn(),
    highlightMention: vi.fn(),
  }),
}))

vi.mock('@/composables/useAlertUtils', () => ({
  useAlertUtils: () => ({
    formatChapterLabel: (chapter: number) => `Cap. ${chapter}`,
    getSeverityConfig: (severity: string) => ({
      color: '#FF0000',
      label: severity,
    }),
    getCategoryLabel: (category: string) => category,
  }),
}))

// Mock del API client
vi.mock('@/services/apiClient', () => ({
  api: {
    getRaw: vi.fn(async () => ({
      success: true,
      data: { overallConfidence: 0.85 },
    })),
  },
}))

describe('EntityInspector', () => {
  const mockEntity: Entity = {
    id: 1,
    projectId: 1,
    name: 'Juan Pérez',
    type: 'character',
    aliases: ['Juan', 'Juanito'],
    importance: 'main',
    mentionCount: 15,
    firstMentionChapter: 1,
    isActive: true,
    mergedFromIds: [],
  }

  const mockAlerts: Alert[] = [
    {
      id: 1,
      projectId: 1,
      category: 'attribute',
      status: 'active',
      severity: 'high',
      alertType: 'test',
      title: 'Inconsistencia de atributo',
      description: 'Test',
      spanStart: 0,
      spanEnd: 10,
      entityIds: [1],
      confidence: 0.9,
      createdAt: new Date(),
    },
    {
      id: 2,
      projectId: 1,
      category: 'other',
      status: 'active',
      severity: 'medium',
      alertType: 'test',
      title: 'Inconsistencia de nombre',
      description: 'Test',
      spanStart: 20,
      spanEnd: 30,
      entityIds: [1],
      confidence: 0.9,
      createdAt: new Date(),
    },
    {
      id: 3,
      projectId: 1,
      category: 'other',
      status: 'resolved',
      severity: 'low',
      alertType: 'test',
      title: 'Ya resuelta',
      description: 'Test',
      spanStart: 40,
      spanEnd: 50,
      entityIds: [1],
      confidence: 0.9,
      createdAt: new Date(),
    },
  ]

  describe('Rendering básico', () => {
    it('monta el componente correctamente', () => {
      const wrapper = mount(EntityInspector, {
        props: {
          entity: mockEntity,
          projectId: 1,
        },
        global: {
          stubs: {
            Button: true,
            Tag: true,
            InputSwitch: true,
            Slider: true,
            DsBadge: true,
          },
        },
      })
      expect(wrapper.exists()).toBe(true)
    })

    it('muestra el nombre de la entidad', () => {
      const wrapper = mount(EntityInspector, {
        props: {
          entity: mockEntity,
          projectId: 1,
        },
        global: {
          stubs: {
            Button: true,
            Tag: true,
            InputSwitch: true,
            Slider: true,
            DsBadge: true,
          },
        },
      })
      expect(wrapper.text()).toContain('Juan Pérez')
    })

    it('muestra el tipo de entidad', () => {
      const wrapper = mount(EntityInspector, {
        props: {
          entity: mockEntity,
          projectId: 1,
        },
        global: {
          stubs: {
            Button: true,
            Tag: true,
            InputSwitch: true,
            Slider: true,
            DsBadge: true,
          },
        },
      })
      // Verificar que el tipo de entidad se computa correctamente
      expect((wrapper.vm as any).entityTypeLabel).toBe('Personaje')
    })
  })

  describe('Aliases', () => {
    it('muestra los aliases cuando existen', () => {
      const wrapper = mount(EntityInspector, {
        props: {
          entity: mockEntity,
          projectId: 1,
        },
        global: {
          stubs: {
            Button: true,
            Tag: true,
            InputSwitch: true,
            Slider: true,
            DsBadge: true,
          },
        },
      })

      const hasAliases = (wrapper.vm as any).hasAliases
      expect(hasAliases).toBe(true)
    })

    it('no muestra aliases cuando no existen', () => {
      const entityWithoutAliases: Entity = {
        ...mockEntity,
        aliases: [],
      }

      const wrapper = mount(EntityInspector, {
        props: {
          entity: entityWithoutAliases,
          projectId: 1,
        },
        global: {
          stubs: {
            Button: true,
            Tag: true,
            InputSwitch: true,
            Slider: true,
            DsBadge: true,
          },
        },
      })

      const hasAliases = (wrapper.vm as any).hasAliases
      expect(hasAliases).toBe(false)
    })
  })

  describe('Merged entities', () => {
    it('detecta entidad fusionada cuando tiene mergedFromIds', () => {
      const mergedEntity: Entity = {
        ...mockEntity,
        mergedFromIds: [2, 3],
      }

      const wrapper = mount(EntityInspector, {
        props: {
          entity: mergedEntity,
          projectId: 1,
        },
        global: {
          stubs: {
            Button: true,
            Tag: true,
            InputSwitch: true,
            Slider: true,
            DsBadge: true,
          },
        },
      })

      const isMerged = (wrapper.vm as any).isMerged
      expect(isMerged).toBe(true)
    })

    it('no detecta fusión cuando no tiene mergedFromIds', () => {
      const entityWithoutMerge: Entity = {
        ...mockEntity,
        mergedFromIds: [],
      }

      const wrapper = mount(EntityInspector, {
        props: {
          entity: entityWithoutMerge,
          projectId: 1,
        },
        global: {
          stubs: {
            Button: true,
            Tag: true,
            InputSwitch: true,
            Slider: true,
            DsBadge: true,
          },
        },
      })

      const isMerged = (wrapper.vm as any).isMerged
      // isMerged es falsy cuando no hay mergedFromIds
      expect(isMerged).toBeFalsy()
    })
  })

  describe('Related alerts', () => {
    it('filtra alertas relacionadas con la entidad', () => {
      const wrapper = mount(EntityInspector, {
        props: {
          entity: mockEntity,
          projectId: 1,
          alerts: mockAlerts,
        },
        global: {
          stubs: {
            Button: true,
            Tag: true,
            InputSwitch: true,
            Slider: true,
            DsBadge: true,
          },
        },
      })

      const relatedAlerts = (wrapper.vm as any).relatedAlerts
      // Solo alertas activas (2 de 3)
      expect(relatedAlerts.length).toBe(2)
      expect(relatedAlerts.every((a: Alert) => a.entityIds.includes(1))).toBe(true)
      expect(relatedAlerts.every((a: Alert) => a.status === 'active')).toBe(true)
    })

    it('separa alertas de atributos de otras alertas', () => {
      const wrapper = mount(EntityInspector, {
        props: {
          entity: mockEntity,
          projectId: 1,
          alerts: mockAlerts,
        },
        global: {
          stubs: {
            Button: true,
            Tag: true,
            InputSwitch: true,
            Slider: true,
            DsBadge: true,
          },
        },
      })

      const attributeAlerts = (wrapper.vm as any).attributeAlerts
      const otherAlerts = (wrapper.vm as any).otherAlerts

      expect(attributeAlerts.length).toBe(1)
      expect(attributeAlerts[0].category).toBe('attribute')

      expect(otherAlerts.length).toBe(1)
      expect(otherAlerts[0].category).not.toBe('attribute')
    })

    it('devuelve array vacío cuando no hay alertas', () => {
      const wrapper = mount(EntityInspector, {
        props: {
          entity: mockEntity,
          projectId: 1,
        },
        global: {
          stubs: {
            Button: true,
            Tag: true,
            InputSwitch: true,
            Slider: true,
            DsBadge: true,
          },
        },
      })

      const relatedAlerts = (wrapper.vm as any).relatedAlerts
      expect(relatedAlerts).toEqual([])
    })
  })

  describe('Edge cases', () => {
    it('maneja entidad sin aliases definidos', () => {
      const entityWithoutAliases: Entity = {
        ...mockEntity,
        aliases: [],
      }

      const wrapper = mount(EntityInspector, {
        props: {
          entity: entityWithoutAliases,
          projectId: 1,
        },
        global: {
          stubs: {
            Button: true,
            Tag: true,
            InputSwitch: true,
            Slider: true,
            DsBadge: true,
          },
        },
      })

      // hasAliases es falsy cuando no hay aliases
      expect((wrapper.vm as any).hasAliases).toBeFalsy()
    })

    it('limita el número de alertas relacionadas a 5', () => {
      const manyAlerts: Alert[] = Array.from({ length: 10 }, (_, i) => ({
        id: i + 1,
        projectId: 1,
        category: 'attribute' as const,
        status: 'active' as const,
        severity: 'medium' as const,
        alertType: 'test' as const,
        title: `Alert ${i + 1}`,
        description: 'Test',
        spanStart: i * 10,
        spanEnd: (i + 1) * 10,
        entityIds: [1],
        confidence: 0.9,
        createdAt: new Date(),
      }))

      const wrapper = mount(EntityInspector, {
        props: {
          entity: mockEntity,
          projectId: 1,
          alerts: manyAlerts,
        },
        global: {
          stubs: {
            Button: true,
            Tag: true,
            InputSwitch: true,
            Slider: true,
            DsBadge: true,
          },
        },
      })

      const relatedAlerts = (wrapper.vm as any).relatedAlerts
      expect(relatedAlerts.length).toBe(5)
    })
  })
})
