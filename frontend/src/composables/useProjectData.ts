/**
 * Composable: project data loading (entities, alerts, chapters, relationships, summaries).
 *
 * Extracted from ProjectDetailView — provides reactive refs and async loaders
 * for the main data collections of a project.
 */

import { ref, computed } from 'vue'
import { api } from '@/services/apiClient'
import { transformEntities, transformAlerts, transformChapters } from '@/types/transformers'
import type { Entity, Alert, Chapter } from '@/types'

/** Summary data per chapter — matches backend ChapterSummary.to_dict() */
export interface ChapterSummaryData {
  chapter_number: number
  chapter_title: string | null
  word_count: number
  characters_present: Array<{
    entity_id: number
    name: string
    mention_count: number
    is_first_appearance: boolean
    is_return: boolean
    chapters_absent: number
  }>
  new_characters: string[]
  returning_characters: string[]
  key_events: Array<{ event_type: string; description: string; characters_involved: string[] }>
  llm_events: Array<{ event_type: string; description: string; characters_involved: string[] }>
  total_interactions: number
  conflict_interactions: number
  positive_interactions: number
  dominant_tone: string
  locations_mentioned: string[]
  auto_summary: string
  llm_summary: string | null
}

export function useProjectData() {
  const entities = ref<Entity[]>([])
  const alerts = ref<Alert[]>([])
  const chapters = ref<Chapter[]>([])
  const relationships = ref<any>(null)
  const chapterSummaries = ref<Map<number, ChapterSummaryData>>(new Map())
  const globalSummary = ref<string | null>(null)

  // Estados de carga y cache
  const loadingChapters = ref(false)
  const chaptersLoaded = ref(false)
  const loadingEntities = ref(false)
  const entitiesLoaded = ref(false)
  const loadingAlerts = ref(false)
  const alertsLoaded = ref(false)
  const loadingRelationships = ref(false)
  const relationshipsLoaded = ref(false)
  const summariesLoaded = ref(false)
  const loadingSummaries = ref(false)
  const lastLoadedProjectId = ref<number | null>(null)

  const entitiesCount = computed(() => entities.value.length)
  const alertsCount = computed(() => alerts.value.length)

  async function loadEntities(projectId: number, forceReload = false) {
    // Cache: si ya están cargadas para este proyecto, no recargar
    if (!forceReload && entitiesLoaded.value && lastLoadedProjectId.value === projectId && entities.value.length > 0) {
      return
    }

    // Si ya está cargando, esperar
    if (loadingEntities.value) {
      while (loadingEntities.value) {
        await new Promise(resolve => setTimeout(resolve, 50))
      }
      return
    }

    loadingEntities.value = true
    try {
      const data = await api.getRaw<{ success: boolean; data?: any[] }>(`/api/projects/${projectId}/entities`)
      if (data.success) {
        entities.value = transformEntities(data.data || [])
        entitiesLoaded.value = true
        lastLoadedProjectId.value = projectId
      }
    } catch (err) {
      console.error('Error loading entities:', err)
      entitiesLoaded.value = false
    } finally {
      loadingEntities.value = false
    }
  }

  async function loadAlerts(projectId: number, forceReload = false) {
    // Alertas cambian con frecuencia (resolve/dismiss/config), evitar cache agresivo.
    if (forceReload) {
      alertsLoaded.value = false
    }

    // Si ya está cargando, esperar
    if (loadingAlerts.value) {
      while (loadingAlerts.value) {
        await new Promise(resolve => setTimeout(resolve, 50))
      }
      return
    }

    loadingAlerts.value = true
    try {
      // Cargar TODAS las alertas (activas + resueltas + descartadas) para mantener el progreso
      const data = await api.getRaw<{ success: boolean; data?: any[] }>(`/api/projects/${projectId}/alerts`)
      if (data.success) {
        alerts.value = transformAlerts(data.data || [])
        alertsLoaded.value = true
        lastLoadedProjectId.value = projectId
      }
    } catch (err) {
      console.error('Error loading alerts:', err)
      alertsLoaded.value = false
    } finally {
      loadingAlerts.value = false
    }
  }

  async function loadChapters(projectId: number, fallbackProject?: { wordCount: number; chapterCount: number }, forceReload = false) {
    // Cache: si ya están cargados para este proyecto, no recargar
    if (!forceReload && chaptersLoaded.value && lastLoadedProjectId.value === projectId && chapters.value.length > 0) {
      return
    }

    // Si ya está cargando, esperar
    if (loadingChapters.value) {
      // Esperar a que termine la carga actual
      while (loadingChapters.value) {
        await new Promise(resolve => setTimeout(resolve, 50))
      }
      return
    }

    loadingChapters.value = true
    try {
      const data = await api.getRaw<{ success: boolean; data?: any[] }>(`/api/projects/${projectId}/chapters`)
      if (data.success) {
        chapters.value = transformChapters(data.data || [])
        chaptersLoaded.value = true
        lastLoadedProjectId.value = projectId
      }
    } catch (err) {
      console.error('Error loading chapters:', err)
      chaptersLoaded.value = false
      if (fallbackProject && fallbackProject.chapterCount > 0) {
        chapters.value = Array.from({ length: fallbackProject.chapterCount }, (_, i) => ({
          id: i + 1,
          projectId,
          title: `Capítulo ${i + 1}`,
          content: '',
          chapterNumber: i + 1,
          wordCount: Math.floor(fallbackProject.wordCount / fallbackProject.chapterCount),
          positionStart: 0,
          positionEnd: 0,
        }))
      }
    } finally {
      loadingChapters.value = false
    }
  }

  async function loadRelationships(projectId: number, forceReload = false) {
    // Cache: si ya están cargadas para este proyecto, no recargar
    if (!forceReload && relationshipsLoaded.value && lastLoadedProjectId.value === projectId && relationships.value) {
      return
    }

    // Si ya está cargando, esperar
    if (loadingRelationships.value) {
      while (loadingRelationships.value) {
        await new Promise(resolve => setTimeout(resolve, 50))
      }
      return
    }

    loadingRelationships.value = true
    try {
      const data = await api.getRaw<{ success: boolean; data?: any[] }>(`/api/projects/${projectId}/relationships`)
      if (data.success) {
        relationships.value = data.data
        relationshipsLoaded.value = true
        lastLoadedProjectId.value = projectId
      }
    } catch (err) {
      console.error('Error loading relationships:', err)
      relationshipsLoaded.value = false
    } finally {
      loadingRelationships.value = false
    }
  }

  async function loadChapterSummaries(projectId: number, forceReload = false) {
    if (!forceReload && summariesLoaded.value && lastLoadedProjectId.value === projectId && chapterSummaries.value.size > 0) {
      return
    }
    if (loadingSummaries.value) {
      while (loadingSummaries.value) {
        await new Promise(resolve => setTimeout(resolve, 50))
      }
      return
    }

    loadingSummaries.value = true
    try {
      const data = await api.getRaw<{ success: boolean; data?: { chapters?: ChapterSummaryData[]; global_summary?: string } }>(
        `/api/projects/${projectId}/chapter-progress?mode=standard`,
        { timeout: 120000 }  // 2 min: chapter-progress puede hacer llamadas LLM
      )
      if (data.success && data.data) {
        if (data.data.chapters) {
          const map = new Map<number, ChapterSummaryData>()
          for (const ch of data.data.chapters) {
            map.set(ch.chapter_number, ch)
          }
          chapterSummaries.value = map
        }
        globalSummary.value = data.data.global_summary ?? null
        summariesLoaded.value = true
        lastLoadedProjectId.value = projectId
      }
    } catch (err) {
      console.error('Error loading chapter summaries:', err)
      summariesLoaded.value = false
    } finally {
      loadingSummaries.value = false
    }
  }

  return {
    entities,
    alerts,
    chapters,
    relationships,
    chapterSummaries,
    globalSummary,
    entitiesCount,
    alertsCount,
    loadingChapters,
    chaptersLoaded,
    loadingEntities,
    entitiesLoaded,
    loadingAlerts,
    alertsLoaded,
    loadingRelationships,
    relationshipsLoaded,
    summariesLoaded,
    loadEntities,
    loadAlerts,
    loadChapters,
    loadRelationships,
    loadChapterSummaries,
  }
}
