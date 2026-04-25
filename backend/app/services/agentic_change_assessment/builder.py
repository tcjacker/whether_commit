from __future__ import annotations

from typing import Any, Dict, List

from app.schemas.assessment import AssessmentManifest, ChangedFileDetail, ReviewState
from app.services.agentic_change_assessment.diff_parser import parse_unified_diff_hunks
from app.services.agentic_change_assessment.id_utils import file_id_for_path, fingerprint_for_text


class AgenticChangeAssessmentBuilder:
    def build(
        self,
        *,
        repo_key: str,
        workspace_snapshot_id: str,
        change_data: Dict[str, Any],
        verification_data: Dict[str, Any],
        review_graph_data: Dict[str, Any],
        agent_records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        changed_files = list(dict.fromkeys(change_data.get("changed_files", [])))
        file_diff_stats = change_data.get("file_diff_stats", {})
        file_diffs = change_data.get("file_diffs", {})
        affected_tests = list(verification_data.get("affected_tests", []))
        missing_tests = set(verification_data.get("missing_tests_for_changed_paths", []))
        evidence_by_path = verification_data.get("evidence_by_path", {})
        agent_sources = sorted({record.get("source", "unknown") for record in agent_records})

        file_list: List[Dict[str, Any]] = []
        file_details: Dict[str, Dict[str, Any]] = {}
        review_items: List[Dict[str, Any]] = []

        for path in changed_files:
            stats = file_diff_stats.get(path, {})
            diff_text = file_diffs.get(path, "")
            diff_fingerprint = fingerprint_for_text(diff_text or path)
            file_id = file_id_for_path(path)
            coverage_status = "missing" if path in missing_tests else ("covered" if affected_tests else "unknown")
            summary = {
                "file_id": file_id,
                "path": path,
                "old_path": None,
                "status": self._status_from_change_type(stats.get("change_type", "modified file")),
                "additions": int(stats.get("added_lines", 0)),
                "deletions": int(stats.get("deleted_lines", 0)),
                "risk_level": "medium" if path in missing_tests else "low",
                "coverage_status": coverage_status,
                "review_status": "unreviewed",
                "agent_sources": agent_sources or ["git_diff"],
                "diff_fingerprint": diff_fingerprint,
            }
            related_tests = self._related_tests(affected_tests, evidence_by_path, coverage_status)
            related_records = [
                record for record in agent_records if path in record.get("files_touched", [])
            ] or agent_records
            review_state = {
                "review_status": "unreviewed",
                "diff_fingerprint": diff_fingerprint,
                "reviewer": None,
                "reviewed_at": None,
                "notes": [],
            }
            detail = {
                "file": summary,
                "diff_hunks": parse_unified_diff_hunks(diff_text),
                "changed_symbols": list(change_data.get("changed_symbols", [])),
                "related_agent_records": related_records,
                "related_tests": related_tests,
                "impact_facts": self._impact_facts_for_path(review_graph_data),
                "file_assessment": {
                    "why_changed": "No structured agent reason is available.",
                    "impact_summary": "Review the diff and related capability evidence.",
                    "test_summary": self._test_summary(related_tests, coverage_status),
                    "recommended_action": (
                        "Review this file manually."
                        if coverage_status == "unknown"
                        else "Review the diff and verify related tests."
                    ),
                },
                "review_state": review_state,
            }
            ChangedFileDetail.model_validate(detail)
            file_list.append(summary)
            file_details[file_id] = detail
            review_items.append({"file_id": file_id, "path": path, **review_state})

        manifest = {
            "assessment_id": f"aca_{workspace_snapshot_id}",
            "workspace_snapshot_id": workspace_snapshot_id,
            "repo_key": repo_key,
            "status": "ready",
            "summary": {
                "headline": self._headline(len(file_list)),
                "overall_risk_level": "medium" if missing_tests else ("low" if file_list else "unknown"),
                "coverage_status": self._overall_coverage(file_list),
                "changed_file_count": len(file_list),
                "unreviewed_file_count": len(file_list),
                "affected_capability_count": 0,
                "missing_test_count": len(missing_tests),
                "agent_sources": agent_sources or ["git_diff"],
                "recommended_review_order": [item["path"] for item in file_list],
            },
            "file_list": file_list,
            "risk_signals_summary": [],
            "agent_sources": agent_sources or ["git_diff"],
            "review_progress": {
                "total": len(file_list),
                "reviewed": 0,
                "needs_follow_up": 0,
                "needs_recheck": 0,
                "unreviewed": len(file_list),
            },
        }
        AssessmentManifest.model_validate(manifest)
        review_state = ReviewState.model_validate({"scope": "assessment", "file_reviews": review_items}).model_dump()
        return {
            "manifest": manifest,
            "file_details": file_details,
            "review_state": review_state,
            "overview_mirror": {"agentic_change_assessment": manifest},
        }

    def _status_from_change_type(self, change_type: str) -> str:
        if "new" in change_type:
            return "added"
        if "delete" in change_type:
            return "deleted"
        if "rename" in change_type:
            return "renamed"
        return "modified"

    def _related_tests(
        self,
        affected_tests: List[str],
        evidence_by_path: Dict[str, Any],
        coverage_status: str,
    ) -> List[Dict[str, Any]]:
        relationship = "inferred" if coverage_status == "unknown" else "primary"
        confidence = "low" if relationship == "inferred" else "medium"
        return [
            {
                "test_id": test_path.replace("/", "_").replace(".py", ""),
                "path": test_path,
                "relationship": relationship,
                "confidence": confidence,
                "last_status": self._evidence_status(evidence_by_path.get(test_path)),
                "evidence": "graph_inference",
            }
            for test_path in affected_tests
        ]

    def _evidence_status(self, evidence: Any) -> str:
        if isinstance(evidence, dict):
            status = evidence.get("status", "unknown")
            return status if status in {"passed", "failed", "not_run", "unknown"} else "unknown"
        return "unknown"

    def _impact_facts_for_path(self, review_graph_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        nodes = review_graph_data.get("nodes", [])
        return [{"kind": "review_graph_node", "value": node.get("id")} for node in nodes[:5] if node.get("id")]

    def _headline(self, changed_file_count: int) -> str:
        if changed_file_count == 0:
            return "当前 workspace 无待审查变更。"
        return f"本次变更包含 {changed_file_count} 个待审查文件。"

    def _overall_coverage(self, file_list: List[Dict[str, Any]]) -> str:
        statuses = {item["coverage_status"] for item in file_list}
        if "missing" in statuses:
            return "missing"
        if "covered" in statuses:
            return "partial" if "unknown" in statuses else "covered"
        return "unknown"

    def _test_summary(self, related_tests: List[Dict[str, Any]], coverage_status: str) -> str:
        if not related_tests:
            return "No direct test evidence was found."
        return f"{len(related_tests)} related test evidence item(s), coverage status: {coverage_status}."
