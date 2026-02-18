/**
 * useAlertFiltering - Filtrado, estadísticas y meta-categorías de alertas.
 *
 * Extraído de AlertsDashboard + AlertsPanel para reutilización.
 * Usa el algoritmo single-pass de AlertsPanel para meta-categorías (más eficiente).
 */

import { ref, computed, watch, onMounted, type Ref, type ComputedRef } from 'vue'
import type { Alert, AlertSeverity } from '@/types'
import { useAlertUtils, getAlertTypeLabel, META_CATEGORIES, type MetaCategoryKey } from './useAlertUtils'
import { safeSetItem, safeGetItem } from '@/utils/safeStorage'

export interface AlertFilteringOptions {
  /** Estados por defecto al iniciar (default: ['active']) */
  defaultStatuses?: string[]
  /** Clave para persistir filtros en localStorage (si se omite, no persiste) */
  persistKey?: string
  /** Fuente de entidades para filtro por entidad */
  entities?: () => Array<{ id: number; name: string }>
}

export interface AlertStats {
  total: number
  filtered: number
  bySeverity: Record<string, number>
  byStatus: Record<string, number>
  active: number
}

/** Preset de filtro rápido */
export interface FilterPreset {
  key: string
  label: string
  icon: string
  filters: Partial<{
    selectedSeverities: AlertSeverity[]
    selectedCategories: string[]
    selectedAlertTypes: string[]
  }>
}

export const FILTER_PRESETS: FilterPreset[] = [
  { key: 'grammar', label: 'Errores gramaticales', icon: 'pi pi-spell-check',
    filters: { selectedCategories: ['grammar', 'agreement', 'typography', 'punctuation'] } },
  { key: 'high', label: 'Severidad alta+', icon: 'pi pi-exclamation-triangle',
    filters: { selectedSeverities: ['critical', 'high'] } },
  { key: 'consistency', label: 'Inconsistencias', icon: 'pi pi-exclamation-circle',
    filters: { selectedCategories: ['attribute', 'timeline', 'relationship', 'location', 'behavior', 'knowledge'] } },
  { key: 'style', label: 'Estilo y repetición', icon: 'pi pi-pencil',
    filters: { selectedCategories: ['style', 'repetition'] } },
]

const PERSIST_SCHEMA_VERSION = 1

export function useAlertFiltering(
  alerts: () => Alert[],
  options?: AlertFilteringOptions
) {
  const { getCategoryConfig } = useAlertUtils()
  const defaultStatuses = options?.defaultStatuses ?? ['active']

  // === Estado de filtros ===
  const searchQuery = ref('')
  const selectedSeverities = ref<AlertSeverity[]>([])
  const selectedCategories = ref<string[]>([])
  const selectedStatuses = ref<string[]>([...defaultStatuses])
  const chapterRange = ref<{ min: number | null; max: number | null }>({ min: null, max: null })
  const minConfidence = ref<number | null>(null)
  const selectedAlertTypes = ref<string[]>([])
  const selectedEntityIds = ref<number[]>([])

  // === Meta-categorías (single-pass, más eficiente) ===
  const selectedMetaCategory = ref<MetaCategoryKey | null>(null)

  const metaCategoryCounts = computed(() => {
    const counts: Record<MetaCategoryKey, number> = { errors: 0, inconsistencies: 0, suggestions: 0 }
    for (const alert of alerts()) {
      if (alert.status !== 'active') continue
      for (const [key, meta] of Object.entries(META_CATEGORIES)) {
        if (meta.categories.includes(alert.category as never)) {
          counts[key as MetaCategoryKey]++
          break
        }
      }
    }
    return counts
  })

  function toggleMetaCategory(key: MetaCategoryKey) {
    if (selectedMetaCategory.value === key) {
      selectedMetaCategory.value = null
      selectedCategories.value = []
    } else {
      selectedMetaCategory.value = key
      selectedCategories.value = [...META_CATEGORIES[key].categories]
    }
  }

  // === Opciones estáticas ===
  const severityOptions: Array<{ label: string; value: AlertSeverity }> = [
    { label: 'Crítica', value: 'critical' },
    { label: 'Alta', value: 'high' },
    { label: 'Media', value: 'medium' },
    { label: 'Baja', value: 'low' },
    { label: 'Info', value: 'info' }
  ]

  const statusOptions = [
    { label: 'Activas', value: 'active' },
    { label: 'Resueltas', value: 'resolved' },
    { label: 'Descartadas', value: 'dismissed' }
  ]

  const confidenceOptions = [
    { label: 'Cualquier confianza', value: null },
    { label: '> 90%', value: 90 },
    { label: '> 80%', value: 80 },
    { label: '> 70%', value: 70 }
  ]

  const categoryOptions = computed(() => {
    const categories = new Set(alerts().map(a => a.category).filter(Boolean))
    return Array.from(categories).map(cat => ({
      label: getCategoryConfig(cat as any).label,
      value: cat
    }))
  })

  const alertTypeOptions = computed(() => {
    const types = new Set(alerts().map(a => a.alertType).filter(Boolean))
    return Array.from(types).sort().map(t => ({
      label: getAlertTypeLabel(t),
      value: t
    }))
  })

  const entityOptions = computed(() => {
    if (options?.entities) {
      return options.entities().map(e => ({ label: e.name, value: e.id }))
    }
    return []
  })

  // === Filtrado (single-pass + sort) ===
  const filteredAlerts = computed(() => {
    const query = searchQuery.value?.toLowerCase()
    const hasSearch = !!query
    const hasSeverityFilter = selectedSeverities.value.length > 0
    const hasCategoryFilter = selectedCategories.value.length > 0
    const hasStatusFilter = selectedStatuses.value.length > 0
    const hasChapterRange = chapterRange.value.min != null || chapterRange.value.max != null
    const hasConfidenceFilter = minConfidence.value !== null
    const hasAlertTypeFilter = selectedAlertTypes.value.length > 0
    const hasEntityFilter = selectedEntityIds.value.length > 0
    const { min: chapterMin, max: chapterMax } = chapterRange.value

    const result = alerts().filter(a => {
      if (hasSearch && !(a.title.toLowerCase().includes(query!) || a.description?.toLowerCase().includes(query!))) {
        return false
      }
      if (hasSeverityFilter && !selectedSeverities.value.includes(a.severity)) {
        return false
      }
      if (hasCategoryFilter && (!a.category || !selectedCategories.value.includes(a.category))) {
        return false
      }
      if (hasAlertTypeFilter && !selectedAlertTypes.value.includes(a.alertType)) {
        return false
      }
      if (hasStatusFilter && !selectedStatuses.value.includes(a.status)) {
        return false
      }
      if (hasChapterRange) {
        if (a.chapter == null) return false
        if (chapterMin != null && a.chapter < chapterMin) return false
        if (chapterMax != null && a.chapter > chapterMax) return false
      }
      if (hasConfidenceFilter && (a.confidence ?? 0) < minConfidence.value!) {
        return false
      }
      if (hasEntityFilter && !a.entityIds?.some(id => selectedEntityIds.value.includes(id))) {
        return false
      }
      return true
    })

    const severityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
    return result.sort((a, b) => {
      const severityDiff = (severityOrder[a.severity] ?? 5) - (severityOrder[b.severity] ?? 5)
      if (severityDiff !== 0) return severityDiff
      return (a.chapter ?? 999) - (b.chapter ?? 999)
    })
  })

  // === Estadísticas (single-pass) ===
  const stats = computed<AlertStats>(() => {
    const bySeverity: Record<string, number> = {}
    const byStatus: Record<string, number> = { active: 0, resolved: 0, dismissed: 0 }

    for (const alert of alerts()) {
      bySeverity[alert.severity] = (bySeverity[alert.severity] || 0) + 1
      byStatus[alert.status] = (byStatus[alert.status] || 0) + 1
    }

    return {
      total: alerts().length,
      filtered: filteredAlerts.value.length,
      bySeverity,
      byStatus,
      active: byStatus.active
    }
  })

  // === Helpers ===
  const hasActiveFilters = computed(() =>
    searchQuery.value || selectedSeverities.value.length > 0 || selectedCategories.value.length > 0
      || chapterRange.value.min != null || chapterRange.value.max != null || minConfidence.value !== null
      || selectedAlertTypes.value.length > 0 || selectedEntityIds.value.length > 0
  )

  function clearFilters() {
    searchQuery.value = ''
    selectedSeverities.value = []
    selectedCategories.value = []
    selectedStatuses.value = [...defaultStatuses]
    chapterRange.value = { min: null, max: null }
    minConfidence.value = null
    selectedMetaCategory.value = null
    selectedAlertTypes.value = []
    selectedEntityIds.value = []
  }

  function applyPreset(preset: FilterPreset) {
    clearFilters()
    if (preset.filters.selectedSeverities) selectedSeverities.value = [...preset.filters.selectedSeverities]
    if (preset.filters.selectedCategories) selectedCategories.value = [...preset.filters.selectedCategories]
    if (preset.filters.selectedAlertTypes) selectedAlertTypes.value = [...preset.filters.selectedAlertTypes]
  }

  // === Persistencia ===
  if (options?.persistKey) {
    const key = options.persistKey

    onMounted(() => {
      try {
        const raw = safeGetItem(key)
        if (raw) {
          const saved = JSON.parse(raw)
          if (saved._v === PERSIST_SCHEMA_VERSION) {
            if (saved.severities?.length) selectedSeverities.value = saved.severities
            if (saved.categories?.length) selectedCategories.value = saved.categories
            if (saved.alertTypes?.length) selectedAlertTypes.value = saved.alertTypes
            if (saved.entityIds?.length) selectedEntityIds.value = saved.entityIds
            if (saved.confidence != null) minConfidence.value = saved.confidence
          }
        }
      } catch { /* ignore corrupt data */ }
    })

    let persistTimer: ReturnType<typeof setTimeout> | null = null
    watch(
      [selectedSeverities, selectedCategories, selectedAlertTypes, selectedEntityIds, minConfidence],
      () => {
        if (persistTimer) clearTimeout(persistTimer)
        persistTimer = setTimeout(() => {
          safeSetItem(key, JSON.stringify({
            _v: PERSIST_SCHEMA_VERSION,
            severities: selectedSeverities.value,
            categories: selectedCategories.value,
            alertTypes: selectedAlertTypes.value,
            entityIds: selectedEntityIds.value,
            confidence: minConfidence.value,
          }))
        }, 300)
      },
    )
  }

  /**
   * Sincroniza con el filtro de severidad del workspace store.
   * Llamar dentro de setup() del componente que lo necesite.
   */
  function syncWithWorkspaceStore(workspaceStore: { alertSeverityFilter: string | null; setAlertSeverityFilter: (v: string | null) => void }) {
    watch(() => workspaceStore.alertSeverityFilter, (newFilter) => {
      if (newFilter) {
        selectedSeverities.value = [newFilter as AlertSeverity]
        workspaceStore.setAlertSeverityFilter(null)
      }
    }, { immediate: true })

    onMounted(() => {
      if (workspaceStore.alertSeverityFilter) {
        selectedSeverities.value = [workspaceStore.alertSeverityFilter as AlertSeverity]
        workspaceStore.setAlertSeverityFilter(null)
      }
    })
  }

  return {
    // Filter state
    searchQuery,
    selectedSeverities,
    selectedCategories,
    selectedStatuses,
    chapterRange,
    minConfidence,
    selectedAlertTypes,
    selectedEntityIds,

    // Meta-categories
    selectedMetaCategory,
    metaCategoryCounts,
    toggleMetaCategory,

    // Static options
    severityOptions,
    statusOptions,
    confidenceOptions,
    categoryOptions,
    alertTypeOptions,
    entityOptions,

    // Presets
    applyPreset,

    // Computed
    filteredAlerts,
    stats,
    hasActiveFilters,

    // Methods
    clearFilters,
    syncWithWorkspaceStore,
  }
}
