import { get } from './client'
import type { ReviewGraphResponse } from '../types/api'

export function fetchReviewGraph(repoKey: string, workspacePath?: string): Promise<ReviewGraphResponse> {
  const params = new URLSearchParams({ repo_key: repoKey })
  if (workspacePath?.trim()) params.set('workspace_path', workspacePath.trim())
  return get<ReviewGraphResponse>(`/api/changes/review-graph/latest?${params}`)
}
