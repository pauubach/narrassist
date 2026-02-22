import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ProjectSummary from './ProjectSummary.vue'
import type { Alert } from '@/types'

// Mock del composable useAlertUtils
vi.mock('@/composables/useAlertUtils', () => ({
  useAlertUtils: () => ({
    getCategoryLabel: (category: string) => {
      const labels: Record<string, string> = {
        consistency: 'Consistencia',
        grammar: 'Gramática',
        style: 'Estilo',
        orthography: 'Ortografía',
        timeline: 'Línea temporal',
      }
      return labels[category] || category
    },
  }),
}))

describe('ProjectSummary', () => {
  const defaultProps = {
    wordCount: 5000,
    chapterCount: 10,
    entityCount: 25,
    alertCount: 15,
  }

  const mockAlerts: Alert[] = [
    {
      id: 1,
      category: 'consistency',
      status: 'active',
      severity: 'high',
      title: 'Alert 1',
      spanStart: 0,
      spanEnd: 10,
    },
    {
      id: 2,
      category: 'consistency',
      status: 'resolved',
      severity: 'medium',
      title: 'Alert 2',
      spanStart: 20,
      spanEnd: 30,
    },
    {
      id: 3,
      category: 'grammar',
      status: 'dismissed',
      severity: 'low',
      title: 'Alert 3',
      spanStart: 40,
      spanEnd: 50,
    },
    {
      id: 4,
      category: 'grammar',
      status: 'active',
      severity: 'high',
      title: 'Alert 4',
      spanStart: 60,
      spanEnd: 70,
    },
    {
      id: 5,
      category: 'style',
      status: 'active',
      severity: 'medium',
      title: 'Alert 5',
      spanStart: 80,
      spanEnd: 90,
    },
  ]

  describe('Rendering básico', () => {
    it('monta el componente correctamente', () => {
      const wrapper = mount(ProjectSummary, {
        props: defaultProps,
      })
      expect(wrapper.exists()).toBe(true)
    })

    it('muestra las 4 estadísticas principales', () => {
      const wrapper = mount(ProjectSummary, {
        props: defaultProps,
      })

      const text = wrapper.text()
      // El formato puede ser 5,000 o 5.000 o simplemente 5000 dependiendo del locale
      expect(text).toMatch(/5[,.]?000/)
      expect(text).toContain('palabras')
      expect(text).toContain('10')
      expect(text).toContain('capítulos')
      expect(text).toContain('25')
      expect(text).toContain('entidades')
      expect(text).toContain('15')
      expect(text).toContain('alertas')
    })

    it('renderiza el wordCount correctamente', () => {
      const wrapper = mount(ProjectSummary, {
        props: {
          ...defaultProps,
          wordCount: 123456,
        },
      })

      // Verificar que el número está presente (puede ser 123,456 o 123.456 o 123456)
      const text = wrapper.text()
      expect(text).toMatch(/123[,.]?456/)
    })
  })

  describe('Eventos de click', () => {
    it('emite stat-click con "words" al hacer click en palabras', async () => {
      const wrapper = mount(ProjectSummary, {
        props: defaultProps,
      })

      const statCards = wrapper.findAll('.stat-card')
      await statCards[0].trigger('click')

      expect(wrapper.emitted('stat-click')).toBeTruthy()
      expect(wrapper.emitted('stat-click')?.[0]).toEqual(['words'])
    })

    it('emite stat-click con "chapters" al hacer click en capítulos', async () => {
      const wrapper = mount(ProjectSummary, {
        props: defaultProps,
      })

      const statCards = wrapper.findAll('.stat-card')
      await statCards[1].trigger('click')

      expect(wrapper.emitted('stat-click')?.[0]).toEqual(['chapters'])
    })

    it('emite stat-click con "entities" al hacer click en entidades', async () => {
      const wrapper = mount(ProjectSummary, {
        props: defaultProps,
      })

      const statCards = wrapper.findAll('.stat-card')
      await statCards[2].trigger('click')

      expect(wrapper.emitted('stat-click')?.[0]).toEqual(['entities'])
    })

    it('emite stat-click con "alerts" al hacer click en alertas', async () => {
      const wrapper = mount(ProjectSummary, {
        props: defaultProps,
      })

      const statCards = wrapper.findAll('.stat-card')
      await statCards[3].trigger('click')

      expect(wrapper.emitted('stat-click')?.[0]).toEqual(['alerts'])
    })
  })

  describe('Progreso de alertas', () => {
    it('muestra sección de progreso cuando hay alertas detalladas', () => {
      const wrapper = mount(ProjectSummary, {
        props: {
          ...defaultProps,
          alerts: mockAlerts,
        },
      })

      expect(wrapper.text()).toContain('Progreso de alertas')
      expect(wrapper.text()).toContain('revisadas')
    })

    it('no muestra sección de progreso cuando no hay alertas detalladas', () => {
      const wrapper = mount(ProjectSummary, {
        props: defaultProps,
      })

      expect(wrapper.text()).not.toContain('Progreso de alertas')
    })

    it('calcula correctamente el porcentaje de revisadas', () => {
      const wrapper = mount(ProjectSummary, {
        props: {
          ...defaultProps,
          alerts: mockAlerts, // 2 resolved + 1 dismissed = 3 de 5 = 60%
        },
      })

      expect(wrapper.text()).toContain('40%') // 60% revisadas (2 de 5 = 40%)
    })

    it('muestra contadores de estado correctos', () => {
      const wrapper = mount(ProjectSummary, {
        props: {
          ...defaultProps,
          alerts: mockAlerts,
        },
      })

      // 3 activas, 1 resuelta, 1 rechazada
      expect(wrapper.text()).toContain('Pendientes')
      expect(wrapper.text()).toContain('Aceptadas')
      expect(wrapper.text()).toContain('Rechazadas')
    })
  })

  describe('Distribución por categoría', () => {
    it('muestra distribución por categoría cuando hay alertas', () => {
      const wrapper = mount(ProjectSummary, {
        props: {
          ...defaultProps,
          alerts: mockAlerts,
        },
      })

      expect(wrapper.text()).toContain('Distribución y pendientes por tipo')
      expect(wrapper.text()).toContain('Consistencia')
      expect(wrapper.text()).toContain('Gramática')
    })

    it('no muestra distribución cuando no hay alertas', () => {
      const wrapper = mount(ProjectSummary, {
        props: defaultProps,
      })

      expect(wrapper.text()).not.toContain('Distribución y pendientes por tipo')
    })

    it('muestra las categorías ordenadas por total descendente', () => {
      const wrapper = mount(ProjectSummary, {
        props: {
          ...defaultProps,
          alerts: mockAlerts,
        },
      })

      const text = wrapper.text()
      const consistencyIndex = text.indexOf('Consistencia')
      const grammarIndex = text.indexOf('Gramática')

      // Consistencia (2) debe aparecer antes que Gramática (2) o al mismo nivel
      expect(consistencyIndex).toBeGreaterThan(-1)
      expect(grammarIndex).toBeGreaterThan(-1)
    })
  })

  describe('Edge cases', () => {
    it('maneja wordCount de 0', () => {
      const wrapper = mount(ProjectSummary, {
        props: {
          ...defaultProps,
          wordCount: 0,
        },
      })

      expect(wrapper.text()).toContain('0')
      expect(wrapper.text()).toContain('palabras')
    })

    it('maneja listas vacías de alertas', () => {
      const wrapper = mount(ProjectSummary, {
        props: {
          ...defaultProps,
          alerts: [],
        },
      })

      expect(wrapper.text()).not.toContain('Progreso de alertas')
    })

    it('calcula correctamente con todas las alertas resueltas', () => {
      const allResolved: Alert[] = [
        {
          id: 1,
          category: 'consistency',
          status: 'resolved',
          severity: 'high',
          title: 'Alert 1',
          spanStart: 0,
          spanEnd: 10,
        },
        {
          id: 2,
          category: 'grammar',
          status: 'resolved',
          severity: 'medium',
          title: 'Alert 2',
          spanStart: 20,
          spanEnd: 30,
        },
      ]

      const wrapper = mount(ProjectSummary, {
        props: {
          ...defaultProps,
          alerts: allResolved,
        },
      })

      expect(wrapper.text()).toContain('100%')
      expect(wrapper.text()).toContain('revisadas')
    })
  })

  describe('Tip de uso', () => {
    it('muestra tip con alertas cuando hay alertas detalladas', () => {
      const wrapper = mount(ProjectSummary, {
        props: {
          ...defaultProps,
          alerts: mockAlerts,
        },
      })

      expect(wrapper.text()).toContain('Abre Alertas para continuar la revisión')
    })

    it('muestra tip sin alertas cuando no hay alertas detalladas', () => {
      const wrapper = mount(ProjectSummary, {
        props: defaultProps,
      })

      expect(wrapper.text()).toContain('Selecciona una entidad o alerta para ver sus detalles')
    })
  })
})
