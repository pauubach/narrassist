/**
 * Tests para DsEmptyState
 *
 * Verifican que el componente renderiza correctamente los iconos
 * y otros elementos visuales.
 */

import { mount } from '@vue/test-utils'
import DsEmptyState from '../ds/DsEmptyState.vue'

describe('DsEmptyState', () => {
  describe('icon rendering', () => {
    it('should render icon with correct classes', () => {
      const wrapper = mount(DsEmptyState, {
        props: {
          icon: 'pi pi-users',
          title: 'No hay entidades',
        },
      })

      const icon = wrapper.find('i')
      expect(icon.exists()).toBe(true)
      expect(icon.classes()).toContain('pi')
      expect(icon.classes()).toContain('pi-users')
    })

    it('should render icon with full PrimeIcons class', () => {
      // Este test habría detectado el bug de "pi-users" sin "pi"
      const wrapper = mount(DsEmptyState, {
        props: {
          icon: 'pi pi-inbox',
          title: 'Sin mensajes',
        },
      })

      const icon = wrapper.find('i')
      expect(icon.classes()).toContain('pi')
      expect(icon.classes()).toContain('pi-inbox')
    })

    it('should NOT render icon correctly with incomplete class', () => {
      // Este test documenta el problema: si pasas solo "pi-users"
      // sin "pi", el icono no se verá
      const wrapper = mount(DsEmptyState, {
        props: {
          icon: 'pi-users', // INCORRECTO - falta "pi"
          title: 'No hay entidades',
        },
      })

      const icon = wrapper.find('i')
      // El icono existe pero solo tiene "pi-users", no "pi"
      expect(icon.classes()).not.toContain('pi')
      // Esto significa que el icono no se renderizará visualmente
    })

    it('should not render icon when not provided', () => {
      const wrapper = mount(DsEmptyState, {
        props: {
          title: 'Sin datos',
        },
      })

      expect(wrapper.find('i.ds-empty-state__icon').exists()).toBe(false)
    })
  })

  describe('content rendering', () => {
    it('should render title', () => {
      const wrapper = mount(DsEmptyState, {
        props: {
          title: 'No hay entidades',
        },
      })

      expect(wrapper.find('.ds-empty-state__title').text()).toBe('No hay entidades')
    })

    it('should render description when provided', () => {
      const wrapper = mount(DsEmptyState, {
        props: {
          title: 'No hay entidades',
          description: 'Analiza el documento para detectar entidades',
        },
      })

      expect(wrapper.find('.ds-empty-state__description').text())
        .toBe('Analiza el documento para detectar entidades')
    })

    it('should not render description when not provided', () => {
      const wrapper = mount(DsEmptyState, {
        props: {
          title: 'Sin datos',
        },
      })

      expect(wrapper.find('.ds-empty-state__description').exists()).toBe(false)
    })
  })

  describe('size variants', () => {
    it('should apply sm size class', () => {
      const wrapper = mount(DsEmptyState, {
        props: {
          title: 'Test',
          size: 'sm',
        },
      })

      expect(wrapper.classes()).toContain('ds-empty-state--sm')
    })

    it('should apply md size class by default', () => {
      const wrapper = mount(DsEmptyState, {
        props: {
          title: 'Test',
        },
      })

      expect(wrapper.classes()).toContain('ds-empty-state--md')
    })

    it('should apply lg size class', () => {
      const wrapper = mount(DsEmptyState, {
        props: {
          title: 'Test',
          size: 'lg',
        },
      })

      expect(wrapper.classes()).toContain('ds-empty-state--lg')
    })
  })

  describe('slots', () => {
    it('should render action slot', () => {
      const wrapper = mount(DsEmptyState, {
        props: {
          title: 'Sin datos',
        },
        slots: {
          action: '<button>Acción</button>',
        },
      })

      expect(wrapper.find('.ds-empty-state__action').exists()).toBe(true)
      expect(wrapper.find('button').text()).toBe('Acción')
    })

    it('should render illustration slot instead of icon', () => {
      const wrapper = mount(DsEmptyState, {
        props: {
          title: 'Sin datos',
          icon: 'pi pi-users', // Should be ignored
        },
        slots: {
          illustration: '<img src="test.svg" />',
        },
      })

      // Illustration takes precedence over icon
      expect(wrapper.find('.ds-empty-state__illustration').exists()).toBe(true)
      expect(wrapper.find('i.ds-empty-state__icon').exists()).toBe(false)
    })
  })
})


/**
 * Test helper para verificar uso correcto de iconos
 */
describe('Icon Usage Patterns', () => {
  it('documents correct icon usage', () => {
    // CORRECTO: Incluir "pi" como prefijo
    const correctIconUsage = [
      'pi pi-users',
      'pi pi-inbox',
      'pi pi-exclamation-triangle',
      'pi pi-check-circle',
    ]

    // INCORRECTO: Solo el nombre del icono
    const incorrectIconUsage = [
      'pi-users',
      'pi-inbox',
      'pi-exclamation-triangle',
    ]

    // Verificar patrón correcto
    for (const icon of correctIconUsage) {
      expect(icon.startsWith('pi ')).toBe(true)
      expect(icon.split(' ').length).toBe(2)
    }

    // Documentar que estos son incorrectos
    for (const icon of incorrectIconUsage) {
      expect(icon.startsWith('pi ')).toBe(false)
    }
  })
})
