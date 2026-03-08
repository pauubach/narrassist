import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { useDocumentViewerInteractions } from './useDocumentViewerInteractions'

describe('useDocumentViewerInteractions', () => {
  const selectionStore = {
    setTextSelection: vi.fn(),
  }
  const emitEntityClick = vi.fn()
  const emitAnnotationClick = vi.fn()
  const chapters = ref([
    {
      id: 1,
      projectId: 1,
      title: 'Capitulo 1',
      content: 'Texto de prueba',
      chapterNumber: 1,
      wordCount: 3,
      positionStart: 100,
      positionEnd: 114,
    },
  ] as any)
  const viewerContainer = ref<HTMLElement | null>(null)

  beforeEach(() => {
    vi.clearAllMocks()
    document.body.innerHTML = `
      <div id="viewer">
        <section class="chapter-section" data-chapter-id="1">
          <div class="chapter-text">Hola mundo de prueba</div>
        </section>
      </div>
    `
    viewerContainer.value = document.getElementById('viewer')
  })

  it('emite clicks sobre entidades y anotaciones', () => {
    const { handleDocumentClick } = useDocumentViewerInteractions({
      viewerContainer,
      chapters,
      selectionStore,
      emitEntityClick,
      emitAnnotationClick,
    })

    const entity = document.createElement('mark')
    entity.className = 'entity-highlight'
    entity.dataset.entityId = '42'
    handleDocumentClick({ target: entity } as unknown as MouseEvent)

    const annotation = document.createElement('span')
    annotation.className = 'annotation'
    annotation.dataset.annotationId = '7'
    handleDocumentClick({ target: annotation } as unknown as MouseEvent)

    expect(emitEntityClick).toHaveBeenCalledWith(42)
    expect(emitAnnotationClick).toHaveBeenCalledWith(7)
  })

  it('guarda la seleccion con offsets globales cuando esta dentro de un capitulo', () => {
    const { handleMouseUp } = useDocumentViewerInteractions({
      viewerContainer,
      chapters,
      selectionStore,
      emitEntityClick,
      emitAnnotationClick,
    })

    const textNode = viewerContainer.value!.querySelector('.chapter-text')!.firstChild as Text
    const range = document.createRange()
    range.setStart(textNode, 5)
    range.setEnd(textNode, 10)

    const selection = {
      isCollapsed: false,
      toString: () => 'mundo',
      getRangeAt: () => range,
    }
    vi.spyOn(window, 'getSelection').mockReturnValue(selection as any)

    handleMouseUp()

    expect(selectionStore.setTextSelection).toHaveBeenCalledWith({
      start: 105,
      end: 110,
      text: 'mundo',
      chapter: 'Capitulo 1',
      chapterNumber: 1,
    })
  })

  it('limpia la seleccion cuando no puede resolverse el capitulo', () => {
    const { handleMouseUp } = useDocumentViewerInteractions({
      viewerContainer: ref(document.createElement('div')),
      chapters,
      selectionStore,
      emitEntityClick,
      emitAnnotationClick,
    })

    const externalText = document.createTextNode('fuera')
    const range = document.createRange()
    range.setStart(externalText, 0)
    range.setEnd(externalText, 4)
    const selection = {
      isCollapsed: false,
      toString: () => 'fuera',
      getRangeAt: () => range,
    }
    vi.spyOn(window, 'getSelection').mockReturnValue(selection as any)

    handleMouseUp()

    expect(selectionStore.setTextSelection).toHaveBeenCalledWith(null)
  })
})
