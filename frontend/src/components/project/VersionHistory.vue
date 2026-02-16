<script setup lang="ts">
/**
 * VersionHistory — tabla expandible con historial de versiones (S15-05, BK-28).
 *
 * Muestra todas las versiones: fecha, alert_count, word_count, health_score.
 * Permite seleccionar 2 versiones para comparar (abre VersionComparison).
 */
import { computed, onMounted, ref, watch } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { api } from '@/services/apiClient'
import type { ApiVersionMetrics } from '@/types/api/projects'
import { transformVersionMetrics } from '@/types/transformers/projects'
import type { VersionMetrics } from '@/types/domain/projects'
import VersionComparison from './VersionComparison.vue'

const props = defineProps<{
  projectId: number
}>()

const versions = ref<VersionMetrics[]>([])
const loading = ref(false)
const selectedVersions = ref<VersionMetrics[]>([])
const showComparison = ref(false)

async function loadVersions() {
  if (!props.projectId) return
  loading.value = true
  try {
    const raw = await api.getRaw<{ success: boolean; data: ApiVersionMetrics[] }>(
      `/api/projects/${props.projectId}/versions`
    )
    if (raw.success && raw.data) {
      versions.value = raw.data.map(transformVersionMetrics)
    }
  } catch {
    versions.value = []
  } finally {
    loading.value = false
  }
}

onMounted(loadVersions)
watch(() => props.projectId, loadVersions)

const canCompare = computed(() => selectedVersions.value.length === 2)

function openComparison() {
  if (canCompare.value) {
    showComparison.value = true
  }
}

function formatDate(date: Date): string {
  return date.toLocaleDateString('es-ES', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function healthSeverity(score: number | null): 'success' | 'warn' | 'danger' | 'info' {
  if (score === null) return 'info'
  if (score >= 0.7) return 'success'
  if (score >= 0.4) return 'warn'
  return 'danger'
}

function formatHealth(score: number | null): string {
  if (score === null) return '-'
  return (score * 100).toFixed(0) + '%'
}

function formatRatio(ratio: number | null): string {
  if (ratio === null) return '-'
  return (ratio * 100).toFixed(0) + '%'
}

/** Delta indicator between consecutive versions */
function alertDelta(version: VersionMetrics, index: number): string | null {
  // versions are desc, so index+1 is the previous version
  if (index >= versions.value.length - 1) return null
  const prev = versions.value[index + 1]
  const diff = version.alertCount - prev.alertCount
  if (diff === 0) return null
  return diff > 0 ? `+${diff}` : `${diff}`
}

function alertDeltaClass(version: VersionMetrics, index: number): string {
  if (index >= versions.value.length - 1) return ''
  const prev = versions.value[index + 1]
  const diff = version.alertCount - prev.alertCount
  if (diff < 0) return 'delta-positive'
  if (diff > 0) return 'delta-negative'
  return ''
}

const comparisonVersions = computed(() => {
  if (!canCompare.value) return { older: null, newer: null }
  const sorted = [...selectedVersions.value].sort((a, b) => a.versionNum - b.versionNum)
  return { older: sorted[0], newer: sorted[1] }
})
</script>

<template>
  <div class="version-history">
    <div class="history-header">
      <h3>Historial de versiones</h3>
      <Button
        v-if="versions.length >= 2"
        label="Comparar seleccionadas"
        icon="pi pi-arrows-h"
        size="small"
        :disabled="!canCompare"
        @click="openComparison"
      />
    </div>

    <DataTable
      v-model:selection="selectedVersions"
      :value="versions"
      :loading="loading"
      :paginator="versions.length > 10"
      :rows="10"
      striped-rows
      size="small"
      data-key="id"
      :selection-mode="versions.length >= 2 ? undefined : undefined"
      class="version-table"
    >
      <Column v-if="versions.length >= 2" selection-mode="multiple" header-style="width: 3rem" />

      <Column field="versionNum" header="Ver." style="width: 4rem">
        <template #body="{ data }">
          <strong>v{{ data.versionNum }}</strong>
        </template>
      </Column>

      <Column field="createdAt" header="Fecha">
        <template #body="{ data }">
          {{ formatDate(data.createdAt) }}
        </template>
      </Column>

      <Column field="alertCount" header="Alertas" style="width: 7rem">
        <template #body="{ data, index }">
          <span>{{ data.alertCount }}</span>
          <span
            v-if="alertDelta(data, index)"
            class="delta-badge"
            :class="alertDeltaClass(data, index)"
          >
            {{ alertDelta(data, index) }}
          </span>
        </template>
      </Column>

      <Column field="wordCount" header="Palabras" style="width: 6rem">
        <template #body="{ data }">
          {{ data.wordCount.toLocaleString('es-ES') }}
        </template>
      </Column>

      <Column field="entityCount" header="Entidades" style="width: 6rem" />

      <Column field="healthScore" header="Salud" style="width: 5rem">
        <template #body="{ data }">
          <Tag
            v-if="data.healthScore !== null"
            :value="formatHealth(data.healthScore)"
            :severity="healthSeverity(data.healthScore)"
          />
          <span v-else class="text-muted">-</span>
        </template>
      </Column>

      <Column field="dialogueRatio" header="Diálogo" style="width: 5rem">
        <template #body="{ data }">
          {{ formatRatio(data.dialogueRatio) }}
        </template>
      </Column>

      <template #empty>
        <div class="empty-message">
          <i class="pi pi-history" />
          <p>No hay versiones registradas. Ejecuta un análisis para crear la primera.</p>
        </div>
      </template>
    </DataTable>

    <!-- Comparison modal -->
    <VersionComparison
      v-if="comparisonVersions.older && comparisonVersions.newer"
      :visible="showComparison"
      :older="comparisonVersions.older"
      :newer="comparisonVersions.newer"
      :project-id="projectId"
      @close="showComparison = false"
    />
  </div>
</template>

<style scoped>
.version-history {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.history-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.delta-badge {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 1px 4px;
  border-radius: var(--app-radius-sm);
  margin-left: 4px;
}

.delta-positive {
  color: var(--green-700, #15803d);
  background: var(--green-50, #f0fdf4);
}

.delta-negative {
  color: var(--red-700, #b91c1c);
  background: var(--red-50, #fef2f2);
}

.text-muted {
  color: var(--text-color-secondary);
}

.empty-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 24px;
  color: var(--text-color-secondary);
}

.empty-message i {
  font-size: 2rem;
}
</style>
