<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import DocumentViewer from '@/components/DocumentViewer.vue'
import TextFindBar from '@/components/workspace/TextFindBar.vue'
import { useWorkspaceStore } from '@/stores/workspace'
import { META_CATEGORIES, type MetaCategoryKey } from '@/composables/useAlertUtils'
import type { Alert, Chapter, DialogueAttribution } from '@/types'

const workspaceStore = useWorkspaceStore()

// Find bar state
const textTabContainer = ref<HTMLElement | null>(null)
const showFindBar = ref(false)
const findBarRef = ref<InstanceType<typeof TextFindBar> | null>(null)
const documentViewerRef = ref<InstanceType<typeof DocumentViewer> | null>(null)

function openFindBar() {
  if (showFindBar.value) {
    // Already open — just re-focus
    findBarRef.value?.focusInput()
  } else {
    showFindBar.value = true
  }
}

function scrollToDialogue(attribution: DialogueAttribution) {
  const chapter = props.chapters.find(ch => ch.chapterNumber === attribution.chapterNumber)
  if (!chapter) return
  documentViewerRef.value?.scrollToMention({
    chapterId: chapter.id,
    position: attribution.startChar,
    text: attribution.text,
  })
}

defineExpose({ openFindBar, scrollToDialogue })

/**
 * TextTab - Pestaña principal de visualización de texto
 *
 * Envuelve el DocumentViewer y añade:
 * - Gutter lateral con marcadores de alertas
 * - Navegación a alertas desde el gutter
 * - Integración con selección global
 */

interface ScrollTarget {
  chapterId: number
  position?: number  // Posición de caracteres dentro del capítulo (para desambiguar)
  text?: string      // Texto a resaltar
}

interface AlertHighlightRange {
  startChar: number
  endChar: number
  text?: string
  chapterId?: number | null
  color?: string
  label?: string
}

interface Props {
  /** ID del proyecto */
  projectId: number
  /** Título del documento */
  documentTitle: string
  /** Alertas del proyecto para mostrar en gutter */
  alerts: Alert[]
  /** Capítulos del proyecto */
  chapters: Chapter[]
  /** ID de entidad a resaltar */
  highlightEntityId?: number | null
  /** ID de capítulo al que hacer scroll */
  scrollToChapterId?: number | null
  /** Posición de carácter al que hacer scroll */
  scrollToPosition?: number | null
  /** Rangos múltiples a resaltar (para alertas de inconsistencia) */
  alertHighlightRanges?: AlertHighlightRange[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'chapter-visible': [chapterId: number]
  'entity-click': [entityId: number]
  'alert-click': [alert: Alert]
}>()

// Gutter state - only show if there are alerts to display
const gutterWidth = ref(20)
const showGutter = computed(() => gutterMarkers.value.length > 0)

// Helper: encontrar el capítulo que contiene una posición de carácter
function findChapterForPosition(position: number): number | undefined {
  for (const chapter of props.chapters) {
    if (position >= chapter.positionStart && position <= chapter.positionEnd) {
      return chapter.chapterNumber
    }
  }
  return undefined
}

// Computed: alertas agrupadas por capítulo para el gutter
const alertsByChapter = computed(() => {
  const grouped = new Map<number, Alert[]>()
  let withoutChapter = 0
  let inferred = 0

  for (const alert of props.alerts) {
    let chapterNum = alert.chapter

    // Si no tiene chapter pero tiene spanStart, inferir el capítulo
    if ((chapterNum === undefined || chapterNum === null) && alert.spanStart !== undefined) {
      chapterNum = findChapterForPosition(alert.spanStart)
      if (chapterNum !== undefined) {
        inferred++
        console.log(`[TextTab] Capítulo inferido para "${alert.title}": cap ${chapterNum} (spanStart=${alert.spanStart})`)
      }
    }

    if (chapterNum !== undefined) {
      const list = grouped.get(chapterNum) || []
      list.push(alert)
      grouped.set(chapterNum, list)
    } else {
      withoutChapter++
      console.warn(`[TextTab] Alert sin capítulo ni posición:`, alert.title, alert)
    }
  }

  console.log(`[TextTab] Total alerts: ${props.alerts.length}, inferidos: ${inferred}, sin capítulo: ${withoutChapter}, agrupadas: ${Array.from(grouped.entries()).map(([ch, alerts]) => `cap${ch}=${alerts.length}`).join(', ')}`)
  return grouped
})

// Computed: posiciones relativas de alertas para el gutter
function computeGutterMarkers() {
  const markers: Array<{
    id: number
    chapterIndex: number
    topPercent: number
    badges: Array<{
      metaCategory: MetaCategoryKey
      count: number
      color: string
      label: string
      alerts: Alert[]
    }>
  }> = []

  if (props.chapters.length === 0) {
    return markers
  }

  const totalChapters = props.chapters.length

  // Para cada capítulo, agrupar alertas por meta-categoría
  props.chapters.forEach((chapter, index) => {
    const chapterAlerts = alertsByChapter.value.get(chapter.chapterNumber) || []
    if (chapterAlerts.length === 0) return

    // Agrupar por meta-categoría
    const byMetaCategory = new Map<MetaCategoryKey, Alert[]>()

    for (const alert of chapterAlerts) {
      // Skip si no tiene categoría
      if (!alert.category) {
        console.warn(`[TextTab] Alert ${alert.id} sin categoría:`, alert.title)
        continue
      }

      // Encontrar la meta-categoría de esta alerta
      let metaKey: MetaCategoryKey | null = null
      for (const [key, metaConfig] of Object.entries(META_CATEGORIES)) {
        const meta = metaConfig as typeof META_CATEGORIES[MetaCategoryKey]
        if (meta.categories.includes(alert.category as never)) {
          metaKey = key as MetaCategoryKey
          console.log(`[TextTab] Alert "${alert.title}" (${alert.category}) → meta: ${metaKey}`)
          break
        }
      }

      // Fallback a 'suggestions' si no encontró meta-categoría
      if (!metaKey) {
        console.warn(`[TextTab] Alert "${alert.title}" category="${alert.category}" no mapeó a ninguna meta-categoría, fallback a suggestions`)
        metaKey = 'suggestions'
      }

      const list = byMetaCategory.get(metaKey) || []
      list.push(alert)
      byMetaCategory.set(metaKey, list)
    }

    // Crear badges ordenados por prioridad (errors, inconsistencies, quality, suggestions)
    const badges = []
    const order: MetaCategoryKey[] = ['errors', 'inconsistencies', 'quality', 'suggestions']

    for (const metaKey of order) {
      const alertsList = byMetaCategory.get(metaKey)
      if (!alertsList || alertsList.length === 0) continue

      const meta = META_CATEGORIES[metaKey]
      if (!meta) {
        console.warn(`[TextTab] No meta-category config for key: ${metaKey}`)
        continue
      }

      const count = alertsList.length
      if (typeof count !== 'number' || isNaN(count)) {
        console.error(`[TextTab] Invalid count for ${metaKey}:`, count, alertsList)
        continue
      }

      badges.push({
        metaCategory: metaKey,
        count,
        color: meta.color,
        label: meta.label,
        alerts: alertsList
      })
    }

    if (badges.length > 0) {
      // Calcular posición vertical como porcentaje del documento total
      const topPercent = (index / totalChapters) * 100

      console.log(`[TextTab] Cap ${index} (${chapter.chapterNumber}) badges:`, badges.map(b => `${b.metaCategory}=${b.count}`).join(', '), `topPercent=${topPercent}%`)

      markers.push({
        id: chapter.id,
        chapterIndex: index,
        topPercent,
        badges
      })
    }
  })

  console.log(`[TextTab] Total markers creados: ${markers.length}`)
  return markers
}

const gutterMarkers = computed(() => {
  return computeGutterMarkers()
})

// Computed: convertir gutterMarkers a Map<chapterId, badges[]> para DocumentViewer
const chapterBadgesMap = computed(() => {
  const map = new Map()
  for (const marker of gutterMarkers.value) {
    map.set(marker.id, marker.badges)
  }
  return map
})

// Handlers
function handleChapterVisible(chapterId: number) {
  emit('chapter-visible', chapterId)
}

function handleEntityClick(entityId: number) {
  emit('entity-click', entityId)
}

function handleBadgeClick(badge: typeof gutterMarkers.value[0]['badges'][0]) {
  // Emitir la primera alerta del badge para navegación
  if (badge.alerts.length > 0) {
    emit('alert-click', badge.alerts[0])
  }
}

// Computed: scroll target basado en posición de carácter y/o chapterId
const scrollTarget = computed((): ScrollTarget | null => {
  if (props.scrollToPosition === null || props.scrollToPosition === undefined) {
    return null
  }

  // Obtener el texto a resaltar y chapterId del store
  const textToHighlight = workspaceStore.scrollToText
  const directChapterId = workspaceStore.scrollToChapterId

  // Si tenemos un chapterId directo (navegación desde menciones), usarlo
  if (directChapterId !== null) {
    // La posición del backend es GLOBAL (relativa a full_text), hay que convertirla
    // a posición relativa al capítulo para que highlightTextInChapter la use correctamente
    const chapter = props.chapters.find(ch => ch.id === directChapterId)
    const localPosition = chapter
      ? props.scrollToPosition - chapter.positionStart
      : props.scrollToPosition

    return {
      chapterId: directChapterId,
      position: localPosition,
      text: textToHighlight || undefined,
    }
  }

  // Si no tenemos chapterId, buscar el capítulo por posición global
  for (const chapter of props.chapters) {
    if (props.scrollToPosition >= chapter.positionStart &&
        props.scrollToPosition <= chapter.positionEnd) {
      return {
        chapterId: chapter.id,
        // Pasar la posición relativa al capítulo para identificar la ocurrencia correcta
        position: props.scrollToPosition - chapter.positionStart,
        text: textToHighlight || undefined,
      }
    }
  }

  // Si no se encuentra, usar el primer capítulo
  if (props.chapters.length > 0) {
    return {
      chapterId: props.chapters[0].id,
      position: props.scrollToPosition,
      text: textToHighlight || undefined,
    }
  }

  return null
})

// Watch: limpiar scrollToPosition del store después de consumirlo
// Solo limpiar cuando el target realmente existe y ha sido procesado
watch(scrollTarget, (target) => {
  if (target !== null) {
    // Esperar a que el DOM se actualice y el DocumentViewer procese el scroll
    // DocumentViewer puede necesitar hasta 200ms + 3 retries de 150ms = 650ms
    // Usamos 800ms para dar margen adicional
    nextTick(() => {
      setTimeout(() => {
        workspaceStore.clearScrollToPosition()
      }, 800)
    })
  }
})

// onMounted: procesar scroll pendiente
onMounted(async () => {
  // Esperar al siguiente tick para asegurar que las props están actualizadas
  await nextTick()

  // Si hay una posición pendiente cuando el componente se monta, el computed scrollTarget
  // ya la habrá detectado. Solo necesitamos asegurar que se procese.
  if (workspaceStore.scrollToPosition !== null) {
    console.log('[TextTab] Scroll pendiente detectado al montar:', workspaceStore.scrollToPosition)
  }
})
</script>

<template>
  <div ref="textTabContainer" class="text-tab">
    <!-- Find bar -->
    <TextFindBar
      ref="findBarRef"
      :visible="showFindBar"
      :container="textTabContainer"
      @close="showFindBar = false"
    />

    <!-- Document Viewer -->
    <div class="document-area">
      <DocumentViewer
        ref="documentViewerRef"
        :project-id="projectId"
        :document-title="documentTitle"
        :highlight-entity-id="highlightEntityId"
        :scroll-to-chapter-id="scrollToChapterId"
        :scroll-to-target="scrollTarget"
        :external-chapters="chapters"
        :alert-highlight-ranges="alertHighlightRanges"
        :chapter-badges="chapterBadgesMap"
        @chapter-visible="handleChapterVisible"
        @entity-click="handleEntityClick"
      />
    </div>
  </div>
</template>

<style scoped>
.text-tab {
  display: flex;
  height: 100%;
  position: relative;
  overflow: hidden;
}

/* Document area */
.document-area {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}
</style>
