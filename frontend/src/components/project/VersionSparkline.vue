<script setup lang="ts">
/**
 * VersionSparkline — SVG inline sparkline for alert_count trend (S15-04, BK-28).
 *
 * Shows last N versions as a mini line chart. Tooltip on hover shows
 * version number + date + alert count. No charting library dependency.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '@/services/apiClient'
import type { ApiVersionTrend } from '@/types/api/projects'
import { transformVersionTrend } from '@/types/transformers/projects'
import type { VersionTrend } from '@/types/domain/projects'

const props = defineProps<{
  projectId: number
  metric?: 'alertCount' | 'healthScore'
  width?: number
  height?: number
}>()

const metric = computed(() => props.metric ?? 'alertCount')
const W = computed(() => props.width ?? 120)
const H = computed(() => props.height ?? 32)
const PADDING = 4

const trend = ref<VersionTrend | null>(null)
const loading = ref(false)
const hoveredIndex = ref<number | null>(null)

async function loadTrend() {
  if (!props.projectId) return
  loading.value = true
  try {
    const raw = await api.getRaw<{ success: boolean; data: ApiVersionTrend }>(
      `/api/projects/${props.projectId}/versions/trend`
    )
    if (raw.success && raw.data) {
      trend.value = transformVersionTrend(raw.data)
    }
  } catch {
    trend.value = null
  } finally {
    loading.value = false
  }
}

onMounted(loadTrend)
watch(() => props.projectId, loadTrend)

/** SVG polyline points from trend data */
const points = computed(() => {
  if (!trend.value || trend.value.trend.length < 2) return ''
  const data = trend.value.trend
  const values = data.map(p =>
    metric.value === 'healthScore' ? (p.healthScore ?? 0) : p.alertCount
  )
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1

  const usableW = W.value - PADDING * 2
  const usableH = H.value - PADDING * 2

  return data.map((_, i) => {
    const x = PADDING + (i / (data.length - 1)) * usableW
    const y = PADDING + usableH - ((values[i] - min) / range) * usableH
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
})

/** Dot positions for hover */
const dots = computed(() => {
  if (!trend.value || trend.value.trend.length < 2) return []
  const data = trend.value.trend
  const values = data.map(p =>
    metric.value === 'healthScore' ? (p.healthScore ?? 0) : p.alertCount
  )
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1

  const usableW = W.value - PADDING * 2
  const usableH = H.value - PADDING * 2

  return data.map((p, i) => ({
    x: PADDING + (i / (data.length - 1)) * usableW,
    y: PADDING + usableH - ((values[i] - min) / range) * usableH,
    label: `v${p.versionNum}: ${metric.value === 'healthScore'
      ? ((p.healthScore ?? 0) * 100).toFixed(0) + '%'
      : p.alertCount + ' alertas'}`,
  }))
})

/** Trend color: green if improving (alerts down / health up), red if worsening */
const strokeColor = computed(() => {
  if (!trend.value?.delta) return 'var(--text-color-secondary)'
  if (metric.value === 'healthScore') {
    const d = trend.value.delta.healthScore
    if (d !== null && d > 0) return 'var(--green-500, #22c55e)'
    if (d !== null && d < 0) return 'var(--red-500, #ef4444)'
  } else {
    const d = trend.value.delta.alertCount
    if (d < 0) return 'var(--green-500, #22c55e)'
    if (d > 0) return 'var(--red-500, #ef4444)'
  }
  return 'var(--text-color-secondary)'
})

/** Delta badge text */
const deltaText = computed(() => {
  if (!trend.value?.delta) return null
  if (metric.value === 'healthScore') {
    const d = trend.value.delta.healthScore
    if (d === null) return null
    const pct = (d * 100).toFixed(0)
    return d > 0 ? `+${pct}%` : `${pct}%`
  }
  const d = trend.value.delta.alertCount
  return d > 0 ? `+${d}` : `${d}`
})

const hasTrend = computed(() => trend.value && trend.value.trend.length >= 2)
</script>

<template>
  <div v-if="hasTrend" class="sparkline-wrapper" :title="deltaText ?? undefined">
    <svg
      :width="W"
      :height="H"
      class="sparkline-svg"
      @mouseleave="hoveredIndex = null"
    >
      <polyline
        :points="points"
        fill="none"
        :stroke="strokeColor"
        stroke-width="1.5"
        stroke-linejoin="round"
        stroke-linecap="round"
      />
      <!-- Hover dots -->
      <circle
        v-for="(dot, i) in dots"
        :key="i"
        :cx="dot.x"
        :cy="dot.y"
        :r="hoveredIndex === i ? 3 : 0"
        :fill="strokeColor"
        @mouseenter="hoveredIndex = i"
      >
        <title>{{ dot.label }}</title>
      </circle>
      <!-- Invisible hit areas for hover -->
      <rect
        v-for="(dot, i) in dots"
        :key="'h' + i"
        :x="dot.x - 6"
        :y="0"
        :width="12"
        :height="H"
        fill="transparent"
        @mouseenter="hoveredIndex = i"
      />
    </svg>
    <span v-if="deltaText" class="delta-badge" :class="{ positive: deltaText.startsWith('-') || deltaText.startsWith('+') && metric === 'healthScore', negative: deltaText.startsWith('+') && metric !== 'healthScore' }">
      {{ deltaText }}
    </span>
  </div>
</template>

<style scoped>
.sparkline-wrapper {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.sparkline-svg {
  cursor: crosshair;
}

.delta-badge {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 1px 4px;
  border-radius: var(--app-radius-sm);
  white-space: nowrap;
}

.delta-badge.positive {
  color: var(--green-700, #15803d);
  background: var(--green-50, #f0fdf4);
}

.delta-badge.negative {
  color: var(--red-700, #b91c1c);
  background: var(--red-50, #fef2f2);
}
</style>
