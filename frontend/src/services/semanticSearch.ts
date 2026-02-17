/**
 * Servicio de búsqueda semántica
 *
 * Proporciona búsqueda de fragmentos similares usando embeddings.
 */

import { api } from './apiClient'

/** Resultado de búsqueda semántica */
export interface SemanticMatch {
  /** Texto del fragmento */
  text: string
  /** Posición inicial en el documento completo */
  start_char: number
  /** Posición final en el documento completo */
  end_char: number
  /** Score de similaridad (0-1) */
  similarity: number
  /** ID del capítulo (si aplica) */
  chapter_id?: number | null
  /** Título del capítulo */
  chapter_title?: string
  /** Posición inicial relativa al capítulo */
  start_char_in_chapter?: number
}

/** Respuesta de búsqueda semántica */
export interface SemanticSearchResponse {
  /** Fragmentos encontrados */
  matches: SemanticMatch[]
  /** Query original */
  query: string
  /** Número de resultados */
  count: number
  /** Total de chunks analizados */
  total_chunks: number
}

/** Parámetros de búsqueda semántica */
export interface SemanticSearchParams {
  /** Texto a buscar */
  query: string
  /** Máximo de resultados (1-50, default 10) */
  limit?: number
  /** Similaridad mínima (0.0-1.0, default 0.5) */
  min_similarity?: number
}

/**
 * Busca fragmentos de texto similares usando embeddings semánticos
 */
export async function searchSimilarText(
  projectId: number,
  params: SemanticSearchParams
): Promise<SemanticSearchResponse> {
  const response = await api.postChecked<SemanticSearchResponse>(
    `/api/projects/${projectId}/search/similar`,
    {
      query: params.query,
      limit: params.limit ?? 10,
      min_similarity: params.min_similarity ?? 0.5,
    },
    { timeout: 30000 } // 30s para procesar embeddings
  )

  return response
}
