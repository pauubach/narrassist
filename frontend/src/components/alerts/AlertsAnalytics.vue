<script setup lang="ts">
import { computed } from 'vue'
import type { Alert } from '@/types'

/**
 * AlertsAnalytics - Componente de analytics para el Tab de Alertas
 *
 * Muestra:
 * - Distribución de alertas por capítulo (gráfico de barras)
 * - Top categorías (tabla compacta)
 * - Estadísticas resumidas
 */

interface Props {
  /** Alertas a analizar */
  alerts: Alert[]
  /** Número total de capítulos */
  chapterCount?: number
}

const props = withDefaults(defineProps<Props>(), {
  chapterCount: 0
})

// ============================================================================
// Distribución por capítulo
// ============================================================================

interface ChapterStat {
  chapter: number
  count: number
  percentage: number // Relativo al máximo
}

const chapterDistribution = computed((): ChapterStat[] => {
  const byChapter = new Map<number, number>()

  // Contar alertas por capítulo
  props.alerts
    .filter(a => a.chapter != null && a.status === 'active')
    .forEach(a => {
      const chNum = a.chapter!
      byChapter.set(chNum, (byChapter.get(chNum) || 0) + 1)
    })

  if (byChapter.size === 0) return []

  // Encontrar máximo para calcular porcentajes
  const maxCount = Math.max(...byChapter.values())

  // Convertir a array y calcular porcentajes
  return Array.from(byChapter.entries())
    .map(([chapter, count]) => ({
      chapter,
      count,
      percentage: maxCount > 0 ? (count / maxCount) * 100 : 0
    }))
    .sort((a, b) => a.chapter - b.chapter)
})

const hasChapterData = computed(() => chapterDistribution.value.length > 0)

// Capítulo con más alertas
const topChapter = computed(() => {
  if (chapterDistribution.value.length === 0) return null
  return chapterDistribution.value.reduce((prev, curr) =>
    curr.count > prev.count ? curr : prev
  )
})

// ============================================================================
// Distribución por categoría
// ============================================================================

interface CategoryStat {
  category: string
  count: number
  percentage: number
}

const categoryDistribution = computed((): CategoryStat[] => {
  const byCategory = new Map<string, number>()

  props.alerts
    .filter(a => a.category && a.status === 'active')
    .forEach(a => {
      const cat = a.category!
      byCategory.set(cat, (byCategory.get(cat) || 0) + 1)
    })

  const total = Array.from(byCategory.values()).reduce((sum, n) => sum + n, 0)

  return Array.from(byCategory.entries())
    .map(([category, count]) => ({
      category,
      count,
      percentage: total > 0 ? (count / total) * 100 : 0
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5) // Top 5
})

const hasCategoryData = computed(() => categoryDistribution.value.length > 0)

// ============================================================================
// Helpers
// ============================================================================

function getCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    coherence: 'Coherencia',
    consistency: 'Consistencia',
    agreement: 'Concordancia',
    punctuation: 'Puntuación',
    attribute: 'Atributos',
    behavior: 'Comportamiento',
    voice: 'Voz narrativa',
    temporal: 'Temporal',
    style: 'Estilo',
    repetition: 'Repetición',
    filler: 'Muletillas'
  }
  return labels[category] || category
}
</script>

<template>
  <div class="alerts-analytics">
    <!-- Header -->
    <div class="analytics-header">
      <i class="pi pi-chart-bar"></i>
      <h3>Análisis de Alertas</h3>
    </div>

    <!-- Distribución por capítulo -->
    <div v-if="hasChapterData" class="analytics-section">
      <div class="section-header">
        <span class="section-title">Distribución por capítulo</span>
        <span v-if="topChapter" class="section-hint">
          Cap. {{ topChapter.chapter }} tiene más alertas ({{ topChapter.count }})
        </span>
      </div>

      <div class="chapter-chart">
        <div
          v-for="stat in chapterDistribution"
          :key="stat.chapter"
          class="chart-bar-wrapper"
        >
          <span class="bar-label">Cap. {{ stat.chapter }}</span>
          <div class="bar-container">
            <div
              class="bar-fill"
              :style="{ width: `${Math.max(stat.percentage, 2)}%` }"
              :title="`${stat.count} alertas`"
            >
              <span v-if="stat.count > 0" class="bar-count">{{ stat.count }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Top categorías -->
    <div v-if="hasCategoryData" class="analytics-section">
      <div class="section-header">
        <span class="section-title">Top categorías</span>
      </div>

      <div class="category-table">
        <div
          v-for="stat in categoryDistribution"
          :key="stat.category"
          class="category-row"
        >
          <span class="category-name">{{ getCategoryLabel(stat.category) }}</span>
          <div class="category-bar-container">
            <div
              class="category-bar-fill"
              :style="{ width: `${stat.percentage}%` }"
            ></div>
          </div>
          <span class="category-count">{{ stat.count }}</span>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!hasChapterData && !hasCategoryData" class="analytics-empty">
      <i class="pi pi-chart-line"></i>
      <p>No hay suficientes datos para mostrar gráficos</p>
      <span class="empty-hint">Las estadísticas aparecerán cuando haya alertas activas</span>
    </div>
  </div>
</template>

<style scoped>
.alerts-analytics {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
  padding: var(--ds-space-4);
  background: var(--surface-card);
  border-radius: var(--border-radius);
  border: 1px solid var(--surface-border);
}

.analytics-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding-bottom: var(--ds-space-2);
  border-bottom: 1px solid var(--surface-border);
}

.analytics-header i {
  font-size: 1.25rem;
  color: var(--primary-color);
}

.analytics-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-color);
}

.analytics-section {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-color);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.section-hint {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

/* Chapter Chart */
.chapter-chart {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.chart-bar-wrapper {
  display: grid;
  grid-template-columns: 70px 1fr;
  align-items: center;
  gap: var(--ds-space-2);
}

.bar-label {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
  text-align: right;
}

.bar-container {
  height: 24px;
  background: var(--surface-100);
  border-radius: var(--border-radius);
  overflow: hidden;
  position: relative;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-500), var(--primary-600));
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 0.5rem;
  transition: width 0.3s ease;
}

.bar-count {
  font-size: 0.75rem;
  font-weight: 600;
  color: white;
}

/* Category Table */
.category-table {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.category-row {
  display: grid;
  grid-template-columns: 150px 1fr 50px;
  align-items: center;
  gap: var(--ds-space-2);
}

.category-name {
  font-size: 0.85rem;
  color: var(--text-color);
}

.category-bar-container {
  height: 8px;
  background: var(--surface-100);
  border-radius: var(--border-radius-xl);
  overflow: hidden;
}

.category-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--blue-500), var(--blue-600));
  transition: width 0.3s ease;
}

.category-count {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-color);
  text-align: right;
}

/* Empty State */
.analytics-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--ds-space-6) var(--ds-space-4);
  text-align: center;
}

.analytics-empty i {
  font-size: 3rem;
  color: var(--text-color-secondary);
  opacity: 0.3;
  margin-bottom: var(--ds-space-3);
}

.analytics-empty p {
  margin: 0;
  font-size: 0.95rem;
  color: var(--text-color-secondary);
}

.empty-hint {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
  opacity: 0.7;
  margin-top: var(--ds-space-1);
}

/* Dark mode */
.dark .alerts-analytics {
  background: var(--surface-800);
}

.dark .bar-container {
  background: var(--surface-700);
}

.dark .category-bar-container {
  background: var(--surface-700);
}
</style>
