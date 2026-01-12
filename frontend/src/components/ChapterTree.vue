<template>
  <div class="chapter-tree">
    <!-- Header -->
    <div class="tree-header">
      <h3>Estructura</h3>
      <Button
        icon="pi pi-refresh"
        text
        rounded
        size="small"
        @click="$emit('refresh')"
        v-tooltip.bottom="'Recargar'"
      />
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="tree-loading">
      <ProgressSpinner style="width: 30px; height: 30px" />
      <small>Cargando estructura...</small>
    </div>

    <!-- Tree content -->
    <div v-else-if="chapters.length > 0" class="tree-content">
      <div
        v-for="chapter in chapters"
        :key="chapter.id"
        class="chapter-item"
        :class="{ 'chapter-active': activeChapterId === chapter.id }"
        @click="selectChapter(chapter.id)"
      >
        <div class="chapter-header">
          <div class="chapter-info">
            <i class="pi pi-book chapter-icon"></i>
            <span class="chapter-title">{{ chapter.title }}</span>
          </div>
          <div class="chapter-meta">
            <span class="chapter-words" v-tooltip.left="'Palabras'">
              {{ chapter.word_count.toLocaleString() }}
            </span>
          </div>
        </div>

        <!-- Stats del capítulo -->
        <div class="chapter-stats">
          <div
            v-if="chapter.entities_count"
            class="stat-item"
            v-tooltip.bottom="'Entidades mencionadas'"
          >
            <i class="pi pi-users"></i>
            <span>{{ chapter.entities_count }}</span>
          </div>
          <div
            v-if="chapter.alerts_count"
            class="stat-item stat-alerts"
            v-tooltip.bottom="'Alertas detectadas'"
          >
            <i class="pi pi-exclamation-triangle"></i>
            <span>{{ chapter.alerts_count }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="tree-empty">
      <i class="pi pi-book"></i>
      <p>No hay capítulos</p>
      <small>El análisis aún no ha detectado la estructura del documento</small>
    </div>

    <!-- Footer con resumen -->
    <div v-if="chapters.length > 0" class="tree-footer">
      <div class="footer-stat">
        <i class="pi pi-book"></i>
        <span>{{ chapters.length }} capítulos</span>
      </div>
      <div class="footer-stat">
        <i class="pi pi-file"></i>
        <span>{{ totalWords.toLocaleString() }} palabras</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'

interface Chapter {
  id: number
  project_id: number
  title: string
  chapter_number: number
  word_count: number
  position_start: number
  position_end: number
  entities_count?: number
  alerts_count?: number
}

const props = defineProps<{
  chapters: Chapter[]
  loading?: boolean
  activeChapterId?: number | null
}>()

const emit = defineEmits<{
  chapterSelect: [chapterId: number]
  refresh: []
}>()

// Computed
const totalWords = computed(() => {
  return props.chapters.reduce((sum, ch) => sum + ch.word_count, 0)
})

// Funciones
const selectChapter = (chapterId: number) => {
  emit('chapterSelect', chapterId)
}
</script>

<style scoped>
.chapter-tree {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.tree-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--surface-50);
  border-bottom: 1px solid var(--surface-200);
}

.tree-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-color);
}

.tree-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 0.75rem;
  color: var(--text-color-secondary);
}

.tree-content {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
}

.chapter-item {
  padding: 0.75rem;
  margin-bottom: 0.5rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.chapter-item:hover {
  background: var(--surface-50);
  border-color: var(--surface-200);
}

.chapter-item.chapter-active {
  background: var(--primary-50);
  border-color: var(--primary-200);
}

.chapter-item.chapter-active .chapter-title {
  color: var(--primary-color);
  font-weight: 600;
}

.chapter-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.chapter-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  min-width: 0;
}

.chapter-icon {
  color: var(--primary-color);
  font-size: 0.875rem;
  flex-shrink: 0;
}

.chapter-title {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-color);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.3;
}

.chapter-meta {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.chapter-words {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  white-space: nowrap;
}

.chapter-stats {
  display: flex;
  gap: 0.75rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--surface-100);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.stat-item i {
  font-size: 0.75rem;
}

.stat-alerts {
  color: var(--orange-500);
}

.tree-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 0.75rem;
  padding: 2rem 1rem;
  color: var(--text-color-secondary);
  text-align: center;
}

.tree-empty i {
  font-size: 2.5rem;
  opacity: 0.5;
}

.tree-empty p {
  margin: 0;
  font-weight: 500;
}

.tree-empty small {
  font-size: 0.75rem;
  line-height: 1.4;
}

.tree-footer {
  padding: 0.75rem 1rem;
  background: var(--surface-50);
  border-top: 1px solid var(--surface-200);
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.footer-stat {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.footer-stat i {
  font-size: 0.875rem;
  color: var(--primary-color);
}

/* Scrollbar styling */
.tree-content::-webkit-scrollbar {
  width: 6px;
}

.tree-content::-webkit-scrollbar-track {
  background: var(--surface-50);
}

.tree-content::-webkit-scrollbar-thumb {
  background: var(--surface-300);
  border-radius: 3px;
}

.tree-content::-webkit-scrollbar-thumb:hover {
  background: var(--surface-400);
}
</style>
