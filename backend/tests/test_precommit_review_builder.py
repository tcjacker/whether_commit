import subprocess
from pathlib import Path

from app.services.precommit_review.builder import PrecommitReviewBuilder
from app.services.precommit_review.review_state import ReviewStateStore


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
    (repo / "backend" / "app.py").write_text("value = 1\n", encoding="utf-8")
    run_git(repo, "add", ".")
    run_git(repo, "commit", "-m", "initial")
    return repo


def test_builder_reports_no_pending_staged_changes(tmp_path):
    repo = make_repo(tmp_path)
    snapshot = PrecommitReviewBuilder(str(repo)).rebuild()

    assert snapshot["decision"] == "no_known_blockers"
    assert snapshot["summary"]["message"] == "No pending staged changes."
    assert snapshot["queue"] == []


def test_builder_creates_queue_and_needs_review_for_staged_change(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "backend" / "schema.py").write_text("value = 2\n", encoding="utf-8")
    run_git(repo, "add", "backend/schema.py")

    snapshot = PrecommitReviewBuilder(str(repo)).rebuild()

    assert snapshot["decision"] == "needs_review"
    assert snapshot["files"][0]["path"] == "backend/schema.py"
    assert snapshot["queue"][0]["item_type"] in {"signal", "hunk", "file"}
    assert snapshot["signals"][0]["status"] == "open"


def test_builder_uses_review_state_to_clear_review_signal(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "backend" / "schema.py").write_text("value = 2\n", encoding="utf-8")
    run_git(repo, "add", "backend/schema.py")

    builder = PrecommitReviewBuilder(str(repo))
    snapshot = builder.rebuild()
    signal_id = snapshot["signals"][0]["signal_id"]

    ReviewStateStore(str(repo)).update_signal_state(signal_id, "reviewed")
    updated = builder.rebuild()

    assert updated["decision"] == "no_known_blockers"
    assert updated["signals"][0]["status"] == "reviewed"


def test_builder_uses_hunk_review_state_to_clear_review_signal(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "backend" / "schema.py").write_text("value = 2\n", encoding="utf-8")
    run_git(repo, "add", "backend/schema.py")

    builder = PrecommitReviewBuilder(str(repo))
    snapshot = builder.rebuild()
    hunk_key = snapshot["hunks"][0]["hunk_carryover_key"]

    ReviewStateStore(str(repo)).update_hunk_state(hunk_key, "reviewed")
    updated = builder.rebuild()

    assert updated["decision"] == "no_known_blockers"
    assert updated["signals"][0]["status"] == "reviewed"


def test_builder_uses_file_review_state_to_clear_review_signal(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "backend" / "schema.py").write_text("value = 2\n", encoding="utf-8")
    run_git(repo, "add", "backend/schema.py")

    builder = PrecommitReviewBuilder(str(repo))
    snapshot = builder.rebuild()
    file_id = snapshot["files"][0]["file_id"]

    ReviewStateStore(str(repo)).update_file_state(file_id, "reviewed")
    updated = builder.rebuild()

    assert updated["decision"] == "no_known_blockers"
    assert updated["signals"][0]["status"] == "reviewed"


def test_builder_current_marks_snapshot_stale_when_staged_content_changes(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "backend" / "schema.py").write_text("value = 2\n", encoding="utf-8")
    run_git(repo, "add", "backend/schema.py")

    builder = PrecommitReviewBuilder(str(repo))
    builder.rebuild()

    (repo / "backend" / "schema.py").write_text("value = 3\n", encoding="utf-8")
    run_git(repo, "add", "backend/schema.py")
    current = builder.current()

    assert current["stale"] is True
    assert current["decision"] == "not_recommended"


def test_rebuild_preserves_review_state_only_for_unchanged_hunk(tmp_path):
    repo = make_repo(tmp_path)
    original = "\n".join(
        [
            "alpha = 1",
            "alpha_context = 1",
            *[f"spacer_{index} = {index}" for index in range(20)],
            "beta = 1",
            "beta_context = 1",
            "",
        ]
    )
    (repo / "backend" / "schema.py").write_text(original, encoding="utf-8")
    run_git(repo, "add", "backend/schema.py")
    run_git(repo, "commit", "-m", "add schema")

    changed = original.replace("alpha = 1", "alpha = 2").replace("beta = 1", "beta = 2")
    (repo / "backend" / "schema.py").write_text(changed, encoding="utf-8")
    run_git(repo, "add", "backend/schema.py")

    builder = PrecommitReviewBuilder(str(repo))
    snapshot = builder.rebuild()
    assert len(snapshot["hunks"]) == 2
    for hunk in snapshot["hunks"]:
        ReviewStateStore(str(repo)).update_hunk_state(hunk["hunk_carryover_key"], "reviewed")

    changed_again = changed.replace("alpha = 2", "alpha = 3")
    (repo / "backend" / "schema.py").write_text(changed_again, encoding="utf-8")
    run_git(repo, "add", "backend/schema.py")

    rebuilt = builder.rebuild()
    statuses_by_line = {
        next(line["content"] for line in hunk["lines"] if line["type"] == "add"): signal["status"]
        for hunk in rebuilt["hunks"]
        for signal in rebuilt["signals"]
        if signal["target_id"] == hunk["hunk_id"]
    }
    hunk_statuses_by_line = {
        next(line["content"] for line in hunk["lines"] if line["type"] == "add"): hunk["review_status"]
        for hunk in rebuilt["hunks"]
    }

    assert statuses_by_line["beta = 2"] == "reviewed"
    assert statuses_by_line["alpha = 3"] == "open"
    assert hunk_statuses_by_line["beta = 2"] == "reviewed"
    assert hunk_statuses_by_line["alpha = 3"] == "open"
    assert rebuilt["summary"]["review_state"] == "partially_reviewed"
    assert rebuilt["files"][0]["review_state_summary"] == "partially_reviewed"
