import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ProjectSummary from './ProjectSummary.vue'
import type { Alert } from '@/types'

// Mock del composable useAlertUtils
vi.mock('@/composables/useAlertUtils', () => ({
  useAlertUtils: () => ({
    getCategoryLabel: (category: string) => {
      const labels: Record<string, string> = {
        attribute: 'Consistencia',
        grammar: 'Gramática',
        style: 'Estilo',
        orthography: 'Ortografía',
        timeline: 'Línea temporal',
      }
      return labels[category] || category
    },
    getSeverityLabel: (severity: string) => {
      const labels: Record<string, string> = {
        critical: 'Crítico',
        high: 'Alto',
        medium: 'Medio',
        low: 'Bajo',
        info: 'Información',
      }
      return labels[severity] || severity
    },
  }),
}))

describe('ProjectSummary', () => {
  const mockAlerts: Alert[] = [
    {
      id: 1,
      projectId: 1,
      category: 'attribute',
      status: 'active',
      severity: 'high',
      alertType: 'test',
      title: 'Alert 1',
      description: 'Test',
      spanStart: 0,
      spanEnd: 10,
      entityIds: [],
      confidence: 0.9,
      createdAt: new Date(),
    },
    {
      id: 2,
      projectId: 1,
      category: 'attribute',
      status: 'resolved',
      severity: 'medium',
      alertType: 'test',
      title: 'Alert 2',
      description: 'Test',
      spanStart: 20,
      spanEnd: 30,
      entityIds: [],
      confidence: 0.9,
      createdAt: new Date(),
    },
    {
      id: 3,
      projectId: 1,
      category: 'grammar',
      status: 'dismissed',
      severity: 'low',
      alertType: 'test',
      title: 'Alert 3',
      description: 'Test',
      spanStart: 40,
      spanEnd: 50,
      entityIds: [],
      confidence: 0.9,
      createdAt: new Date(),
    },
    {
      id: 4,
      projectId: 1,
      category: 'grammar',
      status: 'active',
      severity: 'high',
      alertType: 'test',
      title: 'Alert 4',
      description: 'Test',
      spanStart: 60,
      spanEnd: 70,
      entityIds: [],
      confidence: 0.9,
      createdAt: new Date(),
    },
    {
      id: 5,
      projectId: 1,
      category: 'style',
      status: 'active',
      severity: 'medium',
      alertType: 'test',
      title: 'Alert 5',
      description: 'Test',
      spanStart: 80,
      spanEnd: 90,
      entityIds: [],
      confidence: 0.9,
      createdAt: new Date(),
    },
  ]

  describe('Rendering básico', () => {
    it('monta el componente correctamente', () => {
      const wrapper = mount(ProjectSummary)
      expect(wrapper.exists()).toBe(true)
    })

    it('muestra sinopsis cuando globalSummary está presente', () => {
      const wrapper = mount(ProjectSummary, {
        props: {
          globalSummary: 'Una historia sobre aventuras',
        },
      })

      expect(wrapper.text()).toContain('Sinopsis')
    })
  })

  describe('Progreso de alertas', () => {
    it('muestra sección de progreso cuando hay alertas', () => {
      const wrapper = mount(ProjectSummary, {
        props: {
          alerts: mockAlerts,
        },
      })

      expect(wrapper.text()).toContain('Progreso')
      expect(wrapper.text()).toContain('revisadas')
    })

    it('no muestra sección de progreso cuando no hay alertas', () => {
      const wrapper = mount(ProjectSummary)

      expect(wrapper.text()).not.toContain('Progreso')
    })

    it('calcula correctamente el porcentaje de revisadas', () => {
      const wrapper = mount(ProjectSummary, {
        props: {
          alerts: mockAlerts, // 1 resolved + 1 dismissed = 2 de 5 = 40%
        },
      })

      expect(wrapper.text()).toContain('40%')
    })

    it('muestra contadores de estado correctos', () => {
      const wrapper = mount(ProjectSummary, {
        props: {
          alerts: mockAlerts,
        },
      })

      expect(wrapper.text()).toContain('pendientes')
      expect(wrapper.text()).toContain('aceptadas')
      expect(wrapper.text()).toContain('rechazadas')
    })
  })

  describe('Distribución por categoría', () => {
    it('muestra distribución por categoría cuando hay alertas', () => {
      const wrapper = mount(ProjectSummary, {
        props: {
          alerts: mockAlerts,
        },
      })

      expect(wrapper.text()).toContain('Top alertas por tipo')
      expect(wrapper.text()).toContain('Consistencia')
      expect(wrapper.text()).toContain('Gramática')
    })

    it('no muestra distribución cuando no hay alertas', () => {
      const wrapper = mount(ProjectSummary)

      expect(wrapper.text()).not.toContain('Top alertas por tipo')
    })

    it('muestra las categorías ordenadas por total descendente', () => {
      const wrapper = mount(ProjectSummary, {
        props: {
          alerts: mockAlerts,
        },
      })

      const text = wrapper.text()
      const consistencyIndex = text.indexOf('Consistencia')
      const grammarIndex = text.indexOf('Gramática')

      expect(consistencyIndex).toBeGreaterThan(-1)
      expect(grammarIndex).toBeGreaterThan(-1)
    })
  })

  describe('Edge cases', () => {
    it('maneja listas vacías de alertas', () => {
      const wrapper = mount(ProjectSummary, {
        props: {
          alerts: [],
        },
      })

      expect(wrapper.text()).not.toContain('Progreso')
    })

    it('calcula correctamente con todas las alertas resueltas', () => {
      const allResolved: Alert[] = [
        {
          id: 1,
          projectId: 1,
          category: 'attribute',
          status: 'resolved',
          severity: 'high',
          alertType: 'test',
          title: 'Alert 1',
          description: 'Test',
          spanStart: 0,
          spanEnd: 10,
          entityIds: [],
          confidence: 0.9,
          createdAt: new Date(),
        },
        {
          id: 2,
          projectId: 1,
          category: 'grammar',
          status: 'resolved',
          severity: 'medium',
          alertType: 'test',
          title: 'Alert 2',
          description: 'Test',
          spanStart: 20,
          spanEnd: 30,
          entityIds: [],
          confidence: 0.9,
          createdAt: new Date(),
        },
      ]

      const wrapper = mount(ProjectSummary, {
        props: {
          alerts: allResolved,
        },
      })

      expect(wrapper.text()).toContain('100%')
      expect(wrapper.text()).toContain('revisadas')
    })
  })

  describe('Tip de uso', () => {
    it('muestra tip con alertas cuando hay alertas', () => {
      const wrapper = mount(ProjectSummary, {
        props: {
          alerts: mockAlerts,
        },
      })

      expect(wrapper.text()).toContain('Abre Alertas para continuar la revisión')
    })

    it('muestra tip sin alertas cuando no hay alertas', () => {
      const wrapper = mount(ProjectSummary)

      expect(wrapper.text()).toContain('Selecciona una entidad o alerta para ver sus detalles')
    })
  })
})
