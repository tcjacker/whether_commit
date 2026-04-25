import subprocess

from app.services.agentic_change_assessment.codex_file_assessment import LocalCodexFileAssessmentAdapter


def test_local_codex_adapter_runs_cli_and_normalizes_json(monkeypatch):
    captured = {}

    def fake_run(command, check, capture_output, text, timeout):
        captured["command"] = command
        captured["timeout"] = timeout
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=(
                '{"why_changed":"Changed to support assessment review.",'
                '"impact_summary":"Impacts the per-file review panel.",'
                '"test_summary":"Related endpoint tests cover the response.",'
                '"recommended_action":"Review the diff before accepting.",'
                '"confidence":"high",'
                '"evidence_refs":["git_diff","agent_activity_evidence"],'
                '"unknowns":[]}'
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    adapter = LocalCodexFileAssessmentAdapter(workspace_path="/tmp/workspace", timeout_seconds=12)
    result = adapter.assess(
        {
            "file": {"path": "backend/app/main.py"},
            "diff_hunks": [{"lines": [{"type": "add", "content": "+hello"}]}],
            "file_assessment": {"why_changed": "rule fallback"},
        }
    )

    assert result == {
        "why_changed": "Changed to support assessment review.",
        "impact_summary": "Impacts the per-file review panel.",
        "test_summary": "Related endpoint tests cover the response.",
        "recommended_action": "Review the diff before accepting.",
        "confidence": "high",
        "evidence_refs": ["git_diff", "agent_activity_evidence"],
        "unknowns": [],
    }
    assert captured["command"][:4] == ["codex", "--ask-for-approval", "never", "exec"]
    assert "--sandbox" in captured["command"]
    assert "read-only" in captured["command"]
    assert "/tmp/workspace" in captured["command"]
    assert captured["timeout"] == 12


def test_local_codex_adapter_prompt_defaults_to_chinese_harness_instructions(monkeypatch):
    captured = {}

    def fake_run(command, check, capture_output, text, timeout):
        captured["prompt"] = command[-1]
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=(
                '{"why_changed":"中文原因","impact_summary":"中文影响",'
                '"test_summary":"中文测试","recommended_action":"中文建议",'
                '"confidence":"medium","evidence_refs":["git_diff"],"unknowns":[]}'
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = LocalCodexFileAssessmentAdapter(workspace_path="/tmp/workspace").assess(
        {
            "file": {"path": "backend/app/main.py"},
            "diff_hunks": [],
            "related_agent_records": [],
            "related_tests": [],
            "impact_facts": [],
            "file_assessment": {},
        }
    )

    assert result["why_changed"] == "中文原因"
    assert "默认使用简体中文" in captured["prompt"]
    assert "harness-style" in captured["prompt"]
    assert "git diff --" in captured["prompt"]
    assert "rg" in captured["prompt"]
    assert "Codex / Claude / vibe coding" in captured["prompt"]
    assert "事实、推断、未知、建议验证命令" in captured["prompt"]


def test_local_codex_adapter_accepts_language_override(monkeypatch):
    captured = {}

    def fake_run(command, check, capture_output, text, timeout):
        captured["prompt"] = command[-1]
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=(
                '{"why_changed":"English reason","impact_summary":"English impact",'
                '"test_summary":"English tests","recommended_action":"English action",'
                '"confidence":"medium","evidence_refs":["git_diff"],"unknowns":[]}'
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    LocalCodexFileAssessmentAdapter(workspace_path="/tmp/workspace", language="en-US").assess({"file": {}})

    assert "Use English for all user-facing assessment text." in captured["prompt"]


def test_local_codex_adapter_extracts_json_from_noisy_output(monkeypatch):
    def fake_run(command, check, capture_output, text, timeout):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=(
                "warning\n"
                "```json\n"
                '{"why_changed":"A","impact_summary":"B","test_summary":"C",'
                '"recommended_action":"D","confidence":"unexpected"}\n'
                "```"
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = LocalCodexFileAssessmentAdapter(workspace_path="/tmp/workspace").assess({"file": {}})

    assert result["confidence"] == "medium"
    assert result["evidence_refs"] == ["git_diff"]


def test_local_codex_adapter_returns_none_for_invalid_or_failed_output(monkeypatch):
    def fake_run(command, check, capture_output, text, timeout):
        return subprocess.CompletedProcess(command, 1, stdout="not json", stderr="failed")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert LocalCodexFileAssessmentAdapter(workspace_path="/tmp/workspace").assess({"file": {}}) is None
