<script setup lang="ts">
import { computed } from 'vue'
import type { Alert, AlertCategory } from '@/types'
import { META_CATEGORIES, type MetaCategoryKey } from '@/composables/useAlertUtils'
import DsBarChart, { type BarChartItem } from '@/components/ds/DsBarChart.vue'

/**
 * AlertsAnalytics - Componente de analytics para el Tab de Alertas
 *
 * Muestra:
 * - Distribución de alertas por capítulo (gráfico de barras con categorías)
 * - Top categorías (tabla compacta)
 * - Estadísticas resumidas
 */

interface ChapterInfo {
  id: number
  chapterNumber: number
  title: string
}

interface Props {
  /** Alertas a analizar */
  alerts: Alert[]
  /** Número total de capítulos */
  chapterCount?: number
  /** Capítulos con título (para mostrar nombres completos) */
  chapters?: ChapterInfo[]
}

const props = withDefaults(defineProps<Props>(), {
  chapterCount: 0,
  chapters: () => [],
})

/** Formato corto para label de barra: "1. Título" truncado */
function formatChapterShort(chapterNum: number): string {
  const ch = props.chapters?.find(c => c.chapterNumber === chapterNum)
  if (ch?.title) {
    const full = `${chapterNum}. ${ch.title}`
    return full.length > 18 ? full.slice(0, 16) + '…' : full
  }
  return `Cap. ${chapterNum}`
}

/** Formato completo para tooltip */
function formatChapterFull(chapterNum: number): string {
  const ch = props.chapters?.find(c => c.chapterNumber === chapterNum)
  if (ch?.title) return `${chapterNum}. ${ch.title}`
  return `Capítulo ${chapterNum}`
}

/** Obtiene el color de una categoría según su meta-categoría */
function getCategoryColor(category: string): string {
  const metaCat = getMetaCategory(category as AlertCategory)
  return META_CATEGORIES[metaCat].color
}

// ============================================================================
// Distribución por capítulo
// ============================================================================

interface CategorySegment {
  metaCategory: MetaCategoryKey
  count: number
  percentage: number
  color: string
}

interface ChapterStat {
  chapter: number
  count: number
  percentage: number // Relativo al máximo
  segments: CategorySegment[] // Distribución por meta-categoría
}

/** Encuentra la meta-categoría de una alerta */
function getMetaCategory(category: AlertCategory): MetaCategoryKey {
  for (const [key, meta] of Object.entries(META_CATEGORIES)) {
    if (meta.categories.includes(category)) {
      return key as MetaCategoryKey
    }
  }
  return 'suggestions' // fallback
}

const chapterDistribution = computed((): ChapterStat[] => {
  // Contar alertas por capítulo y meta-categoría
  const byChapter = new Map<number, Map<MetaCategoryKey, number>>()

  props.alerts
    .filter(a => a.chapter != null && a.status === 'active')
    .forEach(a => {
      const chNum = a.chapter!
      const metaCat = getMetaCategory(a.category)

      if (!byChapter.has(chNum)) {
        byChapter.set(chNum, new Map())
      }
      const catMap = byChapter.get(chNum)!
      catMap.set(metaCat, (catMap.get(metaCat) || 0) + 1)
    })

  if (byChapter.size === 0) return []

  // Encontrar máximo para calcular porcentajes de barra
  const maxCount = Math.max(...Array.from(byChapter.values()).map(
    catMap => Array.from(catMap.values()).reduce((sum, n) => sum + n, 0)
  ))

  // Convertir a array con segmentos
  return Array.from(byChapter.entries())
    .map(([chapter, catMap]) => {
      const total = Array.from(catMap.values()).reduce((sum, n) => sum + n, 0)

      // Calcular segmentos ordenados
      const segments: CategorySegment[] = Array.from(catMap.entries())
        .map(([metaCat, count]) => ({
          metaCategory: metaCat,
          count,
          percentage: total > 0 ? (count / total) * 100 : 0,
          color: META_CATEGORIES[metaCat].color
        }))
        .sort((a, b) => b.count - a.count) // Mayor primero

      return {
        chapter,
        count: total,
        percentage: maxCount > 0 ? (total / maxCount) * 100 : 0,
        segments
      }
    })
    .sort((a, b) => a.chapter - b.chapter)
})

const hasChapterData = computed(() => chapterDistribution.value.length > 0)

/** Transforma chapterDistribution a formato BarChartItem */
const chapterBarItems = computed((): BarChartItem[] => {
  const maxCount = Math.max(...chapterDistribution.value.map(s => s.count), 1)

  return chapterDistribution.value.map(stat => ({
    label: formatChapterShort(stat.chapter),
    value: stat.count,
    max: maxCount,
    segments: stat.segments.map(seg => ({
      value: seg.count,
      color: seg.color,
      label: META_CATEGORIES[seg.metaCategory].label
    })),
    tooltip: `${formatChapterFull(stat.chapter)}: ${stat.count} alertas`
  }))
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

/** Transforma categoryDistribution a formato BarChartItem */
const categoryBarItems = computed((): BarChartItem[] => {
  const maxPercentage = 100 // Porcentajes siempre van 0-100

  return categoryDistribution.value.map(stat => ({
    label: getCategoryLabel(stat.category),
    value: stat.count,
    max: maxPercentage,
    color: getCategoryColor(stat.category),
    tooltip: `${getCategoryLabel(stat.category)}: ${stat.count} (${stat.percentage.toFixed(1)}%)`
  }))
})

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
    filler: 'Muletillas',
    grammar: 'Gramática',
    spelling: 'Ortografía'
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
      </div>

      <!-- Leyenda de colores -->
      <div class="color-legend">
        <div
          v-for="(meta, key) in META_CATEGORIES"
          :key="key"
          class="legend-item"
        >
          <span class="legend-dot" :style="{ backgroundColor: meta.color }"></span>
          <span class="legend-label">{{ meta.label }}</span>
        </div>
      </div>

      <DsBarChart :items="chapterBarItems" size="prominent" />
    </div>

    <!-- Top categorías -->
    <div v-if="hasCategoryData" class="analytics-section">
      <div class="section-header">
        <span class="section-title">Top categorías</span>
      </div>

      <DsBarChart :items="categoryBarItems" size="normal" />
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

/* Leyenda de colores */
.color-legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-2) var(--ds-space-3);
  margin-bottom: var(--ds-space-1);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-label {
  font-size: 0.7rem;
  color: var(--text-color-secondary);
  white-space: nowrap;
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
</style>
