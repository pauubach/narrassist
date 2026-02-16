<script setup lang="ts">
/**
 * CharacterProfileModal - Modal unificado de perfil de personaje.
 *
 * Muestra los 6 indicadores del character profiling:
 * presencia, acciones, habla, definición, sentimiento y entorno.
 * Carga datos desde GET /api/projects/{projectId}/character-profiles.
 */
import { ref, computed, watch } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Badge from 'primevue/badge'
import Tag from 'primevue/tag'
import Chart from 'primevue/chart'
import type { Entity } from '@/types'
import { useEntityUtils } from '@/composables/useEntityUtils'
import { api } from '@/services/apiClient'

interface PresenceData {
  totalMentions: number
  chaptersPresent: number[]
  firstChapter: number
  lastChapter: number
  continuity: number
  mentionsPerChapter: Record<number, number>
}

interface ActionData {
  count: number
  topVerbs: [string, number][]
  physical: number
  verbal: number
  mental: number
  social: number
  agency: number
}

interface SpeechData {
  interventions: number
  words: number
  avgLength: number
  formality: number
}

interface DefinitionData {
  physical: Record<string, string>
  psychological: Record<string, string>
  social: Record<string, string>
  totalAttributes: number
}

interface SentimentData {
  avg: number
  positive: number
  negative: number
  dominantEmotions: [string, number][]
  byChapter: Record<number, number>
}

interface EnvironmentData {
  primaryLocation: string
  locations: [string, number][]
  changes: number
  locationsByChapter: Record<number, string[]>
}

interface CharacterProfile {
  entityId: number
  entityName: string
  role: string
  narrativeRelevance: number
  presence: PresenceData
  actions: ActionData
  speech: SpeechData
  definition: DefinitionData
  sentiment: SentimentData
  environment: EnvironmentData
}

const props = defineProps<{
  entity: Entity | null
  visible: boolean
  projectId: number
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
}>()

const { getEntityIcon, getEntityColor } = useEntityUtils()

const loading = ref(false)
const profile = ref<CharacterProfile | null>(null)

const entityIcon = computed(() => props.entity ? getEntityIcon(props.entity.type) : 'pi-circle')
const entityColor = computed(() => props.entity ? getEntityColor(props.entity.type) : '#888')

const roleLabels: Record<string, string> = {
  protagonist: 'Protagonista',
  deuteragonist: 'Deuteragonista',
  supporting: 'Secundario',
  minor: 'Menor',
  mentioned: 'Mencionado',
}

const roleLabel = computed(() => {
  if (!profile.value) return ''
  return roleLabels[profile.value.role] || profile.value.role
})

const roleSeverity = computed(() => {
  if (!profile.value) return 'secondary' as const
  const map: Record<string, 'success' | 'info' | 'warn' | 'secondary'> = {
    protagonist: 'success',
    deuteragonist: 'info',
    supporting: 'warn',
    minor: 'secondary',
    mentioned: 'secondary',
  }
  return map[profile.value.role] || ('secondary' as const)
})

const relevancePercent = computed(() =>
  profile.value ? Math.round(profile.value.narrativeRelevance * 100) : 0
)

const sentimentLabel = computed(() => {
  if (!profile.value) return ''
  const avg = profile.value.sentiment.avg
  if (avg > 0.3) return 'Positivo'
  if (avg < -0.3) return 'Negativo'
  return 'Neutro'
})

const sentimentColor = computed(() => {
  if (!profile.value) return 'secondary' as const
  const avg = profile.value.sentiment.avg
  if (avg > 0.3) return 'success' as const
  if (avg < -0.3) return 'danger' as const
  return 'secondary' as const
})

function transformProfile(raw: any): CharacterProfile {
  return {
    entityId: raw.entity_id,
    entityName: raw.entity_name,
    role: raw.role ?? 'minor',
    narrativeRelevance: raw.narrative_relevance ?? 0,
    presence: {
      totalMentions: raw.presence?.total_mentions ?? 0,
      chaptersPresent: raw.presence?.chapters_present ?? [],
      firstChapter: raw.presence?.first_chapter ?? 0,
      lastChapter: raw.presence?.last_chapter ?? 0,
      continuity: raw.presence?.continuity ?? 0,
      mentionsPerChapter: raw.presence?.mentions_per_chapter ?? {},
    },
    actions: {
      count: raw.actions?.count ?? 0,
      topVerbs: raw.actions?.top_verbs ?? [],
      physical: raw.actions?.physical ?? 0,
      verbal: raw.actions?.verbal ?? 0,
      mental: raw.actions?.mental ?? 0,
      social: raw.actions?.social ?? 0,
      agency: raw.actions?.agency ?? 0,
    },
    speech: {
      interventions: raw.speech?.interventions ?? 0,
      words: raw.speech?.words ?? 0,
      avgLength: raw.speech?.avg_length ?? 0,
      formality: raw.speech?.formality ?? 0,
    },
    definition: {
      physical: raw.definition?.physical ?? {},
      psychological: raw.definition?.psychological ?? {},
      social: raw.definition?.social ?? {},
      totalAttributes: raw.definition?.total_attributes ?? 0,
    },
    sentiment: {
      avg: raw.sentiment?.avg ?? 0,
      positive: raw.sentiment?.positive ?? 0,
      negative: raw.sentiment?.negative ?? 0,
      dominantEmotions: raw.sentiment?.dominant_emotions ?? [],
      byChapter: raw.sentiment?.by_chapter ?? {},
    },
    environment: {
      primaryLocation: raw.environment?.primary_location ?? '',
      locations: raw.environment?.locations ?? [],
      changes: raw.environment?.changes ?? 0,
      locationsByChapter: raw.environment?.locations_by_chapter ?? {},
    },
  }
}

async function loadProfile() {
  if (!props.entity) return
  loading.value = true
  profile.value = null
  try {
    const data = await api.getRaw<any>(
      `/api/projects/${props.projectId}/character-profiles`
    )
    if (data.success && data.data?.profiles) {
      const match = data.data.profiles.find(
        (p: any) => p.entity_id === props.entity!.id
      )
      if (match) {
        profile.value = transformProfile(match)
      }
    }
  } catch {
    // Best effort
  } finally {
    loading.value = false
  }
}

watch(
  () => props.visible,
  (val) => {
    if (val && props.entity) loadProfile()
  }
)

function close() {
  emit('update:visible', false)
}

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`
}

// --- Charts: evolución temporal ---

const sortedChapters = computed(() => {
  if (!profile.value) return []
  return Object.keys(profile.value.presence.mentionsPerChapter)
    .map(Number)
    .sort((a, b) => a - b)
})

const hasTemporalData = computed(() => sortedChapters.value.length >= 2)

const presenceChartData = computed(() => {
  if (!profile.value || !hasTemporalData.value) return null
  const mpc = profile.value.presence.mentionsPerChapter
  const primaryColor = getComputedStyle(document.documentElement).getPropertyValue('--p-primary-color').trim() || '#3B82F6'
  return {
    labels: sortedChapters.value.map(ch => `Cap ${ch}`),
    datasets: [{
      label: 'Menciones',
      data: sortedChapters.value.map(ch => mpc[ch] ?? 0),
      borderColor: primaryColor,
      backgroundColor: primaryColor + '1a',
      fill: true,
      tension: 0.3,
      pointRadius: 3,
    }],
  }
})

const sentimentChartData = computed(() => {
  if (!profile.value || !hasTemporalData.value) return null
  const sbc = profile.value.sentiment.byChapter
  const chapters = sortedChapters.value.filter(ch => sbc[ch] !== undefined)
  if (chapters.length < 2) return null
  return {
    labels: chapters.map(ch => `Cap ${ch}`),
    datasets: [{
      label: 'Sentimiento',
      data: chapters.map(ch => sbc[ch]),
      borderColor: 'rgb(34, 197, 94)',
      backgroundColor: (ctx: any) => {
        if (!ctx.chart?.chartArea) return 'rgba(34,197,94,0.1)'
        const { top, bottom } = ctx.chart.chartArea
        const gradient = ctx.chart.ctx.createLinearGradient(0, top, 0, bottom)
        gradient.addColorStop(0, 'rgba(34, 197, 94, 0.3)')
        gradient.addColorStop(0.5, 'rgba(200, 200, 200, 0.05)')
        gradient.addColorStop(1, 'rgba(239, 68, 68, 0.3)')
        return gradient
      },
      fill: true,
      tension: 0.3,
      pointRadius: 3,
    }],
  }
})

const miniChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        title: (items: any[]) => items[0]?.label ?? '',
      },
    },
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { font: { size: 10 }, maxRotation: 0 },
    },
    y: {
      grid: { color: 'rgba(0,0,0,0.05)' },
      ticks: { font: { size: 10 } },
      beginAtZero: true,
    },
  },
}

const sentimentChartOptions = {
  ...miniChartOptions,
  scales: {
    ...miniChartOptions.scales,
    y: {
      ...miniChartOptions.scales.y,
      min: -1,
      max: 1,
      ticks: { font: { size: 10 }, stepSize: 0.5 },
    },
  },
}

// --- Transiciones de ubicación ---

interface LocationTransition {
  location: string
  fromChapter: number
  toChapter: number
}

const locationTransitions = computed<LocationTransition[]>(() => {
  if (!profile.value) return []
  const lbc = profile.value.environment.locationsByChapter
  const chapters = Object.keys(lbc).map(Number).sort((a, b) => a - b)
  if (chapters.length === 0) return []

  const transitions: LocationTransition[] = []
  let currentLoc = lbc[chapters[0]]?.[0] ?? ''
  let fromCh = chapters[0]

  for (const ch of chapters.slice(1)) {
    const primary = lbc[ch]?.[0] ?? ''
    if (primary && primary !== currentLoc) {
      transitions.push({ location: currentLoc, fromChapter: fromCh, toChapter: ch - 1 })
      currentLoc = primary
      fromCh = ch
    }
  }
  // Último tramo
  if (currentLoc) {
    transitions.push({ location: currentLoc, fromChapter: fromCh, toChapter: chapters[chapters.length - 1] })
  }
  return transitions
})
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    :closable="true"
    :draggable="false"
    :style="{ width: '700px', maxWidth: '95vw' }"
    class="character-profile-modal"
    @update:visible="emit('update:visible', $event)"
  >
    <template #header>
      <div class="modal-header">
        <div class="entity-icon" :style="{ backgroundColor: entityColor }">
          <i :class="['pi', entityIcon]"></i>
        </div>
        <div class="header-content">
          <h2>{{ entity?.name }}</h2>
          <div class="header-meta">
            <Tag v-if="profile" :value="roleLabel" :severity="roleSeverity" />
            <span v-if="profile" class="relevance">
              Relevancia: {{ relevancePercent }}%
            </span>
          </div>
        </div>
      </div>
    </template>

    <div v-if="loading" class="loading-state">
      <i class="pi pi-spin pi-spinner"></i>
      <span>Cargando perfil...</span>
    </div>

    <div v-else-if="profile" class="modal-body">
      <!-- Presencia -->
      <section class="indicator">
        <h3><i class="pi pi-eye"></i> Presencia</h3>
        <div class="stats-grid">
          <div class="stat-card">
            <span class="stat-value">{{ profile.presence.totalMentions }}</span>
            <span class="stat-label">Menciones</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">{{ profile.presence.chaptersPresent.length }}</span>
            <span class="stat-label">Capítulos</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">{{ formatPercent(profile.presence.continuity) }}</span>
            <span class="stat-label">Continuidad</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">{{ profile.presence.firstChapter }}–{{ profile.presence.lastChapter }}</span>
            <span class="stat-label">Rango caps.</span>
          </div>
        </div>
        <div v-if="presenceChartData" class="chart-container">
          <Chart type="line" :data="presenceChartData" :options="miniChartOptions" />
        </div>
      </section>

      <!-- Acciones -->
      <section v-if="profile.actions.count > 0" class="indicator">
        <h3><i class="pi pi-bolt"></i> Acciones</h3>
        <div class="stats-grid">
          <div class="stat-card">
            <span class="stat-value">{{ profile.actions.count }}</span>
            <span class="stat-label">Total</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">{{ formatPercent(profile.actions.agency) }}</span>
            <span class="stat-label">Agentividad</span>
          </div>
        </div>
        <div class="action-categories">
          <span class="action-cat"><i class="pi pi-directions"></i> Físicas: {{ profile.actions.physical }}</span>
          <span class="action-cat"><i class="pi pi-comments"></i> Verbales: {{ profile.actions.verbal }}</span>
          <span class="action-cat"><i class="pi pi-brain"></i> Mentales: {{ profile.actions.mental }}</span>
          <span class="action-cat"><i class="pi pi-users"></i> Sociales: {{ profile.actions.social }}</span>
        </div>
        <div v-if="profile.actions.topVerbs.length > 0" class="top-verbs">
          <span class="detail-label">Verbos frecuentes:</span>
          <span v-for="([verb, count]) in profile.actions.topVerbs.slice(0, 5)" :key="verb" class="verb-tag">
            {{ verb }} ({{ count }})
          </span>
        </div>
      </section>

      <!-- Habla -->
      <section v-if="profile.speech.interventions > 0" class="indicator">
        <h3><i class="pi pi-comments"></i> Habla</h3>
        <div class="stats-grid">
          <div class="stat-card">
            <span class="stat-value">{{ profile.speech.interventions }}</span>
            <span class="stat-label">Intervenciones</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">{{ profile.speech.words.toLocaleString() }}</span>
            <span class="stat-label">Palabras</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">{{ Math.round(profile.speech.avgLength) }}</span>
            <span class="stat-label">Largo medio</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">{{ formatPercent(profile.speech.formality) }}</span>
            <span class="stat-label">Formalidad</span>
          </div>
        </div>
      </section>

      <!-- Definición (atributos) -->
      <section v-if="profile.definition.totalAttributes > 0" class="indicator">
        <h3><i class="pi pi-id-card"></i> Definición ({{ profile.definition.totalAttributes }} atributos)</h3>
        <div class="attribute-groups">
          <div v-if="Object.keys(profile.definition.physical).length > 0" class="attr-group">
            <span class="attr-group-label">Físicos</span>
            <div class="attr-list">
              <span v-for="(val, key) in profile.definition.physical" :key="key" class="attr-tag">
                {{ key }}: {{ val }}
              </span>
            </div>
          </div>
          <div v-if="Object.keys(profile.definition.psychological).length > 0" class="attr-group">
            <span class="attr-group-label">Psicológicos</span>
            <div class="attr-list">
              <span v-for="(val, key) in profile.definition.psychological" :key="key" class="attr-tag">
                {{ key }}: {{ val }}
              </span>
            </div>
          </div>
          <div v-if="Object.keys(profile.definition.social).length > 0" class="attr-group">
            <span class="attr-group-label">Sociales</span>
            <div class="attr-list">
              <span v-for="(val, key) in profile.definition.social" :key="key" class="attr-tag">
                {{ key }}: {{ val }}
              </span>
            </div>
          </div>
        </div>
      </section>

      <!-- Sentimiento -->
      <section class="indicator">
        <h3><i class="pi pi-heart"></i> Sentimiento</h3>
        <div class="stats-grid">
          <div class="stat-card">
            <Badge :value="sentimentLabel" :severity="sentimentColor" />
            <span class="stat-label">Tono general</span>
          </div>
          <div class="stat-card">
            <span class="stat-value positive">{{ profile.sentiment.positive }}</span>
            <span class="stat-label">Positivas</span>
          </div>
          <div class="stat-card">
            <span class="stat-value negative">{{ profile.sentiment.negative }}</span>
            <span class="stat-label">Negativas</span>
          </div>
        </div>
        <div v-if="profile.sentiment.dominantEmotions.length > 0" class="emotions">
          <span class="detail-label">Emociones dominantes:</span>
          <span v-for="([emotion, count]) in profile.sentiment.dominantEmotions.slice(0, 4)" :key="emotion" class="verb-tag">
            {{ emotion }} ({{ count }})
          </span>
        </div>
        <div v-if="sentimentChartData" class="chart-container">
          <Chart type="line" :data="sentimentChartData" :options="sentimentChartOptions" />
        </div>
      </section>

      <!-- Entorno -->
      <section v-if="profile.environment.primaryLocation" class="indicator">
        <h3><i class="pi pi-map-marker"></i> Entorno</h3>
        <div class="stats-grid">
          <div class="stat-card">
            <span class="stat-value">{{ profile.environment.primaryLocation }}</span>
            <span class="stat-label">Ubicación principal</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">{{ profile.environment.changes }}</span>
            <span class="stat-label">Cambios</span>
          </div>
        </div>
        <div v-if="profile.environment.locations.length > 1" class="locations">
          <span class="detail-label">Ubicaciones:</span>
          <span v-for="([loc, count]) in profile.environment.locations.slice(0, 5)" :key="loc" class="verb-tag">
            {{ loc }} ({{ count }})
          </span>
        </div>
        <div v-if="locationTransitions.length > 1" class="location-transitions">
          <span class="detail-label">Recorrido:</span>
          <div class="transition-flow">
            <!-- eslint-disable-next-line vue/no-v-for-template-key -->
            <template v-for="(t, idx) in locationTransitions" :key="idx">
              <span class="transition-step">
                <span class="transition-location">{{ t.location }}</span>
                <span class="transition-range">Cap {{ t.fromChapter === t.toChapter ? t.fromChapter : `${t.fromChapter}–${t.toChapter}` }}</span>
              </span>
              <i v-if="idx < locationTransitions.length - 1" class="pi pi-arrow-right transition-arrow"></i>
            </template>
          </div>
        </div>
      </section>
    </div>

    <div v-else class="empty-state">
      <i class="pi pi-info-circle"></i>
      <p>No hay datos de perfil disponibles para este personaje.</p>
      <p class="empty-hint">Ejecuta el análisis completo para generar perfiles.</p>
    </div>

    <template #footer>
      <Button label="Cerrar" @click="close" />
    </template>
  </Dialog>
</template>

<style scoped>
.modal-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-4);
}

.entity-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--ds-radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1.5rem;
  flex-shrink: 0;
}

.header-content {
  flex: 1;
}

.header-content h2 {
  margin: 0;
  font-size: var(--ds-font-size-xl);
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-text);
}

.header-meta {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
  margin-top: var(--ds-space-1);
}

.relevance {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--ds-space-3);
  padding: var(--ds-space-8);
  color: var(--ds-color-text-secondary);
}

.loading-state i {
  font-size: 2rem;
  color: var(--ds-color-primary);
}

.modal-body {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-5);
}

.indicator {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3);
}

.indicator h3 {
  margin: 0;
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-text-secondary);
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  border-bottom: 1px solid var(--ds-surface-border, #e2e8f0);
  padding-bottom: var(--ds-space-2);
}

.indicator h3 i {
  font-size: 0.875rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  gap: var(--ds-space-3);
}

.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--ds-space-3);
  background: var(--ds-surface-section, var(--ds-surface-50, #f8fafc));
  border-radius: var(--ds-radius-md);
}

.stat-value {
  font-size: var(--ds-font-size-lg);
  font-weight: var(--ds-font-weight-bold);
  color: var(--ds-color-primary);
}

.stat-value.positive {
  color: var(--ds-color-success, #22c55e);
}

.stat-value.negative {
  color: var(--ds-color-danger, #ef4444);
}

.stat-label {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  text-align: center;
}

.action-categories {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-3);
}

.action-cat {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
}

.action-cat i {
  font-size: 0.75rem;
  color: var(--ds-color-text-secondary);
}

.top-verbs,
.emotions,
.locations {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--ds-space-2);
}

.detail-label {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
  font-weight: 500;
}

.verb-tag {
  font-size: var(--ds-font-size-sm);
  background: var(--ds-surface-hover, #f1f5f9);
  padding: var(--ds-space-1) var(--ds-space-2);
  border-radius: var(--ds-radius-sm);
  color: var(--ds-color-text);
}

.attribute-groups {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3);
}

.attr-group {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-1);
}

.attr-group-label {
  font-size: var(--ds-font-size-xs);
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.attr-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-2);
}

.attr-tag {
  font-size: var(--ds-font-size-sm);
  background: var(--ds-surface-hover, #f1f5f9);
  padding: var(--ds-space-1) var(--ds-space-2);
  border-radius: var(--ds-radius-sm);
  color: var(--ds-color-text);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-8);
  text-align: center;
}

.empty-state i {
  font-size: 2rem;
  color: var(--ds-color-text-secondary);
  opacity: 0.5;
}

.empty-state p {
  margin: 0;
  color: var(--ds-color-text-secondary);
}

.empty-hint {
  font-size: var(--ds-font-size-sm);
  opacity: 0.7;
}

/* Charts */
.chart-container {
  height: 180px;
  margin-top: var(--ds-space-2);
}

/* Location transitions */
.location-transitions {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
  margin-top: var(--ds-space-2);
}

.transition-flow {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--ds-space-2);
}

.transition-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--ds-space-2) var(--ds-space-3);
  background: var(--ds-surface-hover, #f1f5f9);
  border-radius: var(--ds-radius-md);
}

.transition-location {
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-text);
}

.transition-range {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.transition-arrow {
  font-size: 0.75rem;
  color: var(--ds-color-text-secondary);
}
</style>
