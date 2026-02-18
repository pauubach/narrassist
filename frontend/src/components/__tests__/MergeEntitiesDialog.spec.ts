/**
 * Tests para MergeEntitiesDialog - lógica pura de fusión de entidades
 *
 * Testea todas las funciones puras y lógica de negocio del diálogo:
 * - Selección y toggle de entidades
 * - Filtrado con búsqueda
 * - Cálculo de nombres disponibles (canónicos + aliases)
 * - Selección automática de nombre principal (scoreProperName)
 * - Resolución de tipo de entidad resultante
 * - Cálculo de aliases, menciones, validación de pasos
 * - Helpers de UI (colores, labels, severities)
 * - Helpers de conflictos de atributos
 */


// ── Entity Mock Helper ──────────────────────────────────────

interface MockEntity {
  id: number
  projectId: number
  type: string
  name: string
  aliases: string[]
  importance: string
  mentionCount: number
  isActive: boolean
  mergedFromIds: number[]
}

function makeEntity(overrides: Partial<MockEntity> & { id: number; name: string }): MockEntity {
  return {
    projectId: 1,
    type: 'CHARACTER',
    aliases: [],
    importance: 'primary',
    mentionCount: 10,
    isActive: true,
    mergedFromIds: [],
    ...overrides,
  }
}

// ── Pure functions extracted from MergeEntitiesDialog ────────

// Entity selection
function toggleEntity(selectedIds: Set<number>, entityId: number): Set<number> {
  const next = new Set(selectedIds)
  if (next.has(entityId)) {
    next.delete(entityId)
  } else {
    next.add(entityId)
  }
  return next
}

function removeEntity(selectedIds: Set<number>, entityId: number): Set<number> {
  const next = new Set(selectedIds)
  next.delete(entityId)
  return next
}

// Search filter
function filterEntities(entities: MockEntity[], query: string): MockEntity[] {
  if (!query) return entities
  const q = query.toLowerCase()
  return entities.filter(e =>
    e.name.toLowerCase().includes(q) ||
    e.aliases?.some((a: string) => a.toLowerCase().includes(q))
  )
}

// Available names (canonical + aliases, sorted)
interface AvailableName {
  value: string
  entityId: number
  entityType: string
  sourceEntityName: string
  isCanonical: boolean
}

function getAllAvailableNames(selectedEntities: MockEntity[]): AvailableName[] {
  const names: AvailableName[] = []
  selectedEntities.forEach(entity => {
    names.push({
      value: entity.name,
      entityId: entity.id,
      entityType: entity.type,
      sourceEntityName: entity.name,
      isCanonical: true,
    })
    if (entity.aliases) {
      entity.aliases.forEach((alias: string) => {
        names.push({
          value: alias,
          entityId: entity.id,
          entityType: entity.type,
          sourceEntityName: entity.name,
          isCanonical: false,
        })
      })
    }
  })
  return names.sort((a, b) => {
    if (a.isCanonical !== b.isCanonical) return a.isCanonical ? -1 : 1
    return b.value.length - a.value.length
  })
}

// Result entity type (by highest mention count)
function getResultEntityType(selectedEntities: MockEntity[]): string {
  if (selectedEntities.length === 0) return ''
  const sorted = [...selectedEntities].sort(
    (a, b) => (b.mentionCount || 0) - (a.mentionCount || 0)
  )
  return sorted[0]?.type || ''
}

// Result aliases (all names except primary)
function getResultAliases(allNames: AvailableName[], primaryName: string | null): string[] {
  if (!primaryName) return []
  return allNames.map(n => n.value).filter(name => name !== primaryName)
}

// Total mentions
function getTotalMentions(selectedEntities: MockEntity[]): number {
  return selectedEntities.reduce((sum, e) => sum + (e.mentionCount || 0), 0)
}

// Step validation
function canProceed(step: number, selectedCount: number, primaryName: string | null): boolean {
  if (step === 1) return selectedCount >= 2
  if (step === 2) return primaryName !== null
  return true
}

// Name scoring algorithm (extracted from nextStep)
function scoreProperName(name: string): number {
  let score = 0
  const words = name.split(' ')

  if (words.length <= 3) score += 20
  if (words.length === 1 || words.length === 2) score += 10

  if (name[0] === name[0].toUpperCase() && name[0] !== name[0].toLowerCase()) {
    score += 30
  }

  const firstWord = words[0]?.toLowerCase()
  if (['el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas'].includes(firstWord)) {
    score -= 50
  }

  const descriptiveWords = ['morena', 'moreno', 'rubia', 'rubio', 'alta', 'alto', 'vieja', 'viejo', 'joven', 'vestido', 'rojo', 'azul', 'verde']
  if (descriptiveWords.some(w => name.toLowerCase().includes(w))) {
    score -= 30
  }

  if (words.length === 2 && words.every(w => w[0] === w[0].toUpperCase())) {
    score += 40
  }

  return score
}

// Select best canonical name
function selectBestCanonicalName(allNames: AvailableName[]): string | null {
  const canonicalNames = allNames.filter(n => n.isCanonical)
  if (canonicalNames.length === 0) return null
  const sorted = [...canonicalNames].sort((a, b) => scoreProperName(b.value) - scoreProperName(a.value))
  return sorted[0].value
}

// UI helpers
function getSimilarityColor(similarity: number): string {
  if (similarity >= 0.7) return 'var(--green-500)'
  if (similarity >= 0.5) return 'var(--yellow-500)'
  if (similarity >= 0.3) return 'var(--orange-500)'
  return 'var(--ds-color-danger, #ef4444)'
}

function getRecommendationText(recommendation: string): string {
  const texts: Record<string, string> = {
    'merge': 'Recomendado fusionar',
    'review': 'Revisar antes de fusionar',
    'keep_separate': 'Mantener separadas',
  }
  return texts[recommendation] || recommendation
}

function getRecommendationSeverity(recommendation: string): string {
  const severities: Record<string, string> = {
    'merge': 'success',
    'review': 'warning',
    'keep_separate': 'danger',
  }
  return severities[recommendation] || 'secondary'
}

function getEntityIcon(type: string): string {
  const icons: Record<string, string> = {
    'CHARACTER': 'pi pi-user',
    'LOCATION': 'pi pi-map-marker',
    'ORGANIZATION': 'pi pi-building',
    'OBJECT': 'pi pi-box',
    'EVENT': 'pi pi-calendar',
  }
  return icons[type] || 'pi pi-tag'
}

function getTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    'CHARACTER': 'Personaje',
    'LOCATION': 'Lugar',
    'ORGANIZATION': 'Organización',
    'OBJECT': 'Objeto',
    'EVENT': 'Evento',
  }
  return labels[type] || type
}

function getTypeSeverity(type: string): string {
  const severities: Record<string, string> = {
    'CHARACTER': 'success',
    'LOCATION': 'danger',
    'ORGANIZATION': 'info',
    'OBJECT': 'warning',
    'EVENT': 'secondary',
  }
  return severities[type] || 'secondary'
}

function getProgressBarClass(score: number): string {
  if (score >= 0.7) return 'progress-high'
  if (score >= 0.5) return 'progress-medium'
  if (score >= 0.3) return 'progress-low'
  return 'progress-very-low'
}

function getConflictSeverityLabel(severity: string): string {
  const labels: Record<string, string> = {
    'high': 'Critico',
    'medium': 'Medio',
    'low': 'Bajo',
  }
  return labels[severity] || severity
}

function getConflictSeverityColor(severity: string): string {
  const severities: Record<string, string> = {
    'high': 'danger',
    'medium': 'warning',
    'low': 'secondary',
  }
  return severities[severity] || 'secondary'
}

function getConflictCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    'physical': 'Fisico',
    'identity': 'Identidad',
    'personality': 'Personalidad',
    'relationship': 'Relacion',
    'background': 'Trasfondo',
    'ability': 'Habilidad',
    'possession': 'Posesion',
  }
  return labels[category] || category
}

// ── Test Data ───────────────────────────────────────────────

const ENTITIES: MockEntity[] = [
  makeEntity({ id: 1, name: 'Pedro García', type: 'CHARACTER', mentionCount: 45, aliases: ['Pedrito', 'Don Pedro'] }),
  makeEntity({ id: 2, name: 'Pedro', type: 'CHARACTER', mentionCount: 12, aliases: [] }),
  makeEntity({ id: 3, name: 'María López', type: 'CHARACTER', mentionCount: 30, aliases: ['Marilópez'] }),
  makeEntity({ id: 4, name: 'Madrid', type: 'LOCATION', mentionCount: 20, aliases: ['Villa y Corte'] }),
  makeEntity({ id: 5, name: 'La morena del bar', type: 'CHARACTER', mentionCount: 3, aliases: [] }),
  makeEntity({ id: 6, name: 'ACME Corp', type: 'ORGANIZATION', mentionCount: 8, aliases: ['ACME'] }),
]

// ── Tests ───────────────────────────────────────────────────

describe('MergeEntitiesDialog: entity selection', () => {
  it('should add entity to selection', () => {
    const ids = toggleEntity(new Set(), 1)
    expect(ids.has(1)).toBe(true)
    expect(ids.size).toBe(1)
  })

  it('should remove entity from selection on second toggle', () => {
    const ids = toggleEntity(new Set([1]), 1)
    expect(ids.has(1)).toBe(false)
    expect(ids.size).toBe(0)
  })

  it('should add multiple entities', () => {
    let ids = new Set<number>()
    ids = toggleEntity(ids, 1)
    ids = toggleEntity(ids, 3)
    ids = toggleEntity(ids, 4)
    expect(ids.size).toBe(3)
    expect(ids.has(1)).toBe(true)
    expect(ids.has(3)).toBe(true)
    expect(ids.has(4)).toBe(true)
  })

  it('should remove specific entity', () => {
    const ids = removeEntity(new Set([1, 2, 3]), 2)
    expect(ids.size).toBe(2)
    expect(ids.has(2)).toBe(false)
    expect(ids.has(1)).toBe(true)
    expect(ids.has(3)).toBe(true)
  })

  it('should handle removing non-existent entity gracefully', () => {
    const ids = removeEntity(new Set([1]), 99)
    expect(ids.size).toBe(1)
    expect(ids.has(1)).toBe(true)
  })
})

describe('MergeEntitiesDialog: search filtering', () => {
  it('should return all entities when query is empty', () => {
    expect(filterEntities(ENTITIES, '')).toHaveLength(ENTITIES.length)
  })

  it('should filter by name (case insensitive)', () => {
    const result = filterEntities(ENTITIES, 'pedro')
    expect(result).toHaveLength(2) // Pedro García, Pedro
    expect(result.map(e => e.name)).toContain('Pedro García')
    expect(result.map(e => e.name)).toContain('Pedro')
  })

  it('should filter by alias', () => {
    const result = filterEntities(ENTITIES, 'pedrito')
    expect(result).toHaveLength(1)
    expect(result[0].name).toBe('Pedro García')
  })

  it('should match partial strings', () => {
    const result = filterEntities(ENTITIES, 'mar')
    // "mar" matches: María López (name "maría" contains "mar"), Marilópez (alias) → same entity
    // "madrid" does NOT contain "mar" (m-a-d-r-i-d)
    expect(result).toHaveLength(1)
    expect(result[0].name).toBe('María López')
  })

  it('should return empty when no match', () => {
    expect(filterEntities(ENTITIES, 'zzzzz')).toHaveLength(0)
  })

  it('should match alias "Villa y Corte"', () => {
    const result = filterEntities(ENTITIES, 'villa')
    expect(result).toHaveLength(1)
    expect(result[0].name).toBe('Madrid')
  })
})

describe('MergeEntitiesDialog: allAvailableNames', () => {
  it('should include canonical names and aliases', () => {
    const selected = [ENTITIES[0], ENTITIES[1]] // Pedro García (+ Pedrito, Don Pedro), Pedro
    const names = getAllAvailableNames(selected)

    expect(names.map(n => n.value)).toContain('Pedro García')
    expect(names.map(n => n.value)).toContain('Pedrito')
    expect(names.map(n => n.value)).toContain('Don Pedro')
    expect(names.map(n => n.value)).toContain('Pedro')
  })

  it('should sort canonical names first', () => {
    const selected = [ENTITIES[0]] // Pedro García (+ Pedrito, Don Pedro)
    const names = getAllAvailableNames(selected)

    const firstCanonical = names.findIndex(n => n.isCanonical)
    const firstAlias = names.findIndex(n => !n.isCanonical)
    expect(firstCanonical).toBeLessThan(firstAlias)
  })

  it('should sort by length within each group (longer first)', () => {
    const selected = [ENTITIES[0], ENTITIES[1]]
    const names = getAllAvailableNames(selected)

    // Among canonical names, Pedro García (12 chars) before Pedro (5 chars)
    const canonicals = names.filter(n => n.isCanonical)
    expect(canonicals[0].value).toBe('Pedro García')
    expect(canonicals[1].value).toBe('Pedro')
  })

  it('should mark canonical vs alias correctly', () => {
    const selected = [ENTITIES[0]]
    const names = getAllAvailableNames(selected)

    const canonical = names.find(n => n.value === 'Pedro García')
    expect(canonical?.isCanonical).toBe(true)

    const alias = names.find(n => n.value === 'Pedrito')
    expect(alias?.isCanonical).toBe(false)
  })

  it('should track source entity for each name', () => {
    const selected = [ENTITIES[0], ENTITIES[2]] // Pedro García, María López
    const names = getAllAvailableNames(selected)

    const pedrito = names.find(n => n.value === 'Pedrito')
    expect(pedrito?.sourceEntityName).toBe('Pedro García')

    const marilopez = names.find(n => n.value === 'Marilópez')
    expect(marilopez?.sourceEntityName).toBe('María López')
  })

  it('should return empty for no entities', () => {
    expect(getAllAvailableNames([])).toHaveLength(0)
  })
})

describe('MergeEntitiesDialog: resultEntityType', () => {
  it('should return type of entity with most mentions', () => {
    const selected = [ENTITIES[0], ENTITIES[3]] // Pedro García (45), Madrid (20)
    expect(getResultEntityType(selected)).toBe('CHARACTER')
  })

  it('should prefer higher mention count regardless of type', () => {
    const entities = [
      makeEntity({ id: 10, name: 'Test Loc', type: 'LOCATION', mentionCount: 100 }),
      makeEntity({ id: 11, name: 'Test Char', type: 'CHARACTER', mentionCount: 5 }),
    ]
    expect(getResultEntityType(entities)).toBe('LOCATION')
  })

  it('should return empty string for no entities', () => {
    expect(getResultEntityType([])).toBe('')
  })
})

describe('MergeEntitiesDialog: resultAliases', () => {
  it('should return all names except primary', () => {
    const names = getAllAvailableNames([ENTITIES[0], ENTITIES[1]])
    const aliases = getResultAliases(names, 'Pedro García')

    expect(aliases).toContain('Pedro')
    expect(aliases).toContain('Pedrito')
    expect(aliases).toContain('Don Pedro')
    expect(aliases).not.toContain('Pedro García')
  })

  it('should return empty when no primary name', () => {
    const names = getAllAvailableNames([ENTITIES[0]])
    expect(getResultAliases(names, null)).toHaveLength(0)
  })

  it('should work when selecting an alias as primary', () => {
    const names = getAllAvailableNames([ENTITIES[0]])
    const aliases = getResultAliases(names, 'Pedrito')

    expect(aliases).toContain('Pedro García')
    expect(aliases).toContain('Don Pedro')
    expect(aliases).not.toContain('Pedrito')
  })
})

describe('MergeEntitiesDialog: totalMentions', () => {
  it('should sum all mention counts', () => {
    const selected = [ENTITIES[0], ENTITIES[1], ENTITIES[2]] // 45 + 12 + 30
    expect(getTotalMentions(selected)).toBe(87)
  })

  it('should handle entities with 0 mentions', () => {
    const entities = [
      makeEntity({ id: 10, name: 'A', mentionCount: 0 }),
      makeEntity({ id: 11, name: 'B', mentionCount: 5 }),
    ]
    expect(getTotalMentions(entities)).toBe(5)
  })

  it('should return 0 for empty selection', () => {
    expect(getTotalMentions([])).toBe(0)
  })
})

describe('MergeEntitiesDialog: canProceed (step validation)', () => {
  it('step 1: requires at least 2 selected entities', () => {
    expect(canProceed(1, 0, null)).toBe(false)
    expect(canProceed(1, 1, null)).toBe(false)
    expect(canProceed(1, 2, null)).toBe(true)
    expect(canProceed(1, 5, null)).toBe(true)
  })

  it('step 2: requires a primary name selected', () => {
    expect(canProceed(2, 2, null)).toBe(false)
    expect(canProceed(2, 2, 'Pedro García')).toBe(true)
  })

  it('step 3: always allows (confirmation step)', () => {
    expect(canProceed(3, 2, 'Pedro')).toBe(true)
    expect(canProceed(3, 0, null)).toBe(true)
  })
})

describe('MergeEntitiesDialog: scoreProperName', () => {
  it('should prefer proper names over descriptions', () => {
    expect(scoreProperName('Pedro García')).toBeGreaterThan(scoreProperName('La morena del bar'))
  })

  it('should prefer names starting with uppercase', () => {
    expect(scoreProperName('Juan')).toBeGreaterThan(scoreProperName('juan'))
  })

  it('should penalize names starting with articles', () => {
    expect(scoreProperName('El viejo')).toBeLessThan(scoreProperName('Miguel'))
    expect(scoreProperName('La mujer')).toBeLessThan(scoreProperName('Ana'))
    expect(scoreProperName('Un extraño')).toBeLessThan(scoreProperName('Carlos'))
  })

  it('should penalize descriptive adjectives', () => {
    expect(scoreProperName('La morena')).toBeLessThan(scoreProperName('Lucía'))
    expect(scoreProperName('El rubio')).toBeLessThan(scoreProperName('Pablo'))
  })

  it('should bonify two-word capitalized names (Nombre Apellido)', () => {
    const twoWord = scoreProperName('Pedro García')
    const oneWord = scoreProperName('Pedro')
    expect(twoWord).toBeGreaterThan(oneWord)
  })

  it('should penalize long descriptions', () => {
    expect(scoreProperName('La mujer alta morena del vestido rojo')).toBeLessThan(scoreProperName('Ana'))
  })

  it('should handle edge cases', () => {
    expect(scoreProperName('A')).toBeGreaterThan(-100) // single letter
    expect(scoreProperName('123')).toBeDefined()
  })
})

describe('MergeEntitiesDialog: selectBestCanonicalName', () => {
  it('should prefer "Pedro García" over "Pedro"', () => {
    const names = getAllAvailableNames([ENTITIES[0], ENTITIES[1]])
    expect(selectBestCanonicalName(names)).toBe('Pedro García')
  })

  it('should prefer proper name over description', () => {
    const names = getAllAvailableNames([ENTITIES[0], ENTITIES[4]])
    // Pedro García (proper name) vs "La morena del bar" (description)
    expect(selectBestCanonicalName(names)).toBe('Pedro García')
  })

  it('should return null for empty names', () => {
    expect(selectBestCanonicalName([])).toBeNull()
  })

  it('should handle single entity', () => {
    const names = getAllAvailableNames([ENTITIES[2]])
    expect(selectBestCanonicalName(names)).toBe('María López')
  })
})

describe('MergeEntitiesDialog: getSimilarityColor', () => {
  it('should return green for high similarity (>=0.7)', () => {
    expect(getSimilarityColor(0.7)).toBe('var(--green-500)')
    expect(getSimilarityColor(0.95)).toBe('var(--green-500)')
    expect(getSimilarityColor(1.0)).toBe('var(--green-500)')
  })

  it('should return yellow for medium similarity (0.5-0.7)', () => {
    expect(getSimilarityColor(0.5)).toBe('var(--yellow-500)')
    expect(getSimilarityColor(0.65)).toBe('var(--yellow-500)')
  })

  it('should return orange for low similarity (0.3-0.5)', () => {
    expect(getSimilarityColor(0.3)).toBe('var(--orange-500)')
    expect(getSimilarityColor(0.45)).toBe('var(--orange-500)')
  })

  it('should return red for very low similarity (<0.3)', () => {
    expect(getSimilarityColor(0.0)).toBe('var(--ds-color-danger, #ef4444)')
    expect(getSimilarityColor(0.29)).toBe('var(--ds-color-danger, #ef4444)')
  })
})

describe('MergeEntitiesDialog: getProgressBarClass', () => {
  it('should map score ranges to CSS classes', () => {
    expect(getProgressBarClass(0.8)).toBe('progress-high')
    expect(getProgressBarClass(0.6)).toBe('progress-medium')
    expect(getProgressBarClass(0.4)).toBe('progress-low')
    expect(getProgressBarClass(0.1)).toBe('progress-very-low')
  })

  it('should handle boundary values', () => {
    expect(getProgressBarClass(0.7)).toBe('progress-high')
    expect(getProgressBarClass(0.5)).toBe('progress-medium')
    expect(getProgressBarClass(0.3)).toBe('progress-low')
    expect(getProgressBarClass(0.0)).toBe('progress-very-low')
  })
})

describe('MergeEntitiesDialog: recommendation helpers', () => {
  it('should map recommendation to text', () => {
    expect(getRecommendationText('merge')).toBe('Recomendado fusionar')
    expect(getRecommendationText('review')).toBe('Revisar antes de fusionar')
    expect(getRecommendationText('keep_separate')).toBe('Mantener separadas')
  })

  it('should return raw value for unknown recommendation', () => {
    expect(getRecommendationText('unknown')).toBe('unknown')
  })

  it('should map recommendation to severity', () => {
    expect(getRecommendationSeverity('merge')).toBe('success')
    expect(getRecommendationSeverity('review')).toBe('warning')
    expect(getRecommendationSeverity('keep_separate')).toBe('danger')
  })

  it('should return secondary for unknown severity', () => {
    expect(getRecommendationSeverity('unknown')).toBe('secondary')
  })
})

describe('MergeEntitiesDialog: entity icon/type helpers', () => {
  it('should return correct icons for all entity types', () => {
    expect(getEntityIcon('CHARACTER')).toBe('pi pi-user')
    expect(getEntityIcon('LOCATION')).toBe('pi pi-map-marker')
    expect(getEntityIcon('ORGANIZATION')).toBe('pi pi-building')
    expect(getEntityIcon('OBJECT')).toBe('pi pi-box')
    expect(getEntityIcon('EVENT')).toBe('pi pi-calendar')
  })

  it('should return default icon for unknown type', () => {
    expect(getEntityIcon('UNKNOWN')).toBe('pi pi-tag')
  })

  it('should return correct labels in Spanish', () => {
    expect(getTypeLabel('CHARACTER')).toBe('Personaje')
    expect(getTypeLabel('LOCATION')).toBe('Lugar')
    expect(getTypeLabel('ORGANIZATION')).toBe('Organización')
    expect(getTypeLabel('OBJECT')).toBe('Objeto')
    expect(getTypeLabel('EVENT')).toBe('Evento')
  })

  it('should return raw type for unknown label', () => {
    expect(getTypeLabel('UNKNOWN')).toBe('UNKNOWN')
  })

  it('should return correct severities for Tag component', () => {
    expect(getTypeSeverity('CHARACTER')).toBe('success')
    expect(getTypeSeverity('LOCATION')).toBe('danger')
    expect(getTypeSeverity('ORGANIZATION')).toBe('info')
    expect(getTypeSeverity('OBJECT')).toBe('warning')
    expect(getTypeSeverity('EVENT')).toBe('secondary')
  })

  it('should return secondary for unknown type severity', () => {
    expect(getTypeSeverity('UNKNOWN')).toBe('secondary')
  })
})

describe('MergeEntitiesDialog: conflict helpers', () => {
  it('should map conflict severity to labels', () => {
    expect(getConflictSeverityLabel('high')).toBe('Critico')
    expect(getConflictSeverityLabel('medium')).toBe('Medio')
    expect(getConflictSeverityLabel('low')).toBe('Bajo')
    expect(getConflictSeverityLabel('unknown')).toBe('unknown')
  })

  it('should map conflict severity to colors', () => {
    expect(getConflictSeverityColor('high')).toBe('danger')
    expect(getConflictSeverityColor('medium')).toBe('warning')
    expect(getConflictSeverityColor('low')).toBe('secondary')
    expect(getConflictSeverityColor('unknown')).toBe('secondary')
  })

  it('should map conflict categories to Spanish labels', () => {
    expect(getConflictCategoryLabel('physical')).toBe('Fisico')
    expect(getConflictCategoryLabel('identity')).toBe('Identidad')
    expect(getConflictCategoryLabel('personality')).toBe('Personalidad')
    expect(getConflictCategoryLabel('relationship')).toBe('Relacion')
    expect(getConflictCategoryLabel('background')).toBe('Trasfondo')
    expect(getConflictCategoryLabel('ability')).toBe('Habilidad')
    expect(getConflictCategoryLabel('possession')).toBe('Posesion')
  })

  it('should return raw category for unknown', () => {
    expect(getConflictCategoryLabel('magical_power')).toBe('magical_power')
  })
})

describe('MergeEntitiesDialog: end-to-end merge workflow', () => {
  it('should simulate full 3-step merge flow', () => {
    // Step 1: Select Pedro García and Pedro
    let selectedIds = new Set<number>()
    selectedIds = toggleEntity(selectedIds, 1)
    selectedIds = toggleEntity(selectedIds, 2)
    expect(canProceed(1, selectedIds.size, null)).toBe(true)

    // Get selected entities
    const selectedEntities = ENTITIES.filter(e => selectedIds.has(e.id))
    expect(selectedEntities).toHaveLength(2)

    // Step 2: Get available names and auto-select best
    const names = getAllAvailableNames(selectedEntities)
    expect(names.length).toBe(4) // Pedro García, Pedro, Pedrito, Don Pedro

    const bestName = selectBestCanonicalName(names)
    expect(bestName).toBe('Pedro García')
    expect(canProceed(2, selectedIds.size, bestName)).toBe(true)

    // Step 3: Verify merge preview data
    const resultType = getResultEntityType(selectedEntities)
    expect(resultType).toBe('CHARACTER')

    const aliases = getResultAliases(names, bestName)
    expect(aliases).toContain('Pedro')
    expect(aliases).toContain('Pedrito')
    expect(aliases).toContain('Don Pedro')
    expect(aliases).toHaveLength(3)

    const totalMentions = getTotalMentions(selectedEntities)
    expect(totalMentions).toBe(57) // 45 + 12

    expect(canProceed(3, selectedIds.size, bestName)).toBe(true)
  })

  it('should handle cross-type merge (CHARACTER + LOCATION)', () => {
    let selectedIds = new Set<number>()
    selectedIds = toggleEntity(selectedIds, 1) // Pedro García (45 mentions)
    selectedIds = toggleEntity(selectedIds, 4) // Madrid (20 mentions)

    const selectedEntities = ENTITIES.filter(e => selectedIds.has(e.id))
    const resultType = getResultEntityType(selectedEntities)

    // Pedro García has more mentions → CHARACTER wins
    expect(resultType).toBe('CHARACTER')

    const names = getAllAvailableNames(selectedEntities)
    expect(names.map(n => n.value)).toContain('Pedro García')
    expect(names.map(n => n.value)).toContain('Madrid')
    expect(names.map(n => n.value)).toContain('Villa y Corte')
  })
})
