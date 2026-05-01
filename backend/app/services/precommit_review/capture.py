from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewTargetFingerprint:
    review_target: str
    base_ref: str
    repo_head_sha: str
    target_tree_hash: str
    included_paths_hash: str
    include_untracked: bool

    @property
    def digest(self) -> str:
        return _digest(
            [
                self.review_target,
                self.base_ref,
                self.repo_head_sha,
                self.target_tree_hash,
                self.included_paths_hash,
                "include_untracked=1" if self.include_untracked else "include_untracked=0",
            ]
        )


@dataclass(frozen=True)
class WorkspaceStateFingerprint:
    repo_head_sha: str
    index_tree_hash: str | None
    working_tree_fingerprint: str
    untracked_fingerprint: str | None

    @property
    def digest(self) -> str:
        return _digest(
            [
                self.repo_head_sha,
                self.index_tree_hash or "",
                self.working_tree_fingerprint,
                self.untracked_fingerprint or "",
            ]
        )


@dataclass(frozen=True)
class PrecommitCapture:
    review_target: str
    base_ref: str
    diff_text: str
    changed_files: list[str]
    review_target_fingerprint: ReviewTargetFingerprint
    workspace_state_fingerprint: WorkspaceStateFingerprint

    @property
    def snapshot_id(self) -> str:
        return f"pr_{self.review_target_fingerprint.digest}"


class PrecommitCaptureService:
    def __init__(self, workspace_path: str, base_ref: str = "HEAD") -> None:
        self.workspace_path = workspace_path
        self.base_ref = base_ref

    def capture(self, review_target: str = "staged_only", include_untracked: bool = False) -> PrecommitCapture:
        if review_target != "staged_only":
            raise ValueError("Only staged_only review target is supported in MVP-0.")

        diff_text = self._git("diff", "--cached")
        changed_files = self._changed_staged_files()
        target = self._review_target_fingerprint(
            review_target=review_target,
            changed_files=changed_files,
            include_untracked=include_untracked,
        )
        workspace = self._workspace_state_fingerprint()
        return PrecommitCapture(
            review_target=review_target,
            base_ref=self.base_ref,
            diff_text=diff_text,
            changed_files=changed_files,
            review_target_fingerprint=target,
            workspace_state_fingerprint=workspace,
        )

    def is_stale(self, snapshot_target: ReviewTargetFingerprint) -> bool:
        current = self.capture(
            review_target=snapshot_target.review_target,
            include_untracked=snapshot_target.include_untracked,
        )
        return current.review_target_fingerprint.digest != snapshot_target.digest

    def workspace_changed_outside_target(self, snapshot_workspace: WorkspaceStateFingerprint) -> bool:
        return self._workspace_state_fingerprint().digest != snapshot_workspace.digest

    def _review_target_fingerprint(
        self,
        *,
        review_target: str,
        changed_files: list[str],
        include_untracked: bool,
    ) -> ReviewTargetFingerprint:
        return ReviewTargetFingerprint(
            review_target=review_target,
            base_ref=self.base_ref,
            repo_head_sha=self._repo_head_sha(),
            target_tree_hash=self._index_tree_hash(),
            included_paths_hash=_digest(sorted(changed_files)),
            include_untracked=include_untracked,
        )

    def _workspace_state_fingerprint(self) -> WorkspaceStateFingerprint:
        return WorkspaceStateFingerprint(
            repo_head_sha=self._repo_head_sha(),
            index_tree_hash=self._index_tree_hash(),
            working_tree_fingerprint=_digest(self._git("status", "--porcelain=v1").splitlines()),
            untracked_fingerprint=_digest(self._git("ls-files", "--others", "--exclude-standard").splitlines()),
        )

    def _changed_staged_files(self) -> list[str]:
        output = self._git("diff", "--cached", "--name-only")
        return sorted(line for line in output.splitlines() if line.strip())

    def _repo_head_sha(self) -> str:
        return self._git("rev-parse", self.base_ref)

    def _index_tree_hash(self) -> str:
        return self._git("write-tree")

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.workspace_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()


def _digest(parts: list[str]) -> str:
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:16]
