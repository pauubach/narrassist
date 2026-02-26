<template>
  <div ref="viewerContainer" class="document-viewer">
    <!-- Diálogo de exportación -->
    <Dialog
      :visible="showExportDialog"
      modal
      header="Exportar Documento"
      :style="{ width: '400px' }"
      @update:visible="showExportDialog = $event"
    >
      <div class="export-options">
        <p>Selecciona el formato de exportación:</p>
        <div class="export-format-options">
          <div class="format-option" :class="{ selected: exportFormat === 'docx' }" @click="exportFormat = 'docx'">
            <i class="pi pi-file-word"></i>
            <span>DOCX</span>
            <small>Documento Word con informe completo</small>
          </div>
          <div class="format-option" :class="{ selected: exportFormat === 'pdf' }" @click="exportFormat = 'pdf'">
            <i class="pi pi-file-pdf"></i>
            <span>PDF</span>
            <small>Documento PDF profesional</small>
          </div>
          <div class="format-option" :class="{ selected: exportFormat === 'json' }" @click="exportFormat = 'json'">
            <i class="pi pi-code"></i>
            <span>JSON</span>
            <small>Datos estructurados</small>
          </div>
        </div>
      </div>
      <template #footer>
        <Button label="Cancelar" text @click="showExportDialog = false" />
        <Button
          label="Exportar"
          icon="pi pi-download"
          :loading="exportLoading"
          @click="doExport"
        />
      </template>
    </Dialog>

    <!-- Toolbar superior -->
    <div class="viewer-toolbar">
      <div class="toolbar-left">
        <span class="viewer-title">{{ documentTitle }}</span>
        <span v-if="totalWords" class="word-count">
          <i class="pi pi-file"></i>
          {{ totalWords.toLocaleString() }} palabras
        </span>
      </div>
      <div class="toolbar-right">
        <!-- Toggle errores de ortografia -->
        <Button
          v-tooltip.bottom="showSpellingErrors ? 'Ocultar errores de ortografia' : 'Mostrar errores de ortografia'"
          :icon="showSpellingErrors ? 'pi pi-check-square' : 'pi pi-stop'"
          :text="!showSpellingErrors"
          :outlined="showSpellingErrors"
          rounded
          size="small"
          :class="{ 'spelling-toggle-active': showSpellingErrors }"
          @click="showSpellingErrors = !showSpellingErrors"
        >
          <template #icon>
            <span class="toggle-icon spelling-icon">Aa</span>
          </template>
        </Button>
        <!-- Toggle errores de gramatica -->
        <Button
          v-tooltip.bottom="showGrammarErrors ? 'Ocultar errores de gramatica' : 'Mostrar errores de gramatica'"
          :icon="showGrammarErrors ? 'pi pi-check-square' : 'pi pi-stop'"
          :text="!showGrammarErrors"
          :outlined="showGrammarErrors"
          rounded
          size="small"
          :class="{ 'grammar-toggle-active': showGrammarErrors }"
          @click="showGrammarErrors = !showGrammarErrors"
        >
          <template #icon>
            <i class="pi pi-language"></i>
          </template>
        </Button>
        <span class="toolbar-divider"></span>
        <Button
          v-tooltip.bottom="'Exportar'"
          icon="pi pi-download"
          text
          rounded
          @click="exportDocument"
        />
      </div>
    </div>

    <!-- Área de contenido del documento -->
    <div class="viewer-content" @scroll="onScroll">
      <div v-if="loading" class="viewer-loading">
        <ProgressSpinner />
        <p>Cargando documento...</p>
      </div>

      <div v-else-if="error" class="viewer-error">
        <i class="pi pi-exclamation-triangle"></i>
        <p>{{ error }}</p>
        <Button label="Reintentar" @click="loadDocument" />
      </div>

      <div v-else class="document-content" @click="handleDocumentClick" @mouseup="handleMouseUp">
        <!-- Renderizar capítulos con lazy loading -->
        <div
          v-for="chapter in chapters"
          :key="chapter.id"
          :ref="el => setChapterRef(el, chapter.id)"
          :data-chapter-id="chapter.id"
          class="chapter-section"
        >
          <div class="chapter-header">
            <span v-if="chapterBadges?.has(chapter.id)" class="chapter-badges-float">
              <button
                v-for="badge in chapterBadges.get(chapter.id)"
                :key="badge.metaCategory"
                class="alert-badge"
                :style="{ backgroundColor: badge.color }"
                :title="`${badge.count} ${badge.label.toLowerCase()}`"
              >
                <span class="badge-count">{{ badge.count }}</span>
              </button>
            </span>
            <h2 class="chapter-title">
              {{ chapter.chapterNumber }}. {{ chapter.title }}
            </h2>
          </div>

          <!-- Contenido del capítulo con entidades resaltadas (lazy loaded) -->
          <div
            v-if="loadedChapters.has(chapter.id)"
            class="chapter-text"
            :style="contentStyle"
            v-html="getHighlightedContent(chapter)"
          ></div>
          <!-- Placeholder mientras no está visible -->
          <div v-else class="chapter-placeholder">
            <ProgressSpinner style="width: 30px; height: 30px" />
            <span>Cargando capítulo...</span>
          </div>
        </div>

        <div v-if="chapters.length === 0" class="no-content">
          <ProgressSpinner v-if="loading" style="width: 40px; height: 40px" />
          <i v-else class="pi pi-file-edit"></i>
          <p>{{ loading ? 'Leyendo documento...' : 'Identificando capítulos...' }}</p>
          <small class="text-secondary">El contenido aparecerá en breve</small>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'
import type { Chapter } from '@/types'
import type { ApiChapter } from '@/types/api/projects'
import { transformChapters } from '@/types/transformers/projects'
import { apiUrl } from '@/config/api'
import { api } from '@/services/apiClient'
import { sanitizeHtml } from '@/utils/sanitizeHtml'
import { useSelectionStore } from '@/stores/selection'

const toast = useToast()
const selectionStore = useSelectionStore()

// Referencias a elementos de capítulos para intersection observer
const chapterRefs = new Map<number, Element>()
let intersectionObserver: IntersectionObserver | null = null

interface Entity {
  id: number
  project_id: number
  name: string
  entity_type: string
  first_mention_chapter?: number
  first_mention_position?: number
  mention_count: number
}

interface EntityMention {
  entity_id: number
  chapter_id: number
  position: number
  context: string
}

interface ScrollTarget {
  chapterId: number
  position?: number  // Posición de caracteres dentro del capítulo (para desambiguar)
  endPosition?: number
  text?: string      // Texto a resaltar
  preserveMultiHighlights?: boolean
}

interface AlertHighlightRange {
  startChar: number
  endChar: number
  text?: string
  chapterId?: number | null
  color?: string
  label?: string
}

interface ChapterBadge {
  metaCategory: string
  count: number
  color: string
  label: string
}

const props = defineProps<{
  projectId: number
  documentTitle?: string
  highlightEntityId?: number | null
  scrollToChapterId?: number | null
  scrollToTarget?: ScrollTarget | null
  /** Capítulos proporcionados por el padre (opcional, si no se pasan se cargan del API) */
  externalChapters?: Chapter[]
  /** Rangos múltiples a resaltar (para alertas de inconsistencia) */
  alertHighlightRanges?: AlertHighlightRange[]
  /** Badges de alertas por capítulo (Map: chapterId -> badges[]) */
  chapterBadges?: Map<number, ChapterBadge[]>
}>()

const emit = defineEmits<{
  chapterVisible: [chapterId: number]
  entityClick: [entityId: number]
  annotationClick: [annotationId: number]
}>()

// Estado
const viewerContainer = ref<HTMLElement | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const chapters = ref<Chapter[]>([])
const entities = ref<Entity[]>([])
// TODO: entityMentions se usará cuando se implemente el endpoint de menciones
const _entityMentions = ref<EntityMention[]>([])

// Estado para lazy loading con LRU cache para limitar memoria
const visibleChapters = ref<Set<number>>(new Set())
const loadedChapters = ref<Set<number>>(new Set())
const MAX_LOADED_CHAPTERS = 10  // Máximo de capítulos en memoria

// LRU: Orden de acceso a capítulos (más reciente al final)
const chapterAccessOrder = ref<number[]>([])

// Función para marcar un capítulo como usado (LRU)
const touchChapter = (chapterId: number) => {
  const idx = chapterAccessOrder.value.indexOf(chapterId)
  if (idx !== -1) {
    chapterAccessOrder.value.splice(idx, 1)
  }
  chapterAccessOrder.value.push(chapterId)

  // Si excedemos el límite, descargar los más antiguos
  while (chapterAccessOrder.value.length > MAX_LOADED_CHAPTERS && chapterAccessOrder.value.length > 0) {
    const oldestId = chapterAccessOrder.value.shift()
    if (oldestId !== undefined && !visibleChapters.value.has(oldestId)) {
      loadedChapters.value.delete(oldestId)
      highlightedContentCache.value.delete(oldestId)

      // FIX #1: Unobserve el elemento del IntersectionObserver para evitar memory leak
      const el = chapterRefs.get(oldestId)
      if (el && intersectionObserver) {
        intersectionObserver.unobserve(el)
      }

      const oldestChapter = chapters.value.find(ch => ch.id === oldestId)
      if (oldestChapter) {
        chapterAnnotations.value.delete(oldestChapter.chapterNumber)
        chapterDialogues.value.delete(oldestChapter.chapterNumber)
      }
    }
  }
}

// Anotaciones de gramática/ortografía por capítulo
interface Annotation {
  id: number
  type: string  // 'grammar' | 'orthography' | 'spelling'
  severity: string
  title: string
  description: string
  start_char: number
  end_char: number
  suggestion?: string
  excerpt?: string
}

// Atribución de diálogos
interface DialogueAttr {
  text: string
  speakerName: string | null
  speakerId: number | null
  confidence: 'high' | 'medium' | 'low' | 'unknown'
  method: string
  startChar: number
  endChar: number
  chapterNumber: number
}

const chapterAnnotations = ref<Map<number, Annotation[]>>(new Map())
const chapterDialogues = ref<Map<number, DialogueAttr[]>>(new Map())  // Cache de diálogos por capítulo
const showSpellingErrors = ref(true)  // Toggle para mostrar/ocultar errores de ortografia
const showGrammarErrors = ref(true)   // Toggle para mostrar/ocultar errores de gramatica
const showDialoguePanel = ref(false)  // Toggle para panel de atribución de diálogos
const showDialogueHighlights = ref(true)  // Mostrar highlights de diálogos cuando el panel está abierto

// Cache de contenido highlighted (performance optimization #1)
interface HighlightedContentCache {
  content: string
  dependencies: {
    chapterId: number
    showSpelling: boolean
    showGrammar: boolean
    showDialogue: boolean
    highlightDialogue: boolean
    entitiesCount: number
    annotationsCount: number
    dialoguesCount: number
    dialoguesKey: string
  }
}
const highlightedContentCache = ref<Map<number, HighlightedContentCache>>(new Map())

// Computed para mantener compatibilidad con showAnnotations (reservado para uso futuro)
const _showAnnotations = computed(() => showSpellingErrors.value || showGrammarErrors.value)

// Configuración de apariencia desde settings
const fontSize = ref<'small' | 'medium' | 'large'>('medium')
const lineHeight = ref<string>('1.6')

// Mapeo de tamaños de fuente a valores CSS
const fontSizeMap: Record<string, string> = {
  small: '0.9rem',
  medium: '1rem',
  large: '1.15rem'
}

// Cargar configuración de apariencia
const loadAppearanceSettings = () => {
  const savedSettings = localStorage.getItem('narrative_assistant_settings')
  if (savedSettings) {
    try {
      const parsed = JSON.parse(savedSettings)
      fontSize.value = parsed.fontSize || 'medium'
      lineHeight.value = parsed.lineHeight || '1.6'
    } catch (e) {
      console.error('Error loading appearance settings:', e)
    }
  }

  // Cargar preferencias de errores
  const errorPrefs = localStorage.getItem('narrative_assistant_error_prefs')
  if (errorPrefs) {
    try {
      const parsed = JSON.parse(errorPrefs)
      showSpellingErrors.value = parsed.showSpellingErrors ?? true
      showGrammarErrors.value = parsed.showGrammarErrors ?? true
    } catch (e) {
      console.error('Error loading error preferences:', e)
    }
  }
}

// Guardar preferencias de errores cuando cambien
const saveErrorPreferences = () => {
  localStorage.setItem('narrative_assistant_error_prefs', JSON.stringify({
    showSpellingErrors: showSpellingErrors.value,
    showGrammarErrors: showGrammarErrors.value
  }))
}

// Watch para persistir los cambios
watch([showSpellingErrors, showGrammarErrors], saveErrorPreferences)

// FIX #4: Invalidar cache selectivamente cuando cambien opciones de visualización
watch([showSpellingErrors, showGrammarErrors, showDialoguePanel, showDialogueHighlights], ([newSpelling, newGrammar, newPanel, newHighlight], [oldSpelling, oldGrammar, oldPanel, oldHighlight]) => {
  // Solo invalidar capítulos con diálogos si cambió el panel/highlight de diálogos
  if ((newPanel !== oldPanel || newHighlight !== oldHighlight) && (newPanel || oldPanel)) {
    // Invalidar solo capítulos que tienen diálogos cargados
    chapterDialogues.value.forEach((_, chNum) => {
      const ch = chapters.value.find(c => c.chapterNumber === chNum)
      if (ch) highlightedContentCache.value.delete(ch.id)
    })
  } else if (newSpelling !== oldSpelling || newGrammar !== oldGrammar) {
    // Si cambiaron los errores de ortografía/gramática, invalidar todo
    highlightedContentCache.value.clear()
  }
})

// Computed para el estilo del contenido
const contentStyle = computed(() => ({
  fontSize: fontSizeMap[fontSize.value] || '1rem',
  lineHeight: lineHeight.value
}))

// Cargar atribuciones de diálogo para un capítulo
const loadChapterDialogues = async (chapterNumber: number) => {
  if (chapterDialogues.value.has(chapterNumber)) return

  try {
    const data = await api.getRaw<{ success: boolean; data?: any }>(`/api/projects/${props.projectId}/chapters/${chapterNumber}/dialogue-attributions`)

    if (data.success && data.data?.attributions) {
      // Transformar snake_case (API) → camelCase (frontend DialogueAttr)
      const transformed: DialogueAttr[] = data.data.attributions.map((a: any) => ({
        text: a.text,
        speakerName: a.speaker_name ?? null,
        speakerId: a.speaker_id ?? null,
        confidence: a.confidence ?? 'unknown',
        method: a.method ?? 'none',
        startChar: a.start_char,
        endChar: a.end_char,
        chapterNumber: chapterNumber,
      }))
      chapterDialogues.value.set(chapterNumber, transformed)
    }
  } catch (err) {
    console.error(`Error loading dialogue attributions for chapter ${chapterNumber}:`, err)
  }
}

// Función para establecer referencia a elementos de capítulo
const setChapterRef = (el: Element | ComponentPublicInstance | null, chapterId: number) => {
  if (el && el instanceof Element) {
    chapterRefs.set(chapterId, el)
    // Si el observer ya existe, observar este elemento
    if (intersectionObserver) {
      intersectionObserver.observe(el)
    }
  }
}

// Configurar intersection observer para lazy loading
const setupIntersectionObserver = () => {
  if (intersectionObserver) {
    intersectionObserver.disconnect()
  }

  intersectionObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        const chapterId = parseInt(entry.target.getAttribute('data-chapter-id') || '0')
        if (chapterId) {
          if (entry.isIntersecting) {
            visibleChapters.value.add(chapterId)
            // Marcar como cargado y actualizar LRU
            loadedChapters.value.add(chapterId)
            touchChapter(chapterId)

            // Cargar anotaciones y diálogos al entrar en viewport (performance optimization #10)
            const chapter = chapters.value.find(ch => ch.id === chapterId)
            if (chapter) {
              loadChapterAnnotations(chapter.chapterNumber)
              if (showDialoguePanel.value) {
                loadChapterDialogues(chapter.chapterNumber)
              }
            }
          } else {
            visibleChapters.value.delete(chapterId)
          }
        }
      })
    },
    {
      root: null,
      rootMargin: '100px', // Pre-cargar cuando esté a 100px de ser visible
      threshold: 0
    }
  )

  // Observar elementos existentes
  chapterRefs.forEach((el) => {
    intersectionObserver?.observe(el)
  })
}

// Tipo para ComponentPublicInstance
type ComponentPublicInstance = { $el: Element }

// Computed
const totalWords = computed(() => {
  return chapters.value.reduce((sum, ch) => {
    const titleWords = ch.title ? ch.title.trim().split(/\s+/).length : 0
    return sum + ch.wordCount + titleWords
  }, 0)
})

// Cargar documento
const loadDocument = async () => {
  loading.value = true
  error.value = null

  // Resetear estado de lazy loading
  loadedChapters.value.clear()
  visibleChapters.value.clear()
  chapterAccessOrder.value = []
  chapterAnnotations.value.clear()
  chapterDialogues.value.clear()
  highlightedContentCache.value.clear()
  chapterRefs.clear()

  try {
    // Si hay capítulos externos, usarlos directamente
    if (props.externalChapters && props.externalChapters.length > 0) {
      chapters.value = props.externalChapters
    } else {
      // Cargar capítulos del API
      const chaptersData = await api.getRaw<{ success: boolean; data?: any[] }>(`/api/projects/${props.projectId}/chapters`)

      if (!chaptersData.success) {
        throw new Error('Error cargando capítulos')
      }

      // Transformar de snake_case (API) a camelCase (domain)
      const apiChapters: ApiChapter[] = chaptersData.data || []
      chapters.value = transformChapters(apiChapters)
    }

    // Pre-cargar el primer capítulo para que se muestre inmediatamente
    if (chapters.value.length > 0) {
      loadedChapters.value.add(chapters.value[0].id)
    }

    // Cargar entidades
    const entitiesData = await api.getRaw<{ success: boolean; data?: any[] }>(`/api/projects/${props.projectId}/entities`)

    if (entitiesData.success) {
      entities.value = entitiesData.data || []
    }

    // Configurar observer después de renderizar
    nextTick(() => {
      setupIntersectionObserver()
    })

  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Error cargando documento'
    console.error('Error loading document:', err)
  } finally {
    loading.value = false
  }
}

// Cargar anotaciones de gramática/ortografía para un capítulo
const loadChapterAnnotations = async (chapterNumber: number, forceReload = false) => {
  if (!forceReload && chapterAnnotations.value.has(chapterNumber)) return

  try {
    const data = await api.getRaw<{ success: boolean; data?: any }>(`/api/projects/${props.projectId}/chapters/${chapterNumber}/annotations`)

    if (data.success && data.data?.annotations) {
      chapterAnnotations.value.set(chapterNumber, data.data.annotations)
    }
  } catch (err) {
    console.error(`Error loading annotations for chapter ${chapterNumber}:`, err)
  }
}

const refreshVisibleChapterAnnotations = async () => {
  const chapterNumbers = chapters.value
    .filter(ch => loadedChapters.value.has(ch.id))
    .map(ch => ch.chapterNumber)

  if (chapterNumbers.length === 0) return

  highlightedContentCache.value.clear()
  await Promise.all(chapterNumbers.map(chNum => loadChapterAnnotations(chNum, true)))
}

// Calcular cuántos caracteres se eliminan del título
const getTitleOffset = (content: string, title: string): number => {
  if (!content || !title) return 0

  // Extraer primera línea del contenido
  const firstNewline = content.indexOf('\n')
  if (firstNewline === -1) return 0

  const firstLine = content.substring(0, firstNewline).trim()

  // Si la primera línea es muy larga, probablemente no es un título
  if (firstLine.length > 100) return 0

  // Normalizar para comparación (minúsculas, sin acentos, sin puntuación extra)
  const normalize = (s: string) => s.toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '') // Quitar acentos
    .replace(/[^a-z0-9\s]/g, '') // Solo alfanuméricos y espacios
    .replace(/\s+/g, ' ')
    .trim()

  const normalizedTitle = normalize(title)
  const normalizedFirstLine = normalize(firstLine)

  // Patrones que indican que la primera línea es un título de capítulo
  const isTitleLine =
    // La primera línea contiene el título
    normalizedFirstLine.includes(normalizedTitle) ||
    // La primera línea ES el título (o muy similar)
    normalizedTitle.includes(normalizedFirstLine) ||
    // Empieza con "Capítulo X" o variantes
    /^cap[ií]tulo\s+\d+/i.test(firstLine) ||
    /^chapter\s+\d+/i.test(firstLine) ||
    /^parte\s+\d+/i.test(firstLine) ||
    // Numeración romana al inicio
    /^[IVXLCDM]+[.:\s]/i.test(firstLine) ||
    // Número seguido de punto y texto corto (ej: "1. El Despertar")
    /^\d+\.\s+\S/.test(firstLine)

  if (isTitleLine) {
    // Calcular offset: posición del newline + newlines eliminados después
    let offset = firstNewline
    // Contar newlines consecutivos después
    let i = firstNewline
    while (i < content.length && content[i] === '\n') {
      offset++
      i++
    }
    return offset
  }

  return 0
}

// Eliminar título duplicado del contenido si existe
const removeLeadingTitle = (content: string, title: string): string => {
  const offset = getTitleOffset(content, title)
  if (offset > 0) {
    return content.substring(offset)
  }
  return content
}

const findClosestTextOccurrence = (
  haystack: string,
  needle: string,
  expectedIndex?: number
): number => {
  if (!needle) return -1

  const firstIndex = haystack.indexOf(needle)
  if (firstIndex === -1) return -1
  if (expectedIndex === undefined || expectedIndex < 0) return firstIndex

  let bestIndex = firstIndex
  let bestDistance = Math.abs(firstIndex - expectedIndex)
  let currentIndex = firstIndex

  while (currentIndex !== -1) {
    const distance = Math.abs(currentIndex - expectedIndex)
    if (distance < bestDistance) {
      bestDistance = distance
      bestIndex = currentIndex
    }
    currentIndex = haystack.indexOf(needle, currentIndex + 1)
  }

  return bestIndex
}

const replaceOutsideHtmlTags = (
  input: string,
  pattern: RegExp,
  replacer: (match: string) => string
): string => {
  const segments = input.split(/(<[^>]+>)/g)
  return segments
    .map(segment => {
      if (!segment) return segment
      if (segment.startsWith('<') && segment.endsWith('>')) return segment
      const safePattern = new RegExp(pattern.source, pattern.flags)
      return segment.replace(safePattern, replacer)
    })
    .join('')
}

// Resaltar entidades en el contenido (memoized, performance optimization #1)
const getHighlightedContent = (chapter: Chapter): string => {
  if (!chapter.content) return ''

  // Verificar cache
  const cached = highlightedContentCache.value.get(chapter.id)
  const annotations = chapterAnnotations.value.get(chapter.chapterNumber) || []
  const dialogues = chapterDialogues.value.get(chapter.chapterNumber) || []

  // Rangos de alerta activos para este capítulo
  const chapterAlertRanges = (props.alertHighlightRanges || [])
    .filter(r => r.chapterId === chapter.id)

  const currentDeps = {
    chapterId: chapter.id,
    showSpelling: showSpellingErrors.value,
    showGrammar: showGrammarErrors.value,
    showDialogue: showDialoguePanel.value,
    highlightDialogue: showDialogueHighlights.value,
    entitiesCount: entities.value.length,
    annotationsCount: annotations.length,
    dialoguesCount: dialogues.length,
    dialoguesKey: dialogues
      .map(d => `${d.startChar}:${d.endChar}:${d.confidence}:${d.method}:${d.text?.length ?? 0}`)
      .join('|'),
    alertRangesKey: chapterAlertRanges
      .map(r => `${r.startChar}:${r.endChar}:${r.color}:${r.text?.length ?? 0}`)
      .join('|')
  }

  // Si el cache es válido, retornar inmediatamente
  if (cached && JSON.stringify(cached.dependencies) === JSON.stringify(currentDeps)) {
    return cached.content
  }

  // Primero remover el título si está duplicado al inicio del contenido
  const contentWithoutTitle = removeLeadingTitle(chapter.content, chapter.title)
  const titleOffset = getTitleOffset(chapter.content, chapter.title)
  let content = escapeHtml(contentWithoutTitle)

  // Aplicar highlighting de diálogos si el panel está abierto
  if (showDialoguePanel.value && showDialogueHighlights.value) {
    const dialogues = chapterDialogues.value.get(chapter.chapterNumber) || []

    // Ordenar por posición descendente para no afectar índices
    const sortedDialogues = [...dialogues]
      .filter(d => d.text && d.startChar !== undefined)
      .sort((a, b) => b.startChar - a.startChar)

    sortedDialogues.forEach(dialogue => {
      // Ajustar posición por el título removido
      const adjustedStart = dialogue.startChar - titleOffset
      const adjustedEnd = dialogue.endChar - titleOffset
      if (adjustedStart < 0) return
      if (adjustedEnd <= adjustedStart) return

      // Priorizar el texto detectado completo; solo usar slice por offsets como fallback.
      // Hay casos donde endChar viene corto y el slice recorta el highlight a 1-2 palabras.
      const dialogueTextFromDetection = escapeHtml(dialogue.text)
      let dialogueIndex = findClosestTextOccurrence(content, dialogueTextFromDetection, adjustedStart)
      let dialogueText = dialogueTextFromDetection

      if (dialogueIndex === -1) {
        const lowerRaw = contentWithoutTitle.toLowerCase()
        const lowerDialogue = dialogue.text.toLowerCase()
        const nearbyStart = Math.max(0, adjustedStart - 8)
        const nearbyMatch = lowerRaw.indexOf(lowerDialogue, nearbyStart)

        let estimatedEnd = adjustedEnd
        if (nearbyMatch !== -1 && nearbyMatch <= adjustedStart + 12) {
          estimatedEnd = Math.max(estimatedEnd, nearbyMatch + dialogue.text.length)
        } else {
          // Fallback genérico: si el detector devuelve un end corto, extender por longitud textual.
          estimatedEnd = Math.max(estimatedEnd, adjustedStart + dialogue.text.length)
        }
        estimatedEnd = Math.min(contentWithoutTitle.length, estimatedEnd)

        const rawSlice = contentWithoutTitle.slice(adjustedStart, estimatedEnd)
        if (rawSlice) {
          dialogueText = escapeHtml(rawSlice)
          dialogueIndex = findClosestTextOccurrence(content, dialogueText, adjustedStart)
        }
      }

      if (dialogueIndex !== -1) {
        const confidenceClass = `dialogue-confidence-${dialogue.confidence}`
        const speakerName = dialogue.speakerName || 'Desconocido'
        const methodLabel = getDialogueMethodLabel(dialogue.method)
        const tooltip = `${speakerName} (${methodLabel})`

        const before = content.substring(0, dialogueIndex)
        const after = content.substring(dialogueIndex + dialogueText.length)

        content = before +
          `<span class="dialogue-highlight ${confidenceClass}" ` +
          `data-speaker-id="${dialogue.speakerId || ''}" ` +
          `data-dialogue-start="${dialogue.startChar}" ` +
          `data-dialogue-end="${dialogue.endChar}" ` +
          `data-speaker-name="${escapeHtml(speakerName)}" ` +
          `title="${escapeHtml(tooltip)}">` +
          dialogueText +
          `</span>` +
          after
      }
    })
  }

  // OPTIMIZACIÓN: Resaltar entidades en un solo pase usando un regex combinado
  // En lugar de N reemplazos (uno por entidad), hacemos 1 pase con todos los nombres
  const validEntities = entities.value.filter(e => e.name && e.name.length >= 2)

  if (validEntities.length > 0) {
    // Construir mapa de nombres a entidades para lookup O(1)
    const entityByName = new Map<string, typeof validEntities[0]>()
    const escapedNames: string[] = []

    for (const entity of validEntities) {
      const escaped = escapeRegex(entity.name)
      if (escaped) {
        // Usar lowercase como key para matching case-insensitive
        entityByName.set(entity.name.toLowerCase(), entity)
        escapedNames.push(escaped)
      }
    }

    if (escapedNames.length > 0) {
      // Ordenar por longitud descendente para que nombres más largos se capturen primero
      // Ej: "Juan Carlos" antes que "Juan"
      escapedNames.sort((a, b) => b.length - a.length)

      // Regex combinado con todos los nombres
      const combinedPattern = `\\b(${escapedNames.join('|')})\\b`
      const combinedRegex = new RegExp(combinedPattern, 'gi')

      // Un solo pase de reemplazo sobre texto (sin tocar etiquetas/atributos HTML)
      content = replaceOutsideHtmlTags(content, combinedRegex, (match) => {
        const entity = entityByName.get(match.toLowerCase())
        if (!entity) return match

        const isActive = entity.id === props.highlightEntityId
        const entityType = entity.entity_type?.toLowerCase() || 'other'

        // Usamos data-entity-id para event delegation (sin onclick inline)
        if (isActive) {
          return `<mark class="entity-highlight entity-highlight-active" data-entity-id="${entity.id}">${match}</mark>`
        } else {
          return `<mark class="entity-highlight entity-${entityType}" data-entity-id="${entity.id}">${match}</mark>`
        }
      })
    }
  }

  // Aplicar anotaciones de gramática/ortografía DESPUÉS de entidades
  // Usamos replaceOutsideHtmlTags para respetar los tags ya insertados
  if (showSpellingErrors.value || showGrammarErrors.value) {
    const annotations = chapterAnnotations.value.get(chapter.chapterNumber) || []

    // Filtrar por tipo según los toggles activos
    const filteredAnnotations = annotations.filter(a => {
      const type = (a.type || '').toLowerCase()
      const isGrammarType = type === 'grammar' || type === 'agreement'
      const isSpellingType = type === 'spelling' || type === 'orthography' || type === 'typography' || type === 'punctuation'

      if (isGrammarType && !showGrammarErrors.value) return false
      if (isSpellingType && !showSpellingErrors.value) return false
      return true
    })

    // Construir regex para cada anotación
    for (const annotation of filteredAnnotations) {
      if (!annotation.excerpt) continue

      const type = (annotation.type || '').toLowerCase()
      const annotationClass =
        type === 'grammar' || type === 'agreement'
          ? 'grammar-error'
          : 'spelling-error'
      const severityClass = `severity-${annotation.severity}`
      const tooltip = annotation.suggestion
        ? `${annotation.title}. Sugerencia: ${annotation.suggestion}`
        : annotation.title

      // El excerpt viene sin escapar, pero content ya está escapado
      // Necesitamos escapar el excerpt para que coincida con el contenido
      const excerptEscapedHtml = escapeHtml(annotation.excerpt)
      const excerptForRegex = escapeRegex(excerptEscapedHtml)
      const annotationRegex = new RegExp(excerptForRegex, 'g')

      // Aplicar highlight usando replaceOutsideHtmlTags (respeta tags existentes)
      content = replaceOutsideHtmlTags(content, annotationRegex, (match) => {
        return `<span class="annotation ${annotationClass} ${severityClass}" ` +
          `data-annotation-id="${annotation.id}" title="${escapeHtml(tooltip)}">${match}</span>`
      })
    }
  }

  // Aplicar highlights de alertas multi-source (ej: "ojos verdes" vs "ojos azules")
  if (chapterAlertRanges.length > 0) {
    for (const range of chapterAlertRanges) {
      if (!range.text) continue

      const searchText = escapeHtml(range.text)
      const searchRegex = new RegExp(escapeRegex(searchText), 'g')
      const color = range.color || '#fbbf24'
      const bgColor = hexToRgba(color, 0.35)
      const borderColor = hexToRgba(color, 0.6)
      const label = range.label ? escapeHtml(range.label) : ''

      content = replaceOutsideHtmlTags(content, searchRegex, (match) => {
        return `<span class="alert-multi-highlight" ` +
          `style="background-color:${bgColor};box-shadow:0 0 0 2px ${borderColor};border-radius:3px;padding:1px 2px;margin:-1px -2px" ` +
          `${label ? `title="${label}" data-label="${label}"` : ''}>` +
          match + `</span>`
      })
    }
  }

  // Convertir saltos de línea en párrafos y detectar encabezados de sección
  const html = content
    .split('\n\n')
    .map(block => {
      const trimmedBlock = block.trim()

      // Detectar si el bloque es un encabezado de sección
      // Criterios: línea corta (< 80 chars), sin punto final, posiblemente con numeración
      if (trimmedBlock.length > 0 && trimmedBlock.length < 80 && !trimmedBlock.includes('\n')) {
        const isHeading = detectSectionHeading(trimmedBlock)
        if (isHeading) {
          return `<div class="section-${isHeading.level}">${block}</div>`
        }
      }

      return `<p>${block.replace(/\n/g, '<br>')}</p>`
    })
    .join('')

  // Defense-in-depth: sanitize final HTML to strip anything unexpected
  const finalHtml = sanitizeHtml(html)

  // Guardar en cache (performance optimization #1)
  highlightedContentCache.value.set(chapter.id, {
    content: finalHtml,
    dependencies: currentDeps
  })

  return finalHtml
}

/**
 * Detecta si un bloque de texto es un encabezado de sección
 * Retorna el nivel del encabezado (h2, h3, h4, h5) o null si no es encabezado
 */
function detectSectionHeading(text: string): { level: 'h2' | 'h3' | 'h4' | 'h5' } | null {
  const trimmed = text.trim()

  // No considerar líneas muy cortas (< 3 chars) o muy largas (> 70 chars)
  if (trimmed.length < 3 || trimmed.length > 70) return null

  // No considerar líneas que terminan en punto, coma, etc. (probablemente son oraciones)
  if (/[.,;:!?]$/.test(trimmed)) return null

  // No considerar líneas que empiezan con minúscula (probablemente continuación)
  if (/^[a-záéíóúñ]/.test(trimmed)) return null

  // Patrones para H2 (secciones principales)
  // - "PARTE I", "PARTE PRIMERA", "SECCIÓN 1", etc.
  // - "I. Titulo", "II. Titulo" (numeración romana)
  // - Todo en mayúsculas
  if (
    /^(PARTE|SECCIÓN|SECCION|LIBRO|ACTO|CAPÍTULO|CAPITULO)\s+/i.test(trimmed) ||
    /^[IVXLCDM]+[.:\s]/i.test(trimmed) ||
    (trimmed === trimmed.toUpperCase() && trimmed.length > 3 && /[A-Z]/.test(trimmed))
  ) {
    return { level: 'h2' }
  }

  // Patrones para H3 (subsecciones)
  // - "1. Titulo", "2. Titulo" (numeración arábiga)
  // - "1.1 Titulo", "1.2 Titulo" (numeración decimal simple)
  // - Líneas cortas que empiezan con mayúscula y tienen estructura de título
  if (
    /^\d+\.\s+[A-ZÁÉÍÓÚÑ]/.test(trimmed) ||
    /^\d+\.\d+\s+[A-ZÁÉÍÓÚÑ]/.test(trimmed)
  ) {
    return { level: 'h3' }
  }

  // Patrones para H4 (sub-subsecciones)
  // - "a) Titulo", "b) Titulo"
  // - "1.1.1 Titulo" (numeración decimal doble)
  // - Líneas cortas con guion inicial
  if (
    /^[a-z]\)\s+[A-ZÁÉÍÓÚÑ]/.test(trimmed) ||
    /^\d+\.\d+\.\d+\s+/.test(trimmed) ||
    /^[-–—]\s+[A-ZÁÉÍÓÚÑ]/.test(trimmed)
  ) {
    return { level: 'h4' }
  }

  // Patrones para H5 (nivel más bajo)
  // - "i) Titulo", "ii) Titulo" (numeración romana minúscula)
  // - Numeración más profunda
  if (
    /^[ivx]+\)\s+/i.test(trimmed) ||
    /^\d+\.\d+\.\d+\.\d+\s+/.test(trimmed)
  ) {
    return { level: 'h5' }
  }

  return null
}

// Helpers
const escapeHtml = (text: string): string => {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

// Etiqueta legible para métodos de atribución de diálogo
const getDialogueMethodLabel = (method: string): string => {
  const labels: Record<string, string> = {
    explicit_verb: 'Verbo explícito',
    alternation: 'Alternancia',
    voice_profile: 'Perfil de voz',
    proximity: 'Proximidad',
    none: 'Sin método'
  }
  return labels[method] || method
}

const escapeRegex = (text: string | undefined | null): string => {
  if (!text) return ''
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

// Scroll a capítulo específico
const scrollToChapter = async (chapterId: number) => {
  // Encontrar el índice del capítulo objetivo
  const targetIndex = chapters.value.findIndex(ch => ch.id === chapterId)
  if (targetIndex === -1) {
    console.warn(`Chapter ${chapterId} not found`)
    return
  }

  // Cargar todos los capítulos desde el inicio hasta el objetivo
  // Esto asegura que las alturas del DOM sean correctas para el scroll
  for (let i = 0; i <= targetIndex; i++) {
    const chId = chapters.value[i].id
    if (!loadedChapters.value.has(chId)) {
      loadedChapters.value.add(chId)
      touchChapter(chId)
    }
  }

  // Esperar a que Vue actualice el DOM
  await nextTick()

  // Dar tiempo adicional para renderizado
  // Fix #2: Trackear timer para cleanup
  await new Promise<void>(resolve => {
    const timer = setTimeout(() => {
      activeScrollTimers.delete(timer)
      resolve()
    }, 50)
    activeScrollTimers.add(timer)
  })

  const element = viewerContainer.value?.querySelector(`[data-chapter-id="${chapterId}"]`)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

// Variable para almacenar el highlight temporal
const temporarySelectedClass = 'mention-highlight-selected'
const highlightDurationMs = 3000

// CSS Custom Highlight API — resalta sin tocar el DOM
let highlightTimer: ReturnType<typeof setTimeout> | null = null
// Tracking de timers activos para cleanup (Fix #2: memory leak prevention)
const activeScrollTimers = new Set<ReturnType<typeof setTimeout>>()
let scrollAbortController: AbortController | null = null

const clearTemporaryMentionHighlights = () => {
  if (highlightTimer) {
    clearTimeout(highlightTimer)
    highlightTimer = null
  }
  CSS.highlights?.delete('mention-temp')
  const selectedElements = viewerContainer.value?.querySelectorAll(`.${temporarySelectedClass}`)
  selectedElements?.forEach(el => {
    el.classList.remove(temporarySelectedClass)
  })
}

// Cleanup de timers activos cuando se cancela un scroll
const cleanupScrollTimers = () => {
  activeScrollTimers.forEach(timer => clearTimeout(timer))
  activeScrollTimers.clear()
  if (scrollAbortController) {
    scrollAbortController.abort()
    scrollAbortController = null
  }
}

const applyHighlightFromRange = (range: Range) => {
  clearTemporaryMentionHighlights()

  // Registrar highlight nativo vía CSS Custom Highlight API
  if (CSS.highlights) {
    const highlight = new Highlight(range)
    CSS.highlights.set('mention-temp', highlight)
  }

  // Scroll al texto
  const el = range.startContainer.parentElement
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  // Auto-limpiar después de la duración
  highlightTimer = setTimeout(() => {
    CSS.highlights?.delete('mention-temp')
    highlightTimer = null
  }, highlightDurationMs)
}

const applyTemporaryHighlightElement = (element: Element) => {
  element.classList.add(temporarySelectedClass)
  element.scrollIntoView({ behavior: 'smooth', block: 'center' })
  const timer = setTimeout(() => {
    element.classList.remove(temporarySelectedClass)
    activeScrollTimers.delete(timer)
  }, highlightDurationMs)
  activeScrollTimers.add(timer)
}

const findDialogueHighlightElement = (
  chapterElement: Element,
  start?: number,
  end?: number
): Element | null => {
  if (start === undefined || end === undefined) return null

  const exact = chapterElement.querySelector(
    `.dialogue-highlight[data-dialogue-start="${start}"][data-dialogue-end="${end}"]`
  )
  if (exact) return exact

  const chapter = chapters.value.find(ch => ch.id === Number((chapterElement as HTMLElement).dataset.chapterId))
  if (!chapter || chapter.positionStart === undefined) return null

  const localStart = start - chapter.positionStart
  const localEnd = end - chapter.positionStart
  if (localEnd <= localStart) return null

  return chapterElement.querySelector(
    `.dialogue-highlight[data-dialogue-start="${localStart}"][data-dialogue-end="${localEnd}"]`
  )
}

const createRangeFromCharacterOffsets = (
  contentElement: Element,
  start: number,
  end: number
): Range | null => {
  const totalLength = contentElement.textContent?.length || 0
  if (totalLength === 0) return null

  const normalizedStart = Math.max(0, Math.min(start, totalLength - 1))
  const normalizedEnd = Math.max(normalizedStart + 1, Math.min(end, totalLength))

  const walker = document.createTreeWalker(contentElement, NodeFilter.SHOW_TEXT, null)
  let node: Text | null
  let charCount = 0
  let startNode: Text | null = null
  let endNode: Text | null = null
  let startOffset = 0
  let endOffset = 0

  while ((node = walker.nextNode() as Text | null)) {
    const nodeText = node.textContent || ''
    const nodeLength = nodeText.length
    const nodeStart = charCount
    const nodeEnd = nodeStart + nodeLength

    if (!startNode && normalizedStart <= nodeEnd) {
      startNode = node
      startOffset = Math.max(0, normalizedStart - nodeStart)
    }

    if (!endNode && normalizedEnd <= nodeEnd) {
      endNode = node
      endOffset = Math.max(0, normalizedEnd - nodeStart)
      break
    }

    charCount = nodeEnd
  }

  if (!startNode || !endNode) return null

  const range = document.createRange()
  range.setStart(startNode, startOffset)
  range.setEnd(endNode, endOffset)
  return range
}

const highlightRangeInChapter = (chapterElement: Element, start: number, end: number): boolean => {
  const contentElement = chapterElement.querySelector('.chapter-text')
  if (!contentElement) return false

  const range = createRangeFromCharacterOffsets(contentElement, start, end)
  if (!range || range.collapsed) return false

  applyHighlightFromRange(range)
  return true
}

// Scroll a una mención específica dentro del documento
const scrollToMention = async (target: ScrollTarget) => {
  // Fix #2: Limpiar timers anteriores para evitar memory leaks
  cleanupScrollTimers()
  clearTemporaryMentionHighlights()

  // Crear nuevo abort controller para esta operación
  scrollAbortController = new AbortController()
  const signal = scrollAbortController.signal

  const isDialogueTarget = target.endPosition !== undefined && !!target.text

  console.log('scrollToMention called:', {
    chapterId: target.chapterId,
    position: target.position,
    endPosition: target.endPosition,
    text: target.text?.substring(0, 50) + (target.text && target.text.length > 50 ? '...' : '')
  })

  // Para que el scroll sea preciso, necesitamos cargar todos los capítulos
  // desde el inicio hasta el capítulo objetivo, ya que el contenido cargado
  // afecta las alturas del DOM y por tanto la posición de scroll

  // Encontrar el índice del capítulo objetivo
  const targetIndex = chapters.value.findIndex(ch => ch.id === target.chapterId)
  if (targetIndex === -1) {
    console.warn(`Chapter with ID ${target.chapterId} not found. Available chapters:`,
      chapters.value.map(ch => ({ id: ch.id, number: ch.chapterNumber })))
    return
  }

  // Cargar todos los capítulos desde el inicio hasta el objetivo (inclusive)
  // Esto asegura que la altura del documento sea correcta
  for (let i = 0; i <= targetIndex; i++) {
    const chapterId = chapters.value[i].id
    if (!loadedChapters.value.has(chapterId)) {
      loadedChapters.value.add(chapterId)
      touchChapter(chapterId)
    }
  }

  if (isDialogueTarget) {
    const chapterForDialogues = chapters.value[targetIndex]
    if (chapterForDialogues) {
      await loadChapterDialogues(chapterForDialogues.chapterNumber)
      highlightedContentCache.value.delete(chapterForDialogues.id)
    }
  }

  // Esperar a que Vue actualice el DOM con todos los capítulos cargados
  await nextTick()

  // Check si la operación fue abortada
  if (signal.aborted) return

  // Dar tiempo adicional para que el contenido HTML se renderice completamente
  // (especialmente importante para capítulos con mucho contenido)
  await new Promise<void>((resolve, reject) => {
    const timer = setTimeout(() => {
      activeScrollTimers.delete(timer)
      if (signal.aborted) reject(new Error('Aborted'))
      else resolve()
    }, 200)
    activeScrollTimers.add(timer)
    signal.addEventListener('abort', () => {
      clearTimeout(timer)
      activeScrollTimers.delete(timer)
      reject(new Error('Aborted'))
    })
  }).catch(() => {
    // Operación abortada, salir silenciosamente
    return
  })

  // Segunda espera para asegurar que v-html se haya procesado
  await nextTick()

  // Check si la operación fue abortada
  if (signal.aborted) return

  const chapterElement = viewerContainer.value?.querySelector(`[data-chapter-id="${target.chapterId}"]`)
  if (!chapterElement) {
    console.warn(`Chapter element not found for ${target.chapterId}`)
    return
  }

  const dialogueElement = findDialogueHighlightElement(
    chapterElement,
    target.position,
    target.endPosition
  )
  if (dialogueElement) {
    if (!isDialogueTarget) {
      applyTemporaryHighlightElement(dialogueElement)
      return
    }
  }

  const chapter = chapters.value.find(ch => ch.id === target.chapterId)
  let adjustedPosition: number | undefined = target.position
  let adjustedEndPosition: number | undefined = target.endPosition
  if (chapter) {
    const chapterLength = chapter.content?.length ?? 0
    if (
      adjustedPosition !== undefined &&
      chapter.positionStart !== undefined &&
      chapterLength > 0 &&
      adjustedPosition > chapterLength
    ) {
      adjustedPosition -= chapter.positionStart
    }
    if (
      adjustedEndPosition !== undefined &&
      chapter.positionStart !== undefined &&
      chapterLength > 0 &&
      adjustedEndPosition > chapterLength
    ) {
      adjustedEndPosition -= chapter.positionStart
    }

    const titleOffset = getTitleOffset(chapter.content, chapter.title)
    if (adjustedPosition !== undefined) adjustedPosition -= titleOffset
    if (adjustedEndPosition !== undefined) adjustedEndPosition -= titleOffset
  }

  // Para diálogos priorizamos búsqueda textual para evitar desalineaciones por offset
  // cuando hay saltos/parágrafos renderizados.
  if (isDialogueTarget && target.text) {
    const highlightedByText = await highlightTextInChapter(chapterElement, target.text, adjustedPosition)
    if (highlightedByText) return

    if (adjustedPosition !== undefined) {
      const textLength = Math.max(1, cleanExcerptForSearch(target.text).length)
      const fallbackEnd = adjustedEndPosition && adjustedEndPosition > adjustedPosition
        ? adjustedEndPosition
        : adjustedPosition + textLength
      const maxEnd = adjustedPosition + Math.max(textLength, 24)
      const clampedEnd = Math.min(maxEnd, fallbackEnd)
      const highlightedByRange = highlightRangeInChapter(
        chapterElement,
        adjustedPosition,
        Math.max(adjustedPosition + 1, clampedEnd)
      )
      if (highlightedByRange) return
    }

    if (adjustedPosition !== undefined) {
      highlightPositionInChapter(chapterElement, adjustedPosition)
    } else {
      chapterElement.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
    return
  }

  // Si tenemos rango completo, priorizarlo: es más preciso que la búsqueda textual.
  if (
    adjustedPosition !== undefined &&
    adjustedEndPosition !== undefined &&
    adjustedEndPosition > adjustedPosition
  ) {
    const highlighted = highlightRangeInChapter(chapterElement, adjustedPosition, adjustedEndPosition)
    if (highlighted) return
  }

  // Si hay texto específico a buscar, ir directamente a él (evitar doble scroll)
  if (target.text) {
    const highlighted = await highlightTextInChapter(chapterElement, target.text, adjustedPosition)
    if (!highlighted && adjustedPosition !== undefined) {
      highlightPositionInChapter(chapterElement, adjustedPosition)
    }
  } else if (target.position !== undefined) {
    // Si solo hay posición, calcular el elemento aproximado
    highlightPositionInChapter(chapterElement, adjustedPosition ?? target.position)
  } else {
    // Si no hay texto ni posición, scroll al capítulo
    chapterElement.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

// Limpia el texto de excerpt para buscar en el documento
// Elimina elipsis, contexto extra, y normaliza espacios
const cleanExcerptForSearch = (text: string): string => {
  return text
    // Eliminar elipsis al inicio y final
    .replace(/^[.…]+\s*/g, '')
    .replace(/\s*[.…]+$/g, '')
    // Eliminar comillas tipográficas que pueden no coincidir
    .replace(/[""''«»]/g, '"')
    // Normalizar espacios múltiples
    .replace(/\s+/g, ' ')
    .trim()
}

// Resalta un texto específico dentro del capítulo
// position: posición de caracteres donde debería estar el texto (para desambiguar)
// retryCount: número de reintentos realizados (para esperar a que v-html renderice)
const highlightTextInChapter = async (chapterElement: Element, text: string, position?: number, retryCount: number = 0): Promise<boolean> => {
  const MAX_RETRIES = 3
  const RETRY_DELAY = 150

  const contentElement = chapterElement.querySelector('.chapter-text')
  if (!contentElement) {
    console.warn('No .chapter-text element found in chapter')
    return false
  }

  // Verificar si el contenido tiene texto (v-html puede no haber renderizado aún)
  const hasContent = contentElement.textContent && contentElement.textContent.trim().length > 0
  if (!hasContent && retryCount < MAX_RETRIES) {
    console.log(`Content not ready yet, retry ${retryCount + 1}/${MAX_RETRIES}...`)
    // Fix #2: Trackear timer para cleanup
    await new Promise<void>(resolve => {
      const timer = setTimeout(() => {
        activeScrollTimers.delete(timer)
        resolve()
      }, RETRY_DELAY)
      activeScrollTimers.add(timer)
    })
    await nextTick()
    return highlightTextInChapter(chapterElement, text, position, retryCount + 1)
  }

  // Limpiar el texto de búsqueda
  const cleanText = cleanExcerptForSearch(text)
  if (!cleanText) {
    console.warn('Empty search text after cleaning')
    return false
  }

  const chapterText = contentElement.textContent || ''
  const lowerChapterText = chapterText.toLowerCase()

  const findAllOccurrences = (needle: string): number[] => {
    if (!needle) return []
    const indices: number[] = []
    let cursor = lowerChapterText.indexOf(needle)
    while (cursor !== -1) {
      indices.push(cursor)
      cursor = lowerChapterText.indexOf(needle, cursor + 1)
    }
    return indices
  }

  let searchedNeedle = cleanText.toLowerCase()
  let matchIndexes = findAllOccurrences(searchedNeedle)

  // Si no hay matches, intentar con fragmentos más cortos del texto.
  if (matchIndexes.length === 0 && cleanText.length > 20) {
    const words = cleanText.split(' ')
    const shortText = words.slice(0, Math.min(5, words.length)).join(' ').trim()
    if (shortText.length >= 10) {
      console.log(`Trying shorter search: "${shortText}"`)
      searchedNeedle = shortText.toLowerCase()
      matchIndexes = findAllOccurrences(searchedNeedle)
    }
  }

  if (matchIndexes.length === 0) {
    // Si no encontramos el texto pero hay contenido, intentar un retry más
    // (a veces v-html necesita más tiempo para procesar)
    if (retryCount < MAX_RETRIES) {
      console.log(`Text not found, retry ${retryCount + 1}/${MAX_RETRIES}...`)
      // Fix #2: Trackear timer para cleanup
      await new Promise<void>(resolve => {
        const timer = setTimeout(() => {
          activeScrollTimers.delete(timer)
          resolve()
        }, RETRY_DELAY)
        activeScrollTimers.add(timer)
      })
      await nextTick()
      return highlightTextInChapter(chapterElement, text, position, retryCount + 1)
    }

    console.warn(`Text "${cleanText}" not found in chapter after ${MAX_RETRIES} retries.`)
    return false
  }

  console.log(`Found ${matchIndexes.length} matches for "${cleanText.substring(0, 30)}..."`, { position })

  // Seleccionar la ocurrencia correcta:
  // Si tenemos posición, usar la más cercana a esa posición
  // Si no, usar la primera
  let bestStart = matchIndexes[0]

  if (position !== undefined && position >= 0 && matchIndexes.length > 1) {
    let minDistance = Math.abs(matchIndexes[0] - position)
    for (const idx of matchIndexes) {
      const distance = Math.abs(idx - position)
      if (distance < minDistance) {
        minDistance = distance
        bestStart = idx
      }
    }
  }

  const range = createRangeFromCharacterOffsets(
    contentElement,
    bestStart,
    bestStart + searchedNeedle.length
  )
  if (!range || range.collapsed) {
    return false
  }

  applyHighlightFromRange(range)
  return true
}

// Resalta una posición aproximada en el capítulo (basado en porcentaje)
const highlightPositionInChapter = (chapterElement: Element, position: number) => {
  const contentElement = chapterElement.querySelector('.chapter-text')
  if (!contentElement) return

  // Calcular posición aproximada basada en la longitud total
  const totalLength = contentElement.textContent?.length || 0
  if (totalLength === 0) return

  const targetRatio = position / totalLength
  const paragraphs = contentElement.querySelectorAll('p, div')

  if (paragraphs.length === 0) {
    // Si no hay párrafos, scroll al centro aproximado
    const targetY = chapterElement.getBoundingClientRect().top + (targetRatio * chapterElement.scrollHeight)
    window.scrollTo({ top: targetY, behavior: 'smooth' })
    return
  }

  // Encontrar el párrafo aproximado basado en la posición
  const targetIndex = Math.floor(targetRatio * paragraphs.length)
  const targetParagraph = paragraphs[Math.min(targetIndex, paragraphs.length - 1)]

  if (targetParagraph) {
    applyTemporaryHighlightElement(targetParagraph)
  }
}

// Detectar capítulo visible al hacer scroll
const onScroll = () => {
  if (!viewerContainer.value) return

  const viewerRect = viewerContainer.value.getBoundingClientRect()
  const viewerTop = viewerRect.top
  const viewerHeight = viewerRect.height

  // Encontrar el capítulo más visible
  let maxVisibleHeight = 0
  let mostVisibleChapterId: number | null = null

  chapters.value.forEach(chapter => {
    const element = viewerContainer.value?.querySelector(`[data-chapter-id="${chapter.id}"]`)
    if (!element) return

    const rect = element.getBoundingClientRect()
    const elementTop = rect.top - viewerTop
    const elementBottom = elementTop + rect.height

    // Calcular altura visible
    const visibleTop = Math.max(0, elementTop)
    const visibleBottom = Math.min(viewerHeight, elementBottom)
    const visibleHeight = Math.max(0, visibleBottom - visibleTop)

    if (visibleHeight > maxVisibleHeight) {
      maxVisibleHeight = visibleHeight
      mostVisibleChapterId = chapter.id
    }
  })

  if (mostVisibleChapterId !== null) {
    emit('chapterVisible', mostVisibleChapterId)
  }
}

// Estado para el diálogo de exportación
const showExportDialog = ref(false)
const exportFormat = ref<'docx' | 'pdf' | 'json'>('docx')
const exportLoading = ref(false)

// Exportar documento
const exportDocument = () => {
  showExportDialog.value = true
}

// Realizar la exportación
const doExport = async () => {
  exportLoading.value = true
  try {
    if (exportFormat.value === 'json') {
      // Exportar como JSON local
      const exportData = {
        project_id: props.projectId,
        title: props.documentTitle || 'Documento',
        exported_at: new Date().toISOString(),
        chapters: chapters.value.map(ch => ({
          id: ch.id,
          title: ch.title,
          chapter_number: ch.chapterNumber,
          word_count: ch.wordCount,
          content: ch.content
        })),
        entities: entities.value,
        total_words: totalWords.value
      }

      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${props.documentTitle || 'documento'}_export.json`
      a.click()
      URL.revokeObjectURL(url)
    } else {
      // Exportar como DOCX o PDF usando el endpoint del backend
      const params = new URLSearchParams({
        format: exportFormat.value,
        include_characters: 'true',
        include_alerts: 'true',
        include_timeline: 'true',
        include_relationships: 'true',
        include_style_guide: 'true'
      })

      const response = await fetch(
        apiUrl(`/api/projects/${props.projectId}/export/document?${params}`)
      )

      if (!response.ok) {
        throw new Error('Error al exportar documento')
      }

      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const ext = exportFormat.value === 'pdf' ? 'pdf' : 'docx'
      a.download = `${props.documentTitle || 'documento'}_informe.${ext}`
      a.click()
      URL.revokeObjectURL(url)
    }

    showExportDialog.value = false
  } catch (err) {
    console.error('Error exporting document:', err)
    toast.add({ severity: 'error', summary: 'Error', detail: 'Error al exportar el documento', life: 5000 })
  } finally {
    exportLoading.value = false
  }
}

// Captura de selección de texto para el asistente
const handleMouseUp = () => {
  const selection = window.getSelection()
  if (!selection || selection.isCollapsed) {
    // No hay selección - limpiar
    selectionStore.setTextSelection(null)
    return
  }

  const selectedText = selection.toString().trim()
  if (!selectedText) {
    selectionStore.setTextSelection(null)
    return
  }

  // Calcular posiciones
  const range = selection.getRangeAt(0)
  const container = range.commonAncestorContainer

  // Encontrar el capítulo y calcular offset
  let chapterElement: HTMLElement | null = null
  let node: Node | null = container
  while (node && node !== viewerContainer.value) {
    if (node instanceof HTMLElement && node.classList.contains('chapter-section')) {
      chapterElement = node
      break
    }
    node = node.parentNode
  }

  if (!chapterElement) {
    // No se pudo determinar el capítulo
    selectionStore.setTextSelection(null)
    return
  }

  const chapterId = parseInt(chapterElement.dataset.chapterId || '0')
  const chapter = chapters.value.find(c => c.id === chapterId)

  if (!chapter) {
    selectionStore.setTextSelection(null)
    return
  }

  // Calcular offset desde el inicio del capítulo
  // Crear un rango desde el inicio del capítulo hasta el inicio de la selección
  const chapterTextElement = chapterElement.querySelector('.chapter-text')
  if (!chapterTextElement) {
    selectionStore.setTextSelection(null)
    return
  }

  const rangeToStart = document.createRange()
  rangeToStart.setStart(chapterTextElement, 0)
  rangeToStart.setEnd(range.startContainer, range.startOffset)

  const textBeforeSelection = rangeToStart.toString()
  const offsetInChapter = textBeforeSelection.length

  // Las posiciones globales se calculan sumando el positionStart del capítulo
  const globalStart = (chapter.positionStart ?? 0) + offsetInChapter
  const globalEnd = globalStart + selectedText.length

  // Guardar selección en el store
  selectionStore.setTextSelection({
    start: globalStart,
    end: globalEnd,
    text: selectedText,
    chapter: chapter.title,
    chapterNumber: chapter.chapterNumber
  })
}

// Event delegation para clicks en entidades y alertas (evita onclick inline y window pollution)
const handleDocumentClick = (event: MouseEvent) => {
  const target = event.target as HTMLElement

  // Verificar si el click fue en una entidad resaltada
  if (target.classList.contains('entity-highlight')) {
    const entityId = target.dataset.entityId
    if (entityId) {
      emit('entityClick', parseInt(entityId, 10))
    }
    return
  }

  // Verificar si el click fue en una alerta de ortografía/gramática
  if (target.classList.contains('annotation')) {
    const annotationId = target.dataset.annotationId
    if (annotationId) {
      emit('annotationClick', parseInt(annotationId, 10))
    }
    return
  }
}

// Watchers
watch(() => props.scrollToChapterId, (chapterId) => {
  if (chapterId !== null && chapterId !== undefined) {
    scrollToChapter(chapterId)
  }
})

watch(() => props.scrollToTarget, (target) => {
  if (target) {
    scrollToMention(target)
  }
}, { deep: true })

watch(() => props.projectId, () => {
  loadDocument()
})

// Watch para capítulos externos (cuando el padre los actualiza durante análisis)
watch(() => props.externalChapters, (newChapters) => {
  if (newChapters && newChapters.length > 0) {
    // Usar los capítulos proporcionados por el padre
    chapters.value = newChapters
    loading.value = false
    error.value = null

    // Pre-cargar el primer capítulo si no hay ninguno cargado
    if (loadedChapters.value.size === 0 && newChapters.length > 0) {
      loadedChapters.value.add(newChapters[0].id)
    }

    // Reconfigurar observer para los nuevos capítulos
    nextTick(() => {
      setupIntersectionObserver()
    })
  }
}, { deep: true })

watch(() => props.chapterBadges, () => {
  void refreshVisibleChapterAnnotations()
})

// Watch para resaltar múltiples rangos de alerta (inconsistencias)
// Cuando cambian los rangos de alertas, invalidar cache y hacer scroll
watch(() => props.alertHighlightRanges, async (ranges) => {
  // Invalidar cache de capítulos afectados para que se regeneren con los nuevos highlights
  highlightedContentCache.value.clear()

  if (!ranges || ranges.length === 0) return

  // Cargar los capítulos necesarios
  const chapterIds = new Set<number>()
  for (const range of ranges) {
    if (range.chapterId) {
      chapterIds.add(range.chapterId)
    }
  }

  for (const chId of chapterIds) {
    if (!loadedChapters.value.has(chId)) {
      loadedChapters.value.add(chId)
      touchChapter(chId)
    }
  }

  await nextTick()

  // Scroll al primer rango
  if (ranges.length > 0) {
    const firstRange = ranges[0]
    if (firstRange.chapterId) {
      const target: ScrollTarget = {
        chapterId: firstRange.chapterId,
        position: firstRange.startChar,
        endPosition: firstRange.endChar,
        text: firstRange.text,
        preserveMultiHighlights: true,
      }
      await scrollToMention(target)
    }
  }
}, { deep: true })

// Convertir hex a rgba
const hexToRgba = (hex: string, alpha: number): string => {
  // Remover # si existe
  const cleanHex = hex.replace('#', '')

  // Expandir hex corto (3 chars) a largo (6 chars)
  const fullHex = cleanHex.length === 3
    ? cleanHex.split('').map(c => c + c).join('')
    : cleanHex

  const r = parseInt(fullHex.substring(0, 2), 16)
  const g = parseInt(fullHex.substring(2, 4), 16)
  const b = parseInt(fullHex.substring(4, 6), 16)

  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

// Escuchar cambios de configuración (evento personalizado desde SettingsView)
const handleSettingsChange = () => {
  loadAppearanceSettings()
}

// Lifecycle
onMounted(() => {
  loadAppearanceSettings()
  loadDocument()
  // Configurar observer después de que se carguen los capítulos
  nextTick(() => {
    setupIntersectionObserver()
  })
  // Escuchar cambios de configuración
  window.addEventListener('settings-changed', handleSettingsChange)
})

onUnmounted(() => {
  // Fix #2: Limpiar timers activos para evitar memory leaks
  cleanupScrollTimers()
  clearTemporaryMentionHighlights()

  // Limpiar observer
  if (intersectionObserver) {
    intersectionObserver.disconnect()
    intersectionObserver = null
  }
  chapterRefs.clear()
  window.removeEventListener('settings-changed', handleSettingsChange)
})

// Exponer métodos para el padre
defineExpose({
  scrollToChapter,
  scrollToMention,
  loadDocument
})
</script>

<style scoped>
.document-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  /* Use theme-aware CSS variable with fallback */
  background: var(--app-document-bg, var(--p-surface-0, #ffffff));
  border-radius: var(--app-radius);
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.viewer-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  /* Use theme-aware CSS variables with fallbacks */
  background: var(--app-toolbar-bg, var(--p-surface-50, #fafafa));
  border-bottom: 1px solid var(--app-toolbar-border, var(--p-surface-200, #e5e5e5));
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.viewer-title {
  font-weight: 600;
  font-size: 1rem;
  /* Use theme-aware CSS variable with fallback */
  color: var(--app-document-text, var(--p-text-color, #1f2937));
}

.word-count {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.word-count i {
  font-size: 0.875rem;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.viewer-content {
  flex: 1;
  overflow-y: auto;
  /* Reduced horizontal padding to better use screen space */
  padding: 1.5rem 1rem;
  /* Use theme-aware CSS variable with fallback */
  background: var(--app-document-bg, var(--p-surface-0, #ffffff));
}

/* Larger screens get more padding */
@media (min-width: 1024px) {
  .viewer-content {
    padding: 1.5rem 2rem;
  }
}

@media (min-width: 1440px) {
  .viewer-content {
    padding: 2rem 3rem;
  }
}

.viewer-loading,
.viewer-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 1rem;
  color: var(--text-color-secondary);
}

.viewer-error i {
  font-size: 3rem;
  color: var(--ds-text-danger);
}

.document-content {
  /* Fluid width with max constraint for readability */
  max-width: min(900px, 100%);
  width: 100%;
  margin: 0 auto;
  line-height: 1.8;
  /* Use theme-aware CSS variable with fallback */
  color: var(--app-document-text, var(--p-text-color, #1f2937));
}

.chapter-section {
  margin-bottom: 3rem;
  /* Offset for scroll-to navigation to account for toolbar */
  scroll-margin-top: 80px;
}

.chapter-header {
  position: relative;
}

.chapter-badges-float {
  position: absolute;
  left: -40px; /* Más cerca del título */
  top: 0; /* Alineado con el inicio del título */
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  align-items: flex-end;
}

.chapter-badges-float .alert-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 2rem;
  height: 1.75rem;
  padding: 0 0.5rem;
  border-radius: 0.875rem;
  border: none;
  font-size: 0.75rem;
  font-weight: 600;
  color: white;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.12);
}

.chapter-badges-float .alert-badge:hover {
  transform: translateX(-2px) scale(1.05);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.18);
}

.chapter-badges-float .alert-badge .badge-count {
  font-size: 0.75rem;
  line-height: 1;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.chapter-title {
  font-size: 1.75rem;
  font-weight: 700;
  /* Use theme-aware CSS variable with fallback */
  color: var(--app-document-text, var(--p-text-color, #1f2937));
  margin-bottom: 1.5rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid var(--p-primary-color, var(--primary-color));
}

.chapter-text {
  /* font-size y line-height se aplican dinámicamente desde contentStyle */
  text-align: justify;
}

.chapter-text :deep(p) {
  margin-bottom: 1rem;
}

.chapter-text :deep(p:last-child) {
  margin-bottom: 0;
}

/* Section headings inside chapter content (H2, H3, H4) - different sizes for visual hierarchy */
.chapter-text :deep(h2),
.chapter-text :deep(.section-h2) {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--app-document-text, var(--p-text-color, #1f2937));
  margin-top: 2rem;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--p-surface-200, #e5e5e5);
  scroll-margin-top: 80px;
}

.chapter-text :deep(h3),
.chapter-text :deep(.section-h3) {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--app-document-text, var(--p-text-color, #1f2937));
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
  scroll-margin-top: 80px;
}

.chapter-text :deep(h4),
.chapter-text :deep(.section-h4) {
  font-size: 1.1rem;
  font-weight: 600;
  font-style: italic;
  color: var(--p-text-muted-color, var(--text-color-secondary, #6b7280));
  margin-top: 1.25rem;
  margin-bottom: 0.5rem;
  scroll-margin-top: 80px;
}

.chapter-text :deep(h5),
.chapter-text :deep(.section-h5) {
  font-size: 1rem;
  font-weight: 600;
  color: var(--p-text-muted-color, var(--text-color-secondary, #6b7280));
  margin-top: 1rem;
  margin-bottom: 0.5rem;
  scroll-margin-top: 80px;
}

/* Resaltado de entidades */
.chapter-text :deep(mark.entity-highlight) {
  background: color-mix(in srgb, var(--p-primary-color, #3B82F6) 15%, transparent);
  color: inherit;
  padding: 0.125rem 0.25rem;
  border-radius: var(--app-radius-sm);
  cursor: pointer;
  transition: background-color 0.2s;
}

.chapter-text :deep(mark.entity-highlight:hover) {
  background: color-mix(in srgb, var(--p-primary-color, #3B82F6) 30%, transparent);
}

.chapter-text :deep(mark.entity-highlight-active) {
  background: color-mix(in srgb, var(--p-primary-color, #3B82F6) 40%, transparent) !important;
  font-weight: 600;
}

/* Highlight temporal para scroll to mention (via clase en elemento existente) */
.chapter-text :deep(.mention-highlight-selected) {
  background: rgba(251, 191, 36, 0.30);
  border-radius: var(--app-radius-sm);
  transition: all var(--ds-duration-fast) var(--ds-ease-in-out);
}

/* Anotaciones de gramática y ortografía */
.chapter-text :deep(.annotation) {
  position: relative;
  cursor: pointer;
  border-bottom: 2px wavy;
  transition: background-color 0.2s ease;
}

.chapter-text :deep(.annotation:hover) {
  background: rgba(251, 191, 36, 0.25) !important;
}

.chapter-text :deep(.annotation.grammar-error) {
  border-color: var(--error-grammar-color, var(--blue-500));
  background: color-mix(in srgb, var(--error-grammar-color, #3b82f6) 8%, transparent);
}

.chapter-text :deep(.annotation.spelling-error) {
  border-color: var(--ds-color-danger, #ef4444);
  background: rgba(239, 68, 68, 0.08);
}

.chapter-text :deep(.annotation.severity-critical),
.chapter-text :deep(.annotation.severity-high) {
  border-width: 3px;
}

.chapter-text :deep(.annotation.severity-low),
.chapter-text :deep(.annotation.severity-info) {
  border-style: dashed;
}

/* Toggle de anotaciones activo */
.annotation-toggle-active {
  color: var(--primary-color) !important;
}

/* Toggle de errores de ortografia activo */
.spelling-toggle-active {
  color: var(--ds-color-danger, #ef4444) !important;
  border-color: var(--ds-color-danger, #ef4444) !important;
}

/* Toggle de errores de gramatica activo */
.grammar-toggle-active {
  color: var(--ds-text-info) !important;
  border-color: var(--blue-500) !important;
}

/* Toggle de atribución de diálogos activo */
.dialogue-toggle-active {
  color: var(--purple-500) !important;
  border-color: var(--purple-500) !important;
}

/* Highlight de diálogos por confianza */
.chapter-text :deep(.dialogue-highlight) {
  position: relative;
  cursor: pointer;
  border-radius: var(--app-radius-sm);
  padding: 0 2px;
  margin: 0 -2px;
  transition: background-color 0.2s, box-shadow 0.2s;
}

.chapter-text :deep(.dialogue-highlight:hover) {
  box-shadow: 0 0 0 2px currentColor;
}

.chapter-text :deep(.dialogue-highlight.dialogue-confidence-high) {
  background: rgba(34, 197, 94, 0.15);
  border-bottom: 2px solid var(--green-500);
  color: inherit;
}

.chapter-text :deep(.dialogue-highlight.dialogue-confidence-medium) {
  background: rgba(251, 191, 36, 0.15);
  border-bottom: 2px solid var(--yellow-500);
  color: inherit;
}

.chapter-text :deep(.dialogue-highlight.dialogue-confidence-low) {
  background: rgba(239, 68, 68, 0.15);
  border-bottom: 2px solid var(--ds-color-danger, #ef4444);
  color: inherit;
}

.chapter-text :deep(.dialogue-highlight.dialogue-confidence-unknown) {
  background: rgba(156, 163, 175, 0.15);
  border-bottom: 2px dashed var(--gray-400);
  color: inherit;
}

/* Icono personalizado para ortografia */
.toggle-icon {
  font-size: 0.75rem;
  font-weight: 700;
  line-height: 1;
}

.spelling-icon {
  text-decoration: underline wavy;
  text-decoration-color: var(--ds-color-danger, #ef4444);
  text-underline-offset: 2px;
}

/* Separador de toolbar */
.toolbar-divider {
  width: 1px;
  height: 1.5rem;
  background: var(--surface-300);
  margin: 0 0.25rem;
}

.chapter-text :deep(mark.entity-character) {
  background: rgba(34, 197, 94, 0.15);
}

.chapter-text :deep(mark.entity-location) {
  background: rgba(239, 68, 68, 0.15);
}

.chapter-text :deep(mark.entity-object) {
  background: rgba(234, 179, 8, 0.15);
}

.chapter-text :deep(mark.entity-event) {
  background: rgba(168, 85, 247, 0.15);
}

.no-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  gap: 1rem;
  color: var(--text-color-secondary);
}

.no-content i {
  font-size: 3rem;
}

/* Placeholder para lazy loading */
.chapter-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 3rem;
  min-height: 200px;
  background: var(--surface-50);
  border-radius: var(--app-radius);
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

/* Diálogo de exportación */
.export-options {
  padding: 0.5rem 0;
}

.export-options p {
  margin-bottom: 1rem;
  color: var(--text-color-secondary);
}

.export-format-options {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.format-option {
  display: flex;
  flex-direction: column;
  padding: 1rem;
  border: 2px solid var(--surface-200);
  border-radius: var(--app-radius);
  cursor: pointer;
  transition: all 0.2s;
}

.format-option:hover {
  border-color: var(--primary-300);
  background: var(--surface-50);
}

.format-option.selected {
  border-color: var(--primary-500);
  background: var(--primary-50);
}

.format-option i {
  font-size: 1.5rem;
  color: var(--primary-500);
  margin-bottom: 0.5rem;
}

.format-option span {
  font-weight: 600;
  font-size: 1rem;
}

.format-option small {
  color: var(--text-color-secondary);
  font-size: 0.85rem;
}
</style>

<!-- Estilos globales para highlight dinámico -->
<style>
/* CSS Custom Highlight API — resalta texto sin modificar el DOM */
::highlight(mention-temp) {
  background-color: rgba(251, 191, 36, 0.30);
}

.mention-highlight-selected {
  background: rgba(251, 191, 36, 0.30) !important;
  border-radius: var(--app-radius-sm);
}

/* Multi-highlight para alertas de inconsistencia */
.alert-multi-highlight {
  display: inline;
  animation: alert-highlight-pulse 2s ease-in-out infinite;
  cursor: help;
  position: relative;
}

.alert-multi-highlight::after {
  content: attr(data-label);
  position: absolute;
  top: -1.5em;
  left: 0;
  font-size: 0.7rem;
  font-weight: 600;
  background: inherit;
  padding: 1px 4px;
  border-radius: var(--app-radius-sm);
  white-space: nowrap;
  opacity: 0;
  transition: opacity 0.2s;
  pointer-events: none;
}

.alert-multi-highlight:hover::after {
  opacity: 1;
}

@keyframes alert-highlight-pulse {
  0%, 100% {
    filter: brightness(1);
  }
  50% {
    filter: brightness(1.2);
  }
}
</style>
