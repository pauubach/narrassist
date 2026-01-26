/**
 * Composable para obtener el perfil de features de un proyecto.
 *
 * Conecta con el backend para obtener qué features están disponibles
 * según el tipo de documento configurado para el proyecto.
 */

import { ref, computed, watch, type Ref, type ComputedRef } from 'vue'

export type FeatureAvailability = 'enabled' | 'optional' | 'disabled'

export interface FeatureProfile {
  document_type: string
  document_subtype: string | null
  type_info: {
    name: string
    description: string
    icon: string
    color: string
  }
  features: {
    // Estructura narrativa
    characters: FeatureAvailability
    relationships: FeatureAvailability
    timeline: FeatureAvailability
    scenes: FeatureAvailability
    pov_focalization: FeatureAvailability
    // Estilo
    pacing: FeatureAvailability
    register_analysis: FeatureAvailability
    voice_profiles: FeatureAvailability
    sticky_sentences: FeatureAvailability
    echo_repetitions: FeatureAvailability
    sentence_variation: FeatureAvailability
    emotional_analysis: FeatureAvailability
    age_readability: FeatureAvailability
    // Consistencia
    attribute_consistency: FeatureAvailability
    world_consistency: FeatureAvailability
    // Técnicos
    glossary: FeatureAvailability
    terminology: FeatureAvailability
    editorial_rules: FeatureAvailability
  }
}

// Mapeo de features a tabs del workspace
const featureToTabMap: Record<string, string> = {
  characters: 'entities',
  relationships: 'relationships',
  timeline: 'timeline',
  scenes: 'style', // Las escenas están en el tab de estilo
  pov_focalization: 'style',
  pacing: 'style',
  register_analysis: 'style',
  voice_profiles: 'style',
  sticky_sentences: 'style',
  echo_repetitions: 'style',
  sentence_variation: 'style',
  emotional_analysis: 'style',
  attribute_consistency: 'alerts',
  world_consistency: 'alerts',
  glossary: 'glossary',
  terminology: 'glossary',
  editorial_rules: 'style',
}

// Mapeo inverso: qué features determinan la visibilidad de cada tab
const tabToFeaturesMap: Record<string, string[]> = {
  text: [], // Siempre visible
  entities: ['characters'],
  relationships: ['relationships'],
  timeline: ['timeline'],
  alerts: ['attribute_consistency', 'world_consistency'],
  style: [
    'scenes', 'pov_focalization', 'pacing', 'register_analysis',
    'voice_profiles', 'sticky_sentences', 'echo_repetitions',
    'sentence_variation', 'emotional_analysis', 'age_readability', 'editorial_rules'
  ],
  glossary: ['glossary', 'terminology'],
  summary: [], // Siempre visible
}

/**
 * Composable para obtener y gestionar el perfil de features de un proyecto.
 *
 * @param projectId - ID del proyecto (puede ser ref o computed)
 * @returns Perfil de features y helpers para consultar disponibilidad
 *
 * @example
 * ```vue
 * const { profile, isFeatureEnabled, isTabVisible, loading } = useFeatureProfile(
 *   computed(() => project.value?.id)
 * )
 *
 * // Usar en template
 * <Tab v-if="isTabVisible('timeline')" label="Timeline" />
 * <SceneTaggingTab v-if="isFeatureEnabled('scenes')" />
 * ```
 */
export function useFeatureProfile(
  projectId: Ref<number | undefined> | ComputedRef<number | undefined>
) {
  const profile = ref<FeatureProfile | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  /**
   * Carga el perfil de features del proyecto.
   */
  const loadProfile = async () => {
    const id = projectId.value
    if (!id) {
      profile.value = null
      return
    }

    loading.value = true
    error.value = null

    try {
      const response = await fetch(`/api/projects/${id}/feature-profile`)
      const data = await response.json()

      if (data.success) {
        profile.value = data.data
      } else {
        error.value = data.error || 'Error loading feature profile'
        profile.value = null
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Network error'
      profile.value = null
    } finally {
      loading.value = false
    }
  }

  // Cargar perfil cuando cambia el projectId
  watch(projectId, () => {
    loadProfile()
  }, { immediate: true })

  /**
   * Comprueba si una feature específica está habilitada.
   */
  const isFeatureEnabled = (feature: string): boolean => {
    if (!profile.value) return true // Default a true si no hay perfil
    const availability = profile.value.features[feature as keyof typeof profile.value.features]
    return availability === 'enabled'
  }

  /**
   * Comprueba si una feature está disponible (enabled u optional).
   */
  const isFeatureAvailable = (feature: string): boolean => {
    if (!profile.value) return true
    const availability = profile.value.features[feature as keyof typeof profile.value.features]
    return availability === 'enabled' || availability === 'optional'
  }

  /**
   * Obtiene el nivel de disponibilidad de una feature.
   */
  const getFeatureAvailability = (feature: string): FeatureAvailability => {
    if (!profile.value) return 'enabled'
    return profile.value.features[feature as keyof typeof profile.value.features] || 'enabled'
  }

  /**
   * Comprueba si un tab del workspace debe ser visible.
   * Un tab es visible si al menos una de sus features asociadas está disponible.
   */
  const isTabVisible = (tab: string): boolean => {
    // Tabs siempre visibles
    if (tab === 'text' || tab === 'summary') return true

    if (!profile.value) return true

    const features = tabToFeaturesMap[tab]
    if (!features || features.length === 0) return true

    // El tab es visible si al menos una feature está disponible
    return features.some(f => isFeatureAvailable(f))
  }

  /**
   * Información del tipo de documento actual.
   */
  const typeInfo = computed(() => profile.value?.type_info || null)

  /**
   * Código del tipo de documento actual.
   */
  const documentType = computed(() => profile.value?.document_type || null)

  /**
   * Subtipo del documento actual.
   */
  const documentSubtype = computed(() => profile.value?.document_subtype || null)

  return {
    profile,
    loading,
    error,
    loadProfile,
    isFeatureEnabled,
    isFeatureAvailable,
    getFeatureAvailability,
    isTabVisible,
    typeInfo,
    documentType,
    documentSubtype,
  }
}
