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

  const entitiesCount = computed(() => entities.value.length)
  const alertsCount = computed(() => alerts.value.length)

  async function loadEntities(projectId: number) {
    try {
      const data = await api.getRaw<{ success: boolean; data?: any[] }>(`/api/projects/${projectId}/entities`)
      if (data.success) {
        entities.value = transformEntities(data.data || [])
      }
    } catch (err) {
      console.error('Error loading entities:', err)
    }
  }

  async function loadAlerts(projectId: number) {
    try {
      const data = await api.getRaw<{ success: boolean; data?: any[] }>(`/api/projects/${projectId}/alerts?status=open`)
      if (data.success) {
        alerts.value = transformAlerts(data.data || [])
      }
    } catch (err) {
      console.error('Error loading alerts:', err)
    }
  }

  async function loadChapters(projectId: number, fallbackProject?: { wordCount: number; chapterCount: number }) {
    try {
      const data = await api.getRaw<{ success: boolean; data?: any[] }>(`/api/projects/${projectId}/chapters`)
      if (data.success) {
        chapters.value = transformChapters(data.data || [])
      }
    } catch (err) {
      console.error('Error loading chapters:', err)
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
    }
  }

  async function loadRelationships(projectId: number) {
    try {
      const data = await api.getRaw<{ success: boolean; data?: any[] }>(`/api/projects/${projectId}/relationships`)
      if (data.success) {
        relationships.value = data.data
      }
    } catch (err) {
      console.error('Error loading relationships:', err)
    }
  }

  return {
    entities,
    alerts,
    chapters,
    relationships,
    entitiesCount,
    alertsCount,
    loadEntities,
    loadAlerts,
    loadChapters,
    loadRelationships,
  }
}
