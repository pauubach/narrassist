<script setup lang="ts">
import { computed } from 'vue'
import Button from 'primevue/button'
import type { Entity } from '@/types'

/**
 * TextSelectionInspector - Panel de información sobre texto seleccionado.
 *
 * Muestra:
 * - Estadísticas del texto seleccionado (palabras, caracteres)
 * - Entidades mencionadas en la selección
 * - Acciones rápidas (copiar, buscar similares)
 */

interface TextSelection {
  start: number
  end: number
  text: string
  chapter?: string
}

const props = defineProps<{
  /** Selección de texto actual */
  selection: TextSelection
  /** Entidades del proyecto (para detectar menciones) */
  entities?: Entity[]
}>()

const emit = defineEmits<{
  /** Cerrar el inspector */
  (e: 'close'): void
  /** Buscar texto similar */
  (e: 'search-similar', text: string): void
  /** Seleccionar entidad mencionada */
  (e: 'select-entity', entityId: number): void
  /** Preguntar a la IA sobre el texto seleccionado */
  (e: 'ask-ai', text: string): void
}>()

// Estadísticas del texto
const wordCount = computed(() => {
  if (!props.selection.text) return 0
  return props.selection.text.trim().split(/\s+/).filter(w => w.length > 0).length
})

const charCount = computed(() => props.selection.text?.length || 0)

const charCountNoSpaces = computed(() => {
  if (!props.selection.text) return 0
  return props.selection.text.replace(/\s/g, '').length
})

// Entidades mencionadas en la selección
const mentionedEntities = computed(() => {
  if (!props.entities || !props.selection.text) return []

  const textLower = props.selection.text.toLowerCase()
  return props.entities.filter(entity => {
    // Buscar nombre principal
    if (textLower.includes(entity.name.toLowerCase())) return true
    // Buscar aliases
    if (entity.aliases?.some(alias => textLower.includes(alias.toLowerCase()))) return true
    return false
  }).slice(0, 5) // Limitar a 5
})

const hasMentionedEntities = computed(() => mentionedEntities.value.length > 0)

// Preview del texto (truncado si es muy largo)
const textPreview = computed(() => {
  const text = props.selection.text || ''
  if (text.length <= 150) return text
  return text.substring(0, 150) + '...'
})

// Copiar al portapapeles
async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(props.selection.text)
  } catch (err) {
    console.error('Error copying to clipboard:', err)
  }
}

function getEntityIcon(type: string): string {
  const icons: Record<string, string> = {
    character: 'pi-user',
    location: 'pi-map-marker',
    organization: 'pi-building',
    object: 'pi-box',
    event: 'pi-calendar',
  }
  return icons[type] || 'pi-tag'
}
</script>

<template>
  <div class="text-selection-inspector">
    <!-- Header -->
    <div class="inspector-header">
      <div class="header-icon">
        <i class="pi pi-text-select"></i>
      </div>
      <div class="header-info">
        <span class="header-title">Texto seleccionado</span>
        <span v-if="selection.chapter" class="header-chapter">{{ selection.chapter }}</span>
      </div>
      <Button
        v-tooltip.bottom="'Cerrar'"
        icon="pi pi-times"
        text
        rounded
        size="small"
        @click="emit('close')"
      />
    </div>

    <!-- Contenido -->
    <div class="inspector-body">
      <!-- Preview del texto -->
      <div class="text-preview">
        <p>{{ textPreview }}</p>
      </div>

      <!-- Estadísticas -->
      <div class="stats-section">
        <div class="stat-item">
          <span class="stat-value">{{ wordCount }}</span>
          <span class="stat-label">palabras</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ charCount }}</span>
          <span class="stat-label">caracteres</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ charCountNoSpaces }}</span>
          <span class="stat-label">sin espacios</span>
        </div>
      </div>

      <!-- Entidades mencionadas -->
      <div v-if="hasMentionedEntities" class="entities-section">
        <div class="section-label">
          <i class="pi pi-users"></i>
          Entidades mencionadas
        </div>
        <div class="entity-list">
          <div
            v-for="entity in mentionedEntities"
            :key="entity.id"
            class="entity-item"
            @click="emit('select-entity', entity.id)"
          >
            <i :class="`pi ${getEntityIcon(entity.type)}`"></i>
            <span class="entity-name">{{ entity.name }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Acciones -->
    <div class="inspector-actions">
      <Button
        label="Preguntar a la IA"
        icon="pi pi-comments"
        size="small"
        class="primary-action"
        @click="emit('ask-ai', selection.text)"
      />
      <div class="secondary-actions">
        <Button
          label="Copiar"
          icon="pi pi-copy"
          size="small"
          outlined
          @click="copyToClipboard"
        />
        <Button
          label="Buscar similar"
          icon="pi pi-search"
          size="small"
          outlined
          @click="emit('search-similar', selection.text)"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.text-selection-inspector {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  min-width: 0;
  overflow: hidden;
}

.inspector-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-3);
  padding: var(--ds-space-3) var(--ds-space-4);
  border-bottom: 1px solid var(--surface-border);
}

.header-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: var(--primary-100);
  border-radius: var(--border-radius);
  color: var(--primary-color);
}

.header-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.header-title {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--text-color);
}

.header-chapter {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

.inspector-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--ds-space-4);
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-4);
}

.text-preview {
  background: var(--surface-50);
  padding: var(--ds-space-3);
  border-radius: var(--border-radius);
  border-left: 3px solid var(--primary-color);
}

.text-preview p {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--text-color);
  font-style: italic;
}

.stats-section {
  display: flex;
  gap: var(--ds-space-3);
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--ds-space-3);
  background: var(--surface-ground);
  border-radius: var(--border-radius);
  text-align: center;
}

.stat-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-color);
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.entities-section {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
}

.section-label {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.section-label i {
  color: var(--primary-color);
}

.entity-list {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-1);
}

.entity-item {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: var(--ds-space-2);
  background: var(--surface-ground);
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: background-color 0.2s;
}

.entity-item:hover {
  background: var(--surface-hover);
}

.entity-item i {
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

.entity-name {
  font-size: 0.9rem;
  color: var(--text-color);
}

.inspector-actions {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2);
  padding: var(--ds-space-3) var(--ds-space-4);
  border-top: 1px solid var(--surface-border);
}

.inspector-actions .primary-action {
  width: 100%;
}

.secondary-actions {
  display: flex;
  gap: var(--ds-space-2);
}

.secondary-actions .p-button {
  flex: 1;
}

/* Dark mode */
.dark .header-icon {
  background: var(--primary-900);
}

.dark .text-preview {
  background: var(--surface-800);
}

.dark .stat-item {
  background: var(--surface-700);
}

.dark .entity-item {
  background: var(--surface-800);
}

.dark .entity-item:hover {
  background: var(--surface-700);
}
</style>
