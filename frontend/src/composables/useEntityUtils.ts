/**
 * useEntityUtils - Utilidades para trabajar con entidades narrativas.
 *
 * Proporciona funciones helper para colores, iconos y formateo de entidades.
 */

import type { Entity, EntityType, EntityImportance } from '@/types'

export interface EntityTypeConfig {
  label: string
  labelPlural: string
  icon: string
  color: string
}

export interface EntityImportanceConfig {
  label: string
  icon: string
  weight: number
}

const entityTypeConfigs: Record<EntityType, EntityTypeConfig> = {
  character: {
    label: 'Personaje',
    labelPlural: 'Personajes',
    icon: 'pi pi-user',
    color: 'var(--ds-entity-character)',
  },
  location: {
    label: 'Lugar',
    labelPlural: 'Lugares',
    icon: 'pi pi-map-marker',
    color: 'var(--ds-entity-location)',
  },
  object: {
    label: 'Objeto',
    labelPlural: 'Objetos',
    icon: 'pi pi-box',
    color: 'var(--ds-entity-object)',
  },
  organization: {
    label: 'Organización',
    labelPlural: 'Organizaciones',
    icon: 'pi pi-building',
    color: 'var(--ds-entity-organization)',
  },
  event: {
    label: 'Evento',
    labelPlural: 'Eventos',
    icon: 'pi pi-calendar',
    color: 'var(--ds-entity-event)',
  },
  concept: {
    label: 'Concepto',
    labelPlural: 'Conceptos',
    icon: 'pi pi-lightbulb',
    color: 'var(--ds-entity-concept)',
  },
  other: {
    label: 'Otro',
    labelPlural: 'Otros',
    icon: 'pi pi-question-circle',
    color: 'var(--ds-entity-other)',
  },
}

const entityImportanceConfigs: Record<EntityImportance, EntityImportanceConfig> = {
  main: {
    label: 'Principal',
    icon: 'pi pi-star-fill',
    weight: 3,
  },
  secondary: {
    label: 'Secundario',
    icon: 'pi pi-star',
    weight: 2,
  },
  minor: {
    label: 'Menor',
    icon: 'pi pi-circle',
    weight: 1,
  },
}

export function useEntityUtils() {
  /**
   * Obtiene la configuración de un tipo de entidad
   */
  function getTypeConfig(type: EntityType): EntityTypeConfig {
    return entityTypeConfigs[type] || entityTypeConfigs.other
  }

  /**
   * Obtiene la configuración de importancia
   */
  function getImportanceConfig(importance: EntityImportance): EntityImportanceConfig {
    return entityImportanceConfigs[importance] || entityImportanceConfigs.minor
  }

  /**
   * Obtiene el color CSS para un tipo de entidad
   */
  function getEntityColor(type: EntityType): string {
    return getTypeConfig(type).color
  }

  /**
   * Obtiene el icono para un tipo de entidad
   */
  function getEntityIcon(type: EntityType): string {
    return getTypeConfig(type).icon
  }

  /**
   * Obtiene el label traducido para un tipo de entidad
   */
  function getEntityLabel(type: EntityType, plural = false): string {
    const config = getTypeConfig(type)
    return plural ? config.labelPlural : config.label
  }

  /**
   * Formatea el nombre de una entidad con sus aliases
   */
  function formatEntityName(entity: Entity, includeAliases = false): string {
    if (!includeAliases || !entity.aliases?.length) {
      return entity.name
    }
    return `${entity.name} (${entity.aliases.slice(0, 2).join(', ')})`
  }

  /**
   * Genera iniciales para una entidad (para avatares)
   */
  function getEntityInitials(entity: Entity, maxChars = 2): string {
    const name = entity.name
    const words = name.split(/\s+/)

    if (words.length >= 2) {
      return words
        .slice(0, maxChars)
        .map((w) => w[0])
        .join('')
        .toUpperCase()
    }

    return name.slice(0, maxChars).toUpperCase()
  }

  /**
   * Ordena entidades por importancia y luego por nombre
   */
  function sortEntities(entities: Entity[]): Entity[] {
    return [...entities].sort((a, b) => {
      const weightA = getImportanceConfig(a.importance).weight
      const weightB = getImportanceConfig(b.importance).weight

      if (weightA !== weightB) {
        return weightB - weightA // Mayor peso primero
      }

      return a.name.localeCompare(b.name, 'es')
    })
  }

  /**
   * Agrupa entidades por tipo
   */
  function groupEntitiesByType(entities: Entity[]): Map<EntityType, Entity[]> {
    const groups = new Map<EntityType, Entity[]>()

    for (const entity of entities) {
      const existing = groups.get(entity.type) || []
      existing.push(entity)
      groups.set(entity.type, existing)
    }

    // Ordenar dentro de cada grupo
    for (const [type, list] of groups) {
      groups.set(type, sortEntities(list))
    }

    return groups
  }

  /**
   * Filtra entidades por búsqueda de texto
   */
  function filterEntities(entities: Entity[], query: string): Entity[] {
    if (!query.trim()) return entities

    const normalizedQuery = query.toLowerCase().trim()

    return entities.filter((entity) => {
      // Buscar en nombre
      if (entity.name.toLowerCase().includes(normalizedQuery)) {
        return true
      }

      // Buscar en aliases
      if (entity.aliases?.some((alias) => alias.toLowerCase().includes(normalizedQuery))) {
        return true
      }

      return false
    })
  }

  /**
   * Obtiene todas las configuraciones de tipos (para selectores)
   */
  function getAllTypeConfigs(): Array<{ value: EntityType } & EntityTypeConfig> {
    return (Object.entries(entityTypeConfigs) as [EntityType, EntityTypeConfig][]).map(
      ([value, config]) => ({ value, ...config }),
    )
  }

  /**
   * Obtiene todas las configuraciones de importancia (para selectores)
   */
  function getAllImportanceConfigs(): Array<{ value: EntityImportance } & EntityImportanceConfig> {
    return (
      Object.entries(entityImportanceConfigs) as [EntityImportance, EntityImportanceConfig][]
    ).map(([value, config]) => ({ value, ...config }))
  }

  // === PrimeVue severity mappings ===

  function getTypeSeverity(type: string): string {
    const severities: Record<string, string> = {
      character: 'success', location: 'danger', organization: 'info',
      object: 'warning', event: 'secondary', concept: 'contrast', other: 'secondary'
    }
    return severities[type] || 'secondary'
  }

  function getImportanceSeverity(importance: string): string {
    const severities: Record<string, string> = {
      main: 'success', secondary: 'info', minor: 'secondary'
    }
    return severities[importance] || 'secondary'
  }

  function getImportanceBadgeSeverity(importance: string): 'critical' | 'high' | 'medium' | 'low' | 'info' {
    const map: Record<string, 'critical' | 'high' | 'medium' | 'low' | 'info'> = {
      main: 'high', principal: 'high', high: 'medium',
      secondary: 'low', medium: 'low',
      minor: 'info', low: 'info', minimal: 'info'
    }
    return map[importance] || 'info'
  }

  function getImportanceLabel(importance: string): string {
    const labels: Record<string, string> = { main: 'Principal', secondary: 'Secundario', minor: 'Menor' }
    return labels[importance] || importance
  }

  // === Colores extendidos (15 tipos + subtipos) ===

  function getTypeBackgroundColor(type: string): string {
    const colors: Record<string, string> = {
      character: 'var(--ds-entity-character-bg)', location: 'var(--ds-entity-location-bg)',
      organization: 'var(--ds-entity-organization-bg)', object: 'var(--ds-entity-object-bg)',
      event: 'var(--ds-entity-event-bg)', concept: 'var(--ds-entity-concept-bg)',
      animal: 'var(--ds-entity-animal-bg)', creature: 'var(--ds-entity-creature-bg)',
      building: 'var(--ds-entity-building-bg)', region: 'var(--ds-entity-region-bg)',
      vehicle: 'var(--ds-entity-vehicle-bg)', faction: 'var(--ds-entity-faction-bg)',
      family: 'var(--ds-entity-family-bg)', time_period: 'var(--ds-entity-time-period-bg)',
      other: 'var(--ds-entity-other-bg)'
    }
    return colors[type] || colors.other
  }

  function getTypeTextColor(type: string): string {
    const colors: Record<string, string> = {
      character: 'var(--ds-entity-character)', location: 'var(--ds-entity-location)',
      organization: 'var(--ds-entity-organization)', object: 'var(--ds-entity-object)',
      event: 'var(--ds-entity-event)', concept: 'var(--ds-entity-concept)',
      animal: 'var(--ds-entity-animal)', creature: 'var(--ds-entity-creature)',
      building: 'var(--ds-entity-building)', region: 'var(--ds-entity-region)',
      vehicle: 'var(--ds-entity-vehicle)', faction: 'var(--ds-entity-faction)',
      family: 'var(--ds-entity-family)', time_period: 'var(--ds-entity-time-period)',
      other: 'var(--ds-entity-other)'
    }
    return colors[type] || colors.other
  }

  // === Relaciones ===

  function getRelationshipIcon(type: string): string {
    const icons: Record<string, string> = {
      family: 'pi pi-users', friend: 'pi pi-heart', friendship: 'pi pi-heart',
      enemy: 'pi pi-bolt', rival: 'pi pi-bolt',
      romantic: 'pi pi-heart-fill',
      professional: 'pi pi-briefcase',
      mentor: 'pi pi-graduation-cap', student: 'pi pi-book',
      ally: 'pi pi-shield', member_of: 'pi pi-sitemap',
      owns: 'pi pi-key', located_in: 'pi pi-map-marker',
      other: 'pi pi-link'
    }
    return icons[type] || icons.other
  }

  function getRelationshipLabel(type: string): string {
    const labels: Record<string, string> = {
      family: 'Familiar', friend: 'Amistad', friendship: 'Amistad',
      enemy: 'Enemigo', rival: 'Rival',
      romantic: 'Romántica',
      professional: 'Profesional',
      mentor: 'Mentor', student: 'Estudiante',
      ally: 'Aliado', member_of: 'Miembro de',
      owns: 'Posee', located_in: 'Ubicado en',
      other: 'Otra'
    }
    return labels[type] || type
  }

  // === Opciones para edición ===

  function getEntityTypeOptions(): Array<{ label: string; value: string }> {
    return [
      { label: 'Personaje', value: 'character' },
      { label: 'Lugar', value: 'location' },
      { label: 'Organización', value: 'organization' },
      { label: 'Objeto', value: 'object' },
      { label: 'Evento', value: 'event' },
      { label: 'Concepto', value: 'concept' },
      { label: 'Otro', value: 'other' }
    ]
  }

  function getImportanceEditOptions(): Array<{ label: string; value: string }> {
    return [
      { label: 'Menor', value: 'minor' },
      { label: 'Secundario', value: 'secondary' },
      { label: 'Principal', value: 'main' }
    ]
  }

  function getEntitySheetTitle(type: string): string {
    const titles: Record<string, string> = {
      character: 'Ficha de Personaje', location: 'Ficha de Lugar',
      object: 'Ficha de Objeto', organization: 'Ficha de Organización',
      event: 'Ficha de Evento', concept: 'Ficha de Concepto',
      other: 'Ficha de Entidad'
    }
    return titles[type] || titles.other
  }

  // === Relevancia ===

  function formatRelevance(score: number): string {
    return `${Math.round(score * 100)}%`
  }

  function getRelevanceClass(score: number): string {
    if (score >= 0.5) return 'relevance-high'
    if (score >= 0.2) return 'relevance-medium'
    if (score >= 0.1) return 'relevance-low'
    return 'relevance-very-low'
  }

  return {
    // Existing
    getTypeConfig,
    getImportanceConfig,
    getEntityColor,
    getEntityIcon,
    getEntityLabel,
    formatEntityName,
    getEntityInitials,
    sortEntities,
    groupEntitiesByType,
    filterEntities,
    getAllTypeConfigs,
    getAllImportanceConfigs,

    // PrimeVue severity
    getTypeSeverity,
    getImportanceSeverity,
    getImportanceBadgeSeverity,
    getImportanceLabel,

    // Extended colors
    getTypeBackgroundColor,
    getTypeTextColor,

    // Relationships
    getRelationshipIcon,
    getRelationshipLabel,

    // Edit options
    getEntityTypeOptions,
    getImportanceEditOptions,
    getEntitySheetTitle,

    // Relevance
    formatRelevance,
    getRelevanceClass,
  }
}
