import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, check=True, text=True, capture_output=True)
    return result.stdout.strip()


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    run_git(repo, "init")
    run_git(repo, "config", "user.email", "test@example.com")
    run_git(repo, "config", "user.name", "Test User")
    (repo / "backend").mkdir()
    (repo / "backend" / "schema.py").write_text("value = 1\n", encoding="utf-8")
    run_git(repo, "add", ".")
    run_git(repo, "commit", "-m", "initial")
    return repo


def test_precommit_review_rebuild_and_queue(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "backend" / "schema.py").write_text("value = 2\n", encoding="utf-8")
    run_git(repo, "add", "backend/schema.py")

    response = client.post("/api/precommit-review/rebuild", json={"workspace_path": str(repo)})

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "needs_review"

    queue_response = client.get(f"/api/precommit-review/queue?workspace_path={repo}")

    assert queue_response.status_code == 200
    assert queue_response.json()["decision"] == "needs_review"
    assert queue_response.json()["queue"]


def test_precommit_review_signal_state_update_changes_decision(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "backend" / "schema.py").write_text("value = 2\n", encoding="utf-8")
    run_git(repo, "add", "backend/schema.py")
    snapshot = client.post("/api/precommit-review/rebuild", json={"workspace_path": str(repo)}).json()
    signal_id = snapshot["signals"][0]["signal_id"]

    response = client.post(
        f"/api/precommit-review/signals/{signal_id}/state",
        json={"workspace_path": str(repo), "status": "reviewed"},
    )

    assert response.status_code == 200
    assert response.json()["decision"] == "no_known_blockers"
    assert response.json()["hunks"][0]["review_status"] == "reviewed"
    assert response.json()["files"][0]["review_state_summary"] == "reviewed"


def test_precommit_review_hunk_state_update_changes_decision(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "backend" / "schema.py").write_text("value = 2\n", encoding="utf-8")
    run_git(repo, "add", "backend/schema.py")
    snapshot = client.post("/api/precommit-review/rebuild", json={"workspace_path": str(repo)}).json()
    hunk_id = snapshot["hunks"][0]["hunk_id"]

    response = client.post(
        f"/api/precommit-review/hunks/{hunk_id}/state",
        json={"workspace_path": str(repo), "status": "reviewed"},
    )

    assert response.status_code == 200
    assert response.json()["decision"] == "no_known_blockers"


def test_precommit_review_file_state_update_changes_decision(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "backend" / "schema.py").write_text("value = 2\n", encoding="utf-8")
    run_git(repo, "add", "backend/schema.py")
    snapshot = client.post("/api/precommit-review/rebuild", json={"workspace_path": str(repo)}).json()
    file_id = snapshot["files"][0]["file_id"]

    response = client.post(
        f"/api/precommit-review/files/{file_id}/state",
        json={"workspace_path": str(repo), "status": "reviewed"},
    )

    assert response.status_code == 200
    assert response.json()["decision"] == "no_known_blockers"


def test_precommit_review_queue_reports_stale_after_staged_change(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "backend" / "schema.py").write_text("value = 2\n", encoding="utf-8")
    run_git(repo, "add", "backend/schema.py")
    client.post("/api/precommit-review/rebuild", json={"workspace_path": str(repo)})

    (repo / "backend" / "schema.py").write_text("value = 3\n", encoding="utf-8")
    run_git(repo, "add", "backend/schema.py")
    response = client.get(f"/api/precommit-review/queue?workspace_path={repo}")

    assert response.status_code == 200
    assert response.json()["stale"] is True
    assert response.json()["decision"] == "not_recommended"


def test_snapshots_current_reports_workspace_changed_outside_staged_target(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "backend" / "schema.py").write_text("value = 2\n", encoding="utf-8")
    run_git(repo, "add", "backend/schema.py")
    client.post("/api/precommit-review/rebuild", json={"workspace_path": str(repo)})

    (repo / "backend" / "local_debug.py").write_text("debug = True\n", encoding="utf-8")
    response = client.get(f"/api/snapshots/current?workspace_path={repo}")

    assert response.status_code == 200
    assert response.json()["review_target"] == "staged_only"
    assert response.json()["stale"] is False
    assert response.json()["workspace_changed_outside_target"] is True
    assert response.json()["decision"] == "needs_review"


def test_precommit_verification_run_endpoint_records_failed_command(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "backend" / "schema.py").write_text("value = 2\n", encoding="utf-8")
    run_git(repo, "add", "backend/schema.py")
    snapshot = client.post("/api/precommit-review/rebuild", json={"workspace_path": str(repo)}).json()

    response = client.post(
        "/api/verification/run",
        json={
            "workspace_path": str(repo),
            "snapshot_id": snapshot["snapshot_id"],
            "command": f"{sys.executable} -c 'import sys; sys.exit(1)'",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "failed"

    run_id = response.json()["run_id"]
    poll = client.get(f"/api/verification/runs/{run_id}?workspace_path={repo}")

    assert poll.status_code == 200
    assert poll.json()["exit_code"] == 1
