from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

AgentHarnessReadTargetType = Literal["file", "symbol", "call_chain", "verification_context"]
AgentHarnessStatus = Literal["accepted", "fallback", "timeout", "validation_failed", "budget_exceeded"]


class AgentHarnessReadRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    target_type: AgentHarnessReadTargetType
    target_id: str
    reason: str


class AgentHarnessProjectSummary(BaseModel):
    model_config = ConfigDict(extra="allow")

    overall_assessment: str = ""
    impact_level: Literal["high", "medium", "low", "unknown"] = "unknown"
    impact_basis: List[Dict[str, Any]] = Field(default_factory=list)
    affected_capability_count: int = 0
    affected_entrypoints: List[str] = Field(default_factory=list)
    critical_paths: List[str] = Field(default_factory=list)
    verification_gaps: List[str] = Field(default_factory=list)
    priority_themes: List[str] = Field(default_factory=list)


class AgentHarnessCapability(BaseModel):
    model_config = ConfigDict(extra="allow")

    capability_key: str = ""
    name: str = ""
    impact_status: Literal["unknown", "untouched", "directly_changed", "indirectly_impacted", "high_risk_unverified"] = "unknown"
    impact_reason: str = ""
    related_themes: List[str] = Field(default_factory=list)
    verification_status: Literal["unknown", "verified", "unverified", "partial", "covered", "missing"] = "unknown"


class AgentHarnessChangeTheme(BaseModel):
    model_config = ConfigDict(extra="allow")

    theme_key: str = ""
    name: str = ""
    summary: str = ""
    capability_keys: List[str] = Field(default_factory=list)
    change_ids: List[str] = Field(default_factory=list)


class AgentHarnessResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: AgentHarnessStatus
    read_requests: List[AgentHarnessReadRequest] = Field(default_factory=list)
    project_summary: AgentHarnessProjectSummary
    capabilities: List[AgentHarnessCapability] = Field(default_factory=list)
    change_themes: List[AgentHarnessChangeTheme] = Field(default_factory=list)
    recent_ai_changes: List[Dict[str, Any]] = Field(default_factory=list)
    file_review_summaries: List[Dict[str, Any]] = Field(default_factory=list)
    overall_risk_summary: str = ""
    recommended_focus: List[str] = Field(default_factory=list)
    business_impact_summary: str = ""
