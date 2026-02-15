import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

/**
 * Mapeo de números de teclado a pestañas del workspace.
 * Sigue el orden visual de las pestañas (izquierda → derecha).
 * Patrón estándar: VS Code, Chrome, Sublime, Firefox.
 */
const TAB_BY_NUMBER: Record<string, string> = {
  '1': 'text',          // Texto
  '2': 'entities',      // Entidades
  '3': 'relationships', // Relaciones
  '4': 'alerts',        // Revisión
  '5': 'timeline',      // Cronología
  '6': 'style',         // Escritura
  '7': 'glossary',      // Glosario
  '8': 'summary',       // Resumen
}

/**
 * Composable para atajos de teclado globales.
 *
 * Diseño validado por panel de expertos (UX, editor, accesibilidad):
 * - Ctrl+1..8 para pestañas (patrón estándar, sin conflictos con OS)
 * - Sin secuestrar Ctrl+A/X/H/P/T/R/D (funciones estándar del sistema)
 * - Ctrl+Shift+I/H/D para paneles (inspector, historial, tema)
 * - F8/Shift+F8 para navegación de alertas
 * - Namespace unificado: todos los eventos usan prefijo 'menubar:' para acciones
 *   de UI, 'keyboard:' solo para acciones sin equivalente en menú (alertas, escape)
 * - Modo corrección secuencial tiene sus propios atajos (A/D/S/F/N/P)
 */
export function useKeyboardShortcuts() {
  const router = useRouter()

  const isInProject = (): boolean => {
    const currentRoute = router.currentRoute.value
    return !!(currentRoute.params.id || currentRoute.params.projectId)
  }

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

    // ── Pestañas del workspace: Ctrl+1..8 ──────────────────────
    if (modifier && !shiftKey && !altKey && key in TAB_BY_NUMBER) {
      event.preventDefault()
      if (isInProject()) {
        const tab = TAB_BY_NUMBER[key]
        window.dispatchEvent(new CustomEvent('menubar:view-tab', { detail: { tab } }))
      }
      return
    }

    // ── Navegación de alertas ──────────────────────────────────
    if (key === 'F8' && !shiftKey) {
      event.preventDefault()
      window.dispatchEvent(new CustomEvent('keyboard:next-alert'))
    } else if (key === 'F8' && shiftKey) {
      event.preventDefault()
      window.dispatchEvent(new CustomEvent('keyboard:prev-alert'))
    }

    // ── Paneles y interfaz ─────────────────────────────────────
    else if (modifier && !shiftKey && key === 'b') {
      event.preventDefault()
      window.dispatchEvent(new CustomEvent('menubar:toggle-sidebar'))
    }

    // Buscar (Ctrl+F — pendiente de implementar listener)
    else if (modifier && !shiftKey && key === 'f') {
      event.preventDefault()
      window.dispatchEvent(new CustomEvent('menubar:find'))
    }

    // Exportar (Ctrl+E — sin conflicto ahora que tabs son numéricos)
    else if (modifier && !shiftKey && key === 'e') {
      event.preventDefault()
      window.dispatchEvent(new CustomEvent('menubar:export'))
    }

    // Configuración
    else if (modifier && key === ',') {
      event.preventDefault()
      router.push({ name: 'settings' })
    }

    // Toggle inspector (Ctrl+Shift+I)
    else if (modifier && shiftKey && (key === 'I' || key === 'i')) {
      event.preventDefault()
      window.dispatchEvent(new CustomEvent('menubar:toggle-inspector'))
    }

    // Toggle historial (Ctrl+Shift+H)
    else if (modifier && shiftKey && (key === 'H' || key === 'h')) {
      event.preventDefault()
      window.dispatchEvent(new CustomEvent('menubar:toggle-history'))
    }

    // Tema (Ctrl+Shift+D)
    else if (modifier && shiftKey && (key === 'D' || key === 'd')) {
      event.preventDefault()
      window.dispatchEvent(new CustomEvent('menubar:toggle-theme'))
    }

    // ── Ayuda ──────────────────────────────────────────────────
    else if (key === 'F1' || (modifier && key === '/')) {
      event.preventDefault()
      window.dispatchEvent(new CustomEvent('keyboard:show-help'))
    }

    // ── Acciones en alertas (cuando hay una seleccionada) ──────
    else if (key === 'Enter' && !modifier && !shiftKey && !altKey) {
      window.dispatchEvent(new CustomEvent('keyboard:resolve-alert'))
    } else if (key === 'Delete' && !modifier && !shiftKey && !altKey) {
      window.dispatchEvent(new CustomEvent('keyboard:dismiss-alert'))
    }

    // ── Escape para cerrar modales/sidebars ────────────────────
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
 * Lista de atajos disponibles para mostrar en ayuda.
 * Fuente única de verdad — KeyboardShortcutsDialog la consume directamente.
 */
export const KEYBOARD_SHORTCUTS = [
  {
    category: 'Pestañas',
    shortcuts: [
      { keys: ['Ctrl/Cmd', '1'], description: 'Texto' },
      { keys: ['Ctrl/Cmd', '2'], description: 'Entidades' },
      { keys: ['Ctrl/Cmd', '3'], description: 'Relaciones' },
      { keys: ['Ctrl/Cmd', '4'], description: 'Revisión (alertas)' },
      { keys: ['Ctrl/Cmd', '5'], description: 'Cronología' },
      { keys: ['Ctrl/Cmd', '6'], description: 'Escritura' },
      { keys: ['Ctrl/Cmd', '7'], description: 'Glosario' },
      { keys: ['Ctrl/Cmd', '8'], description: 'Resumen' },
    ]
  },
  {
    category: 'Alertas',
    shortcuts: [
      { keys: ['F8'], description: 'Siguiente alerta' },
      { keys: ['Shift', 'F8'], description: 'Alerta anterior' },
      { keys: ['Enter'], description: 'Resolver alerta seleccionada' },
      { keys: ['Delete'], description: 'Descartar alerta seleccionada' },
    ]
  },
  {
    category: 'Interfaz',
    shortcuts: [
      { keys: ['Ctrl/Cmd', 'B'], description: 'Mostrar/ocultar sidebar' },
      { keys: ['Ctrl/Cmd', 'Shift', 'I'], description: 'Mostrar/ocultar inspector' },
      { keys: ['Ctrl/Cmd', 'Shift', 'H'], description: 'Mostrar/ocultar historial' },
      { keys: ['Ctrl/Cmd', 'Z'], description: 'Deshacer última acción' },
      { keys: ['Ctrl/Cmd', 'F'], description: 'Buscar' },
      { keys: ['Ctrl/Cmd', 'E'], description: 'Exportar' },
      { keys: ['Ctrl/Cmd', ','], description: 'Configuración' },
      { keys: ['Ctrl/Cmd', 'Shift', 'D'], description: 'Cambiar tema' },
      { keys: ['Escape'], description: 'Cerrar modal/cancelar' },
    ]
  },
  {
    category: 'Navegación en listas',
    shortcuts: [
      { keys: ['↑', '↓'], description: 'Mover entre elementos' },
      { keys: ['Home'], description: 'Ir al primer elemento' },
      { keys: ['End'], description: 'Ir al último elemento' },
      { keys: ['Enter'], description: 'Seleccionar elemento' },
    ]
  },
  {
    category: 'Apariciones de entidad',
    shortcuts: [
      { keys: ['←', '→'], description: 'Anterior/siguiente aparición' },
      { keys: ['Home'], description: 'Primera aparición' },
      { keys: ['End'], description: 'Última aparición' },
    ]
  },
  {
    category: 'Corrección secuencial',
    shortcuts: [
      { keys: ['→', 'N'], description: 'Siguiente alerta' },
      { keys: ['←', 'P'], description: 'Alerta anterior' },
      { keys: ['A', 'Enter'], description: 'Aceptar (resolver)' },
      { keys: ['D'], description: 'Descartar' },
      { keys: ['S'], description: 'Saltar' },
      { keys: ['F'], description: 'Marcar para revisar' },
      { keys: ['Ctrl/Cmd', 'Z'], description: 'Deshacer' },
      { keys: ['Escape'], description: 'Salir del modo' },
    ]
  },
  {
    category: 'Ayuda',
    shortcuts: [
      { keys: ['F1'], description: 'Mostrar ayuda' },
      { keys: ['Ctrl/Cmd', '/'], description: 'Mostrar atajos de teclado' },
    ]
  },
]
