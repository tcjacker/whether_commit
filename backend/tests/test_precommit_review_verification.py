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

    command = f"{sys.executable} -c 'import sys; sys.exit(1)'"
    run = VerificationRunner(str(repo)).run(snapshot["snapshot_id"], command)
    current = PrecommitReviewBuilder(str(repo)).current()

    assert run["status"] == "failed"
    assert run["exit_code"] == 1
    assert run["command"] == command
    assert current["decision"] == "not_recommended"
    signal = next(signal for signal in current["signals"] if signal["policy_rule_id"] == "failed_tool_launched_verification")
    assert "Verification command failed." in signal["message"]
    assert command not in signal["message"]
    assert sys.executable not in signal["message"]


def test_tool_owned_storage_does_not_make_clean_verification_misaligned(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "backend" / "schema.py").write_text("value = 2\n", encoding="utf-8")
    run_git(repo, "add", "backend/schema.py")
    snapshot = PrecommitReviewBuilder(str(repo)).rebuild()

    command = f"{sys.executable} -c 'import sys; sys.exit(0)'"
    run = VerificationRunner(str(repo)).run(snapshot["snapshot_id"], command)
    current = PrecommitReviewBuilder(str(repo)).current()

    assert run["status"] == "passed"
    assert run["target_aligned"] is True
    assert run["display_status"] == "executed"
    signal = next(signal for signal in current["signals"] if signal["policy_rule_id"] == "passed_tool_launched_verification")
    assert "Verification command passed." in signal["message"]
    assert command not in signal["message"]
    assert sys.executable not in signal["message"]


def test_working_tree_verification_misaligned_with_staged_target_cannot_clear_high_risk(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "backend" / "schema.py").write_text("value = 2\n", encoding="utf-8")
    run_git(repo, "add", "backend/schema.py")
    snapshot = PrecommitReviewBuilder(str(repo)).rebuild()
    (repo / "notes.txt").write_text("local notes\n", encoding="utf-8")

    command = f"{sys.executable} -c 'import sys; sys.exit(0)'"
    run = VerificationRunner(str(repo)).run(snapshot["snapshot_id"], command)
    current = PrecommitReviewBuilder(str(repo)).current()

    assert run["status"] == "passed"
    assert run["target_aligned"] is False
    assert run["display_status"] == "executed_but_misaligned"
    assert current["decision"] == "needs_review"
    signal = next(signal for signal in current["signals"] if signal["policy_rule_id"] == "target_misaligned_verification")
    assert "Verification command was executed but target-misaligned." in signal["message"]
    assert command not in signal["message"]
    assert sys.executable not in signal["message"]
