import { get } from './client'
import type { AssessmentManifest, ChangedFileDetail, ChangedFileSummary } from '../types/api'

export function fetchLatestAssessment(repoKey: string, workspacePath?: string): Promise<AssessmentManifest> {
  const params = new URLSearchParams({ repo_key: repoKey })
  if (workspacePath?.trim()) params.set('workspace_path', workspacePath.trim())
  return get<AssessmentManifest>(`/api/assessments/latest?${params}`)
}

export function fetchAssessmentFiles(
  repoKey: string,
  assessmentId: string,
  workspacePath?: string,
): Promise<{ files: ChangedFileSummary[] }> {
  const params = new URLSearchParams({ repo_key: repoKey })
  if (workspacePath?.trim()) params.set('workspace_path', workspacePath.trim())
  return get<{ files: ChangedFileSummary[] }>(`/api/assessments/${assessmentId}/files?${params}`)
}

export function fetchAssessmentFileDetail(
  repoKey: string,
  assessmentId: string,
  fileId: string,
  workspacePath?: string,
): Promise<ChangedFileDetail> {
  const params = new URLSearchParams({ repo_key: repoKey })
  if (workspacePath?.trim()) params.set('workspace_path', workspacePath.trim())
  return get<ChangedFileDetail>(`/api/assessments/${assessmentId}/files/${fileId}?${params}`)
}
