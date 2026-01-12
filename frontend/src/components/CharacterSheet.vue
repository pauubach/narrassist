<template>
  <div class="character-sheet">
    <!-- Header -->
    <div class="sheet-header">
      <div class="character-avatar">
        <i class="pi pi-user"></i>
      </div>
      <div class="character-header-info">
        <h2>{{ character.canonical_name }}</h2>
        <div class="header-tags">
          <Tag severity="success">Personaje</Tag>
          <Tag :severity="getImportanceSeverity(character.importance)">
            {{ getImportanceLabel(character.importance) }}
          </Tag>
        </div>
      </div>
      <div v-if="editable" class="header-actions">
        <Button
          icon="pi pi-pencil"
          rounded
          text
          @click="$emit('edit', character)"
          v-tooltip.left="'Editar'"
        />
      </div>
    </div>

    <Divider />

    <!-- Aliases -->
    <div class="sheet-section">
      <div class="section-header">
        <i class="pi pi-tag"></i>
        <h3>Nombres alternativos</h3>
      </div>
      <div v-if="character.aliases && character.aliases.length > 0" class="aliases-list">
        <Chip
          v-for="(alias, idx) in character.aliases"
          :key="idx"
          :label="alias"
        />
      </div>
      <p v-else class="empty-text">No hay nombres alternativos registrados</p>
    </div>

    <Divider />

    <!-- Estadísticas -->
    <div class="sheet-section">
      <div class="section-header">
        <i class="pi pi-chart-bar"></i>
        <h3>Estadísticas</h3>
      </div>
      <div class="stats-grid">
        <div class="stat-card">
          <i class="pi pi-hashtag stat-icon"></i>
          <div class="stat-info">
            <span class="stat-value">{{ character.mention_count || 0 }}</span>
            <span class="stat-label">Menciones totales</span>
          </div>
        </div>
        <div class="stat-card">
          <i class="pi pi-book stat-icon"></i>
          <div class="stat-info">
            <span class="stat-value">
              {{ character.first_mention_chapter ? `Cap. ${character.first_mention_chapter}` : 'N/A' }}
            </span>
            <span class="stat-label">Primera aparición</span>
          </div>
        </div>
      </div>
    </div>

    <Divider />

    <!-- Atributos físicos -->
    <div class="sheet-section">
      <div class="section-header">
        <i class="pi pi-user"></i>
        <h3>Atributos físicos</h3>
        <Button
          v-if="editable"
          icon="pi pi-plus"
          text
          rounded
          size="small"
          @click="showAddAttributeDialog('physical')"
          v-tooltip.top="'Añadir atributo'"
        />
      </div>
      <div v-if="physicalAttributes.length > 0" class="attributes-list">
        <div
          v-for="attr in physicalAttributes"
          :key="attr.id"
          class="attribute-item"
        >
          <div class="attribute-content">
            <span class="attribute-name">{{ attr.attribute_name }}</span>
            <span class="attribute-value">{{ attr.attribute_value }}</span>
          </div>
          <div v-if="attr.first_mention_chapter" class="attribute-meta">
            <small>Primera mención: Cap. {{ attr.first_mention_chapter }}</small>
          </div>
          <Button
            v-if="editable"
            icon="pi pi-times"
            text
            rounded
            size="small"
            severity="danger"
            @click="$emit('delete-attribute', attr.id)"
          />
        </div>
      </div>
      <p v-else class="empty-text">No hay atributos físicos registrados</p>
    </div>

    <Divider />

    <!-- Atributos psicológicos -->
    <div class="sheet-section">
      <div class="section-header">
        <i class="pi pi-comments"></i>
        <h3>Atributos psicológicos</h3>
        <Button
          v-if="editable"
          icon="pi pi-plus"
          text
          rounded
          size="small"
          @click="showAddAttributeDialog('psychological')"
          v-tooltip.top="'Añadir atributo'"
        />
      </div>
      <div v-if="psychologicalAttributes.length > 0" class="attributes-list">
        <div
          v-for="attr in psychologicalAttributes"
          :key="attr.id"
          class="attribute-item"
        >
          <div class="attribute-content">
            <span class="attribute-name">{{ attr.attribute_name }}</span>
            <span class="attribute-value">{{ attr.attribute_value }}</span>
          </div>
          <div v-if="attr.first_mention_chapter" class="attribute-meta">
            <small>Primera mención: Cap. {{ attr.first_mention_chapter }}</small>
          </div>
          <Button
            v-if="editable"
            icon="pi pi-times"
            text
            rounded
            size="small"
            severity="danger"
            @click="$emit('delete-attribute', attr.id)"
          />
        </div>
      </div>
      <p v-else class="empty-text">No hay atributos psicológicos registrados</p>
    </div>

    <Divider />

    <!-- Relaciones -->
    <div class="sheet-section">
      <div class="section-header">
        <i class="pi pi-sitemap"></i>
        <h3>Relaciones</h3>
        <Button
          v-if="editable"
          icon="pi pi-plus"
          text
          rounded
          size="small"
          @click="showAddRelationshipDialog"
          v-tooltip.top="'Añadir relación'"
        />
      </div>
      <div v-if="relationships.length > 0" class="relationships-list">
        <div
          v-for="rel in relationships"
          :key="rel.id"
          class="relationship-item"
        >
          <div class="relationship-icon">
            <i :class="getRelationshipIcon(rel.relationship_type)"></i>
          </div>
          <div class="relationship-content">
            <span class="relationship-entity">{{ rel.related_entity_name }}</span>
            <span class="relationship-type">{{ rel.relationship_type }}</span>
          </div>
          <Button
            v-if="editable"
            icon="pi pi-times"
            text
            rounded
            size="small"
            severity="danger"
            @click="$emit('delete-relationship', rel.id)"
          />
        </div>
      </div>
      <p v-else class="empty-text">No hay relaciones registradas</p>
    </div>

    <Divider />

    <!-- Timeline -->
    <div class="sheet-section">
      <div class="section-header">
        <i class="pi pi-calendar"></i>
        <h3>Línea temporal</h3>
      </div>
      <Timeline
        v-if="timeline.length > 0"
        :value="timeline"
        align="alternate"
        class="character-timeline"
      >
        <template #content="slotProps">
          <div class="timeline-event">
            <strong>Capítulo {{ slotProps.item.chapter }}</strong>
            <p>{{ slotProps.item.description }}</p>
          </div>
        </template>
      </Timeline>
      <p v-else class="empty-text">No hay eventos en la línea temporal</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Chip from 'primevue/chip'
import Divider from 'primevue/divider'
import Timeline from 'primevue/timeline'
import type { Entity, CharacterAttribute, CharacterRelationship } from '@/types'

interface TimelineEvent {
  chapter: number
  description: string
  type: string
}

const props = withDefaults(defineProps<{
  character: Entity
  attributes?: CharacterAttribute[]
  relationships?: CharacterRelationship[]
  timeline?: TimelineEvent[]
  editable?: boolean
}>(), {
  attributes: () => [],
  relationships: () => [],
  timeline: () => [],
  editable: false
})

const emit = defineEmits<{
  edit: [character: Entity]
  'add-attribute': [category: string]
  'delete-attribute': [id: number | undefined]
  'add-relationship': []
  'delete-relationship': [id: number | undefined]
}>()

// Computed
const physicalAttributes = computed(() => {
  return props.attributes.filter(attr => attr.attribute_category === 'physical')
})

const psychologicalAttributes = computed(() => {
  return props.attributes.filter(attr => attr.attribute_category === 'psychological')
})

// Funciones
const showAddAttributeDialog = (category: string) => {
  emit('add-attribute', category)
}

const showAddRelationshipDialog = () => {
  emit('add-relationship')
}

const getImportanceSeverity = (importance: string): string => {
  const severities: Record<string, string> = {
    'high': 'danger',
    'medium': 'warning',
    'low': 'info'
  }
  return severities[importance] || 'secondary'
}

const getImportanceLabel = (importance: string): string => {
  const labels: Record<string, string> = {
    'high': 'Alta Importancia',
    'medium': 'Media Importancia',
    'low': 'Baja Importancia'
  }
  return labels[importance] || importance
}

const getRelationshipIcon = (type: string): string => {
  const icons: Record<string, string> = {
    'family': 'pi pi-heart',
    'friend': 'pi pi-users',
    'enemy': 'pi pi-times-circle',
    'romantic': 'pi pi-heart-fill',
    'professional': 'pi pi-briefcase'
  }
  return icons[type] || 'pi pi-link'
}
</script>

<style scoped>
.character-sheet {
  display: flex;
  flex-direction: column;
  gap: 0;
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
}

.sheet-header {
  display: flex;
  align-items: flex-start;
  gap: 1.5rem;
}

.character-avatar {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-600) 100%);
  border-radius: 50%;
  flex-shrink: 0;
}

.character-avatar i {
  font-size: 2.5rem;
  color: white;
}

.character-header-info {
  flex: 1;
}

.character-header-info h2 {
  margin: 0 0 0.75rem 0;
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-color);
}

.header-tags {
  display: flex;
  gap: 0.5rem;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
}

.sheet-section {
  padding: 1.5rem 0;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.section-header i {
  font-size: 1.25rem;
  color: var(--primary-color);
}

.section-header h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-color);
  flex: 1;
}

.empty-text {
  color: var(--text-color-secondary);
  font-size: 0.875rem;
  margin: 0;
  font-style: italic;
}

/* Aliases */
.aliases-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

/* Stats */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: var(--surface-50);
  border-radius: 8px;
  border: 1px solid var(--surface-200);
}

.stat-icon {
  font-size: 1.5rem;
  color: var(--primary-color);
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-color);
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  text-transform: uppercase;
}

/* Attributes */
.attributes-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.attribute-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1rem;
  background: var(--surface-50);
  border-radius: 6px;
  border-left: 3px solid var(--primary-color);
}

.attribute-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: 0.25rem;
}

.attribute-name {
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--text-color);
}

.attribute-value {
  font-size: 0.9375rem;
  color: var(--text-color-secondary);
}

.attribute-meta {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

/* Relationships */
.relationships-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.relationship-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1rem;
  background: var(--surface-50);
  border-radius: 6px;
}

.relationship-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-100);
  border-radius: 50%;
  flex-shrink: 0;
}

.relationship-icon i {
  font-size: 1.125rem;
  color: var(--primary-color);
}

.relationship-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: 0.25rem;
}

.relationship-entity {
  font-weight: 600;
  font-size: 0.9375rem;
  color: var(--text-color);
}

.relationship-type {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  text-transform: capitalize;
}

/* Timeline */
.character-timeline {
  margin-top: 1rem;
}

.timeline-event {
  padding: 0.5rem 0;
}

.timeline-event strong {
  color: var(--primary-color);
  display: block;
  margin-bottom: 0.25rem;
}

.timeline-event p {
  margin: 0;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}
</style>
