/**
 * Tests para EntitiesTab - lógica de filtrado, ordenamiento y estadísticas
 *
 * Testea las funciones puras de filtrado y cálculo sin montar el componente
 * (evita dependencias de PrimeVue, router, stores, etc.)
 */


// ── Mock Entity ─────────────────────────────────────────────

interface MockEntity {
  id: number
  name: string
  type: string
  importance: string
  aliases: string[]
  mentionCount: number
  relevanceScore?: number
  isActive: boolean
}

function makeEntity(overrides: Partial<MockEntity> & { id: number; name: string }): MockEntity {
  return {
    type: 'character',
    importance: 'main',
    aliases: [],
    mentionCount: 10,
    isActive: true,
    ...overrides,
  }
}

// ── Pure functions extracted from EntitiesTab ────────────────

const RELEVANCE_THRESHOLD = 0.1

function filterEntities(
  entities: MockEntity[],
  searchQuery: string,
  selectedType: string | null,
  selectedImportance: string | null,
  showOnlyRelevant: boolean,
): MockEntity[] {
  let result = entities

  if (searchQuery) {
    const query = searchQuery.toLowerCase()
    result = result.filter(e =>
      e.name.toLowerCase().includes(query) ||
      e.aliases?.some(a => a.toLowerCase().includes(query))
    )
  }

  if (selectedType) {
    result = result.filter(e => e.type === selectedType)
  }

  if (selectedImportance) {
    result = result.filter(e => e.importance === selectedImportance)
  }

  if (showOnlyRelevant) {
    result = result.filter(e => (e.relevanceScore ?? 0) >= RELEVANCE_THRESHOLD)
  }

  return [...result].sort((a, b) => (b.mentionCount || 0) - (a.mentionCount || 0))
}

function getLowRelevanceCount(entities: MockEntity[]): number {
  return entities.filter(e => (e.relevanceScore ?? 0) < RELEVANCE_THRESHOLD).length
}

function getStats(entities: MockEntity[], filteredEntities: MockEntity[]) {
  return {
    total: entities.length,
    filtered: filteredEntities.length,
    characters: entities.filter(e => e.type === 'character').length,
    locations: entities.filter(e => e.type === 'location').length,
    organizations: entities.filter(e => e.type === 'organization').length,
  }
}

function getTypeOptions(entities: MockEntity[]) {
  const types = new Set(entities.map(e => e.type))
  return [
    { label: 'Todos los tipos', value: null },
    ...Array.from(types).map(type => ({
      label: type, // Simplified - in real code uses getEntityLabel()
      value: type,
    })),
  ]
}

// ── Test Data ───────────────────────────────────────────────

const ENTITIES: MockEntity[] = [
  makeEntity({ id: 1, name: 'Pedro García', type: 'character', importance: 'main', mentionCount: 50, relevanceScore: 0.9, aliases: ['Pedrito'] }),
  makeEntity({ id: 2, name: 'María López', type: 'character', importance: 'secondary', mentionCount: 30, relevanceScore: 0.7, aliases: ['Marilópez'] }),
  makeEntity({ id: 3, name: 'Juan', type: 'character', importance: 'minor', mentionCount: 5, relevanceScore: 0.05, aliases: [] }),
  makeEntity({ id: 4, name: 'Madrid', type: 'location', importance: 'main', mentionCount: 25, relevanceScore: 0.6, aliases: ['Villa y Corte'] }),
  makeEntity({ id: 5, name: 'Barcelona', type: 'location', importance: 'secondary', mentionCount: 15, relevanceScore: 0.3, aliases: [] }),
  makeEntity({ id: 6, name: 'ACME Corp', type: 'organization', importance: 'minor', mentionCount: 8, relevanceScore: 0.08, aliases: ['ACME'] }),
  makeEntity({ id: 7, name: 'El misterioso', type: 'character', importance: 'minor', mentionCount: 2, relevanceScore: 0.02, aliases: [] }),
]

// ── Tests ───────────────────────────────────────────────────

describe('EntitiesTab: search filtering', () => {
  it('should return all entities when no filters applied', () => {
    const result = filterEntities(ENTITIES, '', null, null, false)
    expect(result).toHaveLength(ENTITIES.length)
  })

  it('should filter by name (case insensitive)', () => {
    const result = filterEntities(ENTITIES, 'pedro', null, null, false)
    expect(result).toHaveLength(1)
    expect(result[0].name).toBe('Pedro García')
  })

  it('should filter by alias', () => {
    const result = filterEntities(ENTITIES, 'pedrito', null, null, false)
    expect(result).toHaveLength(1)
    expect(result[0].name).toBe('Pedro García')
  })

  it('should filter by alias "Villa y Corte"', () => {
    const result = filterEntities(ENTITIES, 'villa', null, null, false)
    expect(result).toHaveLength(1)
    expect(result[0].name).toBe('Madrid')
  })

  it('should match partial strings', () => {
    const result = filterEntities(ENTITIES, 'arc', null, null, false)
    // "arc" matches: Pedro García (name "garcía" contains "arc"), Barcelona ("barcelona" contains "arc")
    expect(result).toHaveLength(2)
    expect(result.map(e => e.name)).toContain('Pedro García')
    expect(result.map(e => e.name)).toContain('Barcelona')
  })

  it('should return empty for no match', () => {
    const result = filterEntities(ENTITIES, 'zzzzz', null, null, false)
    expect(result).toHaveLength(0)
  })

  it('should match ACME alias', () => {
    const result = filterEntities(ENTITIES, 'acme', null, null, false)
    expect(result).toHaveLength(1)
    expect(result[0].name).toBe('ACME Corp')
  })
})

describe('EntitiesTab: type filtering', () => {
  it('should filter characters only', () => {
    const result = filterEntities(ENTITIES, '', 'character', null, false)
    expect(result.every(e => e.type === 'character')).toBe(true)
    expect(result).toHaveLength(4) // Pedro, María, Juan, El misterioso
  })

  it('should filter locations only', () => {
    const result = filterEntities(ENTITIES, '', 'location', null, false)
    expect(result.every(e => e.type === 'location')).toBe(true)
    expect(result).toHaveLength(2) // Madrid, Barcelona
  })

  it('should filter organizations only', () => {
    const result = filterEntities(ENTITIES, '', 'organization', null, false)
    expect(result).toHaveLength(1)
    expect(result[0].name).toBe('ACME Corp')
  })

  it('should return empty for non-existent type', () => {
    const result = filterEntities(ENTITIES, '', 'event', null, false)
    expect(result).toHaveLength(0)
  })
})

describe('EntitiesTab: importance filtering', () => {
  it('should filter main importance only', () => {
    const result = filterEntities(ENTITIES, '', null, 'main', false)
    expect(result.every(e => e.importance === 'main')).toBe(true)
    expect(result).toHaveLength(2) // Pedro García, Madrid
  })

  it('should filter secondary importance only', () => {
    const result = filterEntities(ENTITIES, '', null, 'secondary', false)
    expect(result.every(e => e.importance === 'secondary')).toBe(true)
    expect(result).toHaveLength(2) // María, Barcelona
  })

  it('should filter minor importance only', () => {
    const result = filterEntities(ENTITIES, '', null, 'minor', false)
    expect(result.every(e => e.importance === 'minor')).toBe(true)
    expect(result).toHaveLength(3) // Juan, ACME Corp, El misterioso
  })
})

describe('EntitiesTab: relevance filtering', () => {
  it('should hide low-relevance entities when toggle is on', () => {
    const result = filterEntities(ENTITIES, '', null, null, true)
    // Entities with relevanceScore >= 0.1: Pedro (0.9), María (0.7), Madrid (0.6), Barcelona (0.3)
    // Excluded: Juan (0.05), ACME (0.08), El misterioso (0.02)
    expect(result).toHaveLength(4)
    expect(result.map(e => e.name)).not.toContain('Juan')
    expect(result.map(e => e.name)).not.toContain('ACME Corp')
    expect(result.map(e => e.name)).not.toContain('El misterioso')
  })

  it('should include all when toggle is off', () => {
    const result = filterEntities(ENTITIES, '', null, null, false)
    expect(result).toHaveLength(ENTITIES.length)
  })

  it('should treat undefined relevanceScore as 0', () => {
    const entities = [
      makeEntity({ id: 10, name: 'No Score', relevanceScore: undefined }),
    ]
    const result = filterEntities(entities, '', null, null, true)
    expect(result).toHaveLength(0) // 0 < 0.1
  })
})

describe('EntitiesTab: combined filters', () => {
  it('should combine search + type', () => {
    const result = filterEntities(ENTITIES, 'ma', 'location', null, false)
    // "ma" + location: Madrid matches
    expect(result).toHaveLength(1)
    expect(result[0].name).toBe('Madrid')
  })

  it('should combine search + importance', () => {
    const result = filterEntities(ENTITIES, 'mar', null, 'secondary', false)
    // "mar" matches María López (secondary) → 1 result
    expect(result).toHaveLength(1)
    expect(result[0].name).toBe('María López')
  })

  it('should combine type + importance', () => {
    const result = filterEntities(ENTITIES, '', 'character', 'main', false)
    // character + main: Pedro García
    expect(result).toHaveLength(1)
    expect(result[0].name).toBe('Pedro García')
  })

  it('should combine all filters', () => {
    const result = filterEntities(ENTITIES, 'pedro', 'character', 'main', true)
    expect(result).toHaveLength(1)
    expect(result[0].name).toBe('Pedro García')
  })

  it('should return empty when filters conflict', () => {
    const result = filterEntities(ENTITIES, 'pedro', 'location', null, false)
    // Pedro is a character, not a location
    expect(result).toHaveLength(0)
  })
})

describe('EntitiesTab: sorting', () => {
  it('should sort by mentionCount descending', () => {
    const result = filterEntities(ENTITIES, '', null, null, false)
    for (let i = 1; i < result.length; i++) {
      expect(result[i - 1].mentionCount).toBeGreaterThanOrEqual(result[i].mentionCount)
    }
  })

  it('should maintain sort after filtering', () => {
    const result = filterEntities(ENTITIES, '', 'character', null, false)
    // Characters by mention count: Pedro (50), María (30), Juan (5), El misterioso (2)
    expect(result.map(e => e.mentionCount)).toEqual([50, 30, 5, 2])
  })

  it('should handle entities with 0 mentions', () => {
    const entities = [
      makeEntity({ id: 10, name: 'A', mentionCount: 0 }),
      makeEntity({ id: 11, name: 'B', mentionCount: 5 }),
      makeEntity({ id: 12, name: 'C', mentionCount: 0 }),
    ]
    const result = filterEntities(entities, '', null, null, false)
    expect(result[0].name).toBe('B')
  })
})

describe('EntitiesTab: lowRelevanceCount', () => {
  it('should count entities below relevance threshold', () => {
    // Below 0.1: Juan (0.05), ACME (0.08), El misterioso (0.02)
    expect(getLowRelevanceCount(ENTITIES)).toBe(3)
  })

  it('should count 0 when all are relevant', () => {
    const entities = [
      makeEntity({ id: 1, name: 'A', relevanceScore: 0.5 }),
      makeEntity({ id: 2, name: 'B', relevanceScore: 0.9 }),
    ]
    expect(getLowRelevanceCount(entities)).toBe(0)
  })

  it('should treat undefined relevanceScore as 0 (below threshold)', () => {
    const entities = [
      makeEntity({ id: 1, name: 'A', relevanceScore: undefined }),
    ]
    expect(getLowRelevanceCount(entities)).toBe(1)
  })
})

describe('EntitiesTab: stats', () => {
  it('should calculate total and per-type counts', () => {
    const filtered = filterEntities(ENTITIES, '', null, null, false)
    const s = getStats(ENTITIES, filtered)

    expect(s.total).toBe(7)
    expect(s.filtered).toBe(7)
    expect(s.characters).toBe(4)
    expect(s.locations).toBe(2)
    expect(s.organizations).toBe(1)
  })

  it('should reflect filtered count', () => {
    const filtered = filterEntities(ENTITIES, '', 'character', null, false)
    const s = getStats(ENTITIES, filtered)

    expect(s.total).toBe(7) // Total doesn't change
    expect(s.filtered).toBe(4) // Only characters
  })

  it('should handle empty entities', () => {
    const s = getStats([], [])
    expect(s.total).toBe(0)
    expect(s.filtered).toBe(0)
    expect(s.characters).toBe(0)
    expect(s.locations).toBe(0)
    expect(s.organizations).toBe(0)
  })
})

describe('EntitiesTab: typeOptions', () => {
  it('should include "all types" option first', () => {
    const options = getTypeOptions(ENTITIES)
    expect(options[0]).toEqual({ label: 'Todos los tipos', value: null })
  })

  it('should include only types present in data', () => {
    const options = getTypeOptions(ENTITIES)
    const values = options.map(o => o.value).filter(v => v !== null)
    expect(values).toContain('character')
    expect(values).toContain('location')
    expect(values).toContain('organization')
    expect(values).not.toContain('event')
    expect(values).not.toContain('object')
  })

  it('should have unique types (no duplicates)', () => {
    const options = getTypeOptions(ENTITIES)
    const values = options.map(o => o.value).filter(v => v !== null)
    expect(new Set(values).size).toBe(values.length)
  })

  it('should handle empty entities', () => {
    const options = getTypeOptions([])
    expect(options).toHaveLength(1) // Only "all types"
    expect(options[0].value).toBeNull()
  })

  it('should handle single-type entities', () => {
    const entities = [
      makeEntity({ id: 1, name: 'A', type: 'character' }),
      makeEntity({ id: 2, name: 'B', type: 'character' }),
    ]
    const options = getTypeOptions(entities)
    expect(options).toHaveLength(2) // "all types" + "character"
  })
})

describe('EntitiesTab: edge cases', () => {
  it('should handle entity with no aliases', () => {
    const result = filterEntities(
      [makeEntity({ id: 1, name: 'Test', aliases: [] })],
      'test',
      null, null, false
    )
    expect(result).toHaveLength(1)
  })

  it('should handle search with special characters', () => {
    const entities = [
      makeEntity({ id: 1, name: 'García-López' }),
      makeEntity({ id: 2, name: 'O\'Brien' }),
    ]
    const result = filterEntities(entities, 'garcía', null, null, false)
    expect(result).toHaveLength(1)
    expect(result[0].name).toBe('García-López')
  })

  it('should handle whitespace in search', () => {
    const result = filterEntities(ENTITIES, '  ', null, null, false)
    // "  " is truthy but has no matching characters
    expect(result).toHaveLength(0)
  })

  it('should not mutate original array', () => {
    const original = [...ENTITIES]
    filterEntities(ENTITIES, '', null, null, false)
    expect(ENTITIES).toEqual(original)
  })
})
