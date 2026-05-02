from __future__ import annotations

import hashlib
import os
import subprocess
from typing import List

from app.schemas.job import WorkspaceSnapshotState


class WorkspaceSnapshotService:
    """
    Capture the current Git working tree state and normalize it into a stable snapshot object.
    """

    def capture(
        self,
        repo_key: str,
        workspace_path: str,
        base_commit_sha: str = "HEAD",
        include_untracked: bool = True,
    ) -> WorkspaceSnapshotState:
        if not self.is_git_workspace(workspace_path):
            raise RuntimeError(f"WORKSPACE_NOT_A_GIT_REPO: {workspace_path}")

        base_commit_sha = self.resolve_base_commit(workspace_path, base_commit_sha)
        status_lines = self._change_status_lines(
            workspace_path,
            base_commit_sha=base_commit_sha,
            include_untracked=include_untracked,
        )
        changed_files = self._parse_changed_files(status_lines)
        has_pending_changes = bool(changed_files)
        fingerprint = self._build_fingerprint(
            repo_key=repo_key,
            base_commit_sha=base_commit_sha,
            status_lines=status_lines,
            changed_files=changed_files,
            include_untracked=include_untracked,
        )
        workspace_snapshot_id = f"ws_{fingerprint}" if has_pending_changes else f"ws_clean_{fingerprint}"

        return WorkspaceSnapshotState(
            repo_key=repo_key,
            base_commit_sha=base_commit_sha,
            workspace_snapshot_id=workspace_snapshot_id,
            has_pending_changes=has_pending_changes,
            changed_files=changed_files,
            status_lines=status_lines,
            fingerprint=fingerprint,
        )

    def resolve_base_commit(self, workspace_path: str, base_commit_sha: str) -> str:
        if base_commit_sha != "AUTO_MERGE_BASE":
            return base_commit_sha
        for candidate in ("main", "origin/main", "master", "origin/master", "dev", "origin/dev"):
            try:
                result = subprocess.run(
                    ["git", "merge-base", "HEAD", candidate],
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
            value = result.stdout.strip()
            if value:
                return value
        return "HEAD"

    def is_git_workspace(self, workspace_path: str) -> bool:
        if not os.path.isdir(workspace_path):
            return False

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

        return result.stdout.strip() == "true"

    def _git_status_lines(self, workspace_path: str, include_untracked: bool) -> List[str]:
        cmd = ["git", "status", "--porcelain=v1"]
        cmd.append("--untracked-files=all" if include_untracked else "--untracked-files=no")
        result = subprocess.run(
            cmd,
            cwd=workspace_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return [line.rstrip("\n") for line in result.stdout.splitlines() if line.rstrip("\n")]

    def _git_name_status_lines(self, workspace_path: str, base_commit_sha: str) -> List[str]:
        result = subprocess.run(
            ["git", "diff", "--name-status", base_commit_sha, "HEAD"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return [line.rstrip("\n") for line in result.stdout.splitlines() if line.rstrip("\n")]

    def _change_status_lines(self, workspace_path: str, base_commit_sha: str, include_untracked: bool) -> List[str]:
        if base_commit_sha == "HEAD":
            return self._git_status_lines(workspace_path, include_untracked=include_untracked)

        status_lines = [self._name_status_to_porcelain(line) for line in self._git_name_status_lines(workspace_path, base_commit_sha)]
        existing_paths = set(self._parse_changed_files(status_lines))
        for line in self._git_status_lines(workspace_path, include_untracked=include_untracked):
            changed_files = self._parse_changed_files([line])
            if changed_files and changed_files[0] not in existing_paths:
                status_lines.append(line)
        return [line for line in status_lines if line.strip()]

    def _name_status_to_porcelain(self, line: str) -> str:
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1] if parts else ""
        marker = status[:1]
        if marker == "M":
            return f" M {path}"
        if marker == "A":
            return f" A {path}"
        if marker == "D":
            return f" D {path}"
        if marker == "R":
            return f" R {path}"
        return f" M {path}"

    def _parse_changed_files(self, status_lines: List[str]) -> List[str]:
        changed_files: List[str] = []
        for line in status_lines:
            if len(line) < 4:
                continue
            path = line[3:]
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            changed_files.append(path)
        return sorted(set(changed_files))

    def _build_fingerprint(
        self,
        repo_key: str,
        base_commit_sha: str,
        status_lines: List[str],
        changed_files: List[str],
        include_untracked: bool,
    ) -> str:
        digest_input = "\n".join(
            [
                repo_key,
                base_commit_sha,
                "include_untracked=1" if include_untracked else "include_untracked=0",
                *sorted(status_lines),
                *sorted(changed_files),
            ]
        )
        return hashlib.sha1(digest_input.encode("utf-8")).hexdigest()[:12]
