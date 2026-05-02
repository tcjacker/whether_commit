from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional

from app.schemas.assessment import TestCaseDetail, TestManagementSummary


GRADE_ORDER = {"direct": 5, "indirect": 4, "inferred": 3, "claimed": 2, "not_run": 1, "unknown": 0}
RISK_ORDER = {"high": 3, "medium": 2, "low": 1, "unknown": 0}
TEST_EXTENSIONS = (".py", ".js", ".jsx", ".ts", ".tsx")


def is_test_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    basename = normalized.rsplit("/", 1)[-1]
    return normalized.endswith(TEST_EXTENSIONS) and (
        normalized.startswith("tests/")
        or "/tests/" in normalized
        or normalized.startswith("__tests__/")
        or "/__tests__/" in normalized
        or ".test." in basename
        or ".spec." in basename
        or basename.endswith("_test.py")
        or (basename.startswith("test_") and basename.endswith(".py"))
    )


class TestManagementExtractor:
    def build(
        self,
        *,
        assessment_id: str,
        repo_key: str,
        file_details: Dict[str, Dict[str, Any]],
        changed_file_details: Dict[str, Dict[str, Any]],
        review_graph_data: Dict[str, Any],
        command_evidence: Optional[List[Dict[str, Any]]] = None,
        agent_instruction_contract: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        files = []
        test_case_details: Dict[str, Dict[str, Any]] = {}
        unknowns: List[str] = []
        contract_unknowns = self._contract_unknowns(agent_instruction_contract or {})
        unknowns.extend(contract_unknowns)

        for file_id, detail in sorted(file_details.items(), key=lambda item: item[1]["file"]["path"]):
            path = detail["file"]["path"]
            if not self._is_test_path(path):
                continue

            cases = self._extract_cases(file_id, detail, unknowns)
            summaries = []
            for case in cases:
                covered_changes = self._covered_changes(case, changed_file_details, review_graph_data)
                case["covered_changes_preview"] = self._covered_preview(covered_changes, changed_file_details)
                case["highest_risk_covered_hunk_id"] = self._highest_risk_hunk(covered_changes, changed_file_details)
                strongest = self._strongest_grade(covered_changes)
                weakest = self._weakest_grade(covered_changes)
                if strongest:
                    case["evidence_grade"] = strongest
                if weakest:
                    case["weakest_evidence_grade"] = weakest

                detail_payload = {
                    "test_case": self._public_case(case),
                    "diff_hunks": case["_diff_hunks"],
                    "full_body": case["_full_body"],
                    "assertions": case["_assertions"],
                    "covered_scenarios": case["_covered_scenarios"],
                    "test_results": self._historical_test_results(case, command_evidence or []),
                    "covered_changes": covered_changes,
                    "recommended_commands": self._recommended_commands(case),
                    "related_agent_claims": detail.get("agent_claims", []),
                    "unknowns": [*case["_unknowns"], *contract_unknowns],
                }
                validated = TestCaseDetail.model_validate(detail_payload).model_dump()
                test_case_details[case["test_case_id"]] = validated
                summaries.append(validated["test_case"])

            file_payload = {
                "file_id": file_id,
                "path": path,
                "status": detail["file"].get("status", "modified"),
                "additions": detail["file"].get("additions", 0),
                "deletions": detail["file"].get("deletions", 0),
                "test_case_count": len(summaries),
                "strongest_evidence_grade": self._strongest_grade(summaries) or "unknown",
                "weakest_evidence_grade": self._weakest_grade(summaries) or "unknown",
                "latest_command_status": "not_run" if summaries else "unknown",
                "test_cases": summaries,
            }
            files.append(file_payload)

        summary_payload = {
            "assessment_id": assessment_id,
            "repo_key": repo_key,
            "changed_test_file_count": len(files),
            "test_case_count": sum(file["test_case_count"] for file in files),
            "evidence_grade_counts": dict(
                Counter(case["evidence_grade"] for file in files for case in file["test_cases"])
            ),
            "command_status_counts": dict(Counter(file["latest_command_status"] for file in files)),
            "files": files,
            "unknowns": unknowns,
        }
        summary = TestManagementSummary.model_validate(summary_payload).model_dump()
        return {"summary": summary, "test_case_details": test_case_details}

    def _contract_unknowns(self, contract: Dict[str, Any]) -> List[str]:
        return [f"Agent instruction gap: {gap}" for gap in contract.get("gaps", []) if str(gap).strip()]

    def _extract_cases(
        self, file_id: str, detail: Dict[str, Any], summary_unknowns: List[str]
    ) -> List[Dict[str, Any]]:
        path = detail["file"]["path"]
        cases: List[Dict[str, Any]] = []
        for hunk in detail.get("diff_hunks", []):
            lines = hunk.get("lines", [])
            hunk_cases = self._python_cases(file_id, path, hunk, lines)
            if not hunk_cases and path.endswith((".tsx", ".ts", ".jsx", ".js")):
                hunk_cases = self._javascript_cases(file_id, path, hunk, lines, summary_unknowns)
            if not hunk_cases and any(line.get("type") in {"add", "remove"} for line in lines):
                hunk_cases = [self._fallback_case(file_id, path, hunk, lines)]
            cases.extend(hunk_cases)
        for ordinal, case in enumerate(cases, start=1):
            case["test_case_id"] = self._test_case_id(
                path,
                case["name"],
                case["_diff_hunks"][0].get("hunk_id", ""),
                ordinal,
            )
        return cases

    def _python_cases(
        self, file_id: str, path: str, hunk: Dict[str, Any], lines: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        cases: List[Dict[str, Any]] = []
        current: List[Dict[str, str]] = []
        current_name = ""
        current_status = "unknown"
        pattern = re.compile(r"^\s*def\s+(test_[A-Za-z0-9_]+)\s*\(")

        for line in lines:
            content = line.get("content", "")
            match = pattern.search(content)
            if match:
                if current_name:
                    cases.append(self._python_case(file_id, path, current_name, current_status, hunk, current))
                current = [line]
                current_name = match.group(1)
                if line.get("type") == "add":
                    current_status = "added"
                elif line.get("type") == "remove":
                    current_status = "deleted"
                else:
                    current_status = "modified"
                continue
            if current_name:
                current.append(line)

        if current_name:
            cases.append(self._python_case(file_id, path, current_name, current_status, hunk, current))
        return cases

    def _python_case(
        self, file_id: str, path: str, name: str, status: str, hunk: Dict[str, Any], body: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        unknowns = ["Deleted test case retained as risk signal."] if status == "deleted" else []
        confidence = "fallback" if status == "deleted" else "certain"
        return self._case(file_id, path, name, status, confidence, hunk, body, unknowns)

    def _javascript_cases(
        self,
        file_id: str,
        path: str,
        hunk: Dict[str, Any],
        lines: List[Dict[str, str]],
        summary_unknowns: List[str],
    ) -> List[Dict[str, Any]]:
        cases: List[Dict[str, Any]] = []
        simple_pattern = re.compile(r"\b(?:it|test)\(\s*['\"]([^'\"]+)['\"]")
        parameterized_pattern = re.compile(r"\b(?:it|test)\.each\(")

        for index, line in enumerate(lines):
            content = line.get("content", "")
            if line.get("type") not in {"add", "remove"}:
                continue
            status = "added" if line.get("type") == "add" else "deleted"
            unknowns = ["Deleted test case retained as risk signal."] if status == "deleted" else []
            if parameterized_pattern.search(content):
                name = f"parameterized_case_{index + 1}"
                unknown = f"parameterized JavaScript test detected in {path}; extraction is fallback"
                summary_unknowns.append(unknown)
                unknowns = [*unknowns, unknown]
                cases.append(
                    self._case(file_id, path, name, status, "fallback", hunk, self._case_body(lines, index), unknowns)
                )
                continue
            match = simple_pattern.search(content)
            if match:
                cases.append(
                    self._case(
                        file_id,
                        path,
                        match.group(1),
                        status,
                        "heuristic",
                        hunk,
                        self._case_body(lines, index),
                        unknowns,
                    )
                )
        return cases

    def _fallback_case(
        self, file_id: str, path: str, hunk: Dict[str, Any], lines: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        removed = any(line.get("type") == "remove" for line in lines)
        unknown = (
            "Deleted test case retained as risk signal."
            if removed
            else "Could not identify individual test case from changed hunk."
        )
        return self._case(
            file_id,
            path,
            f"fallback_{hunk['hunk_id']}",
            "deleted" if removed else "unknown",
            "fallback",
            hunk,
            lines,
            [unknown],
            force_unknown_intent=True,
        )

    def _case(
        self,
        file_id: str,
        path: str,
        name: str,
        status: str,
        confidence: str,
        hunk: Dict[str, Any],
        body: List[Dict[str, str]],
        unknowns: Optional[List[str]] = None,
        *,
        force_unknown_intent: bool = False,
    ) -> Dict[str, Any]:
        assertions = [
            line
            for line in body
            if line.get("type") in {"add", "remove"} and ("assert " in line.get("content", "") or "expect(" in line.get("content", ""))
        ]
        text = "" if force_unknown_intent else self._intent_text(name, assertions)
        basis = []
        if text and name and not name.startswith("parameterized_case_"):
            basis.append("test_name")
        if text and assertions:
            basis.append("assertions")

        return {
            "test_case_id": "",
            "file_id": file_id,
            "path": path,
            "name": name,
            "status": status,
            "extraction_confidence": confidence,
            "evidence_grade": "unknown",
            "weakest_evidence_grade": "unknown",
            "last_status": "not_run",
            "covered_changes_preview": [],
            "highest_risk_covered_hunk_id": None,
            "intent_summary": {"text": text, "source": "rule_derived" if text else "unknown", "basis": basis},
            "_diff_hunks": [hunk],
            "_full_body": body,
            "_assertions": assertions,
            "_covered_scenarios": self._covered_scenarios(name, body, assertions),
            "_unknowns": unknowns or [],
        }

    def _covered_changes(
        self,
        case: Dict[str, Any],
        changed_file_details: Dict[str, Dict[str, Any]],
        review_graph_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        covered = []
        body_text = "\n".join(line.get("content", "") for line in case.get("_full_body", []))
        for detail in changed_file_details.values():
            path = detail["file"]["path"]
            hunk_items = detail.get("hunk_review_items", [])
            symbols = detail.get("changed_symbols", [])
            relationship = "unknown"
            basis: List[str] = []

            if any(self._symbol_name(symbol) in body_text for symbol in symbols if self._symbol_name(symbol)):
                relationship = "names_changed_symbol"
                basis.append("test_body_names_changed_symbol")
            elif self._has_graph_support(case, path, symbols, review_graph_data):
                relationship = "graph_inferred"
                basis.append("review_graph_edge")
            else:
                basis.append("graph_data_unavailable")

            evidence_grade = "inferred" if relationship != "unknown" else "unknown"
            items = hunk_items or [{"hunk_id": "", "risk_level": detail["file"].get("risk_level", "unknown")}]
            for item in items:
                covered.append(
                    {
                        "path": path,
                        "symbol": symbols[0] if symbols else "",
                        "hunk_id": item.get("hunk_id", ""),
                        "relationship": relationship,
                        "evidence_grade": evidence_grade,
                        "basis": basis,
                    }
                )
        return covered

    def _has_graph_support(
        self, case: Dict[str, Any], changed_path: str, symbols: List[str], review_graph_data: Dict[str, Any]
    ) -> bool:
        edges = review_graph_data.get("edges") or []
        if not edges:
            return False

        test_path = case["path"]
        symbol_names = {self._symbol_name(symbol) for symbol in symbols}
        symbol_names.discard("")

        for edge in edges:
            source = str(edge.get("source") or edge.get("from") or edge.get("source_id") or "")
            target = str(edge.get("target") or edge.get("to") or edge.get("target_id") or "")
            edge_text = " ".join([source, target, str(edge.get("path", "")), str(edge.get("evidence", ""))])
            mentions_test = test_path in edge_text or case["name"] in edge_text
            mentions_change = changed_path in edge_text or any(symbol in edge_text for symbol in symbol_names)
            if mentions_test and mentions_change:
                return True
        return False

    def _covered_preview(
        self, covered_changes: List[Dict[str, Any]], changed_file_details: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        risk_by_hunk = self._risk_by_hunk(changed_file_details)
        return [
            {
                "path": change["path"],
                "hunk_id": change.get("hunk_id") or None,
                "risk_level": risk_by_hunk.get(change.get("hunk_id", ""), "unknown"),
                "evidence_grade": change["evidence_grade"],
            }
            for change in covered_changes[:5]
        ]

    def _recommended_commands(self, case: Dict[str, Any]) -> List[Dict[str, Any]]:
        if case["status"] == "deleted":
            return []
        return [self._recommended_command(case)]

    def _recommended_command(self, case: Dict[str, Any]) -> Dict[str, Any]:
        command = f"uv run pytest {case['path']}" if case["path"].endswith(".py") else f"npm test -- {case['name']}"
        return {
            "command_id": "cmd_" + hashlib.sha256(command.encode("utf-8")).hexdigest()[:12],
            "command": command,
            "reason": "Run the changed test scope.",
            "scope": "test_file",
            "status": "not_run",
            "last_run_id": None,
        }

    def _historical_test_results(self, case: Dict[str, Any], command_evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for item in command_evidence:
            if not isinstance(item, dict):
                continue
            command = str(item.get("command") or "")
            if not command or not self._command_mentions_test_case(command, case):
                continue
            stdout = str(item.get("stdout") or item.get("output") or "")
            stderr = str(item.get("stderr") or "")
            status = "passed" if " passed" in stdout and "failed" not in stdout else "unknown"
            run_id = "codex_" + hashlib.sha256(f"{command}:{case['test_case_id']}".encode("utf-8")).hexdigest()[:12]
            results.append(
                {
                    "run_id": run_id,
                    "source": "codex_command_log",
                    "command_id": "",
                    "command": command,
                    "status": status,
                    "exit_code": 0 if status == "passed" else None,
                    "duration_ms": 0,
                    "stdout": stdout,
                    "stderr": stderr,
                    "stdout_truncated": False,
                    "stderr_truncated": False,
                    "timed_out": False,
                    "argv": [],
                    "executed_cases": [],
                    "analysis": {
                        "summary": (
                            "Codex previously ran a related test command and output was captured."
                            if stdout
                            else "Codex previously ran a related test command, but runner output was not captured."
                        ),
                        "scenarios": case.get("_covered_scenarios", []),
                        "test_data": [],
                        "coverage_gaps": [] if stdout else ["command_seen_without_output"],
                        "source": "rule_derived",
                        "basis": ["codex_command_log"],
                    },
                    "started_at": "",
                    "finished_at": "",
                    "captured_at": str(item.get("created_at") or ""),
                    "evidence_grade": "direct" if stdout else "indirect",
                }
            )
        return results[:3]

    def _command_mentions_test_case(self, command: str, case: Dict[str, Any]) -> bool:
        lowered = command.lower()
        path = case["path"].lower()
        basename = path.rsplit("/", 1)[-1]
        is_test_command = any(token in lowered for token in ("pytest", "npm test", "vitest", "jest"))
        mentions_scope = path in lowered or basename in lowered or case["name"].lower() in lowered
        return is_test_command and mentions_scope

    def _highest_risk_hunk(
        self, covered_changes: List[Dict[str, Any]], changed_file_details: Dict[str, Dict[str, Any]]
    ) -> Optional[str]:
        risk_by_hunk = self._risk_by_hunk(changed_file_details)
        candidates = [change.get("hunk_id", "") for change in covered_changes if change.get("hunk_id")]
        if not candidates:
            return None
        return max(candidates, key=lambda hunk_id: RISK_ORDER.get(risk_by_hunk.get(hunk_id, "unknown"), 0))

    def _risk_by_hunk(self, changed_file_details: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
        risks = {}
        for detail in changed_file_details.values():
            for item in detail.get("hunk_review_items", []):
                risks[item.get("hunk_id", "")] = item.get("risk_level", "unknown")
        return risks

    def _intent_text(self, name: str, assertions: List[Dict[str, str]]) -> str:
        readable = name.replace("_", " ")
        if assertions:
            return f"Verifies {readable} using {len(assertions)} assertion(s)."
        return f"Verifies {readable}." if readable else ""

    def _covered_scenarios(
        self,
        name: str,
        body: List[Dict[str, str]],
        assertions: List[Dict[str, str]],
    ) -> List[Dict[str, Any]]:
        scenarios: List[Dict[str, Any]] = []
        readable_name = name.replace("_", " ").strip()
        if readable_name and not name.startswith("fallback_"):
            scenarios.append(
                {
                    "title": f"Scenario named by test: {readable_name}.",
                    "source": "rule_derived",
                    "basis": ["test_name"],
                }
            )

        body_text = "\n".join(line.get("content", "") for line in body).lower()
        tokens = [
            ("error" in body_text or "exception" in body_text or "raises(" in body_text, "Error or exception handling path."),
            ("fallback" in body_text or "default" in body_text, "Fallback or default behavior."),
            ("empty" in body_text or "none" in body_text or "null" in body_text, "Empty, null, or missing-value input."),
            ("validation" in body_text or "invalid" in body_text, "Validation or invalid-input branch."),
            ("permission" in body_text or "auth" in body_text, "Permission or authentication branch."),
            ("status_code" in body_text or "response.status" in body_text, "HTTP/API response status behavior."),
            ("snapshot" in body_text or "persist" in body_text or "save_" in body_text, "Persistence or snapshot behavior."),
            ("graph" in body_text or "relationship" in body_text, "Relationship or graph-derived evidence behavior."),
            ("command" in body_text or "pytest" in body_text or "npm test" in body_text, "Recommended test command behavior."),
        ]
        for matched, title in tokens:
            if matched:
                scenarios.append({"title": title, "source": "rule_derived", "basis": ["code_tokens"]})

        for assertion in assertions[:4]:
            content = assertion.get("content", "").strip()
            if content:
                scenarios.append(
                    {
                        "title": f"Assertion checks: {content}",
                        "source": "rule_derived",
                        "basis": ["assertion"],
                    }
                )

        deduped: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for scenario in scenarios:
            title = scenario["title"]
            if title in seen:
                continue
            seen.add(title)
            deduped.append(scenario)
        return deduped[:8]

    def _case_body(self, lines: List[Dict[str, str]], start: int) -> List[Dict[str, str]]:
        body = [lines[start]]
        for line in lines[start + 1 :]:
            content = line.get("content", "")
            if line.get("type") in {"add", "remove"} and re.search(r"\b(?:it|test)(?:\.each)?\(", content):
                break
            body.append(line)
            if line.get("type") in {"add", "remove"} and content.strip().startswith("})"):
                break
        return body

    def _public_case(self, case: Dict[str, Any]) -> Dict[str, Any]:
        return {key: value for key, value in case.items() if not key.startswith("_")}

    def _test_case_id(self, path: str, name: str, hunk_id: str, ordinal: int) -> str:
        raw = f"{path}::{name}::{hunk_id}::{ordinal}"
        return "tc_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def _strongest_grade(self, items: Iterable[Dict[str, Any]]) -> str:
        grades = [item.get("evidence_grade", "unknown") for item in items]
        return max(grades, key=lambda grade: GRADE_ORDER.get(grade, 0)) if grades else ""

    def _weakest_grade(self, items: Iterable[Dict[str, Any]]) -> str:
        grades = [item.get("weakest_evidence_grade") or item.get("evidence_grade", "unknown") for item in items]
        return min(grades, key=lambda grade: GRADE_ORDER.get(grade, 0)) if grades else ""

    def _symbol_name(self, symbol: str) -> str:
        return str(symbol).split(".")[-1]

    def _is_test_path(self, path: str) -> bool:
        return is_test_path(path)
