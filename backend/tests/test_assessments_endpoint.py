from fastapi.testclient import TestClient

from app.main import app
from app.services.snapshot_store.store import store as snapshot_store


client = TestClient(app)


def test_get_latest_assessment_returns_manifest(monkeypatch):
    monkeypatch.setattr(
        snapshot_store,
        "get_latest_assessment_manifest",
        lambda repo_key, workspace_path=None: {
            "assessment_id": "aca_ws_1",
            "workspace_snapshot_id": "ws_1",
            "repo_key": repo_key,
            "status": "ready",
            "summary": {},
            "file_list": [],
            "risk_signals_summary": [],
            "agent_sources": ["git_diff"],
            "review_progress": {},
        },
    )

    response = client.get("/api/assessments/latest?repo_key=demo")

    assert response.status_code == 200
    assert response.json()["assessment_id"] == "aca_ws_1"


def test_get_file_detail_returns_changed_file_detail(monkeypatch):
    monkeypatch.setattr(
        snapshot_store,
        "get_assessment_file_detail",
        lambda repo_key, snapshot_id, file_id, workspace_path=None: {
            "file": {
                "file_id": file_id,
                "path": "backend/app/main.py",
                "old_path": None,
                "status": "modified",
                "additions": 1,
                "deletions": 0,
                "risk_level": "low",
                "coverage_status": "unknown",
                "review_status": "unreviewed",
                "agent_sources": ["git_diff"],
                "diff_fingerprint": "sha256:abc",
            },
            "diff_hunks": [],
            "changed_symbols": [],
            "related_agent_records": [],
            "related_tests": [],
            "impact_facts": [],
            "file_assessment": {},
            "review_state": {
                "review_status": "unreviewed",
                "diff_fingerprint": "sha256:abc",
                "reviewer": None,
                "reviewed_at": None,
                "notes": [],
            },
        },
    )

    response = client.get("/api/assessments/ws_1/files/cf_abc123?repo_key=demo")

    assert response.status_code == 200
    assert response.json()["file"]["file_id"] == "cf_abc123"


def test_get_assessment_tests_returns_summary(monkeypatch):
    monkeypatch.setattr(
        snapshot_store,
        "get_test_management_summary",
        lambda repo_key, snapshot_id, workspace_path=None: {
            "assessment_id": f"aca_{snapshot_id}",
            "repo_key": repo_key,
            "changed_test_file_count": 1,
            "test_case_count": 1,
            "evidence_grade_counts": {"unknown": 1},
            "command_status_counts": {"not_run": 1},
            "files": [
                {
                    "file_id": "cf_test",
                    "path": "backend/tests/test_builder.py",
                    "status": "modified",
                    "additions": 2,
                    "deletions": 0,
                    "test_case_count": 1,
                    "strongest_evidence_grade": "unknown",
                    "weakest_evidence_grade": "unknown",
                    "latest_command_status": "not_run",
                    "test_cases": [
                        {
                            "test_case_id": "tc_builder",
                            "file_id": "cf_test",
                            "path": "backend/tests/test_builder.py",
                            "name": "test_builder_emits_review_signals",
                            "status": "added",
                            "extraction_confidence": "certain",
                            "evidence_grade": "unknown",
                            "weakest_evidence_grade": "unknown",
                            "last_status": "unknown",
                            "covered_changes_preview": [],
                            "highest_risk_covered_hunk_id": None,
                            "intent_summary": {"text": "Verifies builder emits review signals.", "source": "rule_derived", "basis": []},
                        }
                    ],
                }
            ],
            "unknowns": [],
        },
    )

    response = client.get("/api/assessments/aca_ws_1/tests?repo_key=demo")

    assert response.status_code == 200
    assert response.json()["test_case_count"] == 1
    assert response.json()["files"][0]["path"] == "backend/tests/test_builder.py"


def test_get_assessment_tests_returns_empty_summary_when_management_data_is_absent(monkeypatch):
    monkeypatch.setattr(
        snapshot_store,
        "get_test_management_summary",
        lambda repo_key, snapshot_id, workspace_path=None: None,
    )
    monkeypatch.setattr(
        snapshot_store,
        "get_assessment_manifest",
        lambda repo_key, snapshot_id, workspace_path=None: {
            "assessment_id": f"aca_{snapshot_id}",
            "workspace_snapshot_id": snapshot_id,
            "repo_key": repo_key,
            "status": "ready",
            "summary": {},
            "file_list": [],
            "risk_signals_summary": [],
            "agent_sources": ["git_diff"],
            "review_progress": {},
        },
    )

    response = client.get("/api/assessments/aca_ws_1/tests?repo_key=demo")

    assert response.status_code == 200
    assert response.json() == {
        "assessment_id": "aca_ws_1",
        "repo_key": "demo",
        "changed_test_file_count": 0,
        "test_case_count": 0,
        "evidence_grade_counts": {},
        "command_status_counts": {},
        "files": [],
        "unknowns": [],
    }


def test_get_assessment_test_case_returns_detail(monkeypatch):
    monkeypatch.setattr(
        snapshot_store,
        "get_test_case_detail",
        lambda repo_key, snapshot_id, test_case_id, workspace_path=None: {
            "test_case": {
                "test_case_id": test_case_id,
                "file_id": "cf_test",
                "path": "backend/tests/test_builder.py",
                "name": "test_builder_emits_review_signals",
                "status": "added",
                "extraction_confidence": "certain",
                "evidence_grade": "unknown",
                "weakest_evidence_grade": "unknown",
                "last_status": "unknown",
                "covered_changes_preview": [],
                "highest_risk_covered_hunk_id": None,
                "intent_summary": {"text": "Verifies builder emits review signals.", "source": "rule_derived", "basis": []},
            },
            "diff_hunks": [],
            "full_body": [],
            "assertions": [],
            "covered_changes": [],
            "recommended_commands": [],
            "related_agent_claims": [],
            "unknowns": [],
        },
    )

    response = client.get("/api/assessments/aca_ws_1/tests/tc_builder?repo_key=demo")

    assert response.status_code == 200
    assert response.json()["test_case"]["test_case_id"] == "tc_builder"
    assert response.json()["test_case"]["name"] == "test_builder_emits_review_signals"


def test_analyze_test_result_runs_codex_agent_and_persists_analysis(monkeypatch):
    saved = {}
    detail = {
        "test_case": {
            "test_case_id": "tc_builder",
            "file_id": "cf_test",
            "path": "backend/tests/test_builder.py",
            "name": "test_builder_emits_review_signals",
            "status": "added",
            "extraction_confidence": "certain",
            "evidence_grade": "direct",
            "weakest_evidence_grade": "direct",
            "last_status": "passed",
            "covered_changes_preview": [],
            "highest_risk_covered_hunk_id": None,
            "intent_summary": {"text": "Verifies builder emits review signals.", "source": "rule_derived", "basis": []},
        },
        "diff_hunks": [],
        "full_body": [
            {"type": "context", "content": "def test_builder_emits_review_signals():"},
            {"type": "add", "content": '    payload = {"review_decision": "needs_tests"}'},
            {"type": "add", "content": '    assert payload["review_decision"] == "needs_tests"'},
        ],
        "assertions": [
            {"type": "add", "content": '    assert payload["review_decision"] == "needs_tests"'},
        ],
        "covered_scenarios": [
            {"title": "Scenario named by test: test builder emits review signals.", "source": "rule_derived", "basis": ["test_name"]},
        ],
        "covered_changes": [],
        "recommended_commands": [],
        "related_agent_claims": [],
        "unknowns": [],
        "test_results": [
            {
                "run_id": "run_builder",
                "source": "rerun",
                "command": "uv run pytest backend/tests/test_builder.py",
                "status": "passed",
                "exit_code": 0,
                "duration_ms": 25,
                "stdout": "1 passed",
                "stderr": "",
                "executed_cases": [
                    {
                        "node_id": "backend/tests/test_builder.py::test_builder_emits_review_signals",
                        "name": "test_builder_emits_review_signals",
                        "status": "passed",
                        "source": "collect_only",
                        "scenarios": [],
                        "test_data": [],
                    }
                ],
                "analysis": {},
                "captured_at": "2026-04-26T00:00:00Z",
                "evidence_grade": "direct",
            }
        ],
    }

    monkeypatch.setattr(
        snapshot_store,
        "get_test_case_detail",
        lambda repo_key, snapshot_id, test_case_id, workspace_path=None: saved.get("detail", detail),
    )
    monkeypatch.setattr(
        snapshot_store,
        "save_test_case_detail",
        lambda repo_key, snapshot_id, test_case_id, data, workspace_path=None: saved.update({"detail": data}),
    )

    class FakeCodexTestResultAnalysisAdapter:
        def __init__(self, workspace_path=None, language="zh-CN"):
            self.workspace_path = workspace_path
            self.language = language

        def analyze(self, *, detail, result):
            assert self.workspace_path == "/tmp/demo"
            assert self.language == "en-US"
            assert detail["test_case"]["name"] == "test_builder_emits_review_signals"
            assert result["run_id"] == "run_builder"
            return {
                "summary": "Codex Agent found the run covers the needs_tests review-decision branch.",
                "scenarios": [
                    {
                        "title": "The builder emits a needs_tests review decision.",
                        "source": "generated",
                        "basis": ["test_code", "runner_output"],
                    }
                ],
                "test_data": ["review_decision=needs_tests"],
                "coverage_gaps": ["Does not cover safe_to_commit decision output."],
                "source": "generated",
                "basis": ["codex_agent", "stored_run", "test_code"],
            }

    monkeypatch.setattr(
        "app.api.endpoints.assessments.LocalCodexTestResultAnalysisAdapter",
        FakeCodexTestResultAnalysisAdapter,
    )

    response = client.post(
        "/api/assessments/aca_ws_1/tests/tc_builder/results/run_builder/analyze?repo_key=demo&workspace_path=/tmp/demo&language=en-US"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == "Codex Agent found the run covers the needs_tests review-decision branch."
    assert payload["source"] == "generated"
    assert "codex_agent" in payload["basis"]
    assert payload["scenarios"][0]["title"] == "The builder emits a needs_tests review decision."
    assert saved["detail"]["test_results"][0]["analysis"]["summary"] == payload["summary"]


def test_analyze_test_result_falls_back_to_rule_analysis_when_codex_agent_fails(monkeypatch):
    saved = {}
    detail = {
        "test_case": {
            "test_case_id": "tc_builder",
            "file_id": "cf_test",
            "path": "backend/tests/test_builder.py",
            "name": "test_builder_emits_review_signals",
            "status": "added",
            "extraction_confidence": "certain",
            "evidence_grade": "direct",
            "weakest_evidence_grade": "direct",
            "last_status": "passed",
            "covered_changes_preview": [],
            "highest_risk_covered_hunk_id": None,
            "intent_summary": {"text": "Verifies builder emits review signals.", "source": "rule_derived", "basis": []},
        },
        "diff_hunks": [],
        "full_body": [
            {"type": "context", "content": "def test_builder_emits_review_signals():"},
            {"type": "add", "content": '    payload = {"review_decision": "needs_tests"}'},
        ],
        "assertions": [],
        "covered_scenarios": [
            {"title": "Scenario named by test: test builder emits review signals.", "source": "rule_derived", "basis": ["test_name"]},
        ],
        "covered_changes": [],
        "recommended_commands": [],
        "related_agent_claims": [],
        "unknowns": [],
        "test_results": [
            {
                "run_id": "run_builder",
                "source": "rerun",
                "command": "uv run pytest backend/tests/test_builder.py",
                "status": "passed",
                "exit_code": 0,
                "duration_ms": 25,
                "stdout": "1 passed",
                "stderr": "",
                "executed_cases": [
                    {
                        "node_id": "backend/tests/test_builder.py::test_builder_emits_review_signals",
                        "name": "test_builder_emits_review_signals",
                        "status": "passed",
                        "source": "collect_only",
                        "scenarios": [],
                        "test_data": [],
                    }
                ],
                "analysis": {},
                "captured_at": "2026-04-26T00:00:00Z",
                "evidence_grade": "direct",
            }
        ],
    }

    monkeypatch.setattr(
        snapshot_store,
        "get_test_case_detail",
        lambda repo_key, snapshot_id, test_case_id, workspace_path=None: saved.get("detail", detail),
    )
    monkeypatch.setattr(
        snapshot_store,
        "save_test_case_detail",
        lambda repo_key, snapshot_id, test_case_id, data, workspace_path=None: saved.update({"detail": data}),
    )

    class EmptyCodexTestResultAnalysisAdapter:
        def __init__(self, workspace_path=None, language="zh-CN"):
            pass

        def analyze(self, *, detail, result):
            return None

    monkeypatch.setattr(
        "app.api.endpoints.assessments.LocalCodexTestResultAnalysisAdapter",
        EmptyCodexTestResultAnalysisAdapter,
    )

    response = client.post(
        "/api/assessments/aca_ws_1/tests/tc_builder/results/run_builder/analyze?repo_key=demo"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "rule_derived"
    assert "rule_fallback" in payload["basis"]
    assert "Codex Agent analysis failed or returned invalid output." in payload["coverage_gaps"]


def test_trigger_agent_assessment_runs_codex_and_persists_result(monkeypatch):
    saved = {}
    detail = {
        "file": {
            "file_id": "cf_abc123",
            "path": "backend/app/main.py",
            "old_path": None,
            "status": "modified",
            "additions": 1,
            "deletions": 0,
            "risk_level": "low",
            "coverage_status": "unknown",
            "review_status": "unreviewed",
            "agent_sources": ["git_diff"],
            "diff_fingerprint": "sha256:abc",
        },
        "diff_hunks": [],
        "changed_symbols": [],
        "related_agent_records": [],
        "related_tests": [],
        "impact_facts": [],
        "file_assessment": {
            "why_changed": "No structured agent reason is available.",
            "impact_summary": "Review the diff.",
            "test_summary": "No direct test evidence was found.",
            "recommended_action": "Review this file manually.",
            "generated_by": "rules",
            "agent_status": "not_run",
            "agent_source": None,
            "confidence": "low",
            "evidence_refs": ["git_diff"],
            "unknowns": ["Codex agent assessment has not run."],
        },
        "review_state": {
            "review_status": "unreviewed",
            "diff_fingerprint": "sha256:abc",
            "reviewer": None,
            "reviewed_at": None,
            "notes": [],
        },
    }

    monkeypatch.setattr(
        snapshot_store,
        "get_assessment_file_detail",
        lambda repo_key, snapshot_id, file_id, workspace_path=None: saved.get("detail", detail),
    )
    monkeypatch.setattr(
        snapshot_store,
        "save_assessment_file_detail",
        lambda repo_key, snapshot_id, file_id, data, workspace_path=None: saved.update({"detail": data}),
    )

    class FakeCodexAdapter:
        def __init__(self, workspace_path=None, language="zh-CN"):
            self.workspace_path = workspace_path
            self.language = language

        def assess(self, payload):
            assert payload["file"]["path"] == "backend/app/main.py"
            assert self.language == "en-US"
            return {
                "why_changed": "Codex found this updates the API entrypoint.",
                "impact_summary": "The endpoint response contract changes.",
                "test_summary": "No direct test run evidence was provided.",
                "recommended_action": "Review the endpoint diff and add API coverage.",
                "confidence": "medium",
                "evidence_refs": ["git_diff"],
                "unknowns": ["No command log was captured."],
            }

    monkeypatch.setattr(
        "app.api.endpoints.assessments.LocalCodexFileAssessmentAdapter",
        FakeCodexAdapter,
    )

    response = client.post(
        "/api/assessments/aca_ws_1/files/cf_abc123/agent-assessment?repo_key=demo&workspace_path=/tmp/demo&language=en-US"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["file_assessment"]["agent_status"] == "accepted"
    assert payload["file_assessment"]["generated_by"] == "codex_agent"
    assert payload["file_assessment"]["agent_source"] == "codex"
    assert payload["file_assessment"]["why_changed"] == "Codex found this updates the API entrypoint."
    assert saved["detail"]["file_assessment"]["agent_status"] == "accepted"


def test_trigger_agent_assessment_marks_failed_when_codex_returns_no_result(monkeypatch):
    saved = {}
    detail = {
        "file": {
            "file_id": "cf_abc123",
            "path": "backend/app/main.py",
            "old_path": None,
            "status": "modified",
            "additions": 1,
            "deletions": 0,
            "risk_level": "low",
            "coverage_status": "unknown",
            "review_status": "unreviewed",
            "agent_sources": ["git_diff"],
            "diff_fingerprint": "sha256:abc",
        },
        "diff_hunks": [],
        "changed_symbols": [],
        "related_agent_records": [],
        "related_tests": [],
        "impact_facts": [],
        "file_assessment": {
            "why_changed": "No structured agent reason is available.",
            "impact_summary": "Review the diff.",
            "test_summary": "No direct test evidence was found.",
            "recommended_action": "Review this file manually.",
            "generated_by": "rules",
            "agent_status": "not_run",
            "agent_source": None,
            "confidence": "low",
            "evidence_refs": ["git_diff"],
            "unknowns": ["Codex agent assessment has not run."],
        },
        "review_state": {
            "review_status": "unreviewed",
            "diff_fingerprint": "sha256:abc",
            "reviewer": None,
            "reviewed_at": None,
            "notes": [],
        },
    }

    monkeypatch.setattr(
        snapshot_store,
        "get_assessment_file_detail",
        lambda repo_key, snapshot_id, file_id, workspace_path=None: saved.get("detail", detail),
    )
    monkeypatch.setattr(
        snapshot_store,
        "save_assessment_file_detail",
        lambda repo_key, snapshot_id, file_id, data, workspace_path=None: saved.update({"detail": data}),
    )

    class EmptyCodexAdapter:
        def __init__(self, workspace_path=None, language="zh-CN"):
            self.workspace_path = workspace_path
            self.language = language

        def assess(self, payload):
            assert self.language == "zh-CN"
            return None

    monkeypatch.setattr(
        "app.api.endpoints.assessments.LocalCodexFileAssessmentAdapter",
        EmptyCodexAdapter,
    )

    response = client.post("/api/assessments/aca_ws_1/files/cf_abc123/agent-assessment?repo_key=demo")

    assert response.status_code == 200
    payload = response.json()
    assert payload["file_assessment"]["agent_status"] == "failed"
    assert payload["file_assessment"]["generated_by"] == "rules"
    assert "Codex agent assessment failed or returned invalid output." in payload["file_assessment"]["unknowns"]
