<template>
  <div class="cross-book-report">
    <div class="report-header">
      <h3>Análisis de Inconsistencias Cross-Book</h3>
      <div class="header-actions">
        <Button
          label="Analizar atributos"
          icon="pi pi-play"
          :loading="analyzingAttributes"
          @click="runAttributeAnalysis"
          size="small"
        />
        <Button
          label="Analizar eventos"
          icon="pi pi-bolt"
          :loading="analyzingEvents"
          @click="runEventAnalysis"
          size="small"
          severity="secondary"
        />
      </div>
    </div>

    <!-- Loading -->
    <div v-if="analyzingAttributes || analyzingEvents" class="loading-state">
      <ProgressSpinner style="width: 2rem; height: 2rem" />
      <span>{{ analyzingAttributes ? 'Comparando atributos...' : 'Comparando eventos...' }}</span>
    </div>

    <!-- No reports yet -->
    <div v-else-if="!report && !eventReport" class="empty-state">
      <i class="pi pi-chart-bar empty-icon"></i>
      <p>No se ha ejecutado el análisis</p>
      <p class="hint">Pulsa uno de los botones de análisis para comparar entidades enlazadas entre libros</p>
    </div>

    <template v-else>
      <!-- ===================== Attribute Inconsistencies ===================== -->
      <template v-if="report">
        <h4 class="section-title">Inconsistencias de Atributos</h4>

        <!-- Summary -->
        <div class="report-summary">
          <div class="summary-card">
            <span class="summary-value" :class="{ 'has-issues': report.summary.totalInconsistencies > 0 }">
              {{ report.summary.totalInconsistencies }}
            </span>
            <span class="summary-label">Inconsistencias</span>
          </div>
          <div class="summary-card">
            <span class="summary-value">{{ report.entityLinksAnalyzed }}</span>
            <span class="summary-label">Enlaces analizados</span>
          </div>
          <div class="summary-card">
            <span class="summary-value">{{ report.projectsAnalyzed }}</span>
            <span class="summary-label">Libros</span>
          </div>
        </div>

        <!-- By type breakdown -->
        <div v-if="Object.keys(report.summary.byType).length" class="type-breakdown">
          <Tag
            v-for="(count, type) in report.summary.byType"
            :key="type"
            :value="`${translateType(String(type))}: ${count}`"
            severity="warn"
          />
        </div>

        <!-- No inconsistencies -->
        <div v-if="report.summary.totalInconsistencies === 0" class="success-state">
          <i class="pi pi-check-circle success-icon"></i>
          <p>No se encontraron inconsistencias de atributos</p>
        </div>

        <!-- Inconsistencies grouped by entity -->
        <div v-else class="inconsistencies">
          <div
            v-for="(group, entityName) in groupedInconsistencies"
            :key="entityName"
            class="entity-group"
          >
            <div class="entity-header">
              <i class="pi pi-user"></i>
              <span class="entity-name">{{ entityName }}</span>
              <Tag :value="`${group.length} diferencias`" severity="warn" />
            </div>

            <DataTable :value="group" striped-rows class="inconsistency-table">
              <Column header="Atributo" style="min-width: 120px">
                <template #body="{ data }">
                  <div class="attr-cell">
                    <span class="attr-key">{{ translateAttribute(data.attributeKey) }}</span>
                    <span class="attr-type">{{ translateType(data.attributeType) }}</span>
                  </div>
                </template>
              </Column>
              <Column :header="'Libro A'" style="min-width: 150px">
                <template #body="{ data }">
                  <div class="value-cell">
                    <span class="value-text value-a">{{ data.valueBookA }}</span>
                    <span class="book-name">{{ data.bookAName }}</span>
                  </div>
                </template>
              </Column>
              <Column header="" style="width: 40px; text-align: center">
                <template #body>
                  <i class="pi pi-exclamation-triangle" style="color: var(--orange-500)"></i>
                </template>
              </Column>
              <Column :header="'Libro B'" style="min-width: 150px">
                <template #body="{ data }">
                  <div class="value-cell">
                    <span class="value-text value-b">{{ data.valueBookB }}</span>
                    <span class="book-name">{{ data.bookBName }}</span>
                  </div>
                </template>
              </Column>
              <Column header="Confianza" style="width: 90px; text-align: center">
                <template #body="{ data }">
                  <Tag
                    :value="`${(data.confidence * 100).toFixed(0)}%`"
                    :severity="data.confidence >= 0.8 ? 'danger' : 'warn'"
                  />
                </template>
              </Column>
            </DataTable>
          </div>
        </div>
      </template>

      <!-- ===================== Event Contradictions ===================== -->
      <template v-if="eventReport">
        <h4 class="section-title section-title--events">Contradicciones de Eventos</h4>

        <!-- Event summary -->
        <div class="report-summary">
          <div class="summary-card">
            <span class="summary-value" :class="{ 'has-issues': eventReport.summary.totalContradictions > 0 }">
              {{ eventReport.summary.totalContradictions }}
            </span>
            <span class="summary-label">Contradicciones</span>
          </div>
          <div class="summary-card">
            <span class="summary-value">{{ eventReport.entityLinksAnalyzed }}</span>
            <span class="summary-label">Enlaces analizados</span>
          </div>
          <div class="summary-card">
            <span class="summary-value">{{ eventReport.projectsAnalyzed }}</span>
            <span class="summary-label">Libros</span>
          </div>
        </div>

        <!-- Rule breakdown -->
        <div v-if="Object.keys(eventReport.summary.byRule).length" class="type-breakdown">
          <Tag
            v-for="(count, rule) in eventReport.summary.byRule"
            :key="rule"
            :value="`${translateRule(String(rule))}: ${count}`"
            severity="danger"
          />
        </div>

        <!-- No contradictions -->
        <div v-if="eventReport.summary.totalContradictions === 0" class="success-state">
          <i class="pi pi-check-circle success-icon"></i>
          <p>No se encontraron contradicciones de eventos entre libros</p>
        </div>

        <!-- Contradictions grouped by entity -->
        <div v-else class="inconsistencies">
          <div
            v-for="(group, entityName) in groupedContradictions"
            :key="entityName"
            class="entity-group entity-group--events"
          >
            <div class="entity-header">
              <i class="pi pi-bolt"></i>
              <span class="entity-name">{{ entityName }}</span>
              <Tag :value="`${group.length} contradicciones`" severity="danger" />
            </div>

            <DataTable :value="group" striped-rows class="inconsistency-table">
              <Column header="Regla" style="min-width: 130px">
                <template #body="{ data }">
                  <div class="attr-cell">
                    <span class="attr-key">{{ translateRule(data.rule) }}</span>
                  </div>
                </template>
              </Column>
              <Column header="Descripción" style="min-width: 250px">
                <template #body="{ data }">
                  <span>{{ data.description }}</span>
                </template>
              </Column>
              <Column header="Libros" style="min-width: 150px">
                <template #body="{ data }">
                  <div class="value-cell">
                    <span class="value-text value-a">{{ data.bookAName }}{{ data.bookAChapter ? ` (cap. ${data.bookAChapter})` : '' }}</span>
                    <span class="value-text value-b">{{ data.bookBName }}{{ data.bookBChapter ? ` (cap. ${data.bookBChapter})` : '' }}</span>
                  </div>
                </template>
              </Column>
              <Column header="Confianza" style="width: 90px; text-align: center">
                <template #body="{ data }">
                  <Tag
                    :value="`${(data.confidence * 100).toFixed(0)}%`"
                    :severity="data.confidence >= 0.8 ? 'danger' : 'warn'"
                  />
                </template>
              </Column>
            </DataTable>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ProgressSpinner from 'primevue/progressspinner'
import { useCollectionsStore } from '@/stores/collections'
import { useAlertUtils } from '@/composables/useAlertUtils'
import type { CrossBookInconsistency, EventContradiction } from '@/types'

const props = defineProps<{
  collectionId: number
}>()

const toast = useToast()
const collectionsStore = useCollectionsStore()
const { translateAttributeName } = useAlertUtils()

const analyzingAttributes = ref(false)
const analyzingEvents = ref(false)

const report = computed(() => collectionsStore.crossBookReport)
const eventReport = computed(() => collectionsStore.crossBookEventReport)

const groupedInconsistencies = computed(() => {
  if (!report.value) return {}
  const groups: Record<string, CrossBookInconsistency[]> = {}
  for (const inc of report.value.inconsistencies) {
    if (!groups[inc.entityName]) groups[inc.entityName] = []
    groups[inc.entityName].push(inc)
  }
  return groups
})

const groupedContradictions = computed(() => {
  if (!eventReport.value) return {}
  const groups: Record<string, EventContradiction[]> = {}
  for (const c of eventReport.value.contradictions) {
    if (!groups[c.entityName]) groups[c.entityName] = []
    groups[c.entityName].push(c)
  }
  return groups
})

const TYPE_TRANSLATIONS: Record<string, string> = {
  physical: 'Físico',
  psychological: 'Psicológico',
  social: 'Social',
  biographical: 'Biográfico',
  location: 'Ubicación',
  object: 'Objeto',
}

const RULE_TRANSLATIONS: Record<string, string> = {
  death_then_alive: 'Muerte y reaparición',
  injury_healed_differently: 'Herida inconsistente',
  acquisition_vs_loss: 'Objeto sin continuidad',
  location_impossibility: 'Ubicación imposible',
}

function translateType(type: string): string {
  return TYPE_TRANSLATIONS[type] || type
}

function translateRule(rule: string): string {
  return RULE_TRANSLATIONS[rule] || rule.replace(/_/g, ' ')
}

function translateAttribute(key: string): string {
  return translateAttributeName(key)
}

async function runAttributeAnalysis() {
  analyzingAttributes.value = true
  try {
    await collectionsStore.fetchCrossBookAnalysis(props.collectionId)
    if (report.value?.summary.totalInconsistencies === 0) {
      toast.add({ severity: 'success', summary: 'Sin inconsistencias', detail: 'Todos los atributos son consistentes', life: 3000 })
    }
  } catch {
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo ejecutar el análisis de atributos', life: 5000 })
  } finally {
    analyzingAttributes.value = false
  }
}

async function runEventAnalysis() {
  analyzingEvents.value = true
  try {
    await collectionsStore.fetchCrossBookEventAnalysis(props.collectionId)
    if (eventReport.value?.summary.totalContradictions === 0) {
      toast.add({ severity: 'success', summary: 'Sin contradicciones', detail: 'No se encontraron contradicciones de eventos', life: 3000 })
    }
  } catch {
    toast.add({ severity: 'error', summary: 'Error', detail: 'No se pudo ejecutar el análisis de eventos', life: 5000 })
  } finally {
    analyzingEvents.value = false
  }
}
</script>

<style scoped>
.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.report-header h3 {
  margin: 0;
  font-size: 1rem;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
}

.section-title {
  font-size: 0.9rem;
  font-weight: 700;
  margin: 0 0 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--surface-border);
}

.section-title--events {
  margin-top: 2rem;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 2rem;
  color: var(--text-color-secondary);
}

.report-summary {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.summary-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1rem 1.5rem;
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  background: var(--surface-card);
  min-width: 120px;
}

.summary-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--primary-color);
}

.summary-value.has-issues {
  color: var(--orange-500);
}

.summary-label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  text-transform: uppercase;
  font-weight: 600;
  margin-top: 0.25rem;
}

.type-breakdown {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 1.5rem;
}

.success-state {
  text-align: center;
  padding: 2rem;
}

.success-icon {
  font-size: 3rem;
  color: var(--green-500);
}

.success-state p {
  margin-top: 0.75rem;
  color: var(--text-color-secondary);
}

.inconsistencies {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.entity-group {
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  overflow: hidden;
}

.entity-group--events {
  border-color: var(--red-200);
}

.entity-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: var(--surface-50);
  border-bottom: 1px solid var(--surface-border);
}

.entity-header i {
  color: var(--primary-color);
}

.entity-name {
  font-weight: 700;
  flex: 1;
}

.attr-cell {
  display: flex;
  flex-direction: column;
}

.attr-key {
  font-weight: 600;
}

.attr-type {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.value-cell {
  display: flex;
  flex-direction: column;
}

.value-text {
  font-weight: 600;
}

.value-a {
  color: var(--blue-600);
}

.value-b {
  color: var(--orange-600);
}

.book-name {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.empty-state {
  text-align: center;
  padding: 2.5rem 2rem;
}

.empty-icon {
  font-size: 2.5rem;
  color: var(--text-color-secondary);
  opacity: 0.3;
}

.empty-state p {
  margin: 0.5rem 0 0;
  color: var(--text-color-secondary);
}

.hint {
  font-size: 0.8125rem;
  opacity: 0.7;
}
</style>
