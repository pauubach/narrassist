<template>
  <div class="chapter-progress-tab">
    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <ProgressSpinner />
      <p>{{ loadingMessage }}</p>
    </div>

    <!-- Error State -->
    <Message v-else-if="error" severity="error" :closable="false">
      {{ error }}
    </Message>

    <!-- Empty State -->
    <div v-else-if="!report || report.total_chapters === 0" class="empty-state">
      <i class="pi pi-book"></i>
      <h3>Sin datos de capítulos</h3>
      <p>Ejecuta el análisis del documento para ver el resumen de avance narrativo.</p>
    </div>

    <!-- Report Content -->
    <div v-else class="report-content">
      <!-- Mode Selector & Stats Header -->
      <div class="header-section">
        <Card class="mode-card">
          <template #content>
            <div class="mode-selector">
              <label>Modo de análisis:</label>
              <Select
                v-model="selectedMode"
                :options="analysisModesOptions"
                option-label="label"
                option-value="value"
                class="mode-dropdown"
                @change="loadReport"
              />
              <Button
                v-tooltip.top="'Recargar análisis'"
                icon="pi pi-refresh"
                :loading="loading"
                text
                rounded
                @click="loadReport"
              />
            </div>
            <small class="mode-description">{{ modeDescription }}</small>
          </template>
        </Card>

        <Card class="stats-card">
          <template #content>
            <div class="stats-grid">
              <div class="stat-item">
                <span class="stat-value">{{ report.total_chapters }}</span>
                <span class="stat-label">Capítulos</span>
              </div>
              <div class="stat-item">
                <span class="stat-value">{{ report.total_characters }}</span>
                <span class="stat-label">Personajes</span>
              </div>
              <div class="stat-item">
                <span class="stat-value">{{ report.active_characters }}</span>
                <span class="stat-label">Activos</span>
              </div>
              <div v-if="report.chekhov_elements?.length" class="stat-item">
                <span class="stat-value warning">{{ report.chekhov_elements.length }}</span>
                <span class="stat-label">Objetos sin resolver</span>
              </div>
            </div>
          </template>
        </Card>
      </div>

      <!-- Alerts Section -->
      <div v-if="hasAlerts" class="alerts-section">
        <!-- Dormant Characters -->
        <Message v-if="report.dormant_characters?.length" severity="warn" :closable="false">
          <div class="alert-content">
            <strong>Personajes dormidos:</strong>
            {{ report.dormant_characters.join(', ') }}
            <small>(sin aparecer en los últimos 3 capítulos)</small>
          </div>
        </Message>

        <!-- Abandoned Threads -->
        <Message v-if="report.abandoned_threads?.length" severity="warn" :closable="false">
          <div class="alert-content">
            <strong>{{ report.abandoned_threads.length }} posibles tramas abandonadas</strong>
            <small>(ver detalles abajo)</small>
          </div>
        </Message>

        <!-- Chekhov's Guns -->
        <Message v-if="report.chekhov_elements?.length" severity="info" :closable="false">
          <div class="alert-content">
            <strong>{{ report.chekhov_elements.length }} objetos introducidos sin payoff claro</strong>
            <small>(Chekhov's Guns)</small>
          </div>
        </Message>
      </div>

      <!-- Tabs for different views -->
      <Tabs value="0" class="progress-tabs">
        <TabList>
          <Tab value="0"><i class="pi pi-list"></i> Por capítulo</Tab>
          <Tab value="1"><i class="pi pi-chart-line"></i> Arcos de personajes</Tab>
          <Tab value="2"><i class="pi pi-bookmark"></i> Chekhov's Guns
            <Badge v-if="report.chekhov_elements?.length" :value="report.chekhov_elements.length" severity="warn" />
          </Tab>
          <Tab v-if="report.abandoned_threads?.length" value="3"><i class="pi pi-exclamation-circle"></i> Tramas abandonadas
            <Badge :value="report.abandoned_threads.length" severity="danger" />
          </Tab>
        </TabList>
        <TabPanels>
        <!-- Chapter Summaries Tab -->
        <TabPanel value="0">

          <Accordion :multiple="true" class="chapters-accordion">
            <AccordionPanel
              v-for="chapter in report.chapters"
              :key="chapter.chapter_number"
              :value="String(chapter.chapter_number)"
            >
              <AccordionHeader>
                <div class="chapter-header">
                  <span class="chapter-title">
                    <i class="pi pi-book"></i>
                    Capítulo {{ chapter.chapter_number }}
                    <span v-if="chapter.chapter_title" class="chapter-subtitle">
                      - {{ chapter.chapter_title }}
                    </span>
                  </span>
                  <div class="chapter-badges">
                    <Tag
                      v-if="chapter.new_characters?.length"
                      severity="success"
                      :value="`+${chapter.new_characters.length} nuevo${chapter.new_characters.length > 1 ? 's' : ''}`"
                    />
                    <Tag
                      v-if="chapter.returning_characters?.length"
                      severity="info"
                      :value="`${chapter.returning_characters.length} regresa${chapter.returning_characters.length > 1 ? 'n' : ''}`"
                    />
                    <Tag
                      :severity="getToneSeverity(chapter.dominant_tone)"
                      :value="getToneLabel(chapter.dominant_tone)"
                    />
                  </div>
                </div>
              </AccordionHeader>
              <AccordionContent>
                <div class="chapter-content">
                  <!-- Summary -->
                  <div class="chapter-summary">
                    <p class="auto-summary">{{ chapter.llm_summary || chapter.auto_summary }}</p>
                  </div>

                  <!-- Characters Present -->
                  <div v-if="chapter.characters_present?.length" class="section characters-section">
                    <h4><i class="pi pi-users"></i> Personajes ({{ chapter.characters_present.length }})</h4>
                    <div class="characters-grid">
                      <div
                        v-for="char in chapter.characters_present.slice(0, 8)"
                        :key="char.entity_id"
                        class="character-chip"
                        :class="{
                          'is-new': char.is_first_appearance,
                          'is-return': char.is_return,
                        }"
                      >
                        <span class="char-name">{{ char.name }}</span>
                        <span class="char-mentions">{{ char.mention_count }}</span>
                        <i v-if="char.is_first_appearance" v-tooltip.top="'Primera aparición'" class="pi pi-star"></i>
                        <i v-if="char.is_return" v-tooltip.top="`Regresa después de ${char.chapters_absent} capítulos`" class="pi pi-replay"></i>
                      </div>
                    </div>
                  </div>

                  <!-- Key Events -->
                  <div v-if="getAllEvents(chapter).length" class="section events-section">
                    <h4><i class="pi pi-bolt"></i> Eventos clave</h4>
                    <div class="events-list">
                      <div
                        v-for="(event, idx) in getAllEvents(chapter)"
                        :key="idx"
                        class="event-item"
                        :class="event.event_type"
                      >
                        <Tag
                          :severity="getEventSeverity(event.event_type)"
                          :value="getEventLabel(event.event_type)"
                          size="small"
                        />
                        <span class="event-description">{{ event.description }}</span>
                        <span v-if="event.characters_involved?.length" class="event-characters">
                          ({{ event.characters_involved.join(', ') }})
                        </span>
                        <Tag
                          v-if="event.detected_by === 'llm'"
                          severity="secondary"
                          value="LLM"
                          size="small"
                          class="llm-tag"
                        />
                      </div>
                    </div>
                  </div>

                  <!-- Interactions Summary -->
                  <div v-if="chapter.total_interactions > 0" class="section interactions-section">
                    <h4><i class="pi pi-comments"></i> Interacciones</h4>
                    <div class="interactions-stats">
                      <span>{{ chapter.total_interactions }} totales</span>
                      <span v-if="chapter.positive_interactions" class="positive">
                        <i class="pi pi-heart"></i> {{ chapter.positive_interactions }} positivas
                      </span>
                      <span v-if="chapter.conflict_interactions" class="negative">
                        <i class="pi pi-exclamation-triangle"></i> {{ chapter.conflict_interactions }} conflictivas
                      </span>
                    </div>
                  </div>

                  <!-- Locations -->
                  <div v-if="chapter.locations_mentioned?.length" class="section locations-section">
                    <h4><i class="pi pi-map-marker"></i> Ubicaciones</h4>
                    <div class="locations-list">
                      <Tag
                        v-for="loc in chapter.locations_mentioned"
                        :key="loc"
                        :value="loc"
                        severity="secondary"
                      />
                    </div>
                  </div>

                  <!-- Absent Characters -->
                  <div v-if="chapter.absent_characters?.length" class="section absent-section">
                    <h4><i class="pi pi-eye-slash"></i> Personajes ausentes</h4>
                    <p class="absent-list">{{ chapter.absent_characters.join(', ') }}</p>
                  </div>
                </div>
              </AccordionContent>
            </AccordionPanel>
          </Accordion>
        </TabPanel>

        <!-- Character Arcs Tab -->
        <TabPanel value="1">

          <div v-if="report.character_arcs?.length" class="arcs-content">
            <div
              v-for="arc in report.character_arcs"
              :key="arc.character_id"
              class="arc-card"
            >
              <div class="arc-header">
                <span class="arc-character">{{ arc.character_name }}</span>
                <Tag
                  :severity="getArcSeverity(arc.arc_type)"
                  :value="getArcLabel(arc.arc_type)"
                />
                <Tag
                  :severity="getTrajectoryColor(arc.trajectory)"
                  :value="getTrajectoryLabel(arc.trajectory)"
                  size="small"
                />
              </div>

              <div class="arc-details">
                <div v-if="arc.start_state || arc.end_state" class="arc-states">
                  <div v-if="arc.start_state" class="state start">
                    <label>Estado inicial:</label>
                    <span>{{ arc.start_state }}</span>
                  </div>
                  <i class="pi pi-arrow-right"></i>
                  <div v-if="arc.end_state" class="state end">
                    <label>Estado final:</label>
                    <span>{{ arc.end_state }}</span>
                  </div>
                </div>

                <div class="arc-stats">
                  <span><i class="pi pi-book"></i> {{ arc.chapters_present }} capítulos</span>
                  <span><i class="pi pi-comment"></i> {{ arc.total_mentions }} menciones</span>
                  <span v-if="arc.max_absence_gap > 0">
                    <i class="pi pi-clock"></i> Max {{ arc.max_absence_gap }} caps ausente
                  </span>
                </div>

                <div v-if="arc.key_turning_points?.length" class="turning-points">
                  <h5>Puntos de giro:</h5>
                  <ul>
                    <li v-for="(point, idx) in arc.key_turning_points" :key="idx">
                      <strong>Cap. {{ point.chapter }}:</strong> {{ point.event }}
                    </li>
                  </ul>
                </div>

                <div v-if="arc.completeness > 0" class="arc-completeness">
                  <label>Completitud del arco:</label>
                  <ProgressBar :value="arc.completeness * 100" :show-value="true" />
                </div>
              </div>
            </div>
          </div>
          <div v-else class="empty-tab">
            <p>No hay arcos de personajes detectados.</p>
            <small>Usa el modo "standard" o "deep" para análisis con LLM.</small>
          </div>
        </TabPanel>

        <!-- Chekhov's Guns Tab -->
        <TabPanel value="2">

          <div v-if="report.chekhov_elements?.length" class="chekhov-content">
            <Message severity="info" :closable="false" class="chekhov-info">
              <strong>Chekhov's Gun:</strong> "Si en el primer acto hay un rifle colgado en la pared,
              en el tercero debe dispararse." Estos son objetos introducidos temprano que podrían
              necesitar un "payoff" narrativo.
            </Message>

            <div
              v-for="element in report.chekhov_elements"
              :key="element.entity_id || element.name"
              class="chekhov-card"
              :class="{ 'is-fired': element.is_fired }"
            >
              <div class="chekhov-header">
                <span class="chekhov-name">{{ element.name }}</span>
                <Tag
                  :severity="element.is_fired ? 'success' : 'warn'"
                  :value="element.is_fired ? 'Con payoff' : 'Sin resolver'"
                />
              </div>
              <div class="chekhov-details">
                <p><strong>Introducido:</strong> Capítulo {{ element.setup_chapter }}</p>
                <p v-if="element.setup_context" class="context">
                  "{{ element.setup_context }}"
                </p>
                <p v-if="element.payoff_chapter">
                  <strong>Payoff:</strong> Capítulo {{ element.payoff_chapter }}
                </p>
                <p v-if="element.llm_analysis" class="llm-analysis">
                  <i class="pi pi-sparkles"></i> {{ element.llm_analysis }}
                </p>
              </div>
            </div>
          </div>
          <div v-else class="empty-tab">
            <i class="pi pi-check-circle"></i>
            <p>No se detectaron objetos narrativos sin resolver.</p>
          </div>
        </TabPanel>

        <!-- Abandoned Threads Tab -->
        <TabPanel v-if="report.abandoned_threads?.length" value="3">

          <div class="abandoned-content">
            <div
              v-for="(thread, idx) in report.abandoned_threads"
              :key="idx"
              class="thread-card"
            >
              <div class="thread-header">
                <span class="thread-description">{{ thread.description }}</span>
              </div>
              <div class="thread-details">
                <p>
                  <strong>Introducida:</strong> Capítulo {{ thread.introduced_chapter }}
                  <i class="pi pi-arrow-right"></i>
                  <strong>Última mención:</strong> Capítulo {{ thread.last_mention_chapter }}
                </p>
                <p v-if="thread.characters_involved?.length">
                  <strong>Personajes:</strong> {{ thread.characters_involved.join(', ') }}
                </p>
                <Message v-if="thread.suggestion" severity="info" :closable="false" class="suggestion">
                  <strong>Sugerencia:</strong> {{ thread.suggestion }}
                </Message>
              </div>
            </div>
          </div>
        </TabPanel>
        </TabPanels>
      </Tabs>

      <!-- Structural Notes -->
      <Card v-if="report.structural_notes" class="structural-notes-card">
        <template #title>
          <i class="pi pi-info-circle"></i>
          Notas estructurales (LLM)
        </template>
        <template #content>
          <p>{{ report.structural_notes }}</p>
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Badge from 'primevue/badge'
import Message from 'primevue/message'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Accordion from 'primevue/accordion'
import AccordionPanel from 'primevue/accordionpanel'
import AccordionHeader from 'primevue/accordionheader'
import AccordionContent from 'primevue/accordioncontent'
import ProgressSpinner from 'primevue/progressspinner'
import ProgressBar from 'primevue/progressbar'
import { useToast } from 'primevue/usetoast'
import { api } from '@/services/apiClient'

interface NarrativeEvent {
  event_type: string
  description: string
  characters_involved: string[]
  chapter_number: number
  position: number
  confidence: number
  source_text: string
  detected_by: string
}

interface CharacterPresence {
  entity_id: number
  name: string
  mention_count: number
  is_first_appearance: boolean
  is_return: boolean
  chapters_absent: number
  dialogues_count: number
  actions_count: number
  interactions_with: string[]
}

interface ChapterSummary {
  chapter_number: number
  chapter_title: string | null
  word_count: number
  characters_present: CharacterPresence[]
  new_characters: string[]
  returning_characters: string[]
  absent_characters: string[]
  key_events: NarrativeEvent[]
  llm_events: NarrativeEvent[]
  total_interactions: number
  conflict_interactions: number
  positive_interactions: number
  dominant_tone: string
  tone_intensity: number
  locations_mentioned: string[]
  auto_summary: string
  llm_summary: string | null
}

interface CharacterArc {
  character_id: number
  character_name: string
  arc_type: string
  start_state: string
  end_state: string
  key_turning_points: Array<{ chapter: number; event: string }>
  completeness: number
  chapters_present: number
  total_mentions: number
  max_absence_gap: number
  trajectory: string
}

interface ChekhovElement {
  entity_id: number | null
  name: string
  element_type: string
  setup_chapter: number
  setup_context: string
  payoff_chapter: number | null
  is_fired: boolean
  llm_analysis: string | null
}

interface AbandonedThread {
  description: string
  introduced_chapter: number
  last_mention_chapter: number
  characters_involved: string[]
  suggestion: string | null
}

interface ChapterProgressReport {
  project_id: number
  analysis_mode: string
  total_chapters: number
  chapters: ChapterSummary[]
  total_characters: number
  active_characters: number
  dormant_characters: string[]
  character_arcs: CharacterArc[]
  chekhov_elements: ChekhovElement[]
  abandoned_threads: AbandonedThread[]
  structural_notes: string | null
}

const props = defineProps<{
  projectId: number
}>()

const _toast = useToast()

const loading = ref(false)
const loadingMessage = ref('Cargando análisis...')
const error = ref<string | null>(null)
const report = ref<ChapterProgressReport | null>(null)
const selectedMode = ref('basic')

const analysisModesOptions = [
  { label: 'Básico (rápido)', value: 'basic' },
  { label: 'Estándar (con LLM)', value: 'standard' },
  { label: 'Profundo (multi-modelo)', value: 'deep' },
]

const modeDescription = computed(() => {
  switch (selectedMode.value) {
    case 'basic':
      return 'Análisis de patrones sin LLM. Rápido pero limitado.'
    case 'standard':
      return 'Análisis con IA. Equilibrio entre velocidad y calidad.'
    case 'deep':
      return 'Análisis multi-modelo con votación. Más preciso pero más lento.'
    default:
      return ''
  }
})

const hasAlerts = computed(() => {
  if (!report.value) return false
  return (
    report.value.dormant_characters?.length > 0 ||
    report.value.abandoned_threads?.length > 0 ||
    report.value.chekhov_elements?.length > 0
  )
})

async function loadReport() {
  loading.value = true
  error.value = null
  loadingMessage.value = selectedMode.value === 'basic'
    ? 'Analizando patrones...'
    : 'Analizando con LLM (puede tardar)...'

  try {
    const data = await api.getRaw<{ success: boolean; data: ChapterProgressReport; error?: string }>(
      `/api/projects/${props.projectId}/chapter-progress?mode=${selectedMode.value}`
    )

    if (data.success) {
      report.value = data.data
    } else {
      error.value = data.error || 'Error al cargar el análisis'
    }
  } catch (err) {
    console.error('Error loading chapter progress:', err)
    error.value = 'No se pudo cargar el análisis de progreso. Recarga la página si persiste.'
  } finally {
    loading.value = false
  }
}

function getAllEvents(chapter: ChapterSummary): NarrativeEvent[] {
  const events = [...(chapter.key_events || []), ...(chapter.llm_events || [])]
  // Deduplicar por descripción similar
  const seen = new Set<string>()
  return events.filter(e => {
    const key = e.description.toLowerCase().substring(0, 30)
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function getToneSeverity(tone: string): 'success' | 'info' | 'warn' | 'danger' | 'secondary' {
  switch (tone) {
    case 'positive': return 'success'
    case 'tense': return 'warn'
    case 'negative': return 'danger'
    default: return 'secondary'
  }
}

function getToneLabel(tone: string): string {
  const labels: Record<string, string> = {
    positive: 'Positivo',
    tense: 'Tenso',
    negative: 'Negativo',
    neutral: 'Neutro',
  }
  return labels[tone] || tone
}

function getEventSeverity(eventType: string): 'success' | 'info' | 'warn' | 'danger' | 'secondary' {
  const severities: Record<string, 'success' | 'info' | 'warn' | 'danger' | 'secondary'> = {
    first_appearance: 'success',
    return: 'info',
    death: 'danger',
    conflict: 'warn',
    revelation: 'info',
    decision: 'info',
    betrayal: 'danger',
    transformation: 'success',
    plot_twist: 'warn',
    climax_moment: 'danger',
    resolution: 'success',
  }
  return severities[eventType] || 'secondary'
}

function getEventLabel(eventType: string): string {
  const labels: Record<string, string> = {
    first_appearance: 'Nueva aparición',
    return: 'Regreso',
    death: 'Muerte',
    departure: 'Partida',
    conflict: 'Conflicto',
    alliance: 'Alianza',
    emotional_shift: 'Cambio emocional',
    location_change: 'Cambio lugar',
    new_relationship: 'Nueva relación',
    decision: 'Decisión',
    discovery: 'Descubrimiento',
    revelation: 'Revelación',
    betrayal: 'Traición',
    sacrifice: 'Sacrificio',
    transformation: 'Transformación',
    plot_twist: 'Giro',
    climax_moment: 'Clímax',
    resolution: 'Resolución',
  }
  return labels[eventType] || eventType
}

function getArcSeverity(arcType: string): 'success' | 'info' | 'warn' | 'danger' | 'secondary' {
  const severities: Record<string, 'success' | 'info' | 'warn' | 'danger' | 'secondary'> = {
    growth: 'success',
    redemption: 'success',
    fall: 'danger',
    circular: 'info',
    static: 'secondary',
  }
  return severities[arcType] || 'secondary'
}

function getArcLabel(arcType: string): string {
  const labels: Record<string, string> = {
    growth: 'Crecimiento',
    fall: 'Caída',
    redemption: 'Redención',
    static: 'Estático',
    circular: 'Circular',
  }
  return labels[arcType] || arcType
}

function getTrajectoryColor(trajectory: string): 'success' | 'info' | 'warn' | 'danger' | 'secondary' {
  switch (trajectory) {
    case 'rising': return 'success'
    case 'declining': return 'warn'
    default: return 'secondary'
  }
}

function getTrajectoryLabel(trajectory: string): string {
  const labels: Record<string, string> = {
    rising: 'Ascendente',
    declining: 'Descendente',
    stable: 'Estable',
  }
  return labels[trajectory] || trajectory
}

watch(() => props.projectId, () => {
  loadReport()
})

onMounted(() => {
  loadReport()
})
</script>

<style scoped>
.chapter-progress-tab {
  height: 100%;
  overflow-y: auto;
  padding: var(--ds-space-2);
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--ds-space-8);
  gap: var(--ds-space-4);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--ds-space-8);
  text-align: center;
  color: var(--text-color-secondary);
}

.empty-state i {
  font-size: 3rem;
  margin-bottom: var(--ds-space-4);
  opacity: 0.5;
}

.report-content {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
}

.header-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--ds-space-4);
}

.mode-card :deep(.p-card-content) {
  padding: var(--ds-space-3);
}

.mode-selector {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.mode-selector label {
  font-weight: 500;
}

.mode-dropdown {
  min-width: 200px;
}

.mode-description {
  color: var(--text-color-secondary);
  font-size: 0.85rem;
  margin-top: var(--ds-space-2);
  display: block;
}

.stats-card :deep(.p-card-content) {
  padding: var(--ds-space-3);
}

.stats-grid {
  display: flex;
  justify-content: space-around;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--ds-space-1);
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 600;
}

.stat-value.warning {
  color: var(--yellow-500);
}

.stat-label {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
}

.alerts-section {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.alert-content {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-1);
}

.alert-content small {
  color: var(--text-color-secondary);
}

.chapters-accordion {
  margin-top: var(--ds-space-2);
}

.chapter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding-right: var(--ds-space-2);
}

.chapter-title {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.chapter-subtitle {
  color: var(--text-color-secondary);
  font-weight: 400;
}

.chapter-badges {
  display: flex;
  gap: var(--ds-space-2);
}

.chapter-content {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
  padding: var(--ds-space-2);
}

.chapter-summary {
  background: var(--surface-50);
  padding: var(--ds-space-3);
  border-radius: var(--border-radius);
  border-left: 3px solid var(--primary-color);
}

.auto-summary {
  margin: 0;
  line-height: 1.6;
}

.section h4 {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  margin: 0 0 var(--ds-space-2) 0;
  font-size: 0.95rem;
  color: var(--text-color-secondary);
}

.characters-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-2);
}

.character-chip {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
  padding: var(--ds-space-1) var(--ds-space-2);
  background: var(--surface-100);
  border-radius: var(--border-radius);
  font-size: 0.9rem;
}

.character-chip.is-new {
  background: var(--green-100);
  border: 1px solid var(--green-300);
}

.character-chip.is-return {
  background: var(--blue-100);
  border: 1px solid var(--blue-300);
}

.char-mentions {
  background: var(--surface-200);
  padding: 0 var(--ds-space-1);
  border-radius: 50%;
  font-size: 0.8rem;
}

.character-chip i {
  font-size: 0.8rem;
  color: var(--yellow-600);
}

.events-list {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.event-item {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2);
  background: var(--surface-50);
  border-radius: var(--border-radius);
}

.event-description {
  flex: 1;
}

.event-characters {
  color: var(--text-color-secondary);
  font-size: 0.85rem;
}

.llm-tag {
  opacity: 0.7;
}

.interactions-stats {
  display: flex;
  gap: var(--ds-space-4);
}

.interactions-stats .positive {
  color: var(--green-600);
}

.interactions-stats .negative {
  color: var(--red-600);
}

.locations-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-2);
}

.absent-section {
  background: var(--yellow-50);
  padding: var(--ds-space-3);
  border-radius: var(--border-radius);
}

.absent-list {
  margin: 0;
  color: var(--yellow-700);
}

/* Arcs Tab */
.arcs-content {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
  padding: var(--ds-space-2);
}

.arc-card {
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  padding: var(--ds-space-4);
}

.arc-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
  margin-bottom: var(--ds-space-3);
}

.arc-character {
  font-size: 1.1rem;
  font-weight: 600;
}

.arc-details {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3);
}

.arc-states {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
  padding: var(--ds-space-3);
  background: var(--surface-50);
  border-radius: var(--border-radius);
}

.state {
  flex: 1;
}

.state label {
  display: block;
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  margin-bottom: var(--ds-space-1);
}

.arc-stats {
  display: flex;
  gap: var(--ds-space-4);
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

.arc-stats span {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
}

.turning-points {
  margin-top: var(--ds-space-2);
}

.turning-points h5 {
  margin: 0 0 var(--ds-space-2) 0;
  font-size: 0.9rem;
}

.turning-points ul {
  margin: 0;
  padding-left: var(--ds-space-4);
}

.turning-points li {
  margin-bottom: var(--ds-space-1);
}

.arc-completeness {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.arc-completeness label {
  font-size: 0.9rem;
  color: var(--text-color-secondary);
}

.arc-completeness :deep(.p-progressbar) {
  flex: 1;
  height: 8px;
}

/* Chekhov Tab */
.chekhov-content {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
  padding: var(--ds-space-2);
}

.chekhov-info {
  margin-bottom: var(--ds-space-2);
}

.chekhov-card {
  background: var(--surface-card);
  border: 1px solid var(--yellow-300);
  border-radius: var(--border-radius);
  padding: var(--ds-space-4);
}

.chekhov-card.is-fired {
  border-color: var(--green-300);
}

.chekhov-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--ds-space-3);
}

.chekhov-name {
  font-weight: 600;
  font-size: 1.1rem;
}

.chekhov-details p {
  margin: var(--ds-space-1) 0;
}

.chekhov-details .context {
  font-style: italic;
  color: var(--text-color-secondary);
  padding: var(--ds-space-2);
  background: var(--surface-50);
  border-radius: var(--border-radius);
}

.chekhov-details .llm-analysis {
  color: var(--primary-600);
  font-size: 0.9rem;
}

/* Abandoned Threads Tab */
.abandoned-content {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
  padding: var(--ds-space-2);
}

.thread-card {
  background: var(--surface-card);
  border: 1px solid var(--red-200);
  border-radius: var(--border-radius);
  padding: var(--ds-space-4);
}

.thread-description {
  font-weight: 500;
  font-size: 1.05rem;
}

.thread-details {
  margin-top: var(--ds-space-3);
}

.thread-details p {
  margin: var(--ds-space-1) 0;
}

.thread-details .suggestion {
  margin-top: var(--ds-space-3);
}

/* Structural Notes */
.structural-notes-card {
  margin-top: var(--ds-space-4);
}

.structural-notes-card :deep(.p-card-title) {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: 1rem;
}

/* Empty Tab State */
.empty-tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--ds-space-8);
  text-align: center;
  color: var(--text-color-secondary);
}

.empty-tab i {
  font-size: 2rem;
  margin-bottom: var(--ds-space-2);
  color: var(--green-500);
}

/* Dark mode */
.dark .chapter-summary {
  background: var(--surface-800);
}

.dark .character-chip {
  background: var(--surface-700);
}

.dark .character-chip.is-new {
  background: var(--green-900);
  border-color: var(--green-700);
}

.dark .character-chip.is-return {
  background: var(--blue-900);
  border-color: var(--blue-700);
}

.dark .event-item {
  background: var(--surface-800);
}

.dark .absent-section {
  background: var(--yellow-900);
}

.dark .arc-states {
  background: var(--surface-800);
}

.dark .chekhov-details .context {
  background: var(--surface-800);
}

/* Responsive */
@media (max-width: 768px) {
  .header-section {
    grid-template-columns: 1fr;
  }

  .stats-grid {
    flex-wrap: wrap;
  }

  .chapter-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--ds-space-2);
  }

  .arc-states {
    flex-direction: column;
  }

  .arc-states i {
    transform: rotate(90deg);
  }
}
</style>
