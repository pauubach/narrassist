<template>
  <div class="chapter-tree">
    <!-- Header -->
    <div class="tree-header">
      <h3>Estructura</h3>
      <Button
        v-tooltip.bottom="'Recargar'"
        icon="pi pi-refresh"
        text
        rounded
        size="small"
        @click="$emit('refresh')"
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
      >
        <div class="chapter-header" @click="selectChapter(chapter.id)">
          <div class="chapter-info">
            <i class="pi pi-book chapter-icon"></i>
            <span class="chapter-title">{{ chapter.chapterNumber }}. {{ chapter.title }}</span>
          </div>
          <div class="chapter-meta">
            <span v-tooltip.left="'Palabras'" class="chapter-words">
              {{ chapter.wordCount.toLocaleString() }}
            </span>
          </div>
        </div>

        <!-- Secciones del capítulo (H2, H3, H4) -->
        <div v-if="chapter.sections && chapter.sections.length > 0" class="sections-list">
          <div
            v-for="(section, sIdx) in chapter.sections"
            :key="`section-${section.id}`"
            class="section-tree"
          >
            <div
              class="section-item"
              :class="[`level-${section.headingLevel}`, { 'section-active': activeSectionId === section.id }]"
              @click.stop="selectSection(chapter.id, section.id, section.startChar)"
            >
              <i class="pi pi-list section-icon"></i>
              <span class="section-title">{{ chapter.chapterNumber }}.{{ sIdx + 1 }}. {{ section.title || `Sección ${section.sectionNumber}` }}</span>
            </div>

            <!-- Subsecciones recursivas -->
            <template v-if="section.subsections && section.subsections.length > 0">
              <div
                v-for="(sub, subIdx) in section.subsections"
                :key="`sub-${sub.id}`"
                class="section-item"
                :class="[`level-${sub.headingLevel}`, { 'section-active': activeSectionId === sub.id }]"
                @click.stop="selectSection(chapter.id, sub.id, sub.startChar)"
              >
                <i class="pi pi-minus section-icon"></i>
                <span class="section-title">{{ chapter.chapterNumber }}.{{ sIdx + 1 }}.{{ subIdx + 1 }}. {{ sub.title || `Subsección ${sub.sectionNumber}` }}</span>
              </div>

              <!-- Nivel 4 (si existe) -->
              <template v-for="(sub, subIdx2) in section.subsections">
                <div
                  v-for="(sub4, sub4Idx) in sub.subsections || []"
                  :key="`sub4-${sub.id}-${sub4.id}`"
                  class="section-item"
                  :class="[`level-${sub4.headingLevel}`, { 'section-active': activeSectionId === sub4.id }]"
                  @click.stop="selectSection(chapter.id, sub4.id, sub4.startChar)"
                >
                  <i class="pi pi-circle-fill section-icon tiny"></i>
                  <span class="section-title">{{ chapter.chapterNumber }}.{{ sIdx + 1 }}.{{ subIdx2 + 1 }}.{{ sub4Idx + 1 }}. {{ sub4.title || `Subsección ${sub4.sectionNumber}` }}</span>
                </div>
              </template>
            </template>
          </div>
        </div>

        <!-- Stats del capítulo -->
        <div class="chapter-stats">
          <div
            v-if="chapter.entitiesCount"
            v-tooltip.bottom="'Entidades mencionadas'"
            class="stat-item"
          >
            <i class="pi pi-users"></i>
            <span>{{ chapter.entitiesCount }}</span>
          </div>
          <div
            v-if="chapter.alertsCount"
            v-tooltip.bottom="'Alertas detectadas'"
            class="stat-item stat-alerts"
          >
            <i class="pi pi-exclamation-triangle"></i>
            <span>{{ chapter.alertsCount }}</span>
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
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import type { Chapter } from '@/types'

// Extendemos Chapter para incluir stats opcionales
interface ChapterWithStats extends Chapter {
  entitiesCount?: number
  alertsCount?: number
}

defineProps<{
  chapters: ChapterWithStats[]
  loading?: boolean
  activeChapterId?: number | null
}>()

const emit = defineEmits<{
  chapterSelect: [chapterId: number]
  sectionSelect: [chapterId: number, sectionId: number, startChar: number]
  refresh: []
}>()

// Estado local para sección activa
const activeSectionId = ref<number | null>(null)

// Funciones
const selectChapter = (chapterId: number) => {
  activeSectionId.value = null
  emit('chapterSelect', chapterId)
}

const selectSection = (chapterId: number, sectionId: number, startChar: number) => {
  activeSectionId.value = sectionId
  emit('sectionSelect', chapterId, sectionId, startChar)
}
</script>

<style scoped>
.chapter-tree {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--p-surface-0, white);
  border-radius: var(--app-radius);
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
  border-radius: var(--app-radius);
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

/* Secciones */
.sections-list {
  margin-top: 0.5rem;
  padding-left: 1rem;
  border-left: 2px solid var(--surface-200);
}

.section-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.5rem;
  margin: 0.15rem 0;
  border-radius: var(--app-radius);
  cursor: pointer;
  transition: all 0.15s;
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

.section-item:hover {
  background: var(--surface-100);
  color: var(--text-color);
}

.section-item.section-active {
  background: var(--primary-50);
  color: var(--primary-color);
}

.section-icon {
  font-size: 0.65rem;
  color: var(--surface-400);
  flex-shrink: 0;
}

.section-icon.tiny {
  font-size: 0.4rem;
}

.section-item.section-active .section-icon {
  color: var(--primary-color);
}

.section-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Indentación por nivel */
.section-item.level-2 {
  padding-left: 0.5rem;
}

.section-item.level-3 {
  padding-left: 1rem;
}

.section-item.level-4 {
  padding-left: 1.5rem;
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

/* Scrollbar styling */
.tree-content::-webkit-scrollbar {
  width: 6px;
}

.tree-content::-webkit-scrollbar-track {
  background: var(--surface-50);
}

.tree-content::-webkit-scrollbar-thumb {
  background: var(--surface-300);
  border-radius: var(--app-radius-sm);
}

.tree-content::-webkit-scrollbar-thumb:hover {
  background: var(--surface-400);
}
</style>
