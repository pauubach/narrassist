<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import DsBadge from '@/components/ds/DsBadge.vue'
import MethodVotingBar from '@/components/shared/MethodVotingBar.vue'
import ConfidenceBadge from '@/components/shared/ConfidenceBadge.vue'
import type { Entity, Alert } from '@/types'
import { useEntityUtils } from '@/composables/useEntityUtils'
import { useMentionNavigation } from '@/composables/useMentionNavigation'
import { useAlertUtils } from '@/composables/useAlertUtils'
import { apiUrl } from '@/config/api'

const { formatChapterLabel, getSeverityConfig } = useAlertUtils()

// Coreference info state
interface MethodContribution {
  name: string
  method: string
  count: number
  score: number
  agreed: boolean
}

interface CoreferenceInfo {
  entityId: number
  entityName: string
  methodContributions: MethodContribution[]
  mentionsByType: Record<string, Array<{ text: string; confidence: number; source: string }>>
  overallConfidence: number
  totalMentions: number
}

const corefInfo = ref<CoreferenceInfo | null>(null)
const corefLoading = ref(false)
const corefError = ref<string | null>(null)

/**
 * EntityInspector - Panel de detalles de entidad para el inspector.
 *
 * Muestra información detallada de una entidad seleccionada:
 * - Nombre y tipo
 * - Aliases
 * - Estadísticas de menciones
 * - Navegación entre menciones (anterior/siguiente)
 * - Indicador de fusión (si aplica)
 * - Acciones (ver ficha, ir a menciones, deshacer fusión)
 */

const props = defineProps<{
  /** Entidad a mostrar */
  entity: Entity
  /** ID del proyecto (para cargar menciones) */
  projectId: number
  /** Alertas del proyecto (para filtrar las relacionadas) */
  alerts?: Alert[]
  /** Número total de capítulos (para mini-timeline) */
  chapterCount?: number
}>()

const emit = defineEmits<{
  /** Ver ficha completa */
  (e: 'view-details'): void
  /** Ir a las menciones en el texto */
  (e: 'go-to-mentions'): void
  /** Cerrar el inspector */
  (e: 'close'): void
  /** Deshacer fusión de esta entidad */
  (e: 'undo-merge'): void
}>()

// Navegación de menciones
const mentionNav = useMentionNavigation(() => props.projectId)

const { getEntityIcon, getEntityLabel, getEntityColor } = useEntityUtils()

const entityIcon = computed(() => getEntityIcon(props.entity.type))
const entityTypeLabel = computed(() => getEntityLabel(props.entity.type))
const entityColor = computed(() => getEntityColor(props.entity.type))

const hasAliases = computed(() =>
  props.entity.aliases && props.entity.aliases.length > 0
)

/** Indica si la entidad es resultado de una fusion */
const isMerged = computed(() =>
  props.entity.mergedFromIds && props.entity.mergedFromIds.length > 0
)

/** Auto-cargar menciones y coreference info cuando cambia la entidad */
watch(
  () => props.entity.id,
  async (newId) => {
    if (newId && props.entity.mentionCount && props.entity.mentionCount > 0) {
      await mentionNav.loadMentions(newId)
      await loadCoreferenceInfo(newId)
    } else {
      mentionNav.clear()
      corefInfo.value = null
    }
  },
  { immediate: true }
)

/** Cargar información de correferencia */
async function loadCoreferenceInfo(entityId: number) {
  corefLoading.value = true
  corefError.value = null

  try {
    const response = await fetch(
      apiUrl(`/api/projects/${props.projectId}/entities/${entityId}/coreference`)
    )
    const result = await response.json()

    if (result.success && result.data) {
      corefInfo.value = result.data
    } else {
      corefError.value = result.error || 'Error al cargar correferencias'
    }
  } catch (err) {
    corefError.value = err instanceof Error ? err.message : 'Error desconocido'
  } finally {
    corefLoading.value = false
  }
}

/** Tiene información de correferencia válida para mostrar */
const hasCoreferenceInfo = computed(() => {
  return corefInfo.value && corefInfo.value.methodContributions.length > 0
})

/** Etiquetas para tipos de mención */
const MENTION_TYPE_LABELS: Record<string, string> = {
  proper_noun: 'Nombre',
  pronoun: 'Pronombre',
  definite_np: 'SN definido',
  demonstrative: 'Demostrativo',
  possessive: 'Posesivo',
}

function getMentionTypeLabel(type: string): string {
  return MENTION_TYPE_LABELS[type] || type
}

// ============================================================================
// Related Alerts
// ============================================================================

/** Alertas relacionadas con esta entidad */
const relatedAlerts = computed(() => {
  if (!props.alerts) return []
  return props.alerts.filter(a =>
    a.entityIds.includes(props.entity.id) && a.status === 'active'
  ).slice(0, 5) // Limitar a 5 alertas
})

/** Alertas de inconsistencias de atributos */
const attributeAlerts = computed(() => {
  return relatedAlerts.value.filter(a => a.category === 'attribute')
})

/** Otras alertas (no de atributos) */
const otherAlerts = computed(() => {
  return relatedAlerts.value.filter(a => a.category !== 'attribute')
})

const hasRelatedAlerts = computed(() => relatedAlerts.value.length > 0)

// ============================================================================
// Mini Timeline
// ============================================================================

interface ChapterAppearance {
  chapterNumber: number
  mentionCount: number
  percentage: number // Para la barra visual
}

/** Apariciones por capítulo para mini-timeline */
const chapterAppearances = computed((): ChapterAppearance[] => {
  const mentions = mentionNav.state.value.mentions
  if (!mentions || mentions.length === 0) {
    return []
  }

  // Agrupar menciones por capítulo
  const byChapter = new Map<number, number>()
  for (const mention of mentions) {
    const chNum = mention.chapterNumber || 0
    byChapter.set(chNum, (byChapter.get(chNum) || 0) + 1)
  }

  // Encontrar máximo para calcular porcentajes
  const maxCount = Math.max(...byChapter.values())

  // Convertir a array ordenado
  return Array.from(byChapter.entries())
    .map(([chapterNumber, mentionCount]) => ({
      chapterNumber,
      mentionCount,
      percentage: maxCount > 0 ? (mentionCount / maxCount) * 100 : 0
    }))
    .sort((a, b) => a.chapterNumber - b.chapterNumber)
})

const hasChapterData = computed(() => chapterAppearances.value.length > 1)
</script>

<template>
  <div class="entity-inspector">
    <!-- Header -->
    <div class="inspector-header">
      <div class="entity-icon-wrapper" :style="{ backgroundColor: entityColor + '20' }">
        <i :class="entityIcon" :style="{ color: entityColor }"></i>
      </div>
      <div class="entity-info">
        <h3 class="entity-name">{{ entity.name }}</h3>
        <div class="entity-meta">
          <DsBadge :entity-type="entity.type" size="sm">{{ entityTypeLabel }}</DsBadge>
          <DsBadge
            v-if="isMerged"
            color="info"
            size="sm"
            icon="pi pi-link"
            v-tooltip.bottom="'Esta entidad es resultado de una fusion'"
          >
            Fusionada
          </DsBadge>
        </div>
      </div>
    </div>

    <!-- Contenido -->
    <div class="inspector-body">
      <!-- Aliases -->
      <div v-if="hasAliases" class="info-section">
        <div class="section-label">También conocido como</div>
        <div class="aliases-list">
          <span
            v-for="(alias, index) in entity.aliases"
            :key="index"
            class="alias-tag"
          >
            {{ alias }}
          </span>
        </div>
      </div>

      <!-- Estadísticas -->
      <div class="info-section">
        <div class="section-label">Estadísticas</div>
        <div class="stats-grid">
          <div class="stat-item">
            <i class="pi pi-comment"></i>
            <span class="stat-value">{{ mentionNav.totalMentions.value || entity.mentionCount || 0 }}</span>
            <span class="stat-label">apariciones</span>
          </div>
          <div v-if="formatChapterLabel(entity.firstMentionChapter)" class="stat-item">
            <i class="pi pi-bookmark"></i>
            <span class="stat-value">{{ formatChapterLabel(entity.firstMentionChapter) }}</span>
            <span class="stat-label">primera aparición</span>
          </div>
        </div>
      </div>

      <!-- Importancia -->
      <div class="info-section">
        <div class="section-label">Importancia</div>
        <div class="importance-badge" :class="`importance-${entity.importance}`">
          {{ entity.importance === 'main' ? 'Principal' : entity.importance === 'secondary' ? 'Secundario' : 'Menor' }}
        </div>
      </div>

      <!-- Descripción si existe -->
      <div v-if="entity.description" class="info-section">
        <div class="section-label">Descripción</div>
        <p class="description">{{ entity.description }}</p>
      </div>

      <!-- Información de Correferencia -->
      <div v-if="hasCoreferenceInfo" class="info-section coref-section">
        <div class="section-label">
          <i class="pi pi-sitemap"></i>
          Detección de menciones
        </div>
        <div class="coref-confidence">
          <span class="confidence-label">Confianza promedio:</span>
          <ConfidenceBadge
            :value="corefInfo!.overallConfidence"
            variant="badge"
            size="sm"
          />
        </div>
        <MethodVotingBar
          :methods="corefInfo!.methodContributions"
          :compact="false"
        />
        <div class="mention-types">
          <span
            v-for="(mentions, type) in corefInfo!.mentionsByType"
            :key="type"
            class="mention-type-tag"
            v-tooltip.top="`${mentions.length} menciones de tipo ${type}`"
          >
            {{ getMentionTypeLabel(type) }}: {{ mentions.length }}
          </span>
        </div>
      </div>

      <!-- Loading coreference -->
      <div v-else-if="corefLoading" class="info-section coref-loading">
        <i class="pi pi-spin pi-spinner"></i>
        <span>Cargando información...</span>
      </div>

      <!-- Mini Timeline de apariciones -->
      <div v-if="hasChapterData" class="info-section timeline-section">
        <div class="section-label">
          <i class="pi pi-chart-bar"></i>
          Apariciones por capítulo
        </div>
        <div class="mini-timeline">
          <div
            v-for="ch in chapterAppearances"
            :key="ch.chapterNumber"
            class="timeline-bar"
            :title="`Cap. ${ch.chapterNumber}: ${ch.mentionCount} menciones`"
          >
            <div
              class="bar-fill"
              :style="{ height: `${Math.max(ch.percentage, 8)}%` }"
            ></div>
            <span class="bar-label">{{ ch.chapterNumber }}</span>
          </div>
        </div>
      </div>

      <!-- Alertas de inconsistencias de atributos -->
      <div v-if="attributeAlerts.length > 0" class="info-section alerts-section">
        <div class="section-label section-label-warning">
          <i class="pi pi-exclamation-triangle"></i>
          Inconsistencias de atributos
        </div>
        <div class="alert-list">
          <div
            v-for="alert in attributeAlerts"
            :key="alert.id"
            class="alert-item alert-attribute"
          >
            <Tag
              :severity="getSeverityConfig(alert.severity).color"
              :value="alert.extraData?.attributeKey || 'Atributo'"
              size="small"
            />
            <span class="alert-desc">{{ alert.description }}</span>
          </div>
        </div>
      </div>

      <!-- Otras alertas relacionadas -->
      <div v-if="otherAlerts.length > 0" class="info-section alerts-section">
        <div class="section-label">
          <i class="pi pi-bell"></i>
          Alertas relacionadas
        </div>
        <div class="alert-list">
          <div
            v-for="alert in otherAlerts"
            :key="alert.id"
            class="alert-item"
          >
            <Tag
              :severity="getSeverityConfig(alert.severity).color"
              :value="getSeverityConfig(alert.severity).label"
              size="small"
            />
            <span class="alert-desc">{{ alert.title }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Barra de navegación de apariciones (siempre visible si hay menciones) -->
    <div v-if="mentionNav.isActive.value" class="mention-navigation">
      <div class="nav-header">
        <span class="nav-title">APARICIONES</span>
      </div>
      <div class="nav-controls">
        <Button
          icon="pi pi-chevron-left"
          text
          rounded
          size="small"
          :disabled="!mentionNav.canGoPrevious.value"
          @click="mentionNav.goToPrevious()"
          v-tooltip.bottom="'Anterior'"
        />
        <span class="nav-counter">{{ mentionNav.navigationLabel.value }}</span>
        <Button
          icon="pi pi-chevron-right"
          text
          rounded
          size="small"
          :disabled="!mentionNav.canGoNext.value"
          @click="mentionNav.goToNext()"
          v-tooltip.bottom="'Siguiente'"
        />
      </div>
      <div v-if="mentionNav.currentMention.value" class="nav-context">
        <span class="context-chapter">
          {{ mentionNav.currentMention.value.chapterTitle || `Capítulo ${mentionNav.currentMention.value.chapterNumber}` }}
        </span>
        <p class="context-text">
          <span class="context-before">{{ mentionNav.currentMention.value.contextBefore }}</span>
          <mark>{{ mentionNav.currentMention.value.surfaceForm }}</mark>
          <span class="context-after">{{ mentionNav.currentMention.value.contextAfter }}</span>
        </p>
      </div>
    </div>

    <!-- Acciones -->
    <div class="inspector-actions">
      <Button
        label="Ver ficha completa"
        icon="pi pi-external-link"
        size="small"
        @click="emit('view-details')"
      />
      <Button
        v-if="isMerged"
        label="Deshacer fusion"
        icon="pi pi-replay"
        size="small"
        outlined
        severity="warning"
        @click="emit('undo-merge')"
        v-tooltip.bottom="'Restaurar las entidades originales'"
      />
    </div>
  </div>
</template>

<style scoped>
.entity-inspector {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.inspector-header {
  display: flex;
  align-items: flex-start;
  gap: var(--ds-space-3);
  padding: var(--ds-space-4);
  border-bottom: 1px solid var(--ds-surface-border);
}

.entity-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: var(--ds-radius-lg);
  flex-shrink: 0;
}

.entity-icon-wrapper i {
  font-size: 1.5rem;
}

.entity-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.entity-name {
  margin: 0;
  font-size: var(--ds-font-size-lg);
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-text);
  line-height: 1.3;
  word-break: break-word;
}

.entity-meta {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  flex-wrap: wrap;
}

.entity-type {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

.merged-tag {
  font-size: var(--ds-font-size-xs);
  padding: 0.125rem 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.merged-tag i {
  font-size: 0.625rem;
}

.inspector-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--ds-space-4);
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
}

.info-section {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.section-label {
  font-size: var(--ds-font-size-xs);
  font-weight: var(--ds-font-weight-medium);
  color: var(--ds-color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.aliases-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-1);
}

.alias-tag {
  padding: var(--ds-space-1) var(--ds-space-2);
  background: var(--ds-surface-hover);
  border-radius: var(--ds-radius-sm);
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--ds-space-2);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--ds-space-3);
  background: var(--ds-surface-ground);
  border-radius: var(--ds-radius-md);
  text-align: center;
}

.stat-item i {
  font-size: 1rem;
  color: var(--ds-color-text-secondary);
  margin-bottom: var(--ds-space-1);
}

.stat-item .stat-value {
  font-size: var(--ds-font-size-lg);
  font-weight: var(--ds-font-weight-bold);
  color: var(--ds-color-text);
}

.stat-item .stat-label {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.importance-badge {
  display: inline-flex;
  align-items: center;
  padding: var(--ds-space-1) var(--ds-space-3);
  border-radius: var(--ds-radius-full);
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-medium);
  width: fit-content;
}

.importance-main {
  background: var(--ds-color-primary-soft);
  color: var(--ds-color-primary);
}

.importance-secondary {
  background: var(--ds-surface-hover);
  color: var(--ds-color-text);
}

.importance-minor {
  background: var(--ds-surface-ground);
  color: var(--ds-color-text-secondary);
}

.description {
  margin: 0;
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
  line-height: 1.5;
}

.inspector-actions {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
  padding: var(--ds-space-4);
  border-top: 1px solid var(--ds-surface-border);
}

/* Barra de navegación de menciones */
.mention-navigation {
  background: var(--ds-surface-ground);
  border-top: 1px solid var(--ds-surface-border);
  padding: var(--ds-space-3);
}

.nav-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--ds-space-2);
}

.nav-title {
  font-size: var(--ds-font-size-xs);
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-primary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.nav-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-2);
  margin-bottom: var(--ds-space-2);
}

.nav-counter {
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-semibold);
  color: var(--ds-color-text);
  min-width: 60px;
  text-align: center;
}

.nav-context {
  background: var(--p-surface-0, white);
  border-radius: var(--ds-radius-md);
  padding: var(--ds-space-2);
  border: 1px solid var(--ds-surface-border);
}

.context-chapter {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  display: block;
  margin-bottom: var(--ds-space-1);
}

.context-text {
  margin: 0;
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
  line-height: 1.5;
  max-height: 4.5em;
  overflow: hidden;
}

.context-text mark {
  background: rgba(59, 130, 246, 0.3);
  color: var(--ds-color-primary);
  font-weight: var(--ds-font-weight-semibold);
  padding: 0.125rem 0.25rem;
  border-radius: 2px;
}

.context-before,
.context-after {
  color: var(--ds-color-text-secondary);
}

/* Dark mode */
.dark .nav-context {
  background: var(--ds-surface-section);
}

/* Coreference section */
.coref-section {
  background: var(--ds-surface-ground);
  padding: var(--ds-space-3);
  border-radius: var(--ds-radius-md);
  margin: 0 calc(-1 * var(--ds-space-4));
  padding-left: var(--ds-space-4);
  padding-right: var(--ds-space-4);
}

.coref-section .section-label {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  margin-bottom: var(--ds-space-3);
}

.coref-section .section-label i {
  color: var(--ds-color-primary);
}

.coref-confidence {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  margin-bottom: var(--ds-space-3);
}

.confidence-label {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text-secondary);
}

.mention-types {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ds-space-2);
  margin-top: var(--ds-space-3);
  padding-top: var(--ds-space-3);
  border-top: 1px solid var(--ds-surface-border);
}

.mention-type-tag {
  font-size: var(--ds-font-size-xs);
  padding: var(--ds-space-1) var(--ds-space-2);
  background: var(--ds-surface-card);
  border-radius: var(--ds-radius-sm);
  color: var(--ds-color-text-secondary);
}

.coref-loading {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  color: var(--ds-color-text-secondary);
  font-size: var(--ds-font-size-sm);
}

/* Mini Timeline */
.timeline-section .section-label {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  margin-bottom: var(--ds-space-3);
}

.timeline-section .section-label i {
  color: var(--ds-color-primary);
}

.mini-timeline {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 60px;
  padding: var(--ds-space-2);
  background: var(--ds-surface-ground);
  border-radius: var(--ds-radius-md);
}

.timeline-bar {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  min-width: 12px;
  max-width: 24px;
}

.bar-fill {
  width: 100%;
  background: var(--ds-color-primary);
  border-radius: 2px 2px 0 0;
  transition: height 0.3s ease;
  margin-top: auto;
}

.bar-label {
  font-size: 0.625rem;
  color: var(--ds-color-text-secondary);
  margin-top: 2px;
}

/* Alerts section */
.alerts-section .section-label {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  margin-bottom: var(--ds-space-2);
}

.alerts-section .section-label i {
  color: var(--ds-color-text-secondary);
}

.section-label-warning i {
  color: var(--orange-500) !important;
}

.alert-list {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.alert-item {
  display: flex;
  align-items: flex-start;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2);
  background: var(--ds-surface-ground);
  border-radius: var(--ds-radius-sm);
  font-size: var(--ds-font-size-sm);
}

.alert-item.alert-attribute {
  border-left: 3px solid var(--orange-500);
}

.alert-desc {
  flex: 1;
  color: var(--ds-color-text);
  line-height: 1.4;
}

/* Dark mode adjustments */
.dark .bar-fill {
  background: var(--ds-color-primary-soft);
}

.dark .alert-item {
  background: var(--ds-surface-section);
}
</style>
