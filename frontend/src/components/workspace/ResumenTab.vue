<script setup lang="ts">
import { computed } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
// import DsBadge from '@/components/ds/DsBadge.vue'  // Reserved
import VersionSparkline from '@/components/project/VersionSparkline.vue'
import VersionHistory from '@/components/project/VersionHistory.vue'
import DsBarChart, { type BarChartItem } from '@/components/ds/DsBarChart.vue'
// EventDensityStrip removed from ResumenTab (redundant with alerts-per-chapter)
import type { Project, Entity, Alert, Chapter } from '@/types'
import { useEntityUtils } from '@/composables/useEntityUtils'

/**
 * ResumenTab - Pestaña de resumen y estadísticas
 *
 * Dashboard con:
 * - Información del proyecto
 * - Estadísticas de análisis
 * - Distribución de alertas
 * - Top entidades
 * - Acciones de exportación
 */

interface Props {
  /** Proyecto actual */
  project: Project
  /** Entidades del proyecto */
  entities: Entity[]
  /** Alertas del proyecto */
  alerts: Alert[]
  /** Capítulos del proyecto (para mostrar nombres) */
  chapters?: Chapter[]
}

const props = withDefaults(defineProps<Props>(), {
  chapters: () => []
})


const emit = defineEmits<{
  'export': []
  'export-style-guide': []
  'export-corrected': []
  're-analyze': []
  'navigate-to-character': [entityId: number]
}>()

const { getEntityIcon, getEntityLabel } = useEntityUtils()

// Estadísticas computadas
const stats = computed(() => ({
  words: props.project.wordCount,
  chapters: props.project.chapterCount,
  entities: props.entities.length,
  alerts: props.alerts.length,
  activeAlerts: props.alerts.filter(a => a.status === 'active').length
}))

// Progreso de revisión
const reviewStats = computed(() => {
  const total = props.alerts.length
  const resolved = props.alerts.filter(a => a.status === 'resolved').length
  const dismissed = props.alerts.filter(a => a.status === 'dismissed').length
  const reviewed = resolved + dismissed
  const pending = total - reviewed
  const percent = total > 0 ? Math.round((reviewed / total) * 100) : 0

  // Estimación de tiempo restante
  // Peso uniforme: ~30 segundos por alerta independientemente de la severidad
  // (Un fallo severo no necesariamente tarda más en corregir que uno leve)
  const pendingAlerts = props.alerts.filter(a => a.status === 'active')
  const SECONDS_PER_ALERT = 30
  const estimatedSeconds = pendingAlerts.length * SECONDS_PER_ALERT
  const estimatedMinutes = Math.ceil(estimatedSeconds / 60)

  let timeEstimate = ''
  if (estimatedMinutes < 60) {
    timeEstimate = `~${estimatedMinutes} min`
  } else {
    const hours = Math.floor(estimatedMinutes / 60)
    const mins = estimatedMinutes % 60
    timeEstimate = mins > 0 ? `~${hours}h ${mins}m` : `~${hours}h`
  }

  return { total, resolved, dismissed, reviewed, pending, percent, timeEstimate }
})

// Distribución de alertas por severidad
const alertDistribution = computed(() => {
  const dist = { critical: 0, high: 0, medium: 0, low: 0, info: 0 }
  for (const alert of props.alerts) {
    if (alert.status === 'active') {
      dist[alert.severity]++
    }
  }
  return dist
})

// Distribución de entidades por tipo
const entityDistribution = computed(() => {
  const dist: Record<string, number> = {}
  for (const entity of props.entities) {
    dist[entity.type] = (dist[entity.type] || 0) + 1
  }
  // Ordenar por cantidad
  return Object.entries(dist)
    .sort((a, b) => b[1] - a[1])
    .map(([type, count]) => ({
      type,
      count,
      icon: getEntityIcon(type as any),
      label: getEntityLabel(type as any)
    }))
})

// Transformar entityDistribution a formato BarChartItem
const entityBarItems = computed((): BarChartItem[] => {
  const maxCount = Math.max(...entityDistribution.value.map(e => e.count), 1)
  return entityDistribution.value.map(item => ({
    label: item.label,
    value: item.count,
    max: maxCount,
    // No especificar color - usa automáticamente el color primario del tema
    tooltip: `${item.label}: ${item.count} entidades`
  }))
})

// Transformar alertDistribution a formato BarChartItem
const alertDistributionBars = computed((): BarChartItem[] => {
  const items = [
    { key: 'critical', label: 'Críticas', count: alertDistribution.value.critical, color: severityColors.critical },
    { key: 'high', label: 'Altas', count: alertDistribution.value.high, color: severityColors.high },
    { key: 'medium', label: 'Medias', count: alertDistribution.value.medium, color: severityColors.medium },
    { key: 'low', label: 'Bajas', count: alertDistribution.value.low, color: severityColors.low },
    { key: 'info', label: 'Info', count: alertDistribution.value.info, color: severityColors.info },
  ]
  const maxCount = Math.max(...items.map(i => i.count), 1)
  return items
    .filter(i => i.count > 0)
    .map(item => ({
      label: item.label,
      value: item.count,
      max: maxCount,
      color: item.color,
      tooltip: `${item.label}: ${item.count} alertas`
    }))
})

// Top personajes por menciones
const topCharacters = computed(() => {
  return props.entities
    .filter(e => e.type === 'character')
    .sort((a, b) => (b.mentionCount || 0) - (a.mentionCount || 0))
    .slice(0, 5)
})

// Mapa de número de capítulo a nombre
const chapterNameMap = computed(() => {
  const map: Record<number, string> = {}
  for (const ch of props.chapters) {
    map[ch.chapterNumber] = ch.title || `Capítulo ${ch.chapterNumber}`
  }
  return map
})

// Densidad de alertas por capítulo
const chapterDensity = computed(() => {
  // Agrupar alertas por capítulo
  const byChapter: Record<number, { count: number; bySeverity: Record<string, number> }> = {}

  for (const alert of props.alerts) {
    if (alert.status !== 'active') continue
    const chapter = alert.chapter ?? 0

    if (!byChapter[chapter]) {
      byChapter[chapter] = { count: 0, bySeverity: { critical: 0, high: 0, medium: 0, low: 0, info: 0 } }
    }
    byChapter[chapter].count++
    byChapter[chapter].bySeverity[alert.severity]++
  }

  // Crear mapa de palabras por capítulo
  const wordsByChapter: Record<number, number> = {}
  if (props.chapters && props.chapters.length > 0) {
    for (const ch of props.chapters) {
      wordsByChapter[ch.chapterNumber] = ch.wordCount || 0
    }
  }

  // Convertir a array ordenado
  const chapters = Object.entries(byChapter)
    .map(([chapterNum, data]) => {
      const num = parseInt(chapterNum)
      const words = wordsByChapter[num] || 0
      const density = words > 0 ? (data.count / words) * 1000 : 0 // alertas por 1000 palabras
      return {
        chapter: num,
        // Usar el nombre del capítulo si existe, si no "Sin capítulo" para 0
        name: num === 0 ? 'Sin capítulo' : (chapterNameMap.value[num] || `Capítulo ${num}`),
        count: data.count,
        words,
        density: Math.round(density * 10) / 10, // 1 decimal
        bySeverity: data.bySeverity,
      }
    })
    .sort((a, b) => a.chapter - b.chapter)

  // Calcular el máximo para normalizar barras
  const maxCount = Math.max(...chapters.map(c => c.count), 1)
  const maxDensity = Math.max(...chapters.map(c => c.density), 1)

  return { chapters, maxCount, maxDensity }
})

// Tendencia de errores (mejorando o empeorando)
const errorTrend = computed(() => {
  const chapters = chapterDensity.value.chapters
  if (chapters.length < 3) return null

  // Comparar primera mitad con segunda mitad
  const mid = Math.floor(chapters.length / 2)
  const firstHalf = chapters.slice(0, mid)
  const secondHalf = chapters.slice(mid)

  const avgFirst = firstHalf.reduce((sum, c) => sum + c.count, 0) / firstHalf.length
  const avgSecond = secondHalf.reduce((sum, c) => sum + c.count, 0) / secondHalf.length

  const percentChange = ((avgSecond - avgFirst) / Math.max(avgFirst, 1)) * 100

  if (percentChange < -15) return { direction: 'improving', percent: Math.abs(percentChange) }
  if (percentChange > 15) return { direction: 'worsening', percent: percentChange }
  return { direction: 'stable', percent: Math.abs(percentChange) }
})

// Severity colors for alerts
const severityColors: Record<string, string> = {
  critical: 'var(--ds-color-danger, #ef4444)',
  high: 'var(--orange-500)',
  medium: 'var(--yellow-500)',
  low: 'var(--blue-500)',
  info: 'var(--gray-400)',
}

// Verificar si el documento es Word (para exportar con Track Changes)
const isWordDocument = computed(() => {
  const path = props.project.documentPath || props.project.source_path || ''
  return path.toLowerCase().endsWith('.docx')
})

// Formato de fecha
function formatDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleDateString('es-ES', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Extraer nombre original del documento (sin hash ni ruta)
const originalDocumentName = computed(() => {
  if (!props.project.documentPath) return null
  // Soportar tanto / como \ (Windows)
  const filename = props.project.documentPath.split(/[/\\]/).pop() || props.project.documentPath
  // Eliminar el hash MD5 del inicio (32 caracteres hex + _)
  const match = filename.match(/^[a-f0-9]{32}_(.+)$/)
  return match ? match[1] : filename
})
</script>

<template>
  <div class="resumen-tab">
    <div class="resumen-content">
      <!-- Row 1: Stat cards across the top -->
      <div class="stats-row">
        <div class="stat-card stat-words">
          <div class="stat-icon-bg">
            <i class="pi pi-file-edit"></i>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.words.toLocaleString() }}</span>
            <span class="stat-label">Palabras</span>
          </div>
        </div>

        <div class="stat-card stat-chapters">
          <div class="stat-icon-bg">
            <i class="pi pi-book"></i>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.chapters }}</span>
            <span class="stat-label">Capítulos</span>
          </div>
        </div>

        <div class="stat-card stat-entities">
          <div class="stat-icon-bg">
            <i class="pi pi-users"></i>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.entities }}</span>
            <span class="stat-label">Entidades</span>
          </div>
        </div>

        <div class="stat-card stat-alerts">
          <div class="stat-icon-bg">
            <i class="pi pi-exclamation-triangle"></i>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.activeAlerts }}</span>
            <span class="stat-label">Alertas activas</span>
          </div>
        </div>

        <div class="stat-card stat-trend">
          <div class="stat-icon-bg">
            <i class="pi pi-chart-line"></i>
          </div>
          <div class="stat-info">
            <span class="stat-label">Tendencia</span>
            <VersionSparkline :project-id="project.id" :width="100" :height="28" />
          </div>
        </div>
      </div>

      <!-- Review Progress (solo si hay alertas) -->
      <Card v-if="reviewStats.total > 0" class="chart-card review-progress-card">
        <template #title>
          <i class="pi pi-check-square"></i>
          Progreso de Revisión
        </template>
        <template #content>
          <div class="review-progress-content">
            <div class="review-progress-header">
              <span class="review-percent">{{ reviewStats.percent }}%</span>
              <div class="review-meta">
                <span class="review-fraction">{{ reviewStats.reviewed }} / {{ reviewStats.total }} completadas</span>
                <span v-if="reviewStats.pending > 0" class="review-estimate">{{ reviewStats.timeEstimate }} restantes</span>
              </div>
            </div>
            <div class="review-bar-track">
              <div class="review-bar-fill" :style="{ width: reviewStats.percent + '%' }"></div>
            </div>
            <div class="review-breakdown">
              <span class="breakdown-item">
                <span class="breakdown-dot breakdown-resolved"></span>
                {{ reviewStats.resolved }} resueltas
              </span>
              <span class="breakdown-separator">·</span>
              <span class="breakdown-item">
                <span class="breakdown-dot breakdown-dismissed"></span>
                {{ reviewStats.dismissed }} descartadas
              </span>
              <span class="breakdown-separator">·</span>
              <span class="breakdown-item">
                <span class="breakdown-dot breakdown-pending"></span>
                {{ reviewStats.pending }} pendientes
              </span>
            </div>
          </div>
        </template>
      </Card>

      <!-- Row 2: Two-column grid for charts -->
      <div class="charts-row">
        <!-- Left: Alert distribution (horizontal bars) -->
        <Card class="chart-card distribution-card">
          <template #title>
            <i class="pi pi-chart-bar"></i>
            Distribución de Alertas
          </template>
          <template #content>
            <div v-if="stats.activeAlerts > 0">
              <DsBarChart :items="alertDistributionBars" size="compact" />
            </div>
            <div v-else class="empty-state">
              <i class="pi pi-check-circle"></i>
              <span>Sin alertas activas</span>
            </div>
          </template>
        </Card>

        <!-- Right: Entity distribution (horizontal bars with theme color) -->
        <Card class="chart-card entities-card">
          <template #title>
            <i class="pi pi-tags"></i>
            Entidades por Tipo
          </template>
          <template #content>
            <DsBarChart :items="entityBarItems" size="normal" />
          </template>
        </Card>
      </div>

      <!-- Row 3: Alerts per chapter (full width) -->
      <Card v-if="chapterDensity.chapters.length > 0" class="chart-card density-card">
        <template #title>
          <i class="pi pi-chart-bar"></i>
          Alertas por Capítulo
          <span
            v-if="errorTrend"
            class="trend-badge"
            :class="'trend-' + errorTrend.direction"
            :title="errorTrend.direction === 'improving'
              ? 'Menos alertas en la segunda mitad del documento'
              : errorTrend.direction === 'worsening'
                ? 'Más alertas en la segunda mitad del documento'
                : 'Distribución uniforme de alertas'"
          >
            <i :class="errorTrend.direction === 'improving' ? 'pi pi-arrow-down' : errorTrend.direction === 'worsening' ? 'pi pi-arrow-up' : 'pi pi-minus'"></i>
            {{ errorTrend.direction === 'improving' ? 'Menos al final' : errorTrend.direction === 'worsening' ? 'Más al final' : 'Uniforme' }}
          </span>
        </template>
        <template #content>
          <div class="density-chart">
            <div
              v-for="item in chapterDensity.chapters"
              :key="item.chapter"
              class="density-row"
            >
              <span class="density-label" :title="item.name">{{ item.name }}</span>
              <div class="density-bar-container">
                <div class="density-bar-stack">
                  <div
                    v-if="item.bySeverity.critical > 0"
                    class="density-segment density-critical"
                    :style="{ width: (item.bySeverity.critical / chapterDensity.maxCount) * 100 + '%' }"
                    :title="`${item.bySeverity.critical} críticas`"
                  ></div>
                  <div
                    v-if="item.bySeverity.high > 0"
                    class="density-segment density-high"
                    :style="{ width: (item.bySeverity.high / chapterDensity.maxCount) * 100 + '%' }"
                    :title="`${item.bySeverity.high} altas`"
                  ></div>
                  <div
                    v-if="item.bySeverity.medium > 0"
                    class="density-segment density-medium"
                    :style="{ width: (item.bySeverity.medium / chapterDensity.maxCount) * 100 + '%' }"
                    :title="`${item.bySeverity.medium} medias`"
                  ></div>
                  <div
                    v-if="item.bySeverity.low > 0"
                    class="density-segment density-low"
                    :style="{ width: (item.bySeverity.low / chapterDensity.maxCount) * 100 + '%' }"
                    :title="`${item.bySeverity.low} bajas`"
                  ></div>
                  <div
                    v-if="item.bySeverity.info > 0"
                    class="density-segment density-info"
                    :style="{ width: (item.bySeverity.info / chapterDensity.maxCount) * 100 + '%' }"
                    :title="`${item.bySeverity.info} info`"
                  ></div>
                </div>
              </div>
              <span class="density-count">{{ item.count }}</span>
              <span v-if="item.words > 0" class="density-metric" :title="`${item.density} alertas por cada 1000 palabras`">
                {{ item.density }}
              </span>
            </div>
          </div>
          <div class="density-legend">
            <span class="legend-item"><span class="legend-dot legend-critical"></span> Crítica</span>
            <span class="legend-item"><span class="legend-dot legend-high"></span> Alta</span>
            <span class="legend-item"><span class="legend-dot legend-medium"></span> Media</span>
            <span class="legend-item"><span class="legend-dot legend-low"></span> Baja</span>
            <span class="legend-item"><span class="legend-dot legend-info"></span> Info</span>
          </div>
        </template>
      </Card>

      <!-- Event density removed: redundant with "Alertas por Capítulo" above.
           EventDensityStrip is still available in ChapterProgressTab (Estilo → Progreso). -->

      <!-- Row 3c: Version History -->
      <Card v-if="project" class="chart-card version-history-card">
        <template #title><i class="pi pi-history"></i> Versiones</template>
        <template #content>
          <VersionHistory :project-id="project.id" />
        </template>
      </Card>

      <!-- Row 4: Top characters + Info + Actions (three columns) -->
      <div class="bottom-row">
        <!-- Top characters -->
        <Card v-if="topCharacters.length > 0" class="chart-card top-characters-card">
          <template #title>
            <i class="pi pi-star"></i>
            Personajes Principales
          </template>
          <template #content>
            <div class="top-characters-list">
              <div
                v-for="(char, index) in topCharacters"
                :key="char.id"
                class="character-item"
                @click="emit('navigate-to-character', char.id)"
              >
                <span class="character-rank" :class="'rank-' + (index + 1)">{{ index + 1 }}</span>
                <div class="character-info">
                  <span class="character-name">{{ char.name }}</span>
                  <div class="character-bar-track">
                    <div
                      class="character-bar-fill"
                      :style="{ width: ((char.mentionCount || 0) / Math.max(topCharacters[0]?.mentionCount || 1, 1)) * 100 + '%' }"
                    ></div>
                  </div>
                </div>
                <span class="character-mentions">{{ char.mentionCount || 0 }}</span>
                <i class="pi pi-chevron-right character-chevron"></i>
              </div>
            </div>
          </template>
        </Card>

        <!-- Project info -->
        <Card class="chart-card info-card">
          <template #title>
            <i class="pi pi-info-circle"></i>
            Proyecto
          </template>
          <template #content>
            <div class="info-list">
              <div class="info-row">
                <i class="pi pi-tag info-row-icon"></i>
                <div class="info-row-content">
                  <span class="info-row-label">Nombre</span>
                  <span class="info-row-value">{{ project.name }}</span>
                </div>
              </div>
              <div v-if="originalDocumentName" class="info-row">
                <i class="pi pi-file info-row-icon"></i>
                <div class="info-row-content">
                  <span class="info-row-label">Documento</span>
                  <span class="info-row-value">{{ originalDocumentName }}</span>
                </div>
              </div>
              <div v-if="project.description" class="info-row">
                <i class="pi pi-align-left info-row-icon"></i>
                <div class="info-row-content">
                  <span class="info-row-label">Descripción</span>
                  <span class="info-row-value">{{ project.description }}</span>
                </div>
              </div>
              <div class="info-row">
                <i class="pi pi-calendar info-row-icon"></i>
                <div class="info-row-content">
                  <span class="info-row-label">Última modificación</span>
                  <span class="info-row-value">{{ formatDate(project.lastModified) }}</span>
                </div>
              </div>
            </div>
          </template>
        </Card>

        <!-- Actions -->
        <Card class="chart-card actions-card">
          <template #title>
            <i class="pi pi-download"></i>
            Acciones
          </template>
          <template #content>
            <div class="actions-stack">
              <Button
                v-tooltip.top="'Exportar informe PDF con todas las alertas, estadísticas y análisis del documento'"
                label="Exportar Informe"
                icon="pi pi-download"
                outlined
                class="action-btn"
                @click="emit('export')"
              />
              <Button
                v-if="isWordDocument"
                v-tooltip.top="'Exporta el documento Word con las correcciones como revisiones (Track Changes)'"
                label="Con Correcciones"
                icon="pi pi-file-edit"
                outlined
                severity="help"
                class="action-btn"
                @click="emit('export-corrected')"
              />
              <Button
                v-tooltip.top="'Exportar guía de estilo personalizada basada en los patrones detectados en el manuscrito'"
                label="Guía de Estilo"
                icon="pi pi-book"
                outlined
                class="action-btn"
                @click="emit('export-style-guide')"
              />
              <Button
                v-tooltip.top="'Volver a analizar el documento para actualizar alertas, entidades y métricas'"
                label="Re-analizar"
                icon="pi pi-refresh"
                outlined
                severity="secondary"
                class="action-btn"
                @click="emit('re-analyze')"
              />
            </div>
          </template>
        </Card>
      </div>
    </div>
  </div>
</template>

<style scoped>
.resumen-tab {
  height: 100%;
  overflow-y: auto;
}

.resumen-content {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

/* ── Row 1: Stat cards ── */
.stats-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 1rem;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem;
  border-radius: var(--app-radius-lg);
  border: 1px solid var(--surface-200);
  background: var(--surface-card);
  transition: box-shadow 0.2s;
}

.stat-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.stat-icon-bg {
  width: 44px;
  height: 44px;
  border-radius: var(--app-radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon-bg i {
  font-size: 1.25rem;
}

.stat-words .stat-icon-bg { background: var(--blue-50); }
.stat-words .stat-icon-bg i { color: var(--blue-600); }
.stat-chapters .stat-icon-bg { background: var(--teal-50); }
.stat-chapters .stat-icon-bg i { color: var(--teal-600); }
.stat-entities .stat-icon-bg { background: var(--purple-50); }
.stat-entities .stat-icon-bg i { color: var(--purple-600); }
.stat-alerts .stat-icon-bg { background: var(--orange-50); }
.stat-alerts .stat-icon-bg i { color: var(--orange-600); }
.stat-trend .stat-icon-bg { background: var(--cyan-50); }
.stat-trend .stat-icon-bg i { color: var(--cyan-600); }

.stat-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-color);
  line-height: 1.2;
}

.stat-label {
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
  white-space: nowrap;
}


/* ── Review Progress ── */
.review-progress-content {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.review-progress-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.review-percent {
  font-size: 2rem;
  font-weight: 700;
  color: var(--ds-color-success, #16a34a);
  line-height: 1;
  flex-shrink: 0;
}

.review-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.125rem;
  font-size: 0.8125rem;
  text-align: right;
}

.review-fraction {
  color: var(--text-color-secondary);
}

.review-estimate {
  color: var(--text-color);
  font-weight: 500;
}

.review-bar-track {
  height: 10px;
  background: var(--surface-200);
  border-radius: 5px;
  overflow: hidden;
}

.review-bar-fill {
  height: 100%;
  background: var(--green-500);
  border-radius: 5px;
  transition: width 0.3s ease;
}

.review-breakdown {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.25rem;
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
}

.breakdown-item {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.breakdown-separator {
  color: var(--surface-400);
}

.breakdown-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.breakdown-resolved { background: var(--green-500); }
.breakdown-dismissed { background: var(--blue-400); }
.breakdown-pending { background: var(--orange-400); }

/* ── Row 2: Charts row (two columns) ── */
.charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.25rem;
}

.chart-card :deep(.p-card-title) {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1rem;
  flex-wrap: wrap;
}

.chart-card :deep(.p-card-body) {
  height: 100%;
}

/* ── Empty state ── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 2rem 0;
  color: var(--ds-color-success, #16a34a);
}

.empty-state i {
  font-size: 2rem;
}

/* ── Density chart (alerts per chapter) ── */
.density-card :deep(.p-card-title) {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1rem;
  flex-wrap: wrap;
}

.trend-badge {
  margin-left: auto;
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  border-radius: var(--app-radius-lg);
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-weight: 500;
}

.trend-improving { background: var(--green-100); color: var(--green-700); }
.trend-worsening { background: var(--red-100); color: var(--red-700); }
.trend-stable { background: var(--gray-100); color: var(--gray-700); }

.density-chart {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.density-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.density-label {
  width: 140px;
  min-width: 140px;
  max-width: 140px;
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.density-bar-container {
  flex: 1;
  height: 16px;
  background: var(--surface-100);
  border-radius: var(--app-radius);
  overflow: hidden;
}

.density-bar-stack {
  display: flex;
  height: 100%;
}

.density-segment {
  height: 100%;
  transition: width 0.3s ease;
}

.density-critical { background: var(--ds-color-danger, #ef4444); }
.density-high { background: var(--orange-500); }
.density-medium { background: var(--yellow-500); }
.density-low { background: var(--blue-500); }
.density-info { background: var(--gray-400); }

.density-count {
  width: 35px;
  text-align: right;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text-color);
}

.density-metric {
  width: 40px;
  text-align: right;
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  font-style: italic;
}

.density-legend {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  justify-content: center;
  padding-top: 0.5rem;
  border-top: 1px solid var(--surface-100);
}

.density-legend .legend-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.density-legend .legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.legend-critical { background: var(--ds-color-danger, #ef4444); }
.legend-high { background: var(--orange-500); }
.legend-medium { background: var(--yellow-500); }
.legend-low { background: var(--blue-500); }
.legend-info { background: var(--gray-400); }

/* ── Bottom row: 3 columns ── */
.bottom-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 1.25rem;
}

/* ── Top characters ── */
.top-characters-list {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.character-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem;
  margin: -0.5rem;
  border-radius: var(--app-radius);
  cursor: pointer;
  transition: background 0.2s;
}

.character-item:hover {
  background: var(--surface-100);
}

.character-item:active {
  background: var(--surface-200);
}

.character-rank {
  width: 1.75rem;
  height: 1.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 0.75rem;
  font-weight: 600;
  flex-shrink: 0;
}

/* Escala basada en color primary con diferentes saturaciones */
.character-rank.rank-1 { background: var(--p-primary-600); color: white; font-weight: 700; }
.character-rank.rank-2 { background: var(--p-primary-500); color: white; font-weight: 600; }
.character-rank.rank-3 { background: var(--p-primary-400); color: white; font-weight: 600; }
.character-rank.rank-4 { background: var(--p-primary-200); color: var(--p-primary-700); }
.character-rank.rank-5 { background: var(--p-primary-100); color: var(--p-primary-700); }

.character-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.character-name {
  font-weight: 500;
  font-size: 0.875rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.character-bar-track {
  height: 6px;
  background: var(--surface-100);
  border-radius: var(--app-radius-sm);
  overflow: hidden;
}

.character-bar-fill {
  height: 100%;
  background: var(--primary-color);
  border-radius: var(--app-radius-sm);
  transition: width 0.4s ease;
  min-width: 4px;
  opacity: 0.6;
}

.character-mentions {
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
  white-space: nowrap;
  flex-shrink: 0;
}

.character-chevron {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  opacity: 0;
  transition: opacity 0.2s;
  flex-shrink: 0;
}

.character-item:hover .character-chevron {
  opacity: 1;
}

/* ── Info card ── */
.info-list {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

.info-row {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.info-row-icon {
  color: var(--text-color-secondary);
  margin-top: 0.125rem;
  flex-shrink: 0;
  font-size: 0.875rem;
}

.info-row-content {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.info-row-label {
  font-size: 0.6875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-color-secondary);
}

.info-row-value {
  font-size: 0.875rem;
  color: var(--text-color);
  word-break: break-word;
}

/* ── Actions ── */
.actions-stack {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.action-btn {
  width: 100%;
  justify-content: flex-start;
}

/* ── Responsive ── */
@media (max-width: 1366px) {
  .stats-row {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 1024px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .bottom-row {
    grid-template-columns: 1fr 1fr;
  }

  .actions-card {
    grid-column: 1 / -1;
  }
}

@media (max-width: 768px) {
  .stats-row {
    grid-template-columns: 1fr;
  }

  .charts-row {
    grid-template-columns: 1fr;
  }

  .bottom-row {
    grid-template-columns: 1fr;
  }

  .density-label {
    width: 100px;
    min-width: 100px;
    max-width: 100px;
  }

  .density-metric {
    display: none;
  }
}

/* ── Dark mode ── */
:deep(.dark) .stat-words .stat-icon-bg { background: var(--blue-900); }
:deep(.dark) .stat-chapters .stat-icon-bg { background: var(--teal-900); }
:deep(.dark) .stat-entities .stat-icon-bg { background: var(--purple-900); }
:deep(.dark) .stat-alerts .stat-icon-bg { background: var(--orange-900); }

:deep(.dark) .stat-card {
  border-color: var(--surface-600);
}

:deep(.dark) .character-bar-track {
  background: var(--surface-700);
}

/* Dark mode - escala primary adaptada */
:deep(.dark) .character-rank.rank-1 { background: var(--p-primary-500); color: white; font-weight: 700; }
:deep(.dark) .character-rank.rank-2 { background: var(--p-primary-600); color: white; font-weight: 600; }
:deep(.dark) .character-rank.rank-3 { background: var(--p-primary-700); color: white; font-weight: 600; }
:deep(.dark) .character-rank.rank-4 { background: var(--p-primary-800); color: var(--p-primary-200); }
:deep(.dark) .character-rank.rank-5 { background: var(--p-primary-900); color: var(--p-primary-300); }

:deep(.dark) .density-bar-container {
  background: var(--surface-700);
}

:deep(.dark) .density-legend {
  border-top-color: var(--surface-600);
}

:deep(.dark) .trend-improving { background: var(--green-900); color: var(--green-300); }
:deep(.dark) .trend-worsening { background: var(--red-900); color: var(--red-300); }
:deep(.dark) .trend-stable { background: var(--gray-800); color: var(--gray-300); }
</style>
