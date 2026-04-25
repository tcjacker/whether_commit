from __future__ import annotations

from typing import Any, Dict, List

from app.schemas.assessment import AssessmentManifest, ChangedFileDetail, ReviewState
from app.services.agentic_change_assessment.diff_parser import parse_unified_diff_hunks
from app.services.agentic_change_assessment.file_assessment_agent import FileAssessmentAgent
from app.services.agentic_change_assessment.id_utils import file_id_for_path, fingerprint_for_text


class AgenticChangeAssessmentBuilder:
    def __init__(self, file_assessment_agent: FileAssessmentAgent | None = None) -> None:
        self.file_assessment_agent = file_assessment_agent or FileAssessmentAgent()

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
        codex_conversation_evidence = (
            change_data.get("codex_conversation_evidence")
            if isinstance(change_data.get("codex_conversation_evidence"), dict)
            else {}
        )
        if codex_conversation_evidence.get("message_count"):
            agent_sources = sorted(set(agent_sources) | {"codex"})

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
            impact_facts = self._impact_facts_for_path(review_graph_data)
            review_state = {
                "review_status": "unreviewed",
                "diff_fingerprint": diff_fingerprint,
                "reviewer": None,
                "reviewed_at": None,
                "notes": [],
            }
            file_assessment = self.file_assessment_agent.build(
                path=path,
                stats=stats,
                coverage_status=coverage_status,
                related_tests=related_tests,
                related_agent_records=related_records,
                change_data=change_data,
                impact_facts=impact_facts,
            )
            detail = {
                "file": summary,
                "diff_hunks": parse_unified_diff_hunks(diff_text),
                "changed_symbols": list(change_data.get("changed_symbols", [])),
                "related_agent_records": related_records,
                "related_tests": related_tests,
                "impact_facts": impact_facts,
                "file_assessment": file_assessment,
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
            "agentic_summary": self._agentic_summary(
                change_data=change_data,
                agent_records=agent_records,
                changed_files=changed_files,
                affected_tests=affected_tests,
                evidence_by_path=evidence_by_path,
            ),
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

    def _agentic_summary(
        self,
        *,
        change_data: Dict[str, Any],
        agent_records: List[Dict[str, Any]],
        changed_files: List[str],
        affected_tests: List[str],
        evidence_by_path: Dict[str, Any],
    ) -> Dict[str, Any]:
        codex_records = [record for record in agent_records if record.get("source") == "codex"]
        activity = [
            item
            for item in change_data.get("agent_activity_evidence", [])
            if isinstance(item, dict) and item.get("source") == "codex" and item.get("summary")
        ]
        conversation = (
            change_data.get("codex_conversation_evidence")
            if isinstance(change_data.get("codex_conversation_evidence"), dict)
            else {}
        )
        user_messages = self._unique_texts(
            [
                str(text).strip()
                for text in conversation.get("user_messages", [])
                if isinstance(text, str)
            ]
        )
        assistant_messages = self._unique_texts(
            [
                str(text).strip()
                for text in conversation.get("assistant_messages", [])
                if isinstance(text, str)
            ]
        )
        classified = (
            conversation.get("classified_summary")
            if isinstance(conversation.get("classified_summary"), dict)
            else {}
        )
        classified_goals = self._unique_texts(
            [str(text).strip() for text in classified.get("goals", []) if isinstance(text, str)]
        )
        classified_decisions = self._unique_texts(
            [str(text).strip() for text in classified.get("decisions", []) if isinstance(text, str)]
        )
        classified_actions = self._unique_texts(
            [
                str(text).strip()
                for text in classified.get("implementation_actions", [])
                if isinstance(text, str)
            ]
        )
        classified_tests = self._unique_texts(
            [
                str(text).strip()
                for text in classified.get("tests_and_verification", [])
                if isinstance(text, str)
            ]
        )
        evidence_texts = self._unique_texts(
            classified_goals + user_messages + [
                text
                for record in codex_records
                for text in (
                    str(record.get("task_summary") or "").strip(),
                    str(record.get("declared_intent") or "").strip(),
                )
            ]
            + [str(item.get("summary") or "").strip() for item in activity]
        )
        reasoning_texts = self._unique_texts(
            classified_actions + assistant_messages
            + [str(record.get("reasoning_summary") or "").strip() for record in codex_records]
            + [str(record.get("task_summary") or "").strip() for record in codex_records]
        )
        commands = self._unique_texts(
            [
                str(command).strip()
                for record in agent_records
                for command in record.get("commands_run", [])
                if command
            ]
            + [
                str(test.get("command", "")).strip()
                for record in agent_records
                for test in record.get("tests_run", [])
                if isinstance(test, dict) and test.get("command")
            ]
        )
        test_statuses = [
            f"{path}: {self._evidence_status(evidence_by_path.get(path))}"
            for path in affected_tests[:5]
        ]
        has_conversation = bool(conversation.get("message_count"))
        has_codex = bool(has_conversation or codex_records or activity)
        return {
            "generated_by": "codex_logs" if has_codex else "rules",
            "capture_level": "partial" if has_codex else "diff_only",
            "confidence": "medium" if has_codex else "low",
            "time_window": {
                "since_commit": str(change_data.get("base_commit_sha") or "HEAD"),
                "since_commit_time": change_data.get("since_commit_time"),
            },
            "user_design_goal": self._join_summary(
                (classified_goals or user_messages or evidence_texts)[:3],
                fallback="未捕获到结构化 Codex 设计目标；仅能基于 git diff 做变更总览。",
            ),
            "codex_change_summary": self._join_summary(
                (
                    classified_actions
                    + assistant_messages
                    + [str(item.get("summary") or "").strip() for item in activity]
                    + reasoning_texts
                )[:3],
                fallback=self._changed_files_summary(changed_files),
            ),
            "main_objective": self._main_objective(evidence_texts + reasoning_texts, changed_files),
            "key_decisions": self._key_decisions(
                evidence_texts + reasoning_texts,
                explicit_decisions=classified_decisions,
            ),
            "files_or_areas_changed": changed_files[:12],
            "tests_and_verification": classified_tests + commands[:8] + test_statuses,
            "unknowns": self._summary_unknowns(
                has_codex,
                classified_summary_source=str(conversation.get("classified_summary_source") or ""),
            ),
        }

    def _main_objective(self, texts: List[str], changed_files: List[str]) -> str:
        combined = " ".join(texts)
        if "session jsonl" in combined.lower():
            return "接入 Codex session JSONL，按当前 workspace 和上次提交后的时间窗口总结本轮修改目标。"
        if "diff review" in combined or "changed files" in combined or "Agentic Change Assessment" in combined:
            return "围绕 diff review 和 Agentic Change Assessment 建立本轮变更评估闭环。"
        if changed_files:
            return f"审查并解释 {len(changed_files)} 个 changed file 的本轮修改目标、影响和测试状态。"
        return "当前 workspace 无待总结的代码变更。"

    def _key_decisions(
        self,
        texts: List[str],
        explicit_decisions: List[str] | None = None,
    ) -> List[str]:
        combined = " ".join(texts)
        decisions: List[str] = list(explicit_decisions or [])
        if "diff" in combined:
            decisions.append("以 changed files 和 diff review 作为评估主线。")
        if "Codex" in combined or "codex" in combined:
            decisions.append("将 Codex 日志作为解释层证据，事实层仍以 git diff 和测试结果为准。")
        if "session jsonl" in combined.lower():
            decisions.append("解析 Codex session JSONL，提取当前 workspace 的 user/assistant 对话。")
        if "test" in combined.lower() or "测试" in combined:
            decisions.append("把测试覆盖和验证状态纳入本轮评估。")
        return decisions[:5]

    def _summary_unknowns(
        self,
        has_codex: bool,
        *,
        classified_summary_source: str = "",
    ) -> List[str]:
        unknowns = [
            "Codex 聊天记录按当前 workspace、时间窗口和 changed files 做 best-effort 关联，可能不完整。",
        ]
        if classified_summary_source == "codex_llm":
            unknowns.append("本轮目标摘要经过 Codex LLM 二次压缩；仍以 git diff 和测试事实为准。")
        else:
            unknowns.append("本轮目标摘要使用规则分段压缩；长对话可能只保留高相关片段。")
        if not has_codex:
            unknowns.insert(0, "未找到可关联的 Codex 日志。")
        return unknowns

    def _changed_files_summary(self, changed_files: List[str]) -> str:
        if not changed_files:
            return "未发现 changed files。"
        preview = ", ".join(changed_files[:5])
        suffix = " 等文件" if len(changed_files) > 5 else ""
        return f"本轮修改涉及 {preview}{suffix}。"

    def _join_summary(self, values: List[str], *, fallback: str) -> str:
        return " | ".join(values) if values else fallback

    def _unique_texts(self, values: List[str]) -> List[str]:
        result: List[str] = []
        for value in values:
            text = " ".join(value.split())
            if text and text not in result:
                result.append(text[:360])
        return result

    def _test_summary(self, related_tests: List[Dict[str, Any]], coverage_status: str) -> str:
        if not related_tests:
            return "No direct test evidence was found."
        return f"{len(related_tests)} related test evidence item(s), coverage status: {coverage_status}."
