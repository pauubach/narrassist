<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import DocumentViewer from '@/components/DocumentViewer.vue'
import TextFindBar from '@/components/workspace/TextFindBar.vue'
import { useWorkspaceStore } from '@/stores/workspace'
import { META_CATEGORIES, type MetaCategoryKey } from '@/composables/useAlertUtils'
import type { Alert, Chapter } from '@/types'

const workspaceStore = useWorkspaceStore()

// Find bar state
const textTabContainer = ref<HTMLElement | null>(null)
const showFindBar = ref(false)
const findBarRef = ref<InstanceType<typeof TextFindBar> | null>(null)

function openFindBar() {
  if (showFindBar.value) {
    // Already open — just re-focus
    findBarRef.value?.focusInput()
  } else {
    showFindBar.value = true
  }
}

defineExpose({ openFindBar })

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

// Computed: alertas agrupadas por capítulo para el gutter
const alertsByChapter = computed(() => {
  const grouped = new Map<number, Alert[]>()
  for (const alert of props.alerts) {
    if (alert.chapter !== undefined) {
      const list = grouped.get(alert.chapter) || []
      list.push(alert)
      grouped.set(alert.chapter, list)
    }
  }
  return grouped
})

// Computed: posiciones relativas de alertas para el gutter
// Memoización de gutterMarkers con hash (performance optimization #6)
const gutterMarkersCache = ref<{ hash: string; value: any[] } | null>(null)

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
      if (!alert.category) continue

      // Encontrar la meta-categoría de esta alerta
      let metaKey: MetaCategoryKey | null = null
      for (const [key, metaConfig] of Object.entries(META_CATEGORIES)) {
        const meta = metaConfig as typeof META_CATEGORIES[MetaCategoryKey]
        if (meta.categories.includes(alert.category as never)) {
          metaKey = key as MetaCategoryKey
          break
        }
      }

      // Fallback a 'suggestions' si no encontró meta-categoría
      if (!metaKey) {
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
      const alerts = byMetaCategory.get(metaKey)
      if (alerts && alerts.length > 0) {
        const meta = META_CATEGORIES[metaKey]
        badges.push({
          metaCategory: metaKey,
          count: alerts.length,
          color: meta.color,
          label: meta.label,
          alerts
        })
      }
    }

    if (badges.length > 0) {
      // Calcular posición vertical como porcentaje del documento total
      const topPercent = (index / totalChapters) * 100

      markers.push({
        id: chapter.id,
        chapterIndex: index,
        topPercent,
        badges
      })
    }
  })

  return markers
}

const gutterMarkers = computed(() => {
  // Hash basado en chapters length y alerts length
  const hash = `${props.chapters.length}-${props.alerts.length}`

  if (gutterMarkersCache.value?.hash === hash) {
    return gutterMarkersCache.value.value
  }

  const markers = computeGutterMarkers()
  // Side effect en nextTick para no violar regla de computed
  nextTick(() => {
    gutterMarkersCache.value = { hash, value: markers }
  })
  return markers
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

    <!-- Gutter con badges de alertas por meta-categoría -->
    <div
      v-if="showGutter"
      class="alert-gutter"
    >
      <div
        v-for="marker in gutterMarkers"
        :key="marker.id"
        class="chapter-badges"
        :style="{ top: marker.topPercent + '%' }"
        :data-chapter-index="marker.chapterIndex"
      >
        <button
          v-for="badge in marker.badges"
          :key="badge.metaCategory"
          class="alert-badge"
          :style="{ backgroundColor: badge.color }"
          :title="`${badge.count} ${badge.label.toLowerCase()}`"
          @click="handleBadgeClick(badge)"
        >
          <span class="badge-count">{{ badge.count }}</span>
        </button>
      </div>
    </div>

    <!-- Document Viewer -->
    <div class="document-area">
      <DocumentViewer
        :project-id="projectId"
        :document-title="documentTitle"
        :highlight-entity-id="highlightEntityId"
        :scroll-to-chapter-id="scrollToChapterId"
        :scroll-to-target="scrollTarget"
        :external-chapters="chapters"
        :alert-highlight-ranges="alertHighlightRanges"
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

/* Gutter lateral con badges por meta-categoría */
.alert-gutter {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 60px;
  z-index: 1;
  pointer-events: none;
}

.chapter-badges {
  position: absolute;
  left: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  pointer-events: all;
  /* top se establece dinámicamente via JS */
}

.alert-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 24px;
  border-radius: 12px;
  border: none;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.alert-badge:hover {
  transform: scale(1.05);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
}

.badge-count {
  font-size: 0.75rem;
  font-weight: 600;
  color: white;
  text-shadow: 0 0 2px rgba(0, 0, 0, 0.3);
}

/* Document area */
.document-area {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

/* Dark mode */
.dark .alert-gutter {
  background: var(--surface-800);
}
</style>
