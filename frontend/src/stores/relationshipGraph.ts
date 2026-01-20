import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'

/**
 * Tipos de relación disponibles
 */
export type RelationshipType =
  | 'FAMILY'
  | 'ROMANTIC'
  | 'FRIENDSHIP'
  | 'PROFESSIONAL'
  | 'RIVALRY'
  | 'ALLY'
  | 'MENTOR'
  | 'ENEMY'
  | 'NEUTRAL'

/**
 * Niveles de fuerza de relación
 */
export type RelationshipStrength = 'WEAK' | 'MODERATE' | 'STRONG' | 'VERY_STRONG'

/**
 * Valencia de la relación
 */
export type RelationshipValence = 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL'

/**
 * Estado de los filtros del grafo
 */
export interface RelationshipGraphFilters {
  relationshipTypes: RelationshipType[]
  strengthLevels: RelationshipStrength[]
  valences: RelationshipValence[]
  showOnlyConfirmed: boolean
  minStrength: number
  showClusters: boolean
}

/**
 * Opciones para los filtros
 */
export interface FilterOption<T> {
  label: string
  value: T
  color?: string
  icon?: string
}

const STORAGE_KEY = 'narrative_assistant_relationship_graph_filters'

/**
 * Store para gestionar los filtros del grafo de relaciones
 */
export const useRelationshipGraphStore = defineStore('relationshipGraph', () => {
  // Opciones de tipos de relación
  const relationshipTypeOptions: FilterOption<RelationshipType>[] = [
    { label: 'Familiar', value: 'FAMILY', color: '#8b5cf6', icon: 'pi pi-users' },
    { label: 'Romántica', value: 'ROMANTIC', color: '#ec4899', icon: 'pi pi-heart' },
    { label: 'Amistad', value: 'FRIENDSHIP', color: '#10b981', icon: 'pi pi-heart-fill' },
    { label: 'Profesional', value: 'PROFESSIONAL', color: '#3b82f6', icon: 'pi pi-briefcase' },
    { label: 'Rivalidad', value: 'RIVALRY', color: '#f97316', icon: 'pi pi-bolt' },
    { label: 'Aliado', value: 'ALLY', color: '#06b6d4', icon: 'pi pi-shield' },
    { label: 'Mentor', value: 'MENTOR', color: '#a855f7', icon: 'pi pi-star' },
    { label: 'Enemigo', value: 'ENEMY', color: '#ef4444', icon: 'pi pi-times-circle' },
    { label: 'Neutral', value: 'NEUTRAL', color: '#6b7280', icon: 'pi pi-minus-circle' }
  ]

  // Opciones de fuerza
  const strengthOptions: FilterOption<RelationshipStrength>[] = [
    { label: 'Débil', value: 'WEAK', color: '#d1d5db' },
    { label: 'Moderada', value: 'MODERATE', color: '#9ca3af' },
    { label: 'Fuerte', value: 'STRONG', color: '#6b7280' },
    { label: 'Muy fuerte', value: 'VERY_STRONG', color: '#374151' }
  ]

  // Opciones de valencia
  const valenceOptions: FilterOption<RelationshipValence>[] = [
    { label: 'Positiva', value: 'POSITIVE', color: '#10b981' },
    { label: 'Negativa', value: 'NEGATIVE', color: '#ef4444' },
    { label: 'Neutral', value: 'NEUTRAL', color: '#6b7280' }
  ]

  // Valores por defecto
  const defaultFilters: RelationshipGraphFilters = {
    relationshipTypes: [],
    strengthLevels: [],
    valences: [],
    showOnlyConfirmed: false,
    minStrength: 0,  // Sin filtro mínimo por defecto
    showClusters: true
  }

  // Cargar filtros desde localStorage
  const loadFiltersFromStorage = (): RelationshipGraphFilters => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const parsed = JSON.parse(stored)
        return { ...defaultFilters, ...parsed }
      }
    } catch (err) {
      console.warn('Error loading relationship graph filters from storage:', err)
    }
    return { ...defaultFilters }
  }

  // Estado de los filtros
  const filters = ref<RelationshipGraphFilters>(loadFiltersFromStorage())

  // Layout seleccionado
  const layoutType = ref<string>('forceAtlas2Based')

  // Guardar filtros en localStorage cuando cambien
  watch(
    filters,
    (newFilters) => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(newFilters))
      } catch (err) {
        console.warn('Error saving relationship graph filters to storage:', err)
      }
    },
    { deep: true }
  )

  // Computed: verificar si hay filtros activos
  const hasActiveFilters = computed(() => {
    return (
      filters.value.relationshipTypes.length > 0 ||
      filters.value.strengthLevels.length > 0 ||
      filters.value.valences.length > 0 ||
      filters.value.showOnlyConfirmed ||
      filters.value.minStrength > 0
    )
  })

  // Computed: contador de filtros activos
  const activeFilterCount = computed(() => {
    let count = 0
    if (filters.value.relationshipTypes.length > 0) count++
    if (filters.value.strengthLevels.length > 0) count++
    if (filters.value.valences.length > 0) count++
    if (filters.value.showOnlyConfirmed) count++
    if (filters.value.minStrength > 0) count++
    return count
  })

  // Acciones
  const setRelationshipTypes = (types: RelationshipType[]) => {
    filters.value.relationshipTypes = types
  }

  const setStrengthLevels = (levels: RelationshipStrength[]) => {
    filters.value.strengthLevels = levels
  }

  const setValences = (valences: RelationshipValence[]) => {
    filters.value.valences = valences
  }

  const setShowOnlyConfirmed = (value: boolean) => {
    filters.value.showOnlyConfirmed = value
  }

  const setMinStrength = (value: number) => {
    filters.value.minStrength = value
  }

  const setShowClusters = (value: boolean) => {
    filters.value.showClusters = value
  }

  const setLayoutType = (layout: string) => {
    layoutType.value = layout
  }

  const resetFilters = () => {
    filters.value = { ...defaultFilters }
  }

  /**
   * Convierte un valor de fuerza numérico a nivel de fuerza
   */
  const strengthValueToLevel = (strength: number): RelationshipStrength => {
    if (strength < 0.25) return 'WEAK'
    if (strength < 0.5) return 'MODERATE'
    if (strength < 0.75) return 'STRONG'
    return 'VERY_STRONG'
  }

  /**
   * Obtiene el rango de fuerza para un nivel dado
   */
  const getStrengthRange = (level: RelationshipStrength): { min: number; max: number } => {
    switch (level) {
      case 'WEAK':
        return { min: 0, max: 0.25 }
      case 'MODERATE':
        return { min: 0.25, max: 0.5 }
      case 'STRONG':
        return { min: 0.5, max: 0.75 }
      case 'VERY_STRONG':
        return { min: 0.75, max: 1.0 }
    }
  }

  /**
   * Obtiene el color para un tipo de relación
   */
  const getRelationshipTypeColor = (type: RelationshipType): string => {
    const option = relationshipTypeOptions.find((o) => o.value === type)
    return option?.color || '#6b7280'
  }

  /**
   * Obtiene el color para una valencia
   */
  const getValenceColor = (valence: RelationshipValence): string => {
    const option = valenceOptions.find((o) => o.value === valence)
    return option?.color || '#6b7280'
  }

  /**
   * Obtiene el grosor de línea según la fuerza
   */
  const getEdgeWidthForStrength = (strength: number): number => {
    const level = strengthValueToLevel(strength)
    switch (level) {
      case 'WEAK':
        return 1
      case 'MODERATE':
        return 2
      case 'STRONG':
        return 3
      case 'VERY_STRONG':
        return 5
    }
  }

  /**
   * Obtiene el estilo de línea según la valencia
   */
  const getEdgeDashForValence = (valence: string): number[] | false => {
    const normalizedValence = valence.toUpperCase()
    switch (normalizedValence) {
      case 'POSITIVE':
      case 'VERY_POSITIVE':
        return false // Línea sólida
      case 'NEGATIVE':
      case 'VERY_NEGATIVE':
        return [5, 5] // Línea punteada
      case 'NEUTRAL':
      default:
        return [10, 5] // Línea con guiones
    }
  }

  return {
    // Estado
    filters,
    layoutType,

    // Opciones
    relationshipTypeOptions,
    strengthOptions,
    valenceOptions,

    // Getters
    hasActiveFilters,
    activeFilterCount,

    // Acciones
    setRelationshipTypes,
    setStrengthLevels,
    setValences,
    setShowOnlyConfirmed,
    setMinStrength,
    setShowClusters,
    setLayoutType,
    resetFilters,

    // Utilidades
    strengthValueToLevel,
    getStrengthRange,
    getRelationshipTypeColor,
    getValenceColor,
    getEdgeWidthForStrength,
    getEdgeDashForValence
  }
})
