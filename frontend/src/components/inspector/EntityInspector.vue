<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import InputSwitch from 'primevue/inputswitch'
import Slider from 'primevue/slider'
import DsBadge from '@/components/ds/DsBadge.vue'
import type { Entity, Alert } from '@/types'
import { useEntityUtils } from '@/composables/useEntityUtils'
import { useMentionNavigation } from '@/composables/useMentionNavigation'
import { useAlertUtils } from '@/composables/useAlertUtils'
import { api } from '@/services/apiClient'

const { formatChapterLabel, getSeverityConfig } = useAlertUtils()

// Coreference info state (solo confianza para indicador compacto)
interface CoreferenceInfo {
  overallConfidence: number
}

const corefInfo = ref<CoreferenceInfo | null>(null)
const corefLoading = ref(false)

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

/** Cargar información de correferencia (solo confianza) */
async function loadCoreferenceInfo(entityId: number) {
  corefLoading.value = true

  try {
    const result = await api.getRaw<any>(
      `/api/projects/${props.projectId}/entities/${entityId}/coreference`
    )

    if (result.success && result.data) {
      corefInfo.value = { overallConfidence: result.data.overallConfidence ?? 1 }
    } else {
      corefInfo.value = null
    }
  } catch {
    corefInfo.value = null
  } finally {
    corefLoading.value = false
  }
}

/** Tiene confianza baja que merece aviso al usuario */
const hasLowConfidence = computed(() => {
  return corefInfo.value != null && corefInfo.value.overallConfidence < 0.7
})

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

const _hasRelatedAlerts = computed(() => relatedAlerts.value.length > 0)

// ============================================================================
// Mention Role Statistics (Mejora 3)
// ============================================================================

interface RoleStats {
  total: number
  asSubject: number      // Sujeto (nsubj, etc.)
  asObject: number       // Objeto directo/indirecto
  inDialogue: number     // Tema de conversación (verbos comunicativos)
  passive: number        // Contextos pasivos (< 0.75 confianza)
  protagonismScore: number  // % de menciones activas (sujeto + objeto + diálogo)
}

const roleStats = computed<RoleStats>(() => {
  const stats: RoleStats = {
    total: mentionNav.state.value.mentions.length,
    asSubject: 0,
    asObject: 0,
    inDialogue: 0,
    passive: 0,
    protagonismScore: 0,
  }

  mentionNav.state.value.mentions.forEach((m: any) => {
    const reasoning = (m.validationReasoning?.toLowerCase() || '') as string
    const conf = m.confidence || 0

    // Categorizar por rol sintáctico
    if (reasoning.includes('sujeto')) {
      stats.asSubject++
    } else if (reasoning.includes('objeto')) {
      stats.asObject++
    } else if (reasoning.includes('comunicativo') || reasoning.includes('verbo')) {
      stats.inDialogue++
    } else if (conf < 0.75 || reasoning.includes('posesivo')) {
      stats.passive++
    }
  })

  // Calcular protagonismo (%)
  const activeCount = stats.asSubject + stats.asObject + stats.inDialogue
  stats.protagonismScore = stats.total > 0 ? Math.round((activeCount / stats.total) * 100) : 0

  return stats
})

const hasRoleStats = computed(() => roleStats.value.total > 0)

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

/** Keyboard navigation for mentions: ←/→ prev/next, Home/End first/last */
function onMentionNavKeydown(event: KeyboardEvent) {
  if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
    event.preventDefault()
    mentionNav.goToPrevious()
  } else if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
    event.preventDefault()
    mentionNav.goToNext()
  } else if (event.key === 'Home') {
    event.preventDefault()
    mentionNav.goToMention(0)
  } else if (event.key === 'End') {
    event.preventDefault()
    mentionNav.goToMention(mentionNav.totalMentions.value - 1)
  }
}

/**
 * Navega a la primera aparición en un capítulo específico
 */
function onChapterClick(chapterNumber: number) {
  mentionNav.goToChapter(chapterNumber)
}
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
            v-tooltip.bottom="'Esta entidad es resultado de una fusión'"
            color="info"
            size="sm"
            icon="pi pi-link"
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

      <!-- Aviso de confianza baja (sin detalles técnicos) -->
      <div v-if="hasLowConfidence" class="info-section">
        <div class="confidence-warning">
          <i class="pi pi-info-circle"></i>
          <span>Confianza de detección: {{ Math.round((corefInfo?.overallConfidence ?? 0) * 100) }}%</span>
        </div>
      </div>

      <!-- Mini Timeline de apariciones -->
      <div v-if="hasChapterData" class="info-section timeline-section">
        <div class="section-label">
          <i class="pi pi-chart-bar"></i>
          Apariciones por capítulo
        </div>
        <div class="mini-timeline">
          <button
            v-for="ch in chapterAppearances"
            :key="ch.chapterNumber"
            type="button"
            class="timeline-bar"
            :class="{
              'timeline-bar--active': mentionNav.currentMention.value?.chapterNumber === ch.chapterNumber
            }"
            :title="`Cap. ${ch.chapterNumber}: ${ch.mentionCount} menciones - Click para ir a la primera aparición`"
            @click="onChapterClick(ch.chapterNumber)"
          >
            <div
              class="bar-fill"
              :style="{ height: `${Math.max(ch.percentage, 8)}%` }"
            ></div>
            <span class="bar-label">{{ ch.chapterNumber }}</span>
          </button>
        </div>
      </div>

      <!-- Estadísticas de Roles (Mejora 3) -->
      <div v-if="hasRoleStats" class="info-section role-stats-section">
        <div class="section-label">
          <i class="pi pi-users"></i>
          Análisis de protagonismo
        </div>

        <!-- Barra de protagonismo -->
        <div class="protagonism-meter">
          <div class="meter-header">
            <span class="meter-label">Menciones activas</span>
            <span class="meter-value">{{ roleStats.protagonismScore }}%</span>
          </div>
          <div class="meter-bar">
            <div
              class="meter-fill"
              :class="{
                'meter-fill--high': roleStats.protagonismScore >= 70,
                'meter-fill--medium': roleStats.protagonismScore >= 40 && roleStats.protagonismScore < 70,
                'meter-fill--low': roleStats.protagonismScore < 40
              }"
              :style="{ width: `${roleStats.protagonismScore}%` }"
            ></div>
          </div>
        </div>

        <!-- Desglose por roles -->
        <div class="role-breakdown">
          <div v-if="roleStats.asSubject > 0" class="role-stat">
            <i class="pi pi-user" style="color: var(--green-500)"></i>
            <span class="role-count">{{ roleStats.asSubject }}</span>
            <span class="role-label">como sujeto</span>
          </div>
          <div v-if="roleStats.asObject > 0" class="role-stat">
            <i class="pi pi-arrow-right" style="color: var(--blue-500)"></i>
            <span class="role-count">{{ roleStats.asObject }}</span>
            <span class="role-label">como objeto</span>
          </div>
          <div v-if="roleStats.inDialogue > 0" class="role-stat">
            <i class="pi pi-comments" style="color: var(--purple-500)"></i>
            <span class="role-count">{{ roleStats.inDialogue }}</span>
            <span class="role-label">en diálogos</span>
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
    <div
      v-if="mentionNav.isActive.value"
      class="mention-navigation"
      tabindex="0"
      role="group"
      aria-label="Navegación entre apariciones"
      @keydown="onMentionNavKeydown"
    >
      <div class="nav-header">
        <span class="nav-title">APARICIONES</span>
        <span class="nav-hint">← → para navegar</span>
      </div>

      <div class="nav-controls">
        <Button
          v-tooltip.bottom="'Anterior (←)'"
          icon="pi pi-chevron-left"
          text
          rounded
          size="small"
          :disabled="!mentionNav.canGoPrevious.value"
          @click="mentionNav.goToPrevious()"
        />
        <span class="nav-counter">{{ mentionNav.navigationLabel.value }}</span>
        <Button
          v-tooltip.bottom="'Siguiente (→)'"
          icon="pi pi-chevron-right"
          text
          rounded
          size="small"
          :disabled="!mentionNav.canGoNext.value"
          @click="mentionNav.goToNext()"
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
        v-tooltip.bottom="'Restaurar las entidades originales'"
        label="Deshacer fusion"
        icon="pi pi-replay"
        size="small"
        outlined
        severity="warning"
        @click="emit('undo-merge')"
      />
    </div>
  </div>
</template>

<style scoped>
.entity-inspector {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  min-width: 0;
  overflow: hidden;
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
  min-width: 0;
  overflow-y: auto;
  overflow-x: hidden;
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
  min-width: 0;
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
  grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
  gap: var(--ds-space-2);
  min-width: 0;
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
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
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

.nav-hint {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  opacity: 0;
  transition: opacity 0.15s;
}

.mention-navigation:focus .nav-hint,
.mention-navigation:focus-within .nav-hint {
  opacity: 1;
}

.mention-navigation:focus {
  outline: 2px solid var(--ds-color-primary);
  outline-offset: -2px;
  border-radius: var(--ds-radius-md);
}

/* Filtro de menciones activas (Mejora 2) */
.nav-filter {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--ds-space-2);
  background: var(--p-surface-50, #f9fafb);
  border-radius: var(--ds-radius-sm);
  margin-bottom: var(--ds-space-3);
  gap: var(--ds-space-2);
}

.filter-label {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
  cursor: pointer;
  user-select: none;
}

.filter-label i {
  color: var(--ds-color-text-secondary);
}

/* Confidence Threshold Slider (Mejora 5) */
.confidence-threshold-filter {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2);
  background: var(--p-surface-50, #f9fafb);
  border-radius: var(--ds-radius-sm);
  margin-bottom: var(--ds-space-3);
}

.threshold-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.threshold-label {
  display: flex;
  align-items: center;
  gap: var(--ds-space-1);
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
  font-weight: var(--ds-font-weight-medium);
}

.threshold-label i {
  color: var(--ds-color-text-secondary);
}

.threshold-value {
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-bold);
  color: var(--ds-color-primary);
}

.confidence-slider {
  width: 100%;
}

.threshold-hints {
  display: flex;
  justify-content: space-between;
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
  margin-top: -4px;
}

.hint-low,
.hint-mid,
.hint-high {
  user-select: none;
}

.dark .confidence-threshold-filter {
  background: var(--ds-surface-section);
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
  background: var(--ds-color-primary-subtle, color-mix(in srgb, var(--p-primary-color, #3B82F6) 30%, transparent));
  color: var(--ds-color-primary);
  font-weight: var(--ds-font-weight-semibold);
  padding: 0.125rem 0.25rem;
  border-radius: var(--app-radius-sm);
}

.context-before,
.context-after {
  color: var(--ds-color-text-secondary);
}

/* Diagnostic Badge (Mejora 1) */
.mention-diagnostic-badge {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2);
  margin-top: var(--ds-space-2);
  border-radius: var(--ds-radius-sm);
  font-size: var(--ds-font-size-xs);
  cursor: help;
  transition: all 0.2s ease;
}

.mention-diagnostic-badge:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.badge--warning {
  background: var(--p-yellow-50, #fefce8);
  border: 1px solid var(--p-yellow-200, #fde68a);
  color: var(--p-yellow-700, #a16207);
}

.badge--error {
  background: var(--p-red-50, #fef2f2);
  border: 1px solid var(--p-red-200, #fecaca);
  color: var(--p-red-700, #b91c1c);
}

.mention-diagnostic-badge i {
  font-size: 0.875rem;
  flex-shrink: 0;
}

.badge-label {
  font-weight: var(--ds-font-weight-semibold);
}

.badge-reason {
  font-size: var(--ds-font-size-xs);
  opacity: 0.9;
  margin-left: auto;
  max-width: 60%;
  text-align: right;
  line-height: 1.3;
}

.dark .badge--warning {
  background: rgba(234, 179, 8, 0.1);
  border-color: rgba(234, 179, 8, 0.3);
  color: var(--p-yellow-400, #facc15);
}

.dark .badge--error {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
  color: var(--p-red-400, #f87171);
}

/* Dark mode */
.dark .nav-context {
  background: var(--ds-surface-section);
}

/* Confidence warning */
.confidence-warning {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2) var(--ds-space-3);
  background: var(--p-yellow-50, #fefce8);
  border: 1px solid var(--p-yellow-200, #fde68a);
  border-radius: var(--ds-radius-md);
  font-size: var(--ds-font-size-sm);
  color: var(--p-yellow-700, #a16207);
}

.confidence-warning i {
  font-size: 1rem;
  flex-shrink: 0;
}

.dark .confidence-warning {
  background: rgba(234, 179, 8, 0.1);
  border-color: rgba(234, 179, 8, 0.3);
  color: var(--p-yellow-400, #facc15);
}

/* Role Statistics (Mejora 3) */
.role-stats-section .section-label {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  margin-bottom: var(--ds-space-3);
}

.role-stats-section .section-label i {
  color: var(--ds-color-primary);
}

.protagonism-meter {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
  margin-bottom: var(--ds-space-3);
}

.meter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.meter-label {
  font-size: var(--ds-font-size-sm);
  color: var(--ds-color-text);
  font-weight: var(--ds-font-weight-medium);
}

.meter-value {
  font-size: var(--ds-font-size-lg);
  font-weight: var(--ds-font-weight-bold);
  color: var(--ds-color-primary);
}

.meter-bar {
  height: 8px;
  background: var(--ds-surface-ground);
  border-radius: var(--ds-radius-full);
  overflow: hidden;
}

.meter-fill {
  height: 100%;
  border-radius: var(--ds-radius-full);
  transition: width 0.3s ease;
}

.meter-fill--high {
  background: linear-gradient(90deg, var(--green-500), var(--ds-color-success, #16a34a));
}

.meter-fill--medium {
  background: linear-gradient(90deg, var(--blue-500), var(--blue-600));
}

.meter-fill--low {
  background: linear-gradient(90deg, var(--orange-500), var(--orange-600));
}

.role-breakdown {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--ds-space-2);
}

.role-stat {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2);
  background: var(--ds-surface-ground);
  border-radius: var(--ds-radius-sm);
}

.role-stat i {
  font-size: 0.875rem;
  flex-shrink: 0;
}

.role-stat .role-count {
  font-size: var(--ds-font-size-sm);
  font-weight: var(--ds-font-weight-bold);
  color: var(--ds-color-text);
}

.role-stat .role-label {
  font-size: var(--ds-font-size-xs);
  color: var(--ds-color-text-secondary);
}

.role-stat--muted {
  opacity: 0.7;
}

.dark .role-breakdown .role-stat {
  background: var(--ds-surface-section);
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
  border: none;
  background: transparent;
  padding: 0;
  cursor: pointer;
  position: relative;
  transition: transform 0.2s ease;
}

.timeline-bar:hover {
  transform: translateY(-2px);
}

.timeline-bar:hover .bar-fill {
  opacity: 0.8;
}

.timeline-bar:active {
  transform: translateY(0);
}

.timeline-bar--active .bar-fill {
  background: var(--ds-color-primary-emphasis, var(--ds-color-primary));
  box-shadow: 0 0 0 2px var(--ds-color-primary-soft);
}

.timeline-bar--active .bar-label {
  color: var(--ds-color-primary);
  font-weight: var(--ds-font-weight-semibold);
}

.bar-fill {
  width: 100%;
  background: var(--ds-color-primary);
  border-radius: 2px 2px 0 0;
  transition: all 0.2s ease;
  margin-top: auto;
  pointer-events: none;
}

.bar-label {
  font-size: 0.625rem;
  color: var(--ds-color-text-secondary);
  margin-top: 2px;
  pointer-events: none;
  transition: color 0.2s ease, font-weight 0.2s ease;
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
