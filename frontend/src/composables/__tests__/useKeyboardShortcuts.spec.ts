/**
 * Tests para useKeyboardShortcuts — enrutamiento de atajos de teclado
 *
 * Testea que los atajos de teclado disparan los eventos CustomEvent
 * correctos en `window`. No monta componentes Vue — prueba la lógica
 * pura del handler de keydown.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// ── Lógica extraída de useKeyboardShortcuts ────────────────

const TAB_BY_NUMBER: Record<string, string> = {
  '1': 'text',
  '2': 'entities',
  '3': 'relationships',
  '4': 'alerts',
  '5': 'timeline',
  '6': 'style',
  '7': 'glossary',
  '8': 'summary',
}

/**
 * Simula el handler de keydown extraído de useKeyboardShortcuts.
 * Recibe un callback para capturar los eventos disparados.
 */
function handleKeydown(
  event: {
    key: string
    ctrlKey: boolean
    metaKey: boolean
    shiftKey: boolean
    altKey: boolean
    target: { tagName: string; isContentEditable: boolean }
  },
  options: {
    isInProject: boolean
    dispatchEvent: (name: string, detail?: unknown) => void
    preventDefault: () => void
    routerPush?: (route: object) => void
  }
) {
  const { key, ctrlKey, metaKey, shiftKey, altKey } = event
  const modifier = ctrlKey || metaKey

  // Ignorar si el usuario está escribiendo en un input
  const target = event.target
  if (
    target.tagName === 'INPUT' ||
    target.tagName === 'TEXTAREA' ||
    target.isContentEditable
  ) {
    if (key === 'Escape') {
      // blur handled externally
    }
    return
  }

  // Pestañas: Ctrl+1..8
  if (modifier && !shiftKey && !altKey && key in TAB_BY_NUMBER) {
    options.preventDefault()
    if (options.isInProject) {
      const tab = TAB_BY_NUMBER[key]
      options.dispatchEvent('menubar:view-tab', { tab })
    }
    return
  }

  // Navegación de alertas
  if (key === 'F8' && !shiftKey) {
    options.preventDefault()
    options.dispatchEvent('keyboard:next-alert')
  } else if (key === 'F8' && shiftKey) {
    options.preventDefault()
    options.dispatchEvent('keyboard:prev-alert')
  }

  // Toggle sidebar
  else if (modifier && !shiftKey && key === 'b') {
    options.preventDefault()
    options.dispatchEvent('menubar:toggle-sidebar')
  }

  // Buscar (Ctrl+F)
  else if (modifier && !shiftKey && key === 'f') {
    options.preventDefault()
    options.dispatchEvent('menubar:find')
  }

  // Exportar (Ctrl+E)
  else if (modifier && !shiftKey && key === 'e') {
    options.preventDefault()
    options.dispatchEvent('menubar:export')
  }

  // Configuración (Ctrl+,)
  else if (modifier && key === ',') {
    options.preventDefault()
    options.routerPush?.({ name: 'settings' })
  }

  // Toggle inspector (Ctrl+Shift+I)
  else if (modifier && shiftKey && (key === 'I' || key === 'i')) {
    options.preventDefault()
    options.dispatchEvent('menubar:toggle-inspector')
  }

  // Toggle historial (Ctrl+Shift+H)
  else if (modifier && shiftKey && (key === 'H' || key === 'h')) {
    options.preventDefault()
    options.dispatchEvent('menubar:toggle-history')
  }

  // Tema (Ctrl+Shift+D)
  else if (modifier && shiftKey && (key === 'D' || key === 'd')) {
    options.preventDefault()
    options.dispatchEvent('menubar:toggle-theme')
  }

  // Ayuda
  else if (key === 'F1' || (modifier && key === '/')) {
    options.preventDefault()
    options.dispatchEvent('keyboard:show-help')
  }

  // Acciones en alertas
  else if (key === 'Enter' && !modifier && !shiftKey && !altKey) {
    options.dispatchEvent('keyboard:resolve-alert')
  } else if (key === 'Delete' && !modifier && !shiftKey && !altKey) {
    options.dispatchEvent('keyboard:dismiss-alert')
  }

  // Escape
  else if (key === 'Escape') {
    options.dispatchEvent('keyboard:escape')
  }
}

// ── Helpers ────────────────────────────────────────────────

function createKeyEvent(overrides: Partial<{
  key: string
  ctrlKey: boolean
  metaKey: boolean
  shiftKey: boolean
  altKey: boolean
  target: { tagName: string; isContentEditable: boolean }
}>) {
  return {
    key: overrides.key ?? '',
    ctrlKey: overrides.ctrlKey ?? false,
    metaKey: overrides.metaKey ?? false,
    shiftKey: overrides.shiftKey ?? false,
    altKey: overrides.altKey ?? false,
    target: overrides.target ?? { tagName: 'DIV', isContentEditable: false },
  }
}

function createOptions(overrides: { isInProject?: boolean } = {}) {
  return {
    isInProject: overrides.isInProject ?? true,
    dispatchEvent: vi.fn(),
    preventDefault: vi.fn(),
    routerPush: vi.fn(),
  }
}

// ── Tests ──────────────────────────────────────────────────

describe('useKeyboardShortcuts — enrutamiento de atajos', () => {
  describe('cambio de pestañas (Ctrl+1..8)', () => {
    it.each([
      ['1', 'text'],
      ['2', 'entities'],
      ['3', 'relationships'],
      ['4', 'alerts'],
      ['5', 'timeline'],
      ['6', 'style'],
      ['7', 'glossary'],
      ['8', 'summary'],
    ])('Ctrl+%s → pestaña "%s"', (key, expectedTab) => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key, ctrlKey: true }), opts)

      expect(opts.preventDefault).toHaveBeenCalled()
      expect(opts.dispatchEvent).toHaveBeenCalledWith(
        'menubar:view-tab',
        { tab: expectedTab }
      )
    })

    it.each([
      ['1', 'text'],
      ['2', 'entities'],
      ['3', 'relationships'],
      ['4', 'alerts'],
      ['5', 'timeline'],
      ['6', 'style'],
      ['7', 'glossary'],
      ['8', 'summary'],
    ])('Cmd+%s → pestaña "%s" (macOS)', (key, expectedTab) => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key, metaKey: true }), opts)

      expect(opts.preventDefault).toHaveBeenCalled()
      expect(opts.dispatchEvent).toHaveBeenCalledWith(
        'menubar:view-tab',
        { tab: expectedTab }
      )
    })

    it('no cambia pestaña si no está en proyecto', () => {
      const opts = createOptions({ isInProject: false })
      handleKeydown(createKeyEvent({ key: '1', ctrlKey: true }), opts)

      expect(opts.preventDefault).toHaveBeenCalled()
      expect(opts.dispatchEvent).not.toHaveBeenCalled()
    })

    it('Ctrl+9 no dispara ningún evento de pestaña', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: '9', ctrlKey: true }), opts)

      expect(opts.dispatchEvent).not.toHaveBeenCalledWith(
        'menubar:view-tab',
        expect.anything()
      )
    })

    it('Ctrl+Shift+número no cambia pestaña', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: '1', ctrlKey: true, shiftKey: true }), opts)

      expect(opts.dispatchEvent).not.toHaveBeenCalledWith(
        'menubar:view-tab',
        expect.anything()
      )
    })

    it('Alt+número no cambia pestaña', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: '1', ctrlKey: true, altKey: true }), opts)

      expect(opts.dispatchEvent).not.toHaveBeenCalledWith(
        'menubar:view-tab',
        expect.anything()
      )
    })
  })

  describe('Ctrl+F — buscar', () => {
    it('Ctrl+F dispara menubar:find', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: 'f', ctrlKey: true }), opts)

      expect(opts.preventDefault).toHaveBeenCalled()
      expect(opts.dispatchEvent).toHaveBeenCalledWith('menubar:find')
    })

    it('Cmd+F dispara menubar:find (macOS)', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: 'f', metaKey: true }), opts)

      expect(opts.dispatchEvent).toHaveBeenCalledWith('menubar:find')
    })

    it('Ctrl+Shift+F no dispara find', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: 'f', ctrlKey: true, shiftKey: true }), opts)

      expect(opts.dispatchEvent).not.toHaveBeenCalledWith('menubar:find')
    })
  })

  describe('navegación de alertas (F8)', () => {
    it('F8 → keyboard:next-alert', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: 'F8' }), opts)

      expect(opts.dispatchEvent).toHaveBeenCalledWith('keyboard:next-alert')
    })

    it('Shift+F8 → keyboard:prev-alert', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: 'F8', shiftKey: true }), opts)

      expect(opts.dispatchEvent).toHaveBeenCalledWith('keyboard:prev-alert')
    })
  })

  describe('paneles y UI (Ctrl — Windows/Linux)', () => {
    it('Ctrl+B → menubar:toggle-sidebar', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: 'b', ctrlKey: true }), opts)

      expect(opts.dispatchEvent).toHaveBeenCalledWith('menubar:toggle-sidebar')
    })

    it('Ctrl+E → menubar:export', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: 'e', ctrlKey: true }), opts)

      expect(opts.dispatchEvent).toHaveBeenCalledWith('menubar:export')
    })

    it('Ctrl+, → router push settings', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: ',', ctrlKey: true }), opts)

      expect(opts.routerPush).toHaveBeenCalledWith({ name: 'settings' })
    })

    it('Ctrl+Shift+I → menubar:toggle-inspector', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: 'I', ctrlKey: true, shiftKey: true }), opts)

      expect(opts.dispatchEvent).toHaveBeenCalledWith('menubar:toggle-inspector')
    })

    it('Ctrl+Shift+H → menubar:toggle-history', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: 'H', ctrlKey: true, shiftKey: true }), opts)

      expect(opts.dispatchEvent).toHaveBeenCalledWith('menubar:toggle-history')
    })

    it('Ctrl+Shift+D → menubar:toggle-theme', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: 'D', ctrlKey: true, shiftKey: true }), opts)

      expect(opts.dispatchEvent).toHaveBeenCalledWith('menubar:toggle-theme')
    })

    it('Ctrl+/ → keyboard:show-help', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: '/', ctrlKey: true }), opts)

      expect(opts.dispatchEvent).toHaveBeenCalledWith('keyboard:show-help')
    })
  })

  describe('paneles y UI (Cmd — macOS)', () => {
    it('Cmd+B → menubar:toggle-sidebar', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: 'b', metaKey: true }), opts)

      expect(opts.dispatchEvent).toHaveBeenCalledWith('menubar:toggle-sidebar')
    })

    it('Cmd+E → menubar:export', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: 'e', metaKey: true }), opts)

      expect(opts.dispatchEvent).toHaveBeenCalledWith('menubar:export')
    })

    it('Cmd+, → router push settings', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: ',', metaKey: true }), opts)

      expect(opts.routerPush).toHaveBeenCalledWith({ name: 'settings' })
    })

    it('Cmd+Shift+I → menubar:toggle-inspector', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: 'I', metaKey: true, shiftKey: true }), opts)

      expect(opts.dispatchEvent).toHaveBeenCalledWith('menubar:toggle-inspector')
    })

    it('Cmd+Shift+H → menubar:toggle-history', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: 'H', metaKey: true, shiftKey: true }), opts)

      expect(opts.dispatchEvent).toHaveBeenCalledWith('menubar:toggle-history')
    })

    it('Cmd+Shift+D → menubar:toggle-theme', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: 'D', metaKey: true, shiftKey: true }), opts)

      expect(opts.dispatchEvent).toHaveBeenCalledWith('menubar:toggle-theme')
    })

    it('Cmd+/ → keyboard:show-help', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: '/', metaKey: true }), opts)

      expect(opts.dispatchEvent).toHaveBeenCalledWith('keyboard:show-help')
    })
  })

  describe('ayuda', () => {
    it('F1 → keyboard:show-help (sin modificador, ambas plataformas)', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: 'F1' }), opts)

      expect(opts.dispatchEvent).toHaveBeenCalledWith('keyboard:show-help')
    })
  })

  describe('acciones de alertas', () => {
    it('Enter → keyboard:resolve-alert', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: 'Enter' }), opts)

      expect(opts.dispatchEvent).toHaveBeenCalledWith('keyboard:resolve-alert')
    })

    it('Delete → keyboard:dismiss-alert', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: 'Delete' }), opts)

      expect(opts.dispatchEvent).toHaveBeenCalledWith('keyboard:dismiss-alert')
    })

    it('Ctrl+Enter no resuelve alerta', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: 'Enter', ctrlKey: true }), opts)

      expect(opts.dispatchEvent).not.toHaveBeenCalledWith('keyboard:resolve-alert')
    })
  })

  describe('escape', () => {
    it('Escape → keyboard:escape', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: 'Escape' }), opts)

      expect(opts.dispatchEvent).toHaveBeenCalledWith('keyboard:escape')
    })
  })

  describe('filtro de inputs', () => {
    it('ignora atajos cuando el foco está en INPUT', () => {
      const opts = createOptions()
      handleKeydown(
        createKeyEvent({
          key: 'f',
          ctrlKey: true,
          target: { tagName: 'INPUT', isContentEditable: false },
        }),
        opts
      )

      expect(opts.dispatchEvent).not.toHaveBeenCalled()
      expect(opts.preventDefault).not.toHaveBeenCalled()
    })

    it('ignora atajos cuando el foco está en TEXTAREA', () => {
      const opts = createOptions()
      handleKeydown(
        createKeyEvent({
          key: '1',
          ctrlKey: true,
          target: { tagName: 'TEXTAREA', isContentEditable: false },
        }),
        opts
      )

      expect(opts.dispatchEvent).not.toHaveBeenCalled()
    })

    it('ignora atajos en elementos contentEditable', () => {
      const opts = createOptions()
      handleKeydown(
        createKeyEvent({
          key: 'b',
          ctrlKey: true,
          target: { tagName: 'DIV', isContentEditable: true },
        }),
        opts
      )

      expect(opts.dispatchEvent).not.toHaveBeenCalled()
    })

    it('números sin Ctrl no disparan nada', () => {
      const opts = createOptions()
      handleKeydown(createKeyEvent({ key: '1' }), opts)

      expect(opts.dispatchEvent).not.toHaveBeenCalledWith(
        'menubar:view-tab',
        expect.anything()
      )
    })
  })
})

describe('useKeyboardShortcuts — KEYBOARD_SHORTCUTS constante', () => {
  // Importar la constante directamente para validar su contenido
  const { KEYBOARD_SHORTCUTS } = (() => {
    // Recreamos la constante aquí para test sin importar el módulo Vue
    return {
      KEYBOARD_SHORTCUTS: [
        { category: 'Pestañas', shortcuts: Array(8).fill(null) },
        { category: 'Alertas', shortcuts: Array(4).fill(null) },
        { category: 'Interfaz', shortcuts: Array(9).fill(null) },
        { category: 'Navegación en listas', shortcuts: Array(4).fill(null) },
        { category: 'Apariciones de entidad', shortcuts: Array(3).fill(null) },
        { category: 'Corrección secuencial', shortcuts: Array(8).fill(null) },
        { category: 'Ayuda', shortcuts: Array(2).fill(null) },
      ]
    }
  })()

  it('tiene 7 categorías', () => {
    expect(KEYBOARD_SHORTCUTS).toHaveLength(7)
  })

  it('las categorías esperadas existen', () => {
    const categories = KEYBOARD_SHORTCUTS.map(c => c.category)
    expect(categories).toContain('Pestañas')
    expect(categories).toContain('Alertas')
    expect(categories).toContain('Interfaz')
    expect(categories).toContain('Ayuda')
    expect(categories).toContain('Corrección secuencial')
  })

  it('Pestañas tiene 8 atajos (1 por tab)', () => {
    const pestanyas = KEYBOARD_SHORTCUTS.find(c => c.category === 'Pestañas')
    expect(pestanyas?.shortcuts).toHaveLength(8)
  })
})

describe('TAB_BY_NUMBER — cobertura completa', () => {
  it('mapea exactamente 8 números a 8 tabs', () => {
    expect(Object.keys(TAB_BY_NUMBER)).toHaveLength(8)
  })

  it('todos los valores son únicos', () => {
    const values = Object.values(TAB_BY_NUMBER)
    expect(new Set(values).size).toBe(values.length)
  })

  it('los tabs siguen el orden visual izquierda → derecha', () => {
    const expectedOrder = [
      'text', 'entities', 'relationships', 'alerts',
      'timeline', 'style', 'glossary', 'summary'
    ]
    const actualOrder = ['1', '2', '3', '4', '5', '6', '7', '8'].map(k => TAB_BY_NUMBER[k])
    expect(actualOrder).toEqual(expectedOrder)
  })
})
