// ─── Core ────────────────────────────────────────────────────────────────────

export interface RepoInfo {
  repo_key: string
  name: string
  default_branch: string
}

export interface SnapshotInfo {
  base_commit_sha: string
  workspace_snapshot_id: string
  has_pending_changes: boolean
  status: string
  generated_at: string
}

// ─── Agent Harness ─────────────────────────────────────────────────────────

export type AgentHarnessStatus = 'accepted' | 'fallback' | 'timeout' | 'validation_failed' | 'budget_exceeded'

export interface AgentHarnessProjectSummary {
  overall_assessment?: string
  impact_level?: 'high' | 'medium' | 'low' | 'unknown'
  impact_basis?: Array<Record<string, unknown>>
  affected_capability_count?: number
  affected_entrypoints?: string[]
  critical_paths?: string[]
  verification_gaps?: string[]
  priority_themes?: string[]
}

export interface AgentHarnessCapability {
  capability_key: string
  name: string
  impact_status: 'unknown' | 'untouched' | 'directly_changed' | 'indirectly_impacted' | 'high_risk_unverified'
  impact_reason: string
  related_themes: string[]
  verification_status: 'unknown' | 'verified' | 'unverified' | 'partial' | 'covered' | 'missing'
}

export interface AgentHarnessChangeTheme {
  theme_key: string
  name: string
  summary: string
  capability_keys: string[]
  change_ids: string[]
}

export type AgentHarnessReadTargetType = 'file' | 'symbol' | 'call_chain' | 'verification_context'

export interface AgentHarnessReadRequest {
  target_type: AgentHarnessReadTargetType
  target_id: string
  reason: string
}

// ─── Project Summary ─────────────────────────────────────────────────────────

export interface AgentReasoning {
  technical_change_summary: string
  change_types: string[]
  risk_factors: string[]
  review_recommendations: string[]
  why_impacted: string
  confidence: string
  unknowns: string[]
  validation_gaps: string[]
  llm_reasoning: Record<string, unknown>
}

export interface ProjectSummary extends AgentHarnessProjectSummary {
  what_this_app_seems_to_do: string
  technical_narrative: string
  core_flow: string
  agent_reasoning?: AgentReasoning
}

export interface ChangeRiskHeadline {
  overall_risk_level: 'high' | 'medium' | 'low' | 'unknown'
  overall_risk_summary: string
  recommended_focus: string[]
}

export interface ChangeRiskCoverage {
  coverage_status: 'well_covered' | 'partially_covered' | 'weakly_covered' | 'unknown'
  affected_test_count: number
  verified_changed_path_count: number
  unverified_changed_path_count: number
  missing_test_paths: string[]
  coverage_summary: string
}

export interface ExistingFeatureImpactItem {
  capability_key: string
  name: string
  impact_status: string
  technical_entrypoints: string[]
  changed_files: string[]
  related_modules: string[]
  verification_status: string
  impact_basis: Array<Record<string, unknown>>
}

export interface ChangeRiskSummary {
  headline: ChangeRiskHeadline
  coverage: ChangeRiskCoverage
  existing_feature_impact: {
    business_impact_summary: string
    affected_capability_count: number
    affected_capabilities: ExistingFeatureImpactItem[]
  }
  risk_signals: Array<{
    signal_key: string
    title: string
    severity: 'high' | 'medium' | 'low'
    reason: string
    related_files: string[]
    related_modules: string[]
    mitigation: string
  }>
  agent_metadata: {
    agent_based_fields: string[]
    rule_based_fields: string[]
  }
}

// ─── Test Assets ─────────────────────────────────────────────────────────────

export interface TestAssetCapabilityCoverage {
  capability_key: string
  business_capability: string
  coverage_status: 'covered' | 'partial' | 'missing' | 'unknown'
  technical_entrypoints: string[]
  covered_paths: string[]
  covering_tests: string[]
  gaps: string[]
  maintenance_recommendation: string
}

export interface TestAssetFile {
  path: string
  maintenance_status: 'keep' | 'update' | 'retire' | 'unknown'
  covered_capabilities: string[]
  covered_paths: string[]
  linked_entrypoints: string[]
  invalidation_reasons: string[]
  recommendation: string
  evidence_status: string
}

export interface TestAssetSummary {
  health_status: 'healthy' | 'needs_maintenance' | 'high_risk' | 'unknown'
  total_test_file_count: number
  affected_test_count: number
  changed_test_file_count: number
  stale_or_invalid_test_count: number
  duplicate_or_low_value_test_count: number
  coverage_gaps: string[]
  recommended_actions: string[]
  capability_coverage: TestAssetCapabilityCoverage[]
  test_files: TestAssetFile[]
}

// ─── File Review Summaries ───────────────────────────────────────────────────

export interface FileDiffSnippet {
  type: 'add' | 'delete' | 'context'
  line: string
  text: string
}

export interface FileReviewSummary {
  path: string
  file_role: string
  risk_level: 'high' | 'medium' | 'low' | 'unknown'
  diff_summary: string
  diff_snippets: FileDiffSnippet[]
  product_meaning: string
  intent_evidence?: string[]
  review_focus: string[]
  related_entrypoints: string[]
  related_capabilities: string[]
  related_tests: string[]
  evidence_basis: string[]
  generated_by: 'rules' | 'agent' | 'rules+agent'
}

// ─── Capability Map ───────────────────────────────────────────────────────────

export interface CapabilityItem {
  capability_key: string
  name: string
  status: string // 'recently_changed' | 'stable' | 'needs_review' | 'unknown'
  linked_modules: string[]
  linked_routes: string[]
  is_primary_target?: boolean
  reasoning_basis?: Record<string, unknown>
  impact_status?: AgentHarnessCapability['impact_status']
  impact_reason?: string
  related_themes?: string[]
  verification_status?: AgentHarnessCapability['verification_status']
}

// ─── Journeys ────────────────────────────────────────────────────────────────

export interface JourneyItem {
  name: string
  primary_actor?: string
  steps: string[]
  criticality?: string
  recent_impact?: string
}

// ─── Architecture ─────────────────────────────────────────────────────────────

export interface ArchitectureNode {
  id: string
  name: string
  type: string
  health?: string
  main_responsibility?: string
}

export interface ArchitectureEdge {
  source: string
  target: string
  type: string
}

export interface ArchitectureOverview {
  nodes: ArchitectureNode[]
  edges: ArchitectureEdge[]
}

// ─── AI Changes ───────────────────────────────────────────────────────────────

export interface ImpactItem {
  entity_id?: string
  reason: string
  evidence: unknown[]
  distance?: number
  direction?: string
}

export interface RecentAIChange {
  change_id: string
  change_title: string
  summary: string
  affected_capabilities: string[]
  technical_entrypoints: string[]
  changed_files: string[]
  changed_symbols: string[]
  changed_routes: string[]
  changed_schemas: string[]
  changed_jobs: string[]
  change_types: string[]
  directly_changed_modules: string[]
  transitively_affected_modules: string[]
  affected_entrypoints: string[]
  affected_data_objects: string[]
  why_impacted: string
  risk_factors: string[]
  review_recommendations: string[]
  linked_tests: string[]
  verification_coverage: string
  confidence: string
  change_intent: string
  coherence: string
  coherence_groups: string[]
}

// ─── Verification ─────────────────────────────────────────────────────────────

export interface VerificationStatus {
  build: { status: string; [k: string]: unknown }
  unit_tests: { status: string; passed?: number; total?: number; [k: string]: unknown }
  integration_tests: { status: string; passed?: number; total?: number; [k: string]: unknown }
  scenario_replay: { status: string; [k: string]: unknown }
  critical_paths: Array<{ name: string; status: string }>
  unverified_areas: string[]
  verified_changed_modules: string[]
  unverified_changed_modules: string[]
  affected_tests: string[]
  verified_changed_paths: string[]
  unverified_changed_paths: string[]
  missing_tests_for_changed_paths: string[]
  critical_changed_paths: Array<Record<string, unknown>>
  evidence_by_path: Record<string, unknown>
}

// ─── Review Graph ────────────────────────────────────────────────────────────

export type ReviewGraphObjectType = 'FeatureContainer' | 'CodeUnit' | 'TestUnit' | 'EvidenceGroup'

export interface ReviewGraphRef {
  kind: string
  value: string
}

export interface ReviewGraphNode {
  id: string
  type: ReviewGraphObjectType
  label: string
  match_status: 'direct' | 'expanded'
  layers: Array<'feature' | 'impact'>
  refs: ReviewGraphRef[]
}

export interface ReviewGraphEdge {
  from: string
  to: string
  type: string
  layers: Array<'feature' | 'impact'>
}

export interface ReviewGraphSummary {
  title: string
  direct_feature_count: number
  impacted_feature_count: number
  verification_gap_count: number
  mapping_status?: 'missing' | 'invalid'
}

export interface ReviewGraphResponse {
  version: 'v1'
  change_id: string
  summary: ReviewGraphSummary
  nodes: ReviewGraphNode[]
  edges: ReviewGraphEdge[]
  unresolved_refs: string[]
}

// ─── Agentic Change Assessment ───────────────────────────────────────────────

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

// ─── Overview Response ────────────────────────────────────────────────────────

export interface OverviewResponse {
  repo: RepoInfo | null
  snapshot: SnapshotInfo | null
  project_summary: ProjectSummary
  capability_map: CapabilityItem[]
  journeys: JourneyItem[]
  architecture_overview: ArchitectureOverview
  change_themes?: AgentHarnessChangeTheme[]
  change_risk_summary: ChangeRiskSummary
  test_asset_summary?: TestAssetSummary
  file_review_summaries?: FileReviewSummary[]
  agent_harness_status?: AgentHarnessStatus | null
  agent_harness_metadata?: Record<string, unknown>
  recent_ai_changes: RecentAIChange[]
  verification_status: VerificationStatus
  warnings: string[]
}

// ─── Job ──────────────────────────────────────────────────────────────────────

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

// ─── Rebuild ──────────────────────────────────────────────────────────────────

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
