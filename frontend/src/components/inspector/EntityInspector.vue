<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import type { Entity } from '@/types'
import { useEntityUtils } from '@/composables/useEntityUtils'
import { useMentionNavigation } from '@/composables/useMentionNavigation'

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

// Estado local para controlar si está activa la navegación
const isNavigating = ref(false)

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

/** Inicia la navegación de menciones */
async function startMentionNavigation() {
  isNavigating.value = true
  await mentionNav.startNavigation(props.entity.id)
}

/** Detener navegación y limpiar */
function stopNavigation() {
  mentionNav.clear()
  isNavigating.value = false
}

/** Detener navegación cuando cambia la entidad */
watch(() => props.entity.id, () => {
  if (isNavigating.value) {
    stopNavigation()
  }
})
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
          <span class="entity-type">{{ entityTypeLabel }}</span>
          <Tag
            v-if="isMerged"
            severity="info"
            class="merged-tag"
            v-tooltip.bottom="'Esta entidad es resultado de una fusion'"
          >
            <i class="pi pi-link"></i>
            Fusionada
          </Tag>
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
            <span class="stat-value">{{ entity.mentionCount || 0 }}</span>
            <span class="stat-label">apariciones</span>
          </div>
          <div v-if="entity.firstMentionChapter" class="stat-item">
            <i class="pi pi-bookmark"></i>
            <span class="stat-value">Cap. {{ entity.firstMentionChapter }}</span>
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
    </div>

    <!-- Barra de navegación de apariciones -->
    <div v-if="isNavigating && mentionNav.isActive.value" class="mention-navigation">
      <div class="nav-header">
        <span class="nav-title">Navegando apariciones</span>
        <Button
          icon="pi pi-times"
          text
          rounded
          size="small"
          @click="stopNavigation"
          v-tooltip.left="'Cerrar navegación'"
        />
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
        v-if="!isNavigating"
        :label="mentionNav.state.value.loading ? 'Cargando...' : 'Ver en texto'"
        icon="pi pi-search"
        size="small"
        outlined
        :loading="mentionNav.state.value.loading"
        :disabled="!entity.mentionCount || entity.mentionCount === 0"
        @click="startMentionNavigation"
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
</style>
