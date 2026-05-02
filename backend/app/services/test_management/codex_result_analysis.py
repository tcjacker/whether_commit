from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from typing import Any, Dict, List


class LocalCodexTestResultAnalysisAdapter:
    """
    Runs the local Codex CLI to analyze a stored test result.

    This uses the user's existing Codex environment and only grants read-only
    repository access. It returns a TestResultAnalysis-shaped dict, or None when
    Codex is unavailable, times out, or returns invalid output.
    """

    def __init__(
        self,
        *,
        workspace_path: str | None = None,
        timeout_seconds: int = 180,
        command: str = "codex",
        language: str = "zh-CN",
    ) -> None:
        self.workspace_path = workspace_path or os.getcwd()
        self.timeout_seconds = timeout_seconds
        self.command = command
        self.language = language

    def analyze(self, *, detail: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any] | None:
        output_path = self._new_output_path()
        command = self._command(self._build_prompt(detail=detail, result=result), output_path)
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            self._remove_output_path(output_path)
            return None

        last_message = self._read_output_path(output_path)
        self._remove_output_path(output_path)
        if completed.returncode != 0:
            return None

        parsed = self._parse_json_object(last_message) or self._parse_json_object(completed.stdout)
        if not isinstance(parsed, dict):
            return None
        return self._normalize_analysis(parsed)

    def _command(self, prompt: str, output_path: str) -> List[str]:
        return [
            self.command,
            "--ask-for-approval",
            "never",
            "exec",
            "--cd",
            self.workspace_path,
            "--sandbox",
            "read-only",
            "--color",
            "never",
            "--ephemeral",
            "--output-last-message",
            output_path,
            prompt,
        ]

    def _build_prompt(self, *, detail: Dict[str, Any], result: Dict[str, Any]) -> str:
        language_instruction = self._language_instruction()
        return (
            "You are the Codex Agent analyzing a completed test run for a Test Management workbench.\n"
            "Work in review mode: inspect the provided run result and, when useful, read the relevant test code from the repository.\n"
            f"{language_instruction}\n"
            "Evidence rules:\n"
            "- You may run read-only inspection commands such as rg, sed, git diff, and ls.\n"
            "- Do not modify files. Do not rerun tests. The test execution result is already provided.\n"
            "- Distinguish executed facts from inferred scenarios and unknown coverage gaps.\n"
            "- Explain which scenarios, input data, parameters, fixtures, and assertions were exercised.\n"
            "- If individual cases are unavailable, say that explicitly in coverage_gaps.\n"
            "- Keep the selected test case separate from the wider command scope.\n"
            "Output content rules:\n"
            "- Summary must start with the Selected test case and then state the Command-level result.\n"
            "- scenarios must list Positive coverage for the selected test case first.\n"
            "- If the command executed additional tests, include them as Other executed cases, clearly labeled as command-scope context.\n"
            "- test_data must use concrete, structured entries such as file:, fixture:, input:, expected:, assertion:, parameter:, or command:.\n"
            "- coverage_gaps must be limited to Not covered / not proven statements and must not repeat positive coverage.\n"
            "- For each provided covered_changed_code item, write one covered_code_analysis item. Preserve relationship and evidence_grade unless repository inspection proves a stronger or weaker grade.\n"
            "- Do not upgrade unknown or inferred relationships to direct evidence without a concrete call, assertion, import, or executed behavior basis.\n"
            "Return exactly one JSON object and no markdown.\n"
            "JSON schema:\n"
            "{\n"
            '  "summary": "Selected test case: ... Command-level result: ...",\n'
            '  "scenarios": [{"title": "Selected case covers: ...", "source": "generated", "basis": ["runner_output", "test_code"]}, {"title": "Other executed case: ...", "source": "generated", "basis": ["command_scope"]}],\n'
            '  "test_data": ["file: ...", "fixture: ...", "input: ...", "expected: ...", "assertion: ..."],\n'
            '  "covered_code_analysis": [{"path": "...", "symbol": "...", "hunk_id": "...", "relationship": "calls|imports|shares_fixture|co_changed|names_changed_symbol|same_file|graph_inferred|unknown", "evidence_grade": "direct|indirect|inferred|claimed|not_run|unknown", "analysis": "why this test does or does not cover this changed code", "basis": ["assertion", "covered_changed_code"]}],\n'
            '  "coverage_gaps": ["Not covered / not proven: ..."],\n'
            '  "basis": ["codex_agent", "stored_run", "test_code"]\n'
            "}\n"
            "Assessment payload:\n"
            f"{json.dumps(self._compact_payload(detail=detail, result=result), ensure_ascii=False, indent=2)}"
        )

    def _language_instruction(self) -> str:
        if self.language == "zh-CN":
            return "默认使用简体中文输出 summary、scenarios、test_data 和 coverage_gaps；JSON 字段名保持英文。"
        if self.language.startswith("en"):
            return "Use English for all user-facing analysis text."
        return f"Use {self.language} for user-facing analysis text when possible; JSON field names stay English."

    def _compact_payload(self, *, detail: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "test_case": detail.get("test_case", {}),
            "test_file_path": detail.get("test_case", {}).get("path"),
            "test_body": self._limit_list(detail.get("full_body", []), 220),
            "assertions": self._limit_list(detail.get("assertions", []), 80),
            "covered_scenarios_from_rules": self._limit_list(detail.get("covered_scenarios", []), 40),
            "covered_changed_code": self._limit_list(detail.get("covered_changes", []), 40),
            "related_agent_claims": self._limit_list(detail.get("related_agent_claims", []), 20),
            "run": {
                "run_id": result.get("run_id"),
                "command": result.get("command"),
                "status": result.get("status"),
                "exit_code": result.get("exit_code"),
                "duration_ms": result.get("duration_ms"),
                "source": result.get("source"),
                "executed_cases": self._limit_list(result.get("executed_cases", []), 80),
                "stdout": self._limit_text(result.get("stdout", ""), 12000),
                "stderr": self._limit_text(result.get("stderr", ""), 6000),
            },
        }

    def _normalize_analysis(self, parsed: Dict[str, Any]) -> Dict[str, Any] | None:
        summary = str(parsed.get("summary") or "").strip()
        if not summary:
            return None

        basis = self._string_list(parsed.get("basis"))
        if "codex_agent" not in basis:
            basis.insert(0, "codex_agent")

        return {
            "summary": summary,
            "scenarios": self._scenario_list(parsed.get("scenarios")),
            "test_data": self._string_list(parsed.get("test_data"))[:30],
            "covered_code_analysis": self._covered_code_analysis_list(parsed.get("covered_code_analysis")),
            "coverage_gaps": self._string_list(parsed.get("coverage_gaps"))[:30],
            "source": "generated",
            "basis": basis[:20],
        }

    def _covered_code_analysis_list(self, value: Any) -> List[Dict[str, Any]]:
        if not isinstance(value, list):
            return []
        valid_relationships = {
            "calls",
            "imports",
            "shares_fixture",
            "co_changed",
            "names_changed_symbol",
            "same_file",
            "graph_inferred",
            "unknown",
        }
        valid_grades = {"direct", "indirect", "inferred", "claimed", "not_run", "unknown"}
        analyses = []
        for item in value[:40]:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path") or "").strip()
            if not path:
                continue
            relationship = str(item.get("relationship") or "unknown").strip()
            if relationship not in valid_relationships:
                relationship = "unknown"
            evidence_grade = str(item.get("evidence_grade") or "unknown").strip()
            if evidence_grade not in valid_grades:
                evidence_grade = "unknown"
            analyses.append(
                {
                    "path": path,
                    "symbol": str(item.get("symbol") or "").strip(),
                    "hunk_id": str(item.get("hunk_id") or "").strip(),
                    "relationship": relationship,
                    "evidence_grade": evidence_grade,
                    "analysis": str(item.get("analysis") or "").strip(),
                    "basis": self._string_list(item.get("basis"))[:12],
                }
            )
        return analyses

    def _scenario_list(self, value: Any) -> List[Dict[str, Any]]:
        if not isinstance(value, list):
            return []
        scenarios = []
        for item in value[:30]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            source = str(item.get("source") or "generated").strip()
            if source not in {"rule_derived", "agent_claim", "generated", "unknown"}:
                source = "generated"
            scenarios.append(
                {
                    "title": title,
                    "source": source,
                    "basis": self._string_list(item.get("basis"))[:10],
                }
            )
        return scenarios

    def _parse_json_object(self, output: str) -> Dict[str, Any] | None:
        text = output.strip()
        if not text:
            return None

        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fence_match:
            text = fence_match.group(1)
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                return None
            return parsed if isinstance(parsed, dict) else None

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            return parsed

        decoder = json.JSONDecoder()
        candidates: List[Dict[str, Any]] = []
        for match in re.finditer(r"\{", text):
            try:
                candidate, _ = decoder.raw_decode(text[match.start() :])
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict):
                candidates.append(candidate)
        return candidates[-1] if candidates else None

    def _string_list(self, value: Any) -> List[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def _limit_list(self, value: Any, limit: int) -> List[Any]:
        return value[:limit] if isinstance(value, list) else []

    def _limit_text(self, value: Any, limit: int) -> str:
        text = str(value or "")
        return text[:limit]

    def _new_output_path(self) -> str:
        handle = tempfile.NamedTemporaryFile(prefix="codex_test_result_analysis_", suffix=".txt", delete=False)
        handle.close()
        return handle.name

    def _read_output_path(self, output_path: str) -> str:
        try:
            with open(output_path, "r", encoding="utf-8") as file:
                return file.read()
        except OSError:
            return ""

    def _remove_output_path(self, output_path: str) -> None:
        try:
            os.unlink(output_path)
        except OSError:
            pass
