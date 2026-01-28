<template>
  <div class="character-location-tab">
    <!-- Header -->
    <div class="tab-header">
      <div class="header-left">
        <h3>
          <i class="pi pi-map-marker"></i>
          Ubicaciones de Personajes
        </h3>
        <p class="subtitle">
          Rastrea movimientos de personajes y detecta inconsistencias de ubicación.
        </p>
      </div>
      <div class="header-controls">
        <Button
          label="Analizar"
          icon="pi pi-refresh"
          :loading="loading"
          @click="analyze"
        />
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner />
      <p>Analizando ubicaciones de personajes...</p>
    </div>

    <!-- Empty state -->
    <div v-else-if="!report" class="empty-state">
      <i class="pi pi-info-circle"></i>
      <p>Haz clic en "Analizar" para rastrear ubicaciones de personajes.</p>
    </div>

    <!-- Results -->
    <div v-else class="results-container">
      <!-- Stats Summary -->
      <div class="stats-cards">
        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.characters_tracked }}</div>
              <div class="stat-label">Personajes rastreados</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.locations_found }}</div>
              <div class="stat-label">Ubicaciones encontradas</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.location_events.length }}</div>
              <div class="stat-label">Eventos de ubicación</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value" :class="report.inconsistencies_count > 0 ? 'text-danger' : 'text-success'">
                {{ report.inconsistencies_count }}
              </div>
              <div class="stat-label">Inconsistencias</div>
            </div>
          </template>
        </Card>
      </div>

      <!-- No Events Message -->
      <Message v-if="report.location_events.length === 0" severity="info" :closable="false" class="info-message">
        <i class="pi pi-info-circle"></i>
        No se detectaron eventos de ubicación en el manuscrito.
      </Message>

      <!-- Inconsistencies -->
      <Card v-if="report.inconsistencies_count > 0" class="inconsistencies-card">
        <template #title>
          <i class="pi pi-exclamation-triangle"></i>
          Inconsistencias de Ubicación ({{ report.inconsistencies_count }})
        </template>
        <template #content>
          <Message severity="warn" :closable="false" class="warning-message">
            Un personaje aparece en dos lugares incompatibles en el mismo momento narrativo.
          </Message>
          <div class="inconsistencies-list">
            <div
              v-for="(inc, idx) in report.inconsistencies"
              :key="idx"
              class="inconsistency-item"
            >
              <div class="inc-header">
                <Tag severity="danger">
                  <i class="pi pi-user"></i>
                  {{ inc.entity_name }}
                </Tag>
                <div class="location-conflict">
                  <Tag severity="info" size="small">
                    <i class="pi pi-map-marker"></i>
                    {{ inc.location1_name }}
                  </Tag>
                  <i class="pi pi-times conflict-icon"></i>
                  <Tag severity="warning" size="small">
                    <i class="pi pi-map-marker"></i>
                    {{ inc.location2_name }}
                  </Tag>
                </div>
              </div>
              <p class="inc-explanation">{{ inc.explanation }}</p>
              <div v-if="inc.location2_excerpt" class="inc-excerpt">
                "{{ truncate(inc.location2_excerpt, 100) }}"
              </div>
            </div>
          </div>
        </template>
      </Card>

      <!-- Current Locations -->
      <Card v-if="Object.keys(report.current_locations).length > 0" class="current-locations-card">
        <template #title>
          <i class="pi pi-map"></i>
          Última Ubicación Conocida
        </template>
        <template #content>
          <div class="locations-grid">
            <div
              v-for="(location, entityId) in report.current_locations"
              :key="entityId"
              class="location-item"
            >
              <div class="character-name">
                <i class="pi pi-user"></i>
                {{ getCharacterName(entityId) }}
              </div>
              <div class="location-name">
                <i class="pi pi-map-marker"></i>
                {{ location }}
              </div>
            </div>
          </div>
        </template>
      </Card>

      <!-- Location Events by Chapter -->
      <Card v-if="report.location_events.length > 0" class="events-card">
        <template #title>
          <i class="pi pi-list"></i>
          Eventos de Ubicación ({{ report.location_events.length }})
        </template>
        <template #content>
          <Accordion :multiple="true" class="events-accordion">
            <AccordionPanel v-for="(events, chapter) in eventsByChapter" :key="chapter" :value="String(chapter)">
              <AccordionHeader>
                <div class="chapter-header">
                  <span class="chapter-title">Capítulo {{ chapter }}</span>
                  <Tag severity="secondary" size="small">{{ events.length }} eventos</Tag>
                </div>
              </AccordionHeader>
              <AccordionContent>
                <div class="events-list">
                  <div
                    v-for="(event, idx) in events"
                    :key="idx"
                    class="event-item"
                    :class="'type-' + event.change_type"
                  >
                    <div class="event-header">
                      <Tag :severity="getChangeTypeSeverity(event.change_type)" size="small">
                        <i :class="getChangeTypeIcon(event.change_type)"></i>
                        {{ getChangeTypeLabel(event.change_type) }}
                      </Tag>
                      <span class="event-character">
                        <i class="pi pi-user"></i>
                        {{ event.entity_name }}
                      </span>
                      <span class="event-location">
                        <i class="pi pi-map-marker"></i>
                        {{ event.location_name }}
                      </span>
                    </div>
                    <div class="event-excerpt">
                      "{{ truncate(event.excerpt, 100) }}"
                    </div>
                  </div>
                </div>
              </AccordionContent>
            </AccordionPanel>
          </Accordion>
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import Accordion from 'primevue/accordion'
import AccordionPanel from 'primevue/accordionpanel'
import AccordionHeader from 'primevue/accordionheader'
import AccordionContent from 'primevue/accordioncontent'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'

interface LocationEvent {
  entity_id: number
  entity_name: string
  location_id: number | null
  location_name: string
  chapter: number
  start_char: number
  end_char: number
  excerpt: string
  change_type: string  // "arrival", "departure", "transition", "presence"
  confidence: number
}

interface LocationInconsistency {
  entity_id: number
  entity_name: string
  location1_name: string
  location1_chapter: number
  location1_excerpt: string
  location2_name: string
  location2_chapter: number
  location2_excerpt: string
  explanation: string
  confidence: number
}

interface CharacterLocationReport {
  project_id: number
  location_events: LocationEvent[]
  inconsistencies: LocationInconsistency[]
  inconsistencies_count: number
  current_locations: Record<number, string>
  characters_tracked: number
  locations_found: number
}

const props = defineProps<{
  projectId: number
}>()

const toast = useToast()

// State
const loading = ref(false)
const report = ref<CharacterLocationReport | null>(null)

// Computed
const eventsByChapter = computed(() => {
  if (!report.value) return {}
  const grouped: Record<number, LocationEvent[]> = {}

  for (const event of report.value.location_events) {
    if (!grouped[event.chapter]) {
      grouped[event.chapter] = []
    }
    grouped[event.chapter].push(event)
  }

  return grouped
})

// Analyze
async function analyze() {
  loading.value = true
  try {
    const response = await fetch(
      `http://localhost:8008/api/projects/${props.projectId}/character-locations`
    )
    const data = await response.json()

    if (data.success) {
      report.value = data.data
    } else {
      throw new Error(data.error || 'Error al analizar')
    }
  } catch (error: any) {
    console.error('Error analyzing character locations:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: error.message || 'No se pudieron analizar las ubicaciones',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

// Helper functions
function truncate(text: string, maxLength: number): string {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

function getCharacterName(entityId: number | string): string {
  if (!report.value) return `Personaje ${entityId}`
  const event = report.value.location_events.find(e => e.entity_id === Number(entityId))
  return event?.entity_name || `Personaje ${entityId}`
}

function getChangeTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    arrival: 'Llegada',
    departure: 'Salida',
    transition: 'Transición',
    presence: 'Presencia',
  }
  return labels[type] || type
}

function getChangeTypeSeverity(type: string): string {
  const severities: Record<string, string> = {
    arrival: 'success',
    departure: 'warning',
    transition: 'info',
    presence: 'secondary',
  }
  return severities[type] || 'secondary'
}

function getChangeTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    arrival: 'pi pi-sign-in',
    departure: 'pi pi-sign-out',
    transition: 'pi pi-arrow-right',
    presence: 'pi pi-map-marker',
  }
  return icons[type] || 'pi pi-circle'
}

// Lifecycle
onMounted(() => {
  analyze()
})

watch(() => props.projectId, () => {
  analyze()
})
</script>

<style scoped>
.character-location-tab {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
  padding: var(--ds-space-4);
  height: 100%;
  overflow: auto;
}

.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--ds-space-4);
}

.header-left h3 {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  margin: 0;
  font-size: var(--ds-font-size-lg);
}

.header-left .subtitle {
  margin: var(--ds-space-1) 0 0;
  color: var(--ds-color-text-secondary);
  font-size: var(--ds-font-size-sm);
}

/* Loading & Empty states */
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-3);
  padding: var(--ds-space-8);
  color: var(--ds-color-text-secondary);
}

.empty-state i {
  font-size: 2rem;
}

/* Stats cards */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: var(--ds-space-3);
}

.stat-card :deep(.p-card-body) {
  padding: var(--ds-space-3);
}

.stat-content {
  text-align: center;
}

.stat-value {
  font-size: var(--ds-font-size-2xl);
  font-weight: var(--ds-font-weight-bold);
}

.stat-label {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  margin-top: var(--ds-space-1);
}

.text-danger { color: var(--p-red-500); }
.text-success { color: var(--p-green-500); }

/* Cards */
.inconsistencies-card :deep(.p-card-title),
.current-locations-card :deep(.p-card-title),
.events-card :deep(.p-card-title) {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: var(--ds-font-size-base);
}

.inconsistencies-card :deep(.p-card-title) i { color: var(--p-yellow-600); }
.current-locations-card :deep(.p-card-title) i { color: var(--p-blue-500); }
.events-card :deep(.p-card-title) i { color: var(--p-green-500); }

/* Inconsistencies */
.inconsistencies-list {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3);
}

.inconsistency-item {
  padding: var(--ds-space-3);
  background: var(--ds-surface-secondary);
  border-radius: var(--ds-radius-md);
  border-left: 3px solid var(--p-yellow-500);
}

.inc-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  flex-wrap: wrap;
  margin-bottom: var(--ds-space-2);
}

.location-conflict {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
}

.conflict-icon {
  color: var(--p-red-500);
  font-size: 0.75rem;
}

.inc-explanation {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
  margin: var(--ds-space-2) 0;
}

.inc-excerpt {
  font-size: var(--ds-font-size-sm);
  font-style: italic;
  color: var(--ds-color-text-tertiary);
}

/* Current Locations */
.locations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--ds-space-3);
}

.location-item {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-1);
  padding: var(--ds-space-3);
  background: var(--ds-surface-secondary);
  border-radius: var(--ds-radius-md);
}

.character-name {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
  font-weight: var(--ds-font-weight-semibold);
}

.location-name {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
  color: var(--ds-color-text-secondary);
  font-size: var(--ds-font-size-sm);
}

.location-name i {
  color: var(--p-blue-500);
}

/* Events */
.chapter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: var(--ds-space-3);
}

.events-list {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.event-item {
  padding: var(--ds-space-2);
  background: var(--ds-surface-secondary);
  border-radius: var(--ds-radius-sm);
  border-left: 3px solid;
}

.event-item.type-arrival { border-left-color: var(--p-green-500); }
.event-item.type-departure { border-left-color: var(--p-yellow-500); }
.event-item.type-transition { border-left-color: var(--p-blue-500); }
.event-item.type-presence { border-left-color: var(--p-gray-400); }

.event-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  flex-wrap: wrap;
  margin-bottom: var(--ds-space-1);
}

.event-character,
.event-location {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
  font-size: var(--ds-font-size-sm);
}

.event-location {
  color: var(--ds-color-text-secondary);
}

.event-excerpt {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-tertiary);
  font-style: italic;
}

/* Responsive */
@media (max-width: 768px) {
  .tab-header {
    flex-direction: column;
  }

  .inc-header,
  .event-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
