/**
 * Projects API Service
 *
 * Funciones para interactuar con el endpoint de proyectos.
 */

import { api } from './apiClient'
import type { ApiProject, ApiProjectSettings, ApiProjectSettingsPatch } from '@/types/api/projects'

/**
 * Response del endpoint PATCH /api/projects/{id}/settings
 */
interface UpdateSettingsResponse {
  settings: ApiProjectSettings
  runtime_warnings?: string[]
}

/**
 * Actualiza los settings de un proyecto (merge profundo).
 *
 * @param projectId - ID del proyecto
 * @param settings - Settings parciales a actualizar
 * @returns Settings actualizados + warnings de degradación runtime
 *
 * @example
 * const result = await updateProjectSettings(1, {
 *   analysis_features: {
 *     pipeline_flags: { grammar: false }
 *   }
 * })
 */
export async function updateProjectSettings(
  projectId: number,
  settings: ApiProjectSettingsPatch,
): Promise<UpdateSettingsResponse> {
  return api.patchChecked<UpdateSettingsResponse>(
    `/api/projects/${projectId}/settings`,
    settings as Record<string, unknown>,
  )
}

/**
 * Obtiene un proyecto por ID (incluye settings.analysis_features).
 *
 * @param projectId - ID del proyecto
 * @returns Proyecto completo
 */
export async function getProject(projectId: number): Promise<ApiProject> {
  return api.get<ApiProject>(`/api/projects/${projectId}`)
}
