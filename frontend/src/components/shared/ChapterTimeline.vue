<template>
  <div class="chapter-timeline" :class="{ compact, vertical }">
    <!-- Header -->
    <div v-if="showHeader" class="timeline-header">
      <span class="timeline-title">{{ title }}</span>
      <span v-if="showCount" class="chapter-count">{{ chapters.length }} capítulos</span>
    </div>

    <!-- Timeline track -->
    <div class="timeline-track" ref="trackRef">
      <div
        v-for="chapter in chaptersWithHighlights"
        :key="chapter.number"
        :class="[
          'chapter-block',
          {
            selected: chapter.number === selectedChapter,
            hasHighlight: chapter.highlight !== null,
          }
        ]"
        :style="getChapterStyle(chapter)"
        @click="$emit('select', chapter.number)"
        @mouseenter="hoveredChapter = chapter.number"
        @mouseleave="hoveredChapter = null"
        v-tooltip.top="getTooltip(chapter)"
      >
        <span v-if="!compact" class="chapter-label">{{ chapter.number }}</span>
        <div
          v-if="chapter.highlight"
          class="chapter-highlight"
          :style="getHighlightStyle(chapter.highlight)"
        ></div>
      </div>
    </div>

    <!-- Legend -->
    <div v-if="showLegend && legend.length > 0" class="timeline-legend">
      <div
        v-for="item in legend"
        :key="item.label"
        class="legend-item"
      >
        <span class="legend-dot" :style="{ backgroundColor: item.color }"></span>
        <span class="legend-label">{{ item.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface Chapter {
  id: number
  number: number
  title?: string
}

interface Highlight {
  chapter: number
  color: string
  intensity: number  // 0-1
  label?: string
}

interface LegendItem {
  label: string
  color: string
}

interface Props {
  chapters: Chapter[]
  highlights?: Highlight[]
  selectedChapter?: number
  title?: string
  showHeader?: boolean
  showCount?: boolean
  showLegend?: boolean
  legend?: LegendItem[]
  compact?: boolean
  vertical?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  highlights: () => [],
  title: 'Capítulos',
  showHeader: false,
  showCount: true,
  showLegend: false,
  legend: () => [],
  compact: false,
  vertical: false,
})

defineEmits<{
  select: [chapterNumber: number]
}>()

const trackRef = ref<HTMLElement | null>(null)
const hoveredChapter = ref<number | null>(null)

// Build chapters with their highlights
const chaptersWithHighlights = computed(() => {
  const highlightMap = new Map<number, Highlight>()

  for (const h of props.highlights) {
    highlightMap.set(h.chapter, h)
  }

  return props.chapters.map(ch => ({
    ...ch,
    highlight: highlightMap.get(ch.number) || null,
  }))
})

// Style for chapter block
const getChapterStyle = (chapter: { number: number; highlight: Highlight | null }) => {
  const style: Record<string, string> = {}

  // If selected, add primary border
  if (chapter.number === props.selectedChapter) {
    style.borderColor = 'var(--ds-color-primary)'
    style.borderWidth = '2px'
  }

  return style
}

// Style for highlight overlay
const getHighlightStyle = (highlight: Highlight) => {
  const opacity = Math.min(1, Math.max(0.1, highlight.intensity))
  return {
    backgroundColor: highlight.color,
    opacity: opacity.toString(),
  }
}

// Tooltip content
const getTooltip = (chapter: { number: number; title?: string; highlight: Highlight | null }) => {
  const parts: string[] = []

  if (chapter.title) {
    parts.push(chapter.title)
  } else {
    parts.push(`Capítulo ${chapter.number}`)
  }

  if (chapter.highlight?.label) {
    parts.push(chapter.highlight.label)
  }

  return parts.join(' - ')
}
</script>

<style scoped>
.chapter-timeline {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.chapter-timeline.vertical {
  flex-direction: row;
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.timeline-title {
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-medium);
  color: var(--ds-color-text);
}

.chapter-count {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.timeline-track {
  display: flex;
  gap: 2px;
  overflow-x: auto;
  padding: var(--ds-space-1) 0;
}

.chapter-timeline.vertical .timeline-track {
  flex-direction: column;
  overflow-x: visible;
  overflow-y: auto;
}

.chapter-block {
  position: relative;
  min-width: 28px;
  height: 28px;
  background: var(--ds-surface-hover);
  border: 1px solid var(--ds-surface-border);
  border-radius: var(--ds-radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
  overflow: hidden;
}

.chapter-timeline.compact .chapter-block {
  min-width: 16px;
  height: 16px;
  border-radius: 2px;
}

.chapter-block:hover {
  transform: scale(1.1);
  z-index: 1;
  border-color: var(--ds-color-primary);
}

.chapter-block.selected {
  background: var(--ds-color-primary-soft);
  border-color: var(--ds-color-primary);
}

.chapter-block.hasHighlight {
  border-color: transparent;
}

.chapter-label {
  font-size: var(--ds-font-size-xs);
  font-weight: var(--ds-font-weight-medium);
  color: var(--ds-color-text-secondary);
  z-index: 1;
}

.chapter-block.selected .chapter-label {
  color: var(--ds-color-primary);
}

.chapter-highlight {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
}

.timeline-legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-3);
  padding-top: var(--ds-space-2);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.legend-label {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}
</style>
