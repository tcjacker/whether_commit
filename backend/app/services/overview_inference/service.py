from __future__ import annotations

import inspect
from datetime import datetime, timezone
from typing import Any, Callable, Dict

from app.config.settings import ObservabilitySettings
from app.schemas.overview import RecentAIChange
from app.services.capability_inference.service import CapabilityInferenceService
from app.services.overview_inference.agent_harness import AgentContextHarness
from app.services.overview_inference.change_risk_summary import ChangeRiskSummaryBuilder
from app.services.overview_inference.file_review_summary import FileReviewSummaryBuilder
from app.services.overview_inference.test_asset_summary import TestAssetSummaryBuilder
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
        agent_harness_service: AgentContextHarness | None = None,
        change_risk_summary_builder: ChangeRiskSummaryBuilder | None = None,
        test_asset_summary_builder: TestAssetSummaryBuilder | None = None,
        file_review_summary_builder: FileReviewSummaryBuilder | None = None,
    ):
        self.agent_reasoning_service = agent_reasoning_service or AgentReasoningService.from_settings(
            ObservabilitySettings.from_env()
        )
        self.capability_inference_service = capability_inference_service or CapabilityInferenceService()
        self.agent_harness_service = agent_harness_service
        self.change_risk_summary_builder = change_risk_summary_builder or ChangeRiskSummaryBuilder()
        self.test_asset_summary_builder = test_asset_summary_builder or TestAssetSummaryBuilder()
        self.file_review_summary_builder = file_review_summary_builder or FileReviewSummaryBuilder()

    def _as_list(self, value: Any) -> list[Any]:
        if not value:
            return []
        if isinstance(value, list):
            return value
        return [value]

    def _empty_change_risk_summary(self) -> Dict[str, Any]:
        return self.change_risk_summary_builder.build_clean()

    def _empty_test_asset_summary(self) -> Dict[str, Any]:
        return self.test_asset_summary_builder.build_clean()

    def _empty_file_review_summaries(self) -> list[Dict[str, Any]]:
        return self.file_review_summary_builder.build_clean()

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
                "what_this_app_seems_to_do": "未检测到待分析的变更",
                "technical_narrative": "当前工作区与基线提交一致，无需执行 AI 变更分析。",
                "core_flow": "HEAD -> 干净工作区",
            },
            "capability_map": [],
            "journeys": [],
            "architecture_overview": {"nodes": [], "edges": []},
            "recent_ai_changes": [],
            "change_themes": [],
            "change_risk_summary": self._empty_change_risk_summary(),
            "test_asset_summary": self._empty_test_asset_summary(),
            "file_review_summaries": self._empty_file_review_summaries(),
            "agent_harness_status": None,
            "agent_harness_metadata": {},
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
        progress_reporter: Callable[[str], None] | None = None,
    ) -> Dict[str, Any]:
        agent_reasoning = self.agent_reasoning_service.analyze(graph_data, change_data, verification_data)
        has_changes = len(change_data.get("changed_files", [])) > 0
        capability_map = self.capability_inference_service.infer(
            graph_data=graph_data,
            change_data=change_data,
            verification_data=verification_data,
            agent_reasoning=agent_reasoning,
        )
        change_risk_summary = self.change_risk_summary_builder.build(
            change_data=change_data,
            verification_data=verification_data,
            capability_map=capability_map,
        )
        test_asset_summary = self.test_asset_summary_builder.build(
            change_data=change_data,
            verification_data=verification_data,
            capability_map=capability_map,
        )
        file_review_summaries = self.file_review_summary_builder.build(
            change_data=change_data,
            verification_data=verification_data,
            change_risk_summary=change_risk_summary,
            test_asset_summary=test_asset_summary,
        )
        self._report_progress(progress_reporter, "prepare_agent_context")
        agent_harness_result = self._run_agent_harness(
            graph_data,
            change_data,
            verification_data,
            change_risk_summary=change_risk_summary,
            file_review_summaries=file_review_summaries,
            progress_reporter=progress_reporter,
        )
        self._report_progress(progress_reporter, "validate_agent_output")

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
                    "change_title": change_data.get("change_title", "未知变更"),
                    "summary": agent_reasoning.get(
                        "technical_change_summary",
                        "技术影响基于工作区差异和 AST 提取结果推断。",
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
                        change_data.get("why_impacted", "在源代码文件中检测到直接修改。"),
                    ),
                    "impact_reasons": impact_reasons,
                    "direct_impacts": direct_impacts,
                    "transitive_impacts": transitive_impacts,
                    "risk_factors": agent_reasoning.get(
                        "risk_factors",
                        change_data.get("risk_factors", ["后端变更路径尚未验证"] if not verification_data.get("affected_tests") else []),
                    ),
                    "review_recommendations": agent_reasoning.get("review_recommendations", change_data.get("minimal_review_set", [])),
                    "linked_tests": change_data.get("linked_tests", []),
                    "verification_coverage": "covered" if verification_data.get("affected_tests") else "missing",
                    "confidence": agent_reasoning.get("confidence", change_data.get("confidence", "medium")),
                    "change_intent": agent_reasoning.get("change_intent", change_data.get("change_intent", "")),
                    "coherence": change_data.get("coherence", "unknown"),
                    "coherence_groups": change_data.get("coherence_groups", []),
                    "affected_capabilities": [
                        item["name"]
                        for item in change_risk_summary["existing_feature_impact"]["affected_capabilities"]
                    ],
                    "technical_entrypoints": list(
                        dict.fromkeys(
                            entry
                            for item in change_risk_summary["existing_feature_impact"]["affected_capabilities"]
                            for entry in item["technical_entrypoints"]
                        )
                    ),
                }
            )

        result = {
            "repo": {"repo_key": repo_key, "name": repo_key, "default_branch": "main"},
            "snapshot": {
                "base_commit_sha": change_data.get("base_commit_sha", "HEAD"),
                "workspace_snapshot_id": snapshot_id,
                "has_pending_changes": has_changes,
                "status": "ready",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            "project_summary": {
                "what_this_app_seems_to_do": "正在对后端系统进行技术分析",
                "technical_narrative": (
                    f"已分析 {len(graph_data.get('modules', []))} 个模块、"
                    f"{len(graph_data.get('symbols', []))} 个符号，以及 "
                    f"{len(graph_data.get('routes', []))} 条路由。"
                ),
                "core_flow": "客户端 -> API 处理器 -> 服务",
                "overall_assessment": change_risk_summary["headline"]["overall_risk_summary"],
                "impact_level": change_risk_summary["headline"]["overall_risk_level"],
                "impact_basis": [],
                "affected_capability_count": change_risk_summary["existing_feature_impact"]["affected_capability_count"],
                "affected_entrypoints": [],
                "critical_paths": [],
                "verification_gaps": list(agent_reasoning.get("validation_gaps", [])),
                "priority_themes": [],
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
            "change_themes": [],
            "change_risk_summary": change_risk_summary,
            "test_asset_summary": test_asset_summary,
            "file_review_summaries": file_review_summaries,
            "agent_harness_status": None,
            "agent_harness_metadata": {},
            "verification_status": verification_data,
            "warnings": list(
                dict.fromkeys(
                    self._build_warnings(agent_reasoning)
                    + [
                        "后端仓库的领域能力与用户旅程推断尚未启用，待 LLM 推理整合后开放。",
                        *agent_reasoning.get("unknowns", []),
                        *agent_reasoning.get("validation_gaps", []),
                    ]
                )
            ),
        }
        self._apply_agent_harness_result(result, agent_harness_result)
        self._report_progress(progress_reporter, "build_overview_payload")
        return result

    def _report_progress(self, progress_reporter: Callable[[str], None] | None, step: str) -> None:
        if progress_reporter is not None:
            progress_reporter(step)

    def _build_warnings(self, agent_reasoning: Dict[str, Any]) -> list[str]:
        warnings: list[str] = []
        llm_reasoning = agent_reasoning.get("llm_reasoning", {})
        if llm_reasoning.get("enabled") and llm_reasoning.get("status") not in {"accepted", "disabled"}:
            warnings.append(f"LLM_REASONING_FALLBACK: {llm_reasoning.get('status', 'unknown')}")
        return warnings

    def _run_agent_harness(
        self,
        graph_data: Dict[str, Any],
        change_data: Dict[str, Any],
        verification_data: Dict[str, Any],
        change_risk_summary: Dict[str, Any],
        file_review_summaries: list[Dict[str, Any]] | None = None,
        progress_reporter: Callable[[str], None] | None = None,
    ) -> Dict[str, Any] | None:
        if self.agent_harness_service is None:
            return None

        run_method = self.agent_harness_service.run
        try:
            parameters = inspect.signature(run_method).parameters
        except (TypeError, ValueError):
            parameters = {}

        if progress_reporter is not None and (
            "progress_reporter" in parameters or any(param.kind == inspect.Parameter.VAR_KEYWORD for param in parameters.values())
        ):
            kwargs: Dict[str, Any] = {"progress_reporter": progress_reporter}
            if "change_risk_summary" in parameters or any(
                param.kind == inspect.Parameter.VAR_KEYWORD for param in parameters.values()
            ):
                kwargs["change_risk_summary"] = change_risk_summary
            if "file_review_summaries" in parameters or any(
                param.kind == inspect.Parameter.VAR_KEYWORD for param in parameters.values()
            ):
                kwargs["file_review_summaries"] = file_review_summaries or []
            return run_method(graph_data, change_data, verification_data, **kwargs)

        if "file_review_summaries" in parameters or any(
            param.kind == inspect.Parameter.VAR_KEYWORD for param in parameters.values()
        ):
            kwargs: Dict[str, Any] = {"file_review_summaries": file_review_summaries or []}
            if "change_risk_summary" in parameters or any(
                param.kind == inspect.Parameter.VAR_KEYWORD for param in parameters.values()
            ):
                kwargs["change_risk_summary"] = change_risk_summary
            return run_method(graph_data, change_data, verification_data, **kwargs)

        if "change_risk_summary" in parameters or any(
            param.kind == inspect.Parameter.VAR_KEYWORD for param in parameters.values()
        ):
            return run_method(graph_data, change_data, verification_data, change_risk_summary=change_risk_summary)

        return run_method(graph_data, change_data, verification_data)

    def _apply_agent_harness_result(
        self,
        result: Dict[str, Any],
        agent_harness_result: Dict[str, Any] | None,
    ) -> None:
        if not agent_harness_result:
            self._apply_change_risk_summary_agent_copy(result["change_risk_summary"], response={}, status=None)
            return

        agent_harness_result = self._normalize_agent_harness_result(agent_harness_result, result)
        result["agent_harness_status"] = agent_harness_result.get("status")
        result["agent_harness_metadata"] = agent_harness_result.get("metadata", {})

        response = agent_harness_result.get("response") or {}
        status = agent_harness_result.get("status")
        if response.get("project_summary"):
            self._merge_agent_project_summary(result["project_summary"], response["project_summary"])
        self._apply_change_risk_summary_agent_copy(result["change_risk_summary"], response=response, status=status)
        self._apply_file_review_agent_copy(result["file_review_summaries"], response=response, status=status)
        result["project_summary"]["impact_level"] = result["change_risk_summary"]["headline"]["overall_risk_level"]
        result["project_summary"]["overall_assessment"] = result["change_risk_summary"]["headline"]["overall_risk_summary"]
        if response.get("change_themes") is not None:
            result["change_themes"] = response.get("change_themes", [])
        if status == "accepted":
            projected_recent_changes = self._project_recent_ai_changes_from_themes(
                response.get("change_themes", []),
                result["recent_ai_changes"],
            )
            if projected_recent_changes:
                result["recent_ai_changes"] = projected_recent_changes
            else:
                normalized_legacy_recent_changes = self._normalize_recent_ai_changes(
                    response.get("recent_ai_changes", []),
                )
                if normalized_legacy_recent_changes:
                    result["recent_ai_changes"] = normalized_legacy_recent_changes
        if status and status != "accepted":
            result["warnings"] = list(dict.fromkeys(result["warnings"] + [f"AGENT_HARNESS_FALLBACK: {status}"]))

    def _apply_change_risk_summary_agent_copy(
        self,
        summary: Dict[str, Any],
        response: Dict[str, Any],
        status: str | None,
    ) -> None:
        if status == "accepted":
            summary["headline"]["overall_risk_summary"] = (
                response.get("overall_risk_summary")
                or response.get("project_summary", {}).get("overall_assessment")
                or summary["headline"]["overall_risk_summary"]
            )
            summary["headline"]["recommended_focus"] = (
                response.get("recommended_focus") or summary["headline"]["recommended_focus"]
            )
            summary["existing_feature_impact"]["business_impact_summary"] = (
                response.get("business_impact_summary")
                or summary["existing_feature_impact"]["business_impact_summary"]
            )

    def _apply_file_review_agent_copy(
        self,
        summaries: list[Dict[str, Any]],
        response: Dict[str, Any],
        status: str | None,
    ) -> None:
        if status != "accepted":
            return

        agent_items = response.get("file_review_summaries", [])
        if not isinstance(agent_items, list):
            return

        summaries_by_path = {
            item.get("path"): item
            for item in summaries
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        }
        for agent_item in agent_items:
            if not isinstance(agent_item, dict):
                continue
            path = agent_item.get("path")
            if not isinstance(path, str) or path not in summaries_by_path:
                continue

            target = summaries_by_path[path]
            product_meaning = agent_item.get("product_meaning")
            if isinstance(product_meaning, str) and product_meaning.strip():
                target["product_meaning"] = product_meaning.strip()

            review_focus = agent_item.get("review_focus")
            if isinstance(review_focus, list):
                normalized_focus = [str(item) for item in review_focus if item]
                if normalized_focus:
                    target["review_focus"] = normalized_focus

            intent_evidence = agent_item.get("intent_evidence")
            if isinstance(intent_evidence, list):
                normalized_evidence = [str(item) for item in intent_evidence if item]
                if normalized_evidence:
                    target["intent_evidence"] = normalized_evidence

            if target.get("generated_by") == "rules":
                target["generated_by"] = "rules+agent"

    def _normalize_agent_harness_result(
        self,
        agent_harness_result: Dict[str, Any],
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        status = agent_harness_result.get("status")
        response = agent_harness_result.get("response") or {}
        metadata = dict(agent_harness_result.get("metadata") or {})

        if status != "accepted":
            return {
                "status": status,
                "response": response,
                "metadata": metadata,
            }

        impact_basis = response.get("project_summary", {}).get("impact_basis")
        if impact_basis and not self._has_traceable_impact_basis(impact_basis, result):
            validation_issues = list(metadata.get("validation_issues") or [])
            validation_issues.append("untraceable_impact_basis")
            metadata["validation_issues"] = list(dict.fromkeys(validation_issues))
            return {
                "status": "validation_failed",
                "response": None,
                "metadata": metadata,
            }

        return {
            "status": status,
            "response": response,
            "metadata": metadata,
        }

    def _has_traceable_impact_basis(
        self,
        impact_basis: list[Any],
        result: Dict[str, Any],
    ) -> bool:
        if not impact_basis:
            return False

        allowed_surfaces = self._build_allowed_changed_surfaces(result)
        return all(
            self._is_traceable_impact_basis_entry(
                entry,
                changed_files=allowed_surfaces["files"],
                changed_symbols=allowed_surfaces["symbols"],
                changed_routes=allowed_surfaces["routes"],
                changed_schemas=allowed_surfaces["schemas"],
                changed_jobs=allowed_surfaces["jobs"],
                module_ids=allowed_surfaces["modules"],
            )
            for entry in impact_basis
        )

    def _build_allowed_changed_surfaces(self, result: Dict[str, Any]) -> Dict[str, set[str]]:
        recent_ai_changes = result.get("recent_ai_changes", [])
        primary_change = recent_ai_changes[0] if recent_ai_changes else {}
        verification_status = result.get("verification_status", {})

        return {
            "files": set(primary_change.get("changed_files", []))
            | set(verification_status.get("verified_changed_paths", []))
            | set(verification_status.get("unverified_changed_paths", []))
            | set(verification_status.get("missing_tests_for_changed_paths", []))
            | {
                item.get("path")
                for item in verification_status.get("critical_changed_paths", [])
                if isinstance(item, dict) and isinstance(item.get("path"), str)
            },
            "symbols": set(primary_change.get("changed_symbols", [])),
            "routes": set(primary_change.get("changed_routes", [])),
            "schemas": set(primary_change.get("changed_schemas", [])),
            "jobs": set(primary_change.get("changed_jobs", [])),
            "modules": set(primary_change.get("directly_changed_modules", []))
            | set(primary_change.get("transitively_affected_modules", []))
            | set(verification_status.get("verified_changed_modules", []))
            | set(verification_status.get("unverified_changed_modules", [])),
        }

    def _is_traceable_impact_basis_entry(
        self,
        entry: Any,
        *,
        changed_files: set[str],
        changed_symbols: set[str],
        changed_routes: set[str],
        changed_schemas: set[str],
        changed_jobs: set[str],
        module_ids: set[str],
    ) -> bool:
        if isinstance(entry, str):
            return (
                entry in changed_files
                or entry in changed_symbols
                or entry in changed_routes
                or entry in changed_schemas
                or entry in changed_jobs
                or entry in module_ids
            )

        if not isinstance(entry, dict):
            return False

        direct_refs = [
            entry.get("path"),
            entry.get("file"),
            entry.get("symbol"),
            entry.get("route"),
            entry.get("module"),
            entry.get("entity_id"),
            entry.get("target_id"),
            entry.get("schema"),
            entry.get("job"),
        ]
        if any(ref in changed_files for ref in direct_refs if isinstance(ref, str)):
            return True
        if any(ref in changed_symbols for ref in direct_refs if isinstance(ref, str)):
            return True
        if any(ref in changed_routes for ref in direct_refs if isinstance(ref, str)):
            return True
        if any(ref in changed_schemas for ref in direct_refs if isinstance(ref, str)):
            return True
        if any(ref in changed_jobs for ref in direct_refs if isinstance(ref, str)):
            return True
        if any(ref in module_ids for ref in direct_refs if isinstance(ref, str)):
            return True

        kind = entry.get("kind")
        value = entry.get("value")
        target_id = entry.get("target_id")
        if kind in {"file", "path"} and isinstance(value, str):
            return value in changed_files
        if kind in {"file", "path"} and isinstance(target_id, str):
            return target_id in changed_files
        if kind == "symbol" and isinstance(value, str):
            return value in changed_symbols
        if kind == "symbol" and isinstance(target_id, str):
            return target_id in changed_symbols
        if kind == "route" and isinstance(value, str):
            return value in changed_routes
        if kind == "route" and isinstance(target_id, str):
            return target_id in changed_routes
        if kind == "schema" and isinstance(value, str):
            return value in changed_schemas
        if kind == "schema" and isinstance(target_id, str):
            return target_id in changed_schemas
        if kind == "job" and isinstance(value, str):
            return value in changed_jobs
        if kind == "job" and isinstance(target_id, str):
            return target_id in changed_jobs
        if kind in {"module", "entity"} and isinstance(value, str):
            return value in module_ids
        if kind in {"module", "entity"} and isinstance(target_id, str):
            return target_id in module_ids
        return False

    def _project_recent_ai_changes_from_themes(
        self,
        change_themes: list[dict[str, Any]],
        source_recent_changes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not change_themes:
            return []

        source_change = source_recent_changes[0] if source_recent_changes else {}
        projected_changes: list[dict[str, Any]] = []

        for index, theme in enumerate(change_themes, start=1):
            if not isinstance(theme, dict):
                continue

            projected_change = {
                "change_id": (theme.get("change_ids") or [f"chg_theme_{index}"])[0],
                "change_title": theme.get("name") or theme.get("theme_key") or f"Theme {index}",
                "summary": theme.get("summary", source_change.get("summary", "")),
                "changed_files": source_change.get("changed_files", []),
                "changed_symbols": source_change.get("changed_symbols", []),
                "changed_routes": source_change.get("changed_routes", []),
                "changed_schemas": source_change.get("changed_schemas", []),
                "changed_jobs": source_change.get("changed_jobs", []),
                "change_types": source_change.get("change_types", []),
                "directly_changed_modules": source_change.get("directly_changed_modules", []),
                "transitively_affected_modules": source_change.get("transitively_affected_modules", []),
                "affected_entrypoints": source_change.get("affected_entrypoints", []),
                "affected_data_objects": source_change.get("affected_data_objects", []),
                "why_impacted": theme.get("summary", source_change.get("why_impacted", "")),
                "impact_reasons": [theme.get("summary")] if theme.get("summary") else source_change.get("impact_reasons", []),
                "direct_impacts": source_change.get("direct_impacts", []),
                "transitive_impacts": source_change.get("transitive_impacts", []),
                "risk_factors": source_change.get("risk_factors", []),
                "review_recommendations": source_change.get("review_recommendations", []),
                "linked_tests": source_change.get("linked_tests", []),
                "verification_coverage": source_change.get("verification_coverage", "unknown"),
                "confidence": source_change.get("confidence", "low"),
                "change_intent": source_change.get("change_intent", ""),
                "coherence": source_change.get("coherence", "unknown"),
                "coherence_groups": source_change.get("coherence_groups", []),
            }

            try:
                projected_changes.append(RecentAIChange.model_validate(projected_change).model_dump())
            except Exception:
                continue

        return projected_changes

    def _normalize_recent_ai_changes(self, recent_ai_changes: list[Any]) -> list[dict[str, Any]]:
        normalized_changes: list[dict[str, Any]] = []
        for raw_change in recent_ai_changes:
            try:
                normalized_changes.append(RecentAIChange.model_validate(raw_change).model_dump())
            except Exception:
                continue
        return normalized_changes

    def _merge_agent_project_summary(
        self,
        project_summary: Dict[str, Any],
        agent_project_summary: Dict[str, Any],
    ) -> None:
        allowed_fields = {
            "overall_assessment",
            "impact_level",
            "impact_basis",
            "affected_capability_count",
            "affected_entrypoints",
            "critical_paths",
            "verification_gaps",
            "priority_themes",
        }
        for field in allowed_fields:
            if field in agent_project_summary:
                project_summary[field] = agent_project_summary[field]
