import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ChapterInspector from './ChapterInspector.vue'
import type { Chapter, Entity, Alert } from '@/types'

// Mock del API client
vi.mock('@/services/apiClient', () => ({
  api: {
    getRaw: vi.fn(async () => ({
      success: true,
      data: {
        chapterNumber: 1,
        chapterTitle: 'Capítulo de prueba',
        wordCount: 1000,
        charactersPresent: [],
        newCharacters: [],
        returningCharacters: [],
        keyEvents: [],
        llmEvents: [],
        totalInteractions: 0,
        conflictInteractions: 0,
        positiveInteractions: 0,
        dominantTone: 'neutral',
        locationsMentioned: [],
        autoSummary: 'Resumen automático',
        llmSummary: null,
      },
    })),
  },
}))

// Mock del servicio de eventos
vi.mock('@/services/events', () => ({
  getChapterEvents: vi.fn(async () => ({
    success: true,
    data: {
      events: [],
      stats: {
        total: 0,
        byCategory: {},
        byTone: {},
      },
    },
  })),
}))

describe('ChapterInspector', () => {
  const mockChapter: Chapter = {
    id: 1,
    chapterNumber: 1,
    title: 'Capítulo 1',
    content: 'Contenido del capítulo',
    positionStart: 0,
    positionEnd: 100,
    wordCount: 50,
  }

  const mockEntities: Entity[] = [
    {
      id: 1,
      projectId: 1,
      name: 'Juan',
      type: 'character',
      mentionCount: 10,
      firstMentionChapter: 1,
      firstMentionPosition: 10,
      entityIds: [],
    },
    {
      id: 2,
      projectId: 1,
      name: 'María',
      type: 'character',
      mentionCount: 8,
      firstMentionChapter: 1,
      firstMentionPosition: 50,
      entityIds: [],
    },
  ]

  const mockAlerts: Alert[] = [
    {
      id: 1,
      category: 'consistency',
      status: 'active',
      severity: 'high',
      title: 'Alert alta',
      spanStart: 10,
      spanEnd: 20,
      entityIds: [],
      chapter: 1,  // usa 'chapter' no 'chapterId'
    },
    {
      id: 2,
      category: 'grammar',
      status: 'active',
      severity: 'medium',
      title: 'Alert media',
      spanStart: 30,
      spanEnd: 40,
      entityIds: [],
      chapter: 1,
    },
    {
      id: 3,
      category: 'style',
      status: 'active',
      severity: 'low',
      title: 'Alert baja',
      spanStart: 50,
      spanEnd: 60,
      entityIds: [],
      chapter: 2,
    },
  ]

  describe('Rendering básico', () => {
    it('monta el componente correctamente', () => {
      const wrapper = mount(ChapterInspector, {
        props: {
          chapter: mockChapter,
          projectId: 1,
        },
        global: {
          stubs: {
            Button: true,
            Tag: true,
            Accordion: true,
            AccordionPanel: true,
            AccordionHeader: true,
            AccordionContent: true,
            ProgressSpinner: true,
            EventsExportDialog: true,
            EventStatsCard: true,
          },
        },
      })
      expect(wrapper.exists()).toBe(true)
    })

    it('muestra el título del capítulo', () => {
      const wrapper = mount(ChapterInspector, {
        props: {
          chapter: mockChapter,
          projectId: 1,
        },
        global: {
          stubs: {
            Button: true,
            Tag: true,
            Accordion: true,
            AccordionPanel: true,
            AccordionHeader: true,
            AccordionContent: true,
            ProgressSpinner: true,
            EventsExportDialog: true,
            EventStatsCard: true,
          },
        },
      })
      expect(wrapper.text()).toContain('Capítulo 1')
    })

    it('muestra el conteo de palabras', () => {
      const wrapper = mount(ChapterInspector, {
        props: {
          chapter: mockChapter,
          projectId: 1,
        },
        global: {
          stubs: {
            Button: true,
            Tag: true,
            Accordion: true,
            AccordionPanel: true,
            AccordionHeader: true,
            AccordionContent: true,
            ProgressSpinner: true,
            EventsExportDialog: true,
            EventStatsCard: true,
          },
        },
      })
      expect(wrapper.text()).toContain('50')
    })
  })

  describe('Chapter alerts', () => {
    it('filtra alertas del capítulo actual', () => {
      const wrapper = mount(ChapterInspector, {
        props: {
          chapter: mockChapter,
          projectId: 1,
          alerts: mockAlerts,
        },
        global: {
          stubs: {
            Button: true,
            Tag: true,
            Accordion: true,
            AccordionPanel: true,
            AccordionHeader: true,
            AccordionContent: true,
            ProgressSpinner: true,
            EventsExportDialog: true,
            EventStatsCard: true,
          },
        },
      })

      const chapterAlerts = wrapper.vm.chapterAlerts
      // Solo las 2 primeras alertas son del capítulo 1
      expect(chapterAlerts.length).toBe(2)
      expect(chapterAlerts.every((a: Alert) => a.chapter === 1)).toBe(true)
    })

    it('devuelve array vacío cuando no hay alertas', () => {
      const wrapper = mount(ChapterInspector, {
        props: {
          chapter: mockChapter,
          projectId: 1,
        },
        global: {
          stubs: {
            Button: true,
            Tag: true,
            Accordion: true,
            AccordionPanel: true,
            AccordionHeader: true,
            AccordionContent: true,
            ProgressSpinner: true,
            EventsExportDialog: true,
            EventStatsCard: true,
          },
        },
      })

      const chapterAlerts = wrapper.vm.chapterAlerts
      expect(chapterAlerts).toEqual([])
    })

    it('cuenta correctamente alertas por severidad', () => {
      const wrapper = mount(ChapterInspector, {
        props: {
          chapter: mockChapter,
          projectId: 1,
          alerts: mockAlerts,
        },
        global: {
          stubs: {
            Button: true,
            Tag: true,
            Accordion: true,
            AccordionPanel: true,
            AccordionHeader: true,
            AccordionContent: true,
            ProgressSpinner: true,
            EventsExportDialog: true,
            EventStatsCard: true,
          },
        },
      })

      const alertCounts = wrapper.vm.alertCounts
      expect(alertCounts.high).toBe(1)
      expect(alertCounts.medium).toBe(1)
      expect(alertCounts.low).toBe(0) // La alerta baja es del capítulo 2
    })
  })

  describe('Events', () => {
    it('emite evento al hacer click en back-to-document', async () => {
      const wrapper = mount(ChapterInspector, {
        props: {
          chapter: mockChapter,
          projectId: 1,
        },
        global: {
          stubs: {
            Button: true,
            Tag: true,
            Accordion: true,
            AccordionPanel: true,
            AccordionHeader: true,
            AccordionContent: true,
            ProgressSpinner: true,
            EventsExportDialog: true,
            EventStatsCard: true,
          },
        },
      })

      wrapper.vm.$emit('back-to-document')
      expect(wrapper.emitted('back-to-document')).toBeTruthy()
    })

    it('emite evento al hacer click en go-to-start', async () => {
      const wrapper = mount(ChapterInspector, {
        props: {
          chapter: mockChapter,
          projectId: 1,
        },
        global: {
          stubs: {
            Button: true,
            Tag: true,
            Accordion: true,
            AccordionPanel: true,
            AccordionHeader: true,
            AccordionContent: true,
            ProgressSpinner: true,
            EventsExportDialog: true,
            EventStatsCard: true,
          },
        },
      })

      wrapper.vm.$emit('go-to-start')
      expect(wrapper.emitted('go-to-start')).toBeTruthy()
    })
  })

  describe('Edge cases', () => {
    it('maneja capítulo sin título', () => {
      const chapterWithoutTitle: Chapter = {
        ...mockChapter,
        title: '',
      }

      const wrapper = mount(ChapterInspector, {
        props: {
          chapter: chapterWithoutTitle,
          projectId: 1,
        },
        global: {
          stubs: {
            Button: true,
            Tag: true,
            Accordion: true,
            AccordionPanel: true,
            AccordionHeader: true,
            AccordionContent: true,
            ProgressSpinner: true,
            EventsExportDialog: true,
            EventStatsCard: true,
          },
        },
      })

      expect(wrapper.exists()).toBe(true)
    })

    it('maneja capítulo con wordCount 0', () => {
      const emptyChapter: Chapter = {
        ...mockChapter,
        wordCount: 0,
      }

      const wrapper = mount(ChapterInspector, {
        props: {
          chapter: emptyChapter,
          projectId: 1,
        },
        global: {
          stubs: {
            Button: true,
            Tag: true,
            Accordion: true,
            AccordionPanel: true,
            AccordionHeader: true,
            AccordionContent: true,
            ProgressSpinner: true,
            EventsExportDialog: true,
            EventStatsCard: true,
          },
        },
      })

      expect(wrapper.text()).toContain('0')
    })
  })
})
