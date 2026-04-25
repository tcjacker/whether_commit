from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from typing import Any, Dict, List, Protocol


class CodexFileAssessmentAdapter(Protocol):
    def assess(self, payload: Dict[str, Any]) -> Dict[str, Any] | None:
        """Return a schema-shaped Codex assessment, or None when unavailable."""


class DisabledCodexFileAssessmentAdapter:
    """
    Placeholder adapter for Phase 1.5.

    The runtime should use Codex's existing environment when this becomes active;
    there is intentionally no token/base URL/provider configuration here.
    """

    def assess(self, payload: Dict[str, Any]) -> Dict[str, Any] | None:
        return None


class LocalCodexFileAssessmentAdapter:
    """
    Runs the local Codex CLI as the assessment agent.

    The adapter intentionally reuses the user's existing Codex environment and
    does not accept provider/token/base URL configuration.
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

    def assess(self, payload: Dict[str, Any]) -> Dict[str, Any] | None:
        prompt = self._build_prompt(payload)
        output_path = self._new_output_path()
        command = self._command(prompt, output_path)
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

        if completed.returncode != 0:
            self._remove_output_path(output_path)
            return None

        last_message = self._read_output_path(output_path)
        self._remove_output_path(output_path)
        parsed = self._parse_json_object(last_message) or self._parse_json_object(completed.stdout)
        if not isinstance(parsed, dict):
            return None
        return self._normalize_assessment(parsed)

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

    def _build_prompt(self, payload: Dict[str, Any]) -> str:
        compact_payload = self._compact_payload(payload)
        language_instruction = self._language_instruction()
        return (
            "You are the Codex Agent producing a per-file Agentic Change Assessment.\n"
            "Work in harness-style review mode: actively gather read-only evidence before writing the assessment.\n"
            f"{language_instruction}\n"
            "Evidence gathering rules:\n"
            "- You may inspect the repository with read-only commands only.\n"
            "- Prefer git diff -- <file>, git status --short, rg, sed, and ls for focused inspection.\n"
            "- Query the changed source file, related tests, nearby symbols, and provided assessment facts.\n"
            "- Look for Codex / Claude / vibe coding operation logs only when paths or evidence hints are available.\n"
            "- Do not modify files. Do not run long or mutating commands. Do not run full test suites.\n"
            "- If you do not run a test command, say so explicitly in unknowns or test_summary.\n"
            "Assessment quality rules:\n"
            "- 中文口径：明确区分事实、推断、未知、建议验证命令。\n"
            "- Separate facts, inferences, unknowns, and recommended verification command in the user-facing text.\n"
            "- Do not present inferred test relationships as executed test results.\n"
            "- Explain why the verdict follows from the evidence, not just what changed.\n"
            "Return exactly one JSON object and no markdown.\n"
            "JSON schema:\n"
            "{\n"
            '  "why_changed": "specific reason this file changed",\n'
            '  "impact_summary": "behavioral and production impact of this file change",\n'
            '  "test_summary": "test coverage and execution evidence",\n'
            '  "recommended_action": "next review action for the human reviewer",\n'
            '  "confidence": "high|medium|low",\n'
            '  "evidence_refs": ["git_diff"],\n'
            '  "unknowns": []\n'
            "}\n"
            "Assessment facts:\n"
            f"{json.dumps(compact_payload, ensure_ascii=False, indent=2)}"
        )

    def _language_instruction(self) -> str:
        if self.language == "zh-CN":
            return "默认使用简体中文输出所有面向用户的评审内容；JSON 字段名保持英文。"
        if self.language.startswith("en"):
            return "Use English for all user-facing assessment text."
        return f"Use {self.language} for all user-facing assessment text when possible; JSON field names stay in English."

    def _compact_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "file": payload.get("file", {}),
            "diff_hunks": self._compact_hunks(payload.get("diff_hunks", [])),
            "changed_symbols": self._limit_list(payload.get("changed_symbols", []), 40),
            "related_agent_records": self._compact_agent_records(payload.get("related_agent_records", [])),
            "related_tests": self._limit_list(payload.get("related_tests", []), 40),
            "impact_facts": self._limit_list(payload.get("impact_facts", []), 30),
            "rule_assessment": payload.get("file_assessment", {}),
        }

    def _compact_hunks(self, hunks: Any) -> List[Dict[str, Any]]:
        compact: List[Dict[str, Any]] = []
        for hunk in hunks[:8] if isinstance(hunks, list) else []:
            if not isinstance(hunk, dict):
                continue
            lines = hunk.get("lines", [])
            compact.append(
                {
                    "hunk_id": hunk.get("hunk_id"),
                    "old_start": hunk.get("old_start"),
                    "new_start": hunk.get("new_start"),
                    "lines": self._limit_list(lines if isinstance(lines, list) else [], 80),
                }
            )
        return compact

    def _compact_agent_records(self, records: Any) -> List[Dict[str, Any]]:
        compact: List[Dict[str, Any]] = []
        for record in records[:10] if isinstance(records, list) else []:
            if not isinstance(record, dict):
                continue
            compact.append(
                {
                    "source": record.get("source"),
                    "capture_level": record.get("capture_level"),
                    "evidence_sources": record.get("evidence_sources", []),
                    "task_summary": record.get("task_summary", ""),
                    "declared_intent": record.get("declared_intent", ""),
                    "reasoning_summary": record.get("reasoning_summary", ""),
                    "commands_run": self._limit_list(record.get("commands_run", []), 20),
                    "tests_run": self._limit_list(record.get("tests_run", []), 20),
                    "known_limitations": self._limit_list(record.get("known_limitations", []), 10),
                }
            )
        return compact

    def _limit_list(self, value: Any, limit: int) -> List[Any]:
        return value[:limit] if isinstance(value, list) else []

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
        for candidate in reversed(candidates):
            if all(field in candidate for field in ("why_changed", "impact_summary", "test_summary", "recommended_action")):
                return candidate
        return candidates[-1] if candidates else None

    def _normalize_assessment(self, parsed: Dict[str, Any]) -> Dict[str, Any] | None:
        required = ["why_changed", "impact_summary", "test_summary", "recommended_action"]
        normalized: Dict[str, Any] = {}
        for field in required:
            value = str(parsed.get(field, "")).strip()
            if not value:
                return None
            normalized[field] = value

        confidence = str(parsed.get("confidence", "medium")).strip().lower()
        normalized["confidence"] = confidence if confidence in {"high", "medium", "low"} else "medium"
        normalized["evidence_refs"] = self._string_list(parsed.get("evidence_refs")) or ["git_diff"]
        normalized["unknowns"] = self._string_list(parsed.get("unknowns"))
        return normalized

    def _string_list(self, value: Any) -> List[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def _new_output_path(self) -> str:
        handle = tempfile.NamedTemporaryFile(prefix="codex_file_assessment_", suffix=".txt", delete=False)
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
