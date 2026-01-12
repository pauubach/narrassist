<template>
  <div class="behavior-expectations">
    <!-- Header -->
    <div class="expectations-header">
      <div class="header-left">
        <i class="pi pi-sparkles"></i>
        <h3>Expectativas de Comportamiento</h3>
        <Tag v-if="llmAvailable" severity="success" size="small">
          {{ llmBackend === 'ollama' ? 'Ollama' : 'Local' }}
        </Tag>
        <Tag v-else severity="warning" size="small">No disponible</Tag>
      </div>
      <div class="header-actions">
        <Button
          v-if="llmAvailable && !profile"
          label="Analizar"
          icon="pi pi-play"
          :loading="analyzing"
          size="small"
          @click="analyzeCharacter"
        />
        <Button
          v-if="profile"
          icon="pi pi-refresh"
          text
          rounded
          size="small"
          :loading="analyzing"
          @click="analyzeCharacter"
          v-tooltip.bottom="'Re-analizar'"
        />
      </div>
    </div>

    <!-- LLM No Disponible - usar análisis básico -->
    <div v-if="!llmAvailable && !checking" class="llm-basic-mode">
      <i class="pi pi-info-circle"></i>
      <div class="basic-mode-text">
        <p>Usando análisis básico</p>
        <small>Los métodos de reglas y embeddings están disponibles para el análisis de comportamiento.</small>
      </div>
    </div>

    <!-- Loading -->
    <div v-else-if="checking || analyzing" class="loading-state">
      <ProgressSpinner style="width: 30px; height: 30px" />
      <p>{{ analyzing ? 'Analizando personaje...' : 'Verificando disponibilidad...' }}</p>
    </div>

    <!-- Profile Content -->
    <div v-else-if="profile" class="profile-content">
      <!-- Personality Traits -->
      <div class="profile-section">
        <h4><i class="pi pi-user"></i> Rasgos de Personalidad</h4>
        <div v-if="profile.personality_traits.length > 0" class="trait-list">
          <Tag
            v-for="(trait, idx) in profile.personality_traits"
            :key="idx"
            severity="info"
            class="trait-tag"
          >
            {{ trait }}
          </Tag>
        </div>
        <p v-else class="empty-text">No se detectaron rasgos</p>
      </div>

      <!-- Values -->
      <div class="profile-section">
        <h4><i class="pi pi-heart"></i> Valores</h4>
        <div v-if="profile.values.length > 0" class="trait-list">
          <Tag
            v-for="(value, idx) in profile.values"
            :key="idx"
            severity="success"
            class="trait-tag"
          >
            {{ value }}
          </Tag>
        </div>
        <p v-else class="empty-text">No se detectaron valores</p>
      </div>

      <!-- Goals -->
      <div class="profile-section">
        <h4><i class="pi pi-flag"></i> Objetivos</h4>
        <div v-if="profile.goals.length > 0" class="goals-list">
          <div v-for="(goal, idx) in profile.goals" :key="idx" class="goal-item">
            <i class="pi pi-arrow-right"></i>
            <span>{{ goal }}</span>
          </div>
        </div>
        <p v-else class="empty-text">No se detectaron objetivos</p>
      </div>

      <!-- Behavioral Expectations -->
      <div class="profile-section">
        <h4><i class="pi pi-eye"></i> Expectativas Comportamentales</h4>
        <div v-if="profile.expectations.length > 0" class="expectations-list">
          <div
            v-for="(exp, idx) in profile.expectations"
            :key="idx"
            class="expectation-item"
            :class="`expectation-${exp.expectation_type}`"
          >
            <div class="expectation-header">
              <Tag :severity="getExpectationTypeSeverity(exp.expectation_type)" size="small">
                {{ getExpectationTypeLabel(exp.expectation_type) }}
              </Tag>
              <span class="confidence">{{ (exp.confidence * 100).toFixed(0) }}% confianza</span>
            </div>
            <p class="expectation-description">{{ exp.description }}</p>
            <div class="expectation-reasoning">
              <small><strong>Razonamiento:</strong> {{ exp.reasoning }}</small>
            </div>
            <div v-if="exp.source_chapters.length > 0" class="expectation-sources">
              <small>Capítulos: {{ exp.source_chapters.join(', ') }}</small>
            </div>
            <div v-if="exp.votes && Object.keys(exp.votes).length > 0" class="expectation-votes">
              <small><strong>Métodos:</strong>
                <Tag
                  v-for="(score, method) in exp.votes"
                  :key="String(method)"
                  :severity="getMethodSeverity(String(method))"
                  size="small"
                  class="method-tag"
                >
                  {{ getMethodLabel(String(method)) }}: {{ (Number(score) * 100).toFixed(0) }}%
                </Tag>
              </small>
            </div>
          </div>
        </div>
        <p v-else class="empty-text">No se generaron expectativas</p>
      </div>

      <!-- Methods Used -->
      <div v-if="profile.methods_used && profile.methods_used.length > 0" class="profile-section methods-section">
        <h4><i class="pi pi-cog"></i> Métodos de Análisis Usados</h4>
        <div class="methods-list">
          <Tag
            v-for="method in profile.methods_used"
            :key="method"
            :severity="getMethodSeverity(method)"
            class="method-tag"
          >
            {{ getMethodLabel(method) }}
          </Tag>
        </div>
      </div>

      <!-- Violations Button -->
      <div class="violations-section">
        <Button
          label="Detectar Violaciones"
          icon="pi pi-search"
          :loading="detectingViolations"
          severity="warning"
          outlined
          @click="detectViolations"
        />
        <small>Analiza el texto buscando acciones que contradigan las expectativas</small>
      </div>

      <!-- Violations List -->
      <div v-if="violations.length > 0" class="violations-list">
        <h4><i class="pi pi-exclamation-triangle"></i> Violaciones Detectadas ({{ violations.length }})</h4>
        <div
          v-for="(violation, idx) in violations"
          :key="idx"
          class="violation-item"
          :class="`violation-${violation.severity}`"
        >
          <div class="violation-header">
            <Tag :severity="getViolationSeverity(violation.severity)">
              {{ getViolationSeverityLabel(violation.severity) }}
            </Tag>
            <span class="violation-chapter">Capítulo {{ violation.chapter_number }}</span>
          </div>
          <div class="violation-text">
            <i class="pi pi-quote-left"></i>
            <span>"{{ violation.violation_text }}"</span>
          </div>
          <p class="violation-explanation">{{ violation.explanation }}</p>
          <div v-if="violation.possible_justifications.length > 0" class="justifications">
            <strong>Posibles justificaciones:</strong>
            <ul>
              <li v-for="(just, jIdx) in violation.possible_justifications" :key="jIdx">{{ just }}</li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- No Profile Yet -->
    <div v-else-if="llmAvailable" class="no-profile">
      <i class="pi pi-lightbulb empty-icon"></i>
      <p>Haz clic en "Analizar" para que la IA infiera las expectativas de comportamiento del personaje.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import ProgressSpinner from 'primevue/progressspinner'

interface BehaviorProfile {
  character_id: number
  character_name: string
  personality_traits: string[]
  values: string[]
  fears: string[]
  goals: string[]
  speech_patterns: string[]
  expectations: Array<{
    expectation_type: string
    description: string
    reasoning: string
    confidence: number
    source_chapters: number[]
    related_traits: string[]
    inference_method?: string
    votes?: Record<string, number>
  }>
  methods_used?: string[]
}

interface Violation {
  violation_text: string
  chapter_number: number
  position: number
  severity: string
  explanation: string
  possible_justifications: string[]
}

const props = defineProps<{
  projectId: number
  characterId: number
}>()

const emit = defineEmits<{
  profileLoaded: [profile: BehaviorProfile]
  violationsFound: [violations: Violation[]]
}>()

// State
const checking = ref(true)
const analyzing = ref(false)
const detectingViolations = ref(false)
const llmAvailable = ref(false)
const llmBackend = ref<string>('none')
const llmModel = ref<string | null>(null)
const availableMethods = ref<string[]>([])
const profile = ref<BehaviorProfile | null>(null)
const violations = ref<Violation[]>([])

// Check LLM availability on mount
onMounted(async () => {
  await checkLLMStatus()
})

const checkLLMStatus = async () => {
  checking.value = true
  try {
    const response = await fetch('http://localhost:8008/api/llm/status')
    const data = await response.json()
    if (data.success) {
      llmAvailable.value = data.data?.available || false
      llmBackend.value = data.data?.backend || 'none'
      llmModel.value = data.data?.model || null
      availableMethods.value = data.data?.available_methods || []
    }
  } catch (err) {
    console.error('Error checking LLM status:', err)
    llmAvailable.value = false
  } finally {
    checking.value = false
  }
}

const analyzeCharacter = async () => {
  analyzing.value = true
  try {
    const response = await fetch(
      `/api/projects/${props.projectId}/characters/${props.characterId}/analyze-behavior`,
      { method: 'POST' }
    )
    const data = await response.json()

    if (data.success) {
      profile.value = data.data
      emit('profileLoaded', data.data)
    } else {
      console.error('Error analyzing character:', data.error)
    }
  } catch (err) {
    console.error('Error analyzing character:', err)
  } finally {
    analyzing.value = false
  }
}

const detectViolations = async () => {
  detectingViolations.value = true
  try {
    const response = await fetch(
      `/api/projects/${props.projectId}/characters/${props.characterId}/detect-violations`,
      { method: 'POST' }
    )
    const data = await response.json()

    if (data.success) {
      violations.value = data.data?.violations || []
      emit('violationsFound', violations.value)
    } else {
      console.error('Error detecting violations:', data.error)
    }
  } catch (err) {
    console.error('Error detecting violations:', err)
  } finally {
    detectingViolations.value = false
  }
}

// Helpers
const getExpectationTypeSeverity = (type: string): string => {
  const severities: Record<string, string> = {
    behavioral: 'info',
    relational: 'success',
    knowledge: 'warning',
    capability: 'secondary',
    temporal: 'contrast',
    contextual: 'help'
  }
  return severities[type] || 'secondary'
}

const getExpectationTypeLabel = (type: string): string => {
  const labels: Record<string, string> = {
    behavioral: 'Comportamiento',
    relational: 'Relacional',
    knowledge: 'Conocimiento',
    capability: 'Capacidad',
    temporal: 'Temporal',
    contextual: 'Contextual'
  }
  return labels[type] || type
}

const getViolationSeverity = (severity: string): string => {
  const severities: Record<string, string> = {
    critical: 'danger',
    high: 'warning',
    medium: 'info',
    low: 'secondary'
  }
  return severities[severity] || 'secondary'
}

const getViolationSeverityLabel = (severity: string): string => {
  const labels: Record<string, string> = {
    critical: 'Crítica',
    high: 'Alta',
    medium: 'Media',
    low: 'Baja'
  }
  return labels[severity] || severity
}

// Method helpers
const getMethodLabel = (method: string): string => {
  const labels: Record<string, string> = {
    'llama3.2': 'Llama 3.2',
    'mistral': 'Mistral',
    'gemma2': 'Gemma 2',
    'qwen2.5': 'Qwen 2.5',
    'rule_based': 'Reglas',
    'embeddings': 'Embeddings'
  }
  return labels[method] || method
}

const getMethodSeverity = (method: string): string => {
  const severities: Record<string, string> = {
    'llama3.2': 'info',
    'mistral': 'success',
    'gemma2': 'warning',
    'qwen2.5': 'success',
    'rule_based': 'secondary',
    'embeddings': 'contrast'
  }
  return severities[method] || 'secondary'
}
</script>

<style scoped>
.behavior-expectations {
  background: var(--surface-card);
  border-radius: 8px;
  padding: 1.5rem;
}

.expectations-header {
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

.llm-basic-mode {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 6px;
  border-left: 4px solid var(--primary-color);
}

.llm-basic-mode i {
  color: var(--primary-color);
  font-size: 1.25rem;
  margin-top: 0.1rem;
}

.basic-mode-text p {
  margin: 0;
  font-weight: 500;
  color: var(--text-color);
}

.basic-mode-text small {
  color: var(--text-color-secondary);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem;
  gap: 0.75rem;
  color: var(--text-color-secondary);
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

.trait-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.trait-tag {
  font-size: 0.8125rem;
}

.goals-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.goal-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  font-size: 0.875rem;
}

.goal-item i {
  color: var(--primary-color);
  font-size: 0.75rem;
  margin-top: 0.25rem;
}

.expectations-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.expectation-item {
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 6px;
  border-left: 4px solid var(--primary-color);
}

.expectation-item.expectation-relational { border-color: var(--green-500); }
.expectation-item.expectation-knowledge { border-color: var(--yellow-500); }
.expectation-item.expectation-capability { border-color: var(--purple-500); }

.expectation-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.confidence {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.expectation-description {
  margin: 0.5rem 0;
  font-size: 0.9rem;
  line-height: 1.5;
}

.expectation-reasoning {
  padding: 0.5rem;
  background: var(--surface-100);
  border-radius: 4px;
  margin-top: 0.5rem;
}

.expectation-reasoning small {
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
}

.expectation-sources {
  margin-top: 0.5rem;
}

.expectation-sources small {
  color: var(--text-color-secondary);
  font-size: 0.75rem;
}

.violations-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 6px;
  margin-top: 0.5rem;
}

.violations-section small {
  color: var(--text-color-secondary);
  font-size: 0.8125rem;
}

.violations-list {
  margin-top: 1rem;
}

.violations-list h4 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 1rem 0;
  color: var(--red-500);
  font-size: 0.9rem;
}

.violation-item {
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 6px;
  border-left: 4px solid var(--red-500);
  margin-bottom: 0.75rem;
}

.violation-item.violation-high { border-color: var(--orange-500); }
.violation-item.violation-medium { border-color: var(--yellow-500); }
.violation-item.violation-low { border-color: var(--gray-400); }

.violation-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.violation-chapter {
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
}

.violation-text {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.75rem;
  background: var(--surface-100);
  border-radius: 4px;
  font-style: italic;
  font-size: 0.875rem;
  line-height: 1.5;
}

.violation-text i {
  color: var(--text-color-secondary);
  font-size: 0.75rem;
  margin-top: 0.25rem;
}

.violation-explanation {
  margin: 0.75rem 0 0 0;
  font-size: 0.875rem;
  line-height: 1.5;
}

.justifications {
  margin-top: 0.75rem;
  padding: 0.75rem;
  background: var(--green-50);
  border-radius: 4px;
  font-size: 0.8125rem;
}

.justifications strong {
  color: var(--green-700);
}

.justifications ul {
  margin: 0.5rem 0 0 0;
  padding-left: 1.25rem;
}

.justifications li {
  color: var(--green-800);
  margin-bottom: 0.25rem;
}

.empty-text {
  margin: 0;
  color: var(--text-color-secondary);
  font-size: 0.875rem;
  font-style: italic;
}

/* Methods section */
.methods-section {
  padding: 0.75rem;
  background: var(--surface-50);
  border-radius: 6px;
}

.methods-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.method-tag {
  font-size: 0.75rem;
}

.expectation-votes {
  margin-top: 0.5rem;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem;
}

.expectation-votes small {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem;
  color: var(--text-color-secondary);
  font-size: 0.75rem;
}

.basic-mode-text code {
  background: var(--surface-100);
  padding: 0.125rem 0.25rem;
  border-radius: 3px;
  font-size: 0.8rem;
}
</style>
