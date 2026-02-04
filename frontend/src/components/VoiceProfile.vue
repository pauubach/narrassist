<template>
  <div class="voice-profile">
    <!-- Header -->
    <div class="profile-header">
      <div class="header-left">
        <i class="pi pi-volume-up"></i>
        <h3>Perfil de Voz</h3>
        <Tag v-if="profile" severity="success" size="small">
          {{ (profile.confidence * 100).toFixed(0) }}% confianza
        </Tag>
      </div>
      <div class="header-actions">
        <Button
          v-if="!profile && !loading"
          label="Analizar"
          icon="pi pi-play"
          :loading="loading"
          size="small"
          @click="loadProfile"
        />
        <Button
          v-if="profile"
          v-tooltip.bottom="'Actualizar'"
          icon="pi pi-refresh"
          text
          rounded
          size="small"
          :loading="loading"
          @click="loadProfile"
        />
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner style="width: 30px; height: 30px" />
      <p>Analizando perfil de voz...</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="error-state">
      <i class="pi pi-exclamation-triangle"></i>
      <p>{{ error }}</p>
      <Button label="Reintentar" size="small" @click="loadProfile" />
    </div>

    <!-- Profile Content -->
    <div v-else-if="profile" class="profile-content">
      <!-- Voice Metrics -->
      <div class="profile-section">
        <h4><i class="pi pi-chart-bar"></i> Métricas de Voz</h4>
        <div class="metrics-grid">
          <div class="metric-card">
            <span class="metric-value">{{ formatNumber(profile.metrics.avgInterventionLength) }}</span>
            <span class="metric-label">Palabras/Intervención</span>
          </div>
          <div class="metric-card">
            <span class="metric-value">{{ formatPercent(profile.metrics.typeTokenRatio) }}</span>
            <span class="metric-label">Diversidad Léxica</span>
          </div>
          <div class="metric-card">
            <span class="metric-value">{{ getFormalityLabel(profile.metrics.formalityScore) }}</span>
            <span class="metric-label">Formalidad</span>
          </div>
          <div class="metric-card">
            <span class="metric-value">{{ formatPercent(profile.metrics.questionRatio) }}</span>
            <span class="metric-label">Preguntas</span>
          </div>
        </div>
      </div>

      <!-- Extended Metrics -->
      <div class="profile-section">
        <h4><i class="pi pi-sliders-h"></i> Métricas Detalladas</h4>
        <div class="extended-metrics">
          <div class="metric-row">
            <span class="metric-name">Exclamaciones</span>
            <ProgressBar
              :value="profile.metrics.exclamationRatio * 100"
              :show-value="false"
              style="height: 8px; width: 100px"
            />
            <span class="metric-percent">{{ formatPercent(profile.metrics.exclamationRatio) }}</span>
          </div>
          <div class="metric-row">
            <span class="metric-name">Muletillas</span>
            <ProgressBar
              :value="profile.metrics.fillerRatio * 100"
              :show-value="false"
              style="height: 8px; width: 100px"
            />
            <span class="metric-percent">{{ formatPercent(profile.metrics.fillerRatio) }}</span>
          </div>
          <div class="metric-row">
            <span class="metric-name">Total intervenciones</span>
            <span class="metric-count">{{ profile.metrics.totalInterventions }}</span>
          </div>
          <div class="metric-row">
            <span class="metric-name">Total palabras</span>
            <span class="metric-count">{{ profile.metrics.totalWords.toLocaleString() }}</span>
          </div>
        </div>
      </div>

      <!-- Characteristic Words -->
      <div v-if="profile.characteristicWords.length > 0" class="profile-section">
        <h4><i class="pi pi-key"></i> Palabras Características</h4>
        <div class="words-list">
          <Tag
            v-for="(item, idx) in profile.characteristicWords.slice(0, 15)"
            :key="idx"
            :severity="getWordSeverity(item.score)"
            class="word-tag"
          >
            {{ item.word }}
            <span class="word-score">{{ (item.score * 100).toFixed(0) }}</span>
          </Tag>
        </div>
      </div>

      <!-- Top Fillers -->
      <div v-if="profile.topFillers.length > 0" class="profile-section">
        <h4><i class="pi pi-comment"></i> Muletillas Frecuentes</h4>
        <div class="fillers-list">
          <div
            v-for="(filler, idx) in profile.topFillers.slice(0, 10)"
            :key="idx"
            class="filler-item"
          >
            <span class="filler-word">"{{ filler.word }}"</span>
            <span class="filler-count">{{ filler.count }}x</span>
          </div>
        </div>
      </div>

      <!-- Speech Patterns -->
      <div class="profile-section">
        <h4><i class="pi pi-comments"></i> Patrones de Habla</h4>

        <!-- Start Patterns -->
        <div v-if="profile.speechPatterns.startPatterns.length > 0" class="pattern-group">
          <span class="pattern-label">Formas de empezar:</span>
          <div class="patterns">
            <Chip
              v-for="(pattern, idx) in profile.speechPatterns.startPatterns.slice(0, 5)"
              :key="idx"
              :label="pattern"
            />
          </div>
        </div>

        <!-- End Patterns -->
        <div v-if="profile.speechPatterns.endPatterns.length > 0" class="pattern-group">
          <span class="pattern-label">Formas de terminar:</span>
          <div class="patterns">
            <Chip
              v-for="(pattern, idx) in profile.speechPatterns.endPatterns.slice(0, 5)"
              :key="idx"
              :label="pattern"
            />
          </div>
        </div>

        <!-- Expressions -->
        <div v-if="profile.speechPatterns.expressions.length > 0" class="pattern-group">
          <span class="pattern-label">Expresiones típicas:</span>
          <div class="patterns">
            <Chip
              v-for="(expr, idx) in profile.speechPatterns.expressions.slice(0, 5)"
              :key="idx"
              :label="expr"
            />
          </div>
        </div>

        <p v-if="noPatterns" class="empty-text">No se detectaron patrones de habla distintivos</p>
      </div>
    </div>

    <!-- No Profile Yet -->
    <div v-else class="no-profile">
      <i class="pi pi-microphone empty-icon"></i>
      <p>Haz clic en "Analizar" para generar el perfil de voz del personaje basado en sus diálogos.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Chip from 'primevue/chip'
import ProgressBar from 'primevue/progressbar'
import ProgressSpinner from 'primevue/progressspinner'
import { useVoiceAndStyleStore } from '@/stores/voiceAndStyle'
import type { VoiceProfile } from '@/types'

const props = defineProps<{
  projectId: number
  characterId: number
  characterName: string
}>()

const store = useVoiceAndStyleStore()

// State
const loading = ref(false)
const error = ref<string | null>(null)

// Get profile from store
const profile = computed<VoiceProfile | null>(() => {
  const profiles = store.getVoiceProfiles(props.projectId)
  return profiles.find(p => p.entityId === props.characterId) || null
})

// Check if there are no speech patterns
const noPatterns = computed(() => {
  if (!profile.value) return true
  const sp = profile.value.speechPatterns
  return sp.startPatterns.length === 0 &&
         sp.endPatterns.length === 0 &&
         sp.expressions.length === 0
})

// Load profile
const loadProfile = async () => {
  loading.value = true
  error.value = null

  try {
    const success = await store.fetchVoiceProfiles(props.projectId)
    if (!success) {
      error.value = store.error || 'Error al cargar el perfil de voz'
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Error desconocido'
  } finally {
    loading.value = false
  }
}

// Format helpers
const formatNumber = (value: number): string => {
  return value.toFixed(1)
}

const formatPercent = (value: number): string => {
  return `${(value * 100).toFixed(1)}%`
}

const getFormalityLabel = (score: number): string => {
  if (score >= 0.7) return 'Formal'
  if (score >= 0.4) return 'Neutral'
  return 'Coloquial'
}

const getWordSeverity = (score: number): string => {
  if (score >= 0.7) return 'success'
  if (score >= 0.4) return 'info'
  return 'secondary'
}

// Auto-load on mount if we have projectId
onMounted(() => {
  if (props.projectId && !profile.value) {
    // Check if store already has data
    const existingProfiles = store.voiceProfiles[props.projectId]
    if (!existingProfiles) {
      loadProfile()
    }
  }
})

// Watch for projectId changes
watch(() => props.projectId, (newId) => {
  if (newId && !store.voiceProfiles[newId]) {
    loadProfile()
  }
})
</script>

<style scoped>
.voice-profile {
  background: var(--surface-card);
  border-radius: 8px;
  padding: 1.5rem;
}

.profile-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
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

.no-profile {
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

/* Profile Content */
.profile-content {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.profile-section {
  padding: 0;
}

.profile-section h4 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 0.75rem 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-color-secondary);
}

.profile-section h4 i {
  font-size: 0.875rem;
}

/* Metrics Grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 0.75rem;
}

.metric-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.75rem;
  background: var(--surface-50);
  border-radius: 6px;
  text-align: center;
}

.metric-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--primary-color);
}

.metric-label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  margin-top: 0.25rem;
}

/* Extended Metrics */
.extended-metrics {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.metric-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0;
}

.metric-name {
  flex: 1;
  font-size: 0.875rem;
  color: var(--text-color);
}

.metric-percent,
.metric-count {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-color-secondary);
  min-width: 50px;
  text-align: right;
}

/* Words List */
.words-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.word-tag {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.word-score {
  font-size: 0.7rem;
  opacity: 0.7;
  margin-left: 0.25rem;
}

/* Fillers List */
.fillers-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.filler-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: var(--surface-50);
  border-radius: 6px;
  font-size: 0.875rem;
}

.filler-word {
  font-style: italic;
  color: var(--text-color);
}

.filler-count {
  font-weight: 600;
  color: var(--primary-color);
  font-size: 0.75rem;
}

/* Pattern Groups */
.pattern-group {
  margin-bottom: 0.75rem;
}

.pattern-label {
  display: block;
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
  margin-bottom: 0.5rem;
}

.patterns {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.empty-text {
  margin: 0;
  color: var(--text-color-secondary);
  font-size: 0.875rem;
  font-style: italic;
}
</style>
