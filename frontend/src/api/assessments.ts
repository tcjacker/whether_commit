import { get, post } from './client'
import type {
  AssessmentManifest,
  ChangedFileDetail,
  ChangedFileSummary,
  RebuildRequest,
  RebuildResponse,
  TestCaseDetail,
  TestCommandRunResult,
  TestManagementSummary,
  TestResultAnalysis,
} from '../types/api'

export function triggerAssessmentRebuild(req: RebuildRequest): Promise<RebuildResponse> {
  return post<RebuildResponse>('/api/assessments/rebuild', req)
}

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

export function fetchAssessmentTests(
  repoKey: string,
  assessmentId: string,
  workspacePath?: string,
): Promise<TestManagementSummary> {
  const params = new URLSearchParams({ repo_key: repoKey })
  if (workspacePath?.trim()) params.set('workspace_path', workspacePath.trim())
  return get<TestManagementSummary>(`/api/assessments/${assessmentId}/tests?${params}`)
}

export function fetchAssessmentTestCaseDetail(
  repoKey: string,
  assessmentId: string,
  testCaseId: string,
  workspacePath?: string,
): Promise<TestCaseDetail> {
  const params = new URLSearchParams({ repo_key: repoKey })
  if (workspacePath?.trim()) params.set('workspace_path', workspacePath.trim())
  return get<TestCaseDetail>(`/api/assessments/${assessmentId}/tests/${testCaseId}?${params}`)
}

export function runAssessmentTestCommand(
  repoKey: string,
  assessmentId: string,
  testCaseId: string,
  commandId: string,
  workspacePath?: string,
): Promise<TestCommandRunResult> {
  const params = new URLSearchParams({ repo_key: repoKey })
  if (workspacePath?.trim()) params.set('workspace_path', workspacePath.trim())
  return post<TestCommandRunResult>(
    `/api/assessments/${assessmentId}/tests/${testCaseId}/commands/${commandId}/run?${params}`,
    {},
  )
}

export function analyzeAssessmentTestResult(
  repoKey: string,
  assessmentId: string,
  testCaseId: string,
  runId: string,
  workspacePath?: string,
): Promise<TestResultAnalysis> {
  const params = new URLSearchParams({ repo_key: repoKey })
  if (workspacePath?.trim()) params.set('workspace_path', workspacePath.trim())
  return post<TestResultAnalysis>(
    `/api/assessments/${assessmentId}/tests/${testCaseId}/results/${runId}/analyze?${params}`,
    {},
  )
}

export function triggerFileAgentAssessment(
  repoKey: string,
  assessmentId: string,
  fileId: string,
  workspacePath?: string,
  language = 'zh-CN',
): Promise<ChangedFileDetail> {
  const params = new URLSearchParams({ repo_key: repoKey })
  if (workspacePath?.trim()) params.set('workspace_path', workspacePath.trim())
  params.set('language', language)
  return post<ChangedFileDetail>(`/api/assessments/${assessmentId}/files/${fileId}/agent-assessment?${params}`, {})
}
