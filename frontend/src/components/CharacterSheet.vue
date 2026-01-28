<template>
  <div class="character-sheet">
    <!-- Header -->
    <div class="sheet-header">
      <div class="character-avatar">
        <i :class="entityTypeIcon"></i>
      </div>
      <div class="character-header-info">
        <h2>{{ character.name }}</h2>
        <div class="header-tags">
          <Tag :severity="entityTypeSeverity">{{ entityTypeLabel }}</Tag>
          <Tag :severity="getImportanceSeverity(character.importance)">
            {{ getImportanceLabel(character.importance) }}
          </Tag>
          <Tag
            v-if="isMerged"
            v-tooltip.bottom="'Esta entidad es resultado de una fusion'"
            severity="info"
            class="merged-tag"
          >
            <i class="pi pi-link"></i>
            Fusionada
          </Tag>
        </div>
      </div>
      <div v-if="editable" class="header-actions">
        <Button
          v-if="isMerged"
          v-tooltip.left="'Deshacer fusion'"
          icon="pi pi-replay"
          rounded
          text
          severity="warning"
          @click="$emit('undo-merge')"
        />
        <Button
          v-tooltip.left="'Editar'"
          icon="pi pi-pencil"
          rounded
          text
          @click="$emit('edit', character)"
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
            <span class="stat-value">{{ character.mentionCount || 0 }}</span>
            <span class="stat-label">Apariciones totales</span>
          </div>
        </div>
        <div class="stat-card">
          <i class="pi pi-book stat-icon"></i>
          <div class="stat-info">
            <span class="stat-value">
              {{ formatChapterLabel(character.firstMentionChapter) || 'N/A' }}
            </span>
            <span class="stat-label">Primera aparición</span>
          </div>
        </div>
      </div>
    </div>

    <Divider />

    <!-- Secciones de atributos dinámicas según tipo de entidad -->
    <div
      v-for="(section, sectionIdx) in attributeConfig"
      :key="`section-${sectionIdx}`"
      class="sheet-section-wrapper"
    >
      <div class="sheet-section">
        <div class="section-header">
          <i :class="section.icon"></i>
          <h3>{{ section.label }}</h3>
          <Button
            v-if="editable"
            v-tooltip.top="'Añadir atributo'"
            icon="pi pi-plus"
            text
            rounded
            size="small"
            @click="showAddAttributeDialog(section.categories[0])"
          />
        </div>
        <div v-if="getAttributesBySection(sectionIdx).length > 0" class="attributes-list">
          <div
            v-for="attr in getAttributesBySection(sectionIdx)"
            :key="attr.id"
            class="attribute-item"
          >
            <div class="attribute-content">
              <span class="attribute-name">{{ getAttributeLabel(attr.name) }}</span>
              <span class="attribute-value">{{ attr.value }}</span>
            </div>
            <div v-if="attr.firstMentionChapter" class="attribute-meta">
              <small>Primera aparición: {{ formatChapterLabel(attr.firstMentionChapter) }}</small>
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
        <p v-else class="empty-text">No hay {{ section.label.toLowerCase() }} registrados</p>
      </div>
      <Divider />
    </div>

    <!-- Relaciones (solo para personajes y organizaciones) -->
    <template v-if="supportsRelationships">
      <div class="sheet-section">
        <div class="section-header">
          <i class="pi pi-sitemap"></i>
          <h3>Relaciones</h3>
          <Button
            v-if="editable"
            v-tooltip.top="'Añadir relación'"
            icon="pi pi-plus"
            text
            rounded
            size="small"
            @click="showAddRelationshipDialog"
          />
        </div>
        <div v-if="relationships.length > 0" class="relationships-list">
          <div
            v-for="rel in relationships"
            :key="rel.id"
            class="relationship-item"
          >
            <div class="relationship-icon">
              <i :class="getRelationshipIcon(rel.relationshipType)"></i>
            </div>
            <div class="relationship-content">
              <span class="relationship-entity">{{ rel.relatedEntityName }}</span>
              <span class="relationship-type">{{ rel.relationshipType }}</span>
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
    </template>

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

    <!-- Análisis avanzado solo para personajes -->
    <template v-if="projectId && supportsBehaviorAnalysis">
      <Divider />

      <!-- Análisis de Comportamiento (LLM) -->
      <div class="sheet-section">
        <BehaviorExpectations
          :project-id="projectId"
          :character-id="character.id"
          :character-name="character.name"
        />
      </div>

      <Divider />

      <!-- Análisis Emocional -->
      <div class="sheet-section">
        <EmotionalAnalysis
          :project-id="projectId"
          :character-name="character.name"
        />
      </div>

      <Divider />

      <!-- Perfil de Voz -->
      <div class="sheet-section">
        <VoiceProfile
          :project-id="projectId"
          :character-id="character.id"
          :character-name="character.name"
        />
      </div>

      <Divider />

      <!-- Conocimiento del Personaje -->
      <div class="sheet-section">
        <CharacterKnowledgeAnalysis
          :project-id="projectId"
          :character-id="character.id"
          :character-name="character.name"
        />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Chip from 'primevue/chip'
import Divider from 'primevue/divider'
import Timeline from 'primevue/timeline'
import BehaviorExpectations from '@/components/BehaviorExpectations.vue'
import EmotionalAnalysis from '@/components/EmotionalAnalysis.vue'
import VoiceProfile from '@/components/VoiceProfile.vue'
import CharacterKnowledgeAnalysis from '@/components/CharacterKnowledgeAnalysis.vue'
import type { Entity, CharacterAttribute, CharacterRelationship } from '@/types'
import { useAlertUtils } from '@/composables/useAlertUtils'

// Traduce claves de atributos en inglés a etiquetas en español
const ATTRIBUTE_LABELS: Record<string, string> = {
  eye_color: 'Color de ojos',
  hair_color: 'Color de pelo',
  hair_type: 'Tipo de pelo',
  age: 'Edad',
  height: 'Altura',
  build: 'Complexión',
  skin: 'Piel',
  distinctive_feature: 'Rasgo distintivo',
  profession: 'Profesión',
  occupation: 'Ocupación',
  personality: 'Personalidad',
  temperament: 'Temperamento',
}

function getAttributeLabel(key: string): string {
  if (key in ATTRIBUTE_LABELS) return ATTRIBUTE_LABELS[key]
  return key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
}

const { formatChapterLabel } = useAlertUtils()

interface TimelineEvent {
  chapter: number
  description: string
  type: string
}

const props = withDefaults(defineProps<{
  character: Entity
  projectId?: number
  attributes?: CharacterAttribute[]
  relationships?: CharacterRelationship[]
  timeline?: TimelineEvent[]
  editable?: boolean
}>(), {
  projectId: undefined,
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
  'undo-merge': []
}>()

// Configuración de atributos válidos por tipo de entidad
const ATTRIBUTE_CONFIG: Record<string, { categories: string[], icon: string, label: string }[]> = {
  character: [
    { categories: ['physical'], icon: 'pi pi-user', label: 'Atributos físicos' },
    { categories: ['psychological'], icon: 'pi pi-comments', label: 'Atributos psicológicos' },
  ],
  location: [
    { categories: ['physical', 'geographic'], icon: 'pi pi-map', label: 'Características del lugar' },
    { categories: ['atmosphere'], icon: 'pi pi-sun', label: 'Atmósfera y ambiente' },
  ],
  object: [
    { categories: ['physical', 'appearance'], icon: 'pi pi-box', label: 'Características físicas' },
    { categories: ['function', 'history'], icon: 'pi pi-info-circle', label: 'Función e historia' },
  ],
  organization: [
    { categories: ['structure'], icon: 'pi pi-sitemap', label: 'Estructura' },
    { categories: ['purpose', 'history'], icon: 'pi pi-flag', label: 'Propósito e historia' },
  ],
  event: [
    { categories: ['temporal'], icon: 'pi pi-calendar', label: 'Información temporal' },
    { categories: ['participants', 'consequences'], icon: 'pi pi-users', label: 'Participantes y consecuencias' },
  ],
  concept: [
    { categories: ['definition'], icon: 'pi pi-book', label: 'Definición' },
    { categories: ['examples', 'related'], icon: 'pi pi-link', label: 'Ejemplos y relaciones' },
  ],
}

// Computed
const isMerged = computed(() => {
  return props.character.mergedFromIds && props.character.mergedFromIds.length > 0
})

// Obtener configuración de atributos para el tipo de entidad actual
const attributeConfig = computed(() => {
  const entityType = props.character.type || 'character'
  return ATTRIBUTE_CONFIG[entityType] || ATTRIBUTE_CONFIG.character
})

// Filtrar atributos por las categorías configuradas para este tipo
const getAttributesBySection = (sectionIndex: number) => {
  const config = attributeConfig.value[sectionIndex]
  if (!config) return []
  return props.attributes.filter(attr => config.categories.includes(attr.category))
}

// Para compatibilidad con el código existente
const physicalAttributes = computed(() => {
  return props.attributes.filter(attr => attr.category === 'physical')
})

const psychologicalAttributes = computed(() => {
  return props.attributes.filter(attr => attr.category === 'psychological')
})

// Verificar si el tipo de entidad soporta relaciones (principalmente personajes y organizaciones)
const supportsRelationships = computed(() => {
  return ['character', 'organization'].includes(props.character.type || 'character')
})

// Verificar si el tipo soporta análisis de comportamiento (solo personajes)
const supportsBehaviorAnalysis = computed(() => {
  return props.character.type === 'character'
})

// Iconos y labels por tipo de entidad
const entityTypeIcon = computed(() => {
  const icons: Record<string, string> = {
    character: 'pi pi-user',
    location: 'pi pi-map-marker',
    object: 'pi pi-box',
    organization: 'pi pi-building',
    event: 'pi pi-calendar',
    concept: 'pi pi-lightbulb',
  }
  return icons[props.character.type] || 'pi pi-tag'
})

const entityTypeLabel = computed(() => {
  const labels: Record<string, string> = {
    character: 'Personaje',
    location: 'Lugar',
    object: 'Objeto',
    organization: 'Organización',
    event: 'Evento',
    concept: 'Concepto',
  }
  return labels[props.character.type] || 'Entidad'
})

const entityTypeSeverity = computed(() => {
  const severities: Record<string, string> = {
    character: 'success',
    location: 'danger',
    object: 'warning',
    organization: 'info',
    event: 'secondary',
    concept: 'contrast',
  }
  return severities[props.character.type] || 'secondary'
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
    'main': 'success',
    'secondary': 'warning',
    'minor': 'secondary'
  }
  return severities[importance] || 'secondary'
}

const getImportanceLabel = (importance: string): string => {
  const labels: Record<string, string> = {
    'main': 'Principal',
    'secondary': 'Secundario',
    'minor': 'Menor'
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
  background: var(--p-surface-0, white);
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
  flex-wrap: wrap;
}

.merged-tag {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.merged-tag i {
  font-size: 0.75rem;
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
