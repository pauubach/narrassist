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

  return {
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
  }
}
