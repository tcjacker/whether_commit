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
