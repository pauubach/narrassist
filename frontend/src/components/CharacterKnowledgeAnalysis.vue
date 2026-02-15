<template>
  <div class="character-knowledge">
    <!-- Header -->
    <div class="knowledge-header">
      <div class="header-left">
        <i class="pi pi-brain"></i>
        <h3>Conocimiento del Personaje</h3>
        <Tag v-if="knowledge" severity="info" size="small">
          {{ totalFacts }} hechos
        </Tag>
      </div>
      <div class="header-actions">
        <Select
          v-model="selectedMode"
          :options="modeOptions"
          option-label="label"
          option-value="value"
          placeholder="Modo"
          class="mode-selector"
          size="small"
        />
        <Button
          v-if="!knowledge && !loading"
          label="Analizar"
          icon="pi pi-play"
          :loading="loading"
          size="small"
          @click="loadKnowledge"
        />
        <Button
          v-if="knowledge"
          v-tooltip.bottom="'Actualizar'"
          icon="pi pi-refresh"
          text
          rounded
          size="small"
          :loading="loading"
          @click="loadKnowledge"
        />
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner style="width: 30px; height: 30px" />
      <p>Analizando conocimiento del personaje...</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="error-state">
      <i class="pi pi-exclamation-triangle"></i>
      <p>{{ error }}</p>
      <Button label="Reintentar" size="small" @click="loadKnowledge" />
    </div>

    <!-- Knowledge Content -->
    <div v-else-if="knowledge" class="knowledge-content">
      <!-- Tab View for knowledge direction -->
      <Tabs value="0">
        <TabList>
          <Tab value="0"><i class="pi pi-eye"></i> Lo que sabe ({{ knowledge.knowsAboutOthers.length }})</Tab>
          <Tab value="1"><i class="pi pi-users"></i> Lo que otros saben ({{ knowledge.othersKnowAbout.length }})</Tab>
        </TabList>
        <TabPanels>
        <!-- What this character knows -->
        <TabPanel value="0">

          <div v-if="knowledge.knowsAboutOthers.length > 0" class="facts-list">
            <div
              v-for="(fact, idx) in knowledge.knowsAboutOthers"
              :key="`knows-${idx}`"
              class="fact-item"
              :class="getFactClass(fact)"
            >
              <div class="fact-header">
                <div class="fact-about">
                  <i class="pi pi-user"></i>
                  <span class="about-name">{{ fact.knownName }}</span>
                </div>
                <div class="fact-meta">
                  <Tag :severity="getTypeSeverity(fact.knowledgeType)" size="small">
                    {{ getTypeLabel(fact.knowledgeType) }}
                  </Tag>
                  <ConfidenceBadge
                    :value="fact.confidence"
                    variant="dot"
                    size="sm"
                    inline
                  />
                </div>
              </div>
              <p class="fact-description">{{ fact.factDescription }}</p>
              <div v-if="fact.factValue" class="fact-value">
                <strong>Valor:</strong> {{ fact.factValue }}
              </div>
              <div class="fact-footer">
                <span class="fact-chapter">
                  <i class="pi pi-book"></i> Capítulo {{ fact.sourceChapter }}
                </span>
                <Tag
                  v-if="fact.isAccurate !== null"
                  :severity="fact.isAccurate ? 'success' : 'danger'"
                  size="small"
                >
                  {{ fact.isAccurate ? 'Correcto' : 'Incorrecto' }}
                </Tag>
              </div>
            </div>
          </div>
          <p v-else class="empty-text">No se detectó conocimiento sobre otros personajes</p>
        </TabPanel>

        <!-- What others know about this character -->
        <TabPanel value="1">

          <div v-if="knowledge.othersKnowAbout.length > 0" class="facts-list">
            <div
              v-for="(fact, idx) in knowledge.othersKnowAbout"
              :key="`known-${idx}`"
              class="fact-item"
              :class="getFactClass(fact)"
            >
              <div class="fact-header">
                <div class="fact-about">
                  <i class="pi pi-user"></i>
                  <span class="about-name">{{ fact.knowerName }}</span>
                  <span class="about-verb">sabe que</span>
                </div>
                <div class="fact-meta">
                  <Tag :severity="getTypeSeverity(fact.knowledgeType)" size="small">
                    {{ getTypeLabel(fact.knowledgeType) }}
                  </Tag>
                  <ConfidenceBadge
                    :value="fact.confidence"
                    variant="dot"
                    size="sm"
                    inline
                  />
                </div>
              </div>
              <p class="fact-description">{{ fact.factDescription }}</p>
              <div v-if="fact.factValue" class="fact-value">
                <strong>Valor:</strong> {{ fact.factValue }}
              </div>
              <div class="fact-footer">
                <span class="fact-chapter">
                  <i class="pi pi-book"></i> Capítulo {{ fact.sourceChapter }}
                </span>
                <Tag
                  v-if="fact.isAccurate !== null"
                  :severity="fact.isAccurate ? 'success' : 'danger'"
                  size="small"
                >
                  {{ fact.isAccurate ? 'Correcto' : 'Incorrecto' }}
                </Tag>
              </div>
            </div>
          </div>
          <p v-else class="empty-text">No se detectó que otros personajes sepan cosas sobre este</p>
        </TabPanel>
        </TabPanels>
      </Tabs>

      <!-- Stats Summary -->
      <div v-if="knowledge.stats" class="stats-summary">
        <h4><i class="pi pi-chart-pie"></i> Resumen</h4>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-value">{{ knowledge.knowsAboutOthers.length }}</span>
            <span class="stat-label">Hechos que sabe</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ knowledge.othersKnowAbout.length }}</span>
            <span class="stat-label">Hechos sobre él/ella</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ uniqueCharactersKnown }}</span>
            <span class="stat-label">Personajes que conoce</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ uniqueCharactersKnowing }}</span>
            <span class="stat-label">Personajes que lo conocen</span>
          </div>
        </div>
      </div>
    </div>

    <!-- No Knowledge Yet -->
    <div v-else class="no-knowledge">
      <i class="pi pi-brain empty-icon"></i>
      <p>Haz clic en "Analizar" para detectar qué sabe este personaje sobre otros y viceversa.</p>
      <small>Selecciona el modo de análisis: Reglas (rápido), LLM (preciso) o Híbrido.</small>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Select from 'primevue/select'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import ProgressSpinner from 'primevue/progressspinner'
import ConfidenceBadge from '@/components/shared/ConfidenceBadge.vue'
import { useVoiceAndStyleStore } from '@/stores/voiceAndStyle'
import type { KnowledgeFact } from '@/types'

const props = defineProps<{
  projectId: number
  characterId: number
  characterName: string
}>()

const store = useVoiceAndStyleStore()

// State
const loading = ref(false)
const error = ref<string | null>(null)
const selectedMode = ref('auto')

const modeOptions = [
  { label: 'Auto', value: 'auto' },
  { label: 'Reglas', value: 'rules' },
  { label: 'LLM', value: 'llm' },
  { label: 'Híbrido', value: 'hybrid' }
]

// Get knowledge from store
const knowledge = computed(() => {
  return store.getCharacterKnowledge(props.projectId, props.characterId)
})

// Computed stats
const totalFacts = computed(() => {
  if (!knowledge.value) return 0
  return knowledge.value.knowsAboutOthers.length + knowledge.value.othersKnowAbout.length
})

const uniqueCharactersKnown = computed(() => {
  if (!knowledge.value) return 0
  const ids = new Set(knowledge.value.knowsAboutOthers.map(f => f.knownEntityId))
  return ids.size
})

const uniqueCharactersKnowing = computed(() => {
  if (!knowledge.value) return 0
  const ids = new Set(knowledge.value.othersKnowAbout.map(f => f.knowerEntityId))
  return ids.size
})

// Load knowledge
const loadKnowledge = async () => {
  loading.value = true
  error.value = null

  try {
    const success = await store.fetchCharacterKnowledge(
      props.projectId,
      props.characterId,
      selectedMode.value
    )
    if (!success) {
      error.value = store.error || 'Error al cargar el conocimiento del personaje'
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'No se pudo completar la operación'
  } finally {
    loading.value = false
  }
}

// Helpers
const getTypeSeverity = (type: string): string => {
  const severities: Record<string, string> = {
    identity: 'info',
    relationship: 'success',
    location: 'warning',
    secret: 'danger',
    attribute: 'secondary',
    event: 'contrast'
  }
  return severities[type] || 'secondary'
}

const getTypeLabel = (type: string): string => {
  const labels: Record<string, string> = {
    identity: 'Identidad',
    relationship: 'Relación',
    location: 'Ubicación',
    secret: 'Secreto',
    attribute: 'Atributo',
    event: 'Evento'
  }
  return labels[type] || type
}

const getFactClass = (fact: KnowledgeFact): string => {
  if (fact.knowledgeType === 'secret') return 'fact-secret'
  if (fact.isAccurate === false) return 'fact-incorrect'
  return ''
}

// Auto-load on mount
onMounted(() => {
  if (props.projectId && props.characterId && !knowledge.value) {
    loadKnowledge()
  }
})

// Watch for character changes
watch(
  () => [props.projectId, props.characterId],
  ([newProjectId, newCharacterId]) => {
    if (newProjectId && newCharacterId) {
      const key = `${newProjectId}-${newCharacterId}`
      if (!store.characterKnowledge[key]) {
        loadKnowledge()
      }
    }
  }
)
</script>

<style scoped>
.character-knowledge {
  background: var(--surface-card);
  border-radius: 8px;
  padding: 1.5rem;
}

.knowledge-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.header-left h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.header-left i {
  color: var(--primary-color);
  font-size: 1.25rem;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.mode-selector {
  width: 100px;
}

/* Loading and Error States */
.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem;
  gap: 0.75rem;
  color: var(--text-color-secondary);
}

.error-state {
  color: var(--red-500);
}

.error-state i {
  font-size: 2rem;
}

.no-knowledge {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem;
  text-align: center;
  color: var(--text-color-secondary);
}

.empty-icon {
  font-size: 2.5rem;
  opacity: 0.4;
  margin-bottom: 0.5rem;
}

.no-knowledge small {
  margin-top: 0.5rem;
  font-size: 0.8125rem;
}

/* Knowledge Content */
.knowledge-content {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

/* Facts List */
.facts-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.fact-item {
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 6px;
  border-left: 4px solid var(--primary-color);
}

.fact-item.fact-secret {
  border-color: var(--red-500);
  background: var(--red-50);
}

.fact-item.fact-incorrect {
  border-color: var(--orange-500);
  background: var(--orange-50);
}

.fact-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.5rem;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.fact-about {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.fact-about i {
  color: var(--primary-color);
  font-size: 0.875rem;
}

.about-name {
  font-weight: 600;
  color: var(--text-color);
}

.about-verb {
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
}

.fact-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.fact-description {
  margin: 0.5rem 0;
  font-size: 0.9rem;
  line-height: 1.5;
  color: var(--text-color);
}

.fact-value {
  padding: 0.5rem;
  background: var(--surface-100);
  border-radius: 4px;
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.fact-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.5rem;
}

.fact-chapter {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.fact-chapter i {
  font-size: 0.7rem;
}

/* Stats Summary */
.stats-summary {
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 6px;
}

.stats-summary h4 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 0.75rem 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-color-secondary);
}

.stats-summary h4 i {
  font-size: 0.875rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  gap: 0.75rem;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.stat-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--primary-color);
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.empty-text {
  margin: 0;
  padding: 1rem;
  color: var(--text-color-secondary);
  font-size: 0.875rem;
  font-style: italic;
  text-align: center;
}

/* Tab styling */
:deep(.p-tablist) {
  background: transparent;
}

:deep(.p-tabpanel) {
  padding: 0.5rem 0;
}

:deep(.p-tab) {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
</style>
