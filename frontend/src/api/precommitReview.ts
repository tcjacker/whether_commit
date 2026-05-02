import { get, post } from './client'
import type { PrecommitSnapshot, PrecommitReviewState, VerificationRun } from '../types/api'

function params(workspacePath: string) {
  return new URLSearchParams({ workspace_path: workspacePath })
}

export function fetchCurrentSnapshot(workspacePath: string): Promise<PrecommitSnapshot> {
  return get<PrecommitSnapshot>(`/api/snapshots/current?${params(workspacePath)}`)
}

export function rebuildPrecommitReview(workspacePath: string): Promise<PrecommitSnapshot> {
  return post<PrecommitSnapshot>('/api/precommit-review/rebuild', { workspace_path: workspacePath })
}

export function updateFileReviewState(
  workspacePath: string,
  fileId: string,
  status: PrecommitReviewState,
): Promise<PrecommitSnapshot> {
  return post<PrecommitSnapshot>(`/api/precommit-review/files/${fileId}/state`, { workspace_path: workspacePath, status })
}

export function updateHunkReviewState(
  workspacePath: string,
  hunkId: string,
  status: PrecommitReviewState,
): Promise<PrecommitSnapshot> {
  return post<PrecommitSnapshot>(`/api/precommit-review/hunks/${hunkId}/state`, { workspace_path: workspacePath, status })
}

export function updateSignalReviewState(
  workspacePath: string,
  signalId: string,
  status: PrecommitReviewState,
): Promise<PrecommitSnapshot> {
  return post<PrecommitSnapshot>(`/api/precommit-review/signals/${signalId}/state`, { workspace_path: workspacePath, status })
}

export function runVerificationCommand(
  workspacePath: string,
  snapshotId: string,
  command: string,
): Promise<VerificationRun> {
  return post<VerificationRun>('/api/verification/run', { workspace_path: workspacePath, snapshot_id: snapshotId, command })
}

export function fetchVerificationRun(workspacePath: string, runId: string): Promise<VerificationRun> {
  return get<VerificationRun>(`/api/verification/runs/${runId}?${params(workspacePath)}`)
}
