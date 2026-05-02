from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


RiskLevel = Literal["high", "medium", "low", "unknown"]
CoverageStatus = Literal["covered", "partial", "missing", "unknown"]
ReviewStatus = Literal["unreviewed", "reviewed", "needs_follow_up", "needs_recheck"]
CaptureLevel = Literal["full", "partial", "diff_only"]
ConfidenceLevel = Literal["high", "medium", "low"]
RelationshipType = Literal["primary", "secondary", "inferred"]
TestEvidenceKind = Literal["marker", "naming_convention", "graph_inference", "agent_claim"]
FileAssessmentGenerator = Literal["rules", "codex_agent"]
AgentAssessmentStatus = Literal["not_run", "running", "accepted", "failed", "fallback"]
AssessmentMode = Literal["working_tree", "commit_range", "pull_request"]
EvidenceGrade = Literal["direct", "indirect", "inferred", "claimed", "not_run", "unknown"]
ClaimType = Literal["refactor", "bugfix", "feature", "test", "config", "docs", "cleanup", "unknown"]
ReviewDecision = Literal["safe_to_commit", "needs_recheck", "needs_tests", "do_not_commit_yet", "unknown"]
TestCaseStatus = Literal["added", "modified", "deleted", "unknown"]
TestExtractionConfidence = Literal["certain", "heuristic", "fallback"]
TestIntentSource = Literal["rule_derived", "agent_claim", "generated", "unknown"]
CoveredChangeRelationship = Literal[
    "calls",
    "imports",
    "shares_fixture",
    "co_changed",
    "names_changed_symbol",
    "same_file",
    "graph_inferred",
    "unknown",
]
CommandScope = Literal["test_case", "test_file", "changed_area", "assessment"]
CommandStatus = Literal["not_run", "running", "passed", "failed", "partial", "unknown"]
TestRunEvidenceSource = Literal["codex_command_log", "rerun"]
ExecutedTestCaseSource = Literal["runner_output", "collect_only", "test_file_parse"]
MismatchKind = Literal[
    "claimed_refactor_but_public_surface_changed",
    "claimed_tested_but_no_executed_test_evidence",
    "claimed_ui_only_but_backend_changed",
    "claimed_small_fix_but_many_files_changed",
    "claimed_config_only_but_runtime_code_changed",
]


class RebuildRequest(BaseModel):
    repo_key: str
    base_commit_sha: str = "HEAD"
    include_untracked: bool = True
    workspace_path: Optional[str] = None


class RebuildResponse(BaseModel):
    job_id: str
    status: str


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
    highest_hunk_priority: Optional[int] = None
    mismatch_count: int = 0
    weakest_test_evidence_grade: Optional[EvidenceGrade] = None


class ReviewProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int = 0
    reviewed: int = 0
    needs_follow_up: int = 0
    needs_recheck: int = 0
    unreviewed: int = 0


class AgenticSummaryTimeWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    since_commit: str = ""
    since_commit_time: Optional[str] = None


class AgenticSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_by: Literal["codex_logs", "rules"] = "rules"
    capture_level: CaptureLevel = "diff_only"
    confidence: ConfidenceLevel = "low"
    time_window: AgenticSummaryTimeWindow = Field(default_factory=AgenticSummaryTimeWindow)
    user_design_goal: str = ""
    codex_change_summary: str = ""
    main_objective: str = ""
    key_decisions: List[str] = Field(default_factory=list)
    files_or_areas_changed: List[str] = Field(default_factory=list)
    tests_and_verification: List[str] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)


class AssessmentManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment_id: str
    workspace_snapshot_id: str
    repo_key: str
    status: Literal["ready", "partial", "failed"] = "ready"
    mode: AssessmentMode = "working_tree"
    provenance_capture_level: CaptureLevel = "diff_only"
    mismatch_count: int = 0
    weak_test_evidence_count: int = 0
    review_decision: ReviewDecision = "unknown"
    hunk_queue_preview: List["HunkReviewItem"] = Field(default_factory=list)
    agentic_summary: AgenticSummary = Field(default_factory=AgenticSummary)
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
    evidence_grade: EvidenceGrade = "unknown"
    basis: List[str] = Field(default_factory=list)


class AgentClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str
    type: ClaimType = "unknown"
    text: str = ""
    source: str = ""
    session_id: str = ""
    message_ref: str = ""
    tool_call_ref: str = ""
    related_files: List[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = "low"


class ProvenanceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = ""
    session_id: str = ""
    message_ref: str = ""
    tool_call_ref: str = ""
    command: str = ""
    file_path: str = ""
    hunk_id: str = ""
    confidence: ConfidenceLevel = "low"


class ClaimMismatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mismatch_id: str
    kind: MismatchKind
    claim_id: str
    severity: RiskLevel = "unknown"
    explanation: str = ""
    fact_refs: List[str] = Field(default_factory=list)
    provenance_refs: List[ProvenanceRef] = Field(default_factory=list)


class HunkReviewItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hunk_id: str
    file_id: str
    path: str
    priority: int = 0
    risk_level: RiskLevel = "unknown"
    reasons: List[str] = Field(default_factory=list)
    fact_basis: List[str] = Field(default_factory=list)
    provenance_refs: List[ProvenanceRef] = Field(default_factory=list)
    mismatch_ids: List[str] = Field(default_factory=list)


class TestIntentSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    __test__: ClassVar[bool] = False

    text: str = ""
    source: TestIntentSource = "unknown"
    basis: List[str] = Field(default_factory=list)


class CoveredChangePreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    hunk_id: Optional[str] = None
    risk_level: RiskLevel = "unknown"
    evidence_grade: EvidenceGrade = "unknown"


class TestCaseSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    __test__: ClassVar[bool] = False

    test_case_id: str
    file_id: str
    path: str
    name: str
    status: TestCaseStatus = "unknown"
    extraction_confidence: TestExtractionConfidence = "fallback"
    evidence_grade: EvidenceGrade = "unknown"
    weakest_evidence_grade: EvidenceGrade = "unknown"
    last_status: Literal["passed", "failed", "not_run", "unknown"] = "unknown"
    covered_changes_preview: List[CoveredChangePreview] = Field(default_factory=list)
    highest_risk_covered_hunk_id: Optional[str] = None
    intent_summary: TestIntentSummary = Field(default_factory=TestIntentSummary)


class CoveredChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    symbol: str = ""
    hunk_id: str = ""
    relationship: CoveredChangeRelationship = "unknown"
    evidence_grade: EvidenceGrade = "unknown"
    basis: List[str] = Field(default_factory=list)


class TestCoveredScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    __test__: ClassVar[bool] = False

    title: str
    source: TestIntentSource = "rule_derived"
    basis: List[str] = Field(default_factory=list)


class ExecutedTestCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    __test__: ClassVar[bool] = False

    node_id: str
    name: str
    status: Literal["passed", "failed", "skipped", "unknown"] = "unknown"
    source: ExecutedTestCaseSource = "test_file_parse"
    scenarios: List[TestCoveredScenario] = Field(default_factory=list)
    test_data: List[str] = Field(default_factory=list)


class TestCoveredCodeAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    __test__: ClassVar[bool] = False

    path: str
    symbol: str = ""
    hunk_id: str = ""
    relationship: CoveredChangeRelationship = "unknown"
    evidence_grade: EvidenceGrade = "unknown"
    analysis: str = ""
    basis: List[str] = Field(default_factory=list)


class TestResultAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    __test__: ClassVar[bool] = False

    summary: str = ""
    scenarios: List[TestCoveredScenario] = Field(default_factory=list)
    test_data: List[str] = Field(default_factory=list)
    covered_code_analysis: List[TestCoveredCodeAnalysis] = Field(default_factory=list)
    coverage_gaps: List[str] = Field(default_factory=list)
    source: TestIntentSource = "rule_derived"
    basis: List[str] = Field(default_factory=list)


class TestRunEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    __test__: ClassVar[bool] = False

    run_id: str
    source: TestRunEvidenceSource
    command_id: str = ""
    command: str
    status: CommandStatus = "unknown"
    exit_code: Optional[int] = None
    duration_ms: int = 0
    stdout: str = ""
    stderr: str = ""
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    timed_out: bool = False
    argv: List[str] = Field(default_factory=list)
    executed_cases: List[ExecutedTestCase] = Field(default_factory=list)
    analysis: TestResultAnalysis = Field(default_factory=TestResultAnalysis)
    started_at: str = ""
    finished_at: str = ""
    captured_at: str = ""
    evidence_grade: EvidenceGrade = "unknown"


class RecommendedTestCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command_id: str
    command: str
    reason: str = ""
    scope: CommandScope = "test_file"
    status: CommandStatus = "not_run"
    last_run_id: Optional[str] = None


class TestCaseDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")
    __test__: ClassVar[bool] = False

    test_case: TestCaseSummary
    diff_hunks: List[DiffHunk] = Field(default_factory=list)
    full_body: List[DiffLine] = Field(default_factory=list)
    assertions: List[DiffLine] = Field(default_factory=list)
    covered_scenarios: List[TestCoveredScenario] = Field(default_factory=list)
    test_results: List[TestRunEvidence] = Field(default_factory=list)
    covered_changes: List[CoveredChange] = Field(default_factory=list)
    recommended_commands: List[RecommendedTestCommand] = Field(default_factory=list)
    related_agent_claims: List[AgentClaim] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)


class TestFileSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    __test__: ClassVar[bool] = False

    file_id: str
    path: str
    status: str = "modified"
    additions: int = 0
    deletions: int = 0
    test_case_count: int = 0
    strongest_evidence_grade: EvidenceGrade = "unknown"
    weakest_evidence_grade: EvidenceGrade = "unknown"
    latest_command_status: CommandStatus = "unknown"
    test_cases: List[TestCaseSummary] = Field(default_factory=list)


class TestManagementSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    __test__: ClassVar[bool] = False

    assessment_id: str
    repo_key: str
    changed_test_file_count: int = 0
    test_case_count: int = 0
    evidence_grade_counts: Dict[str, int] = Field(default_factory=dict)
    command_status_counts: Dict[str, int] = Field(default_factory=dict)
    files: List[TestFileSummary] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)


class FileAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    why_changed: str = ""
    impact_summary: str = ""
    test_summary: str = ""
    recommended_action: str = ""
    generated_by: FileAssessmentGenerator = "rules"
    agent_status: AgentAssessmentStatus = "not_run"
    agent_source: Optional[Literal["codex"]] = None
    confidence: ConfidenceLevel = "low"
    evidence_refs: List[str] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)


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
    agent_claims: List[AgentClaim] = Field(default_factory=list)
    mismatches: List[ClaimMismatch] = Field(default_factory=list)
    provenance_refs: List[ProvenanceRef] = Field(default_factory=list)
    hunk_review_items: List[HunkReviewItem] = Field(default_factory=list)
    file_assessment: FileAssessment = Field(default_factory=FileAssessment)
    review_state: FileReviewState


AssessmentManifest.model_rebuild()
