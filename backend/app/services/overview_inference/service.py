from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from app.config.settings import ObservabilitySettings
from app.services.capability_inference.service import CapabilityInferenceService
from app.services.overview_inference.agent_reasoning import AgentReasoningService


class OverviewInferenceService:
    """
    Builds the overview payload from normalized graph/change/verification facts.
    The current implementation intentionally prefers technical summaries over
    speculative product narratives for backend-heavy repositories.
    """

    def __init__(
        self,
        agent_reasoning_service: AgentReasoningService | None = None,
        capability_inference_service: CapabilityInferenceService | None = None,
    ):
        self.agent_reasoning_service = agent_reasoning_service or AgentReasoningService.from_settings(
            ObservabilitySettings.from_env()
        )
        self.capability_inference_service = capability_inference_service or CapabilityInferenceService()

    def _as_list(self, value: Any) -> list[Any]:
        if not value:
            return []
        if isinstance(value, list):
            return value
        return [value]

    def build_clean_overview(self, repo_key: str, workspace_snapshot: Any) -> Dict[str, Any]:
        return {
            "repo": {"repo_key": repo_key, "name": repo_key, "default_branch": "main"},
            "snapshot": {
                "base_commit_sha": workspace_snapshot.base_commit_sha,
                "workspace_snapshot_id": workspace_snapshot.workspace_snapshot_id,
                "has_pending_changes": False,
                "status": "ready",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            "project_summary": {
                "what_this_app_seems_to_do": "No pending changes detected",
                "technical_narrative": "Working tree matches the base commit; no AI change analysis was required.",
                "core_flow": "HEAD -> clean working tree",
            },
            "capability_map": [],
            "journeys": [],
            "architecture_overview": {"nodes": [], "edges": []},
            "recent_ai_changes": [],
            "verification_status": {
                "build": {"status": "unknown"},
                "unit_tests": {"status": "unknown"},
                "integration_tests": {"status": "unknown"},
                "scenario_replay": {"status": "unknown"},
                "critical_paths": [],
                "unverified_areas": [],
                "verified_changed_modules": [],
                "unverified_changed_modules": [],
                "affected_tests": [],
                "missing_tests_for_changed_paths": [],
                "critical_changed_paths": [],
                "evidence_by_path": {},
            },
            "warnings": ["NO_PENDING_CHANGES"],
        }

    def build_overview(
        self,
        repo_key: str,
        snapshot_id: str,
        graph_data: Dict[str, Any],
        change_data: Dict[str, Any],
        verification_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        agent_reasoning = self.agent_reasoning_service.analyze(graph_data, change_data, verification_data)
        has_changes = len(change_data.get("changed_files", [])) > 0
        capability_map = self.capability_inference_service.infer(
            graph_data=graph_data,
            change_data=change_data,
            verification_data=verification_data,
            agent_reasoning=agent_reasoning,
        )

        recent_changes = []
        if has_changes:
            direct_impacts = self._as_list(change_data.get("direct_impacts")) or change_data.get("directly_changed_modules", [])
            transitive_impacts = self._as_list(change_data.get("transitive_impacts")) or change_data.get(
                "transitively_affected_modules",
                [],
            )
            impact_reasons = self._as_list(change_data.get("impact_reasons"))
            if not impact_reasons and agent_reasoning.get("why_impacted"):
                impact_reasons = [agent_reasoning["why_impacted"]]

            recent_changes.append(
                {
                    "change_id": "chg_latest",
                    "change_title": change_data.get("change_title", "Unknown change"),
                    "summary": agent_reasoning.get(
                        "technical_change_summary",
                        "Technical impact inferred from working tree diffs and AST extraction.",
                    ),
                    "changed_files": change_data.get("changed_files", []),
                    "changed_symbols": change_data.get("changed_symbols", []),
                    "changed_routes": change_data.get("changed_routes", []),
                    "changed_schemas": change_data.get("changed_schemas", []),
                    "changed_jobs": change_data.get("changed_jobs", []),
                    "change_types": agent_reasoning.get("change_types", change_data.get("change_types", ["code_modification"])),
                    "directly_changed_modules": change_data.get("directly_changed_modules", []),
                    "transitively_affected_modules": change_data.get("transitively_affected_modules", []),
                    "affected_entrypoints": change_data.get("affected_entrypoints", []),
                    "affected_data_objects": change_data.get("affected_data_objects", []),
                    "why_impacted": agent_reasoning.get(
                        "why_impacted",
                        change_data.get("why_impacted", "Direct modifications found in source code files."),
                    ),
                    "impact_reasons": impact_reasons,
                    "direct_impacts": direct_impacts,
                    "transitive_impacts": transitive_impacts,
                    "risk_factors": agent_reasoning.get(
                        "risk_factors",
                        change_data.get("risk_factors", ["Unverified backend paths"] if not verification_data.get("affected_tests") else []),
                    ),
                    "review_recommendations": agent_reasoning.get("review_recommendations", change_data.get("minimal_review_set", [])),
                    "linked_tests": change_data.get("linked_tests", []),
                    "verification_coverage": "covered" if verification_data.get("affected_tests") else "missing",
                    "confidence": agent_reasoning.get("confidence", change_data.get("confidence", "medium")),
                    "change_intent": agent_reasoning.get("change_intent", change_data.get("change_intent", "")),
                    "coherence": change_data.get("coherence", "unknown"),
                    "coherence_groups": change_data.get("coherence_groups", []),
                }
            )

        return {
            "repo": {"repo_key": repo_key, "name": repo_key, "default_branch": "main"},
            "snapshot": {
                "base_commit_sha": change_data.get("base_commit_sha", "HEAD"),
                "workspace_snapshot_id": snapshot_id,
                "has_pending_changes": has_changes,
                "status": "ready",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            "project_summary": {
                "what_this_app_seems_to_do": "Backend system under technical analysis",
                "technical_narrative": (
                    f"Analyzed {len(graph_data.get('modules', []))} modules, "
                    f"{len(graph_data.get('symbols', []))} symbols, and "
                    f"{len(graph_data.get('routes', []))} routes."
                ),
                "core_flow": "Client -> API Handler -> Service",
                "agent_reasoning": agent_reasoning,
            },
            "capability_map": capability_map,
            "journeys": [],
            "architecture_overview": {
                "nodes": [
                    {
                        "id": module["module_id"],
                        "name": module["name"],
                        "type": module["type"],
                        "health": "healthy",
                    }
                    for module in graph_data.get("modules", [])
                ],
                "edges": [
                    {
                        "source": dependency["from"],
                        "target": dependency["to"],
                        "type": dependency["type"],
                    }
                    for dependency in graph_data.get("dependencies", [])
                ],
            },
            "recent_ai_changes": recent_changes,
            "verification_status": verification_data,
            "warnings": list(
                dict.fromkeys(
                    self._build_warnings(agent_reasoning)
                    + [
                        "Domain capabilities and journeys are disabled for backend repos until LLM reasoning is integrated.",
                        *agent_reasoning.get("unknowns", []),
                        *agent_reasoning.get("validation_gaps", []),
                    ]
                )
            ),
        }

    def _build_warnings(self, agent_reasoning: Dict[str, Any]) -> list[str]:
        warnings: list[str] = []
        llm_reasoning = agent_reasoning.get("llm_reasoning", {})
        if llm_reasoning.get("enabled") and llm_reasoning.get("status") not in {"accepted", "disabled"}:
            warnings.append(f"LLM_REASONING_FALLBACK: {llm_reasoning.get('status', 'unknown')}")
        return warnings
