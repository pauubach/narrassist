<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import DocumentViewer from '@/components/DocumentViewer.vue'
import { useWorkspaceStore } from '@/stores/workspace'
import type { Alert, Chapter } from '@/types'

const workspaceStore = useWorkspaceStore()

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
const gutterMarkers = computed(() => {
  const markers: Array<{
    id: number
    top: number // porcentaje
    severity: string
    count: number
    alerts: Alert[]
  }> = []

  if (props.chapters.length === 0) return markers

  // Calcular posición de cada capítulo como porcentaje del documento total
  const totalChapters = props.chapters.length
  props.chapters.forEach((chapter, index) => {
    const chapterAlerts = alertsByChapter.value.get(chapter.chapterNumber) || []
    if (chapterAlerts.length > 0) {
      // Posición vertical como porcentaje
      const top = (index / totalChapters) * 100

      // Severidad más alta
      const severities = ['critical', 'high', 'medium', 'low', 'info']
      const highestSeverity = chapterAlerts.reduce((highest, alert) => {
        const currentIdx = severities.indexOf(alert.severity)
        const highestIdx = severities.indexOf(highest)
        return currentIdx < highestIdx ? alert.severity : highest
      }, 'info')

      markers.push({
        id: chapter.id,
        top,
        severity: highestSeverity,
        count: chapterAlerts.length,
        alerts: chapterAlerts
      })
    }
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

function handleGutterMarkerClick(marker: typeof gutterMarkers.value[0]) {
  // Emitir la primera alerta del grupo para navegación
  if (marker.alerts.length > 0) {
    emit('alert-click', marker.alerts[0])
  }
}

// Colores de severidad para el gutter
function getSeverityColor(severity: string): string {
  const colors: Record<string, string> = {
    critical: 'var(--red-500)',
    high: 'var(--orange-500)',
    medium: 'var(--yellow-500)',
    low: 'var(--blue-500)',
    info: 'var(--gray-400)'
  }
  return colors[severity] || colors.info
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

// onMounted: procesar scroll pendiente si el componente se monta después de setear la posición
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
  <div class="text-tab">
    <!-- Gutter con marcadores de alertas -->
    <div
      v-if="showGutter"
      class="alert-gutter"
      :style="{ width: gutterWidth + 'px' }"
    >
      <div
        v-for="marker in gutterMarkers"
        :key="marker.id"
        class="gutter-marker"
        :style="{
          top: marker.top + '%',
          backgroundColor: getSeverityColor(marker.severity)
        }"
        :title="`${marker.count} alerta(s) en este capítulo`"
        @click="handleGutterMarkerClick(marker)"
      >
        <span v-if="marker.count > 1" class="marker-count">{{ marker.count }}</span>
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
}

/* Gutter lateral */
.alert-gutter {
  position: relative;
  background: var(--surface-100);
  border-right: 1px solid var(--surface-border);
  flex-shrink: 0;
}

.gutter-marker {
  position: absolute;
  left: 4px;
  right: 4px;
  height: 8px;
  border-radius: 2px;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.gutter-marker:hover {
  transform: scaleY(1.5);
  box-shadow: 0 0 4px currentColor;
}

.marker-count {
  font-size: 0.625rem;
  font-weight: 700;
  color: white;
  text-shadow: 0 0 2px rgba(0, 0, 0, 0.5);
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
