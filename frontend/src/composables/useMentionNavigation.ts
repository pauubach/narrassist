import { computed, ref } from 'vue'
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

/**
 * useMentionNavigation - Composable para navegar entre menciones de una entidad
 *
 * Permite cargar las menciones de una entidad y navegar entre ellas
 * con botones anterior/siguiente.
 */

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
   * Deduplica menciones (normaliza texto + solape/proximidad) y prioriza la más fiable.
   */
  function deduplicateMentions(mentions: Mention[]): Mention[] {
    if (mentions.length <= 1) return mentions

    const SOURCE_PRIORITY: Record<string, number> = {
      manual: 4,
      coref: 3,
      ner: 2,
      embeddings: 1,
      heuristics: 1,
      unknown: 0,
    }

    const normalizeSurface = (text: string): string => {
      const noDiacritics = text.normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      return noDiacritics.toLowerCase().replace(/[^\w\s'-]/g, ' ').split(/\s+/).filter(Boolean).join(' ')
    }

    const spanIoU = (aStart: number, aEnd: number, bStart: number, bEnd: number): number => {
      const intersection = Math.max(0, Math.min(aEnd, bEnd) - Math.max(aStart, bStart))
      if (intersection === 0) return 0
      const union = Math.max(aEnd, bEnd) - Math.min(aStart, bStart)
      return union === 0 ? 0 : intersection / union
    }

    const spanGap = (aStart: number, aEnd: number, bStart: number, bEnd: number): number => {
      if (aEnd >= bStart && bEnd >= aStart) return 0
      return Math.min(Math.abs(aEnd - bStart), Math.abs(bEnd - aStart))
    }

    const sourcePriority = (src?: string | null): number => SOURCE_PRIORITY[src?.toLowerCase() || 'unknown'] ?? 0

    const choosePreferred = (a: Mention, b: Mention): Mention => {
      if (a.confidence !== b.confidence) return a.confidence >= b.confidence ? a : b
      const aPriority = sourcePriority(a.source)
      const bPriority = sourcePriority(b.source)
      if (aPriority !== bPriority) return aPriority > bPriority ? a : b
      if (a.surfaceForm.length !== b.surfaceForm.length) return a.surfaceForm.length >= b.surfaceForm.length ? a : b
      if (a.chapterId && !b.chapterId) return a
      if (b.chapterId && !a.chapterId) return b
      return a
    }

    const sorted = [...mentions].sort((a, b) => a.startChar - b.startChar)
    const result: Mention[] = []
    const normCache = new Map<Mention, string>()

    for (const mention of sorted) {
      const mentionNorm = normCache.get(mention) ?? normalizeSurface(mention.surfaceForm)
      normCache.set(mention, mentionNorm)

      let handled = false

      for (let i = 0; i < result.length; i++) {
        const existing = result[i]
        const existingNorm = normCache.get(existing) ?? normalizeSurface(existing.surfaceForm)
        normCache.set(existing, existingNorm)

        const iou = spanIoU(mention.startChar, mention.endChar, existing.startChar, existing.endChar)
        const gap = spanGap(mention.startChar, mention.endChar, existing.startChar, existing.endChar)

        const looksDuplicate = iou >= 0.7 || gap < 10 || (mentionNorm === existingNorm && (iou > 0 || gap < 15))
        if (!looksDuplicate) continue

        const preferred = choosePreferred(mention, existing)
        if (preferred === mention) {
          result.splice(i, 1, mention)
        }
        handled = true
        break
      }

      if (!handled) {
        result.push(mention)
      }
    }

    return result
  }

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
        throw new Error(data.error || 'No se pudo completar la operación. Si persiste, reinicia la aplicación.')
      }

      state.value.entityId = entityId
      state.value.entityName = data.data.entityName
      state.value.entityType = data.data.entityType
      state.value.mentions = data.data.mentions || []
      state.value.currentIndex = state.value.mentions.length > 0 ? 0 : -1

      // Si hay menciones, navegar a la primera
      if (state.value.mentions.length > 0) {
        const dedupedMentions = deduplicateMentions(state.value.mentions)
        if (dedupedMentions.length < state.value.mentions.length) {
          console.log(`[MentionNav] Deduped ${state.value.mentions.length} -> ${dedupedMentions.length} mentions`)
          state.value.mentions = dedupedMentions
        }
        navigateToCurrentMention()
      }

      return true
    } catch (err) {
      state.value.error = err instanceof Error ? err.message : 'No se pudo completar la operación. Si persiste, reinicia la aplicación.'
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
    if (state.value.entityId === entityId && state.value.mentions.length > 0) {
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
