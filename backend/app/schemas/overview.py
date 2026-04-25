from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any, Union, Literal
from datetime import datetime

from app.schemas.agent_harness import AgentHarnessChangeTheme, AgentHarnessProjectSummary, AgentHarnessStatus

class RepoInfo(BaseModel):
    repo_key: str
    name: str
    default_branch: str

class SnapshotInfo(BaseModel):
    base_commit_sha: str
    workspace_snapshot_id: str
    has_pending_changes: bool
    status: str
    generated_at: datetime

class ArchitectureNode(BaseModel):
    id: str
    name: str
    type: str  # Prefer: router, api handler, service, repository, db model, worker, external integration, config
    health: Optional[str] = None

class ArchitectureEdge(BaseModel):
    source: str
    target: str
    type: str  # Prefer: calls, reads, writes, publishes, subscribes, validates, transforms

class ArchitectureOverview(BaseModel):
    nodes: List[ArchitectureNode] = []
    edges: List[ArchitectureEdge] = []


class AgentReasoning(BaseModel):
    technical_change_summary: str = ""
    change_types: List[str] = []
    risk_factors: List[str] = []
    review_recommendations: List[str] = []
    why_impacted: str = ""
    confidence: str = "low"
    unknowns: List[str] = []
    validation_gaps: List[str] = []
    llm_reasoning: Dict[str, Any] = {}


class ProjectSummary(AgentHarnessProjectSummary):
    what_this_app_seems_to_do: str = ""
    technical_narrative: str = ""
    core_flow: str = ""
    agent_reasoning: Optional[AgentReasoning] = None


class ChangeRiskHeadline(BaseModel):
    overall_risk_level: Literal["high", "medium", "low", "unknown"] = "unknown"
    overall_risk_summary: str = ""
    recommended_focus: List[str] = Field(default_factory=list)


class ChangeRiskCoverage(BaseModel):
    coverage_status: Literal["well_covered", "partially_covered", "weakly_covered", "unknown"] = "unknown"
    affected_test_count: int = 0
    verified_changed_path_count: int = 0
    unverified_changed_path_count: int = 0
    missing_test_paths: List[str] = Field(default_factory=list)
    coverage_summary: str = ""


class ExistingFeatureImpactItem(BaseModel):
    capability_key: str = ""
    name: str = ""
    impact_status: str = "unknown"
    technical_entrypoints: List[str] = Field(default_factory=list)
    changed_files: List[str] = Field(default_factory=list)
    related_modules: List[str] = Field(default_factory=list)
    verification_status: str = "unknown"
    impact_basis: List[Dict[str, Any]] = Field(default_factory=list)


class ExistingFeatureImpact(BaseModel):
    business_impact_summary: str = ""
    affected_capability_count: int = 0
    affected_capabilities: List[ExistingFeatureImpactItem] = Field(default_factory=list)


class RiskSignal(BaseModel):
    signal_key: str = ""
    title: str = ""
    severity: Literal["high", "medium", "low"] = "low"
    reason: str = ""
    related_files: List[str] = Field(default_factory=list)
    related_modules: List[str] = Field(default_factory=list)
    mitigation: str = ""


class ChangeRiskAgentMetadata(BaseModel):
    agent_based_fields: List[str] = Field(default_factory=list)
    rule_based_fields: List[str] = Field(default_factory=list)


class ChangeRiskSummary(BaseModel):
    headline: ChangeRiskHeadline = ChangeRiskHeadline()
    coverage: ChangeRiskCoverage = ChangeRiskCoverage()
    existing_feature_impact: ExistingFeatureImpact = ExistingFeatureImpact()
    risk_signals: List[RiskSignal] = Field(default_factory=list)
    agent_metadata: ChangeRiskAgentMetadata = ChangeRiskAgentMetadata()


class TestAssetCapabilityCoverage(BaseModel):
    capability_key: str = ""
    business_capability: str = ""
    coverage_status: Literal["covered", "partial", "missing", "unknown"] = "unknown"
    technical_entrypoints: List[str] = Field(default_factory=list)
    covered_paths: List[str] = Field(default_factory=list)
    covering_tests: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    maintenance_recommendation: str = ""


class TestAssetFile(BaseModel):
    path: str = ""
    maintenance_status: Literal["keep", "update", "retire", "unknown"] = "unknown"
    covered_capabilities: List[str] = Field(default_factory=list)
    covered_paths: List[str] = Field(default_factory=list)
    linked_entrypoints: List[str] = Field(default_factory=list)
    invalidation_reasons: List[str] = Field(default_factory=list)
    recommendation: str = ""
    evidence_status: str = "unknown"


class TestAssetSummary(BaseModel):
    health_status: Literal["healthy", "needs_maintenance", "high_risk", "unknown"] = "unknown"
    total_test_file_count: int = 0
    affected_test_count: int = 0
    changed_test_file_count: int = 0
    stale_or_invalid_test_count: int = 0
    duplicate_or_low_value_test_count: int = 0
    coverage_gaps: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    capability_coverage: List[TestAssetCapabilityCoverage] = Field(default_factory=list)
    test_files: List[TestAssetFile] = Field(default_factory=list)


class FileDiffSnippet(BaseModel):
    type: Literal["add", "delete", "context"] = "context"
    line: str = ""
    text: str = ""


class FileReviewSummary(BaseModel):
    path: str = ""
    file_role: str = ""
    risk_level: Literal["high", "medium", "low", "unknown"] = "unknown"
    diff_summary: str = ""
    diff_snippets: List[FileDiffSnippet] = Field(default_factory=list)
    product_meaning: str = ""
    intent_evidence: List[str] = Field(default_factory=list)
    review_focus: List[str] = Field(default_factory=list)
    related_entrypoints: List[str] = Field(default_factory=list)
    related_capabilities: List[str] = Field(default_factory=list)
    related_tests: List[str] = Field(default_factory=list)
    evidence_basis: List[str] = Field(default_factory=list)
    generated_by: Literal["rules", "agent", "rules+agent"] = "rules"


class ImpactItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    entity_id: Optional[str] = None
    reason: str = ""
    evidence: Any = []
    distance: Optional[int] = None
    direction: Optional[str] = None


class RecentAIChange(BaseModel):
    change_id: str = "chg_unknown"
    change_title: str
    summary: str = ""
    affected_capabilities: List[str] = Field(default_factory=list)
    technical_entrypoints: List[str] = Field(default_factory=list)
    changed_files: List[str] = []
    changed_symbols: List[str] = []
    changed_routes: List[str] = []
    changed_schemas: List[str] = []
    changed_jobs: List[str] = []
    change_types: List[str] = []
    directly_changed_modules: List[str] = []
    transitively_affected_modules: List[str] = []
    affected_entrypoints: List[str] = []
    affected_data_objects: List[str] = []
    why_impacted: str = ""
    impact_reasons: List[Union[ImpactItem, str]] = []
    direct_impacts: List[Union[ImpactItem, str]] = []
    transitive_impacts: List[Union[ImpactItem, str]] = []
    risk_factors: List[str] = []
    review_recommendations: List[str] = []
    linked_tests: List[str] = []
    verification_coverage: str = "unknown"
    confidence: str = "low"
    change_intent: str = ""
    coherence: str = "unknown"
    coherence_groups: List[str] = []

class VerificationStatus(BaseModel):
    build: Dict[str, Any] = {"status": "unknown"}
    unit_tests: Dict[str, Any] = {"status": "unknown"}
    integration_tests: Dict[str, Any] = {"status": "unknown"}
    scenario_replay: Dict[str, Any] = {"status": "unknown"}
    critical_paths: List[Dict[str, Any]] = []
    unverified_areas: List[str] = []
    # New change-aware verification fields
    verified_changed_modules: List[str] = []
    unverified_changed_modules: List[str] = []
    affected_tests: List[str] = []
    verified_changed_paths: List[str] = []
    unverified_changed_paths: List[str] = []
    verified_impacts: List[Dict[str, Any]] = []
    unverified_impacts: List[Dict[str, Any]] = []
    missing_tests_for_changed_paths: List[str] = []
    critical_changed_paths: List[Dict[str, Any]] = []
    evidence_by_path: Dict[str, Any] = {}

class OverviewResponse(BaseModel):
    repo: Optional[RepoInfo] = None
    snapshot: Optional[SnapshotInfo] = None
    project_summary: ProjectSummary = ProjectSummary()
    capability_map: List[Dict[str, Any]] = []
    journeys: List[Dict[str, Any]] = []
    architecture_overview: ArchitectureOverview = ArchitectureOverview()
    recent_ai_changes: List[RecentAIChange] = []
    change_themes: List[AgentHarnessChangeTheme] = Field(default_factory=list)
    change_risk_summary: ChangeRiskSummary = ChangeRiskSummary()
    test_asset_summary: TestAssetSummary = TestAssetSummary()
    file_review_summaries: List[FileReviewSummary] = Field(default_factory=list)
    agent_harness_status: Optional[AgentHarnessStatus] = None
    agent_harness_metadata: Dict[str, Any] = Field(default_factory=dict)
    verification_status: VerificationStatus = VerificationStatus()
    warnings: List[str] = []

class RunVerificationRequest(BaseModel):
    repo_key: str
    workspace_path: str

class RunVerificationResponse(BaseModel):
    status: str
    passed: int = 0
    total: int = 0
    duration_ms: int = 0
    detail: str = ""

class RebuildRequest(BaseModel):
    repo_key: str
    base_commit_sha: str = "HEAD"
    include_untracked: bool = True
    workspace_path: Optional[str] = None  # 允许用户传入本地任意绝对路径进行分析

class RebuildResponse(BaseModel):
    job_id: str
    status: str
