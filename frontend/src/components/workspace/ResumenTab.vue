<script setup lang="ts">
import { computed, ref } from 'vue'
import Button from 'primevue/button'
import DsProgressRing from '../design-system/DsProgressRing.vue'
import type { Project, Entity, Alert, Chapter } from '@/types'
import { useWorkspaceStore } from '../../stores/workspace'
import { useSelectionStore } from '../../stores/selection'

/**
 * ResumenTab - Dashboard MVP con diseño híbrido
 *
 * Propuesta de los 3 comités:
 * - Hero section con progreso radial
 * - 3 CTAs contextuales (Continuar/Priorizar/Elegir)
 * - Estadísticas colapsables (progressive disclosure)
 * - Click-to-action en todas las métricas
 */

interface Props {
  /** Proyecto actual */
  project: Project
  /** Entidades del proyecto */
  entities: Entity[]
  /** Alertas del proyecto */
  alerts: Alert[]
  /** Capítulos del proyecto */
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

const workspaceStore = useWorkspaceStore()
const selectionStore = useSelectionStore()

// Estado local
const showAdvancedStats = ref(false)

// ── Estadísticas computadas ──
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
  return { total, resolved, dismissed, reviewed, pending, percent }
})

// ── Lógica de priorización inteligente ──

// Próxima alerta sugerida (basada en severidad + posición)
const nextAlert = computed(() => {
  const active = props.alerts.filter(a => a.status === 'active')
  if (active.length === 0) return null

  // Priorizar: critical > high > medium > low > info
  // Dentro de cada severidad, ordenar por posición
  const severityOrder = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
  const sorted = active.sort((a, b) => {
    const sevDiff = severityOrder[a.severity] - severityOrder[b.severity]
    if (sevDiff !== 0) return sevDiff
    return (a.spanStart ?? 0) - (b.spanStart ?? 0)
  })

  return sorted[0]
})

// Alertas críticas pendientes
const criticalAlerts = computed(() =>
  props.alerts.filter(a => a.status === 'active' && a.severity === 'critical')
)

// Distribución de alertas por severidad
const alertsBySeverity = computed(() => {
  const dist = { critical: 0, high: 0, medium: 0, low: 0, info: 0 }
  for (const alert of props.alerts) {
    if (alert.status === 'active') {
      dist[alert.severity]++
    }
  }
  return dist
})

// Capítulo con más alertas
const hottestChapter = computed(() => {
  if (props.chapters.length === 0) return null

  const byChapter: Record<number, number> = {}
  for (const alert of props.alerts) {
    if (alert.status === 'active' && alert.chapter != null) {
      byChapter[alert.chapter] = (byChapter[alert.chapter] || 0) + 1
    }
  }

  const entries = Object.entries(byChapter).map(([ch, count]) => ({ chapter: parseInt(ch), count }))
  if (entries.length === 0) return null

  entries.sort((a, b) => b.count - a.count)
  const hottest = entries[0]
  const chapter = props.chapters.find(c => c.chapterNumber === hottest.chapter)
  return chapter ? { chapter, count: hottest.count } : null
})

// ── Acciones CTA ──

// [▶ CONTINUAR] - Ir a la próxima alerta sugerida
function handleContinue() {
  if (!nextAlert.value) return

  // Cambiar a tab de alertas
  workspaceStore.setActiveTab('alerts')

  // Seleccionar la alerta
  setTimeout(() => {
    selectionStore.selectAlert(nextAlert.value!)
    // Navegar al documento
    window.dispatchEvent(new CustomEvent('alert:navigate', {
      detail: { alertId: nextAlert.value!.id }
    }))
  }, 100)
}

// [🔥 PRIORIZAR] - Filtrar solo críticas
function handlePrioritize() {
  workspaceStore.setActiveTab('alerts')
  // Enviar evento para filtrar por críticas
  setTimeout(() => {
    window.dispatchEvent(new CustomEvent('alerts:filter', {
      detail: { severity: 'critical' }
    }))
  }, 100)
}

// [📍 ELEGIR CAPÍTULO] - Ir al capítulo con más alertas
function handleChooseChapter() {
  if (!hottestChapter.value) return

  // Cambiar a tab de texto (para ver el documento)
  workspaceStore.setActiveTab('text')

  // Emitir evento para navegar al capítulo
  setTimeout(() => {
    window.dispatchEvent(new CustomEvent('chapter:navigate', {
      detail: { chapterId: hottestChapter.value!.chapter.id }
    }))
  }, 100)
}

// ── Estadísticas avanzadas (colapsables) ──

// Entidades por tipo
const entityDistribution = computed(() => {
  const dist: Record<string, number> = {}
  for (const entity of props.entities) {
    dist[entity.type] = (dist[entity.type] || 0) + 1
  }
  return Object.entries(dist)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
})

// Top personajes
const topCharacters = computed(() => {
  return props.entities
    .filter(e => e.type === 'character')
    .sort((a, b) => (b.mentionCount || 0) - (a.mentionCount || 0))
    .slice(0, 3)
})

// Formato de fecha
function formatDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleDateString('es-ES', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  })
}

// Severity labels
const severityLabels: Record<string, string> = {
  critical: 'Críticas',
  high: 'Altas',
  medium: 'Medias',
  low: 'Bajas',
  info: 'Info'
}
</script>

<template>
  <div class="resumen-tab">
    <div class="resumen-content">
      <!-- ══════════════════════════════════════════════════════════════
           HERO SECTION - Progreso + CTAs
           ══════════════════════════════════════════════════════════════ -->
      <div class="hero-section">
        <div class="hero-left">
          <DsProgressRing
            :value="reviewStats.percent"
            size="large"
            label="REVISADO"
            color="auto"
          />
        </div>

        <div class="hero-right">
          <div class="hero-title">
            <h2>{{ reviewStats.pending === 0 ? '¡Revisión completa!' : 'Continúa donde lo dejaste' }}</h2>
            <p class="hero-subtitle">
              <template v-if="reviewStats.pending === 0">
                Has revisado todas las alertas del documento
              </template>
              <template v-else>
                {{ reviewStats.pending }} alerta{{ reviewStats.pending === 1 ? '' : 's' }} pendiente{{ reviewStats.pending === 1 ? '' : 's' }}
                <template v-if="criticalAlerts.length > 0">
                  · <span class="critical-badge">{{ criticalAlerts.length }} crítica{{ criticalAlerts.length === 1 ? '' : 's' }}</span>
                </template>
              </template>
            </p>
          </div>

          <!-- 3 CTAs contextuales -->
          <div class="hero-ctas">
            <!-- CTA 1: Continuar (próxima alerta sugerida) -->
            <Button
              v-if="nextAlert"
              label="Continuar"
              icon="pi pi-play"
              class="cta-primary"
              @click="handleContinue"
            >
              <template #default>
                <i class="pi pi-play"></i>
                <span class="cta-label">Continuar</span>
                <span class="cta-hint">{{ severityLabels[nextAlert.severity] }} · Cap. {{ nextAlert.chapter || '?' }}</span>
              </template>
            </Button>

            <!-- CTA 2: Priorizar (solo críticas) -->
            <Button
              v-if="criticalAlerts.length > 0"
              label="Priorizar Críticas"
              icon="pi pi-bolt"
              severity="danger"
              outlined
              class="cta-secondary"
              @click="handlePrioritize"
            >
              <template #default>
                <i class="pi pi-bolt"></i>
                <span class="cta-label">Priorizar Críticas</span>
                <span class="cta-hint">{{ criticalAlerts.length }} alerta{{ criticalAlerts.length === 1 ? '' : 's' }}</span>
              </template>
            </Button>

            <!-- CTA 3: Elegir capítulo (más alertas) -->
            <Button
              v-if="hottestChapter"
              label="Elegir Capítulo"
              icon="pi pi-map-marker"
              severity="secondary"
              outlined
              class="cta-tertiary"
              @click="handleChooseChapter"
            >
              <template #default>
                <i class="pi pi-map-marker"></i>
                <span class="cta-label">Capítulo {{ hottestChapter.chapter.chapterNumber }}</span>
                <span class="cta-hint">{{ hottestChapter.count }} alerta{{ hottestChapter.count === 1 ? '' : 's' }}</span>
              </template>
            </Button>
          </div>
        </div>
      </div>

      <!-- ══════════════════════════════════════════════════════════════
           ESTADÍSTICAS RÁPIDAS (Siempre visibles)
           ══════════════════════════════════════════════════════════════ -->
      <div class="quick-stats">
        <div class="quick-stat">
          <i class="pi pi-file-edit stat-icon"></i>
          <span class="stat-value">{{ stats.words.toLocaleString() }}</span>
          <span class="stat-label">palabras</span>
        </div>
        <div class="quick-stat">
          <i class="pi pi-book stat-icon"></i>
          <span class="stat-value">{{ stats.chapters }}</span>
          <span class="stat-label">capítulos</span>
        </div>
        <div class="quick-stat">
          <i class="pi pi-users stat-icon"></i>
          <span class="stat-value">{{ stats.entities }}</span>
          <span class="stat-label">entidades</span>
        </div>
        <div class="quick-stat">
          <i class="pi pi-exclamation-triangle stat-icon"></i>
          <span class="stat-value">{{ stats.activeAlerts }}</span>
          <span class="stat-label">alertas activas</span>
        </div>
      </div>

      <!-- ══════════════════════════════════════════════════════════════
           ESTADÍSTICAS AVANZADAS (Progressive Disclosure)
           ══════════════════════════════════════════════════════════════ -->
      <div class="advanced-stats-toggle">
        <Button
          :label="showAdvancedStats ? 'Ocultar estadísticas avanzadas' : 'Mostrar estadísticas avanzadas'"
          :icon="showAdvancedStats ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"
          text
          size="small"
          class="toggle-btn"
          @click="showAdvancedStats = !showAdvancedStats"
        />
      </div>

      <div v-if="showAdvancedStats" class="advanced-stats">
        <!-- Distribución por severidad -->
        <div class="advanced-card">
          <h3 class="advanced-title">
            <i class="pi pi-chart-pie"></i>
            Distribución por Severidad
          </h3>
          <div class="severity-grid">
            <div
              v-for="[sev, count] in Object.entries(alertsBySeverity).filter(([,c]) => c > 0)"
              :key="sev"
              class="severity-item"
              :class="`severity-${sev}`"
            >
              <span class="severity-count">{{ count }}</span>
              <span class="severity-label">{{ severityLabels[sev] }}</span>
            </div>
          </div>
        </div>

        <!-- Top entidades -->
        <div v-if="entityDistribution.length > 0" class="advanced-card">
          <h3 class="advanced-title">
            <i class="pi pi-tags"></i>
            Entidades Detectadas
          </h3>
          <div class="entity-list">
            <div v-for="[type, count] in entityDistribution" :key="type" class="entity-item">
              <span class="entity-type">{{ type }}</span>
              <span class="entity-count">{{ count }}</span>
            </div>
          </div>
        </div>

        <!-- Top personajes -->
        <div v-if="topCharacters.length > 0" class="advanced-card">
          <h3 class="advanced-title">
            <i class="pi pi-star"></i>
            Personajes Principales
          </h3>
          <div class="character-list">
            <div v-for="char in topCharacters" :key="char.id" class="character-item">
              <span class="character-name">{{ char.name }}</span>
              <span class="character-mentions">{{ char.mentionCount || 0 }} menciones</span>
            </div>
          </div>
        </div>

        <!-- Info del proyecto -->
        <div class="advanced-card">
          <h3 class="advanced-title">
            <i class="pi pi-info-circle"></i>
            Proyecto
          </h3>
          <div class="info-list">
            <div class="info-row">
              <span class="info-label">Nombre</span>
              <span class="info-value">{{ project.name }}</span>
            </div>
            <div v-if="project.description" class="info-row">
              <span class="info-label">Descripción</span>
              <span class="info-value">{{ project.description }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Última modificación</span>
              <span class="info-value">{{ formatDate(project.lastModified) }}</span>
            </div>
          </div>
        </div>

        <!-- Acciones de exportación -->
        <div class="advanced-card actions-card">
          <h3 class="advanced-title">
            <i class="pi pi-download"></i>
            Exportar
          </h3>
          <div class="actions-stack">
            <Button
              label="Informe de Análisis"
              icon="pi pi-file-pdf"
              outlined
              size="small"
              class="action-btn"
              @click="emit('export')"
            />
            <Button
              label="Guía de Estilo"
              icon="pi pi-book"
              outlined
              size="small"
              class="action-btn"
              @click="emit('export-style-guide')"
            />
            <Button
              label="Re-analizar Documento"
              icon="pi pi-refresh"
              outlined
              severity="secondary"
              size="small"
              class="action-btn"
              @click="emit('re-analyze')"
            />
          </div>
        </div>
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
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

/* ══════════════════════════════════════════════════════════════
   HERO SECTION
   ══════════════════════════════════════════════════════════════ */
.hero-section {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 2.5rem;
  align-items: center;
  padding: 2rem;
  background: var(--surface-card);
  border-radius: var(--app-radius-lg);
  border: 1px solid var(--surface-200);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.hero-left {
  display: flex;
  justify-content: center;
  align-items: center;
}

.hero-right {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  min-width: 0;
}

.hero-title h2 {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-color);
  line-height: 1.2;
}

.hero-subtitle {
  margin: 0.5rem 0 0;
  font-size: 1rem;
  color: var(--text-color-secondary);
  line-height: 1.4;
}

.critical-badge {
  color: var(--red-600);
  font-weight: 600;
}

/* ── CTAs ── */
.hero-ctas {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.hero-ctas :deep(.p-button) {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 1rem 1.25rem;
  min-width: 0;
  flex: 1 1 auto;
  height: auto;
}

.hero-ctas :deep(.p-button-label) {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.25rem;
  width: 100%;
}

.cta-label {
  font-size: 0.9375rem;
  font-weight: 600;
  line-height: 1.2;
}

.cta-hint {
  font-size: 0.75rem;
  font-weight: 400;
  opacity: 0.8;
  line-height: 1.2;
}

.cta-primary :deep(.p-button-label) i {
  font-size: 1rem;
  margin-bottom: 0.25rem;
}

/* ══════════════════════════════════════════════════════════════
   QUICK STATS
   ══════════════════════════════════════════════════════════════ */
.quick-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}

.quick-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1.25rem;
  background: var(--surface-card);
  border-radius: var(--app-radius);
  border: 1px solid var(--surface-200);
  transition: all 0.2s;
}

.quick-stat:hover {
  border-color: var(--primary-color);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.stat-icon {
  font-size: 1.5rem;
  color: var(--primary-color);
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-color);
  line-height: 1;
  margin-bottom: 0.25rem;
}

.stat-label {
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* ══════════════════════════════════════════════════════════════
   ADVANCED STATS (Progressive Disclosure)
   ══════════════════════════════════════════════════════════════ */
.advanced-stats-toggle {
  display: flex;
  justify-content: center;
  padding: 0.5rem 0;
}

.toggle-btn {
  color: var(--text-color-secondary);
}

.advanced-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.25rem;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.advanced-card {
  padding: 1.5rem;
  background: var(--surface-card);
  border-radius: var(--app-radius);
  border: 1px solid var(--surface-200);
}

.advanced-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 1rem;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-color);
}

.advanced-title i {
  color: var(--primary-color);
}

/* ── Severity grid ── */
.severity-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
  gap: 0.75rem;
}

.severity-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1rem 0.75rem;
  border-radius: var(--app-radius);
  border: 2px solid transparent;
  transition: all 0.2s;
}

.severity-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.severity-critical {
  background: var(--red-50);
  border-color: var(--red-200);
}

.severity-high {
  background: var(--orange-50);
  border-color: var(--orange-200);
}

.severity-medium {
  background: var(--yellow-50);
  border-color: var(--yellow-200);
}

.severity-low {
  background: var(--blue-50);
  border-color: var(--blue-200);
}

.severity-info {
  background: var(--gray-50);
  border-color: var(--gray-200);
}

.severity-count {
  font-size: 1.5rem;
  font-weight: 700;
  line-height: 1;
  margin-bottom: 0.25rem;
}

.severity-critical .severity-count {
  color: var(--red-700);
}

.severity-high .severity-count {
  color: var(--orange-700);
}

.severity-medium .severity-count {
  color: var(--yellow-700);
}

.severity-low .severity-count {
  color: var(--blue-700);
}

.severity-info .severity-count {
  color: var(--gray-700);
}

.severity-label {
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-color-secondary);
}

/* ── Entity list ── */
.entity-list,
.character-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.entity-item,
.character-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  border-radius: var(--app-radius-sm);
  background: var(--surface-100);
  font-size: 0.875rem;
}

.entity-type,
.character-name {
  font-weight: 500;
  color: var(--text-color);
  text-transform: capitalize;
}

.entity-count,
.character-mentions {
  font-weight: 600;
  color: var(--text-color-secondary);
}

/* ── Info list ── */
.info-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.info-row {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.info-label {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-color-secondary);
}

.info-value {
  font-size: 0.875rem;
  color: var(--text-color);
  word-break: break-word;
}

/* ── Actions ── */
.actions-card {
  grid-column: 1 / -1;
}

.actions-stack {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.action-btn {
  flex: 1 1 auto;
  min-width: 180px;
}

/* ══════════════════════════════════════════════════════════════
   RESPONSIVE
   ══════════════════════════════════════════════════════════════ */
@media (max-width: 1024px) {
  .hero-section {
    grid-template-columns: 1fr;
    text-align: center;
  }

  .hero-right {
    align-items: center;
  }

  .hero-ctas {
    justify-content: center;
    width: 100%;
  }

  .advanced-stats {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .resumen-content {
    padding: 1rem;
  }

  .hero-section {
    padding: 1.5rem;
  }

  .quick-stats {
    grid-template-columns: repeat(2, 1fr);
  }

  .hero-ctas :deep(.p-button) {
    width: 100%;
  }
}

/* ══════════════════════════════════════════════════════════════
   DARK MODE
   ══════════════════════════════════════════════════════════════ */
@media (prefers-color-scheme: dark) {
  .hero-section,
  .quick-stat,
  .advanced-card {
    border-color: var(--surface-600);
  }

  .severity-critical {
    background: var(--red-900);
    border-color: var(--red-700);
  }

  .severity-critical .severity-count {
    color: var(--red-300);
  }

  .severity-high {
    background: var(--orange-900);
    border-color: var(--orange-700);
  }

  .severity-high .severity-count {
    color: var(--orange-300);
  }

  .severity-medium {
    background: var(--yellow-900);
    border-color: var(--yellow-700);
  }

  .severity-medium .severity-count {
    color: var(--yellow-300);
  }

  .severity-low {
    background: var(--blue-900);
    border-color: var(--blue-700);
  }

  .severity-low .severity-count {
    color: var(--blue-300);
  }

  .severity-info {
    background: var(--gray-800);
    border-color: var(--gray-600);
  }

  .severity-info .severity-count {
    color: var(--gray-300);
  }

  .entity-item,
  .character-item {
    background: var(--surface-700);
  }

  .critical-badge {
    color: var(--red-400);
  }
}
</style>
