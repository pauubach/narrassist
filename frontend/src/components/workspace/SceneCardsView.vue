<script setup lang="ts">
/**
 * SceneCardsView - Vista de tarjetas visuales de escenas (estilo storyboard)
 *
 * Muestra las escenas como tarjetas en una cuadricula organizada por capitulo.
 * Cada tarjeta muestra tipo, tono, extracto, participantes y metadatos.
 * Inspirado en yWriter y Scrivener's corkboard.
 */

import { computed } from 'vue'

interface SceneData {
  id: number
  chapter_id: number
  chapter_number: number
  chapter_title: string
  scene_number: number
  word_count: number
  separator_type: string
  excerpt: string
  tags: {
    scene_type?: string
    tone?: string
    location_entity_id?: number
    location_name?: string
    participant_ids?: number[]
    participant_names?: string[]
    summary?: string
    notes?: string
  } | null
  custom_tags: Array<{ name: string; color?: string }>
}

const props = defineProps<{
  scenes: SceneData[]
  projectId: number
}>()

const emit = defineEmits<{
  (e: 'tag-scene', sceneId: number): void
  (e: 'select-scene', sceneId: number): void
}>()

// Group scenes by chapter
const chaptersWithScenes = computed(() => {
  const chapters: Map<number, { number: number; title: string; scenes: SceneData[] }> = new Map()
  for (const scene of props.scenes) {
    if (!chapters.has(scene.chapter_id)) {
      chapters.set(scene.chapter_id, {
        number: scene.chapter_number,
        title: scene.chapter_title || `Cap. ${scene.chapter_number}`,
        scenes: [],
      })
    }
    chapters.get(scene.chapter_id)!.scenes.push(scene)
  }
  // Sort by chapter number
  return Array.from(chapters.values()).sort((a, b) => a.number - b.number)
})

// Color mappings for scene types
const typeColors: Record<string, string> = {
  action: '#e74c3c',
  dialogue: '#3498db',
  exposition: '#2ecc71',
  introspection: '#9b59b6',
  flashback: '#e67e22',
  dream: '#1abc9c',
  transition: '#95a5a6',
  mixed: '#f39c12',
}

const typeLabels: Record<string, string> = {
  action: 'Accion',
  dialogue: 'Dialogo',
  exposition: 'Exposicion',
  introspection: 'Introspeccion',
  flashback: 'Flashback',
  dream: 'Sueno',
  transition: 'Transicion',
  mixed: 'Mixta',
}

const toneLabels: Record<string, string> = {
  tense: 'Tensa',
  calm: 'Calma',
  happy: 'Alegre',
  sad: 'Triste',
  romantic: 'Romantica',
  mysterious: 'Misteriosa',
  ominous: 'Ominosa',
  hopeful: 'Esperanzadora',
  nostalgic: 'Nostalgica',
  neutral: 'Neutral',
}

function getTypeColor(type?: string): string {
  return type ? typeColors[type] || '#95a5a6' : '#ddd'
}

function getTypeLabel(type?: string): string {
  return type ? typeLabels[type] || type : 'Sin tipo'
}

function getToneLabel(tone?: string): string {
  return tone ? toneLabels[tone] || tone : ''
}

function isTagged(scene: SceneData): boolean {
  return scene.tags !== null && (
    !!scene.tags.scene_type ||
    !!scene.tags.tone ||
    !!scene.tags.summary
  )
}
</script>

<template>
  <div class="scene-cards">
    <div
      v-for="chapter in chaptersWithScenes"
      :key="chapter.number"
      class="chapter-group"
    >
      <div class="chapter-header">
        <span class="chapter-number">{{ chapter.number }}</span>
        <span class="chapter-title">{{ chapter.title }}</span>
        <span class="chapter-scene-count">{{ chapter.scenes.length }} escenas</span>
      </div>

      <div class="cards-grid">
        <div
          v-for="scene in chapter.scenes"
          :key="scene.id"
          class="scene-card"
          :class="{
            'scene-card--tagged': isTagged(scene),
            'scene-card--untagged': !isTagged(scene)
          }"
          @click="emit('select-scene', scene.id)"
        >
          <!-- Card header with type color stripe -->
          <div
            class="card-stripe"
            :style="{ backgroundColor: getTypeColor(scene.tags?.scene_type) }"
          />

          <div class="card-body">
            <!-- Scene label -->
            <div class="card-header">
              <span class="scene-label">E{{ scene.scene_number }}</span>
              <span class="word-count">{{ scene.word_count }} pal.</span>
            </div>

            <!-- Type and tone chips -->
            <div v-if="scene.tags" class="card-chips">
              <span
                v-if="scene.tags.scene_type"
                class="chip chip--type"
                :style="{ backgroundColor: getTypeColor(scene.tags.scene_type), color: 'white' }"
              >
                {{ getTypeLabel(scene.tags.scene_type) }}
              </span>
              <span v-if="scene.tags.tone" class="chip chip--tone">
                {{ getToneLabel(scene.tags.tone) }}
              </span>
            </div>

            <!-- Summary or excerpt -->
            <p class="card-text">
              {{ scene.tags?.summary || scene.excerpt || '(sin contenido)' }}
            </p>

            <!-- Participants -->
            <div v-if="scene.tags?.participant_names?.length" class="card-participants">
              <i class="pi pi-users" />
              <span>{{ scene.tags.participant_names.join(', ') }}</span>
            </div>

            <!-- Location -->
            <div v-if="scene.tags?.location_name" class="card-location">
              <i class="pi pi-map-marker" />
              <span>{{ scene.tags.location_name }}</span>
            </div>

            <!-- Custom tags -->
            <div v-if="scene.custom_tags.length" class="card-custom-tags">
              <span
                v-for="tag in scene.custom_tags"
                :key="tag.name"
                class="custom-tag"
                :style="tag.color ? { backgroundColor: tag.color, color: 'white' } : {}"
              >
                {{ tag.name }}
              </span>
            </div>

            <!-- Notes indicator -->
            <div v-if="scene.tags?.notes" class="card-notes-indicator" :title="scene.tags.notes">
              <i class="pi pi-comment" />
            </div>
          </div>

          <!-- Tag button for untagged scenes -->
          <button
            v-if="!isTagged(scene)"
            class="card-tag-btn"
            title="Etiquetar escena"
            @click.stop="emit('tag-scene', scene.id)"
          >
            <i class="pi pi-tag" />
          </button>
        </div>
      </div>
    </div>

    <div v-if="scenes.length === 0" class="empty-state">
      <i class="pi pi-images" />
      <p>No hay escenas detectadas en este proyecto.</p>
      <p class="empty-hint">Las escenas se detectan automaticamente al analizar el documento.</p>
    </div>
  </div>
</template>

<style scoped>
.scene-cards {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-6, 1.5rem);
}

/* Chapter group */
.chapter-group {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-3, 0.75rem);
}

.chapter-header {
  display: flex;
  align-items: center;
  gap: var(--ds-space-2, 0.5rem);
  padding-bottom: var(--ds-space-2, 0.5rem);
  border-bottom: 2px solid var(--ds-surface-border, var(--surface-border));
}

.chapter-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background-color: var(--ds-color-primary, var(--primary-color));
  color: white;
  font-size: 0.75rem;
  font-weight: 700;
  flex-shrink: 0;
}

.chapter-title {
  font-size: var(--ds-font-size-base, 0.875rem);
  font-weight: 600;
  color: var(--ds-color-text, var(--text-color));
}

.chapter-scene-count {
  margin-left: auto;
  font-size: var(--ds-font-size-xs, 0.75rem);
  color: var(--ds-color-text-tertiary, var(--text-color-secondary));
}

/* Cards grid */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--ds-space-3, 0.75rem);
}

/* Scene card */
.scene-card {
  position: relative;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--ds-surface-border, var(--surface-border));
  border-radius: var(--ds-radius-md, 8px);
  background-color: var(--ds-surface-card, var(--surface-card));
  overflow: hidden;
  cursor: pointer;
  transition: box-shadow 0.15s ease, transform 0.15s ease;
  min-height: 140px;
}

.scene-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-1px);
}

.scene-card--untagged {
  opacity: 0.75;
  border-style: dashed;
}

.scene-card--untagged:hover {
  opacity: 1;
}

/* Color stripe at top */
.card-stripe {
  height: 4px;
  width: 100%;
  flex-shrink: 0;
}

/* Card body */
.card-body {
  display: flex;
  flex-direction: column;
  gap: var(--ds-space-2, 0.5rem);
  padding: var(--ds-space-3, 0.75rem);
  flex: 1;
}

/* Header row */
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.scene-label {
  font-size: var(--ds-font-size-sm, 0.8125rem);
  font-weight: 700;
  color: var(--ds-color-text, var(--text-color));
}

.word-count {
  font-size: var(--ds-font-size-xs, 0.75rem);
  color: var(--ds-color-text-tertiary, var(--text-color-secondary));
}

/* Chips */
.card-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.chip {
  display: inline-flex;
  align-items: center;
  padding: 1px 8px;
  border-radius: var(--app-radius-lg);
  font-size: 0.6875rem;
  font-weight: 600;
  line-height: 1.6;
}

.chip--tone {
  background-color: var(--ds-surface-ground, var(--surface-ground));
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
  border: 1px solid var(--ds-surface-border, var(--surface-border));
}

/* Text excerpt */
.card-text {
  font-size: var(--ds-font-size-xs, 0.75rem);
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin: 0;
}

/* Participants */
.card-participants,
.card-location {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.6875rem;
  color: var(--ds-color-text-tertiary, var(--text-color-secondary));
}

.card-participants i,
.card-location i {
  font-size: 0.625rem;
}

/* Custom tags */
.card-custom-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
  margin-top: auto;
}

.custom-tag {
  display: inline-flex;
  align-items: center;
  padding: 0 6px;
  border-radius: var(--app-radius);
  font-size: 0.625rem;
  font-weight: 600;
  line-height: 1.8;
  background-color: var(--ds-surface-ground, var(--surface-ground));
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
}

/* Notes indicator */
.card-notes-indicator {
  position: absolute;
  top: var(--ds-space-2, 0.5rem);
  right: var(--ds-space-2, 0.5rem);
  color: var(--ds-color-text-tertiary, var(--text-color-secondary));
  font-size: 0.75rem;
}

/* Tag button for untagged cards */
.card-tag-btn {
  position: absolute;
  bottom: var(--ds-space-2, 0.5rem);
  right: var(--ds-space-2, 0.5rem);
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 50%;
  background-color: var(--ds-color-primary, var(--primary-color));
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.scene-card:hover .card-tag-btn {
  opacity: 1;
}

/* Empty state */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--ds-space-2, 0.5rem);
  padding: var(--ds-space-8, 2rem);
  color: var(--ds-color-text-secondary, var(--text-color-secondary));
  text-align: center;
}

.empty-state i {
  font-size: 2.5rem;
  opacity: 0.4;
}

.empty-state p {
  margin: 0;
}

.empty-hint {
  font-size: var(--ds-font-size-xs, 0.75rem);
  opacity: 0.7;
}

/* Responsive */
@media (max-width: 640px) {
  .cards-grid {
    grid-template-columns: 1fr;
  }
}
</style>
