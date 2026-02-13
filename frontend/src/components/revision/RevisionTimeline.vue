<script setup lang="ts">
/**
 * RevisionTimeline — Timeline simple de versiones (S14-11).
 *
 * Muestra: "V1 (87 alertas) → V2 (62 alertas) → V3 (42 alertas)"
 * usando los datos de comparación disponibles.
 */
import { computed } from 'vue'
import type { ComparisonDetail } from '@/types/domain/alerts'

const props = defineProps<{
  comparison: ComparisonDetail
}>()

interface TimelineEntry {
  version: string
  alertCount: number
  isCurrent: boolean
}

const entries = computed<TimelineEntry[]>(() => {
  if (!props.comparison.hasComparison) return []

  return [
    {
      version: 'Anterior',
      alertCount: props.comparison.totalAlertsBefore,
      isCurrent: false,
    },
    {
      version: 'Actual',
      alertCount: props.comparison.totalAlertsAfter,
      isCurrent: true,
    },
  ]
})

const trend = computed(() => {
  if (entries.value.length < 2) return 'neutral'
  const prev = entries.value[0].alertCount
  const curr = entries.value[1].alertCount
  if (curr < prev) return 'improving'
  if (curr > prev) return 'worsening'
  return 'neutral'
})
</script>

<template>
  <div v-if="entries.length > 0" class="revision-timeline">
    <div class="timeline-track">
      <div
        v-for="(entry, idx) in entries"
        :key="idx"
        class="timeline-entry"
        :class="{ current: entry.isCurrent }"
      >
        <div class="entry-dot" :class="{ current: entry.isCurrent }" />
        <div class="entry-content">
          <span class="entry-version">{{ entry.version }}</span>
          <span class="entry-count" :class="[trend]">
            {{ entry.alertCount }} alertas
          </span>
        </div>
        <div v-if="idx < entries.length - 1" class="entry-connector">
          <i class="pi pi-arrow-right" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.revision-timeline {
  padding: 12px 0;
}

.timeline-track {
  display: flex;
  align-items: center;
  gap: 0;
}

.timeline-entry {
  display: flex;
  align-items: center;
  gap: 8px;
}

.entry-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--surface-300);
  flex-shrink: 0;
}

.entry-dot.current {
  background: var(--primary-color);
  box-shadow: 0 0 0 3px var(--primary-100);
}

.entry-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.entry-version {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.entry-count {
  font-size: 0.9rem;
  font-weight: 600;
}

.entry-count.improving { color: var(--green-600); }
.entry-count.worsening { color: var(--orange-600); }
.entry-count.neutral { color: var(--text-color); }

.entry-connector {
  padding: 0 12px;
  color: var(--surface-400);
  font-size: 0.8rem;
}
</style>
