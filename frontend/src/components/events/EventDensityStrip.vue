<template>
  <div class="event-density-container">
    <div class="density-header">
      <span class="header-label">Densidad de Eventos por Capítulo</span>
      <div class="legend">
        <span class="legend-item">
          <span class="dot tier1"></span>
          Tier 1
        </span>
        <span class="legend-item">
          <span class="dot tier2"></span>
          Tier 2
        </span>
        <span class="legend-item">
          <span class="dot tier3"></span>
          Tier 3
        </span>
      </div>
    </div>

    <svg
      ref="svgRef"
      class="density-strip"
      :width="width"
      :height="height"
      @mousemove="handleMouseMove"
      @mouseleave="tooltip = null"
    >
      <!-- Barras de densidad -->
      <g
        v-for="(ch, idx) in densityData"
        :key="ch.chapter"
        :transform="`translate(${idx * barWidth}, 0)`"
      >
        <!-- Tier 1 (abajo, rojo) -->
        <rect
          v-if="ch.tier1 > 0"
          :width="barWidth - 2"
          :height="getTierHeight(ch.tier1)"
          :y="height - getTierHeight(ch.tier1)"
          class="tier1-bar"
          @click="emit('navigate-to-chapter', ch.chapter)"
        />

        <!-- Tier 2 (medio, amarillo) -->
        <rect
          v-if="ch.tier2 > 0"
          :width="barWidth - 2"
          :height="getTierHeight(ch.tier2)"
          :y="height - getTierHeight(ch.tier1) - getTierHeight(ch.tier2)"
          class="tier2-bar"
          @click="emit('navigate-to-chapter', ch.chapter)"
        />

        <!-- Tier 3 (arriba, azul) -->
        <rect
          v-if="ch.tier3 > 0"
          :width="barWidth - 2"
          :height="getTierHeight(ch.tier3)"
          :y="
            height - getTierHeight(ch.tier1) - getTierHeight(ch.tier2) - getTierHeight(ch.tier3)
          "
          class="tier3-bar"
          @click="emit('navigate-to-chapter', ch.chapter)"
        />

        <!-- Marcador de capítulo vacío -->
        <rect
          v-if="ch.total === 0"
          :width="barWidth - 2"
          :height="height"
          y="0"
          class="empty-chapter"
          @click="emit('navigate-to-chapter', ch.chapter)"
        />

        <!-- Indicador de capítulo actual -->
        <rect
          v-if="ch.chapter === currentChapter"
          :width="barWidth - 2"
          :height="4"
          :y="height - 2"
          class="current-indicator"
        />
      </g>

      <!-- Etiquetas de capítulo (cada 5) -->
      <text
        v-for="ch in labeledChapters"
        :key="`label-${ch.chapter}`"
        :x="getChapterIndex(ch.chapter) * barWidth + barWidth / 2"
        :y="height + 15"
        class="chapter-label"
      >
        {{ ch.chapter }}
      </text>
    </svg>

    <!-- Tooltip -->
    <div
      v-if="tooltip"
      class="density-tooltip"
      :style="{ left: `${tooltip.x}px`, top: `${tooltip.y}px` }"
    >
      <div class="tooltip-header">Capítulo {{ tooltip.chapter }}</div>
      <div class="tooltip-row">
        <span>Total:</span>
        <strong>{{ tooltip.total }}</strong>
      </div>
      <div class="tooltip-row tier1">
        <span>Tier 1:</span>
        <strong>{{ tooltip.tier1 }}</strong>
      </div>
      <div class="tooltip-row tier2">
        <span>Tier 2:</span>
        <strong>{{ tooltip.tier2 }}</strong>
      </div>
      <div class="tooltip-row tier3">
        <span>Tier 3:</span>
        <strong>{{ tooltip.tier3 }}</strong>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface ChapterDensity {
  chapter: number
  tier1: number
  tier2: number
  tier3: number
  total: number
}

const props = withDefaults(
  defineProps<{
    densityData: ChapterDensity[]
    currentChapter?: number
    width?: number
    height?: number
  }>(),
  {
    width: 800,
    height: 60
  }
)

const emit = defineEmits<{
  'navigate-to-chapter': [number]
}>()

const barWidth = computed(() => props.width / props.densityData.length)
const maxEvents = computed(() => Math.max(...props.densityData.map((ch) => ch.total), 1))

const labeledChapters = computed(() => {
  return props.densityData.filter((ch, idx) => idx % 5 === 0)
})

const svgRef = ref<SVGElement | null>(null)
const tooltip = ref<{
  x: number
  y: number
  chapter: number
  tier1: number
  tier2: number
  tier3: number
  total: number
} | null>(null)

function getTierHeight(count: number): number {
  return (count / maxEvents.value) * props.height
}

function getChapterIndex(chapterNumber: number): number {
  return props.densityData.findIndex((ch) => ch.chapter === chapterNumber)
}

function handleMouseMove(event: MouseEvent) {
  if (!svgRef.value) return

  const rect = svgRef.value.getBoundingClientRect()
  const x = event.clientX - rect.left
  const idx = Math.floor(x / barWidth.value)

  if (idx >= 0 && idx < props.densityData.length) {
    const ch = props.densityData[idx]
    tooltip.value = {
      x: event.clientX - rect.left + 10,
      y: event.clientY - rect.top - 80,
      chapter: ch.chapter,
      tier1: ch.tier1,
      tier2: ch.tier2,
      tier3: ch.tier3,
      total: ch.total
    }
  }
}
</script>

<style scoped>
.event-density-container {
  position: relative;
  width: 100%;
  padding: 1rem;
  background: var(--surface-card);
  border-radius: var(--border-radius);
  border: 1px solid var(--surface-border);
  margin-bottom: 1rem;
}

.density-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.header-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-color);
}

.legend {
  display: flex;
  gap: 1rem;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.dot.tier1 {
  background: #ef4444;
}

.dot.tier2 {
  background: #f59e0b;
}

.dot.tier3 {
  background: #3b82f6;
}

.density-strip {
  display: block;
  cursor: pointer;
}

.tier1-bar {
  fill: #ef4444;
  transition: opacity 0.2s;
}

.tier1-bar:hover {
  opacity: 0.8;
}

.tier2-bar {
  fill: #f59e0b;
  transition: opacity 0.2s;
}

.tier2-bar:hover {
  opacity: 0.8;
}

.tier3-bar {
  fill: #3b82f6;
  transition: opacity 0.2s;
}

.tier3-bar:hover {
  opacity: 0.8;
}

.empty-chapter {
  fill: var(--surface-200);
  stroke: var(--surface-300);
  stroke-width: 1;
  stroke-dasharray: 2 2;
}

.current-indicator {
  fill: var(--primary-color);
}

.chapter-label {
  font-size: 10px;
  fill: var(--text-color-secondary);
  text-anchor: middle;
}

.density-tooltip {
  position: absolute;
  background: var(--surface-900);
  color: white;
  padding: 0.75rem;
  border-radius: var(--border-radius);
  font-size: 0.8125rem;
  pointer-events: none;
  z-index: 1000;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.tooltip-header {
  font-weight: 600;
  margin-bottom: 0.5rem;
  padding-bottom: 0.375rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

.tooltip-row {
  display: flex;
  justify-content: space-between;
  gap: 1.5rem;
  margin-bottom: 0.25rem;
}

.tooltip-row.tier1 {
  color: #fca5a5;
}

.tooltip-row.tier2 {
  color: #fcd34d;
}

.tooltip-row.tier3 {
  color: #93c5fd;
}
</style>
