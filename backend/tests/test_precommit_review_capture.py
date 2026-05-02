import subprocess
from pathlib import Path

from app.services.precommit_review.capture import PrecommitCaptureService


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, check=True, text=True, capture_output=True)
    return result.stdout.strip()


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    run_git(repo, "init")
    run_git(repo, "config", "user.email", "test@example.com")
    run_git(repo, "config", "user.name", "Test User")
    (repo / "app.py").write_text("value = 1\n", encoding="utf-8")
    (repo / "notes.txt").write_text("notes\n", encoding="utf-8")
    run_git(repo, "add", ".")
    run_git(repo, "commit", "-m", "initial")
    return repo


def test_staged_only_capture_ignores_unrelated_unstaged_change_for_target_stale(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "app.py").write_text("value = 2\n", encoding="utf-8")
    run_git(repo, "add", "app.py")

    service = PrecommitCaptureService(str(repo))
    capture = service.capture(review_target="staged_only")

    (repo / "notes.txt").write_text("local notes\n", encoding="utf-8")

    assert service.is_stale(capture.review_target_fingerprint) is False
    assert service.workspace_changed_outside_target(capture.workspace_state_fingerprint) is True


def test_tool_owned_precommit_review_storage_does_not_count_as_outside_target_change(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "app.py").write_text("value = 2\n", encoding="utf-8")
    run_git(repo, "add", "app.py")

    service = PrecommitCaptureService(str(repo))
    capture = service.capture(review_target="staged_only")

    raw_output_dir = repo / ".precommit-review" / "raw" / "command-output"
    raw_output_dir.mkdir(parents=True)
    (raw_output_dir / "run_1.txt").write_text("test output\n", encoding="utf-8")
    (repo / ".precommit-review" / "verification.sqlite").write_text("local state\n", encoding="utf-8")

    assert service.is_stale(capture.review_target_fingerprint) is False
    assert service.workspace_changed_outside_target(capture.workspace_state_fingerprint) is False

    (repo / "notes.txt").write_text("local notes\n", encoding="utf-8")

    assert service.workspace_changed_outside_target(capture.workspace_state_fingerprint) is True


def test_staged_only_capture_becomes_stale_when_staged_content_changes(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "app.py").write_text("value = 2\n", encoding="utf-8")
    run_git(repo, "add", "app.py")

    service = PrecommitCaptureService(str(repo))
    capture = service.capture(review_target="staged_only")

    (repo / "app.py").write_text("value = 3\n", encoding="utf-8")
    run_git(repo, "add", "app.py")

    assert service.is_stale(capture.review_target_fingerprint) is True
