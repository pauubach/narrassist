/**
 * Composable para gestionar la configuración de UI según el tipo de documento.
 *
 * Determina qué pestañas, opciones y análisis están disponibles
 * basándose en el tipo de documento detectado (ficción, autoayuda, etc.)
 */

import { computed, type ComputedRef } from 'vue'
import type { DocumentType, RecommendedAnalysis } from '@/types/domain/projects'

export interface DocumentTypeUIConfig {
  /** Pestañas visibles en el workspace */
  tabs: {
    text: boolean
    entities: boolean
    relations: boolean
    timeline: boolean
    alerts: boolean
    style: boolean
  }
  /** Etiquetas de las pestañas (pueden cambiar según tipo) */
  tabLabels: {
    text: string
    entities: string
    relations: string
    timeline: string
    alerts: string
    style: string
  }
  /** Análisis disponibles */
  analysis: {
    temporal: boolean
    relationships: boolean
    behaviorConsistency: boolean
    dialogAnalysis: boolean
    conceptTracking: boolean
  }
  /** Opciones de configuración habilitadas */
  settings: {
    /** Si LLM es requerido (no mostrar opción de desactivar) */
    llmRequired: boolean
    /** Si mostrar opciones de personajes */
    showCharacterOptions: boolean
    /** Si mostrar opciones de timeline */
    showTimelineOptions: boolean
  }
  /** Descripción del tipo de documento para mostrar al usuario */
  typeLabel: string
  typeDescription: string
}

/** Configuraciones por defecto para cada tipo de documento */
const configByType: Record<DocumentType, DocumentTypeUIConfig> = {
  fiction: {
    tabs: {
      text: true,
      entities: true,
      relations: true,
      timeline: true,
      alerts: true,
      style: true,
    },
    tabLabels: {
      text: 'Texto',
      entities: 'Personajes',
      relations: 'Relaciones',
      timeline: 'Línea temporal',
      alerts: 'Alertas',
      style: 'Estilo',
    },
    analysis: {
      temporal: true,
      relationships: true,
      behaviorConsistency: true,
      dialogAnalysis: true,
      conceptTracking: false,
    },
    settings: {
      llmRequired: false,
      showCharacterOptions: true,
      showTimelineOptions: true,
    },
    typeLabel: 'Ficción',
    typeDescription: 'Novela, cuento o relato con personajes y trama',
  },

  self_help: {
    tabs: {
      text: true,
      entities: true,
      relations: false,  // No relevante
      timeline: false,   // No relevante
      alerts: true,
      style: true,
    },
    tabLabels: {
      text: 'Texto',
      entities: 'Conceptos',  // Cambiado de "Personajes"
      relations: 'Relaciones',
      timeline: 'Línea temporal',
      alerts: 'Alertas',
      style: 'Estilo',
    },
    analysis: {
      temporal: false,
      relationships: false,
      behaviorConsistency: false,
      dialogAnalysis: false,
      conceptTracking: true,
    },
    settings: {
      llmRequired: true,  // Necesario para reducir falsos positivos
      showCharacterOptions: false,
      showTimelineOptions: false,
    },
    typeLabel: 'Autoayuda',
    typeDescription: 'Libro de desarrollo personal o autoayuda',
  },

  essay: {
    tabs: {
      text: true,
      entities: true,
      relations: false,
      timeline: false,
      alerts: true,
      style: true,
    },
    tabLabels: {
      text: 'Texto',
      entities: 'Conceptos',
      relations: 'Relaciones',
      timeline: 'Línea temporal',
      alerts: 'Alertas',
      style: 'Estilo',
    },
    analysis: {
      temporal: false,
      relationships: false,
      behaviorConsistency: false,
      dialogAnalysis: false,
      conceptTracking: true,
    },
    settings: {
      llmRequired: true,
      showCharacterOptions: false,
      showTimelineOptions: false,
    },
    typeLabel: 'Ensayo',
    typeDescription: 'Ensayo o artículo de opinión',
  },

  memoir: {
    tabs: {
      text: true,
      entities: true,
      relations: true,
      timeline: true,
      alerts: true,
      style: true,
    },
    tabLabels: {
      text: 'Texto',
      entities: 'Personas',  // Personas reales, no personajes
      relations: 'Relaciones',
      timeline: 'Cronología',  // Cambiado de "Línea temporal"
      alerts: 'Alertas',
      style: 'Estilo',
    },
    analysis: {
      temporal: true,
      relationships: true,
      behaviorConsistency: false,  // Personas reales, no personajes
      dialogAnalysis: false,
      conceptTracking: false,
    },
    settings: {
      llmRequired: false,
      showCharacterOptions: true,
      showTimelineOptions: true,
    },
    typeLabel: 'Memorias',
    typeDescription: 'Autobiografía o memorias personales',
  },

  biography: {
    tabs: {
      text: true,
      entities: true,
      relations: true,
      timeline: true,
      alerts: true,
      style: true,
    },
    tabLabels: {
      text: 'Texto',
      entities: 'Personas',
      relations: 'Relaciones',
      timeline: 'Cronología',
      alerts: 'Alertas',
      style: 'Estilo',
    },
    analysis: {
      temporal: true,
      relationships: true,
      behaviorConsistency: false,
      dialogAnalysis: false,
      conceptTracking: false,
    },
    settings: {
      llmRequired: false,
      showCharacterOptions: true,
      showTimelineOptions: true,
    },
    typeLabel: 'Biografía',
    typeDescription: 'Biografía de una persona',
  },

  celebrity: {
    tabs: {
      text: true,
      entities: true,
      relations: true,
      timeline: true,
      alerts: true,
      style: true,
    },
    tabLabels: {
      text: 'Texto',
      entities: 'Personas',
      relations: 'Relaciones',
      timeline: 'Cronología',
      alerts: 'Alertas',
      style: 'Estilo',
    },
    analysis: {
      temporal: true,
      relationships: true,
      behaviorConsistency: false,
      dialogAnalysis: false,
      conceptTracking: false,
    },
    settings: {
      llmRequired: false,
      showCharacterOptions: true,
      showTimelineOptions: true,
    },
    typeLabel: 'Famosos',
    typeDescription: 'Libro de celebridad o influencer',
  },

  divulgation: {
    tabs: {
      text: true,
      entities: true,
      relations: false,
      timeline: false,
      alerts: true,
      style: true,
    },
    tabLabels: {
      text: 'Texto',
      entities: 'Conceptos',
      relations: 'Relaciones',
      timeline: 'Línea temporal',
      alerts: 'Alertas',
      style: 'Estilo',
    },
    analysis: {
      temporal: false,
      relationships: false,
      behaviorConsistency: false,
      dialogAnalysis: false,
      conceptTracking: true,
    },
    settings: {
      llmRequired: true,
      showCharacterOptions: false,
      showTimelineOptions: false,
    },
    typeLabel: 'Divulgación',
    typeDescription: 'Divulgación científica o histórica',
  },

  practical: {
    tabs: {
      text: true,
      entities: true,
      relations: false,
      timeline: false,
      alerts: true,
      style: false,
    },
    tabLabels: {
      text: 'Contenido',
      entities: 'Elementos',
      relations: 'Relaciones',
      timeline: 'Línea temporal',
      alerts: 'Alertas',
      style: 'Estilo',
    },
    analysis: {
      temporal: false,
      relationships: false,
      behaviorConsistency: false,
      dialogAnalysis: false,
      conceptTracking: false,
    },
    settings: {
      llmRequired: false,
      showCharacterOptions: false,
      showTimelineOptions: false,
    },
    typeLabel: 'Práctico',
    typeDescription: 'Libro práctico: cocina, jardinería, DIY',
  },

  children: {
    tabs: {
      text: true,
      entities: true,
      relations: true,
      timeline: true,
      alerts: true,
      style: true,
    },
    tabLabels: {
      text: 'Texto',
      entities: 'Personajes',
      relations: 'Relaciones',
      timeline: 'Línea temporal',
      alerts: 'Alertas',
      style: 'Estilo',
    },
    analysis: {
      temporal: true,
      relationships: true,
      behaviorConsistency: true,
      dialogAnalysis: true,
      conceptTracking: false,
    },
    settings: {
      llmRequired: false,
      showCharacterOptions: true,
      showTimelineOptions: true,
    },
    typeLabel: 'Infantil/Juvenil',
    typeDescription: 'Literatura para niños y jóvenes',
  },

  drama: {
    tabs: {
      text: true,
      entities: true,
      relations: true,
      timeline: true,
      alerts: true,
      style: false,
    },
    tabLabels: {
      text: 'Guion',
      entities: 'Personajes',
      relations: 'Relaciones',
      timeline: 'Línea temporal',
      alerts: 'Alertas',
      style: 'Estilo',
    },
    analysis: {
      temporal: true,
      relationships: true,
      behaviorConsistency: true,
      dialogAnalysis: true,
      conceptTracking: false,
    },
    settings: {
      llmRequired: false,
      showCharacterOptions: true,
      showTimelineOptions: true,
    },
    typeLabel: 'Teatro/Guion',
    typeDescription: 'Obra de teatro o guion de cine/TV',
  },

  graphic: {
    tabs: {
      text: true,
      entities: true,
      relations: true,
      timeline: true,
      alerts: true,
      style: false,
    },
    tabLabels: {
      text: 'Texto',
      entities: 'Personajes',
      relations: 'Relaciones',
      timeline: 'Línea temporal',
      alerts: 'Alertas',
      style: 'Estilo',
    },
    analysis: {
      temporal: true,
      relationships: true,
      behaviorConsistency: true,
      dialogAnalysis: true,
      conceptTracking: false,
    },
    settings: {
      llmRequired: false,
      showCharacterOptions: true,
      showTimelineOptions: true,
    },
    typeLabel: 'Novela gráfica',
    typeDescription: 'Cómic, manga o novela gráfica',
  },

  technical: {
    tabs: {
      text: true,
      entities: true,
      relations: false,
      timeline: false,
      alerts: true,
      style: false,  // No relevante para manuales
    },
    tabLabels: {
      text: 'Texto',
      entities: 'Términos',
      relations: 'Relaciones',
      timeline: 'Línea temporal',
      alerts: 'Alertas',
      style: 'Estilo',
    },
    analysis: {
      temporal: false,
      relationships: false,
      behaviorConsistency: false,
      dialogAnalysis: false,
      conceptTracking: true,
    },
    settings: {
      llmRequired: false,
      showCharacterOptions: false,
      showTimelineOptions: false,
    },
    typeLabel: 'Técnico',
    typeDescription: 'Manual técnico o documentación',
  },

  cookbook: {
    tabs: {
      text: true,
      entities: true,
      relations: false,
      timeline: false,
      alerts: true,
      style: false,
    },
    tabLabels: {
      text: 'Recetas',
      entities: 'Ingredientes',
      relations: 'Relaciones',
      timeline: 'Línea temporal',
      alerts: 'Alertas',
      style: 'Estilo',
    },
    analysis: {
      temporal: false,
      relationships: false,
      behaviorConsistency: false,
      dialogAnalysis: false,
      conceptTracking: false,
    },
    settings: {
      llmRequired: false,
      showCharacterOptions: false,
      showTimelineOptions: false,
    },
    typeLabel: 'Recetario',
    typeDescription: 'Libro de cocina o recetas',
  },

  academic: {
    tabs: {
      text: true,
      entities: true,
      relations: false,
      timeline: false,
      alerts: true,
      style: true,
    },
    tabLabels: {
      text: 'Texto',
      entities: 'Conceptos',
      relations: 'Relaciones',
      timeline: 'Línea temporal',
      alerts: 'Alertas',
      style: 'Estilo',
    },
    analysis: {
      temporal: false,
      relationships: false,
      behaviorConsistency: false,
      dialogAnalysis: false,
      conceptTracking: true,
    },
    settings: {
      llmRequired: true,
      showCharacterOptions: false,
      showTimelineOptions: false,
    },
    typeLabel: 'Académico',
    typeDescription: 'Paper o texto académico',
  },

  unknown: {
    // Configuración por defecto: mostrar todo
    tabs: {
      text: true,
      entities: true,
      relations: true,
      timeline: true,
      alerts: true,
      style: true,
    },
    tabLabels: {
      text: 'Texto',
      entities: 'Entidades',
      relations: 'Relaciones',
      timeline: 'Línea temporal',
      alerts: 'Alertas',
      style: 'Estilo',
    },
    analysis: {
      temporal: true,
      relationships: true,
      behaviorConsistency: true,
      dialogAnalysis: true,
      conceptTracking: true,
    },
    settings: {
      llmRequired: false,
      showCharacterOptions: true,
      showTimelineOptions: true,
    },
    typeLabel: 'Documento',
    typeDescription: 'Tipo de documento no determinado',
  },
}

/**
 * Composable para obtener la configuración de UI según el tipo de documento.
 *
 * @param documentType - Tipo de documento detectado
 * @param recommendedAnalysis - Configuración recomendada del backend (opcional, para override)
 * @returns Configuración de UI para ese tipo de documento
 *
 * @example
 * ```vue
 * const { config, visibleTabs, getTabLabel } = useDocumentTypeConfig(
 *   computed(() => project.value?.documentType)
 * )
 *
 * // Usar en template
 * <Tab v-for="tab in visibleTabs" :label="getTabLabel(tab)" />
 * ```
 */
export function useDocumentTypeConfig(
  documentType: ComputedRef<DocumentType | undefined>,
  recommendedAnalysis?: ComputedRef<RecommendedAnalysis | undefined>
) {
  /** Configuración completa para el tipo de documento actual */
  const config = computed<DocumentTypeUIConfig>(() => {
    const type = documentType.value || 'unknown'
    const baseConfig = configByType[type] || configByType.unknown

    // Si hay recommendedAnalysis del backend, hacer override
    if (recommendedAnalysis?.value?.analysis) {
      const ra = recommendedAnalysis.value.analysis
      return {
        ...baseConfig,
        tabs: {
          ...baseConfig.tabs,
          timeline: ra.temporal_analysis ?? baseConfig.tabs.timeline,
          relations: ra.relationship_detection ?? baseConfig.tabs.relations,
        },
        analysis: {
          ...baseConfig.analysis,
          temporal: ra.temporal_analysis ?? baseConfig.analysis.temporal,
          relationships: ra.relationship_detection ?? baseConfig.analysis.relationships,
          behaviorConsistency: ra.behavior_consistency ?? baseConfig.analysis.behaviorConsistency,
          dialogAnalysis: ra.dialog_analysis ?? baseConfig.analysis.dialogAnalysis,
          conceptTracking: ra.concept_tracking ?? baseConfig.analysis.conceptTracking,
        },
      }
    }

    return baseConfig
  })

  /** Lista de tabs visibles */
  const visibleTabs = computed(() => {
    const tabs = config.value.tabs
    return (Object.keys(tabs) as Array<keyof typeof tabs>).filter(key => tabs[key])
  })

  /** Obtiene la etiqueta para una pestaña */
  const getTabLabel = (tabKey: string): string => {
    return config.value.tabLabels[tabKey as keyof typeof config.value.tabLabels] || tabKey
  }

  /** Verifica si una pestaña está visible */
  const isTabVisible = (tabKey: string): boolean => {
    return config.value.tabs[tabKey as keyof typeof config.value.tabs] ?? true
  }

  /** Verifica si un análisis está habilitado */
  const isAnalysisEnabled = (analysisKey: string): boolean => {
    return config.value.analysis[analysisKey as keyof typeof config.value.analysis] ?? true
  }

  return {
    config,
    visibleTabs,
    getTabLabel,
    isTabVisible,
    isAnalysisEnabled,
  }
}
