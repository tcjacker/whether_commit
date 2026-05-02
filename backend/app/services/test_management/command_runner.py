from __future__ import annotations

import os
import re
import shlex
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


MAX_OUTPUT_BYTES = 64 * 1024
DISALLOWED_TOKENS = {";", "&&", "||", "|", ">", ">>", "<"}
ALLOWED_PREFIXES = (
    ("pytest",),
    ("uv", "run", "pytest"),
    ("npm", "test"),
    ("npm", "run", "test"),
)


class CommandValidationError(ValueError):
    pass


def command_to_argv(command: str) -> List[str]:
    if "$(" in command or "`" in command:
        raise CommandValidationError("shell substitution is not allowed")
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        raise CommandValidationError("command cannot be parsed") from exc
    if not argv:
        raise CommandValidationError("command is empty")
    if any(token in DISALLOWED_TOKENS for token in argv):
        raise CommandValidationError("shell control operators are not allowed")
    if not any(tuple(argv[: len(prefix)]) == prefix for prefix in ALLOWED_PREFIXES):
        raise CommandValidationError("command is not in the test command allowlist")
    return argv


def verify_workspace_path(workspace_path: str) -> str:
    resolved = os.path.realpath(workspace_path)
    path = Path(resolved)
    if not path.is_dir():
        raise CommandValidationError("workspace_path is not a directory")
    if not ((path / ".git").exists() or (path.parent / ".git" / "worktrees" / path.name).exists()):
        raise CommandValidationError("workspace_path does not look like a git workspace")
    return resolved


def _bounded(text: str) -> tuple[str, bool]:
    data = text.encode("utf-8", errors="replace")
    if len(data) <= MAX_OUTPUT_BYTES:
        return text, False
    return data[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace"), True


def run_test_command(command: str, workspace_path: str, *, timeout_seconds: int = 120) -> Dict[str, Any]:
    argv = command_to_argv(command)
    cwd = verify_workspace_path(workspace_path)
    started = time.monotonic()
    timed_out = False
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        exit_code = completed.returncode
        stdout, stdout_truncated = _bounded(completed.stdout)
        stderr, stderr_truncated = _bounded(completed.stderr)
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = None
        stdout, stdout_truncated = _bounded(exc.stdout if isinstance(exc.stdout, str) else "")
        stderr, stderr_truncated = _bounded(exc.stderr if isinstance(exc.stderr, str) else "")

    duration_ms = int((time.monotonic() - started) * 1000)
    status = "partial" if timed_out else ("passed" if exit_code == 0 else "failed")
    return {
        "status": status,
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "stdout": stdout,
        "stderr": stderr,
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
        "timed_out": timed_out,
        "argv": argv,
    }


def collect_test_cases(command: str, workspace_path: str, *, timeout_seconds: int = 60) -> List[Dict[str, Any]]:
    argv = command_to_argv(command)
    cwd = verify_workspace_path(workspace_path)
    if "pytest" not in argv:
        return []
    pytest_index = argv.index("pytest")
    collect_argv = [*argv[: pytest_index + 1], "--collect-only", "-q", *argv[pytest_index + 1 :]]
    completed = subprocess.run(
        collect_argv,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    cases = []
    for line in completed.stdout.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("<") or stripped.startswith("="):
            continue
        if "::" not in stripped:
            continue
        cases.append(
            {
                "node_id": stripped,
                "name": stripped.rsplit("::", 1)[-1],
                "status": "unknown",
                "source": "collect_only",
                "scenarios": [],
                "test_data": [],
            }
        )
    return cases


def parse_summary_counts(stdout: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for name in ("passed", "failed", "skipped", "error", "errors"):
        match = re.search(rf"(\d+)\s+{name}", stdout)
        if match:
            key = "failed" if name in {"error", "errors"} else name
            counts[key] = counts.get(key, 0) + int(match.group(1))
    return counts


def analyze_test_result(
    *,
    command: str,
    run_result: Dict[str, Any],
    workspace_path: str,
    focused_scenarios: List[Dict[str, Any]],
) -> Dict[str, Any]:
    executed_cases = collect_test_cases(command, workspace_path)
    counts = parse_summary_counts(run_result.get("stdout", ""))
    status = run_result.get("status", "unknown")
    passed_count = counts.get("passed", 0)
    failed_count = counts.get("failed", 0)
    case_count = len(executed_cases) or passed_count + failed_count
    for case in executed_cases:
        if status == "passed":
            case["status"] = "passed"
    gaps = []
    basis = ["runner_output"]
    if executed_cases:
        basis.append("collect_only")
    else:
        gaps.append("Runner output did not include individual test case names; case list could not be proven.")
    if not focused_scenarios:
        gaps.append("No scenario extraction was available for the selected test case.")
    summary = (
        f"{case_count} test case(s) were associated with this run; "
        f"{passed_count} passed and {failed_count} failed based on runner output."
    )
    return {
        "summary": summary,
        "scenarios": focused_scenarios,
        "test_data": _test_data_from_cases(executed_cases),
        "covered_code_analysis": [],
        "coverage_gaps": gaps,
        "source": "rule_derived",
        "basis": basis,
        "executed_cases": executed_cases,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "evidence_grade": "direct" if run_result.get("exit_code") is not None else "unknown",
    }


def analyze_stored_test_result(*, detail: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    executed_cases = result.get("executed_cases", [])
    passed_count = sum(1 for case in executed_cases if case.get("status") == "passed")
    failed_count = sum(1 for case in executed_cases if case.get("status") == "failed")
    case_count = len(executed_cases)
    scenarios = _merge_scenarios(
        detail.get("covered_scenarios", []),
        [_scenario_from_case(case) for case in executed_cases[:20]],
    )
    test_data = _test_data_from_cases(executed_cases)
    test_data.extend(_literal_test_data(detail.get("full_body", [])))
    gaps = []
    if not executed_cases:
        gaps.append("No individual executed test cases were stored for this run.")
    if not scenarios:
        gaps.append("No covered scenarios could be derived from the test name, code, or run result.")
    if not test_data:
        gaps.append("No concrete test data literals were detected in the stored test code.")
    summary = (
        f"Rule analysis inspected {case_count} executed case(s): {passed_count} passed and {failed_count} failed. "
        f"The selected test is {detail.get('test_case', {}).get('name', 'unknown')}."
    )
    return {
        "summary": summary,
        "scenarios": scenarios,
        "test_data": list(dict.fromkeys(test_data))[:20],
        "covered_code_analysis": [],
        "coverage_gaps": gaps,
        "source": "rule_derived",
        "basis": ["stored_run", "test_code", "assertions"],
    }


def _test_data_from_cases(cases: List[Dict[str, Any]]) -> List[str]:
    findings = []
    for case in cases[:20]:
        name = case.get("name", "")
        if "[" in name and "]" in name:
            findings.append(f"Parameterized data: {name[name.find('[') + 1:name.rfind(']')]}")
    return findings


def _scenario_from_case(case: Dict[str, Any]) -> Dict[str, Any]:
    name = str(case.get("name") or "unknown")
    return {
        "title": f"Executed case: {name.replace('_', ' ')}.",
        "source": "rule_derived",
        "basis": ["executed_case_name"],
    }


def _merge_scenarios(*groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen = set()
    for group in groups:
        for item in group:
            title = item.get("title")
            if not title or title in seen:
                continue
            seen.add(title)
            merged.append(item)
    return merged[:20]


def _literal_test_data(lines: List[Dict[str, Any]]) -> List[str]:
    findings = []
    for line in lines:
        content = str(line.get("content") or "")
        for match in re.findall(r"(['\"])(?P<value>[^'\"]{2,80})\1", content):
            value = match[1].strip()
            if value and not value.startswith(("test_", "backend/")):
                findings.append(f"Literal test data: {value}")
    return findings[:20]
