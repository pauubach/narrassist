<template>
  <div class="age-readability-tab">
    <!-- Header -->
    <div class="tab-header">
      <div class="header-left">
        <h3>
          <i class="pi pi-users"></i>
          Legibilidad por Edad
        </h3>
        <p class="subtitle">
          Analiza si el texto es adecuado para el grupo de edad objetivo.
        </p>
      </div>
      <div class="header-controls">
        <div class="target-control">
          <label>Edad objetivo:</label>
          <Select
            v-model="targetAgeGroup"
            :options="ageGroupOptions"
            option-label="label"
            option-value="value"
            placeholder="Seleccionar edad"
            class="age-dropdown"
          />
        </div>
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
      <p>Analizando legibilidad por edad...</p>
    </div>

    <!-- Empty state -->
    <div v-else-if="!report" class="empty-state">
      <i class="pi pi-info-circle"></i>
      <p>Haz clic en "Analizar" para evaluar la legibilidad por edad.</p>
    </div>

    <!-- Results -->
    <div v-else class="results-container">
      <!-- Estimation Card -->
      <Card class="estimation-card" :class="'age-' + report.estimated_age_group">
        <template #content>
          <div class="estimation-content">
            <div class="estimation-icon">
              <i :class="getAgeIcon(report.estimated_age_group)"></i>
            </div>
            <div class="estimation-info">
              <div class="estimation-label">Edad lectora estimada</div>
              <div class="estimation-value">{{ report.estimated_age_range }}</div>
              <div class="estimation-grade">{{ report.estimated_grade_level }}</div>
            </div>
          </div>
        </template>
      </Card>

      <!-- Appropriateness Score (if target selected) -->
      <Card v-if="report.target_comparison && targetAgeGroup" class="appropriateness-card">
        <template #title>
          <i class="pi pi-check-circle"></i>
          Adecuación al objetivo
        </template>
        <template #content>
          <div class="score-container">
            <div class="score-circle" :class="getScoreClass(report.evaluation.appropriateness_score)">
              <span class="score-value">{{ Math.round(report.evaluation.appropriateness_score) }}</span>
              <span class="score-label">/ 100</span>
            </div>
            <div class="score-status">
              <Tag
                :severity="report.evaluation.is_appropriate ? 'success' : 'danger'"
                :value="report.evaluation.is_appropriate ? 'Adecuado' : 'Necesita ajustes'"
              />
            </div>
          </div>

          <!-- Issues -->
          <div v-if="report.evaluation.issues.length > 0" class="issues-list">
            <div v-for="(issue, idx) in report.evaluation.issues" :key="idx" class="issue-item">
              <i class="pi pi-exclamation-triangle"></i>
              <span>{{ issue }}</span>
            </div>
          </div>
        </template>
      </Card>

      <!-- Vocabulary Stats -->
      <div class="stats-cards">
        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.metrics.total_words }}</div>
              <div class="stat-label">Palabras</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.metrics.avg_words_per_sentence }}</div>
              <div class="stat-label">Palabras/oración</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.vocabulary.sight_word_ratio }}%</div>
              <div class="stat-label">Palabras frecuentes</div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <div class="stat-value">{{ report.vocabulary.vocabulary_diversity }}</div>
              <div class="stat-label">Diversidad léxica</div>
            </div>
          </template>
        </Card>
      </div>

      <!-- Vocabulary Breakdown -->
      <Card class="vocabulary-card">
        <template #title>
          <i class="pi pi-book"></i>
          Complejidad del Vocabulario
        </template>
        <template #content>
          <div class="vocab-bars">
            <div class="vocab-row">
              <span class="vocab-label">Palabras simples (1-2 sílabas)</span>
              <div class="vocab-bar-container">
                <div
                  class="vocab-bar simple"
                  :style="{ width: (report.vocabulary.simple_words_ratio * 100) + '%' }"
                ></div>
              </div>
              <span class="vocab-percent">{{ (report.vocabulary.simple_words_ratio * 100).toFixed(1) }}%</span>
            </div>
            <div class="vocab-row">
              <span class="vocab-label">Palabras complejas (4+ sílabas)</span>
              <div class="vocab-bar-container">
                <div
                  class="vocab-bar complex"
                  :style="{ width: (report.vocabulary.complex_words_ratio * 100) + '%' }"
                ></div>
              </div>
              <span class="vocab-percent">{{ (report.vocabulary.complex_words_ratio * 100).toFixed(1) }}%</span>
            </div>
          </div>

          <!-- Most Repeated Words -->
          <div v-if="report.repetition.most_repeated.length > 0" class="repeated-words">
            <h4>Palabras más repetidas</h4>
            <div class="word-tags">
              <Tag
                v-for="item in report.repetition.most_repeated.slice(0, 10)"
                :key="item.word"
                :value="`${item.word} (${item.count})`"
                severity="secondary"
                class="word-tag"
              />
            </div>
          </div>
        </template>
      </Card>

      <!-- Recommendations -->
      <Card v-if="report.evaluation.recommendations.length > 0" class="recommendations-card">
        <template #title>
          <i class="pi pi-lightbulb"></i>
          Recomendaciones
        </template>
        <template #content>
          <ul class="recommendations-list">
            <li v-for="(rec, idx) in report.evaluation.recommendations" :key="idx">{{ rec }}</li>
          </ul>
        </template>
      </Card>

      <!-- Chapters Accordion -->
      <Accordion v-if="report.chapters && report.chapters.length > 0" :multiple="true" class="chapters-accordion">
        <AccordionPanel v-for="chapter in report.chapters" :key="chapter.chapter_number" :value="String(chapter.chapter_number)">
          <AccordionHeader>
            <div class="chapter-header">
              <span class="chapter-title">{{ chapter.chapter_title }}</span>
              <div class="chapter-stats">
                <Tag
                  :severity="chapter.is_appropriate ? 'success' : 'warn'"
                  :value="chapter.estimated_age_range"
                />
                <span class="chapter-score">{{ Math.round(chapter.appropriateness_score) }}%</span>
              </div>
            </div>
          </AccordionHeader>
          <AccordionContent>
            <div class="chapter-metrics">
              <div class="metric">
                <span class="metric-label">Palabras/oración:</span>
                <span class="metric-value">{{ chapter.metrics.avg_words_per_sentence }}</span>
              </div>
              <div class="metric">
                <span class="metric-label">Sílabas/palabra:</span>
                <span class="metric-value">{{ chapter.metrics.avg_syllables_per_word }}</span>
              </div>
              <div class="metric">
                <span class="metric-label">Palabras frecuentes:</span>
                <span class="metric-value">{{ chapter.metrics.sight_word_ratio }}%</span>
              </div>
            </div>
          </AccordionContent>
        </AccordionPanel>
      </Accordion>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Tag from 'primevue/tag'
import Select from 'primevue/select'
import Accordion from 'primevue/accordion'
import AccordionPanel from 'primevue/accordionpanel'
import AccordionHeader from 'primevue/accordionheader'
import AccordionContent from 'primevue/accordioncontent'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'

const props = defineProps<{
  projectId: number
}>()

const toast = useToast()

// State
const loading = ref(false)
const report = ref<any>(null)
const targetAgeGroup = ref<string | null>(null)

const ageGroupOptions = [
  { label: 'Sin objetivo específico', value: null },
  { label: 'Board book (0-3 años)', value: 'board_book' },
  { label: 'Álbum ilustrado (3-5 años)', value: 'picture_book' },
  { label: 'Primeros lectores (5-8 años)', value: 'early_reader' },
  { label: 'Libro por capítulos (6-10 años)', value: 'chapter_book' },
  { label: 'Middle grade (8-12 años)', value: 'middle_grade' },
  { label: 'Young adult (12+ años)', value: 'young_adult' },
]

// Analyze on mount
onMounted(() => {
  analyze()
})

// Re-analyze when project changes
watch(() => props.projectId, () => {
  analyze()
})

// Analyze
async function analyze() {
  loading.value = true
  try {
    let url = `http://localhost:8008/api/projects/${props.projectId}/age-readability`
    if (targetAgeGroup.value) {
      url += `?target_age_group=${targetAgeGroup.value}`
    }

    const response = await fetch(url)
    const data = await response.json()

    if (data.success) {
      report.value = data.data
    } else {
      throw new Error(data.error || 'Error al analizar')
    }
  } catch (error) {
    console.error('Error analyzing age readability:', error)
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'No se pudo analizar la legibilidad por edad',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

// Helper functions
function getAgeIcon(ageGroup: string): string {
  const icons: Record<string, string> = {
    board_book: 'pi pi-heart',
    picture_book: 'pi pi-image',
    early_reader: 'pi pi-book',
    chapter_book: 'pi pi-bookmark',
    middle_grade: 'pi pi-user',
    young_adult: 'pi pi-users',
    adult: 'pi pi-briefcase',
  }
  return icons[ageGroup] || 'pi pi-user'
}

function getScoreClass(score: number): string {
  if (score >= 80) return 'score-excellent'
  if (score >= 60) return 'score-good'
  if (score >= 40) return 'score-fair'
  return 'score-poor'
}
</script>

<style scoped>
.age-readability-tab {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
  padding: var(--ds-space-3);
  height: 100%;
  overflow: auto;
}

.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--ds-space-4);
  flex-wrap: wrap;
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

.header-controls {
  display: flex;
  align-items: center;
  gap: var(--ds-space-4);
  flex-wrap: wrap;
}

.target-control {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.target-control label {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

.age-dropdown {
  min-width: 200px;
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

/* Estimation card */
.estimation-card {
  background: linear-gradient(135deg, var(--ds-color-primary-soft), var(--ds-surface-card));
}

.estimation-content {
  display: flex;
  align-items: center;
  gap: var(--ds-space-4);
}

.estimation-icon {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--ds-color-primary);
  color: white;
  border-radius: 50%;
  font-size: 1.5rem;
}

.estimation-info {
  flex: 1;
}

.estimation-label {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
  margin-bottom: var(--ds-space-1);
}

.estimation-value {
  font-size: var(--ds-font-size-xl);
  font-weight: var(--ds-font-weight-bold);
  color: var(--ds-color-text);
}

.estimation-grade {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

/* Appropriateness card */
.score-container {
  display: flex;
  align-items: center;
  gap: var(--ds-space-4);
  margin-bottom: var(--ds-space-4);
}

.score-circle {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 4px solid currentColor;
}

.score-circle.score-excellent { color: #10b981; }
.score-circle.score-good { color: #3b82f6; }
.score-circle.score-fair { color: #f59e0b; }
.score-circle.score-poor { color: #ef4444; }

.score-value {
  font-size: var(--ds-font-size-xl);
  font-weight: var(--ds-font-weight-bold);
}

.score-label {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.issues-list {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.issue-item {
  display: flex;
  align-items: flex-start;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2);
  background: var(--p-yellow-50);
  border-radius: var(--ds-radius-sm);
  font-size: var(--ds-font-size-sm);
}

.issue-item i {
  color: var(--p-yellow-600);
  margin-top: 2px;
}

/* Stats cards */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
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

/* Vocabulary card */
.vocabulary-card :deep(.p-card-title) {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: var(--ds-font-size-base);
}

.vocab-bars {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3);
  margin-bottom: var(--ds-space-4);
}

.vocab-row {
  display: grid;
  grid-template-columns: 200px 1fr 60px;
  align-items: center;
  gap: var(--ds-space-3);
}

.vocab-label {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

.vocab-bar-container {
  height: 12px;
  background: var(--ds-surface-hover);
  border-radius: 6px;
  overflow: hidden;
}

.vocab-bar {
  height: 100%;
  border-radius: 6px;
  transition: width 0.3s ease;
}

.vocab-bar.simple {
  background: #10b981;
}

.vocab-bar.complex {
  background: #f59e0b;
}

.vocab-percent {
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-medium);
  text-align: right;
}

.repeated-words h4 {
  margin: 0 0 var(--ds-space-2);
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

.word-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-2);
}

.word-tag {
  font-family: var(--ds-font-family-mono);
}

/* Recommendations */
.recommendations-card :deep(.p-card-title) {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: var(--ds-font-size-base);
}

.recommendations-list {
  margin: 0;
  padding-left: var(--ds-space-4);
}

.recommendations-list li {
  margin-bottom: var(--ds-space-2);
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

/* Chapters accordion */
.chapters-accordion {
  margin-top: var(--ds-space-4);
}

.chapter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  gap: var(--ds-space-3);
}

.chapter-title {
  font-weight: var(--ds-font-weight-medium);
}

.chapter-stats {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
}

.chapter-score {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

.chapter-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--ds-space-3);
}

.metric {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-1);
}

.metric-label {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.metric-value {
  font-size: var(--ds-font-size-lg);
  font-weight: var(--ds-font-weight-semibold);
}

/* Responsive */
@media (max-width: 768px) {
  .tab-header {
    flex-direction: column;
  }

  .header-controls {
    width: 100%;
  }

  .vocab-row {
    grid-template-columns: 1fr;
    gap: var(--ds-space-1);
  }
}
</style>
