<script setup lang="ts">
/**
 * CharacterArchetypesTab - Arquetipos de personaje (Jung/Campbell)
 *
 * Muestra qué arquetipo narrativo encaja con cada personaje
 * basándose en arco, relaciones, interacciones e importancia.
 */

import { ref, onMounted, watch } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import ProgressSpinner from 'primevue/progressspinner'
import { api } from '@/services/apiClient'
import AnalysisErrorState from '@/components/shared/AnalysisErrorState.vue'

const props = defineProps<{
  projectId: number
}>()

interface ArchetypeScore {
  archetype: string
  name: string
  description: string
  icon: string
  color: string
  score: number
  confidence: number
  signals: string[]
}

interface CharacterProfile {
  character_id: number
  character_name: string
  importance: string
  primary_archetype: ArchetypeScore | null
  secondary_archetype: ArchetypeScore | null
  top_archetypes: ArchetypeScore[]
  summary: string
}

interface ArchetypeReport {
  characters: CharacterProfile[]
  archetype_distribution: Record<string, number>
  ensemble_notes: string[]
  protagonist_suggestion: string | null
}

const loading = ref(false)
const report = ref<ArchetypeReport | null>(null)
const errorMsg = ref<string | null>(null)
const expandedCharacter = ref<number | null>(null)

onMounted(() => {
  analyze()
})

watch(() => props.projectId, () => {
  report.value = null
  errorMsg.value = null
  analyze()
})

async function analyze() {
  loading.value = true
  errorMsg.value = null
  try {
    const data = await api.getRaw<{ success: boolean; data: ArchetypeReport; error?: string }>(
      `/api/projects/${props.projectId}/character-archetypes`
    )
    if (data.success) {
      report.value = data.data
    } else {
      errorMsg.value = data.error || 'Error al analizar arquetipos'
    }
  } catch (error) {
    console.error('Error analyzing character archetypes:', error)
    errorMsg.value = error instanceof Error ? error.message : 'Error del servicio local'
  } finally {
    loading.value = false
  }
}

function toggleCharacter(id: number) {
  expandedCharacter.value = expandedCharacter.value === id ? null : id
}

function getImportanceLabel(imp: string): string {
  const labels: Record<string, string> = {
    protagonist: 'Protagonista',
    principal: 'Protagonista',
    high: 'Principal',
    primary: 'Principal',
    secondary: 'Secundario',
    medium: 'Secundario',
    minor: 'Menor',
    low: 'Menor',
    minimal: 'Mencionado',
    mentioned: 'Mencionado',
  }
  return labels[imp] || imp
}

function getImportanceSeverity(imp: string): 'info' | 'warn' | 'secondary' | 'success' {
  const map: Record<string, 'info' | 'warn' | 'secondary' | 'success'> = {
    protagonist: 'success',
    principal: 'success',
    high: 'info',
    primary: 'info',
    secondary: 'info',
    medium: 'info',
    minor: 'secondary',
    low: 'secondary',
    minimal: 'secondary',
    mentioned: 'secondary',
  }
  return map[imp] || 'secondary'
}

function getConfidenceLabel(c: number): string {
  if (c >= 0.7) return 'Alta'
  if (c >= 0.4) return 'Media'
  return 'Baja'
}

function getConfidenceSeverity(c: number): 'success' | 'warn' | 'secondary' {
  if (c >= 0.7) return 'success'
  if (c >= 0.4) return 'warn'
  return 'secondary'
}
</script>

<template>
  <div class="character-archetypes-tab">
    <!-- Header -->
    <div class="tab-header">
      <div class="header-left">
        <h3>
          <i class="pi pi-users"></i>
          Arquetipos de Personaje
        </h3>
        <p class="subtitle">
          Clasificación Jung/Campbell: Héroe, Sombra, Mentor, Heraldo y más.
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

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner />
      <p>Analizando arquetipos de personajes...</p>
    </div>

    <!-- Error -->
    <AnalysisErrorState v-else-if="errorMsg" :message="errorMsg" :on-retry="analyze" />

    <!-- Empty -->
    <div v-else-if="!report" class="empty-state">
      <i class="pi pi-users"></i>
      <p>Haz clic en "Analizar" para clasificar los personajes por arquetipo.</p>
    </div>

    <!-- Results -->
    <div v-else class="results-container">
      <!-- Protagonist suggestion -->
      <div v-if="report.protagonist_suggestion" class="protagonist-banner">
        <i class="pi pi-star-fill"></i>
        <span>
          Protagonista sugerido: <strong>{{ report.protagonist_suggestion }}</strong>
        </span>
      </div>

      <!-- Ensemble notes -->
      <Card v-if="report.ensemble_notes.length" class="ensemble-card">
        <template #title>
          <i class="pi pi-info-circle"></i>
          Análisis del elenco
        </template>
        <template #content>
          <ul class="ensemble-list">
            <li v-for="(note, i) in report.ensemble_notes" :key="i">{{ note }}</li>
          </ul>
        </template>
      </Card>

      <!-- Distribution -->
      <Card v-if="Object.keys(report.archetype_distribution).length" class="dist-card">
        <template #title>
          <i class="pi pi-chart-pie"></i>
          Distribución de arquetipos
        </template>
        <template #content>
          <div class="dist-chips">
            <span
              v-for="(count, name) in report.archetype_distribution"
              :key="String(name)"
              class="dist-chip"
            >
              {{ name }} <strong>{{ count }}</strong>
            </span>
          </div>
        </template>
      </Card>

      <!-- Characters -->
      <div class="characters-list">
        <div
          v-for="char in report.characters"
          :key="char.character_id"
          class="character-card"
          :class="{
            'character-card--expanded': expandedCharacter === char.character_id,
            'character-card--protagonist': report.protagonist_suggestion === char.character_name,
          }"
          @click="toggleCharacter(char.character_id)"
        >
          <!-- Character header -->
          <div class="char-header">
            <div class="char-identity">
              <i
                v-if="char.primary_archetype"
                :class="'pi ' + char.primary_archetype.icon"
                :style="{ color: char.primary_archetype.color }"
                class="char-archetype-icon"
              />
              <i v-else class="pi pi-user char-archetype-icon" />
              <div class="char-names">
                <span class="char-name">
                  {{ char.character_name }}
                  <i
                    v-if="report.protagonist_suggestion === char.character_name"
                    class="pi pi-star-fill protagonist-star"
                    title="Protagonista sugerido"
                  />
                </span>
                <span v-if="char.primary_archetype" class="char-archetype">
                  {{ char.primary_archetype.name }}
                  <span v-if="char.secondary_archetype" class="char-secondary">
                    / {{ char.secondary_archetype.name }}
                  </span>
                </span>
              </div>
            </div>
            <div class="char-badges">
              <Tag
                :value="getImportanceLabel(char.importance)"
                :severity="getImportanceSeverity(char.importance)"
              />
              <Tag
                v-if="char.primary_archetype"
                :value="getConfidenceLabel(char.primary_archetype.confidence)"
                :severity="getConfidenceSeverity(char.primary_archetype.confidence)"
              />
            </div>
          </div>

          <!-- Summary -->
          <p class="char-summary">{{ char.summary }}</p>

          <!-- Expanded: top archetypes -->
          <div v-if="expandedCharacter === char.character_id" class="char-expanded">
            <div class="top-archetypes">
              <div
                v-for="arch in char.top_archetypes"
                :key="arch.archetype"
                class="archetype-row"
              >
                <i :class="'pi ' + arch.icon" :style="{ color: arch.color }" />
                <span class="arch-name">{{ arch.name }}</span>
                <div class="arch-bar-container">
                  <div
                    class="arch-bar"
                    :style="{ width: arch.score + '%', backgroundColor: arch.color }"
                  />
                </div>
                <span class="arch-score">{{ Math.round(arch.score) }}</span>
              </div>
            </div>

            <!-- Signals for primary -->
            <div v-if="char.primary_archetype?.signals.length" class="arch-signals">
              <h4>Señales detectadas</h4>
              <ul>
                <li v-for="(s, i) in char.primary_archetype.signals" :key="i">{{ s }}</li>
              </ul>
            </div>

            <!-- Primary archetype description -->
            <p v-if="char.primary_archetype" class="arch-desc">
              <strong>{{ char.primary_archetype.name }}:</strong>
              {{ char.primary_archetype.description }}
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.character-archetypes-tab {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4, 1rem);
}

.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--ds-space-4, 1rem);
  flex-wrap: wrap;
}

.header-left h3 {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2, 0.5rem);
  margin: 0 0 var(--ds-space-1, 0.25rem);
  font-size: 1.125rem;
}

.subtitle {
  margin: 0;
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
  font-size: var(--ds-font-size-sm, 0.8125rem);
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--ds-space-8, 2rem);
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
  gap: var(--ds-space-3, 0.75rem);
}

.empty-state i { font-size: 2rem; opacity: 0.5; }

/* Protagonist banner */
.protagonist-banner {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2, 0.5rem);
  padding: var(--ds-space-2, 0.5rem) var(--ds-space-3, 0.75rem);
  background: var(--p-blue-50, #eff6ff);
  border: 1px solid var(--p-blue-200, #bfdbfe);
  border-radius: var(--ds-radius-md, 8px);
  color: var(--p-blue-700, #1d4ed8);
  font-size: var(--ds-font-size-sm, 0.8125rem);
}

.protagonist-banner i {
  color: var(--p-yellow-500, #eab308);
  font-size: 1rem;
}

:global(.dark) .protagonist-banner {
  background: var(--p-blue-900, #1e3a5f);
  border-color: var(--p-blue-700, #1d4ed8);
  color: var(--p-blue-100, #dbeafe);
}

/* Ensemble */
.ensemble-card :deep(.p-card-title) {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2, 0.5rem);
  font-size: 0.9375rem;
}

.ensemble-list {
  margin: 0;
  padding-left: var(--ds-space-5, 1.25rem);
}

.ensemble-list li {
  font-size: var(--ds-font-size-sm, 0.8125rem);
  line-height: 1.6;
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
}

/* Distribution */
.dist-card :deep(.p-card-title) {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2, 0.5rem);
  font-size: 0.9375rem;
}

.dist-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-2, 0.5rem);
}

.dist-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--ds-space-1, 0.25rem);
  padding: var(--ds-space-1, 0.25rem) var(--ds-space-3, 0.75rem);
  background: var(--ds-surface-ground, var(--surface-ground));
  border-radius: 16px;
  font-size: var(--ds-font-size-sm, 0.8125rem);
}

.dist-chip strong {
  color: var(--ds-color-primary, var(--primary-color));
}

/* Characters list */
.characters-list {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2, 0.5rem);
}

.character-card {
  padding: var(--ds-space-3, 0.75rem);
  border-radius: var(--ds-radius-md, 8px);
  background: var(--ds-surface-card, var(--surface-card));
  border: 1px solid var(--ds-surface-border, var(--surface-border));
  cursor: pointer;
  transition: box-shadow 0.15s ease, border-color 0.15s ease;
}

.character-card:hover {
  border-color: var(--ds-color-primary, var(--primary-color));
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.character-card--expanded {
  border-color: var(--ds-color-primary, var(--primary-color));
}

.character-card--protagonist {
  border-left: 3px solid var(--p-blue-500, #3b82f6);
}

.protagonist-star {
  color: var(--p-yellow-500, #eab308);
  font-size: 0.75rem;
  margin-left: 4px;
}

.char-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--ds-space-3, 0.75rem);
  margin-bottom: var(--ds-space-2, 0.5rem);
}

.char-identity {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2, 0.5rem);
}

.char-archetype-icon {
  font-size: 1.25rem;
}

.char-names {
  display: flex;
  flex-direction: column;
}

.char-name {
  font-weight: 700;
  font-size: 0.9375rem;
}

.char-archetype {
  font-size: 0.8125rem;
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
}

.char-secondary {
  opacity: 0.7;
}

.char-badges {
  display: flex;
  gap: var(--ds-space-1, 0.25rem);
  flex-shrink: 0;
}

.char-summary {
  margin: 0;
  font-size: var(--ds-font-size-sm, 0.8125rem);
  line-height: 1.5;
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
}

/* Expanded */
.char-expanded {
  margin-top: var(--ds-space-3, 0.75rem);
  padding-top: var(--ds-space-3, 0.75rem);
  border-top: 1px solid var(--ds-surface-border, var(--surface-border));
}

.top-archetypes {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2, 0.5rem);
  margin-bottom: var(--ds-space-3, 0.75rem);
}

.archetype-row {
  display: grid;
  grid-template-columns: 20px 90px 1fr 32px;
  align-items: center;
  gap: var(--ds-space-2, 0.5rem);
  font-size: var(--ds-font-size-sm, 0.8125rem);
}

.arch-name { font-weight: 500; }

.arch-bar-container {
  height: 12px;
  background: var(--ds-surface-ground, var(--surface-ground));
  border-radius: 6px;
  overflow: hidden;
}

.arch-bar {
  height: 100%;
  border-radius: 6px;
  min-width: 2px;
  transition: width 0.3s ease;
}

.arch-score {
  text-align: right;
  font-weight: 600;
  font-size: 0.75rem;
}

.arch-signals h4 {
  margin: 0 0 var(--ds-space-1, 0.25rem);
  font-size: 0.8125rem;
}

.arch-signals ul {
  margin: 0;
  padding-left: var(--ds-space-4, 1rem);
}

.arch-signals li {
  font-size: 0.75rem;
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
  line-height: 1.5;
}

.arch-desc {
  margin: var(--ds-space-2, 0.5rem) 0 0;
  font-size: 0.75rem;
  color: var(--ds-color-text-tertiary, #999);
  font-style: italic;
}
</style>
