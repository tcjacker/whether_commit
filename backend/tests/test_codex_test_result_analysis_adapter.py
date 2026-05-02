import subprocess

from app.services.test_management.codex_result_analysis import LocalCodexTestResultAnalysisAdapter


def test_local_codex_test_result_adapter_runs_cli_and_normalizes_analysis(monkeypatch):
    captured = {}

    def fake_run(command, check, capture_output, text, timeout):
        captured["command"] = command
        captured["timeout"] = timeout
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=(
                '{"summary":"Codex found the run covers the review decision path.",'
                '"scenarios":[{"title":"Builder emits needs_tests.","source":"generated","basis":["test_code"]}],'
                '"test_data":["review_decision=needs_tests"],'
                '"covered_code_analysis":[{"path":"backend/app/services/builder.py","symbol":"build","hunk_id":"hunk_1",'
                '"relationship":"calls","evidence_grade":"direct","analysis":"The assertion exercises build output.",'
                '"basis":["assertion","changed_hunk"]}],'
                '"coverage_gaps":["safe_to_commit is not covered"],'
                '"basis":["stored_run","test_code"]}'
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = LocalCodexTestResultAnalysisAdapter(workspace_path="/tmp/workspace", timeout_seconds=12).analyze(
        detail={
            "test_case": {"name": "test_builder_emits_review_signals", "path": "backend/tests/test_builder.py"},
            "full_body": [{"type": "context", "content": "def test_builder_emits_review_signals():"}],
            "covered_scenarios": [],
        },
        result={
            "run_id": "run_builder",
            "command": "uv run pytest backend/tests/test_builder.py",
            "status": "passed",
            "executed_cases": [{"name": "test_builder_emits_review_signals", "status": "passed"}],
            "stdout": "1 passed",
        },
    )

    assert result == {
        "summary": "Codex found the run covers the review decision path.",
        "scenarios": [{"title": "Builder emits needs_tests.", "source": "generated", "basis": ["test_code"]}],
        "test_data": ["review_decision=needs_tests"],
        "covered_code_analysis": [
            {
                "path": "backend/app/services/builder.py",
                "symbol": "build",
                "hunk_id": "hunk_1",
                "relationship": "calls",
                "evidence_grade": "direct",
                "analysis": "The assertion exercises build output.",
                "basis": ["assertion", "changed_hunk"],
            }
        ],
        "coverage_gaps": ["safe_to_commit is not covered"],
        "source": "generated",
        "basis": ["codex_agent", "stored_run", "test_code"],
    }
    assert captured["command"][:4] == ["codex", "--ask-for-approval", "never", "exec"]
    assert "--sandbox" in captured["command"]
    assert "read-only" in captured["command"]
    assert "/tmp/workspace" in captured["command"]
    assert captured["timeout"] == 12


def test_local_codex_test_result_adapter_prompt_forbids_rerunning_tests(monkeypatch):
    captured = {}

    def fake_run(command, check, capture_output, text, timeout):
        captured["prompt"] = command[-1]
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='{"summary":"中文分析","scenarios":[],"test_data":[],"coverage_gaps":[],"basis":[]}',
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = LocalCodexTestResultAnalysisAdapter(workspace_path="/tmp/workspace").analyze(detail={"test_case": {}}, result={})

    assert result["basis"] == ["codex_agent"]
    assert "默认使用简体中文" in captured["prompt"]
    assert "Do not rerun tests" in captured["prompt"]
    assert "executed facts" in captured["prompt"]
    assert "Selected test case" in captured["prompt"]
    assert "Command-level result" in captured["prompt"]
    assert "Other executed cases" in captured["prompt"]
    assert "Positive coverage" in captured["prompt"]
    assert "Not covered / not proven" in captured["prompt"]
    assert "test_data" in captured["prompt"]
    assert "file:" in captured["prompt"]
    assert "fixture:" in captured["prompt"]
    assert "assertion:" in captured["prompt"]
    assert "covered_code_analysis" in captured["prompt"]
    assert "relationship" in captured["prompt"]
    assert "evidence_grade" in captured["prompt"]
    assert "Do not upgrade unknown or inferred relationships to direct evidence" in captured["prompt"]


def test_local_codex_test_result_adapter_returns_none_for_invalid_output(monkeypatch):
    def fake_run(command, check, capture_output, text, timeout):
        return subprocess.CompletedProcess(command, 0, stdout='{"scenarios":[]}', stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert LocalCodexTestResultAnalysisAdapter(workspace_path="/tmp/workspace").analyze(detail={}, result={}) is None
