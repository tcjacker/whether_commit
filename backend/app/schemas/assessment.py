from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


RiskLevel = Literal["high", "medium", "low", "unknown"]
CoverageStatus = Literal["covered", "partial", "missing", "unknown"]
ReviewStatus = Literal["unreviewed", "reviewed", "needs_follow_up", "needs_recheck"]
CaptureLevel = Literal["full", "partial", "diff_only"]
ConfidenceLevel = Literal["high", "medium", "low"]
RelationshipType = Literal["primary", "secondary", "inferred"]
TestEvidenceKind = Literal["marker", "naming_convention", "graph_inference", "agent_claim"]


class AssessmentSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str = ""
    overall_risk_level: RiskLevel = "unknown"
    coverage_status: CoverageStatus = "unknown"
    changed_file_count: int = 0
    unreviewed_file_count: int = 0
    affected_capability_count: int = 0
    missing_test_count: int = 0
    agent_sources: List[str] = Field(default_factory=list)
    recommended_review_order: List[str] = Field(default_factory=list)


class ChangedFileSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_id: str
    path: str
    old_path: Optional[str] = None
    status: str = "modified"
    additions: int = 0
    deletions: int = 0
    risk_level: RiskLevel = "unknown"
    coverage_status: CoverageStatus = "unknown"
    review_status: ReviewStatus = "unreviewed"
    agent_sources: List[str] = Field(default_factory=list)
    diff_fingerprint: str


class ReviewProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int = 0
    reviewed: int = 0
    needs_follow_up: int = 0
    needs_recheck: int = 0
    unreviewed: int = 0


class AssessmentManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment_id: str
    workspace_snapshot_id: str
    repo_key: str
    status: Literal["ready", "partial", "failed"] = "ready"
    summary: AssessmentSummary = Field(default_factory=AssessmentSummary)
    file_list: List[ChangedFileSummary] = Field(default_factory=list)
    risk_signals_summary: List[Dict[str, Any]] = Field(default_factory=list)
    agent_sources: List[str] = Field(default_factory=list)
    review_progress: ReviewProgress = Field(default_factory=ReviewProgress)


class DiffLine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["add", "remove", "context", "header"]
    content: str


class DiffHunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hunk_id: str
    old_start: int
    old_lines: int
    new_start: int
    new_lines: int
    hunk_fingerprint: str
    lines: List[DiffLine] = Field(default_factory=list)


class AgentConfidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    files_touched: ConfidenceLevel = "low"
    commands_run: ConfidenceLevel = "low"
    reasoning_summary: ConfidenceLevel = "low"
    tests_run: ConfidenceLevel = "low"


class AgentTestRun(BaseModel):
    model_config = ConfigDict(extra="allow")

    command: str = ""
    status: str = "unknown"


class AgentChangeRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    source: str
    capture_level: CaptureLevel
    evidence_sources: List[str] = Field(default_factory=list)
    confidence: AgentConfidence = Field(default_factory=AgentConfidence)
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    task_summary: str = ""
    declared_intent: str = ""
    reasoning_summary: str = ""
    files_touched: List[str] = Field(default_factory=list)
    commands_run: List[str] = Field(default_factory=list)
    tests_run: List[AgentTestRun] = Field(default_factory=list)
    known_limitations: List[str] = Field(default_factory=list)
    raw_log_ref: str = ""


class TestRelationship(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_id: str
    path: str
    relationship: RelationshipType = "inferred"
    confidence: ConfidenceLevel = "low"
    last_status: Literal["passed", "failed", "not_run", "unknown"] = "unknown"
    evidence: TestEvidenceKind = "graph_inference"


class FileAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    why_changed: str = ""
    impact_summary: str = ""
    test_summary: str = ""
    recommended_action: str = ""


class FileReviewState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_status: ReviewStatus = "unreviewed"
    diff_fingerprint: str
    reviewer: Optional[str] = None
    reviewed_at: Optional[str] = None
    notes: List[str] = Field(default_factory=list)


class ReviewStateFileItem(FileReviewState):
    file_id: str
    path: str


class ReviewState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: Literal["assessment"] = "assessment"
    file_reviews: List[ReviewStateFileItem] = Field(default_factory=list)


class ChangedFileDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file: ChangedFileSummary
    diff_hunks: List[DiffHunk] = Field(default_factory=list)
    changed_symbols: List[str] = Field(default_factory=list)
    related_agent_records: List[AgentChangeRecord] = Field(default_factory=list)
    related_tests: List[TestRelationship] = Field(default_factory=list)
    impact_facts: List[Dict[str, Any]] = Field(default_factory=list)
    file_assessment: FileAssessment = Field(default_factory=FileAssessment)
    review_state: FileReviewState
