<template>
  <div v-if="visible" class="event-stats-card">
    <div class="stats-header">
      <h4>
        <i class="pi pi-chart-bar"></i>
        Estadísticas de Eventos
      </h4>
      <Button icon="pi pi-times" text rounded size="small" @click="emit('close')" />
    </div>

    <div v-if="loading" class="stats-loading">
      <ProgressSpinner style="width: 30px; height: 30px" />
    </div>

    <div v-else-if="stats" class="stats-body">
      <!-- Métrica 1: Eventos críticos sin resolver -->
      <div class="stat-section critical">
        <div class="stat-label">
          <i class="pi pi-exclamation-triangle"></i>
          Eventos Críticos Sin Resolver
        </div>
        <div class="stat-value">{{ stats.criticalUnresolved.count }}</div>
        <div v-if="stats.criticalUnresolved.count > 0" class="stat-details">
          <div
            v-for="(count, type) in stats.criticalUnresolved.byType"
            :key="type"
            class="detail-item"
          >
            <span class="detail-type">{{ formatEventType(type) }}</span>
            <Tag severity="danger" :value="count.toString()" />
          </div>
        </div>
      </div>

      <!-- Métrica 2: Capítulos vacíos -->
      <div class="stat-section empty">
        <div class="stat-label">
          <i class="pi pi-file"></i>
          Capítulos sin eventos base
        </div>
        <div class="stat-value">{{ stats.emptyChapters.length }}</div>
        <div v-if="stats.emptyChapters.length > 0" class="stat-details">
          <div class="chapter-chips">
            <Chip
              v-for="ch in stats.emptyChapters.slice(0, 10)"
              :key="ch"
              :label="`Cap. ${ch}`"
              class="chapter-chip"
              @click="emit('navigate-to-chapter', ch)"
            />
            <span v-if="stats.emptyChapters.length > 10" class="more-count">
              +{{ stats.emptyChapters.length - 10 }} más
            </span>
          </div>
        </div>
      </div>

      <!-- Métrica 3: Event clusters -->
      <div class="stat-section clusters">
        <div class="stat-label">
          <i class="pi pi-sitemap"></i>
          Clusters de Eventos (Top 3)
        </div>
        <div v-if="stats.eventClusters.length > 0" class="stat-details">
          <div
            v-for="cluster in stats.eventClusters"
            :key="`${cluster.eventType}-${cluster.chapter}`"
            class="cluster-item"
            @click="emit('navigate-to-chapter', cluster.chapter)"
          >
            <div class="cluster-info">
              <span class="cluster-count">{{ cluster.count }}x</span>
              <span class="cluster-type">{{ formatEventType(cluster.eventType) }}</span>
            </div>
            <span class="cluster-chapter">Cap. {{ cluster.chapter }}</span>
          </div>
        </div>
        <div v-else class="no-clusters">No hay clusters significativos (3+ eventos)</div>
      </div>

      <!-- Total de eventos -->
      <div class="stat-footer">
        <span>Total de eventos detectados:</span>
        <strong>{{ stats.totalEvents }}</strong>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Chip from 'primevue/chip'
import ProgressSpinner from 'primevue/progressspinner'

interface EventStats {
  projectId: number
  totalEvents: number
  criticalUnresolved: {
    count: number
    byType: Record<string, number>
  }
  emptyChapters: number[]
  eventClusters: Array<{
    eventType: string
    chapter: number
    count: number
  }>
}

const props = defineProps<{
  projectId: number
  visible: boolean
}>()

const emit = defineEmits<{
  close: []
  'navigate-to-chapter': [number]
}>()

const loading = ref(false)
const stats = ref<EventStats | null>(null)

async function loadStats() {
  loading.value = true
  try {
    const response = await fetch(`/api/projects/${props.projectId}/events/stats`)
    const data = await response.json()

    if (data.success) {
      stats.value = {
        projectId: data.data.project_id,
        totalEvents: data.data.total_events,
        criticalUnresolved: {
          count: data.data.critical_unresolved.count,
          byType: data.data.critical_unresolved.by_type
        },
        emptyChapters: data.data.empty_chapters,
        eventClusters: data.data.event_clusters.map((c: any) => ({
          eventType: c.event_type,
          chapter: c.chapter,
          count: c.count
        }))
      }
    }
  } catch (error) {
    console.error('Error loading event stats:', error)
  } finally {
    loading.value = false
  }
}

watch(
  () => props.visible,
  (newVal) => {
    if (newVal && !stats.value) {
      loadStats()
    }
  },
  { immediate: true }
)

function formatEventType(type: string): string {
  const labels: Record<string, string> = {
    promise: 'Promesas',
    injury: 'Heridas',
    flashback_start: 'Flashbacks',
    acquisition: 'Adquisiciones',
    confession: 'Confesiones',
    lie: 'Mentiras',
    conflict_start: 'Conflictos',
    revelation: 'Revelaciones',
    death: 'Muertes',
    betrayal: 'Traiciones'
  }
  return labels[type] || type
}
</script>

<style scoped>
.event-stats-card {
  position: fixed;
  top: 80px;
  right: 20px;
  width: 320px;
  max-height: calc(100vh - 100px);
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  z-index: var(--ds-z-popover);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.stats-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid var(--surface-border);
  background: var(--surface-50);
}

.stats-header h4 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.stats-loading {
  padding: 2rem;
  display: flex;
  justify-content: center;
}

.stats-body {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.stat-section {
  padding: 0.75rem;
  border-radius: var(--border-radius);
  border-left: 4px solid;
}

.stat-section.critical {
  border-color: #ef4444;
  background: #fef2f2;
}

.stat-section.empty {
  border-color: #f59e0b;
  background: #fffbeb;
}

.stat-section.clusters {
  border-color: #3b82f6;
  background: #eff6ff;
}

.stat-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text-color);
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-color);
}

.stat-details {
  margin-top: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8125rem;
}

.detail-type {
  color: var(--text-color-secondary);
}

.chapter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
}

.chapter-chip {
  font-size: 0.75rem;
  cursor: pointer;
  transition: transform 0.15s;
}

.chapter-chip:hover {
  transform: scale(1.05);
}

.more-count {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  font-style: italic;
}

.cluster-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  background: var(--surface-0);
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: background 0.15s;
}

.cluster-item:hover {
  background: var(--surface-100);
}

.cluster-info {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.cluster-count {
  font-weight: 700;
  color: var(--primary-color);
}

.cluster-type {
  font-size: 0.8125rem;
  color: var(--text-color);
}

.cluster-chapter {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.no-clusters {
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
  font-style: italic;
  text-align: center;
  padding: 1rem 0;
}

.stat-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 0.75rem;
  border-top: 1px solid var(--surface-border);
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.stat-footer strong {
  font-size: 1.125rem;
  color: var(--text-color);
}
</style>
