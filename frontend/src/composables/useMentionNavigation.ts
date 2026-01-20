/**
 * useMentionNavigation - Composable para navegar entre menciones de una entidad
 *
 * Permite cargar las menciones de una entidad y navegar entre ellas
 * con botones anterior/siguiente.
 */

import { ref, computed, watch } from 'vue'
import { useWorkspaceStore } from '@/stores/workspace'

export interface Mention {
  id: number
  entityId: number
  surfaceForm: string
  startChar: number
  endChar: number
  chapterId: number | null
  chapterNumber: number | null
  chapterTitle: string | null
  contextBefore: string | null
  contextAfter: string | null
  confidence: number
  source: string
}

export interface MentionNavigationState {
  entityId: number | null
  entityName: string | null
  entityType: string | null
  mentions: Mention[]
  currentIndex: number
  loading: boolean
  error: string | null
}

export function useMentionNavigation(projectId: () => number) {
  const workspaceStore = useWorkspaceStore()

  // Estado
  const state = ref<MentionNavigationState>({
    entityId: null,
    entityName: null,
    entityType: null,
    mentions: [],
    currentIndex: -1,
    loading: false,
    error: null,
  })

  // Computed
  const isActive = computed(() => state.value.entityId !== null && state.value.mentions.length > 0)
  const currentMention = computed(() => {
    if (state.value.currentIndex < 0 || state.value.currentIndex >= state.value.mentions.length) {
      return null
    }
    return state.value.mentions[state.value.currentIndex]
  })
  const totalMentions = computed(() => state.value.mentions.length)
  const canGoPrevious = computed(() => state.value.currentIndex > 0)
  const canGoNext = computed(() => state.value.currentIndex < state.value.mentions.length - 1)
  const navigationLabel = computed(() => {
    if (!isActive.value) return ''
    return `${state.value.currentIndex + 1} / ${state.value.mentions.length}`
  })

  /**
   * Carga las menciones de una entidad desde el backend
   */
  async function loadMentions(entityId: number): Promise<boolean> {
    state.value.loading = true
    state.value.error = null

    const pid = projectId()
    if (!pid) {
      state.value.error = 'ID de proyecto no disponible'
      state.value.loading = false
      return false
    }

    try {
      const response = await fetch(
        `/api/projects/${pid}/entities/${entityId}/mentions`
      )

      if (!response.ok) {
        throw new Error('Error cargando menciones')
      }

      const data = await response.json()

      if (!data.success) {
        throw new Error(data.error || 'Error desconocido')
      }

      state.value.entityId = entityId
      state.value.entityName = data.data.entityName
      state.value.entityType = data.data.entityType
      state.value.mentions = data.data.mentions || []
      state.value.currentIndex = state.value.mentions.length > 0 ? 0 : -1

      // Si hay menciones, navegar a la primera
      if (state.value.mentions.length > 0) {
        navigateToCurrentMention()
      }

      return true
    } catch (err) {
      state.value.error = err instanceof Error ? err.message : 'Error desconocido'
      console.error('Error loading mentions:', err)
      return false
    } finally {
      state.value.loading = false
    }
  }

  /**
   * Navega a la mención actual en el texto
   */
  function navigateToCurrentMention() {
    const mention = currentMention.value
    if (!mention) return

    // Usar el store de workspace para navegar
    // Pasar startChar (posición global) y surfaceForm (texto exacto)
    // El frontend usará la posición para encontrar la ocurrencia exacta
    workspaceStore.navigateToTextPosition(mention.startChar, mention.surfaceForm)
  }

  /**
   * Va a la mención anterior
   */
  function goToPrevious() {
    if (!canGoPrevious.value) return
    state.value.currentIndex--
    navigateToCurrentMention()
  }

  /**
   * Va a la mención siguiente
   */
  function goToNext() {
    if (!canGoNext.value) return
    state.value.currentIndex++
    navigateToCurrentMention()
  }

  /**
   * Va a una mención específica por índice
   */
  function goToMention(index: number) {
    if (index < 0 || index >= state.value.mentions.length) return
    state.value.currentIndex = index
    navigateToCurrentMention()
  }

  /**
   * Limpia el estado de navegación
   */
  function clear() {
    state.value = {
      entityId: null,
      entityName: null,
      entityType: null,
      mentions: [],
      currentIndex: -1,
      loading: false,
      error: null,
    }
  }

  /**
   * Inicia la navegación de menciones para una entidad
   */
  async function startNavigation(entityId: number) {
    // Si ya estamos navegando la misma entidad, no recargar
    if (state.value.entityId === entityId && state.value.mentions.length > 0) {
      // Solo navegar a la primera mención
      state.value.currentIndex = 0
      navigateToCurrentMention()
      return true
    }

    return await loadMentions(entityId)
  }

  return {
    // Estado
    state,

    // Computed
    isActive,
    currentMention,
    totalMentions,
    canGoPrevious,
    canGoNext,
    navigationLabel,

    // Acciones
    loadMentions,
    startNavigation,
    goToPrevious,
    goToNext,
    goToMention,
    navigateToCurrentMention,
    clear,
  }
}
