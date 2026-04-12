import { get, post } from './client'
import type { OverviewResponse, RebuildRequest, RebuildResponse } from '../types/api'

export function fetchOverview(repoKey: string, snapshotId?: string): Promise<OverviewResponse> {
  const params = new URLSearchParams({ repo_key: repoKey })
  if (snapshotId) params.set('workspace_snapshot_id', snapshotId)
  return get<OverviewResponse>(`/api/overview?${params}`)
}

export function triggerRebuild(req: RebuildRequest): Promise<RebuildResponse> {
  return post<RebuildResponse>('/api/overview/rebuild', req)
}
