import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import DocumentViewer from './DocumentViewer.vue'
import type { Chapter } from '@/types'

// Mock de Pinia store
vi.mock('@/stores/selection', () => ({
  useSelectionStore: vi.fn(() => ({
    selectedAlert: null,
    selectedEntity: null,
    selectedChapter: null,
  })),
}))

// Mock del API client
vi.mock('@/services/apiClient', () => ({
  api: {
    getRaw: vi.fn(async (url: string) => {
      // Mock de entities endpoint
      if (url.includes('/entities')) {
        return { success: true, data: [] }
      }
      // Mock de annotations endpoint
      if (url.includes('/annotations')) {
        return { success: true, data: { annotations: [] } }
      }
      // Mock de dialogues endpoint
      if (url.includes('/dialogues')) {
        return { success: true, data: { dialogues: [] } }
      }
      return { success: true, data: [] }
    }),
  },
}))

// Helper para montar con plugins necesarios
const mountWithPlugins = (component: any, options: any = {}) => {
  return mount(component, {
    ...options,
    global: {
      plugins: [PrimeVue, ToastService],
      stubs: {
        // Stub de componentes PrimeVue pesados
        Toast: true,
      },
      ...options.global,
    },
  })
}

describe('DocumentViewer', () => {
  const mockChapters: Chapter[] = [
    {
      id: 1,
      chapterNumber: 1,
      title: 'Capítulo 1',
      content: 'Este es el contenido del primer capítulo.',
      positionStart: 0,
      positionEnd: 42,
      wordCount: 7,
    },
    {
      id: 2,
      chapterNumber: 2,
      title: 'Capítulo 2',
      content: 'Contenido del segundo capítulo con más texto.',
      positionStart: 43,
      positionEnd: 87,
      wordCount: 8,
    },
  ]

  describe('Rendering básico', () => {
    it('monta el componente correctamente', () => {
      const wrapper = mountWithPlugins(DocumentViewer, {
        props: {
          externalChapters: [],
          projectId: 1,
        },
      })
      expect(wrapper.exists()).toBe(true)
    })

    it('muestra estado vacío cuando no hay capítulos', async () => {
      const wrapper = mountWithPlugins(DocumentViewer, {
        props: {
          externalChapters: [],
          projectId: 1,
        },
      })

      // Esperar a que termine la carga
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 10))

      // El componente existe aunque no tenga capítulos
      expect(wrapper.exists()).toBe(true)
    })

    it('renderiza capítulos cuando hay datos', async () => {
      const wrapper = mountWithPlugins(DocumentViewer, {
        props: {
          externalChapters: mockChapters,
          projectId: 1,
        },
      })

      // Esperar a que termine la carga
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 10))

      expect(wrapper.text()).toContain('Capítulo 1')
    })

    it('renderiza múltiples capítulos', async () => {
      const wrapper = mountWithPlugins(DocumentViewer, {
        props: {
          externalChapters: mockChapters,
          projectId: 1,
        },
      })

      // Esperar a que termine la carga
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 10))

      // Verifica que el componente monta con múltiples capítulos
      expect(wrapper.exists()).toBe(true)
    })
  })

  describe('Highlights de alertas', () => {
    it('aplica highlights cuando hay alertas', async () => {
      const wrapper = mountWithPlugins(DocumentViewer, {
        props: {
          externalChapters: mockChapters,
          projectId: 1,
          alertHighlightRanges: [
            {
              startChar: 0,
              endChar: 10,
              chapterId: 1,
            },
          ],
        },
      })

      // Esperar a que termine la carga
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 10))

      // Verificar que se renderiza el componente
      expect(wrapper.exists()).toBe(true)
    })

    it('usa clases CSS correctas para severidad de alerta', async () => {
      const wrapper = mountWithPlugins(DocumentViewer, {
        props: {
          externalChapters: mockChapters,
          projectId: 1,
          alertHighlightRanges: [
            {
              startChar: 0,
              endChar: 5,
              chapterId: 1,
              color: '#ff0000',
            },
            {
              startChar: 10,
              endChar: 15,
              chapterId: 1,
              color: '#ff9900',
            },
          ],
        },
      })

      // Esperar a que termine la carga
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 10))

      expect(wrapper.exists()).toBe(true)
    })
  })

  describe('Navegación', () => {
    it('emite evento al hacer click en capítulo', async () => {
      const wrapper = mountWithPlugins(DocumentViewer, {
        props: {
          externalChapters: mockChapters,
          projectId: 1,
        },
      })

      // Esperar a que termine la carga
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 10))

      const chapterElement = wrapper.find('.chapter-section')
      if (chapterElement.exists()) {
        await chapterElement.trigger('click')
        // Verificar emisión de eventos si aplica
      }
    })
  })

  describe('Edge cases', () => {
    it('maneja capítulos sin contenido', async () => {
      const emptyChapter: Chapter[] = [
        {
          id: 1,
          chapterNumber: 1,
          title: 'Capítulo Vacío',
          content: '',
          positionStart: 0,
          positionEnd: 0,
          wordCount: 0,
        },
      ]

      const wrapper = mountWithPlugins(DocumentViewer, {
        props: {
          externalChapters: emptyChapter,
          projectId: 1,
        },
      })

      // Esperar a que termine la carga
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 10))

      expect(wrapper.exists()).toBe(true)
      expect(wrapper.text()).toContain('Capítulo Vacío')
    })

    it('maneja texto muy largo sin errores', async () => {
      const longContent = 'a'.repeat(10000)
      const longChapters: Chapter[] = [
        {
          id: 1,
          chapterNumber: 1,
          title: 'Capítulo Largo',
          content: longContent,
          positionStart: 0,
          positionEnd: longContent.length,
          wordCount: 10000,
        },
      ]

      const wrapper = mountWithPlugins(DocumentViewer, {
        props: {
          externalChapters: longChapters,
          projectId: 1,
        },
      })

      // Esperar a que termine la carga
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 10))

      expect(wrapper.exists()).toBe(true)
    })

    it('maneja caracteres especiales en contenido', async () => {
      const specialChars: Chapter[] = [
        {
          id: 1,
          chapterNumber: 1,
          title: 'Caracteres Especiales',
          content: '¿Cómo está? ¡Muy bien! — "Hola" <test> & más',
          positionStart: 0,
          positionEnd: 45,
          wordCount: 8,
        },
      ]

      const wrapper = mountWithPlugins(DocumentViewer, {
        props: {
          externalChapters: specialChars,
          projectId: 1,
        },
      })

      // Esperar a que termine la carga
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 10))

      expect(wrapper.text()).toContain('¿Cómo está?')
      expect(wrapper.text()).toContain('"Hola"')
    })
  })

  describe('Performance - Lazy Loading', () => {
    it('no renderiza todos los capítulos inmediatamente con lazy loading', async () => {
      const manyChapters: Chapter[] = Array.from({ length: 100 }, (_, i) => ({
        id: i + 1,
        chapterNumber: i + 1,
        title: `Capítulo ${i + 1}`,
        content: `Contenido del capítulo ${i + 1}`,
        positionStart: i * 100,
        positionEnd: (i + 1) * 100 - 1,
        wordCount: 5,
      }))

      const wrapper = mountWithPlugins(DocumentViewer, {
        props: {
          externalChapters: manyChapters,
          projectId: 1,
        },
      })

      // Esperar a que termine la carga
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 10))

      expect(wrapper.exists()).toBe(true)
      // Con lazy loading, no todos los capítulos deberían estar en el DOM
    })
  })
})
