/**
 * Collections Store - Cross-Book / Sagas (BK-07)
 *
 * Gestiona el estado de colecciones, entity links y análisis cross-book.
 * Los endpoints NO usan ApiResponse wrapper → usar getRaw/postRaw/putRaw/del.
 */

import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type {
  Collection, CollectionDetail, EntityLink, LinkSuggestion,
  CrossBookReport, CrossBookEventReport,
} from '@/types'
import type {
  ApiCollection, ApiCollectionDetail, ApiEntityLink,
  ApiLinkSuggestion, ApiCrossBookReport, ApiCrossBookEventReport,
} from '@/types/api'
import {
  transformCollection, transformCollections, transformCollectionDetail,
  transformEntityLinks, transformLinkSuggestions, transformCrossBookReport,
  transformCrossBookEventReport,
} from '@/types/transformers'
import { api } from '@/services/apiClient'
import { ensureBackendReady } from '@/composables/useBackendReady'

export const useCollectionsStore = defineStore('collections', () => {
  const collections = ref<Collection[]>([])
  const currentCollection = ref<CollectionDetail | null>(null)
  const entityLinks = ref<EntityLink[]>([])
  const linkSuggestions = ref<LinkSuggestion[]>([])
  const crossBookReport = ref<CrossBookReport | null>(null)
  const crossBookEventReport = ref<CrossBookEventReport | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const collectionCount = computed(() => collections.value.length)
  const hasCollections = computed(() => collectionCount.value > 0)

  // ==================== Collection CRUD ====================

  async function fetchCollections() {
    loading.value = true
    error.value = null
    try {
      await ensureBackendReady()
      const data = await api.getRaw<ApiCollection[]>('/api/collections')
      collections.value = transformCollections(data)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Error al cargar colecciones'
      console.error('Failed to fetch collections:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchCollection(id: number) {
    loading.value = true
    error.value = null
    try {
      await ensureBackendReady()
      const data = await api.getRaw<ApiCollectionDetail>(`/api/collections/${id}`)
      currentCollection.value = transformCollectionDetail(data)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Error al cargar colección'
      console.error('Failed to fetch collection:', err)
    } finally {
      loading.value = false
    }
  }

  async function createCollection(name: string, description: string = '') {
    try {
      const data = await api.postRaw<{ id: number; name: string }>(
        '/api/collections',
        { name, description },
      )
      await fetchCollections()
      return data
    } catch (err) {
      console.error('Failed to create collection:', err)
      throw err
    }
  }

  async function updateCollection(id: number, updates: { name?: string; description?: string }) {
    try {
      await api.putRaw('/api/collections/' + id, updates as Record<string, unknown>)
      await fetchCollection(id)
    } catch (err) {
      console.error('Failed to update collection:', err)
      throw err
    }
  }

  async function deleteCollection(id: number) {
    try {
      await api.del('/api/collections/' + id)
      collections.value = collections.value.filter(c => c.id !== id)
      if (currentCollection.value?.id === id) {
        currentCollection.value = null
      }
    } catch (err) {
      console.error('Failed to delete collection:', err)
      throw err
    }
  }

  // ==================== Project membership ====================

  async function addProject(collectionId: number, projectId: number, order: number = 0) {
    try {
      await api.postRaw(`/api/collections/${collectionId}/projects/${projectId}?order=${order}`)
      await fetchCollection(collectionId)
    } catch (err) {
      console.error('Failed to add project to collection:', err)
      throw err
    }
  }

  async function removeProject(collectionId: number, projectId: number) {
    try {
      await api.del(`/api/collections/${collectionId}/projects/${projectId}`)
      await fetchCollection(collectionId)
    } catch (err) {
      console.error('Failed to remove project from collection:', err)
      throw err
    }
  }

  // ==================== Entity links ====================

  async function fetchEntityLinks(collectionId: number) {
    try {
      const data = await api.getRaw<ApiEntityLink[]>(
        `/api/collections/${collectionId}/entity-links`,
      )
      entityLinks.value = transformEntityLinks(data)
    } catch (err) {
      console.error('Failed to fetch entity links:', err)
      entityLinks.value = []
    }
  }

  async function fetchLinkSuggestions(collectionId: number, threshold: number = 0.7) {
    try {
      const data = await api.getRaw<ApiLinkSuggestion[]>(
        `/api/collections/${collectionId}/entity-link-suggestions?threshold=${threshold}`,
      )
      linkSuggestions.value = transformLinkSuggestions(data)
    } catch (err) {
      console.error('Failed to fetch link suggestions:', err)
      linkSuggestions.value = []
    }
  }

  async function createEntityLink(
    collectionId: number,
    data: {
      source_entity_id: number
      target_entity_id: number
      source_project_id: number
      target_project_id: number
      similarity: number
      match_type: string
    },
  ) {
    try {
      await api.postRaw(
        `/api/collections/${collectionId}/entity-links`,
        data as Record<string, unknown>,
      )
      await fetchEntityLinks(collectionId)
    } catch (err) {
      console.error('Failed to create entity link:', err)
      throw err
    }
  }

  async function deleteEntityLink(collectionId: number, linkId: number) {
    try {
      await api.del(`/api/collections/${collectionId}/entity-links/${linkId}`)
      entityLinks.value = entityLinks.value.filter(l => l.id !== linkId)
    } catch (err) {
      console.error('Failed to delete entity link:', err)
      throw err
    }
  }

  // ==================== Cross-book analysis ====================

  async function fetchCrossBookAnalysis(collectionId: number) {
    loading.value = true
    try {
      const data = await api.getRaw<ApiCrossBookReport>(
        `/api/collections/${collectionId}/cross-book-analysis`,
        { timeout: 120000 },
      )
      crossBookReport.value = transformCrossBookReport(data)
    } catch (err) {
      console.error('Failed to fetch cross-book analysis:', err)
      crossBookReport.value = null
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchCrossBookEventAnalysis(collectionId: number, validateLlm: boolean = false) {
    loading.value = true
    try {
      const url = `/api/collections/${collectionId}/cross-book-events?validate_llm=${validateLlm}`
      const data = await api.getRaw<ApiCrossBookEventReport>(url, { timeout: 120000 })
      crossBookEventReport.value = transformCrossBookEventReport(data)
    } catch (err) {
      console.error('Failed to fetch cross-book event analysis:', err)
      crossBookEventReport.value = null
      throw err
    } finally {
      loading.value = false
    }
  }

  function clearCurrentCollection() {
    currentCollection.value = null
    entityLinks.value = []
    linkSuggestions.value = []
    crossBookReport.value = null
    crossBookEventReport.value = null
  }

  return {
    // State
    collections,
    currentCollection,
    entityLinks,
    linkSuggestions,
    crossBookReport,
    crossBookEventReport,
    loading,
    error,

    // Computeds
    collectionCount,
    hasCollections,

    // Collection CRUD
    fetchCollections,
    fetchCollection,
    createCollection,
    updateCollection,
    deleteCollection,

    // Project membership
    addProject,
    removeProject,

    // Entity links
    fetchEntityLinks,
    fetchLinkSuggestions,
    createEntityLink,
    deleteEntityLink,

    // Cross-book analysis
    fetchCrossBookAnalysis,
    fetchCrossBookEventAnalysis,

    // Utils
    clearCurrentCollection,
  }
})
