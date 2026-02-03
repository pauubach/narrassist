/**
 * useMentionNavigation - Composable para navegar entre menciones de una entidad
 *
 * Permite cargar las menciones de una entidad y navegar entre ellas
 * con botones anterior/siguiente.
 */

import { ref, computed, watch } from 'vue'
import { useWorkspaceStore } from '@/stores/workspace'
import { apiUrl } from '@/config/api'

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

  /**
   * Normaliza texto para comparación (minúsculas, sin espacios extra)
   */
  function normalizeText(text: string): string {
    return text.toLowerCase().trim().replace(/\s+/g, ' ')
  }

  /**
   * Calcula IoU (Intersection over Union) de dos spans
   */
  function calculateIoU(start1: number, end1: number, start2: number, end2: number): number {
    const intersectionStart = Math.max(start1, start2)
    const intersectionEnd = Math.min(end1, end2)
    if (intersectionEnd <= intersectionStart) return 0
    const intersection = intersectionEnd - intersectionStart
    const union = Math.max(end1, end2) - Math.min(start1, start2)
    return union > 0 ? intersection / union : 0
  }

  /**
   * Deduplica menciones que son visualmente iguales
   * - Compara posiciones SIN importar chapter_id (puede haber errores de asignación)
   * - Usa normalización de texto para comparación
   * - Usa IoU >70% para detectar solapamientos parciales
   */
  function deduplicateMentions(mentions: Mention[]): Mention[] {
    if (mentions.length <= 1) return mentions

    const result: Mention[] = []
    const POSITION_THRESHOLD = 20 // caracteres para texto muy cercano
    const IOU_THRESHOLD = 0.7 // 70% de solapamiento

    for (const mention of mentions) {
      // Verificar si es duplicada de alguna existente
      const isDuplicate = result.some(existing => {
        // 1. Verificar solapamiento de posiciones (IoU > 70%)
        const iou = calculateIoU(
          mention.startChar, mention.endChar,
          existing.startChar, existing.endChar
        )
        if (iou > IOU_THRESHOLD) return true

        // 2. Mismo texto normalizado y posición muy cercana
        const sameText = normalizeText(existing.surfaceForm) === normalizeText(mention.surfaceForm)
        const distance = Math.min(
          Math.abs(mention.startChar - existing.endChar),
          Math.abs(existing.startChar - mention.endChar)
        )
        if (sameText && distance < POSITION_THRESHOLD) return true

        return false
      })

      if (!isDuplicate) {
        result.push(mention)
      }
    }

    return result
  }

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
        apiUrl(`/api/projects/${pid}/entities/${entityId}/mentions`)
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
        // Deduplicar menciones con misma posición visual (mismo capítulo + texto + posición cercana)
        const dedupedMentions = deduplicateMentions(state.value.mentions)
        if (dedupedMentions.length < state.value.mentions.length) {
          console.log(`[MentionNav] Deduped ${state.value.mentions.length} -> ${dedupedMentions.length} mentions`)
          state.value.mentions = dedupedMentions
        }
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
    // Pasar startChar (posición dentro del capítulo), surfaceForm (texto exacto) y chapterId
    workspaceStore.navigateToTextPosition(mention.startChar, mention.surfaceForm, mention.chapterId)
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
