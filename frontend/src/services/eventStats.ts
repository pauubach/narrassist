import { api } from '@/services/apiClient'

export interface ProjectEventStats {
  project_id: number
  total_events: number
  critical_unresolved: {
    count: number
    by_type: Record<string, number>
  }
  empty_chapters: number[]
  event_clusters: Array<{
    event_type: string
    chapter: number
    count: number
  }>
  density_by_chapter: Array<{
    chapter: number
    tier1: number
    tier2: number
    tier3: number
    total: number
  }>
}

export async function fetchProjectEventStats(projectId: number): Promise<ProjectEventStats> {
  return api.getChecked<ProjectEventStats>(`/api/projects/${projectId}/events/stats`)
}
