import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

/**
 * Composable para atajos de teclado globales
 * Basado en UI Design Proposal líneas 1401-1461
 */
export function useKeyboardShortcuts() {
  const router = useRouter()

  const handleKeydown = (event: KeyboardEvent) => {
    const { key, ctrlKey, metaKey, shiftKey, altKey } = event
    const modifier = ctrlKey || metaKey

    // Ignorar si el usuario está escribiendo en un input
    const target = event.target as HTMLElement
    if (
      target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA' ||
      target.isContentEditable
    ) {
      // Solo permitir Escape para salir de inputs
      if (key === 'Escape') {
        target.blur()
      }
      return
    }

    // Navegación de alertas
    if (key === 'F8' && !shiftKey) {
      event.preventDefault()
      // Emit evento para el componente de alertas
      window.dispatchEvent(new CustomEvent('keyboard:next-alert'))
    } else if (key === 'F8' && shiftKey) {
      event.preventDefault()
      window.dispatchEvent(new CustomEvent('keyboard:prev-alert'))
    }

    // Paneles y vistas
    else if (modifier && key === 'b') {
      event.preventDefault()
      window.dispatchEvent(new CustomEvent('keyboard:toggle-sidebar'))
    } else if (modifier && key === 'e') {
      event.preventDefault()
      // Ir al tab de entidades si estamos en un proyecto
      const currentRoute = router.currentRoute.value
      if (currentRoute.params.id || currentRoute.params.projectId) {
        window.dispatchEvent(new CustomEvent('menubar:view-tab', { detail: { tab: 'entities' } }))
      }
    } else if (modifier && key === 'a') {
      event.preventDefault()
      // Ir al tab de alertas si estamos en un proyecto
      const currentRoute = router.currentRoute.value
      if (currentRoute.params.id || currentRoute.params.projectId) {
        window.dispatchEvent(new CustomEvent('menubar:view-tab', { detail: { tab: 'alerts' } }))
      }
    } else if (modifier && key === 't') {
      event.preventDefault()
      // Ir al tab de texto si estamos en un proyecto
      const currentRoute = router.currentRoute.value
      if (currentRoute.params.id || currentRoute.params.projectId) {
        window.dispatchEvent(new CustomEvent('menubar:view-tab', { detail: { tab: 'text' } }))
      }
    } else if (modifier && key === 'r') {
      event.preventDefault()
      // Ir al tab de relaciones si estamos en un proyecto
      const currentRoute = router.currentRoute.value
      if (currentRoute.params.id || currentRoute.params.projectId) {
        window.dispatchEvent(new CustomEvent('menubar:view-tab', { detail: { tab: 'relations' } }))
      }
    } else if (modifier && key === 'd') {
      event.preventDefault()
      // Navegar al dashboard del proyecto
      const currentRoute = router.currentRoute.value
      if (currentRoute.params.id || currentRoute.params.projectId) {
        const projectId = currentRoute.params.id || currentRoute.params.projectId
        router.push({ name: 'project', params: { id: projectId } })
      }
    }

    // Búsqueda
    else if (modifier && key === 'f') {
      event.preventDefault()
      window.dispatchEvent(new CustomEvent('keyboard:focus-search'))
    }

    // Exportación
    else if (modifier && key === 'x') {
      event.preventDefault()
      window.dispatchEvent(new CustomEvent('keyboard:export'))
    }

    // Configuración
    else if (modifier && key === ',') {
      event.preventDefault()
      router.push({ name: 'settings' })
    }

    // Ayuda
    else if (key === 'F1' || (modifier && key === '/')) {
      event.preventDefault()
      window.dispatchEvent(new CustomEvent('keyboard:show-help'))
    }

    // Tema
    else if (modifier && shiftKey && key === 'D') {
      event.preventDefault()
      window.dispatchEvent(new CustomEvent('keyboard:toggle-theme'))
    }

    // Acciones en alertas (cuando hay una seleccionada)
    else if (key === 'Enter' && !modifier && !shiftKey && !altKey) {
      window.dispatchEvent(new CustomEvent('keyboard:resolve-alert'))
    } else if (key === 'Delete' && !modifier && !shiftKey && !altKey) {
      window.dispatchEvent(new CustomEvent('keyboard:dismiss-alert'))
    }

    // Navegación general
    else if (modifier && key === 'h') {
      event.preventDefault()
      router.push({ name: 'projects' })
    } else if (modifier && key === 'p') {
      event.preventDefault()
      router.push({ name: 'projects' })
    }

    // Escape para cerrar modales/sidebars
    else if (key === 'Escape') {
      window.dispatchEvent(new CustomEvent('keyboard:escape'))
    }
  }

  onMounted(() => {
    window.addEventListener('keydown', handleKeydown)
  })

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeydown)
  })

  return {
    // Exponer función para registrar handlers personalizados si se necesita
    addEventListener: (event: string, handler: EventListener) => {
      window.addEventListener(event, handler)
      return () => window.removeEventListener(event, handler)
    }
  }
}

/**
 * Lista de atajos disponibles para mostrar en ayuda
 */
export const KEYBOARD_SHORTCUTS = [
  {
    category: 'Navegación',
    shortcuts: [
      { keys: ['Ctrl/Cmd', 'H'], description: 'Ir a inicio' },
      { keys: ['Ctrl/Cmd', 'P'], description: 'Ir a proyectos' },
      { keys: ['Ctrl/Cmd', 'D'], description: 'Ir al dashboard del proyecto' },
      { keys: ['Ctrl/Cmd', 'T'], description: 'Ir a pestaña Texto' },
      { keys: ['Ctrl/Cmd', 'E'], description: 'Ir a pestaña Entidades' },
      { keys: ['Ctrl/Cmd', 'R'], description: 'Ir a pestaña Relaciones' },
      { keys: ['Ctrl/Cmd', 'A'], description: 'Ir a pestaña Alertas' },
      { keys: ['Ctrl/Cmd', ','], description: 'Abrir configuración' }
    ]
  },
  {
    category: 'Alertas',
    shortcuts: [
      { keys: ['F8'], description: 'Siguiente alerta' },
      { keys: ['Shift', 'F8'], description: 'Alerta anterior' },
      { keys: ['Enter'], description: 'Resolver alerta seleccionada' },
      { keys: ['Delete'], description: 'Descartar alerta seleccionada' }
    ]
  },
  {
    category: 'Interfaz',
    shortcuts: [
      { keys: ['Ctrl/Cmd', 'B'], description: 'Mostrar/ocultar sidebar' },
      { keys: ['Ctrl/Cmd', 'F'], description: 'Buscar' },
      { keys: ['Ctrl/Cmd', 'X'], description: 'Exportar' },
      { keys: ['Ctrl/Cmd', 'Shift', 'D'], description: 'Cambiar tema' },
      { keys: ['Escape'], description: 'Cerrar modal/cancelar' }
    ]
  },
  {
    category: 'Ayuda',
    shortcuts: [
      { keys: ['F1'], description: 'Mostrar ayuda' },
      { keys: ['Ctrl/Cmd', '/'], description: 'Mostrar atajos de teclado' }
    ]
  }
]
