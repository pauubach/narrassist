/**
 * Configuración unificada de atributos por tipo de entidad.
 *
 * Fuente de verdad compartida entre CharacterSheet y CharacterView.
 */

export interface AttributeSectionConfig {
  categories: string[]
  icon: string
  label: string
}

export const ATTRIBUTE_CONFIG: Record<string, AttributeSectionConfig[]> = {
  character: [
    { categories: ['physical'], icon: 'pi pi-user', label: 'Atributos físicos' },
    { categories: ['psychological'], icon: 'pi pi-comments', label: 'Atributos psicológicos' },
    { categories: ['social'], icon: 'pi pi-users', label: 'Atributos sociales' },
    { categories: ['ability'], icon: 'pi pi-bolt', label: 'Habilidades' },
  ],
  location: [
    { categories: ['geographic'], icon: 'pi pi-map', label: 'Características del lugar' },
    { categories: ['architectural'], icon: 'pi pi-building', label: 'Arquitectura y estado' },
  ],
  object: [
    { categories: ['material'], icon: 'pi pi-box', label: 'Materiales' },
    { categories: ['appearance'], icon: 'pi pi-palette', label: 'Apariencia' },
    { categories: ['state', 'function'], icon: 'pi pi-cog', label: 'Estado y función' },
  ],
  organization: [
    { categories: ['structure'], icon: 'pi pi-sitemap', label: 'Estructura' },
    { categories: ['purpose', 'history'], icon: 'pi pi-flag', label: 'Propósito e historia' },
  ],
  event: [
    { categories: ['temporal'], icon: 'pi pi-calendar', label: 'Información temporal' },
    { categories: ['participants', 'consequences'], icon: 'pi pi-users', label: 'Participantes y consecuencias' },
  ],
  concept: [
    { categories: ['definition'], icon: 'pi pi-book', label: 'Definición' },
    { categories: ['examples', 'related'], icon: 'pi pi-link', label: 'Ejemplos y relaciones' },
  ],
}

const CATEGORY_LABELS: Record<string, string> = {
  physical: 'Físico',
  psychological: 'Psicológico',
  social: 'Social',
  ability: 'Habilidad',
  geographic: 'Geográfico',
  architectural: 'Arquitectónico',
  material: 'Material',
  appearance: 'Apariencia',
  state: 'Estado',
  function: 'Función',
  structure: 'Estructura',
  purpose: 'Propósito',
  history: 'Historia',
  temporal: 'Temporal',
  participants: 'Participantes',
  consequences: 'Consecuencias',
  definition: 'Definición',
  examples: 'Ejemplos',
  related: 'Relacionado',
}

export function getAttributeCategoriesForEntityType(entityType?: string): Array<{ label: string; value: string }> {
  const type = entityType || 'character'
  const sections = ATTRIBUTE_CONFIG[type] || ATTRIBUTE_CONFIG.character

  const seen = new Set<string>()
  const categories: Array<{ label: string; value: string }> = []

  for (const section of sections) {
    for (const category of section.categories) {
      if (seen.has(category)) continue
      seen.add(category)
      categories.push({
        value: category,
        label: CATEGORY_LABELS[category] || category,
      })
    }
  }

  return categories
}
