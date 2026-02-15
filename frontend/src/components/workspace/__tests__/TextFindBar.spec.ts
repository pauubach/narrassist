/**
 * Tests para TextFindBar - lógica de búsqueda en texto del documento
 *
 * Testea la lógica de búsqueda DOM (TreeWalker, mark elements, navegación)
 * usando happy-dom como entorno.
 */

// ── Helpers para simular el DOM del DocumentViewer ──────────

function createDocumentContainer(chapters: string[]): HTMLElement {
  const container = document.createElement('div')
  container.className = 'text-tab'

  const documentContent = document.createElement('div')
  documentContent.className = 'document-content'

  for (const text of chapters) {
    const chapterDiv = document.createElement('div')
    chapterDiv.className = 'chapter-text'
    chapterDiv.textContent = text
    documentContent.appendChild(chapterDiv)
  }

  container.appendChild(documentContent)
  return container
}

function createContainerWithHtml(chapters: string[]): HTMLElement {
  const container = document.createElement('div')
  container.className = 'text-tab'

  const documentContent = document.createElement('div')
  documentContent.className = 'document-content'

  for (const html of chapters) {
    const chapterDiv = document.createElement('div')
    chapterDiv.className = 'chapter-text'
    chapterDiv.innerHTML = html
    documentContent.appendChild(chapterDiv)
  }

  container.appendChild(documentContent)
  return container
}

// ── Lógica de búsqueda extraída de TextFindBar ──────────────

interface TextMatch {
  node: Text
  offset: number
  length: number
}

function findMatches(container: HTMLElement, query: string): HTMLElement[] {
  if (!query || query.length < 2) return []

  const searchContainer = container.querySelector('.document-content') as HTMLElement
  if (!searchContainer) return []

  const lowerQuery = query.toLowerCase()
  const allMatches: TextMatch[] = []
  const chapterTexts = searchContainer.querySelectorAll('.chapter-text')

  chapterTexts.forEach(chapterText => {
    const walker = document.createTreeWalker(chapterText, NodeFilter.SHOW_TEXT)

    while (walker.nextNode()) {
      const node = walker.currentNode as Text
      const text = (node.textContent || '').toLowerCase()
      let pos = 0

      while (true) {
        const idx = text.indexOf(lowerQuery, pos)
        if (idx === -1) break
        allMatches.push({ node, offset: idx, length: query.length })
        pos = idx + 1
      }
    }
  })

  // Wrap from end to start
  const foundMarks: HTMLElement[] = new Array(allMatches.length)

  for (let i = allMatches.length - 1; i >= 0; i--) {
    const { node, offset, length } = allMatches[i]
    try {
      const range = document.createRange()
      range.setStart(node, offset)
      range.setEnd(node, offset + length)

      const mark = document.createElement('mark')
      mark.className = 'text-find-match'
      range.surroundContents(mark)
      foundMarks[i] = mark
    } catch {
      // Skip cross-boundary matches
    }
  }

  return foundMarks.filter(Boolean)
}

function clearMarks(container: HTMLElement): void {
  const searchContainer = container.querySelector('.document-content') as HTMLElement
  if (!searchContainer) return

  const existingMarks = searchContainer.querySelectorAll('mark.text-find-match')
  existingMarks.forEach(mark => {
    const parent = mark.parentNode
    if (parent) {
      while (mark.firstChild) {
        parent.insertBefore(mark.firstChild, mark)
      }
      parent.removeChild(mark)
      parent.normalize()
    }
  })
}

// ── Navigation logic ────────────────────────────────────────

function navigateNext(currentIndex: number, total: number): number {
  if (total === 0) return -1
  return (currentIndex + 1) % total
}

function navigatePrevious(currentIndex: number, total: number): number {
  if (total === 0) return -1
  return (currentIndex - 1 + total) % total
}

// ── Tests ───────────────────────────────────────────────────

describe('TextFindBar — búsqueda en texto', () => {
  describe('búsqueda básica', () => {
    it('encuentra coincidencias simples', () => {
      const container = createDocumentContainer([
        'Don Quijote salió de la aldea.',
      ])
      const marks = findMatches(container, 'Quijote')
      expect(marks).toHaveLength(1)
      expect(marks[0].textContent).toBe('Quijote')
    })

    it('búsqueda case-insensitive', () => {
      const container = createDocumentContainer([
        'Don Quijote y don quijote son el mismo.',
      ])
      const marks = findMatches(container, 'quijote')
      expect(marks).toHaveLength(2)
    })

    it('encuentra múltiples coincidencias en un capítulo', () => {
      const container = createDocumentContainer([
        'El gato persiguió al ratón. El gato volvió a casa. El gato durmió.',
      ])
      const marks = findMatches(container, 'gato')
      expect(marks).toHaveLength(3)
    })

    it('encuentra coincidencias en múltiples capítulos', () => {
      const container = createDocumentContainer([
        'María caminó por el parque.',
        'María llegó a la estación.',
        'Pedro esperaba a María.',
      ])
      const marks = findMatches(container, 'María')
      expect(marks).toHaveLength(3)
    })

    it('devuelve array vacío cuando no hay coincidencias', () => {
      const container = createDocumentContainer([
        'Don Quijote salió de la aldea.',
      ])
      const marks = findMatches(container, 'Hamlet')
      expect(marks).toHaveLength(0)
    })
  })

  describe('longitud mínima de consulta', () => {
    it('ignora consultas de un solo carácter', () => {
      const container = createDocumentContainer(['abc abc abc'])
      const marks = findMatches(container, 'a')
      expect(marks).toHaveLength(0)
    })

    it('ignora consultas vacías', () => {
      const container = createDocumentContainer(['abc'])
      const marks = findMatches(container, '')
      expect(marks).toHaveLength(0)
    })

    it('encuentra coincidencias con 2 caracteres', () => {
      const container = createDocumentContainer(['el gato el perro el ratón'])
      const marks = findMatches(container, 'el')
      expect(marks).toHaveLength(3)
    })
  })

  describe('contenido HTML con entidades resaltadas', () => {
    it('busca dentro de spans de entidades', () => {
      const container = createContainerWithHtml([
        'Habló <span class="entity-highlight">Don Quijote</span> con Sancho.',
      ])
      const marks = findMatches(container, 'Quijote')
      expect(marks).toHaveLength(1)
      expect(marks[0].textContent).toBe('Quijote')
    })

    it('busca texto fuera de spans de entidades', () => {
      const container = createContainerWithHtml([
        'Habló <span class="entity-highlight">Don Quijote</span> con Sancho.',
      ])
      const marks = findMatches(container, 'Sancho')
      expect(marks).toHaveLength(1)
    })

    it('busca en texto con múltiples spans anidados', () => {
      const container = createContainerWithHtml([
        '<span class="entity">María</span> habló con <span class="entity">Pedro</span>. María se fue.',
      ])
      const marks = findMatches(container, 'María')
      expect(marks).toHaveLength(2)
    })
  })

  describe('edge cases', () => {
    it('maneja contenedor sin .document-content', () => {
      const container = document.createElement('div')
      const marks = findMatches(container, 'test')
      expect(marks).toHaveLength(0)
    })

    it('maneja capítulos vacíos', () => {
      const container = createDocumentContainer(['', '', ''])
      const marks = findMatches(container, 'test')
      expect(marks).toHaveLength(0)
    })

    it('maneja texto con caracteres especiales de regex', () => {
      const container = createDocumentContainer([
        'El precio es $100.00 (con IVA).',
      ])
      const marks = findMatches(container, '$100')
      expect(marks).toHaveLength(1)
    })

    it('maneja texto con acentos y ñ', () => {
      const container = createDocumentContainer([
        'El niño corría por la mañana.',
      ])
      const marks = findMatches(container, 'niño')
      expect(marks).toHaveLength(1)
    })

    it('maneja coincidencias solapadas (busca todas las posiciones)', () => {
      const container = createDocumentContainer(['aaaa'])
      const marks = findMatches(container, 'aa')
      // "aaaa" contiene "aa" en posiciones 0, 1, 2
      // Pero surroundContents modifica el DOM, so we get fewer
      // After first wrap at pos 2: "aa<mark>aa</mark>"
      // After second wrap at pos 0: "<mark>aa</mark><mark>aa</mark>"
      // Positions depend on DOM mutation order
      expect(marks.length).toBeGreaterThanOrEqual(2)
    })

    it('encuentra coincidencias con espacios', () => {
      const container = createDocumentContainer([
        'Don Quijote de la Mancha era un hidalgo.',
      ])
      const marks = findMatches(container, 'de la')
      expect(marks).toHaveLength(1)
      expect(marks[0].textContent).toBe('de la')
    })
  })

  describe('limpieza de marks', () => {
    it('elimina todos los marks y restaura el texto', () => {
      const container = createDocumentContainer([
        'El gato persiguió al ratón.',
      ])
      const originalText = container.querySelector('.chapter-text')!.textContent

      findMatches(container, 'gato')
      expect(container.querySelectorAll('mark.text-find-match')).toHaveLength(1)

      clearMarks(container)
      expect(container.querySelectorAll('mark.text-find-match')).toHaveLength(0)
      expect(container.querySelector('.chapter-text')!.textContent).toBe(originalText)
    })

    it('restaura el texto después de múltiples coincidencias', () => {
      const container = createDocumentContainer([
        'El gato, el gato y el gato.',
      ])
      const originalText = container.querySelector('.chapter-text')!.textContent

      findMatches(container, 'gato')
      expect(container.querySelectorAll('mark.text-find-match')).toHaveLength(3)

      clearMarks(container)
      expect(container.querySelectorAll('mark.text-find-match')).toHaveLength(0)
      expect(container.querySelector('.chapter-text')!.textContent).toBe(originalText)
    })

    it('no falla con contenedor sin marks', () => {
      const container = createDocumentContainer(['texto sin marks'])
      expect(() => clearMarks(container)).not.toThrow()
    })

    it('permite buscar de nuevo tras limpiar', () => {
      const container = createDocumentContainer(['El gato descansó.'])

      findMatches(container, 'gato')
      expect(container.querySelectorAll('mark')).toHaveLength(1)

      clearMarks(container)

      const newMarks = findMatches(container, 'descansó')
      expect(newMarks).toHaveLength(1)
      expect(newMarks[0].textContent).toBe('descansó')
    })
  })
})

describe('TextFindBar — navegación', () => {
  describe('navigateNext', () => {
    it('avanza al siguiente índice', () => {
      expect(navigateNext(0, 5)).toBe(1)
      expect(navigateNext(3, 5)).toBe(4)
    })

    it('wraps al inicio cuando llega al final', () => {
      expect(navigateNext(4, 5)).toBe(0)
    })

    it('devuelve -1 si no hay resultados', () => {
      expect(navigateNext(0, 0)).toBe(-1)
    })

    it('funciona con un solo resultado', () => {
      expect(navigateNext(0, 1)).toBe(0)
    })
  })

  describe('navigatePrevious', () => {
    it('retrocede al índice anterior', () => {
      expect(navigatePrevious(3, 5)).toBe(2)
      expect(navigatePrevious(1, 5)).toBe(0)
    })

    it('wraps al final cuando está en el primer índice', () => {
      expect(navigatePrevious(0, 5)).toBe(4)
    })

    it('devuelve -1 si no hay resultados', () => {
      expect(navigatePrevious(0, 0)).toBe(-1)
    })

    it('funciona con un solo resultado', () => {
      expect(navigatePrevious(0, 1)).toBe(0)
    })
  })

  describe('ciclo completo next → next → ... → wrap', () => {
    it('recorre todos los resultados en ciclo', () => {
      const total = 3
      let idx = 0
      const visited: number[] = [idx]

      for (let i = 0; i < total; i++) {
        idx = navigateNext(idx, total)
        visited.push(idx)
      }

      // 0 → 1 → 2 → 0 (wrap)
      expect(visited).toEqual([0, 1, 2, 0])
    })
  })

  describe('ciclo completo prev → prev → ... → wrap', () => {
    it('recorre todos los resultados en reversa', () => {
      const total = 3
      let idx = 0
      const visited: number[] = [idx]

      for (let i = 0; i < total; i++) {
        idx = navigatePrevious(idx, total)
        visited.push(idx)
      }

      // 0 → 2 → 1 → 0 (wrap)
      expect(visited).toEqual([0, 2, 1, 0])
    })
  })
})

describe('TextFindBar — match label', () => {
  function getMatchLabel(query: string, total: number, currentIndex: number): string {
    if (!query) return ''
    if (total === 0) return 'Sin resultados'
    return `${currentIndex + 1} / ${total}`
  }

  it('muestra vacío sin consulta', () => {
    expect(getMatchLabel('', 0, -1)).toBe('')
  })

  it('muestra "Sin resultados" cuando no hay coincidencias', () => {
    expect(getMatchLabel('test', 0, -1)).toBe('Sin resultados')
  })

  it('muestra posición correcta', () => {
    expect(getMatchLabel('test', 5, 0)).toBe('1 / 5')
    expect(getMatchLabel('test', 5, 4)).toBe('5 / 5')
  })

  it('muestra posición con un solo resultado', () => {
    expect(getMatchLabel('test', 1, 0)).toBe('1 / 1')
  })
})
