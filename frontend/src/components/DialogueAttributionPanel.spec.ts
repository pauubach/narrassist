import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import DialogueAttributionPanel from './DialogueAttributionPanel.vue'
import type { DialogueAttribution } from '@/types'

// Mock del API client
vi.mock('@/services/apiClient', () => ({
  api: {
    getRaw: vi.fn(async () => ({ success: true, data: {} })),
  },
}))

// Helper para montar con plugins necesarios
const mountWithPlugins = (component: any, options: any = {}) => {
  return mount(component, {
    ...options,
    global: {
      plugins: [PrimeVue, ToastService, createPinia()],
      stubs: {
        Toast: true,
        Select: true,
        Tag: true,
        Button: true,
        ProgressSpinner: true,
      },
      ...options.global,
    },
  })
}

describe('DialogueAttributionPanel', () => {
  const mockChapters = [
    { id: 1, number: 1, title: 'Capítulo 1' },
    { id: 2, number: 2, title: 'Capítulo 2' },
  ]

  const mockEntities = [
    { id: 1, name: 'Juan', entity_type: 'character' },
    { id: 2, name: 'María', entity_type: 'character' },
    { id: 3, name: 'El perro', entity_type: 'animal' },
  ]

  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('Rendering básico', () => {
    it('monta el componente correctamente', () => {
      const wrapper = mountWithPlugins(DialogueAttributionPanel, {
        props: {
          projectId: 1,
          chapters: mockChapters,
        },
      })
      expect(wrapper.exists()).toBe(true)
    })

    it('muestra el título del panel', () => {
      const wrapper = mountWithPlugins(DialogueAttributionPanel, {
        props: {
          projectId: 1,
          chapters: mockChapters,
        },
      })
      expect(wrapper.text()).toContain('Atribución de Diálogos')
    })

    it('muestra estado vacío cuando no hay atribuciones', () => {
      const wrapper = mountWithPlugins(DialogueAttributionPanel, {
        props: {
          projectId: 1,
          chapters: mockChapters,
        },
      })
      expect(wrapper.text()).toContain('No se encontraron diálogos')
    })
  })

  describe('Chapter selector', () => {
    it('renderiza el selector de capítulos', () => {
      const wrapper = mountWithPlugins(DialogueAttributionPanel, {
        props: {
          projectId: 1,
          chapters: mockChapters,
        },
      })
      expect(wrapper.find('.chapter-selector').exists()).toBe(true)
    })

    it('inicializa con el capítulo inicial si se proporciona', () => {
      const wrapper = mountWithPlugins(DialogueAttributionPanel, {
        props: {
          projectId: 1,
          chapters: mockChapters,
          initialChapter: 2,
        },
      })
      expect(wrapper.vm.selectedChapter).toBe(2)
    })
  })

  describe('Speaker correction', () => {
    it('renderiza opciones de hablantes a partir de entidades de tipo character', () => {
      const wrapper = mountWithPlugins(DialogueAttributionPanel, {
        props: {
          projectId: 1,
          chapters: mockChapters,
          entities: mockEntities,
        },
      })

      const speakerOptions = wrapper.vm.speakerOptions
      expect(speakerOptions.length).toBeGreaterThan(0)
      expect(speakerOptions.some((opt: any) => opt.label === 'Juan')).toBe(true)
      expect(speakerOptions.some((opt: any) => opt.label === 'María')).toBe(true)
    })

    it('incluye animales en las opciones de hablantes', () => {
      const wrapper = mountWithPlugins(DialogueAttributionPanel, {
        props: {
          projectId: 1,
          chapters: mockChapters,
          entities: mockEntities,
        },
      })

      const speakerOptions = wrapper.vm.speakerOptions
      expect(speakerOptions.some((opt: any) => opt.label === 'El perro')).toBe(true)
    })

    it('incluye opción "Desconocido" cuando hay personajes', () => {
      const wrapper = mountWithPlugins(DialogueAttributionPanel, {
        props: {
          projectId: 1,
          chapters: mockChapters,
          entities: mockEntities,
        },
      })

      const speakerOptions = wrapper.vm.speakerOptions
      expect(speakerOptions.some((opt: any) => opt.label === 'Desconocido')).toBe(true)
    })

    it('no incluye opción "Desconocido" cuando no hay personajes', () => {
      const wrapper = mountWithPlugins(DialogueAttributionPanel, {
        props: {
          projectId: 1,
          chapters: mockChapters,
          entities: [],
        },
      })

      const speakerOptions = wrapper.vm.speakerOptions
      expect(speakerOptions.length).toBe(0)
    })
  })

  describe('Edge cases', () => {
    it('maneja lista vacía de capítulos', () => {
      const wrapper = mountWithPlugins(DialogueAttributionPanel, {
        props: {
          projectId: 1,
          chapters: [],
        },
      })
      expect(wrapper.exists()).toBe(true)
    })

    it('maneja entities undefined', () => {
      const wrapper = mountWithPlugins(DialogueAttributionPanel, {
        props: {
          projectId: 1,
          chapters: mockChapters,
          // entities: undefined implícito
        },
      })

      const speakerOptions = wrapper.vm.speakerOptions
      expect(speakerOptions).toEqual([])
    })

    it('filtra entidades que no son characters/animals', () => {
      const entitiesWithNonCharacters = [
        { id: 1, name: 'Juan', entity_type: 'character' },
        { id: 2, name: 'Madrid', entity_type: 'location' },
        { id: 3, name: 'Espada', entity_type: 'object' },
      ]

      const wrapper = mountWithPlugins(DialogueAttributionPanel, {
        props: {
          projectId: 1,
          chapters: mockChapters,
          entities: entitiesWithNonCharacters,
        },
      })

      const speakerOptions = wrapper.vm.speakerOptions
      expect(speakerOptions.some((opt: any) => opt.label === 'Juan')).toBe(true)
      expect(speakerOptions.some((opt: any) => opt.label === 'Madrid')).toBe(false)
      expect(speakerOptions.some((opt: any) => opt.label === 'Espada')).toBe(false)
    })

    it('maneja entidades con nombres en diferentes formatos', () => {
      const entitiesWithVariousFormats = [
        { id: 1, name: 'Juan', entity_type: 'character' },
        { id: 2, canonical_name: 'María García', entity_type: 'character' },
        { id: 3, canonicalName: 'Pedro', entity_type: 'character' },
      ]

      const wrapper = mountWithPlugins(DialogueAttributionPanel, {
        props: {
          projectId: 1,
          chapters: mockChapters,
          entities: entitiesWithVariousFormats,
        },
      })

      const speakerOptions = wrapper.vm.speakerOptions
      expect(speakerOptions.some((opt: any) => opt.label === 'Juan')).toBe(true)
      expect(speakerOptions.some((opt: any) => opt.label === 'María García')).toBe(true)
      expect(speakerOptions.some((opt: any) => opt.label === 'Pedro')).toBe(true)
    })
  })
})
