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

export interface ProjectSummary {
  what_this_app_seems_to_do: string
  technical_narrative: string
  core_flow: string
  agent_reasoning?: AgentReasoning
}

// ─── Capability Map ───────────────────────────────────────────────────────────

export interface CapabilityItem {
  capability_key: string
  name: string
  status: string // 'recently_changed' | 'stable' | 'needs_review' | 'unknown'
  linked_modules: string[]
  linked_routes: string[]
  reasoning_basis?: Record<string, unknown>
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

// ─── Overview Response ────────────────────────────────────────────────────────

export interface OverviewResponse {
  repo: RepoInfo | null
  snapshot: SnapshotInfo | null
  project_summary: ProjectSummary
  capability_map: CapabilityItem[]
  journeys: JourneyItem[]
  architecture_overview: ArchitectureOverview
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
