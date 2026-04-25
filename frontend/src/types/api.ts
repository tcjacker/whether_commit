export type AssessmentRiskLevel = 'high' | 'medium' | 'low' | 'unknown'
export type AssessmentCoverageStatus = 'covered' | 'partial' | 'missing' | 'unknown'
export type AssessmentReviewStatus = 'unreviewed' | 'reviewed' | 'needs_follow_up' | 'needs_recheck'

export interface AssessmentSummary {
  headline: string
  overall_risk_level: AssessmentRiskLevel
  coverage_status: AssessmentCoverageStatus
  changed_file_count: number
  unreviewed_file_count: number
  affected_capability_count: number
  missing_test_count: number
  agent_sources: string[]
  recommended_review_order: string[]
}

export interface AgenticSummary {
  generated_by: 'codex_logs' | 'rules'
  capture_level: 'full' | 'partial' | 'diff_only'
  confidence: 'high' | 'medium' | 'low'
  time_window: {
    since_commit: string
    since_commit_time: string | null
  }
  user_design_goal: string
  codex_change_summary: string
  main_objective: string
  key_decisions: string[]
  files_or_areas_changed: string[]
  tests_and_verification: string[]
  unknowns: string[]
}

export interface ChangedFileSummary {
  file_id: string
  path: string
  old_path: string | null
  status: string
  additions: number
  deletions: number
  risk_level: AssessmentRiskLevel
  coverage_status: AssessmentCoverageStatus
  review_status: AssessmentReviewStatus
  agent_sources: string[]
  diff_fingerprint: string
}

export interface AssessmentManifest {
  assessment_id: string
  workspace_snapshot_id: string
  repo_key: string
  status: 'ready' | 'partial' | 'failed'
  agentic_summary: AgenticSummary
  summary: AssessmentSummary
  file_list: ChangedFileSummary[]
  risk_signals_summary: Array<Record<string, unknown>>
  agent_sources: string[]
  review_progress: {
    total: number
    reviewed: number
    needs_follow_up: number
    needs_recheck: number
    unreviewed: number
  }
}

export interface DiffLine {
  type: 'add' | 'remove' | 'context' | 'header'
  content: string
}

export interface DiffHunk {
  hunk_id: string
  old_start: number
  old_lines: number
  new_start: number
  new_lines: number
  hunk_fingerprint: string
  lines: DiffLine[]
}

export interface AgentChangeRecord {
  record_id: string
  source: string
  capture_level: 'full' | 'partial' | 'diff_only'
  evidence_sources: string[]
  confidence: Record<string, 'high' | 'medium' | 'low'>
  task_summary: string
  declared_intent: string
  reasoning_summary: string
  files_touched: string[]
  commands_run: string[]
  tests_run: Array<{ command: string; status: string }>
  known_limitations: string[]
  raw_log_ref: string
}

export interface TestRelationship {
  test_id: string
  path: string
  relationship: 'primary' | 'secondary' | 'inferred'
  confidence: 'high' | 'medium' | 'low'
  last_status: 'passed' | 'failed' | 'not_run' | 'unknown'
  evidence: 'marker' | 'naming_convention' | 'graph_inference' | 'agent_claim'
}

export interface ChangedFileDetail {
  file: ChangedFileSummary
  diff_hunks: DiffHunk[]
  changed_symbols: string[]
  related_agent_records: AgentChangeRecord[]
  related_tests: TestRelationship[]
  impact_facts: Array<Record<string, unknown>>
  file_assessment: {
    why_changed: string
    impact_summary: string
    test_summary: string
    recommended_action: string
    generated_by: 'rules' | 'codex_agent'
    agent_status: 'not_run' | 'running' | 'accepted' | 'failed' | 'fallback'
    agent_source: 'codex' | null
    confidence: 'high' | 'medium' | 'low'
    evidence_refs: string[]
    unknowns: string[]
  }
  review_state: {
    review_status: AssessmentReviewStatus
    diff_fingerprint: string
    reviewer: string | null
    reviewed_at: string | null
    notes: string[]
  }
}

export type JobStatus = 'pending' | 'running' | 'success' | 'failed' | 'partial_success'

export interface JobState {
  job_id: string
  repo_key: string
  status: JobStatus
  step: string
  progress: number
  message: string
  created_at: string
  updated_at: string
}

export interface RebuildRequest {
  repo_key: string
  base_commit_sha?: string
  include_untracked?: boolean
  workspace_path?: string
}

export interface RebuildResponse {
  job_id: string
  status: string
}
