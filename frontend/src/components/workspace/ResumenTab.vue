<script setup lang="ts">
import { computed } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
// import DsBadge from '@/components/ds/DsBadge.vue'  // Reserved
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

  // Convertir a array ordenado
  const chapters = Object.entries(byChapter)
    .map(([chapterNum, data]) => {
      const num = parseInt(chapterNum)
      return {
        chapter: num,
        // Usar el nombre del capítulo si existe, si no "Sin capítulo" para 0
        name: num === 0 ? 'Sin capítulo' : (chapterNameMap.value[num] || `Capítulo ${num}`),
        count: data.count,
        bySeverity: data.bySeverity,
      }
    })
    .sort((a, b) => a.chapter - b.chapter)

  // Calcular el máximo para normalizar barras
  const maxCount = Math.max(...chapters.map(c => c.count), 1)

  return { chapters, maxCount }
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
      <!-- Info del proyecto -->
      <Card class="info-card">
        <template #title>
          <i class="pi pi-info-circle"></i>
          Información del Proyecto
        </template>
        <template #content>
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">Nombre:</span>
              <span class="info-value">{{ project.name }}</span>
            </div>
            <div v-if="project.description" class="info-item info-item-full">
              <span class="info-label">Descripción:</span>
              <span class="info-value">{{ project.description }}</span>
            </div>
            <div v-if="originalDocumentName" class="info-item">
              <span class="info-label">Documento:</span>
              <span class="info-value">{{ originalDocumentName }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Última modificación:</span>
              <span class="info-value">{{ formatDate(project.lastModified) }}</span>
            </div>
          </div>
        </template>
      </Card>

      <!-- Estadísticas principales -->
      <div class="stats-grid">
        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <i class="pi pi-file-edit stat-icon"></i>
              <div class="stat-info">
                <span class="stat-value">{{ stats.words.toLocaleString() }}</span>
                <span class="stat-label">Palabras</span>
              </div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <i class="pi pi-book stat-icon"></i>
              <div class="stat-info">
                <span class="stat-value">{{ stats.chapters }}</span>
                <span class="stat-label">Capítulos</span>
              </div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <i class="pi pi-users stat-icon"></i>
              <div class="stat-info">
                <span class="stat-value">{{ stats.entities }}</span>
                <span class="stat-label">Entidades</span>
              </div>
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #content>
            <div class="stat-content">
              <i class="pi pi-exclamation-triangle stat-icon stat-icon-warning"></i>
              <div class="stat-info">
                <span class="stat-value">{{ stats.activeAlerts }}</span>
                <span class="stat-label">Alertas activas</span>
              </div>
            </div>
          </template>
        </Card>
      </div>

      <!-- Distribución de alertas -->
      <Card class="distribution-card">
        <template #title>
          <i class="pi pi-chart-pie"></i>
          Distribución de Alertas
        </template>
        <template #content>
          <table class="alert-distribution-table">
            <tbody>
              <tr>
                <td class="severity-cell">
                  <span class="severity-dot severity-critical"></span>
                  <span>Críticas</span>
                </td>
                <td class="bar-cell">
                  <div class="distribution-bar">
                    <div
                      class="bar-segment bar-critical"
                      :style="{ width: (alertDistribution.critical / Math.max(stats.activeAlerts, 1)) * 100 + '%' }"
                    ></div>
                  </div>
                </td>
                <td class="count-cell">{{ alertDistribution.critical }}</td>
              </tr>
              <tr>
                <td class="severity-cell">
                  <span class="severity-dot severity-high"></span>
                  <span>Altas</span>
                </td>
                <td class="bar-cell">
                  <div class="distribution-bar">
                    <div
                      class="bar-segment bar-high"
                      :style="{ width: (alertDistribution.high / Math.max(stats.activeAlerts, 1)) * 100 + '%' }"
                    ></div>
                  </div>
                </td>
                <td class="count-cell">{{ alertDistribution.high }}</td>
              </tr>
              <tr>
                <td class="severity-cell">
                  <span class="severity-dot severity-medium"></span>
                  <span>Medias</span>
                </td>
                <td class="bar-cell">
                  <div class="distribution-bar">
                    <div
                      class="bar-segment bar-medium"
                      :style="{ width: (alertDistribution.medium / Math.max(stats.activeAlerts, 1)) * 100 + '%' }"
                    ></div>
                  </div>
                </td>
                <td class="count-cell">{{ alertDistribution.medium }}</td>
              </tr>
              <tr>
                <td class="severity-cell">
                  <span class="severity-dot severity-low"></span>
                  <span>Bajas</span>
                </td>
                <td class="bar-cell">
                  <div class="distribution-bar">
                    <div
                      class="bar-segment bar-low"
                      :style="{ width: (alertDistribution.low / Math.max(stats.activeAlerts, 1)) * 100 + '%' }"
                    ></div>
                  </div>
                </td>
                <td class="count-cell">{{ alertDistribution.low }}</td>
              </tr>
              <tr>
                <td class="severity-cell">
                  <span class="severity-dot severity-info"></span>
                  <span>Info</span>
                </td>
                <td class="bar-cell">
                  <div class="distribution-bar">
                    <div
                      class="bar-segment bar-info"
                      :style="{ width: (alertDistribution.info / Math.max(stats.activeAlerts, 1)) * 100 + '%' }"
                    ></div>
                  </div>
                </td>
                <td class="count-cell">{{ alertDistribution.info }}</td>
              </tr>
            </tbody>
          </table>
        </template>
      </Card>

      <!-- Alertas por capítulo (junto a Distribución de Alertas) -->
      <Card v-if="chapterDensity.chapters.length > 0" class="density-card">
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

      <!-- Entidades por tipo -->
      <Card class="entities-card">
        <template #title>
          <i class="pi pi-users"></i>
          Entidades por Tipo
        </template>
        <template #content>
          <div class="entity-type-list">
            <div
              v-for="item in entityDistribution"
              :key="item.type"
              class="entity-type-item"
            >
              <i :class="item.icon" class="entity-type-icon"></i>
              <span class="entity-type-label">{{ item.label }}</span>
              <span class="entity-type-count">{{ item.count }}</span>
            </div>
          </div>
        </template>
      </Card>

      <!-- Top personajes -->
      <Card v-if="topCharacters.length > 0" class="top-characters-card">
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
            >
              <span class="character-rank">{{ index + 1 }}</span>
              <span class="character-name">{{ char.name }}</span>
              <span class="character-mentions">{{ char.mentionCount || 0 }} apariciones</span>
            </div>
          </div>
        </template>
      </Card>

      <!-- Acciones -->
      <Card class="actions-card">
        <template #title>
          <i class="pi pi-cog"></i>
          Acciones
        </template>
        <template #content>
          <div class="actions-grid">
            <Button
              label="Exportar Informe"
              icon="pi pi-download"
              outlined
              @click="emit('export')"
            />
            <Button
              v-if="isWordDocument"
              v-tooltip.top="'Exporta el documento Word con las correcciones como revisiones (Track Changes)'"
              label="Documento con Correcciones"
              icon="pi pi-file-edit"
              outlined
              severity="help"
              @click="emit('export-corrected')"
            />
            <Button
              label="Guía de Estilo"
              icon="pi pi-book"
              outlined
              @click="emit('export-style-guide')"
            />
            <Button
              label="Re-analizar"
              icon="pi pi-refresh"
              outlined
              severity="secondary"
              @click="emit('re-analyze')"
            />
          </div>
        </template>
      </Card>
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
  gap: 1.5rem;
  max-width: 900px;
  margin: 0 auto;
}

/* Info card */
.info-card :deep(.p-card-title) {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1rem;
}

.info-grid {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.info-item {
  display: flex;
  flex-direction: row;
  align-items: baseline;
  gap: 0.5rem;
}

.info-label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
  flex-shrink: 0;
}

.info-value {
  font-size: 0.9375rem;
  color: var(--text-color);
  word-break: break-word;
}

/* Stats grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.stat-card :deep(.p-card-body) {
  padding: 1rem;
}

.stat-content {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 0.75rem;
  padding: 0.25rem 0;
}

.stat-icon {
  font-size: 1.75rem;
  color: var(--primary-color);
  flex-shrink: 0;
}

.stat-icon-warning {
  color: var(--orange-500);
}

.stat-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.stat-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-color);
  line-height: 1.2;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  white-space: nowrap;
}

/* Distribution */
.distribution-card :deep(.p-card-title),
.entities-card :deep(.p-card-title),
.top-characters-card :deep(.p-card-title),
.actions-card :deep(.p-card-title) {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 1rem;
}

/* Alert distribution table */
.alert-distribution-table {
  width: 100%;
  border-collapse: collapse;
}

.alert-distribution-table tr {
  border-bottom: 1px solid var(--surface-100);
}

.alert-distribution-table tr:last-child {
  border-bottom: none;
}

.severity-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0;
  width: 100px;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.severity-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.severity-critical { background: var(--red-500); }
.severity-high { background: var(--orange-500); }
.severity-medium { background: var(--yellow-500); }
.severity-low { background: var(--blue-500); }
.severity-info { background: var(--gray-400); }

.bar-cell {
  padding: 0.5rem 0.75rem;
}

.distribution-bar {
  height: 8px;
  background: var(--surface-200);
  border-radius: 4px;
  overflow: hidden;
}

.bar-segment {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.bar-critical { background: var(--red-500); }
.bar-high { background: var(--orange-500); }
.bar-medium { background: var(--yellow-500); }
.bar-low { background: var(--blue-500); }
.bar-info { background: var(--gray-400); }

.count-cell {
  padding: 0.5rem 0;
  text-align: right;
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--text-color);
  width: 40px;
}

/* Entity types */
.entity-type-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

.entity-type-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: var(--surface-50);
  border-radius: 6px;
}

.entity-type-icon {
  color: var(--text-color-secondary);
}

.entity-type-label {
  flex: 1;
  font-size: 0.875rem;
}

.entity-type-count {
  font-weight: 600;
  color: var(--text-color);
}

/* Top characters */
.top-characters-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.character-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem;
}

.character-rank {
  width: 1.5rem;
  height: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-100);
  color: var(--primary-700);
  border-radius: 50%;
  font-size: 0.75rem;
  font-weight: 600;
}

.character-name {
  flex: 1;
  font-weight: 500;
}

.character-mentions {
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
}

/* Density map */
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
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-weight: 500;
}

.trend-improving {
  background: var(--green-100);
  color: var(--green-700);
}

.trend-worsening {
  background: var(--red-100);
  color: var(--red-700);
}

.trend-stable {
  background: var(--gray-100);
  color: var(--gray-700);
}

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
  border-radius: 4px;
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

.density-critical { background: var(--red-500); }
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

.density-legend {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  justify-content: center;
  padding-top: 0.5rem;
  border-top: 1px solid var(--surface-100);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.legend-critical { background: var(--red-500); }
.legend-high { background: var(--orange-500); }
.legend-medium { background: var(--yellow-500); }
.legend-low { background: var(--blue-500); }
.legend-info { background: var(--gray-400); }

/* Actions */
.actions-grid {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

/* Responsive */
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }

  .entity-type-list {
    grid-template-columns: 1fr;
  }
}

/* Dark mode */
.dark .distribution-bar {
  background: var(--surface-700);
}

.dark .entity-type-item {
  background: var(--surface-800);
}

.dark .character-rank {
  background: var(--primary-900);
  color: var(--primary-300);
}

.dark .density-bar-container {
  background: var(--surface-700);
}

.dark .density-legend {
  border-top-color: var(--surface-600);
}

.dark .trend-improving {
  background: var(--green-900);
  color: var(--green-300);
}

.dark .trend-worsening {
  background: var(--red-900);
  color: var(--red-300);
}

.dark .trend-stable {
  background: var(--gray-800);
  color: var(--gray-300);
}
</style>
