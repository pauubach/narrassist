/**
 * useAlertUtils - Utilidades para trabajar con alertas de inconsistencia.
 *
 * Proporciona funciones helper para severidades, categorías y formateo de alertas.
 */

import type { Alert, AlertSeverity, AlertCategory, AlertStatus } from '@/types'

/**
 * Traducciones de claves de atributos a español.
 * Centralizado para evitar duplicación entre componentes.
 */
export const ATTRIBUTE_TRANSLATIONS: Record<string, string> = {
  // Físicos - personajes
  eye_color: 'Color de ojos',
  hair_color: 'Color de cabello',
  hair_type: 'Tipo de cabello',
  age: 'Edad',
  height: 'Altura',
  build: 'Complexión',
  skin: 'Piel',
  skin_color: 'Color de piel',
  distinctive_feature: 'Rasgo distintivo',
  weight: 'Peso',
  scar: 'Cicatriz',
  tattoo: 'Tatuaje',

  // Psicológicos
  personality: 'Personalidad',
  temperament: 'Temperamento',
  fear: 'Miedo',
  desire: 'Deseo',
  goal: 'Objetivo',
  trait: 'Rasgo',
  motivation: 'Motivación',
  quirk: 'Peculiaridad',
  habit: 'Hábito',
  mannerism: 'Manierismo',
  like: 'Gusto',
  dislike: 'Disgusto',
  favorite: 'Favorito',

  // Sociales
  profession: 'Profesión',
  occupation: 'Ocupación',
  title: 'Título',
  role: 'Rol',
  relationship: 'Relación',
  nationality: 'Nacionalidad',
  family: 'Familia',
  friend: 'Amigo',
  enemy: 'Enemigo',
  ally: 'Aliado',
  affiliation: 'Afiliación',
  organization: 'Organización',
  group: 'Grupo',
  faction: 'Facción',
  allegiance: 'Lealtad',
  rank: 'Rango',

  // Origen y especie
  background: 'Trasfondo',
  origin: 'Origen',
  species: 'Especie',
  race: 'Raza',
  class: 'Clase',

  // Comunicación
  language: 'Idioma',
  accent: 'Acento',
  voice: 'Voz',

  // Lugares
  climate: 'Clima',
  terrain: 'Terreno',
  size: 'Tamaño',
  location: 'Ubicación',
  address: 'Dirección',

  // Objetos
  material: 'Material',
  color: 'Color',
  condition: 'Estado',
  appearance: 'Apariencia',
  clothing: 'Vestimenta',
  weapon: 'Arma',
  vehicle: 'Vehículo',
  symbol: 'Símbolo',
  mark: 'Marca',

  // Habilidades
  skill: 'Habilidad',
  power: 'Poder',
  weakness: 'Debilidad',
  strength: 'Fortaleza',
  hobby: 'Pasatiempo',

  // Lugares (extendido)
  location_type: 'Tipo de lugar',
  atmosphere: 'Atmósfera',

  // Objetos (extendido)
  function: 'Función',

  // Genérico
  notes: 'Notas',
  other: 'Otro',
  name: 'Nombre',
  alias: 'Alias',
  description: 'Descripción',
  status: 'Estado',
  pet: 'Mascota',
  birth_date: 'Fecha de nacimiento',
  birthdate: 'Fecha de nacimiento',
  death_date: 'Fecha de fallecimiento',
  gender: 'Género',
}

/**
 * Traduce un nombre de atributo del inglés al español.
 * @param key - Clave del atributo en inglés (ej: "hair_type")
 * @returns Nombre traducido (ej: "Tipo de cabello")
 */
export function translateAttributeName(key: string): string {
  // Normalizar: manejar tanto snake_case como espacios
  const normalizedKey = key.toLowerCase().replace(/\s+/g, '_')

  if (normalizedKey in ATTRIBUTE_TRANSLATIONS) {
    return ATTRIBUTE_TRANSLATIONS[normalizedKey]
  }

  // Fallback: convertir snake_case a Title Case
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())
}

/**
 * Labels en español para cada tipo específico de alerta (AlertIssueType).
 *
 * Cubre ~55 de 80+ tipos del backend. Los tipos no listados usan fallback
 * en getAlertTypeLabel().
 */
export const ALERT_TYPE_LABELS: Record<string, string> = {
  // Repetition
  linguistic_filler: 'Muletilla (catálogo)',
  overused_word: 'Palabra sobreusada',
  lexical_close: 'Repetición léxica',
  sentence_start: 'Inicio oración repetido',
  paragraph_start: 'Inicio párrafo repetido',
  cacophony: 'Cacofonía',

  // Typography (dashguiones, comillas, puntos suspensivos, espaciado)
  wrong_dash_dialogue: 'Guion de diálogo incorrecto',
  wrong_dash_range: 'Guion de rango incorrecto',
  wrong_dash_inciso: 'Guion de inciso incorrecto',
  wrong_quote_style: 'Estilo de comillas incorrecto',
  mixed_quotes: 'Comillas mezcladas',
  wrong_ellipsis: 'Puntos suspensivos incorrectos',
  spacing_before_punct: 'Espacio antes de puntuación',
  spacing_after_punct: 'Espacio después de puntuación',
  multiple_spaces: 'Espacios múltiples',
  invalid_punct_sequence: 'Secuencia de puntuación inválida',
  unclosed_pair: 'Par sin cerrar',
  quote_period_order: 'Orden punto-comilla incorrecto',

  // Grammar
  leismo: 'Leísmo',
  laismo: 'Laísmo',
  loismo: 'Loísmo',
  dequeismo: 'Dequeísmo',
  queismo: 'Queísmo',
  gender_agreement: 'Concordancia de género',
  number_agreement: 'Concordancia de número',
  adjective_agreement: 'Concordancia de adjetivo',
  subject_verb: 'Concordancia sujeto-verbo',
  redundancy: 'Redundancia',
  gender_disagreement: 'Discordancia género',
  number_disagreement: 'Discordancia número',

  // Clarity
  sentence_too_long: 'Oración demasiado larga',
  sentence_long_warning: 'Oración larga',
  too_many_subordinates: 'Demasiadas subordinadas',
  paragraph_no_pauses: 'Párrafo sin pausas',
  run_on_sentence: 'Oración continua',
  paragraph_too_short: 'Párrafo muy corto',
  paragraph_too_long: 'Párrafo muy largo',

  // POV
  person_shift: 'Cambio de persona',
  focalizer_shift: 'Cambio de focalizador',
  tu_usted_mix: 'Mezcla tú/usted',
  inconsistent_omniscience: 'Omnisciencia inconsistente',
  pov_shift: 'Cambio de POV',

  // Style
  register_change: 'Cambio de registro',
  speech_change: 'Cambio de habla',
  sticky_sentence: 'Oración pegajosa',
  low_energy_sentence: 'Oración baja energía',

  // Spelling
  typo: 'Error tipográfico',
  misspelling: 'Falta ortográfica',
  accent: 'Tilde incorrecta',

  // Anglicisms
  raw_anglicism: 'Anglicismo crudo',
  morphological_anglicism: 'Anglicismo morfológico',
  semantic_calque: 'Calco semántico',
}

export function getAlertTypeLabel(type: string): string {
  return ALERT_TYPE_LABELS[type] || type.replace(/_/g, ' ')
}

export interface SeverityConfig {
  label: string
  icon: string
  color: string
  priority: number
  /** PrimeVue severity value for Tag/Badge components */
  primeSeverity: 'danger' | 'warn' | 'info' | 'success' | 'secondary'
}

export interface CategoryConfig {
  label: string
  description: string
  icon: string
}

export interface StatusConfig {
  label: string
  icon: string
}

const severityConfigs: Record<AlertSeverity, SeverityConfig> = {
  critical: {
    label: 'Crítico',
    icon: 'pi pi-exclamation-circle',
    color: 'var(--ds-alert-critical)',
    priority: 5,
    primeSeverity: 'danger',
  },
  high: {
    label: 'Alto',
    icon: 'pi pi-exclamation-triangle',
    color: 'var(--ds-alert-high)',
    priority: 4,
    primeSeverity: 'warn',
  },
  medium: {
    label: 'Medio',
    icon: 'pi pi-info-circle',
    color: 'var(--ds-alert-medium-text, var(--ds-alert-medium))',
    priority: 3,
    primeSeverity: 'info',
  },
  low: {
    label: 'Bajo',
    icon: 'pi pi-circle',
    color: 'var(--ds-alert-low)',
    priority: 2,
    primeSeverity: 'secondary',
  },
  info: {
    label: 'Información',
    icon: 'pi pi-info',
    color: 'var(--ds-alert-info)',
    priority: 1,
    primeSeverity: 'info',
  },
}

const categoryConfigs: Record<AlertCategory, CategoryConfig> = {
  attribute: {
    label: 'Inconsistencia de atributo',
    description: 'Un personaje tiene atributos contradictorios',
    icon: 'pi pi-user-edit',
  },
  timeline: {
    label: 'Inconsistencia temporal',
    description: 'Problema en la línea temporal de eventos',
    icon: 'pi pi-clock',
  },
  relationship: {
    label: 'Inconsistencia de relación',
    description: 'Contradicción en relaciones entre personajes',
    icon: 'pi pi-users',
  },
  location: {
    label: 'Inconsistencia de ubicación',
    description: 'Un personaje aparece en lugares imposibles',
    icon: 'pi pi-map',
  },
  behavior: {
    label: 'Inconsistencia de comportamiento',
    description: 'Acción fuera de carácter del personaje',
    icon: 'pi pi-exclamation-triangle',
  },
  knowledge: {
    label: 'Inconsistencia de conocimiento',
    description: 'Personaje sabe algo que no debería',
    icon: 'pi pi-brain',
  },
  style: {
    label: 'Problema de estilo',
    description: 'Repeticiones, voz narrativa, etc.',
    icon: 'pi pi-pencil',
  },
  grammar: {
    label: 'Error gramatical u ortográfico',
    description: 'Errores de escritura detectados',
    icon: 'pi pi-spell-check',
  },
  structure: {
    label: 'Problema estructural',
    description: 'Problemas en la estructura narrativa',
    icon: 'pi pi-sitemap',
  },
  typography: {
    label: 'Tipografía',
    description: 'Comillas, espaciado incorrecto',
    icon: 'pi pi-minus',
  },
  punctuation: {
    label: 'Puntuación',
    description: 'Raya de diálogo, puntos suspensivos',
    icon: 'pi pi-ellipsis-h',
  },
  repetition: {
    label: 'Repetición',
    description: 'Palabras repetidas en proximidad',
    icon: 'pi pi-clone',
  },
  agreement: {
    label: 'Concordancia',
    description: 'Errores de concordancia género/número',
    icon: 'pi pi-link',
  },
  other: {
    label: 'Otra inconsistencia',
    description: 'Otro tipo de problema narrativo',
    icon: 'pi pi-question-circle',
  },
}

const statusConfigs: Record<AlertStatus, StatusConfig> = {
  active: {
    label: 'Activa',
    icon: 'pi pi-circle-fill',
  },
  dismissed: {
    label: 'Descartada',
    icon: 'pi pi-times-circle',
  },
  resolved: {
    label: 'Resuelta',
    icon: 'pi pi-check-circle',
  },
}

/**
 * Meta-categorías para agrupación simplificada de alertas.
 * Agrupa las 14 categorías en 3 grupos de alto nivel.
 */
export const META_CATEGORIES = {
  errors: {
    key: 'errors' as const,
    label: 'Errores',
    icon: 'pi pi-times-circle',
    color: 'var(--ds-color-danger, #ef4444)',
    bgColor: 'var(--p-red-50, #fef2f2)',
    darkBgColor: 'color-mix(in srgb, var(--p-red-900, #7f1d1d) 40%, transparent)',
    categories: ['grammar', 'typography', 'punctuation', 'agreement'] as AlertCategory[],
  },
  inconsistencies: {
    key: 'inconsistencies' as const,
    label: 'Inconsistencias',
    icon: 'pi pi-exclamation-triangle',
    color: 'var(--ds-color-warning, #d97706)',
    bgColor: 'var(--p-yellow-50, #fefce8)',
    darkBgColor: 'color-mix(in srgb, var(--p-yellow-900, #713f12) 40%, transparent)',
    categories: ['attribute', 'timeline', 'relationship', 'location', 'behavior', 'knowledge'] as AlertCategory[],
  },
  suggestions: {
    key: 'suggestions' as const,
    label: 'Sugerencias',
    icon: 'pi pi-lightbulb',
    color: 'var(--ds-color-success, #16a34a)',
    bgColor: 'var(--p-green-50, #f0fdf4)',
    darkBgColor: 'color-mix(in srgb, var(--p-green-900, #14532d) 40%, transparent)',
    categories: ['style', 'structure', 'repetition', 'other'] as AlertCategory[],
  },
} as const

export type MetaCategoryKey = keyof typeof META_CATEGORIES

export function useAlertUtils() {
  /**
   * Obtiene la configuración de una severidad
   */
  function getSeverityConfig(severity: AlertSeverity): SeverityConfig {
    return severityConfigs[severity] || severityConfigs.medium
  }

  /**
   * Obtiene la configuración de una categoría
   */
  function getCategoryConfig(category: AlertCategory): CategoryConfig {
    return categoryConfigs[category] || categoryConfigs.other
  }

  /**
   * Obtiene la configuración de un estado
   */
  function getStatusConfig(status: AlertStatus): StatusConfig {
    return statusConfigs[status] || statusConfigs.active
  }

  /**
   * Obtiene el color CSS para una severidad
   */
  function getSeverityColor(severity: AlertSeverity): string {
    return getSeverityConfig(severity).color
  }

  /**
   * Obtiene el icono para una severidad
   */
  function getSeverityIcon(severity: AlertSeverity): string {
    return getSeverityConfig(severity).icon
  }

  /**
   * Obtiene el label traducido para una severidad
   */
  function getSeverityLabel(severity: AlertSeverity): string {
    return getSeverityConfig(severity).label
  }

  /**
   * Obtiene el label traducido para una categoría
   */
  function getCategoryLabel(category: AlertCategory): string {
    return getCategoryConfig(category).label
  }

  /**
   * Ordena alertas por severidad (más grave primero) y luego por fecha
   */
  function sortAlerts(alerts: Alert[]): Alert[] {
    return [...alerts].sort((a, b) => {
      const priorityA = getSeverityConfig(a.severity).priority
      const priorityB = getSeverityConfig(b.severity).priority

      if (priorityA !== priorityB) {
        return priorityB - priorityA // Mayor prioridad primero
      }

      // Si misma severidad, ordenar por fecha (más reciente primero)
      const dateA = a.createdAt?.getTime() ?? 0
      const dateB = b.createdAt?.getTime() ?? 0
      return dateB - dateA
    })
  }

  /**
   * Agrupa alertas por categoría
   */
  function groupAlertsByCategory(alerts: Alert[]): Map<AlertCategory, Alert[]> {
    const groups = new Map<AlertCategory, Alert[]>()

    for (const alert of alerts) {
      const existing = groups.get(alert.category) || []
      existing.push(alert)
      groups.set(alert.category, existing)
    }

    // Ordenar dentro de cada grupo
    for (const [category, list] of groups) {
      groups.set(category, sortAlerts(list))
    }

    return groups
  }

  /**
   * Agrupa alertas por severidad
   */
  function groupAlertsBySeverity(alerts: Alert[]): Map<AlertSeverity, Alert[]> {
    const groups = new Map<AlertSeverity, Alert[]>()

    for (const alert of alerts) {
      const existing = groups.get(alert.severity) || []
      existing.push(alert)
      groups.set(alert.severity, existing)
    }

    return groups
  }

  /**
   * Filtra alertas por búsqueda de texto
   */
  function filterAlerts(alerts: Alert[], query: string): Alert[] {
    if (!query.trim()) return alerts

    const normalizedQuery = query.toLowerCase().trim()

    return alerts.filter((alert) => {
      // Buscar en título
      if (alert.title.toLowerCase().includes(normalizedQuery)) {
        return true
      }

      // Buscar en descripción
      if (alert.description.toLowerCase().includes(normalizedQuery)) {
        return true
      }

      // Buscar en sugerencia
      if (alert.suggestion?.toLowerCase().includes(normalizedQuery)) {
        return true
      }

      return false
    })
  }

  /**
   * Cuenta alertas por severidad
   */
  function countBySeverity(alerts: Alert[]): Record<AlertSeverity, number> {
    const counts: Record<AlertSeverity, number> = {
      critical: 0,
      high: 0,
      medium: 0,
      low: 0,
      info: 0,
    }

    for (const alert of alerts) {
      counts[alert.severity]++
    }

    return counts
  }

  /**
   * Cuenta alertas por estado
   */
  function countByStatus(alerts: Alert[]): Record<AlertStatus, number> {
    const counts: Record<AlertStatus, number> = {
      active: 0,
      dismissed: 0,
      resolved: 0,
    }

    for (const alert of alerts) {
      counts[alert.status]++
    }

    return counts
  }

  /**
   * Obtiene solo alertas activas
   */
  function getActiveAlerts(alerts: Alert[]): Alert[] {
    return alerts.filter((alert) => alert.status === 'active')
  }

  /**
   * Formatea la ubicación de una alerta (capítulo + posición)
   */
  function formatAlertLocation(alert: Alert): string {
    const parts: string[] = []

    if (alert.chapter !== undefined) {
      parts.push(`Cap. ${alert.chapter}`)
    }

    if (alert.spanStart !== undefined && alert.spanEnd !== undefined) {
      parts.push(`pos. ${alert.spanStart}-${alert.spanEnd}`)
    }

    return parts.join(' · ') || 'Sin ubicación'
  }

  /**
   * Obtiene todas las configuraciones de severidad (para selectores)
   */
  function getAllSeverityConfigs(): Array<{ value: AlertSeverity } & SeverityConfig> {
    return (Object.entries(severityConfigs) as [AlertSeverity, SeverityConfig][]).map(
      ([value, config]) => ({ value, ...config }),
    )
  }

  /**
   * Obtiene todas las configuraciones de categoría (para selectores)
   */
  function getAllCategoryConfigs(): Array<{ value: AlertCategory } & CategoryConfig> {
    return (Object.entries(categoryConfigs) as [AlertCategory, CategoryConfig][]).map(
      ([value, config]) => ({ value, ...config }),
    )
  }

  /**
   * Formatea la etiqueta de capítulo de forma inteligente.
   *
   * Si el documento no tiene estructura de capítulos real (un solo capítulo sin título),
   * no muestra "Cap. 1" para evitar confusión.
   *
   * @param chapterNumber - Número del capítulo
   * @param totalChapters - Total de capítulos en el documento (opcional)
   * @param hasChapterTitle - Si el capítulo tiene título (opcional)
   * @returns String con la etiqueta o null si no debe mostrarse
   */
  function formatChapterLabel(
    chapterNumber: number | null | undefined,
    totalChapters?: number,
    hasChapterTitle?: boolean
  ): string | null {
    // Si no hay número de capítulo, no mostrar nada
    if (chapterNumber === null || chapterNumber === undefined) {
      return null
    }

    // Si hay solo 1 capítulo sin título, es probablemente un documento sin estructura de capítulos
    if (totalChapters === 1 && chapterNumber === 1 && !hasChapterTitle) {
      return null
    }

    return `Cap. ${chapterNumber}`
  }

  return {
    getSeverityConfig,
    getCategoryConfig,
    getStatusConfig,
    getSeverityColor,
    getSeverityIcon,
    getSeverityLabel,
    getCategoryLabel,
    sortAlerts,
    groupAlertsByCategory,
    groupAlertsBySeverity,
    filterAlerts,
    countBySeverity,
    countByStatus,
    getActiveAlerts,
    formatAlertLocation,
    formatChapterLabel,
    getAllSeverityConfigs,
    getAllCategoryConfigs,
    translateAttributeName,
  }
}
