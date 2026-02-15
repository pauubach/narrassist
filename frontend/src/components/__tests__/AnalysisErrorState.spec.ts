/**
 * Tests para AnalysisErrorState
 *
 * Verifican que el componente de error renderiza correctamente:
 * - Icono de advertencia
 * - Mensaje de error
 * - Botón de reintentar (opcional)
 */

import { mount } from '@vue/test-utils'
import AnalysisErrorState from '../shared/AnalysisErrorState.vue'

describe('AnalysisErrorState', () => {
  describe('message rendering', () => {
    it('should render error message', () => {
      const wrapper = mount(AnalysisErrorState, {
        props: {
          message: 'Error del servidor (404)',
        },
      })

      expect(wrapper.find('.error-message').text()).toBe('Error del servidor (404)')
    })

    it('should render warning icon', () => {
      const wrapper = mount(AnalysisErrorState, {
        props: {
          message: 'No se pudo re-analizar el documento. Recarga la página si persiste.',
        },
      })

      const icon = wrapper.find('i.pi')
      expect(icon.exists()).toBe(true)
      expect(icon.classes()).toContain('pi-exclamation-triangle')
    })

    it('should render long error messages without truncation', () => {
      const longMsg = 'Error al evaluar la salud narrativa: módulo no disponible. Verifique que las dependencias estén instaladas correctamente.'
      const wrapper = mount(AnalysisErrorState, {
        props: {
          message: longMsg,
        },
      })

      expect(wrapper.find('.error-message').text()).toBe(longMsg)
    })
  })

  describe('retry button', () => {
    it('should render retry button when onRetry is provided', () => {
      const retryFn = vi.fn()
      const wrapper = mount(AnalysisErrorState, {
        props: {
          message: 'Error',
          onRetry: retryFn,
        },
      })

      const button = wrapper.findComponent({ name: 'Button' })
      expect(button.exists()).toBe(true)
    })

    it('should NOT render retry button when onRetry is not provided', () => {
      const wrapper = mount(AnalysisErrorState, {
        props: {
          message: 'Error',
        },
      })

      const button = wrapper.findComponent({ name: 'Button' })
      expect(button.exists()).toBe(false)
    })

    it('should call onRetry when retry button is clicked', async () => {
      const retryFn = vi.fn()
      const wrapper = mount(AnalysisErrorState, {
        props: {
          message: 'Error',
          onRetry: retryFn,
        },
      })

      const button = wrapper.findComponent({ name: 'Button' })
      await button.trigger('click')
      expect(retryFn).toHaveBeenCalledOnce()
    })

    it('retry button should have "Reintentar" label', () => {
      const wrapper = mount(AnalysisErrorState, {
        props: {
          message: 'Error',
          onRetry: () => {},
        },
      })

      const button = wrapper.findComponent({ name: 'Button' })
      expect(button.props('label')).toBe('Reintentar')
    })
  })

  describe('accessibility', () => {
    it('should have proper structure for screen readers', () => {
      const wrapper = mount(AnalysisErrorState, {
        props: {
          message: 'Error al analizar',
        },
      })

      // Error message is in a <p> tag
      expect(wrapper.find('p.error-message').exists()).toBe(true)
    })
  })
})
