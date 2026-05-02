export type AssessmentRiskLevel = 'high' | 'medium' | 'low' | 'unknown'
export type AssessmentCoverageStatus = 'covered' | 'partial' | 'missing' | 'unknown'
export type AssessmentReviewStatus = 'unreviewed' | 'reviewed' | 'needs_follow_up' | 'needs_recheck'
export type AssessmentMode = 'working_tree' | 'commit_range' | 'pull_request'
export type AssessmentCaptureLevel = 'full' | 'partial' | 'diff_only'
export type AssessmentConfidenceLevel = 'high' | 'medium' | 'low'
export type EvidenceGrade = 'direct' | 'indirect' | 'inferred' | 'claimed' | 'not_run' | 'unknown'
export type ReviewDecision = 'safe_to_commit' | 'needs_recheck' | 'needs_tests' | 'do_not_commit_yet' | 'unknown'
export type ClaimType = 'refactor' | 'bugfix' | 'feature' | 'test' | 'config' | 'docs' | 'cleanup' | 'unknown'
export type TestCaseStatus = 'added' | 'modified' | 'deleted' | 'unknown'
export type TestExtractionConfidence = 'certain' | 'heuristic' | 'fallback'
export type TestIntentSource = 'rule_derived' | 'agent_claim' | 'generated' | 'unknown'
export type CoveredChangeRelationship =
  | 'calls'
  | 'imports'
  | 'shares_fixture'
  | 'co_changed'
  | 'names_changed_symbol'
  | 'same_file'
  | 'graph_inferred'
  | 'unknown'
export type CommandScope = 'test_case' | 'test_file' | 'changed_area' | 'assessment'
export type CommandStatus = 'not_run' | 'running' | 'passed' | 'failed' | 'partial' | 'unknown'

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
  capture_level: AssessmentCaptureLevel
  confidence: AssessmentConfidenceLevel
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
  highest_hunk_priority?: number
  mismatch_count?: number
  weakest_test_evidence_grade?: EvidenceGrade
}

export interface AssessmentManifest {
  assessment_id: string
  workspace_snapshot_id: string
  repo_key: string
  status: 'ready' | 'partial' | 'failed'
  mode?: AssessmentMode
  provenance_capture_level?: AssessmentCaptureLevel
  mismatch_count?: number
  weak_test_evidence_count?: number
  review_decision?: ReviewDecision
  hunk_queue_preview?: HunkReviewItem[]
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
  capture_level: AssessmentCaptureLevel
  evidence_sources: string[]
  confidence: Record<string, AssessmentConfidenceLevel>
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
  evidence_grade?: EvidenceGrade
  basis?: string[]
}

export interface AgentClaim {
  claim_id: string
  type: ClaimType
  text: string
  source: string
  session_id: string
  message_ref: string
  tool_call_ref: string
  related_files: string[]
  confidence: AssessmentConfidenceLevel
}

export interface ProvenanceRef {
  source: string
  session_id: string
  message_ref: string
  tool_call_ref: string
  command: string
  file_path: string
  hunk_id: string
  confidence: AssessmentConfidenceLevel
}

export interface ClaimMismatch {
  mismatch_id: string
  kind: string
  claim_id: string
  severity: AssessmentRiskLevel
  explanation: string
  fact_refs: string[]
  provenance_refs: ProvenanceRef[]
}

export interface HunkReviewItem {
  hunk_id: string
  file_id: string
  path: string
  priority: number
  risk_level: AssessmentRiskLevel
  reasons: string[]
  fact_basis: string[]
  provenance_refs: ProvenanceRef[]
  mismatch_ids: string[]
}

export interface ChangedFileDetail {
  file: ChangedFileSummary
  diff_hunks: DiffHunk[]
  changed_symbols: string[]
  related_agent_records: AgentChangeRecord[]
  related_tests: TestRelationship[]
  impact_facts: Array<Record<string, unknown>>
  agent_claims?: AgentClaim[]
  mismatches?: ClaimMismatch[]
  provenance_refs?: ProvenanceRef[]
  hunk_review_items?: HunkReviewItem[]
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

export interface TestIntentSummary {
  text: string
  source: TestIntentSource
  basis: string[]
}

export interface CoveredChangePreview {
  path: string
  hunk_id: string | null
  risk_level: AssessmentRiskLevel
  evidence_grade: EvidenceGrade
}

export interface TestCaseSummary {
  test_case_id: string
  file_id: string
  path: string
  name: string
  status: TestCaseStatus
  extraction_confidence: TestExtractionConfidence
  evidence_grade: EvidenceGrade
  weakest_evidence_grade: EvidenceGrade
  last_status: 'passed' | 'failed' | 'not_run' | 'unknown'
  covered_changes_preview: CoveredChangePreview[]
  highest_risk_covered_hunk_id: string | null
  intent_summary: TestIntentSummary
}

export interface CoveredChange {
  path: string
  symbol: string
  hunk_id: string
  relationship: CoveredChangeRelationship
  evidence_grade: EvidenceGrade
  basis: string[]
}

export interface TestCoveredScenario {
  title: string
  source: TestIntentSource
  basis: string[]
}

export interface ExecutedTestCase {
  node_id: string
  name: string
  status: 'passed' | 'failed' | 'skipped' | 'unknown'
  source: 'runner_output' | 'collect_only' | 'test_file_parse'
  scenarios: TestCoveredScenario[]
  test_data: string[]
}

export interface TestCoveredCodeAnalysis {
  path: string
  symbol: string
  hunk_id: string
  relationship: CoveredChangeRelationship
  evidence_grade: EvidenceGrade
  analysis: string
  basis: string[]
}

export interface TestResultAnalysis {
  summary: string
  scenarios: TestCoveredScenario[]
  test_data: string[]
  covered_code_analysis?: TestCoveredCodeAnalysis[]
  coverage_gaps: string[]
  source: TestIntentSource
  basis: string[]
}

export interface TestRunEvidence {
  run_id: string
  source: 'codex_command_log' | 'rerun'
  command: string
  status: CommandStatus
  exit_code: number | null
  duration_ms: number
  stdout: string
  stderr: string
  executed_cases: ExecutedTestCase[]
  analysis: TestResultAnalysis
  captured_at: string
  evidence_grade: EvidenceGrade
}

export interface RecommendedTestCommand {
  command_id: string
  command: string
  reason: string
  scope: CommandScope
  status: CommandStatus
  last_run_id: string | null
}

export interface TestCommandRunResult {
  run_id: string
  source: 'codex_command_log' | 'rerun'
  command_id: string
  command: string
  status: CommandStatus
  exit_code: number | null
  duration_ms: number
  stdout: string
  stderr: string
  stdout_truncated: boolean
  stderr_truncated: boolean
  timed_out: boolean
  started_at: string
  finished_at: string
  captured_at: string
  argv: string[]
  executed_cases: ExecutedTestCase[]
  analysis: TestResultAnalysis
  evidence_grade: EvidenceGrade
}

export interface TestCaseDetail {
  test_case: TestCaseSummary
  diff_hunks: DiffHunk[]
  full_body: DiffLine[]
  assertions: DiffLine[]
  covered_scenarios: TestCoveredScenario[]
  test_results?: TestRunEvidence[]
  covered_changes: CoveredChange[]
  recommended_commands: RecommendedTestCommand[]
  related_agent_claims: AgentClaim[]
  unknowns: string[]
}

export interface TestFileSummary {
  file_id: string
  path: string
  status: string
  additions: number
  deletions: number
  test_case_count: number
  strongest_evidence_grade: EvidenceGrade
  weakest_evidence_grade: EvidenceGrade
  latest_command_status: CommandStatus
  test_cases: TestCaseSummary[]
}

export interface TestManagementSummary {
  assessment_id: string
  repo_key: string
  changed_test_file_count: number
  test_case_count: number
  evidence_grade_counts: Record<string, number>
  command_status_counts: Record<string, number>
  files: TestFileSummary[]
  unknowns: string[]
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
