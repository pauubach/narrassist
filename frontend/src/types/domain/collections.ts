/**
 * Domain Types - Collections / Cross-Book
 *
 * Tipos frontend (camelCase) para colecciones y análisis cross-book.
 */

/** Colección / saga de proyectos */
export interface Collection {
  id: number
  name: string
  description: string
  projectCount: number
  createdAt: Date
}

/** Colección con detalle completo */
export interface CollectionDetail extends Collection {
  projects: CollectionProject[]
  entityLinkCount: number
}

/** Proyecto dentro de una colección */
export interface CollectionProject {
  id: number
  name: string
  orderIndex: number
  wordCount: number
  entityCount: number
  documentFormat: string
}

/** Enlace confirmado entre entidades de distintos libros */
export interface EntityLink {
  id: number
  collectionId: number
  sourceEntityId: number
  targetEntityId: number
  sourceProjectId: number
  targetProjectId: number
  sourceEntityName: string
  targetEntityName: string
  sourceProjectName: string
  targetProjectName: string
  similarity: number
  matchType: string
}

/** Sugerencia de enlace generada por el fuzzy matcher */
export interface LinkSuggestion {
  sourceEntityId: number
  sourceEntityName: string
  sourceEntityType: string
  sourceProjectId: number
  sourceProjectName: string
  targetEntityId: number
  targetEntityName: string
  targetEntityType: string
  targetProjectId: number
  targetProjectName: string
  similarity: number
  matchType: string
}

/** Informe de análisis cross-book */
export interface CrossBookReport {
  collectionId: number
  collectionName: string
  inconsistencies: CrossBookInconsistency[]
  entityLinksAnalyzed: number
  projectsAnalyzed: number
  summary: {
    totalInconsistencies: number
    byType: Record<string, number>
  }
}

/** Inconsistencia detectada entre libros */
export interface CrossBookInconsistency {
  entityName: string
  attributeType: string
  attributeKey: string
  valueBookA: string
  valueBookB: string
  bookAName: string
  bookBName: string
  confidence: number
}

/** Contradicción de eventos entre libros */
export interface EventContradiction {
  rule: string
  entityName: string
  description: string
  eventAType: string
  eventBType: string
  bookAName: string
  bookBName: string
  bookAChapter: number | null
  bookBChapter: number | null
  confidence: number
  metadata: Record<string, unknown>
}

/** Informe de contradicciones de eventos cross-book */
export interface CrossBookEventReport {
  collectionId: number
  collectionName: string
  contradictions: EventContradiction[]
  entityLinksAnalyzed: number
  projectsAnalyzed: number
  summary: {
    totalContradictions: number
    byRule: Record<string, number>
  }
}
