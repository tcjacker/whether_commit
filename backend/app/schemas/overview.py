from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

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


class ProjectSummary(BaseModel):
    what_this_app_seems_to_do: str = ""
    technical_narrative: str = ""
    core_flow: str = ""
    agent_reasoning: Optional[AgentReasoning] = None


class ImpactItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    entity_id: Optional[str] = None
    reason: str = ""
    evidence: List[Any] = []
    distance: Optional[int] = None
    direction: Optional[str] = None


class RecentAIChange(BaseModel):
    change_id: str = "chg_unknown"
    change_title: str
    summary: str = ""
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
    verification_status: VerificationStatus = VerificationStatus()
    warnings: List[str] = []

class RebuildRequest(BaseModel):
    repo_key: str
    base_commit_sha: str = "HEAD"
    include_untracked: bool = True
    workspace_path: Optional[str] = None  # 允许用户传入本地任意绝对路径进行分析

class RebuildResponse(BaseModel):
    job_id: str
    status: str
