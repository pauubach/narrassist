<script setup lang="ts">
/**
 * ComparisonBanner — resumen de cambios tras reanálisis (BK-25, S13-07 + S14).
 *
 * Muestra un banner con "↓N resueltas · ↑N nuevas · =N sin cambio"
 * tras completar un reanálisis. Clic navega a RevisionDashboard (S14)
 * o abre modal de detalle simple.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import { api } from '@/services/apiClient'

interface ComparisonSummary {
  has_comparison: boolean
  resolved: number
  new: number
  unchanged: number
  document_changed: boolean
}

const props = defineProps<{
  projectId: number
  analysisCompleted?: boolean
}>()

const router = useRouter()

const summary = ref<ComparisonSummary | null>(null)
const showDetail = ref(false)
const loading = ref(false)

const hasComparison = computed(() => summary.value?.has_comparison === true)
const isPositive = computed(() =>
  hasComparison.value && (summary.value!.resolved > summary.value!.new)
)
const isNegative = computed(() =>
  hasComparison.value && (summary.value!.new > summary.value!.resolved)
)

async function loadSummary() {
  if (!props.projectId) return
  loading.value = true
  try {
    const data = await api.getRaw<ComparisonSummary>(
      `/api/projects/${props.projectId}/comparison/summary`
    )
    summary.value = data
  } catch {
    summary.value = null
  } finally {
    loading.value = false
  }
}

function dismiss() {
  summary.value = null
}

// Cargar al montar y cuando cambia el proyecto
onMounted(loadSummary)
watch(() => props.projectId, loadSummary)
watch(() => props.analysisCompleted, (val) => {
  if (val) loadSummary()
})
</script>

<template>
  <div
    v-if="hasComparison && !loading"
    class="comparison-banner"
    :class="{ positive: isPositive, negative: isNegative, neutral: !isPositive && !isNegative }"
  >
    <div class="banner-content" @click="router.push({ name: 'revision', params: { id: props.projectId } })">
      <i class="pi pi-chart-line banner-icon" />
      <span class="banner-text">
        <span v-if="summary!.resolved > 0" class="resolved-count">
          <i class="pi pi-arrow-down" /> {{ summary!.resolved }} resueltas
        </span>
        <span v-if="summary!.resolved > 0 && summary!.new > 0" class="separator"> · </span>
        <span v-if="summary!.new > 0" class="new-count">
          <i class="pi pi-arrow-up" /> {{ summary!.new }} nuevas
        </span>
        <span v-if="(summary!.resolved > 0 || summary!.new > 0) && summary!.unchanged > 0" class="separator"> · </span>
        <span v-if="summary!.unchanged > 0" class="unchanged-count">
          = {{ summary!.unchanged }} sin cambio
        </span>
        <span v-if="summary!.resolved === 0 && summary!.new === 0">
          Sin cambios respecto al análisis anterior
        </span>
      </span>
    </div>
    <Button
      icon="pi pi-times"
      text
      rounded
      size="small"
      class="dismiss-btn"
      @click.stop="dismiss"
    />
  </div>

  <!-- Modal detalle -->
  <Dialog
    :visible="showDetail"
    header="Comparación con análisis anterior"
    :modal="true"
    :style="{ width: '500px' }"
    @update:visible="showDetail = $event"
  >
    <div v-if="summary" class="comparison-detail">
      <div class="detail-row resolved">
        <i class="pi pi-check-circle" />
        <span class="detail-label">Alertas resueltas</span>
        <span class="detail-count">{{ summary.resolved }}</span>
      </div>
      <div class="detail-row new-issues">
        <i class="pi pi-exclamation-circle" />
        <span class="detail-label">Alertas nuevas</span>
        <span class="detail-count">{{ summary.new }}</span>
      </div>
      <div class="detail-row unchanged">
        <i class="pi pi-minus-circle" />
        <span class="detail-label">Sin cambio</span>
        <span class="detail-count">{{ summary.unchanged }}</span>
      </div>
      <div v-if="summary.document_changed" class="detail-note">
        <i class="pi pi-file-edit" />
        El documento ha cambiado respecto a la versión anterior.
      </div>
    </div>

    <template #footer>
      <Button label="Cerrar" text @click="showDetail = false" />
    </template>
  </Dialog>
</template>

<style scoped>
.comparison-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  border-radius: var(--app-radius);
  margin-bottom: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.comparison-banner.positive {
  background: var(--green-50, #f0fdf4);
  border: 1px solid var(--green-200, #bbf7d0);
  color: var(--green-800, #166534);
}

.comparison-banner.negative {
  background: var(--orange-50, #fff7ed);
  border: 1px solid var(--orange-200, #fed7aa);
  color: var(--orange-800, #9a3412);
}

.comparison-banner.neutral {
  background: var(--surface-50, #f8fafc);
  border: 1px solid var(--surface-200, #e2e8f0);
  color: var(--text-color-secondary);
}

.banner-content {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.banner-icon {
  font-size: 1.1rem;
}

.banner-text {
  font-size: 0.9rem;
  font-weight: 500;
}

.resolved-count { color: var(--green-700, #15803d); }
.new-count { color: var(--orange-700, #c2410c); }
.unchanged-count { color: var(--text-color-secondary); }
.separator { color: var(--text-color-secondary); margin: 0 2px; }

.dismiss-btn {
  flex-shrink: 0;
}

.comparison-detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--app-radius);
}

.detail-row.resolved {
  background: var(--green-50, #f0fdf4);
  color: var(--green-700, #15803d);
}

.detail-row.new-issues {
  background: var(--orange-50, #fff7ed);
  color: var(--orange-700, #c2410c);
}

.detail-row.unchanged {
  background: var(--surface-50, #f8fafc);
  color: var(--text-color-secondary);
}

.detail-label {
  flex: 1;
  font-weight: 500;
}

.detail-count {
  font-size: 1.2rem;
  font-weight: 700;
}

.detail-note {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--blue-50, #eff6ff);
  color: var(--blue-700, #1d4ed8);
  border-radius: var(--app-radius);
  font-size: 0.85rem;
}
</style>
