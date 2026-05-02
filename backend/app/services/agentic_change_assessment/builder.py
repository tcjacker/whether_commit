from __future__ import annotations

from typing import Any, Dict, List

from app.schemas.assessment import AssessmentManifest, ChangedFileDetail, ReviewState
from app.services.agentic_change_assessment.diff_parser import parse_unified_diff_hunks
from app.services.agentic_change_assessment.file_assessment_agent import FileAssessmentAgent
from app.services.agentic_change_assessment.id_utils import file_id_for_path, fingerprint_for_text
from app.services.test_management.agent_contract import AgentInstructionContractReader
from app.services.test_management.extractor import TestManagementExtractor, is_test_path


class AgenticChangeAssessmentBuilder:
    def __init__(
        self,
        file_assessment_agent: FileAssessmentAgent | None = None,
        test_management_extractor: TestManagementExtractor | None = None,
    ) -> None:
        self.file_assessment_agent = file_assessment_agent or FileAssessmentAgent()
        self.test_management_extractor = test_management_extractor or TestManagementExtractor()

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
        hunk_queue: List[Dict[str, Any]] = []
        all_mismatches: List[Dict[str, Any]] = []
        weak_test_evidence_count = 0

        for path in changed_files:
            stats = file_diff_stats.get(path, {})
            diff_text = file_diffs.get(path, "")
            diff_hunks = parse_unified_diff_hunks(diff_text)
            diff_fingerprint = fingerprint_for_text(diff_text or path)
            file_id = file_id_for_path(path)
            coverage_status = "missing" if path in missing_tests else ("covered" if affected_tests else "unknown")
            related_records = [
                record for record in agent_records if path in record.get("files_touched", [])
            ] or agent_records
            agent_claims = self._agent_claims_for_path(
                path=path,
                related_agent_records=related_records,
                change_data=change_data,
            )
            related_tests = self._related_tests(
                affected_tests,
                evidence_by_path,
                coverage_status,
                agent_claims,
                codex_conversation_evidence if isinstance(codex_conversation_evidence, dict) else {},
            )
            weakest_grade = self._weakest_evidence_grade(related_tests)
            if weakest_grade in {"claimed", "inferred", "not_run", "unknown"}:
                weak_test_evidence_count += 1
            provenance_refs = self._provenance_refs_for_path(
                path=path,
                diff_hunks=diff_hunks,
                related_agent_records=related_records,
                change_data=change_data,
            )
            mismatches = self._mismatches_for_path(
                path=path,
                agent_claims=agent_claims,
                related_tests=related_tests,
                stats=stats,
            )
            hunk_review_items = self._hunk_review_items(
                path=path,
                file_id=file_id,
                diff_hunks=diff_hunks,
                stats=stats,
                weakest_grade=weakest_grade,
                mismatches=mismatches,
                provenance_refs=provenance_refs,
            )
            highest_priority = max((item["priority"] for item in hunk_review_items), default=None)
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
                "highest_hunk_priority": highest_priority,
                "mismatch_count": len(mismatches),
                "weakest_test_evidence_grade": weakest_grade,
            }
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
                "diff_hunks": diff_hunks,
                "changed_symbols": list(change_data.get("changed_symbols", [])),
                "related_agent_records": related_records,
                "related_tests": related_tests,
                "impact_facts": impact_facts,
                "agent_claims": agent_claims,
                "mismatches": mismatches,
                "provenance_refs": provenance_refs,
                "hunk_review_items": hunk_review_items,
                "file_assessment": file_assessment,
                "review_state": review_state,
            }
            ChangedFileDetail.model_validate(detail)
            file_list.append(summary)
            file_details[file_id] = detail
            hunk_queue.extend(hunk_review_items)
            all_mismatches.extend(mismatches)
            review_items.append({"file_id": file_id, "path": path, **review_state})

        hunk_queue = sorted(hunk_queue, key=lambda item: (-item["priority"], item["path"], item["hunk_id"]))
        file_list = sorted(
            file_list,
            key=lambda item: (-(item.get("highest_hunk_priority") or -1), -item.get("mismatch_count", 0), item["path"]),
        )
        agentic_summary = self._agentic_summary(
            change_data=change_data,
            agent_records=agent_records,
            changed_files=changed_files,
            affected_tests=affected_tests,
            evidence_by_path=evidence_by_path,
        )
        manifest = {
            "assessment_id": f"aca_{workspace_snapshot_id}",
            "workspace_snapshot_id": workspace_snapshot_id,
            "repo_key": repo_key,
            "status": "ready",
            "mode": "working_tree",
            "provenance_capture_level": agentic_summary["capture_level"],
            "mismatch_count": len(all_mismatches),
            "weak_test_evidence_count": weak_test_evidence_count,
            "review_decision": self._review_decision(
                mismatches=all_mismatches,
                weak_test_evidence_count=weak_test_evidence_count,
                missing_tests=len(missing_tests),
                hunk_queue=hunk_queue,
            ),
            "hunk_queue_preview": hunk_queue[:8],
            "agentic_summary": agentic_summary,
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
        test_file_details = {
            file_id: detail for file_id, detail in file_details.items() if self._is_test_path(detail["file"]["path"])
        }
        changed_non_test_file_details = {
            file_id: detail for file_id, detail in file_details.items() if not self._is_test_path(detail["file"]["path"])
        }
        agent_instruction_contract = {}
        workspace_path = change_data.get("workspace_path")
        if isinstance(workspace_path, str) and workspace_path.strip():
            agent_instruction_contract = AgentInstructionContractReader(workspace_path).read()
        test_management = self.test_management_extractor.build(
            assessment_id=manifest["assessment_id"],
            repo_key=repo_key,
            file_details=test_file_details,
            changed_file_details=changed_non_test_file_details,
            review_graph_data=review_graph_data,
            command_evidence=codex_conversation_evidence.get("commands", []),
            agent_instruction_contract=agent_instruction_contract,
        )
        self._apply_test_management_feedback(
            test_management=test_management,
            file_details=file_details,
            file_list=file_list,
        )
        AssessmentManifest.model_validate(manifest)
        return {
            "manifest": manifest,
            "file_details": file_details,
            "review_state": review_state,
            "test_management": test_management,
        }

    def _is_test_path(self, path: str) -> bool:
        return is_test_path(path)

    def _apply_test_management_feedback(
        self,
        *,
        test_management: Dict[str, Any],
        file_details: Dict[str, Dict[str, Any]],
        file_list: List[Dict[str, Any]],
    ) -> None:
        file_summaries_by_path = {item["path"]: item for item in file_list}
        seen_tests_by_path = {
            detail["file"]["path"]: {test.get("test_id") for test in detail.get("related_tests", [])}
            for detail in file_details.values()
        }

        for case_detail in test_management.get("test_case_details", {}).values():
            test_case = case_detail.get("test_case", {})
            test_id = str(test_case.get("test_case_id") or "")
            test_path = str(test_case.get("path") or "")
            if not test_id or not test_path:
                continue

            for covered_change in case_detail.get("covered_changes", []):
                changed_path = str(covered_change.get("path") or "")
                changed_detail = next(
                    (
                        detail
                        for detail in file_details.values()
                        if detail["file"]["path"] == changed_path and not self._is_test_path(changed_path)
                    ),
                    None,
                )
                if changed_detail is None:
                    continue

                evidence_grade = str(covered_change.get("evidence_grade") or "unknown")
                if test_id not in seen_tests_by_path.setdefault(changed_path, set()):
                    changed_detail.setdefault("related_tests", []).append(
                        {
                            "test_id": test_id,
                            "path": test_path,
                            "relationship": self._review_relationship_for_evidence(evidence_grade),
                            "confidence": self._confidence_for_evidence(evidence_grade),
                            "last_status": test_case.get("last_status", "unknown"),
                            "evidence": "graph_inference",
                            "evidence_grade": evidence_grade,
                            "basis": [
                                "test_management",
                                f"test_case:{test_case.get('name', '')}",
                                f"relationship:{covered_change.get('relationship', 'unknown')}",
                                *covered_change.get("basis", []),
                            ],
                        }
                    )
                    seen_tests_by_path[changed_path].add(test_id)

                weakest_grade = self._weakest_evidence_grade(changed_detail.get("related_tests", []))
                changed_detail["file"]["weakest_test_evidence_grade"] = weakest_grade
                if changed_path in file_summaries_by_path:
                    file_summaries_by_path[changed_path]["weakest_test_evidence_grade"] = weakest_grade
                self._annotate_hunk_with_test_feedback(changed_detail, covered_change, test_case)
                ChangedFileDetail.model_validate(changed_detail)

    def _review_relationship_for_evidence(self, evidence_grade: str) -> str:
        if evidence_grade == "direct":
            return "primary"
        if evidence_grade in {"indirect", "inferred"}:
            return "secondary"
        return "inferred"

    def _confidence_for_evidence(self, evidence_grade: str) -> str:
        if evidence_grade == "direct":
            return "high"
        if evidence_grade in {"indirect", "inferred"}:
            return "medium"
        return "low"

    def _annotate_hunk_with_test_feedback(
        self, detail: Dict[str, Any], covered_change: Dict[str, Any], test_case: Dict[str, Any]
    ) -> None:
        hunk_id = str(covered_change.get("hunk_id") or "")
        evidence_grade = str(covered_change.get("evidence_grade") or "unknown")
        if not hunk_id:
            return
        for item in detail.get("hunk_review_items", []):
            if item.get("hunk_id") != hunk_id:
                continue
            reason = f"Test workbench links {test_case.get('name', 'test case')} with {evidence_grade} evidence."
            fact = f"test_workbench:{evidence_grade}"
            if reason not in item.setdefault("reasons", []):
                item["reasons"].append(reason)
            if fact not in item.setdefault("fact_basis", []):
                item["fact_basis"].append(fact)
            return

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
        agent_claims: List[Dict[str, Any]] | None = None,
        codex_conversation_evidence: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        relationship = "inferred" if coverage_status == "unknown" else "primary"
        confidence = "low" if relationship == "inferred" else "medium"
        tests = []
        for test_path in affected_tests:
            command_evidence = self._matching_test_command(test_path, codex_conversation_evidence or {})
            status = self._evidence_status(evidence_by_path.get(test_path))
            basis = ["verification" if evidence_by_path.get(test_path) else "graph_inference"]
            if status == "unknown" and command_evidence:
                status = "passed"
                basis.append("command_evidence")
            tests.append(
                {
                    "test_id": test_path.replace("/", "_").replace(".py", ""),
                    "path": test_path,
                    "relationship": relationship,
                    "confidence": "high" if command_evidence else confidence,
                    "last_status": status,
                    "evidence": "marker" if command_evidence else "graph_inference",
                    "evidence_grade": self._test_evidence_grade(
                        relationship=relationship,
                        status=status,
                        evidence="marker" if command_evidence else "graph_inference",
                    ),
                    "basis": basis,
                }
            )
        if not tests and any(claim.get("type") == "test" for claim in agent_claims or []):
            tests.append(
                {
                    "test_id": "agent_claimed_tests",
                    "path": "agent_claimed_tests",
                    "relationship": "inferred",
                    "confidence": "low",
                    "last_status": "unknown",
                    "evidence": "agent_claim",
                    "evidence_grade": "claimed",
                    "basis": ["agent_claim", "no_execution_record"],
                }
            )
        return tests

    def _matching_test_command(self, test_path: str, codex_conversation_evidence: Dict[str, Any]) -> str:
        for item in codex_conversation_evidence.get("commands", []):
            if not isinstance(item, dict):
                continue
            command = str(item.get("command") or "")
            if not self._looks_like_test_command(command):
                continue
            if self._command_matches_test_path(command, test_path):
                return command
        return ""

    def _looks_like_test_command(self, command: str) -> bool:
        lowered = command.lower()
        return any(token in lowered for token in ("pytest", "npm test", "vitest", "jest", "cargo test", "go test"))

    def _command_matches_test_path(self, command: str, test_path: str) -> bool:
        lowered_command = command.lower()
        lowered_path = test_path.lower()
        basename = lowered_path.rsplit("/", 1)[-1]
        parent = lowered_path.rsplit("/", 1)[0]
        path_parts = [part for part in parent.split("/") if part not in {"src", "__tests__", "tests", "test"}]
        return (
            lowered_path in lowered_command
            or basename in lowered_command
            or any(len(part) >= 3 and part in lowered_command for part in path_parts[-2:])
        )

    def _evidence_status(self, evidence: Any) -> str:
        if isinstance(evidence, dict):
            status = evidence.get("status", "unknown")
            return status if status in {"passed", "failed", "not_run", "unknown"} else "unknown"
        return "unknown"

    def _impact_facts_for_path(self, review_graph_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        nodes = review_graph_data.get("nodes", [])
        return [{"kind": "review_graph_node", "value": node.get("id")} for node in nodes[:5] if node.get("id")]

    def _test_evidence_grade(self, *, relationship: str, status: str, evidence: str) -> str:
        if evidence == "agent_claim":
            return "claimed"
        if status in {"passed", "failed"} and relationship == "primary":
            return "direct"
        if status in {"passed", "failed"}:
            return "indirect"
        if status == "not_run":
            return "not_run"
        if relationship == "inferred":
            return "inferred"
        return "unknown"

    def _weakest_evidence_grade(self, related_tests: List[Dict[str, Any]]) -> str:
        if not related_tests:
            return "unknown"
        order = {"unknown": 0, "not_run": 1, "claimed": 2, "inferred": 3, "indirect": 4, "direct": 5}
        return min((test.get("evidence_grade", "unknown") for test in related_tests), key=lambda grade: order.get(grade, 0))

    def _agent_claims_for_path(
        self,
        *,
        path: str,
        related_agent_records: List[Dict[str, Any]],
        change_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        texts: List[tuple[str, str, str, str, str]] = []
        conversation = change_data.get("codex_conversation_evidence")
        session_id = ""
        if isinstance(conversation, dict):
            session_ids = conversation.get("session_ids", [])
            session_id = str(session_ids[0]) if session_ids else ""
            message_ref_by_text = self._message_refs_by_text(conversation)
            classified = conversation.get("classified_summary") if isinstance(conversation.get("classified_summary"), dict) else {}
            classified_texts = [
                text
                for text in classified.get("goals", []) + classified.get("implementation_actions", []) + classified.get("tests_and_verification", [])
                if isinstance(text, str)
            ]
            conversation_texts = [
                text
                for text in conversation.get("user_messages", []) + conversation.get("assistant_messages", [])
                if isinstance(text, str)
            ]
            all_conversation_texts = classified_texts + conversation_texts
            any_path_scoped_text = any(
                self._text_mentions_path(text, changed_path)
                for text in all_conversation_texts
                for changed_path in change_data.get("changed_files", [])
            )
            current_path_context = any(self._text_mentions_path(text, path) for text in all_conversation_texts)
            for text in classified_texts:
                if isinstance(text, str):
                    if (
                        self._text_mentions_path(text, path)
                        or not any_path_scoped_text
                        or (current_path_context and self._claim_type(text) == "test")
                    ):
                        ref = self._best_message_ref_for_text(text, message_ref_by_text)
                        texts.append(("codex", text, session_id, ref.get("message_ref", ""), ""))
            for text in conversation_texts:
                if isinstance(text, str):
                    if self._text_mentions_path(text, path) or not any_path_scoped_text:
                        ref = self._best_message_ref_for_text(text, message_ref_by_text)
                        texts.append(("codex", text, session_id, ref.get("message_ref", ""), ""))

        for record in related_agent_records:
            source = str(record.get("source") or "agent")
            record_session = self._session_id_from_record(record) or session_id
            for field in ("declared_intent", "reasoning_summary", "task_summary"):
                value = str(record.get(field, "")).strip()
                if value:
                    texts.append((source, value, record_session, "", ""))

        claims: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for source, text, claim_session_id, message_ref, tool_call_ref in texts:
            claim_type = self._claim_type(text)
            if claim_type == "unknown":
                continue
            key = f"{claim_type}:{text}"
            if key in seen:
                continue
            seen.add(key)
            claims.append(
                {
                    "claim_id": f"claim_{fingerprint_for_text(key)[:12]}",
                    "type": claim_type,
                    "text": text[:360],
                    "source": source,
                    "session_id": claim_session_id,
                    "message_ref": message_ref,
                    "tool_call_ref": tool_call_ref,
                    "related_files": [path],
                    "confidence": "medium" if source == "codex" else "low",
                }
            )
        return claims[:8]

    def _claim_type(self, text: str) -> str:
        lowered = text.lower()
        if any(token in lowered for token in ("test", "pytest", "coverage", "测试", "验证")):
            return "test"
        if any(token in lowered for token in ("refactor", "重构")):
            return "refactor"
        if any(token in lowered for token in ("bug", "fix", "修复")):
            return "bugfix"
        if any(token in lowered for token in ("feature", "add", "新增", "实现")):
            return "feature"
        if any(token in lowered for token in ("config", "配置")):
            return "config"
        if any(token in lowered for token in ("docs", "readme", "文档")):
            return "docs"
        if any(token in lowered for token in ("cleanup", "清理")):
            return "cleanup"
        return "unknown"

    def _session_id_from_record(self, record: Dict[str, Any]) -> str:
        raw = str(record.get("raw_log_ref") or "")
        if "session/" in raw:
            return raw.rsplit("/", 1)[-1]
        return ""

    def _provenance_refs_for_path(
        self,
        *,
        path: str,
        diff_hunks: List[Dict[str, Any]],
        related_agent_records: List[Dict[str, Any]],
        change_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        refs: List[Dict[str, Any]] = []
        hunk_id = diff_hunks[0]["hunk_id"] if diff_hunks else ""
        conversation = change_data.get("codex_conversation_evidence")
        session_id = ""
        if isinstance(conversation, dict):
            session_ids = conversation.get("session_ids", [])
            session_id = str(session_ids[0]) if session_ids else ""
            refs.extend(self._structured_codex_provenance_refs(path=path, hunk_id=hunk_id, conversation=conversation))
        for record in related_agent_records:
            source = str(record.get("source") or "agent")
            record_session = self._session_id_from_record(record) or session_id
            if source == "git_diff" and not record_session:
                continue
            commands = record.get("commands_run", [])
            refs.append(
                {
                    "source": source,
                    "session_id": record_session,
                    "message_ref": "",
                    "tool_call_ref": "",
                    "command": str(commands[0]) if commands else "",
                    "file_path": path,
                    "hunk_id": hunk_id,
                    "confidence": "medium" if record_session or path in record.get("files_touched", []) else "low",
                }
            )
        if not refs and session_id:
            refs.append(
                {
                    "source": "codex",
                    "session_id": session_id,
                    "message_ref": "",
                    "tool_call_ref": "",
                    "command": "",
                    "file_path": path,
                    "hunk_id": hunk_id,
                    "confidence": "medium",
                }
            )
        return self._dedupe_provenance_refs(refs)[:8]

    def _message_refs_by_text(self, conversation: Dict[str, Any]) -> List[Dict[str, str]]:
        refs: List[Dict[str, str]] = []
        for item in conversation.get("message_refs", []):
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            message_ref = str(item.get("message_ref") or "")
            if not text or not message_ref:
                continue
            refs.append(
                {
                    "text": text,
                    "message_ref": message_ref,
                    "session_id": str(item.get("session_id") or ""),
                }
            )
        return refs

    def _best_message_ref_for_text(self, text: str, refs: List[Dict[str, str]]) -> Dict[str, str]:
        if not refs:
            return {}
        lowered = text.lower()
        for ref in refs:
            ref_text = ref["text"].lower()
            if lowered in ref_text or ref_text in lowered:
                return ref
        for ref in refs:
            if self._text_overlap_score(lowered, ref["text"].lower()) >= 2:
                return ref
        return {}

    def _text_overlap_score(self, left: str, right: str) -> int:
        tokens = {
            token
            for token in left.replace("。", " ").replace("，", " ").replace(".", " ").split()
            if len(token) >= 4
        }
        return sum(1 for token in tokens if token in right)

    def _structured_codex_provenance_refs(
        self,
        *,
        path: str,
        hunk_id: str,
        conversation: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        refs: List[Dict[str, Any]] = []
        for ref in conversation.get("file_refs", []):
            if not isinstance(ref, dict) or ref.get("file_path") != path:
                continue
            refs.append(
                {
                    "source": str(ref.get("source") or "codex"),
                    "session_id": str(ref.get("session_id") or ""),
                    "message_ref": str(ref.get("message_ref") or ""),
                    "tool_call_ref": str(ref.get("tool_call_ref") or ""),
                    "command": "",
                    "file_path": path,
                    "hunk_id": hunk_id,
                    "confidence": str(ref.get("confidence") or "medium"),
                }
            )
        for command in conversation.get("commands", []):
            if not isinstance(command, dict):
                continue
            related_files = command.get("related_files") if isinstance(command.get("related_files"), list) else []
            command_text = str(command.get("command") or "")
            if related_files and path not in related_files:
                continue
            if not related_files and not self._text_mentions_path(command_text, path):
                continue
            refs.append(
                {
                    "source": "codex_command",
                    "session_id": str(command.get("session_id") or ""),
                    "message_ref": "",
                    "tool_call_ref": str(command.get("tool_call_ref") or ""),
                    "command": command_text,
                    "file_path": path,
                    "hunk_id": hunk_id,
                    "confidence": "medium" if related_files else "low",
                }
            )
        return refs

    def _dedupe_provenance_refs(self, refs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        confidence_rank = {"high": 0, "medium": 1, "low": 2}
        deduped: Dict[tuple[str, str, str, str, str], Dict[str, Any]] = {}
        for ref in refs:
            key = (
                str(ref.get("source") or ""),
                str(ref.get("session_id") or ""),
                str(ref.get("message_ref") or ""),
                str(ref.get("tool_call_ref") or ""),
                str(ref.get("command") or ""),
            )
            existing = deduped.get(key)
            if existing is None or confidence_rank.get(str(ref.get("confidence") or "low"), 2) < confidence_rank.get(str(existing.get("confidence") or "low"), 2):
                deduped[key] = ref
        return sorted(
            deduped.values(),
            key=lambda ref: (
                confidence_rank.get(str(ref.get("confidence") or "low"), 2),
                0 if ref.get("tool_call_ref") else 1,
                str(ref.get("source") or ""),
            ),
        )

    def _mismatches_for_path(
        self,
        *,
        path: str,
        agent_claims: List[Dict[str, Any]],
        related_tests: List[Dict[str, Any]],
        stats: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        mismatches: List[Dict[str, Any]] = []
        emitted_kinds: set[str] = set()
        has_executed_test = any(test.get("last_status") in {"passed", "failed"} for test in related_tests)
        for claim in agent_claims:
            if claim.get("type") == "test" and not has_executed_test and "claimed_tested_but_no_executed_test_evidence" not in emitted_kinds:
                emitted_kinds.add("claimed_tested_but_no_executed_test_evidence")
                mismatches.append(
                    {
                        "mismatch_id": f"mm_{fingerprint_for_text(claim['claim_id'] + ':no_exec')[:12]}",
                        "kind": "claimed_tested_but_no_executed_test_evidence",
                        "claim_id": claim["claim_id"],
                        "severity": "high",
                        "explanation": "Agent claimed test coverage or test work, but no executed test evidence was found.",
                        "fact_refs": ["agent_claim", "no_execution_record"],
                        "provenance_refs": [],
                    }
                )
            if claim.get("type") == "refactor" and self._is_public_surface_path(path) and "claimed_refactor_but_public_surface_changed" not in emitted_kinds:
                emitted_kinds.add("claimed_refactor_but_public_surface_changed")
                mismatches.append(
                    {
                        "mismatch_id": f"mm_{fingerprint_for_text(claim['claim_id'] + ':surface')[:12]}",
                        "kind": "claimed_refactor_but_public_surface_changed",
                        "claim_id": claim["claim_id"],
                        "severity": "medium",
                        "explanation": "Agent claimed refactor work, but the changed file looks like a public surface.",
                        "fact_refs": ["public_surface_path"],
                        "provenance_refs": [],
                    }
                )
            if (
                claim.get("type") == "bugfix"
                and int(stats.get("added_lines", 0) or 0) + int(stats.get("deleted_lines", 0) or 0) > 60
                and "claimed_small_fix_but_many_files_changed" not in emitted_kinds
            ):
                emitted_kinds.add("claimed_small_fix_but_many_files_changed")
                mismatches.append(
                    {
                        "mismatch_id": f"mm_{fingerprint_for_text(claim['claim_id'] + ':scope')[:12]}",
                        "kind": "claimed_small_fix_but_many_files_changed",
                        "claim_id": claim["claim_id"],
                        "severity": "medium",
                        "explanation": "Agent described a fix, but the changed file has a large diff.",
                        "fact_refs": ["large_diff"],
                        "provenance_refs": [],
                    }
                )
            if (
                self._claim_implies_ui_only(str(claim.get("text") or ""))
                and self._is_backend_runtime_path(path)
                and "claimed_ui_only_but_backend_changed" not in emitted_kinds
            ):
                emitted_kinds.add("claimed_ui_only_but_backend_changed")
                mismatches.append(
                    {
                        "mismatch_id": f"mm_{fingerprint_for_text(claim['claim_id'] + ':ui_backend')[:12]}",
                        "kind": "claimed_ui_only_but_backend_changed",
                        "claim_id": claim["claim_id"],
                        "severity": "medium",
                        "explanation": "Agent described UI-only work, but backend or runtime code changed.",
                        "fact_refs": ["backend_runtime_path"],
                        "provenance_refs": [],
                    }
                )
            if (
                claim.get("type") == "config"
                and self._is_runtime_source_path(path)
                and "claimed_config_only_but_runtime_code_changed" not in emitted_kinds
            ):
                emitted_kinds.add("claimed_config_only_but_runtime_code_changed")
                mismatches.append(
                    {
                        "mismatch_id": f"mm_{fingerprint_for_text(claim['claim_id'] + ':config_runtime')[:12]}",
                        "kind": "claimed_config_only_but_runtime_code_changed",
                        "claim_id": claim["claim_id"],
                        "severity": "medium",
                        "explanation": "Agent described config-only work, but runtime source code changed.",
                        "fact_refs": ["runtime_source_path"],
                        "provenance_refs": [],
                    }
                )
        return mismatches[:5]

    def _hunk_review_items(
        self,
        *,
        path: str,
        file_id: str,
        diff_hunks: List[Dict[str, Any]],
        stats: Dict[str, Any],
        weakest_grade: str,
        mismatches: List[Dict[str, Any]],
        provenance_refs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for hunk in diff_hunks or [{"hunk_id": "hunk_001", "lines": []}]:
            score = 0
            reasons: List[str] = []
            fact_basis: List[str] = []
            hunk_refs = [{**ref, "hunk_id": hunk["hunk_id"]} for ref in provenance_refs[:2]]
            if self._is_public_surface_path(path):
                score += 30
                reasons.append("Public API/type/config surface changed.")
                fact_basis.append("public_surface_path")
            if mismatches:
                score += 30
                reasons.append("Agent claim conflicts with fact-layer evidence.")
                fact_basis.append("claim_fact_mismatch")
            if weakest_grade in {"claimed", "inferred", "not_run", "unknown"}:
                score += 20 if weakest_grade in {"claimed", "not_run"} else 15
                reasons.append(f"Test evidence is {weakest_grade}.")
                fact_basis.append(f"test_evidence:{weakest_grade}")
            if not hunk_refs and mismatches:
                score += 10
                reasons.append("No agent provenance was linked.")
                fact_basis.append("missing_provenance")
            if int(stats.get("added_lines", 0) or 0) + int(stats.get("deleted_lines", 0) or 0) >= 50:
                score += 5
                reasons.append("Large file-level diff.")
                fact_basis.append("large_diff")
            if self._hunk_deletes_guard_or_fallback(hunk):
                score += 20
                reasons.append("Fallback, error handling, permission, or validation branch was removed.")
                fact_basis.append("guard_or_fallback_deleted")
            score = min(score, 100)
            items.append(
                {
                    "hunk_id": hunk["hunk_id"],
                    "file_id": file_id,
                    "path": path,
                    "priority": score,
                    "risk_level": "high" if score >= 70 else ("medium" if score >= 35 else ("low" if score > 0 else "unknown")),
                    "reasons": reasons or ["Low-priority changed hunk."],
                    "fact_basis": fact_basis or ["diff_hunk"],
                    "provenance_refs": hunk_refs,
                    "mismatch_ids": [mismatch["mismatch_id"] for mismatch in mismatches],
                }
            )
        return items

    def _is_public_surface_path(self, path: str) -> bool:
        lowered = path.lower()
        return any(token in lowered for token in ("api", "schema", "types", "route", "endpoint", "config"))

    def _text_mentions_path(self, text: str, path: str) -> bool:
        lowered_text = text.lower()
        lowered_path = path.lower()
        basename = lowered_path.rsplit("/", 1)[-1]
        stem = basename.rsplit(".", 1)[0]
        return lowered_path in lowered_text or basename in lowered_text or (len(stem) >= 4 and stem in lowered_text)

    def _claim_implies_ui_only(self, text: str) -> bool:
        lowered = text.lower()
        return any(
            token in lowered
            for token in (
                "ui only",
                "frontend only",
                "front-end only",
                "only frontend",
                "只改前端",
                "仅前端",
                "前端页面",
                "页面改造",
            )
        )

    def _is_backend_runtime_path(self, path: str) -> bool:
        lowered = path.lower()
        return lowered.startswith(("backend/", "app/")) or "/backend/" in lowered

    def _is_runtime_source_path(self, path: str) -> bool:
        lowered = path.lower()
        source_suffixes = (".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".kt", ".rb")
        if lowered.endswith((".md", ".json", ".yaml", ".yml", ".toml", ".ini", ".lock")):
            return False
        return lowered.endswith(source_suffixes) and any(
            segment in lowered for segment in ("backend/", "frontend/src/", "src/", "app/")
        )

    def _hunk_deletes_guard_or_fallback(self, hunk: Dict[str, Any]) -> bool:
        guard_tokens = (
            "catch",
            "except",
            "fallback",
            "default",
            "permission",
            "authorize",
            "validate",
            "validation",
            "guard",
            "if ",
        )
        for line in hunk.get("lines", []):
            if line.get("type") != "remove":
                continue
            content = str(line.get("content") or "").lower()
            if any(token in content for token in guard_tokens):
                return True
        return False

    def _review_decision(
        self,
        *,
        mismatches: List[Dict[str, Any]],
        weak_test_evidence_count: int,
        missing_tests: int,
        hunk_queue: List[Dict[str, Any]],
    ) -> str:
        if any(mismatch.get("severity") == "high" for mismatch in mismatches):
            return "needs_tests"
        if missing_tests or weak_test_evidence_count:
            return "needs_tests"
        if any(item.get("risk_level") == "high" for item in hunk_queue):
            return "needs_recheck"
        if hunk_queue:
            return "safe_to_commit"
        return "unknown"

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
