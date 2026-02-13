<script setup lang="ts">
/**
 * RevisionDashboard — Panel de Revision Intelligence (S14-09).
 *
 * Accesible desde ComparisonBanner (S13). Muestra tabs:
 * Resueltas / Nuevas / Sin cambio, con badge de confianza de matching.
 */
import { computed, onMounted, ref, watch } from 'vue'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import { api } from '@/services/apiClient'
import type { ComparisonDetail, ComparisonAlertDiff } from '@/types/domain/alerts'
import type { ApiComparisonDetail } from '@/types/api/alerts'
import { transformComparisonDetail } from '@/types/transformers/alerts'
import AlertDiffViewer from './AlertDiffViewer.vue'

const props = defineProps<{
  projectId: number
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const detail = ref<ComparisonDetail | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const selectedAlert = ref<ComparisonAlertDiff | null>(null)

async function loadDetail() {
  if (!props.projectId) return
  loading.value = true
  error.value = null
  try {
    const raw = await api.getRaw<{ success: boolean; data: ApiComparisonDetail }>(
      `/api/projects/${props.projectId}/comparison/detail`
    )
    if (raw.success && raw.data) {
      detail.value = transformComparisonDetail(raw.data)
    }
  } catch (e: any) {
    error.value = e.message || 'Error cargando comparación'
  } finally {
    loading.value = false
  }
}

const hasData = computed(() => detail.value?.hasComparison === true)

const resolvedCount = computed(() => detail.value?.alertsResolved.length ?? 0)
const newCount = computed(() => detail.value?.alertsNew.length ?? 0)
const unchangedCount = computed(() => detail.value?.alertsUnchanged ?? 0)

const deltaPercent = computed(() => {
  if (!detail.value || detail.value.totalAlertsBefore === 0) return 0
  const before = detail.value.totalAlertsBefore
  const after = detail.value.totalAlertsAfter
  return Math.round(((after - before) / before) * 100)
})

function confidenceSeverity(conf: number | undefined): 'success' | 'warn' | 'danger' | 'info' {
  if (!conf) return 'info'
  if (conf >= 0.9) return 'success'
  if (conf >= 0.7) return 'warn'
  return 'info'
}

function reasonLabel(reason: string | undefined): string {
  switch (reason) {
    case 'text_changed': return 'Texto editado'
    case 'detector_improved': return 'Mejora del detector'
    case 'manual': return 'Resolución manual'
    default: return reason || 'Desconocido'
  }
}

onMounted(loadDetail)
watch(() => props.projectId, loadDetail)
</script>

<template>
  <div class="revision-dashboard">
    <div class="dashboard-header">
      <h2>
        <i class="pi pi-chart-line" /> Revision Intelligence
      </h2>
      <div v-if="hasData" class="header-stats">
        <span class="stat-before">
          {{ detail!.totalAlertsBefore }} alertas (anterior)
        </span>
        <i class="pi pi-arrow-right" />
        <span class="stat-after">
          {{ detail!.totalAlertsAfter }} alertas (actual)
        </span>
        <Tag
          :value="`${deltaPercent > 0 ? '+' : ''}${deltaPercent}%`"
          :severity="deltaPercent <= 0 ? 'success' : 'danger'"
          class="delta-tag"
        />
      </div>
      <Button
        icon="pi pi-times"
        text
        rounded
        @click="emit('close')"
      />
    </div>

    <div v-if="loading" class="loading-state">
      <i class="pi pi-spin pi-spinner" /> Cargando comparación...
    </div>

    <div v-else-if="error" class="error-state">
      <i class="pi pi-exclamation-triangle" /> {{ error }}
    </div>

    <div v-else-if="!hasData" class="empty-state">
      <i class="pi pi-info-circle" />
      No hay comparación disponible. Realiza un reanálisis para ver cambios.
    </div>

    <template v-else>
      <TabView>
        <TabPanel value="resolved">
          <template #header>
            <span>
              <i class="pi pi-check-circle" />
              Resueltas
              <Tag :value="String(resolvedCount)" severity="success" rounded class="tab-badge" />
            </span>
          </template>
          <div v-if="resolvedCount === 0" class="tab-empty">
            No hay alertas resueltas en esta revisión.
          </div>
          <div v-else class="alert-diff-list">
            <div
              v-for="(alert, idx) in detail!.alertsResolved"
              :key="idx"
              class="alert-diff-item resolved"
              @click="selectedAlert = alert"
            >
              <div class="diff-item-header">
                <span class="diff-title">{{ alert.title }}</span>
                <div class="diff-badges">
                  <Tag
                    v-if="alert.matchConfidence"
                    :value="`${Math.round((alert.matchConfidence ?? 0) * 100)}%`"
                    :severity="confidenceSeverity(alert.matchConfidence)"
                    rounded
                    class="confidence-badge"
                  />
                  <Tag
                    v-if="alert.resolutionReason"
                    :value="reasonLabel(alert.resolutionReason)"
                    severity="info"
                    rounded
                    class="reason-badge"
                  />
                </div>
              </div>
              <div class="diff-item-meta">
                <span v-if="alert.chapter" class="meta-chapter">Cap. {{ alert.chapter }}</span>
                <span class="meta-type">{{ alert.alertType }}</span>
                <span class="meta-severity">{{ alert.severity }}</span>
              </div>
            </div>
          </div>
        </TabPanel>

        <TabPanel value="new">
          <template #header>
            <span>
              <i class="pi pi-exclamation-circle" />
              Nuevas
              <Tag :value="String(newCount)" severity="danger" rounded class="tab-badge" />
            </span>
          </template>
          <div v-if="newCount === 0" class="tab-empty">
            No hay alertas nuevas en esta revisión.
          </div>
          <div v-else class="alert-diff-list">
            <div
              v-for="(alert, idx) in detail!.alertsNew"
              :key="idx"
              class="alert-diff-item new-alert"
            >
              <div class="diff-item-header">
                <span class="diff-title">{{ alert.title }}</span>
              </div>
              <div class="diff-item-meta">
                <span v-if="alert.chapter" class="meta-chapter">Cap. {{ alert.chapter }}</span>
                <span class="meta-type">{{ alert.alertType }}</span>
                <span class="meta-severity">{{ alert.severity }}</span>
              </div>
            </div>
          </div>
        </TabPanel>

        <TabPanel value="unchanged">
          <template #header>
            <span>
              <i class="pi pi-minus-circle" />
              Sin cambio
              <Tag :value="String(unchangedCount)" severity="secondary" rounded class="tab-badge" />
            </span>
          </template>
          <div class="tab-empty">
            {{ unchangedCount }} alertas permanecen sin cambios respecto al análisis anterior.
          </div>
        </TabPanel>
      </TabView>

      <AlertDiffViewer
        v-if="selectedAlert"
        :alert="selectedAlert"
        :project-id="projectId"
        @close="selectedAlert = null"
      />
    </template>
  </div>
</template>

<style scoped>
.revision-dashboard {
  background: var(--surface-card);
  border-radius: 8px;
  padding: 16px;
}

.dashboard-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.dashboard-header h2 {
  margin: 0;
  font-size: 1.1rem;
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-stats {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
  font-size: 0.85rem;
  color: var(--text-color-secondary);
}

.stat-before { opacity: 0.7; }
.stat-after { font-weight: 600; }
.delta-tag { margin-left: 4px; }

.loading-state, .error-state, .empty-state {
  padding: 32px;
  text-align: center;
  color: var(--text-color-secondary);
}

.error-state { color: var(--red-500); }

.tab-badge { margin-left: 6px; }

.tab-empty {
  padding: 24px;
  text-align: center;
  color: var(--text-color-secondary);
  font-style: italic;
}

.alert-diff-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.alert-diff-item {
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
}

.alert-diff-item:hover {
  background: var(--surface-hover);
}

.alert-diff-item.resolved {
  border-left: 3px solid var(--green-400);
}

.alert-diff-item.new-alert {
  border-left: 3px solid var(--orange-400);
}

.diff-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.diff-title {
  font-weight: 500;
  font-size: 0.9rem;
}

.diff-badges {
  display: flex;
  gap: 4px;
}

.diff-item-meta {
  display: flex;
  gap: 8px;
  margin-top: 4px;
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

.meta-chapter {
  font-weight: 500;
}
</style>
