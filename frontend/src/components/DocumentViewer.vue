<template>
  <div class="document-viewer" ref="viewerContainer">
    <!-- Diálogo de exportación -->
    <Dialog
      :visible="showExportDialog"
      @update:visible="showExportDialog = $event"
      modal
      header="Exportar Documento"
      :style="{ width: '400px' }"
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
          :icon="showSpellingErrors ? 'pi pi-check-square' : 'pi pi-stop'"
          :text="!showSpellingErrors"
          :outlined="showSpellingErrors"
          rounded
          size="small"
          @click="showSpellingErrors = !showSpellingErrors"
          v-tooltip.bottom="showSpellingErrors ? 'Ocultar errores de ortografia' : 'Mostrar errores de ortografia'"
          :class="{ 'spelling-toggle-active': showSpellingErrors }"
        >
          <template #icon>
            <span class="toggle-icon spelling-icon">Aa</span>
          </template>
        </Button>
        <!-- Toggle errores de gramatica -->
        <Button
          :icon="showGrammarErrors ? 'pi pi-check-square' : 'pi pi-stop'"
          :text="!showGrammarErrors"
          :outlined="showGrammarErrors"
          rounded
          size="small"
          @click="showGrammarErrors = !showGrammarErrors"
          v-tooltip.bottom="showGrammarErrors ? 'Ocultar errores de gramatica' : 'Mostrar errores de gramatica'"
          :class="{ 'grammar-toggle-active': showGrammarErrors }"
        >
          <template #icon>
            <i class="pi pi-language"></i>
          </template>
        </Button>
        <!-- Toggle atribución de diálogos -->
        <Button
          :text="!showDialoguePanel"
          :outlined="showDialoguePanel"
          rounded
          size="small"
          @click="showDialoguePanel = !showDialoguePanel"
          v-tooltip.bottom="showDialoguePanel ? 'Ocultar atribución de diálogos' : 'Mostrar atribución de diálogos'"
          :class="{ 'dialogue-toggle-active': showDialoguePanel }"
        >
          <template #icon>
            <i class="pi pi-comments"></i>
          </template>
        </Button>
        <span class="toolbar-divider"></span>
        <Button
          icon="pi pi-download"
          text
          rounded
          @click="exportDocument"
          v-tooltip.bottom="'Exportar'"
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

      <div v-else class="document-content">
        <!-- Renderizar capítulos con lazy loading -->
        <div
          v-for="chapter in chapters"
          :key="chapter.id"
          :ref="el => setChapterRef(el, chapter.id)"
          :data-chapter-id="chapter.id"
          class="chapter-section"
        >
          <h2 class="chapter-title">
            {{ chapter.title }}
          </h2>

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

    <!-- Sidebar para atribución de diálogos -->
    <Sidebar
      :visible="showDialoguePanel"
      @update:visible="showDialoguePanel = $event"
      position="right"
      :style="{ width: '400px' }"
      header="Atribución de Diálogos"
    >
      <DialogueAttributionPanel
        v-if="showDialoguePanel"
        :project-id="projectId"
        :chapters="chaptersForPanel"
        @select-dialogue="onDialogueSelected"
      />
    </Sidebar>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick, watchEffect } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Sidebar from 'primevue/sidebar'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'
import type { Chapter } from '@/types'
import type { ApiChapter } from '@/types/api/projects'
import { transformChapters } from '@/types/transformers/projects'
import DialogueAttributionPanel from '@/components/DialogueAttributionPanel.vue'

const toast = useToast()

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
  text?: string      // Texto a resaltar
}

const props = defineProps<{
  projectId: number
  documentTitle?: string
  highlightEntityId?: number | null
  scrollToChapterId?: number | null
  scrollToTarget?: ScrollTarget | null
  /** Capítulos proporcionados por el padre (opcional, si no se pasan se cargan del API) */
  externalChapters?: Chapter[]
}>()

const emit = defineEmits<{
  chapterVisible: [chapterId: number]
  entityClick: [entityId: number]
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
      chapterAnnotations.value.delete(oldestId)
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

// Computed para mantener compatibilidad con showAnnotations
const showAnnotations = computed(() => showSpellingErrors.value || showGrammarErrors.value)

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

// Computed para el estilo del contenido
const contentStyle = computed(() => ({
  fontSize: fontSizeMap[fontSize.value] || '1rem',
  lineHeight: lineHeight.value
}))

// Chapters formatted for DialogueAttributionPanel
const chaptersForPanel = computed(() => {
  return chapters.value.map(ch => ({
    id: ch.id,
    number: ch.chapterNumber,
    title: ch.title
  }))
})

// Handler for dialogue selection from panel
const onDialogueSelected = (attribution: { startChar: number; endChar: number; text: string; chapterNumber?: number }) => {
  // Encontrar el capítulo que contiene este diálogo
  let targetChapter: Chapter | undefined

  if (attribution.chapterNumber) {
    targetChapter = chapters.value.find(ch => ch.chapterNumber === attribution.chapterNumber)
  }

  if (!targetChapter) {
    // Fallback: buscar en todos los capítulos basándose en la posición
    // Asumimos que startChar es relativo al capítulo
    console.warn('No chapter number in attribution, cannot scroll precisely')
    return
  }

  // Usar scrollToMention para ir al diálogo
  scrollToMention({
    chapterId: targetChapter.id,
    position: attribution.startChar,
    text: attribution.text
  })
}

// Cargar atribuciones de diálogo para un capítulo
const loadChapterDialogues = async (chapterNumber: number) => {
  if (chapterDialogues.value.has(chapterNumber)) return

  try {
    const API_BASE = 'http://localhost:8008'
    const response = await fetch(`${API_BASE}/api/projects/${props.projectId}/chapters/${chapterNumber}/dialogue-attributions`)
    const data = await response.json()

    if (data.success && data.data?.attributions) {
      chapterDialogues.value.set(chapterNumber, data.data.attributions)
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
  return chapters.value.reduce((sum, ch) => sum + ch.wordCount, 0)
})

// Cargar documento
const loadDocument = async () => {
  loading.value = true
  error.value = null

  // Resetear estado de lazy loading
  loadedChapters.value.clear()
  visibleChapters.value.clear()
  chapterRefs.clear()

  try {
    const API_BASE = 'http://localhost:8008'

    // Si hay capítulos externos, usarlos directamente
    if (props.externalChapters && props.externalChapters.length > 0) {
      chapters.value = props.externalChapters
    } else {
      // Cargar capítulos del API
      const chaptersResponse = await fetch(`${API_BASE}/api/projects/${props.projectId}/chapters`)
      const chaptersData = await chaptersResponse.json()

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
    const entitiesResponse = await fetch(`${API_BASE}/api/projects/${props.projectId}/entities`)
    const entitiesData = await entitiesResponse.json()

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
const loadChapterAnnotations = async (chapterNumber: number) => {
  if (chapterAnnotations.value.has(chapterNumber)) return

  try {
    const API_BASE = 'http://localhost:8008'
    const response = await fetch(`${API_BASE}/api/projects/${props.projectId}/chapters/${chapterNumber}/annotations`)
    const data = await response.json()

    if (data.success && data.data?.annotations) {
      chapterAnnotations.value.set(chapterNumber, data.data.annotations)
    }
  } catch (err) {
    console.error(`Error loading annotations for chapter ${chapterNumber}:`, err)
  }
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
    /^[IVXLCDM]+[\.\:\s]/i.test(firstLine) ||
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

// Resaltar entidades en el contenido
const getHighlightedContent = (chapter: Chapter): string => {
  if (!chapter.content) return ''

  // Cargar anotaciones de gramática/ortografía para este capítulo (async)
  loadChapterAnnotations(chapter.chapterNumber)

  // Cargar atribuciones de diálogo si el panel está abierto
  if (showDialoguePanel.value) {
    loadChapterDialogues(chapter.chapterNumber)
  }

  // Primero remover el título si está duplicado al inicio del contenido
  const contentWithoutTitle = removeLeadingTitle(chapter.content, chapter.title)
  const titleOffset = getTitleOffset(chapter.content, chapter.title)
  let content = escapeHtml(contentWithoutTitle)

  // Aplicar anotaciones de gramática/ortografía
  if (showSpellingErrors.value || showGrammarErrors.value) {
    const annotations = chapterAnnotations.value.get(chapter.chapterNumber) || []

    // Filtrar por tipo según los toggles activos
    const filteredAnnotations = annotations.filter(a => {
      if (a.type === 'grammar' && !showGrammarErrors.value) return false
      if ((a.type === 'spelling' || a.type === 'orthography') && !showSpellingErrors.value) return false
      return true
    })

    // Ordenar de mayor a menor posición para no afectar índices
    const sortedAnnotations = [...filteredAnnotations]
      .filter(a => a.start_char !== undefined && a.end_char !== undefined)
      .sort((a, b) => b.start_char - a.start_char)

    sortedAnnotations.forEach(annotation => {
      // Calcular posición ajustada (el HTML escaping puede cambiar longitudes)
      // Por simplicidad, aplicamos sobre el contenido escapado
      const annotationClass = annotation.type === 'grammar' ? 'grammar-error' : 'spelling-error'
      const severityClass = `severity-${annotation.severity}`
      const tooltip = annotation.suggestion
        ? `${annotation.title}. Sugerencia: ${annotation.suggestion}`
        : annotation.title

      // Buscar el texto del excerpt en el contenido
      if (annotation.excerpt) {
        const excerptEscaped = escapeHtml(annotation.excerpt)
        const excerptIndex = content.indexOf(excerptEscaped)
        if (excerptIndex !== -1) {
          const before = content.substring(0, excerptIndex)
          const after = content.substring(excerptIndex + excerptEscaped.length)
          content = before +
            `<span class="annotation ${annotationClass} ${severityClass}" ` +
            `data-annotation-id="${annotation.id}" title="${escapeHtml(tooltip)}">` +
            excerptEscaped +
            `</span>` +
            after
        }
      }
    })
  }

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
      if (adjustedStart < 0) return

      // Buscar el texto del diálogo en el contenido
      const dialogueText = escapeHtml(dialogue.text)
      const dialogueIndex = content.indexOf(dialogueText)

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

      // Un solo pase de reemplazo
      content = content.replace(combinedRegex, (match) => {
        const entity = entityByName.get(match.toLowerCase())
        if (!entity) return match

        const isActive = entity.id === props.highlightEntityId
        const entityType = entity.entity_type?.toLowerCase() || 'other'

        if (isActive) {
          return `<mark class="entity-highlight entity-highlight-active" data-entity-id="${entity.id}">${match}</mark>`
        } else {
          return `<mark class="entity-highlight entity-${entityType}" data-entity-id="${entity.id}" onclick="window.handleEntityClick(${entity.id})">${match}</mark>`
        }
      })
    }
  }

  // Convertir saltos de línea en párrafos y detectar encabezados de sección
  return content
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
    /^[IVXLCDM]+[\.\:\s]/i.test(trimmed) ||
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
  await new Promise(resolve => setTimeout(resolve, 50))

  const element = viewerContainer.value?.querySelector(`[data-chapter-id="${chapterId}"]`)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

// Variable para almacenar el highlight temporal
const temporaryHighlightClass = 'mention-highlight-active'

// Scroll a una mención específica dentro del documento
const scrollToMention = async (target: ScrollTarget) => {
  console.log('scrollToMention called:', {
    chapterId: target.chapterId,
    position: target.position,
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

  // Esperar a que Vue actualice el DOM con todos los capítulos cargados
  await nextTick()

  // Dar tiempo adicional para que el contenido HTML se renderice completamente
  // (especialmente importante para capítulos con mucho contenido)
  await new Promise(resolve => setTimeout(resolve, 200))

  // Segunda espera para asegurar que v-html se haya procesado
  await nextTick()

  const chapterElement = viewerContainer.value?.querySelector(`[data-chapter-id="${target.chapterId}"]`)
  if (!chapterElement) {
    console.warn(`Chapter element not found for ${target.chapterId}`)
    return
  }

  // Si hay texto específico a buscar, ir directamente a él (evitar doble scroll)
  if (target.text) {
    // Calcular la posición ajustada dentro del capítulo
    const chapter = chapters.value.find(ch => ch.id === target.chapterId)
    let adjustedPosition: number | undefined = undefined

    if (chapter && target.position !== undefined) {
      const titleOffset = getTitleOffset(chapter.content, chapter.title)
      adjustedPosition = target.position - titleOffset
    }

    // Resaltar directamente el texto (incluye scroll)
    await highlightTextInChapter(chapterElement, target.text!, adjustedPosition)
  } else if (target.position !== undefined) {
    // Si solo hay posición, calcular el elemento aproximado
    const chapter = chapters.value.find(ch => ch.id === target.chapterId)
    let adjustedPosition = target.position
    if (chapter) {
      const titleOffset = getTitleOffset(chapter.content, chapter.title)
      adjustedPosition = adjustedPosition - titleOffset
    }
    highlightPositionInChapter(chapterElement, adjustedPosition)
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
const highlightTextInChapter = async (chapterElement: Element, text: string, position?: number, retryCount: number = 0): Promise<void> => {
  const MAX_RETRIES = 3
  const RETRY_DELAY = 150

  const contentElement = chapterElement.querySelector('.chapter-text')
  if (!contentElement) {
    console.warn('No .chapter-text element found in chapter')
    return
  }

  // Verificar si el contenido tiene texto (v-html puede no haber renderizado aún)
  const hasContent = contentElement.textContent && contentElement.textContent.trim().length > 0
  if (!hasContent && retryCount < MAX_RETRIES) {
    console.log(`Content not ready yet, retry ${retryCount + 1}/${MAX_RETRIES}...`)
    await new Promise(resolve => setTimeout(resolve, RETRY_DELAY))
    await nextTick()
    return highlightTextInChapter(chapterElement, text, position, retryCount + 1)
  }

  // Limpiar el texto de búsqueda
  const cleanText = cleanExcerptForSearch(text)
  if (!cleanText) {
    console.warn('Empty search text after cleaning')
    return
  }

  // Buscar TODAS las ocurrencias del texto (case-insensitive)
  const walker = document.createTreeWalker(contentElement, NodeFilter.SHOW_TEXT, null)

  interface TextMatch {
    node: Text
    index: number
    length: number
    charPosition: number  // Posición en caracteres desde el inicio del contenido
  }
  const matches: TextMatch[] = []
  let node: Text | null
  let charCount = 0

  // Primero intentar búsqueda exacta
  while ((node = walker.nextNode() as Text | null)) {
    const nodeText = node.textContent || ''
    let searchIndex = 0

    // Buscar ocurrencias exactas (case-insensitive)
    while (true) {
      const index = nodeText.toLowerCase().indexOf(cleanText.toLowerCase(), searchIndex)
      if (index === -1) break

      matches.push({
        node,
        index,
        length: cleanText.length,
        charPosition: charCount + index
      })
      searchIndex = index + 1
    }

    charCount += nodeText.length
  }

  // Si no hay matches, intentar con fragmentos más cortos del texto
  if (matches.length === 0 && cleanText.length > 20) {
    // Intentar con las primeras palabras (más probable que coincidan)
    const words = cleanText.split(' ')
    const shortText = words.slice(0, Math.min(5, words.length)).join(' ')

    if (shortText.length >= 10) {
      console.log(`Trying shorter search: "${shortText}"`)

      // Reset walker
      const walker2 = document.createTreeWalker(contentElement, NodeFilter.SHOW_TEXT, null)
      charCount = 0

      while ((node = walker2.nextNode() as Text | null)) {
        const nodeText = node.textContent || ''
        let searchIndex = 0

        while (true) {
          const index = nodeText.toLowerCase().indexOf(shortText.toLowerCase(), searchIndex)
          if (index === -1) break

          matches.push({
            node,
            index,
            length: shortText.length,
            charPosition: charCount + index
          })
          searchIndex = index + 1
        }

        charCount += nodeText.length
      }
    }
  }

  if (matches.length === 0) {
    // Si no encontramos el texto pero hay contenido, intentar un retry más
    // (a veces v-html necesita más tiempo para procesar)
    if (retryCount < MAX_RETRIES) {
      console.log(`Text not found, retry ${retryCount + 1}/${MAX_RETRIES}...`)
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY))
      await nextTick()
      return highlightTextInChapter(chapterElement, text, position, retryCount + 1)
    }

    console.warn(`Text "${cleanText}" not found in chapter after ${MAX_RETRIES} retries. Using position fallback.`)
    // Fallback: usar highlightPositionInChapter si tenemos posición
    if (position !== undefined) {
      highlightPositionInChapter(chapterElement, position)
    }
    return
  }

  console.log(`Found ${matches.length} matches for "${cleanText.substring(0, 30)}..."`, { position })

  // Seleccionar la ocurrencia correcta:
  // Si tenemos posición, usar la más cercana a esa posición
  // Si no, usar la primera
  let match = matches[0]

  if (position !== undefined && position >= 0 && matches.length > 1) {
    let minDistance = Math.abs(matches[0].charPosition - position)
    for (const m of matches) {
      const distance = Math.abs(m.charPosition - position)
      if (distance < minDistance) {
        minDistance = distance
        match = m
      }
    }
  }

  // Crear el rango para el highlight
  const range = document.createRange()
  range.setStart(match.node, match.index)
  range.setEnd(match.node, match.index + match.length)

  // Crear span de highlight
  const highlightSpan = document.createElement('span')
  highlightSpan.className = temporaryHighlightClass

  try {
    // Extraer el contenido y envolverlo en el span
    highlightSpan.appendChild(range.extractContents())
    range.insertNode(highlightSpan)
  } catch (e) {
    console.warn('Error creating highlight span:', e)
    return
  }

  // Scroll al elemento resaltado (único scroll, no hay doble)
  highlightSpan.scrollIntoView({ behavior: 'smooth', block: 'center' })

  // Animación de entrada
  highlightSpan.classList.add('highlight-entering')
  setTimeout(() => {
    highlightSpan.classList.remove('highlight-entering')
  }, 500)

  // Quitar highlight después de 3 segundos
  setTimeout(() => {
    highlightSpan.classList.add('highlight-leaving')

    setTimeout(() => {
      const parent = highlightSpan.parentNode
      if (parent) {
        // Restaurar: mover los hijos del span de vuelta al padre
        while (highlightSpan.firstChild) {
          parent.insertBefore(highlightSpan.firstChild, highlightSpan)
        }
        parent.removeChild(highlightSpan)
        parent.normalize()
      }
    }, 400)
  }, 3000)
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
    // Añadir clase de highlight temporal
    targetParagraph.classList.add(temporaryHighlightClass)
    targetParagraph.scrollIntoView({ behavior: 'smooth', block: 'center' })

    // Quitar highlight después de 3 segundos
    setTimeout(() => {
      targetParagraph.classList.remove(temporaryHighlightClass)
    }, 3000)
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
        `http://localhost:8008/api/projects/${props.projectId}/export/document?${params}`
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

// Exponer función global para manejar clicks en entidades
if (typeof window !== 'undefined') {
  (window as any).handleEntityClick = (entityId: number) => {
    emit('entityClick', entityId)
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
  border-radius: 8px;
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
  color: var(--red-500);
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
  background: rgba(59, 130, 246, 0.15);
  color: inherit;
  padding: 0.125rem 0.25rem;
  border-radius: 3px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.chapter-text :deep(mark.entity-highlight:hover) {
  background: rgba(59, 130, 246, 0.3);
}

.chapter-text :deep(mark.entity-highlight-active) {
  background: rgba(59, 130, 246, 0.4) !important;
  font-weight: 600;
}

/* Highlight temporal para scroll to mention */
.chapter-text :deep(.mention-highlight-active) {
  background: linear-gradient(90deg, rgba(251, 191, 36, 0.5), rgba(251, 191, 36, 0.3));
  border-radius: 2px;
  box-shadow: 0 0 0 2px rgba(251, 191, 36, 0.3);
  animation: highlight-glow 1.5s ease-in-out infinite;
  transition: all 0.4s ease-out;
}

/* Animación de entrada */
.chapter-text :deep(.mention-highlight-active.highlight-entering) {
  animation: highlight-enter 0.5s ease-out forwards;
}

/* Animación de salida */
.chapter-text :deep(.mention-highlight-active.highlight-leaving) {
  animation: highlight-leave 0.4s ease-out forwards;
}

@keyframes highlight-glow {
  0%, 100% {
    background: rgba(251, 191, 36, 0.35);
    box-shadow: 0 0 0 2px rgba(251, 191, 36, 0.2);
  }
  50% {
    background: rgba(251, 191, 36, 0.55);
    box-shadow: 0 0 8px 2px rgba(251, 191, 36, 0.4);
  }
}

@keyframes highlight-enter {
  0% {
    background: rgba(251, 191, 36, 0);
    box-shadow: 0 0 0 0 rgba(251, 191, 36, 0);
    transform: scale(1.1);
  }
  50% {
    background: rgba(251, 191, 36, 0.7);
    box-shadow: 0 0 12px 4px rgba(251, 191, 36, 0.5);
  }
  100% {
    background: rgba(251, 191, 36, 0.4);
    box-shadow: 0 0 0 2px rgba(251, 191, 36, 0.3);
    transform: scale(1);
  }
}

@keyframes highlight-leave {
  0% {
    background: rgba(251, 191, 36, 0.4);
    box-shadow: 0 0 0 2px rgba(251, 191, 36, 0.3);
    opacity: 1;
  }
  100% {
    background: rgba(251, 191, 36, 0);
    box-shadow: 0 0 0 0 rgba(251, 191, 36, 0);
    opacity: 0;
  }
}

/* Anotaciones de gramática y ortografía */
.chapter-text :deep(.annotation) {
  position: relative;
  cursor: help;
  border-bottom: 2px wavy;
}

.chapter-text :deep(.annotation.grammar-error) {
  border-color: var(--blue-500);
  background: rgba(59, 130, 246, 0.08);
}

.chapter-text :deep(.annotation.spelling-error) {
  border-color: var(--red-500);
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

.chapter-text :deep(.annotation:hover) {
  background: rgba(251, 191, 36, 0.2);
}

/* Toggle de anotaciones activo */
.annotation-toggle-active {
  color: var(--primary-color) !important;
}

/* Toggle de errores de ortografia activo */
.spelling-toggle-active {
  color: var(--red-500) !important;
  border-color: var(--red-500) !important;
}

/* Toggle de errores de gramatica activo */
.grammar-toggle-active {
  color: var(--blue-500) !important;
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
  border-radius: 2px;
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
  border-bottom: 2px solid var(--red-500);
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
  text-decoration-color: var(--red-500);
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
  border-radius: 8px;
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
  border-radius: 8px;
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

<!-- Estilos globales para highlight dinámico (insertado via JS, no funciona con scoped) -->
<style>
/* Highlight temporal para navegación a alertas/menciones */
.mention-highlight-active {
  background: rgba(251, 191, 36, 0.6) !important;
  border-radius: 3px;
  box-shadow: 0 0 0 3px rgba(251, 191, 36, 0.4);
  animation: mention-highlight-pulse 1.5s ease-in-out infinite;
  padding: 2px 4px;
  margin: -2px -4px;
}

.mention-highlight-active.highlight-entering {
  animation: mention-highlight-enter 0.5s ease-out forwards;
}

.mention-highlight-active.highlight-leaving {
  animation: mention-highlight-leave 0.4s ease-out forwards;
}

@keyframes mention-highlight-pulse {
  0%, 100% {
    background: rgba(251, 191, 36, 0.5);
    box-shadow: 0 0 0 2px rgba(251, 191, 36, 0.3);
  }
  50% {
    background: rgba(251, 191, 36, 0.7);
    box-shadow: 0 0 12px 4px rgba(251, 191, 36, 0.5);
  }
}

@keyframes mention-highlight-enter {
  0% {
    background: rgba(251, 191, 36, 0);
    box-shadow: 0 0 0 0 rgba(251, 191, 36, 0);
    transform: scale(1.2);
  }
  100% {
    background: rgba(251, 191, 36, 0.6);
    box-shadow: 0 0 0 3px rgba(251, 191, 36, 0.4);
    transform: scale(1);
  }
}

@keyframes mention-highlight-leave {
  0% {
    background: rgba(251, 191, 36, 0.6);
    box-shadow: 0 0 0 3px rgba(251, 191, 36, 0.4);
    opacity: 1;
  }
  100% {
    background: rgba(251, 191, 36, 0);
    box-shadow: 0 0 0 0 rgba(251, 191, 36, 0);
    opacity: 0;
  }
}
</style>
