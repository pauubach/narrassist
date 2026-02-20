/**
 * Composable: project data loading (entities, alerts, chapters, relationships).
 *
 * Extracted from ProjectDetailView — provides reactive refs and async loaders
 * for the four main data collections of a project.
 */

import { ref, computed } from 'vue'
import { api } from '@/services/apiClient'
import { transformEntities, transformAlerts, transformChapters } from '@/types/transformers'
import type { Entity, Alert, Chapter } from '@/types'

export function useProjectData() {
  const entities = ref<Entity[]>([])
  const alerts = ref<Alert[]>([])
  const chapters = ref<Chapter[]>([])
  const relationships = ref<any>(null)

  // Estados de carga y cache
  const loadingChapters = ref(false)
  const chaptersLoaded = ref(false)
  const loadingEntities = ref(false)
  const entitiesLoaded = ref(false)
  const loadingAlerts = ref(false)
  const alertsLoaded = ref(false)
  const loadingRelationships = ref(false)
  const relationshipsLoaded = ref(false)
  const lastLoadedProjectId = ref<number | null>(null)

  const entitiesCount = computed(() => entities.value.length)
  const alertsCount = computed(() => alerts.value.length)

  async function loadEntities(projectId: number, forceReload = false) {
    // Cache: si ya están cargadas para este proyecto, no recargar
    if (!forceReload && entitiesLoaded.value && lastLoadedProjectId.value === projectId && entities.value.length > 0) {
      console.log('[useProjectData] Entities already loaded from cache')
      return
    }

    // Si ya está cargando, esperar
    if (loadingEntities.value) {
      console.log('[useProjectData] Entities already loading, waiting...')
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
        console.log('[useProjectData] Entities loaded successfully:', entities.value.length)
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
      console.log('[useProjectData] Alerts already loading, waiting...')
      while (loadingAlerts.value) {
        await new Promise(resolve => setTimeout(resolve, 50))
      }
      return
    }

    loadingAlerts.value = true
    try {
      const data = await api.getRaw<{ success: boolean; data?: any[] }>(`/api/projects/${projectId}/alerts?status=open`)
      if (data.success) {
        alerts.value = transformAlerts(data.data || [])
        alertsLoaded.value = true
        lastLoadedProjectId.value = projectId
        console.log('[useProjectData] Alerts loaded successfully:', alerts.value.length)
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
      console.log('[useProjectData] Chapters already loaded from cache')
      return
    }

    // Si ya está cargando, esperar
    if (loadingChapters.value) {
      console.log('[useProjectData] Chapters already loading, waiting...')
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
        console.log('[useProjectData] Chapters loaded successfully:', chapters.value.length)
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
      console.log('[useProjectData] Relationships already loaded from cache')
      return
    }

    // Si ya está cargando, esperar
    if (loadingRelationships.value) {
      console.log('[useProjectData] Relationships already loading, waiting...')
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
        console.log('[useProjectData] Relationships loaded successfully')
      }
    } catch (err) {
      console.error('Error loading relationships:', err)
      relationshipsLoaded.value = false
    } finally {
      loadingRelationships.value = false
    }
  }

  return {
    entities,
    alerts,
    chapters,
    relationships,
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
    loadEntities,
    loadAlerts,
    loadChapters,
    loadRelationships,
  }
}
