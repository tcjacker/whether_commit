from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping

from pydantic import ValidationError

from app.schemas.agent_harness import AgentHarnessReadRequest, AgentHarnessResponse
from app.services.overview_inference.context_manifest import ContextManifest


class AgentContextHarness:
    def __init__(
        self,
        provider: Callable[[Dict[str, Any]], Any],
        max_rounds: int = 2,
        max_read_requests: int = 4,
    ) -> None:
        self.provider = provider
        self.max_rounds = max_rounds
        self.max_read_requests = max_read_requests

    def run(
        self,
        graph_data: Dict[str, Any],
        change_data: Dict[str, Any],
        verification_data: Dict[str, Any],
        change_risk_summary: Dict[str, Any] | None = None,
        file_review_summaries: List[Dict[str, Any]] | None = None,
        progress_reporter: Callable[[str], None] | None = None,
    ) -> Dict[str, Any]:
        manifest = ContextManifest.from_sources(graph_data, change_data, verification_data)
        requested_context: List[Dict[str, Any]] = []
        requests_used = 0

        for round_number in range(1, self.max_rounds + 1):
            self._report_progress(progress_reporter, f"agent_round_{round_number}")
            payload = {
                "round": round_number,
                "facts": self._build_facts(
                    graph_data,
                    change_data,
                    verification_data,
                    change_risk_summary or {},
                    file_review_summaries or [],
                ),
                "manifest": manifest.to_prompt_manifest(),
            }
            if requested_context:
                payload["requested_context"] = requested_context

            try:
                raw_response = self.provider(payload)
            except Exception as exc:
                return self._result(
                    status="fallback",
                    response=None,
                    rounds_used=round_number,
                    requests_used=requests_used,
                    validation_issues=[str(exc)],
                )

            if not isinstance(raw_response, Mapping):
                return self._result(
                    status="validation_failed",
                    response=None,
                    rounds_used=round_number,
                    requests_used=requests_used,
                    validation_issues=["provider_response_not_mapping"],
                )

            if raw_response.get("status") == "needs_more_context":
                read_requests, validation_issues = self._parse_read_requests(raw_response.get("read_requests", []))
                if validation_issues:
                    return self._result("validation_failed", None, round_number, requests_used, validation_issues)
                if requests_used + len(read_requests) > self.max_read_requests:
                    return self._result("budget_exceeded", None, round_number, requests_used, [])

                requested_context, manifest_issues = manifest.resolve_requests(read_requests)
                if manifest_issues:
                    return self._result("validation_failed", None, round_number, requests_used, manifest_issues)

                requests_used += len(read_requests)
                if round_number >= self.max_rounds:
                    return self._result("budget_exceeded", None, round_number, requests_used, [])
                continue

            try:
                response = AgentHarnessResponse.model_validate(raw_response)
            except ValidationError as exc:
                return self._result(
                    status="validation_failed",
                    response=None,
                    rounds_used=round_number,
                    requests_used=requests_used,
                    validation_issues=[exc.errors()[0]["type"]],
                )

            return self._result(
                status=response.status,
                response=response.model_dump(),
                rounds_used=round_number,
                requests_used=requests_used,
                validation_issues=[],
            )

        return self._result("budget_exceeded", None, self.max_rounds, requests_used, [])

    def _report_progress(self, progress_reporter: Callable[[str], None] | None, step: str) -> None:
        if progress_reporter is not None:
            progress_reporter(step)

    def _parse_read_requests(self, raw_requests: Any) -> tuple[List[AgentHarnessReadRequest], List[str]]:
        if not isinstance(raw_requests, list):
            return [], ["read_requests_not_list"]

        parsed_requests: List[AgentHarnessReadRequest] = []
        validation_issues: List[str] = []
        for raw_request in raw_requests:
            try:
                parsed_requests.append(AgentHarnessReadRequest.model_validate(raw_request))
            except ValidationError as exc:
                validation_issues.append(exc.errors()[0]["type"])
        return parsed_requests, validation_issues

    def _build_facts(
        self,
        graph_data: Dict[str, Any],
        change_data: Dict[str, Any],
        verification_data: Dict[str, Any],
        change_risk_summary: Dict[str, Any],
        file_review_summaries: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return {
            "changed_files": list(change_data.get("changed_files", [])),
            "changed_symbols": list(change_data.get("changed_symbols", [])),
            "changed_routes": list(change_data.get("changed_routes", [])),
            "directly_changed_modules": list(change_data.get("directly_changed_modules", [])),
            "affected_tests": list(verification_data.get("affected_tests", [])),
            "module_count": len(graph_data.get("modules", [])),
            "coverage_summary": dict(change_risk_summary.get("coverage", {})),
            "impacted_capabilities": list(
                change_risk_summary.get("existing_feature_impact", {}).get("affected_capabilities", [])
            ),
            "risk_signals": list(change_risk_summary.get("risk_signals", [])),
            "file_review_targets": [
                {
                    "path": item.get("path", ""),
                    "file_role": item.get("file_role", ""),
                    "risk_level": item.get("risk_level", "unknown"),
                    "diff_summary": item.get("diff_summary", ""),
                    "diff_snippets": list(item.get("diff_snippets", []))[:5],
                    "intent_evidence": list(item.get("intent_evidence", []))[:3],
                    "related_entrypoints": list(item.get("related_entrypoints", []))[:5],
                    "related_capabilities": list(item.get("related_capabilities", []))[:5],
                    "related_tests": list(item.get("related_tests", []))[:5],
                }
                for item in file_review_summaries[:20]
            ],
            "top_unverified_paths": list(verification_data.get("unverified_changed_paths", []))[:3],
            "top_changed_entrypoints": list(change_data.get("affected_entrypoints", []))[:3],
        }

    def _result(
        self,
        status: str,
        response: Dict[str, Any] | None,
        rounds_used: int,
        requests_used: int,
        validation_issues: List[str],
    ) -> Dict[str, Any]:
        return {
            "status": status,
            "response": response,
            "metadata": {
                "rounds_used": rounds_used,
                "requests_used": requests_used,
                "max_rounds": self.max_rounds,
                "max_read_requests": self.max_read_requests,
                "validation_issues": validation_issues,
            },
        }
