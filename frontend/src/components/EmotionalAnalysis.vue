<template>
  <div class="emotional-analysis">
    <!-- Header -->
    <div class="analysis-header">
      <div class="header-left">
        <i class="pi pi-heart"></i>
        <h3>Análisis Emocional</h3>
      </div>
      <div class="header-actions">
        <Button
          v-if="!loading && !profile"
          label="Analizar"
          icon="pi pi-play"
          :loading="loading"
          size="small"
          @click="analyzeEmotions"
        />
        <Button
          v-if="profile"
          v-tooltip.bottom="'Re-analizar'"
          icon="pi pi-refresh"
          text
          rounded
          size="small"
          :loading="loading"
          @click="analyzeEmotions"
        />
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner style="width: 30px; height: 30px" />
      <p>Analizando emociones...</p>
    </div>

    <!-- Error State -->
    <Message v-else-if="error" severity="error" :closable="false" class="error-message">
      {{ error }}
    </Message>

    <!-- Empty State -->
    <div v-else-if="!profile" class="empty-state">
      <i class="pi pi-heart"></i>
      <p>Analiza las emociones del personaje</p>
      <small>Detecta estados emocionales e incoherencias en el texto</small>
    </div>

    <!-- Profile Content -->
    <div v-else class="profile-content">
      <!-- Stats Summary -->
      <div class="stats-summary">
        <div class="stat-item">
          <span class="stat-value">{{ profile.stats?.total_states || 0 }}</span>
          <span class="stat-label">Estados detectados</span>
        </div>
        <div class="stat-item" :class="{ 'has-issues': (profile.stats?.total_incoherences || 0) > 0 }">
          <span class="stat-value">{{ profile.stats?.total_incoherences || 0 }}</span>
          <span class="stat-label">Incoherencias</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ profile.stats?.chapters_with_presence || 0 }}</span>
          <span class="stat-label">Capítulos</span>
        </div>
      </div>

      <!-- Emotional Evolution Timeline -->
      <div v-if="profile.evolution && profile.evolution.length > 0" class="profile-section">
        <h4><i class="pi pi-chart-line"></i> Evolución Emocional</h4>
        <div class="evolution-timeline">
          <div
            v-for="evo in profile.evolution"
            :key="evo.chapter"
            v-tooltip.top="getEvolutionTooltip(evo)"
            class="evolution-point"
            :class="{ 'has-incoherence': evo.has_incoherences }"
          >
            <div class="point-marker">
              <span class="chapter-num">{{ evo.chapter }}</span>
            </div>
            <div class="emotion-label">
              <Tag :severity="getEmotionSeverity(evo.dominant_emotion)">
                {{ evo.dominant_emotion }}
              </Tag>
            </div>
          </div>
        </div>
      </div>

      <!-- Emotional States -->
      <div v-if="profile.emotional_states && profile.emotional_states.length > 0" class="profile-section">
        <h4>
          <i class="pi pi-list"></i>
          Estados Emocionales
          <span class="count-badge">({{ profile.emotional_states.length }})</span>
        </h4>
        <div class="states-list">
          <div
            v-for="(state, idx) in visibleStates"
            :key="idx"
            class="state-item"
          >
            <Tag :severity="getEmotionSeverity(state.emotion)" class="emotion-tag">
              {{ state.emotion }}
            </Tag>
            <span class="state-chapter">Cap. {{ state.chapter }}</span>
            <span v-if="state.context" class="state-context">
              "{{ truncateText(state.context, 60) }}"
            </span>
          </div>
          <Button
            v-if="profile.emotional_states.length > maxVisibleStates"
            :label="showAllStates ? 'Ver menos' : `Ver ${profile.emotional_states.length - maxVisibleStates} más`"
            text
            size="small"
            @click="showAllStates = !showAllStates"
          />
        </div>
      </div>

      <!-- Incoherences -->
      <div v-if="profile.incoherences && profile.incoherences.length > 0" class="profile-section incoherences-section">
        <h4>
          <i class="pi pi-exclamation-triangle"></i>
          Incoherencias Detectadas
          <span class="count-badge warning">({{ profile.incoherences.length }})</span>
        </h4>
        <div class="incoherences-list">
          <div
            v-for="(inc, idx) in profile.incoherences"
            :key="idx"
            class="incoherence-item"
            :class="`type-${inc.incoherence_type}`"
          >
            <div class="incoherence-header">
              <Tag :severity="getIncoherenceTypeSeverity(inc.incoherence_type)" size="small">
                {{ getIncoherenceTypeLabel(inc.incoherence_type) }}
              </Tag>
              <span class="confidence">{{ (inc.confidence * 100).toFixed(0) }}%</span>
              <span v-if="inc.chapter_id" class="chapter-ref">Cap. {{ inc.chapter_id }}</span>
            </div>
            <p class="incoherence-explanation">{{ inc.explanation }}</p>
            <div class="incoherence-details">
              <div v-if="inc.declared_emotion" class="detail-row">
                <span class="detail-label">Emoción declarada:</span>
                <Tag severity="info" size="small">{{ inc.declared_emotion }}</Tag>
              </div>
              <div v-if="inc.actual_behavior" class="detail-row">
                <span class="detail-label">Comportamiento:</span>
                <span class="detail-value">{{ inc.actual_behavior }}</span>
              </div>
            </div>
            <div v-if="inc.behavior_text" class="incoherence-excerpt">
              <small>"{{ truncateText(inc.behavior_text, 150) }}"</small>
            </div>
            <div v-if="inc.suggestion" class="incoherence-suggestion">
              <i class="pi pi-lightbulb"></i>
              <small>{{ inc.suggestion }}</small>
            </div>
          </div>
        </div>
      </div>

      <!-- No incoherences -->
      <div v-else class="no-incoherences">
        <i class="pi pi-check-circle"></i>
        <p>No se detectaron incoherencias emocionales</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import { api } from '@/services/apiClient'

interface EmotionalState {
  emotion: string
  intensity?: string
  chapter: number
  position: number
  context?: string
}

interface EmotionalIncoherence {
  entity_name: string
  incoherence_type: string
  declared_emotion: string
  actual_behavior: string
  declared_text: string
  behavior_text: string
  confidence: number
  explanation: string
  suggestion?: string
  chapter_id?: number
  start_char: number
  end_char: number
}

interface EmotionalEvolution {
  chapter: number
  dominant_emotion: string
  emotion_count: number
  has_incoherences: boolean
}

interface EmotionalProfile {
  character_name: string
  emotional_states: EmotionalState[]
  evolution: EmotionalEvolution[]
  incoherences: EmotionalIncoherence[]
  stats: {
    total_states: number
    total_incoherences: number
    chapters_with_presence: number
  }
}

const props = defineProps<{
  projectId: number
  characterName: string
}>()

const loading = ref(false)
const error = ref<string | null>(null)
const profile = ref<EmotionalProfile | null>(null)
const showAllStates = ref(false)
const maxVisibleStates = 5

const visibleStates = computed(() => {
  if (!profile.value?.emotional_states) return []
  if (showAllStates.value) return profile.value.emotional_states
  return profile.value.emotional_states.slice(0, maxVisibleStates)
})

const analyzeEmotions = async () => {
  loading.value = true
  error.value = null

  try {
    const data = await api.getRaw<any>(
      `/api/projects/${props.projectId}/characters/${encodeURIComponent(props.characterName)}/emotional-profile`
    )

    if (data.success) {
      profile.value = data.data
    } else {
      error.value = data.error || 'No se pudo completar la operación. Recarga la página si persiste.'
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'No se pudo cargar el análisis emocional. Recarga la página si persiste.'
  } finally {
    loading.value = false
  }
}

const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

const getEmotionSeverity = (emotion: string): string => {
  const negativeEmotions = ['triste', 'furioso', 'enfadado', 'asustado', 'aterrado', 'desesperado', 'angustiado']
  const positiveEmotions = ['feliz', 'alegre', 'emocionado', 'satisfecho', 'contento', 'entusiasmado']

  if (negativeEmotions.some(e => emotion.toLowerCase().includes(e))) return 'danger'
  if (positiveEmotions.some(e => emotion.toLowerCase().includes(e))) return 'success'
  return 'info'
}

const getIncoherenceTypeSeverity = (type: string): string => {
  switch (type) {
    case 'emotion_dialogue': return 'warning'
    case 'emotion_action': return 'info'
    case 'temporal_jump': return 'secondary'
    case 'narrator_bias': return 'contrast'
    default: return 'info'
  }
}

const getIncoherenceTypeLabel = (type: string): string => {
  const labels: Record<string, string> = {
    'emotion_dialogue': 'Diálogo',
    'emotion_action': 'Acción',
    'temporal_jump': 'Cambio brusco',
    'narrator_bias': 'Narrador',
  }
  return labels[type] || type
}

const getEvolutionTooltip = (evo: EmotionalEvolution): string => {
  let tooltip = `Capítulo ${evo.chapter}\nEmoción: ${evo.dominant_emotion}\n${evo.emotion_count} estados`
  if (evo.has_incoherences) {
    tooltip += '\n⚠️ Con incoherencias'
  }
  return tooltip
}

// Auto-analyze when character changes
watch(
  () => props.characterName,
  (newName) => {
    if (newName) {
      profile.value = null
    }
  }
)
</script>

<style scoped>
.emotional-analysis {
  background: var(--surface-card);
  border-radius: 8px;
  padding: 1rem;
}

.analysis-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--surface-border);
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
  font-size: 1.2rem;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem;
  color: var(--text-color-secondary);
  text-align: center;
}

.empty-state i {
  font-size: 2rem;
  margin-bottom: 0.5rem;
  opacity: 0.5;
}

.stats-summary {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  padding: 0.75rem;
  background: var(--surface-ground);
  border-radius: 6px;
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.stat-item.has-issues .stat-value {
  color: var(--red-500);
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--primary-color);
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.profile-section {
  margin-bottom: 1.25rem;
}

.profile-section h4 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 0.75rem 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-color);
}

.profile-section h4 i {
  color: var(--primary-color);
}

.count-badge {
  font-weight: 400;
  color: var(--text-color-secondary);
}

.count-badge.warning {
  color: var(--orange-500);
}

/* Evolution Timeline */
.evolution-timeline {
  display: flex;
  gap: 0.5rem;
  overflow-x: auto;
  padding: 0.5rem 0;
}

.evolution-point {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  min-width: 60px;
}

.evolution-point.has-incoherence .point-marker {
  border-color: var(--orange-500);
  background: var(--orange-50);
}

.point-marker {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 2px solid var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-card);
}

.chapter-num {
  font-size: 0.75rem;
  font-weight: 600;
}

.emotion-label {
  font-size: 0.7rem;
}

/* States List */
.states-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.state-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: var(--surface-ground);
  border-radius: 4px;
  font-size: 0.85rem;
}

.emotion-tag {
  min-width: 80px;
  text-align: center;
}

.state-chapter {
  font-weight: 500;
  color: var(--text-color-secondary);
  white-space: nowrap;
}

.state-context {
  flex: 1;
  color: var(--text-color-secondary);
  font-style: italic;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Incoherences */
.incoherences-section h4 i {
  color: var(--orange-500);
}

.incoherences-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.incoherence-item {
  padding: 0.75rem;
  background: var(--surface-ground);
  border-radius: 6px;
  border-left: 3px solid var(--orange-400);
}

.incoherence-item.type-emotion_dialogue {
  border-left-color: var(--yellow-500);
}

.incoherence-item.type-emotion_action {
  border-left-color: var(--blue-500);
}

.incoherence-item.type-temporal_jump {
  border-left-color: var(--purple-500);
}

.incoherence-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.confidence {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.chapter-ref {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  margin-left: auto;
}

.incoherence-explanation {
  margin: 0 0 0.5rem 0;
  font-size: 0.9rem;
  line-height: 1.4;
}

.incoherence-details {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 0.5rem;
}

.detail-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
}

.detail-label {
  color: var(--text-color-secondary);
}

.incoherence-excerpt {
  padding: 0.5rem;
  background: var(--surface-card);
  border-radius: 4px;
  color: var(--text-color-secondary);
  font-style: italic;
  margin-bottom: 0.5rem;
}

.incoherence-suggestion {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.5rem;
  background: var(--green-50);
  border-radius: 4px;
  color: var(--green-700);
}

.incoherence-suggestion i {
  color: var(--green-500);
  margin-top: 2px;
}

.no-incoherences {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  background: var(--green-50);
  border-radius: 6px;
  color: var(--green-700);
}

.no-incoherences i {
  font-size: 1.25rem;
  color: var(--green-500);
}

.error-message {
  margin: 0;
}
</style>
