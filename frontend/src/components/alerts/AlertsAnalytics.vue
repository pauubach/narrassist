<script setup lang="ts">
import { computed } from 'vue'
import type { Alert, AlertCategory } from '@/types'
import { META_CATEGORIES, type MetaCategoryKey } from '@/composables/useAlertUtils'

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

      <div class="chapter-chart">
        <div
          v-for="stat in chapterDistribution"
          :key="stat.chapter"
          class="chart-bar-wrapper"
        >
          <span class="bar-label" :title="formatChapterFull(stat.chapter)">
            {{ formatChapterShort(stat.chapter) }}
          </span>
          <div class="bar-track">
            <div
              class="bar-fill-container"
              :style="{ width: `${Math.max(stat.percentage, 3)}%` }"
            >
              <!-- Segmentos por meta-categoría -->
              <div
                v-for="segment in stat.segments"
                :key="segment.metaCategory"
                class="bar-segment"
                :style="{
                  width: `${segment.percentage}%`,
                  backgroundColor: segment.color
                }"
                :title="`${META_CATEGORIES[segment.metaCategory].label}: ${segment.count}`"
              ></div>
            </div>
          </div>
          <span class="bar-count">{{ stat.count }}</span>
        </div>
      </div>
    </div>

    <!-- Top categorías -->
    <div v-if="hasCategoryData" class="analytics-section">
      <div class="section-header">
        <span class="section-title">Top categorías</span>
      </div>

      <div class="category-chart">
        <div
          v-for="stat in categoryDistribution"
          :key="stat.category"
          class="chart-bar-wrapper"
        >
          <span class="bar-label" :title="getCategoryLabel(stat.category)">
            {{ getCategoryLabel(stat.category) }}
          </span>
          <div class="bar-track">
            <div
              class="bar-fill-container"
              :style="{
                width: `${Math.max(stat.percentage, 3)}%`,
                backgroundColor: getCategoryColor(stat.category)
              }"
            ></div>
          </div>
          <span class="bar-count">{{ stat.count }}</span>
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

/* Gráficos de barras - Estilos compartidos */
.chapter-chart,
.category-chart {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.chart-bar-wrapper {
  display: grid;
  grid-template-columns: 120px 1fr 40px; /* Columnas fijas para alineación consistente */
  align-items: center;
  gap: 0.5rem;
  min-width: 0; /* Permite que grid respete restricciones */
}

.bar-label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  text-align: left; /* Alineación a la izquierda para consistencia */
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.3;
  cursor: default; /* Mostrar que tiene tooltip */
}

.bar-track {
  height: 14px; /* Altura unificada para todas las barras */
  background: var(--surface-100);
  border-radius: var(--border-radius);
  overflow: hidden;
  position: relative;
}

/* Contenedor de la barra completa */
.bar-fill-container {
  height: 100%;
  display: flex;
  flex-direction: row;
  border-radius: inherit;
  transition: width 0.3s ease;
  min-width: 3px;
  overflow: hidden;
}

.bar-fill-container:hover {
  filter: brightness(1.1);
}

/* Segmentos individuales por categoría (para barras segmentadas) */
.bar-segment {
  height: 100%;
  transition: width 0.3s ease, background-color 0.3s ease;
  cursor: help; /* Indica que tiene tooltip */
  position: relative;
}

.bar-segment:hover {
  filter: brightness(1.15);
}

/* Separadores entre segmentos */
.bar-segment + .bar-segment {
  border-left: 1px solid rgba(255, 255, 255, 0.2);
}

.bar-count {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-color);
  text-align: right;
  font-variant-numeric: tabular-nums;
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

.dark .bar-track {
  background: var(--surface-700);
}

.dark .bar-segment + .bar-segment {
  border-left: 1px solid rgba(0, 0, 0, 0.3); /* Separadores más oscuros en dark mode */
}
</style>
