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

      <!-- Speech Patterns (from LLM) -->
      <div v-if="profile.speech_patterns && profile.speech_patterns.length > 0" class="profile-section">
        <h4><i class="pi pi-comments"></i> Patrones de Habla (LLM)</h4>
        <div class="trait-list">
          <Tag
            v-for="(pattern, idx) in profile.speech_patterns"
            :key="idx"
            severity="secondary"
            class="trait-tag"
          >
            {{ pattern }}
          </Tag>
        </div>
      </div>

      <!-- Voice Metrics (from statistical analysis) -->
      <div v-if="voiceProfile" class="profile-section voice-metrics-section">
        <h4><i class="pi pi-chart-bar"></i> Métricas de Voz</h4>
        <div class="voice-metrics-grid">
          <div class="voice-metric">
            <span class="metric-value">{{ formatVoiceMetric(voiceProfile.metrics.avgInterventionLength) }}</span>
            <span class="metric-label">Palabras/Intervención</span>
          </div>
          <div class="voice-metric">
            <span class="metric-value">{{ formatVoicePercent(voiceProfile.metrics.typeTokenRatio) }}</span>
            <span class="metric-label">Diversidad léxica</span>
          </div>
          <div class="voice-metric">
            <span class="metric-value">{{ getFormalityLabel(voiceProfile.metrics.formalityScore) }}</span>
            <span class="metric-label">Formalidad</span>
          </div>
          <div class="voice-metric">
            <span class="metric-value">{{ formatVoicePercent(voiceProfile.metrics.fillerRatio) }}</span>
            <span class="metric-label">Muletillas</span>
          </div>
        </div>

        <!-- Characteristic Words -->
        <div v-if="voiceProfile.characteristicWords.length > 0" class="voice-subsection">
          <span class="subsection-label">Palabras características:</span>
          <div class="words-chips">
            <Chip
              v-for="(item, idx) in voiceProfile.characteristicWords.slice(0, 8)"
              :key="idx"
              :label="item.word"
            />
          </div>
        </div>

        <!-- Top Fillers -->
        <div v-if="voiceProfile.topFillers.length > 0" class="voice-subsection">
          <span class="subsection-label">Muletillas frecuentes:</span>
          <div class="fillers-chips">
            <Chip
              v-for="(filler, idx) in voiceProfile.topFillers.slice(0, 5)"
              :key="idx"
              :label="`&quot;${filler.word}&quot; (${filler.count}x)`"
            />
          </div>
        </div>

        <!-- Compare Button -->
        <div v-if="availableForComparison.length > 0" class="voice-comparison-btn">
          <Button
            label="Comparar con otro personaje"
            icon="pi pi-users"
            text
            size="small"
            @click="openComparison"
          />
        </div>
      </div>
      <div v-else-if="!voiceProfile && profile" class="profile-section">
        <h4><i class="pi pi-chart-bar"></i> Métricas de Voz</h4>
        <div class="voice-loading">
          <Button
            label="Cargar métricas"
            icon="pi pi-download"
            text
            size="small"
            @click="loadVoiceProfile"
            :loading="voiceStore.loading"
          />
        </div>
      </div>

      <!-- Behavioral Expectations -->
      <div class="profile-section">
        <div class="section-header">
          <h4><i class="pi pi-eye"></i> Expectativas Comportamentales</h4>
          <Button
            icon="pi pi-plus"
            text
            rounded
            size="small"
            @click="openAddExpectation"
            v-tooltip.left="'Añadir expectativa manual'"
          />
        </div>
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
              <ConfidenceBadge
                :value="exp.confidence"
                variant="badge"
                size="sm"
                :show-icon="false"
                show-label
                label="confianza"
                inline
              />
              <div class="expectation-actions">
                <Button
                  icon="pi pi-pencil"
                  text
                  rounded
                  size="small"
                  @click="openEditExpectation(idx)"
                  v-tooltip.top="'Editar'"
                />
                <Button
                  icon="pi pi-trash"
                  text
                  rounded
                  size="small"
                  severity="danger"
                  @click="deleteExpectation(idx)"
                  v-tooltip.top="'Eliminar'"
                />
              </div>
            </div>
            <p class="expectation-description">{{ exp.description }}</p>
            <div class="expectation-reasoning">
              <small><strong>Razonamiento:</strong> {{ exp.reasoning }}</small>
            </div>
            <div v-if="exp.source_chapters.length > 0" class="expectation-sources">
              <small>Capítulos: {{ exp.source_chapters.join(', ') }}</small>
            </div>
            <div v-if="exp.votes && Object.keys(exp.votes).length > 1" class="expectation-votes">
              <MethodVotingBar
                :methods="formatVotesForBar(exp.votes)"
                compact
              />
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

    <!-- Diálogo de edición de expectativa -->
    <Dialog
      :visible="showExpectationDialog"
      @update:visible="showExpectationDialog = $event"
      modal
      :header="editingExpectationIndex === -1 ? 'Añadir Expectativa' : 'Editar Expectativa'"
      :style="{ width: '500px' }"
    >
      <div class="expectation-form">
        <div class="form-field">
          <label>Tipo de expectativa</label>
          <Dropdown
            v-model="editingExpectation.expectation_type"
            :options="expectationTypes"
            optionLabel="label"
            optionValue="value"
            placeholder="Selecciona un tipo"
            class="w-full"
          />
        </div>

        <div class="form-field">
          <label>Descripción</label>
          <Textarea
            v-model="editingExpectation.description"
            rows="3"
            placeholder="Describe la expectativa de comportamiento..."
            class="w-full"
          />
        </div>

        <div class="form-field">
          <label>Razonamiento</label>
          <Textarea
            v-model="editingExpectation.reasoning"
            rows="2"
            placeholder="¿Por qué se espera este comportamiento?"
            class="w-full"
          />
        </div>

        <div class="form-field">
          <label>Confianza: {{ (editingExpectation.confidence * 100).toFixed(0) }}%</label>
          <Slider v-model="editingExpectation.confidence" :min="0" :max="1" :step="0.05" class="w-full" />
        </div>
      </div>

      <template #footer>
        <Button label="Cancelar" text @click="showExpectationDialog = false" />
        <Button
          :label="editingExpectationIndex === -1 ? 'Añadir' : 'Guardar'"
          icon="pi pi-check"
          @click="saveExpectation"
          :disabled="!editingExpectation.description.trim()"
        />
      </template>
    </Dialog>

    <!-- Voice Profile Comparison Dialog -->
    <Dialog
      :visible="showComparisonDialog"
      @update:visible="showComparisonDialog = $event"
      modal
      header="Comparar Perfiles de Voz"
      :style="{ width: '700px' }"
      class="voice-comparison-dialog"
    >
      <!-- Character Selector -->
      <div class="comparison-selector">
        <label>Comparar con:</label>
        <Dropdown
          v-model="compareCharacterId"
          :options="availableForComparison"
          optionLabel="name"
          optionValue="id"
          placeholder="Selecciona un personaje"
          class="w-full"
        />
      </div>

      <!-- Comparison Table -->
      <div v-if="voiceProfile && comparisonVoiceProfile" class="comparison-content">
        <table class="comparison-table">
          <thead>
            <tr>
              <th>Métrica</th>
              <th>{{ characterName || 'Actual' }}</th>
              <th>{{ comparisonVoiceProfile.entityName }}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Palabras/Intervención</td>
              <td>{{ formatVoiceMetric(voiceProfile.metrics.avgInterventionLength) }}</td>
              <td>{{ formatVoiceMetric(comparisonVoiceProfile.metrics.avgInterventionLength) }}</td>
              <td>
                <i
                  :class="getComparisonIcon(getMetricComparison(
                    voiceProfile.metrics.avgInterventionLength,
                    comparisonVoiceProfile.metrics.avgInterventionLength
                  ))"
                ></i>
              </td>
            </tr>
            <tr>
              <td>Diversidad léxica (TTR)</td>
              <td>{{ formatVoicePercent(voiceProfile.metrics.typeTokenRatio) }}</td>
              <td>{{ formatVoicePercent(comparisonVoiceProfile.metrics.typeTokenRatio) }}</td>
              <td>
                <i
                  :class="getComparisonIcon(getMetricComparison(
                    voiceProfile.metrics.typeTokenRatio,
                    comparisonVoiceProfile.metrics.typeTokenRatio
                  ))"
                ></i>
              </td>
            </tr>
            <tr>
              <td>Formalidad</td>
              <td>{{ formatVoicePercent(voiceProfile.metrics.formalityScore) }}</td>
              <td>{{ formatVoicePercent(comparisonVoiceProfile.metrics.formalityScore) }}</td>
              <td>
                <i
                  :class="getComparisonIcon(getMetricComparison(
                    voiceProfile.metrics.formalityScore,
                    comparisonVoiceProfile.metrics.formalityScore
                  ))"
                ></i>
              </td>
            </tr>
            <tr>
              <td>Muletillas</td>
              <td>{{ formatVoicePercent(voiceProfile.metrics.fillerRatio) }}</td>
              <td>{{ formatVoicePercent(comparisonVoiceProfile.metrics.fillerRatio) }}</td>
              <td>
                <i
                  :class="getComparisonIcon(getMetricComparison(
                    voiceProfile.metrics.fillerRatio,
                    comparisonVoiceProfile.metrics.fillerRatio
                  ))"
                ></i>
              </td>
            </tr>
            <tr>
              <td>Exclamaciones</td>
              <td>{{ formatVoicePercent(voiceProfile.metrics.exclamationRatio) }}</td>
              <td>{{ formatVoicePercent(comparisonVoiceProfile.metrics.exclamationRatio) }}</td>
              <td>
                <i
                  :class="getComparisonIcon(getMetricComparison(
                    voiceProfile.metrics.exclamationRatio,
                    comparisonVoiceProfile.metrics.exclamationRatio
                  ))"
                ></i>
              </td>
            </tr>
            <tr>
              <td>Preguntas</td>
              <td>{{ formatVoicePercent(voiceProfile.metrics.questionRatio) }}</td>
              <td>{{ formatVoicePercent(comparisonVoiceProfile.metrics.questionRatio) }}</td>
              <td>
                <i
                  :class="getComparisonIcon(getMetricComparison(
                    voiceProfile.metrics.questionRatio,
                    comparisonVoiceProfile.metrics.questionRatio
                  ))"
                ></i>
              </td>
            </tr>
            <tr>
              <td>Total intervenciones</td>
              <td>{{ voiceProfile.metrics.totalInterventions }}</td>
              <td>{{ comparisonVoiceProfile.metrics.totalInterventions }}</td>
              <td>
                <i
                  :class="getComparisonIcon(getMetricComparison(
                    voiceProfile.metrics.totalInterventions,
                    comparisonVoiceProfile.metrics.totalInterventions
                  ))"
                ></i>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Characteristic Words Comparison -->
        <div class="comparison-words">
          <div class="words-column">
            <h5>Palabras de {{ characterName || 'Actual' }}</h5>
            <div class="words-chips">
              <Chip
                v-for="(item, idx) in voiceProfile.characteristicWords.slice(0, 6)"
                :key="idx"
                :label="item.word"
              />
            </div>
          </div>
          <div class="words-column">
            <h5>Palabras de {{ comparisonVoiceProfile.entityName }}</h5>
            <div class="words-chips">
              <Chip
                v-for="(item, idx) in comparisonVoiceProfile.characteristicWords.slice(0, 6)"
                :key="idx"
                :label="item.word"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- No comparison selected -->
      <div v-else-if="!compareCharacterId" class="comparison-empty">
        <p>Selecciona un personaje para comparar sus métricas de voz.</p>
      </div>

      <!-- Loading comparison profile -->
      <div v-else class="comparison-loading">
        <ProgressSpinner style="width: 30px; height: 30px" />
        <p>Cargando perfil de voz...</p>
      </div>

      <template #footer>
        <Button label="Cerrar" @click="showComparisonDialog = false" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Chip from 'primevue/chip'
import Dialog from 'primevue/dialog'
import Dropdown from 'primevue/dropdown'
import Textarea from 'primevue/textarea'
import Slider from 'primevue/slider'
import ProgressSpinner from 'primevue/progressspinner'
import ConfidenceBadge from '@/components/shared/ConfidenceBadge.vue'
import MethodVotingBar from '@/components/shared/MethodVotingBar.vue'
import { useVoiceAndStyleStore } from '@/stores/voiceAndStyle'
import type { VoiceProfile } from '@/types'

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
  characterName?: string
  allCharacters?: Array<{ id: number; name: string }>  // For comparison dropdown
}>()

const emit = defineEmits<{
  profileLoaded: [profile: BehaviorProfile]
  violationsFound: [violations: Violation[]]
}>()

// Voice profile store
const voiceStore = useVoiceAndStyleStore()

// Get voice profile from store
const voiceProfile = computed<VoiceProfile | null>(() => {
  const profiles = voiceStore.getVoiceProfiles(props.projectId)
  return profiles.find(p => p.entityId === props.characterId) || null
})

// Load voice profiles if not loaded
const loadVoiceProfile = async () => {
  if (!voiceStore.voiceProfiles[props.projectId]) {
    await voiceStore.fetchVoiceProfiles(props.projectId)
  }
}

// Format helpers for voice metrics
const formatVoiceMetric = (value: number, decimals: number = 1): string => {
  return value.toFixed(decimals)
}

const formatVoicePercent = (value: number): string => {
  return `${(value * 100).toFixed(0)}%`
}

const getFormalityLabel = (score: number): string => {
  if (score >= 0.7) return 'Formal'
  if (score >= 0.4) return 'Neutro'
  return 'Coloquial'
}

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

// Estado para edición de expectativas
const showExpectationDialog = ref(false)
const editingExpectationIndex = ref(-1)
const editingExpectation = ref({
  expectation_type: 'behavioral',
  description: '',
  reasoning: '',
  confidence: 0.8,
  source_chapters: [] as number[],
  related_traits: [] as string[],
  inference_method: 'manual'
})

const expectationTypes = [
  { label: 'Comportamiento', value: 'behavioral' },
  { label: 'Relacional', value: 'relational' },
  { label: 'Conocimiento', value: 'knowledge' },
  { label: 'Capacidad', value: 'capability' },
  { label: 'Temporal', value: 'temporal' },
  { label: 'Contextual', value: 'contextual' }
]

// Voice Profile Comparison
const showComparisonDialog = ref(false)
const compareCharacterId = ref<number | null>(null)

// Characters available for comparison (excluding current)
const availableForComparison = computed(() => {
  if (!props.allCharacters) return []
  return props.allCharacters.filter(c => c.id !== props.characterId)
})

// Get comparison voice profile
const comparisonVoiceProfile = computed<VoiceProfile | null>(() => {
  if (!compareCharacterId.value) return null
  const profiles = voiceStore.getVoiceProfiles(props.projectId)
  return profiles.find(p => p.entityId === compareCharacterId.value) || null
})

// Open comparison dialog
const openComparison = () => {
  compareCharacterId.value = null
  showComparisonDialog.value = true
}

// Compare metrics between two profiles
const getMetricComparison = (current: number, other: number): 'higher' | 'lower' | 'similar' => {
  const diff = current - other
  const threshold = Math.max(Math.abs(current), Math.abs(other)) * 0.1 // 10% threshold
  if (diff > threshold) return 'higher'
  if (diff < -threshold) return 'lower'
  return 'similar'
}

// Get icon class for comparison
const getComparisonIcon = (comparison: 'higher' | 'lower' | 'similar'): string => {
  switch (comparison) {
    case 'higher': return 'pi pi-arrow-up comparison-higher'
    case 'lower': return 'pi pi-arrow-down comparison-lower'
    default: return 'pi pi-minus comparison-similar'
  }
}

// Check LLM availability on mount
onMounted(async () => {
  await checkLLMStatus()
  // Also load voice profiles in background
  loadVoiceProfile()
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

// Format votes for MethodVotingBar component
const formatVotesForBar = (votes: Record<string, number>) => {
  const maxScore = Math.max(...Object.values(votes))
  return Object.entries(votes).map(([method, score]) => ({
    name: method,
    score: Number(score),
    agreed: Number(score) >= maxScore * 0.8 // Consider agreed if within 80% of max
  }))
}

// Funciones de edición de expectativas
const openAddExpectation = () => {
  editingExpectationIndex.value = -1
  editingExpectation.value = {
    expectation_type: 'behavioral',
    description: '',
    reasoning: '',
    confidence: 0.8,
    source_chapters: [],
    related_traits: [],
    inference_method: 'manual'
  }
  showExpectationDialog.value = true
}

const openEditExpectation = (index: number) => {
  if (!profile.value) return
  editingExpectationIndex.value = index
  const exp = profile.value.expectations[index]
  editingExpectation.value = {
    expectation_type: exp.expectation_type,
    description: exp.description,
    reasoning: exp.reasoning,
    confidence: exp.confidence,
    source_chapters: [...exp.source_chapters],
    related_traits: [...exp.related_traits],
    inference_method: exp.inference_method || 'manual'
  }
  showExpectationDialog.value = true
}

const saveExpectation = () => {
  if (!profile.value) return

  const newExp = {
    expectation_type: editingExpectation.value.expectation_type,
    description: editingExpectation.value.description,
    reasoning: editingExpectation.value.reasoning,
    confidence: editingExpectation.value.confidence,
    source_chapters: editingExpectation.value.source_chapters,
    related_traits: editingExpectation.value.related_traits,
    inference_method: 'manual',
    votes: { 'manual': 1.0 }
  }

  if (editingExpectationIndex.value === -1) {
    // Añadir nueva
    profile.value.expectations.push(newExp)
  } else {
    // Actualizar existente
    profile.value.expectations[editingExpectationIndex.value] = newExp
  }

  showExpectationDialog.value = false
  emit('profileLoaded', profile.value)
}

const deleteExpectation = (index: number) => {
  if (!profile.value) return
  profile.value.expectations.splice(index, 1)
  emit('profileLoaded', profile.value)
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
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--surface-200);
}

.basic-mode-text code {
  background: var(--surface-100);
  padding: 0.125rem 0.25rem;
  border-radius: 3px;
  font-size: 0.8rem;
}

/* Estilos para edición de expectativas */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-header h4 {
  margin: 0;
}

.expectation-header {
  position: relative;
}

.expectation-actions {
  position: absolute;
  right: 0;
  top: 0;
  display: flex;
  gap: 0.25rem;
  opacity: 0;
  transition: opacity 0.2s;
}

.expectation-item:hover .expectation-actions {
  opacity: 1;
}

.expectation-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-field label {
  font-weight: 500;
  font-size: 0.9rem;
  color: var(--text-color);
}

.w-full {
  width: 100%;
}

/* Voice Metrics Section */
.voice-metrics-section {
  background: var(--surface-50);
  padding: 1rem;
  border-radius: 6px;
}

.voice-metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.voice-metric {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.5rem;
  background: var(--surface-0);
  border-radius: 4px;
  text-align: center;
}

.voice-metric .metric-value {
  font-size: 1rem;
  font-weight: 700;
  color: var(--primary-color);
}

.voice-metric .metric-label {
  font-size: 0.7rem;
  color: var(--text-color-secondary);
  margin-top: 0.125rem;
}

.voice-subsection {
  margin-top: 0.75rem;
}

.subsection-label {
  display: block;
  font-size: 0.8rem;
  color: var(--text-color-secondary);
  margin-bottom: 0.5rem;
}

.words-chips,
.fillers-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
}

.words-chips :deep(.p-chip),
.fillers-chips :deep(.p-chip) {
  font-size: 0.75rem;
}

.voice-loading {
  display: flex;
  justify-content: center;
  padding: 0.5rem;
}

/* Voice Comparison Button */
.voice-comparison-btn {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--surface-200);
  display: flex;
  justify-content: center;
}

/* Voice Comparison Dialog */
.comparison-selector {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.comparison-selector label {
  font-weight: 500;
  color: var(--text-color);
}

.comparison-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.comparison-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.comparison-table th,
.comparison-table td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid var(--surface-200);
}

.comparison-table th {
  background: var(--surface-50);
  font-weight: 600;
  color: var(--text-color-secondary);
}

.comparison-table th:first-child {
  width: 40%;
}

.comparison-table th:last-child {
  width: 40px;
  text-align: center;
}

.comparison-table td:last-child {
  text-align: center;
}

.comparison-higher {
  color: var(--green-500);
}

.comparison-lower {
  color: var(--red-500);
}

.comparison-similar {
  color: var(--text-color-secondary);
}

.comparison-words {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.words-column h5 {
  margin: 0 0 0.5rem 0;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text-color-secondary);
}

.comparison-empty,
.comparison-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  color: var(--text-color-secondary);
  text-align: center;
}
</style>
