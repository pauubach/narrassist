<template>
  <div class="document-viewer" ref="viewerContainer">
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
        <Button
          icon="pi pi-search-minus"
          text
          rounded
          @click="decreaseZoom"
          :disabled="zoomLevel <= 0.8"
          v-tooltip.bottom="'Reducir zoom'"
        />
        <span class="zoom-level">{{ Math.round(zoomLevel * 100) }}%</span>
        <Button
          icon="pi pi-search-plus"
          text
          rounded
          @click="increaseZoom"
          :disabled="zoomLevel >= 1.5"
          v-tooltip.bottom="'Aumentar zoom'"
        />
        <Divider layout="vertical" />
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
    <div class="viewer-content" :style="{ transform: `scale(${zoomLevel})`, transformOrigin: 'top center' }" @scroll="onScroll">
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
          <i class="pi pi-file"></i>
          <p>No hay contenido disponible</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import Button from 'primevue/button'
import Divider from 'primevue/divider'
import ProgressSpinner from 'primevue/progressspinner'

// Referencias a elementos de capítulos para intersection observer
const chapterRefs = new Map<number, Element>()
let intersectionObserver: IntersectionObserver | null = null

interface Chapter {
  id: number
  project_id: number
  title: string
  content: string
  chapter_number: number
  word_count: number
  position_start: number
  position_end: number
  created_at: string
  updated_at: string
}

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

const props = defineProps<{
  projectId: number
  documentTitle?: string
  highlightEntityId?: number | null
  scrollToChapterId?: number | null
}>()

const emit = defineEmits<{
  chapterVisible: [chapterId: number]
  entityClick: [entityId: number]
}>()

// Estado
const viewerContainer = ref<HTMLElement | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const zoomLevel = ref(1.0)
const chapters = ref<Chapter[]>([])
const entities = ref<Entity[]>([])
// TODO: entityMentions se usará cuando se implemente el endpoint de menciones
const _entityMentions = ref<EntityMention[]>([])

// Estado para lazy loading
const visibleChapters = ref<Set<number>>(new Set())
const loadedChapters = ref<Set<number>>(new Set())

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
}

// Computed para el estilo del contenido
const contentStyle = computed(() => ({
  fontSize: fontSizeMap[fontSize.value] || '1rem',
  lineHeight: lineHeight.value
}))

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
            // Marcar como cargado cuando entra en vista
            loadedChapters.value.add(chapterId)
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
  return chapters.value.reduce((sum, ch) => sum + ch.word_count, 0)
})

// Funciones de zoom
const increaseZoom = () => {
  if (zoomLevel.value < 1.5) {
    zoomLevel.value = Math.min(1.5, zoomLevel.value + 0.1)
  }
}

const decreaseZoom = () => {
  if (zoomLevel.value > 0.8) {
    zoomLevel.value = Math.max(0.8, zoomLevel.value - 0.1)
  }
}

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

    // Cargar capítulos (metadatos, el contenido se carga lazy)
    const chaptersResponse = await fetch(`${API_BASE}/api/projects/${props.projectId}/chapters`)
    const chaptersData = await chaptersResponse.json()

    if (!chaptersData.success) {
      throw new Error('Error cargando capítulos')
    }

    chapters.value = chaptersData.data || []

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

// Eliminar título duplicado del contenido si existe
const removeLeadingTitle = (content: string, title: string): string => {
  if (!content || !title) return content

  // Extraer primera línea del contenido
  const firstNewline = content.indexOf('\n')
  if (firstNewline === -1) return content

  const firstLine = content.substring(0, firstNewline).trim()

  // Si la primera línea es muy larga, probablemente no es un título
  if (firstLine.length > 100) return content

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
    // Eliminar primera línea y espacios en blanco siguientes
    return content.substring(firstNewline).replace(/^\n+/, '')
  }

  return content
}

// Resaltar entidades en el contenido
const getHighlightedContent = (chapter: Chapter): string => {
  if (!chapter.content) return ''

  // Primero remover el título si está duplicado al inicio del contenido
  const contentWithoutTitle = removeLeadingTitle(chapter.content, chapter.title)
  let content = escapeHtml(contentWithoutTitle)

  // Si hay una entidad seleccionada para resaltar
  if (props.highlightEntityId) {
    const entity = entities.value.find(e => e.id === props.highlightEntityId)
    if (entity) {
      // Resaltar todas las menciones de esta entidad
      const regex = new RegExp(`\\b${escapeRegex(entity.name)}\\b`, 'gi')
      content = content.replace(
        regex,
        `<mark class="entity-highlight entity-highlight-active" data-entity-id="${entity.id}">$&</mark>`
      )
    }
  }

  // Resaltar todas las entidades (con estilo más sutil)
  entities.value.forEach(entity => {
    if (entity.id !== props.highlightEntityId && entity.name) {
      const regex = new RegExp(`\\b${escapeRegex(entity.name)}\\b`, 'gi')
      content = content.replace(
        regex,
        `<mark class="entity-highlight entity-${entity.entity_type.toLowerCase()}" data-entity-id="${entity.id}" onclick="window.handleEntityClick(${entity.id})">$&</mark>`
      )
    }
  })

  // Convertir saltos de línea en párrafos
  return content
    .split('\n\n')
    .map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`)
    .join('')
}

// Helpers
const escapeHtml = (text: string): string => {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

const escapeRegex = (text: string): string => {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

// Scroll a capítulo específico
const scrollToChapter = (chapterId: number) => {
  nextTick(() => {
    const element = viewerContainer.value?.querySelector(`[data-chapter-id="${chapterId}"]`)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  })
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

// Exportar documento
const exportDocument = () => {
  // TODO: Implementar exportación a DOCX/PDF
  console.log('Export document')
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

watch(() => props.projectId, () => {
  loadDocument()
})

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
  loadDocument
})
</script>

<style scoped>
.document-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.viewer-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: var(--surface-50);
  border-bottom: 1px solid var(--surface-200);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.viewer-title {
  font-weight: 600;
  font-size: 1rem;
  color: var(--text-color);
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

.zoom-level {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
  min-width: 3rem;
  text-align: center;
}

.viewer-content {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
  background: white;
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
  max-width: 900px;
  margin: 0 auto;
  line-height: 1.8;
  color: var(--text-color);
}

.chapter-section {
  margin-bottom: 3rem;
}

.chapter-title {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-color);
  margin-bottom: 1.5rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid var(--primary-color);
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
</style>
