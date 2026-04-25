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
