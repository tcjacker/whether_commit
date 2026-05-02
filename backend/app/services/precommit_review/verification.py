from __future__ import annotations

import json
import os
import shlex
import sqlite3
import subprocess
import uuid
from pathlib import Path
from typing import Any

from app.services.precommit_review.capture import PrecommitCaptureService


class VerificationRunner:
    def __init__(self, workspace_path: str, *, ensure: bool = True) -> None:
        self.workspace_path = workspace_path
        self.root = Path(workspace_path) / ".precommit-review"
        self.db_path = self.root / "verification.sqlite"
        if ensure:
            os.makedirs(self.root / "raw" / "command-output", exist_ok=True)
            self._ensure_schema()

    def run(self, snapshot_id: str, command: str) -> dict[str, Any]:
        snapshot = self._read_snapshot(snapshot_id)
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        raw_output_ref = f"raw/command-output/{run_id}.txt"
        result = subprocess.run(
            shlex.split(command),
            cwd=self.workspace_path,
            capture_output=True,
            text=True,
            check=False,
        )
        (self.root / raw_output_ref).write_text((result.stdout or "") + (result.stderr or ""), encoding="utf-8")
        target_aligned = self._target_aligned(snapshot)
        run = {
            "run_id": run_id,
            "snapshot_id": snapshot_id,
            "command": command,
            "exit_code": result.returncode,
            "status": "passed" if result.returncode == 0 else "failed",
            "execution_mode": "working_tree",
            "review_target_fingerprint": snapshot["review_target_fingerprint"]["digest"],
            "execution_tree_fingerprint": PrecommitCaptureService(self.workspace_path)
            .capture(review_target="staged_only")
            .workspace_state_fingerprint.digest,
            "target_aligned": target_aligned,
            "display_status": "executed" if target_aligned else "executed_but_misaligned",
            "raw_output_ref": raw_output_ref,
        }
        self._save_run(run)
        return run

    def get(self, run_id: str) -> dict[str, Any] | None:
        if not self.db_path.exists():
            return None
        with self._connect() as conn:
            row = conn.execute("select payload from verification_runs where run_id = ?", (run_id,)).fetchone()
            return json.loads(row[0]) if row else None

    def runs_for_snapshot(self, snapshot_id: str) -> list[dict[str, Any]]:
        if not self.db_path.exists():
            return []
        with self._connect() as conn:
            rows = conn.execute(
                "select payload from verification_runs where snapshot_id = ? order by rowid",
                (snapshot_id,),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def _target_aligned(self, snapshot: dict[str, Any]) -> bool:
        service = PrecommitCaptureService(self.workspace_path)
        if service.is_stale(_target_from_snapshot(snapshot)):
            return False
        return not service.workspace_changed_outside_target(_workspace_from_snapshot(snapshot))

    def _read_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        path = self.root / "snapshots" / snapshot_id / "analysis.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_run(self, run: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                insert into verification_runs(run_id, snapshot_id, payload)
                values(?, ?, ?)
                """,
                (run["run_id"], run["snapshot_id"], json.dumps(run, ensure_ascii=False)),
            )

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists verification_runs (
                    run_id text primary key,
                    snapshot_id text not null,
                    payload text not null
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)


def _target_from_snapshot(snapshot: dict[str, Any]):
    from app.services.precommit_review.capture import ReviewTargetFingerprint

    payload = {key: value for key, value in snapshot["review_target_fingerprint"].items() if key != "digest"}
    return ReviewTargetFingerprint(**payload)


def _workspace_from_snapshot(snapshot: dict[str, Any]):
    from app.services.precommit_review.capture import WorkspaceStateFingerprint

    payload = {key: value for key, value in snapshot["workspace_state_fingerprint"].items() if key != "digest"}
    return WorkspaceStateFingerprint(**payload)
