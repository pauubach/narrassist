<script setup lang="ts">
/**
 * VersionComparison — modal con diff de métricas entre 2 versiones (S15-06, BK-28).
 *
 * Barras de progreso comparativas. Enlace a RevisionDashboard si existe snapshot.
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import ProgressBar from 'primevue/progressbar'
import type { VersionMetrics } from '@/types/domain/projects'

const props = defineProps<{
  visible: boolean
  older: VersionMetrics
  newer: VersionMetrics
  projectId: number
}>()

const emit = defineEmits<{
  close: []
}>()

const router = useRouter()

interface MetricRow {
  label: string
  icon: string
  oldValue: number
  newValue: number
  format: (v: number) => string
  invert?: boolean // true = lower is better (alerts)
}

const metrics = computed<MetricRow[]>(() => [
  {
    label: 'Alertas',
    icon: 'pi pi-exclamation-triangle',
    oldValue: props.older.alertCount,
    newValue: props.newer.alertCount,
    format: (v) => v.toString(),
    invert: true,
  },
  {
    label: 'Alertas nuevas',
    icon: 'pi pi-plus-circle',
    oldValue: props.older.alertsNewCount ?? 0,
    newValue: props.newer.alertsNewCount ?? 0,
    format: (v) => v.toString(),
    invert: true,
  },
  {
    label: 'Alertas resueltas',
    icon: 'pi pi-check-circle',
    oldValue: props.older.alertsResolvedCount ?? 0,
    newValue: props.newer.alertsResolvedCount ?? 0,
    format: (v) => v.toString(),
  },
  {
    label: 'Palabras',
    icon: 'pi pi-file-word',
    oldValue: props.older.wordCount,
    newValue: props.newer.wordCount,
    format: (v) => v.toLocaleString('es-ES'),
  },
  {
    label: 'Entidades',
    icon: 'pi pi-users',
    oldValue: props.older.entityCount,
    newValue: props.newer.entityCount,
    format: (v) => v.toString(),
  },
  {
    label: 'Renombres',
    icon: 'pi pi-pencil',
    oldValue: props.older.entitiesRenamedCount ?? props.older.renamedEntities ?? 0,
    newValue: props.newer.entitiesRenamedCount ?? props.newer.renamedEntities ?? 0,
    format: (v) => v.toString(),
  },
  {
    label: 'Salud narrativa',
    icon: 'pi pi-heart',
    oldValue: (props.older.healthScore ?? 0) * 100,
    newValue: (props.newer.healthScore ?? 0) * 100,
    format: (v) => v.toFixed(0) + '%',
  },
  {
    label: 'Ratio diálogo',
    icon: 'pi pi-comments',
    oldValue: (props.older.dialogueRatio ?? 0) * 100,
    newValue: (props.newer.dialogueRatio ?? 0) * 100,
    format: (v) => v.toFixed(0) + '%',
  },
])

function deltaClass(row: MetricRow): string {
  const diff = row.newValue - row.oldValue
  if (diff === 0) return 'neutral'
  if (row.invert) return diff < 0 ? 'improved' : 'worsened'
  return diff > 0 ? 'improved' : 'worsened'
}

function deltaText(row: MetricRow): string {
  const diff = row.newValue - row.oldValue
  if (diff === 0) return '='
  const sign = diff > 0 ? '+' : ''
  return `${sign}${row.format(diff)}`
}

function barValue(value: number, row: MetricRow): number {
  const max = Math.max(row.oldValue, row.newValue, 1)
  return Math.round((value / max) * 100)
}

const hasSnapshot = computed(() => props.newer.snapshotId !== null)

function goToRevision() {
  router.push({ name: 'revision', params: { id: props.projectId } })
  emit('close')
}
</script>

<template>
  <Dialog
    :visible="visible"
    :modal="true"
    :header="`Comparación: v${older.versionNum} → v${newer.versionNum}`"
    :style="{ width: '560px' }"
    @update:visible="!$event && emit('close')"
  >
    <div class="comparison-grid">
      <div v-for="row in metrics" :key="row.label" class="metric-row">
        <div class="metric-label">
          <i :class="row.icon" />
          {{ row.label }}
        </div>
        <div class="metric-bars">
          <div class="bar-row">
            <span class="bar-label">v{{ older.versionNum }}</span>
            <ProgressBar
              :value="barValue(row.oldValue, row)"
              :show-value="false"
              class="bar old-bar"
            />
            <span class="bar-value">{{ row.format(row.oldValue) }}</span>
          </div>
          <div class="bar-row">
            <span class="bar-label">v{{ newer.versionNum }}</span>
            <ProgressBar
              :value="barValue(row.newValue, row)"
              :show-value="false"
              class="bar new-bar"
            />
            <span class="bar-value">{{ row.format(row.newValue) }}</span>
          </div>
        </div>
        <div class="metric-delta" :class="deltaClass(row)">
          {{ deltaText(row) }}
        </div>
      </div>
    </div>

    <template #footer>
      <Button
        v-if="hasSnapshot"
        label="Ver detalle de revisiones"
        icon="pi pi-external-link"
        text
        size="small"
        @click="goToRevision"
      />
      <Button label="Cerrar" text @click="emit('close')" />
    </template>
  </Dialog>
</template>

<style scoped>
.comparison-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.metric-row {
  display: grid;
  grid-template-columns: 140px 1fr 60px;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--surface-200, #e2e8f0);
}

.metric-row:last-child {
  border-bottom: none;
}

.metric-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
  font-size: 0.9rem;
  color: var(--text-color);
}

.metric-label i {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
}

.metric-bars {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.bar-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bar-label {
  font-size: 0.7rem;
  color: var(--text-color-secondary);
  width: 24px;
  text-align: right;
}

.bar {
  flex: 1;
  height: 8px;
}

.bar-value {
  font-size: 0.75rem;
  font-weight: 600;
  width: 50px;
  text-align: right;
}

.metric-delta {
  font-size: 0.8rem;
  font-weight: 700;
  text-align: center;
  padding: 2px 6px;
  border-radius: var(--app-radius);
}

.metric-delta.improved {
  color: var(--green-700, #15803d);
  background: var(--green-50, #f0fdf4);
}

.metric-delta.worsened {
  color: var(--red-700, #b91c1c);
  background: var(--red-50, #fef2f2);
}

.metric-delta.neutral {
  color: var(--text-color-secondary);
  background: var(--surface-50, #f8fafc);
}
</style>
