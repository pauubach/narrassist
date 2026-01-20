<script setup lang="ts">
import ChapterTree from '@/components/ChapterTree.vue'
import type { Chapter } from '@/types'

/**
 * ChaptersPanel - Panel de capítulos para el sidebar.
 *
 * Wrapper del ChapterTree con header consistente.
 */

defineProps<{
  /** Lista de capítulos */
  chapters: Chapter[]
  /** Si está cargando */
  loading?: boolean
  /** ID del capítulo activo (visible en el documento) */
  activeChapterId?: number | null
}>()

const emit = defineEmits<{
  /** Cuando se selecciona un capítulo (emite el ID) */
  (e: 'chapterSelect', chapterId: number): void
  /** Cuando se selecciona una sección (emite chapterId, sectionId, startChar) */
  (e: 'sectionSelect', chapterId: number, sectionId: number, startChar: number): void
  /** Cuando se solicita refrescar */
  (e: 'refresh'): void
}>()
</script>

<template>
  <div class="chapters-panel">
    <ChapterTree
      :chapters="chapters"
      :loading="loading"
      :active-chapter-id="activeChapterId"
      @chapter-select="emit('chapterSelect', $event)"
      @section-select="(chapterId, sectionId, startChar) => emit('sectionSelect', chapterId, sectionId, startChar)"
      @refresh="emit('refresh')"
    />
  </div>
</template>

<style scoped>
.chapters-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}
</style>
