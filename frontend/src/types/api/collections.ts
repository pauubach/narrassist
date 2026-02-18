/**
 * API Types - Collections / Cross-Book (BK-07)
 *
 * Tipos que coinciden con la respuesta del backend.
 * Los endpoints de collections NO usan el wrapper ApiResponse,
 * devuelven directamente estos objetos.
 */

/** Colección en listado */
export interface ApiCollection {
  id: number
  name: string
  description: string
  project_count: number
  created_at: string
}

/** Colección con detalle completo */
export interface ApiCollectionDetail extends ApiCollection {
  projects: ApiCollectionProject[]
  entity_link_count: number
}

/** Proyecto dentro de una colección */
export interface ApiCollectionProject {
  id: number
  name: string
  order_index: number
  word_count: number
  entity_count: number
  document_format: string
}

/** Enlace confirmado entre entidades de distintos libros */
export interface ApiEntityLink {
  id: number
  collection_id: number
  source_entity_id: number
  target_entity_id: number
  source_project_id: number
  target_project_id: number
  source_entity_name: string
  target_entity_name: string
  source_project_name: string
  target_project_name: string
  similarity: number
  match_type: string
}

/** Sugerencia de enlace generada por el fuzzy matcher */
export interface ApiLinkSuggestion {
  source_entity_id: number
  source_entity_name: string
  source_entity_type: string
  source_project_id: number
  source_project_name: string
  target_entity_id: number
  target_entity_name: string
  target_entity_type: string
  target_project_id: number
  target_project_name: string
  similarity: number
  match_type: string
}

/** Informe de análisis cross-book */
export interface ApiCrossBookReport {
  collection_id: number
  collection_name: string
  inconsistencies: ApiCrossBookInconsistency[]
  entity_links_analyzed: number
  projects_analyzed: number
  summary: {
    total_inconsistencies: number
    by_type: Record<string, number>
  }
}

/** Inconsistencia detectada entre libros */
export interface ApiCrossBookInconsistency {
  entity_name: string
  attribute_type: string
  attribute_key: string
  value_book_a: string
  value_book_b: string
  book_a_name: string
  book_b_name: string
  confidence: number
}

/** Contradicción de eventos entre libros */
export interface ApiEventContradiction {
  rule: string
  entity_name: string
  description: string
  event_a_type: string
  event_b_type: string
  book_a_name: string
  book_b_name: string
  book_a_chapter: number | null
  book_b_chapter: number | null
  confidence: number
  metadata: Record<string, unknown>
}

/** Informe de contradicciones de eventos cross-book */
export interface ApiCrossBookEventReport {
  collection_id: number
  collection_name: string
  contradictions: ApiEventContradiction[]
  entity_links_analyzed: number
  projects_analyzed: number
  summary: {
    total_contradictions: number
    by_rule: Record<string, number>
  }
}
