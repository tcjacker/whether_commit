import subprocess
import sys
from pathlib import Path

from app.services.precommit_review.builder import PrecommitReviewBuilder
from app.services.precommit_review.verification import VerificationRunner


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
    (repo / "notes.txt").write_text("notes\n", encoding="utf-8")
    run_git(repo, "add", ".")
    run_git(repo, "commit", "-m", "initial")
    return repo


def test_failed_tool_launched_verification_forces_not_recommended(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "backend" / "schema.py").write_text("value = 2\n", encoding="utf-8")
    run_git(repo, "add", "backend/schema.py")
    snapshot = PrecommitReviewBuilder(str(repo)).rebuild()

    run = VerificationRunner(str(repo)).run(snapshot["snapshot_id"], f"{sys.executable} -c 'import sys; sys.exit(1)'")
    current = PrecommitReviewBuilder(str(repo)).current()

    assert run["status"] == "failed"
    assert run["exit_code"] == 1
    assert current["decision"] == "not_recommended"
    assert any(signal["policy_rule_id"] == "failed_tool_launched_verification" for signal in current["signals"])


def test_working_tree_verification_misaligned_with_staged_target_cannot_clear_high_risk(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "backend" / "schema.py").write_text("value = 2\n", encoding="utf-8")
    run_git(repo, "add", "backend/schema.py")
    snapshot = PrecommitReviewBuilder(str(repo)).rebuild()
    (repo / "notes.txt").write_text("local notes\n", encoding="utf-8")

    run = VerificationRunner(str(repo)).run(snapshot["snapshot_id"], f"{sys.executable} -c 'import sys; sys.exit(0)'")
    current = PrecommitReviewBuilder(str(repo)).current()

    assert run["status"] == "passed"
    assert run["target_aligned"] is False
    assert run["display_status"] == "executed_but_misaligned"
    assert current["decision"] == "needs_review"
    assert any(signal["policy_rule_id"] == "target_misaligned_verification" for signal in current["signals"])
