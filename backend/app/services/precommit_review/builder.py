from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.schemas.assessment import ReviewSignal
from app.services.agentic_change_assessment.diff_parser import parse_unified_diff_hunks
from app.services.precommit_review.capture import PrecommitCaptureService
from app.services.precommit_review.fingerprints import file_id_for_review, hunk_id_for_review, signal_id_for_review
from app.services.precommit_review.policy import decide_review
from app.services.precommit_review.review_state import ReviewStateStore
from app.services.precommit_review.risk import score_file_risk


class PrecommitReviewBuilder:
    def __init__(self, workspace_path: str) -> None:
        self.workspace_path = workspace_path
        self.capture_service = PrecommitCaptureService(workspace_path)
        self.state_store = ReviewStateStore(workspace_path)

    def rebuild(self) -> dict[str, Any]:
        capture = self.capture_service.capture(review_target="staged_only")
        snapshot = self._build_snapshot(capture)
        self._save_snapshot(snapshot)
        return snapshot

    def current(self) -> dict[str, Any]:
        latest = self._latest_snapshot()
        if latest is None:
            return self.rebuild()
        snapshot = self._read_snapshot(latest)
        snapshot["stale"] = self.capture_service.is_stale(_target_from_snapshot(snapshot))
        snapshot["workspace_changed_outside_target"] = self.capture_service.workspace_changed_outside_target(
            _workspace_from_snapshot(snapshot)
        )
        snapshot["decision"] = decide_review(
            [ReviewSignal.model_validate(signal) for signal in snapshot.get("signals", [])],
            snapshot_is_stale=snapshot["stale"],
        )
        return snapshot

    def update_signal_state(self, signal_id: str, status: str) -> dict[str, Any]:
        self.state_store.update_signal_state(signal_id, status)
        return self.rebuild()

    def _build_snapshot(self, capture) -> dict[str, Any]:
        files = []
        hunks = []
        signals: list[ReviewSignal] = []

        if not capture.changed_files:
            snapshot = self._base_snapshot(capture)
            snapshot.update(
                {
                    "decision": "no_known_blockers",
                    "summary": {"message": "No pending staged changes.", "changed_file_count": 0},
                    "files": [],
                    "hunks": [],
                    "signals": [],
                    "queue": [],
                }
            )
            return snapshot

        diff_by_file = _split_diff_by_file(capture.diff_text)
        for path in capture.changed_files:
            file_diff = diff_by_file.get(path, "")
            file_id = file_id_for_review(capture.review_target, path, file_diff)
            file_hunks = parse_unified_diff_hunks(file_diff)
            additions, deletions = _line_counts(file_diff)
            risk = score_file_risk(path, additions=additions, deletions=deletions, has_test_evidence=False)
            file_record = {
                "file_id": file_id,
                "path": path,
                "additions": additions,
                "deletions": deletions,
                "risk": {"score": risk.score, "band": risk.band, "reasons": [reason.__dict__ for reason in risk.reasons]},
            }
            files.append(file_record)
            for raw_hunk in file_hunks:
                stable_hunk_id = hunk_id_for_review(file_id, raw_hunk["hunk_fingerprint"])
                hunk = {**raw_hunk, "hunk_id": stable_hunk_id, "file_id": file_id, "path": path}
                hunks.append(hunk)
                if risk.band in {"medium", "high"}:
                    signal = self._hunk_signal(file_id=file_id, hunk_id=stable_hunk_id, path=path, risk_band=risk.band)
                    stored_status = self.state_store.get_signal_status(signal.signal_id)
                    hunk_status = self.state_store.get_hunk_status(stable_hunk_id)
                    file_status = self.state_store.get_file_status(file_id)
                    if stored_status:
                        signal.status = stored_status
                    elif hunk_status:
                        signal.status = hunk_status
                    elif file_status:
                        signal.status = file_status
                    signals.append(signal)

        decision = decide_review(signals, snapshot_is_stale=False)
        snapshot = self._base_snapshot(capture)
        snapshot.update(
            {
                "decision": decision,
                "summary": {"message": "Pending staged changes require review.", "changed_file_count": len(files)},
                "files": files,
                "hunks": hunks,
                "signals": [signal.model_dump() for signal in signals],
                "queue": self._queue(files=files, hunks=hunks, signals=signals),
            }
        )
        return snapshot

    def _hunk_signal(self, *, file_id: str, hunk_id: str, path: str, risk_band: str) -> ReviewSignal:
        signal_id = signal_id_for_review(
            "unreviewed_high_risk_hunk",
            "hunk",
            hunk_id,
            [],
            "high_risk_hunk_unreviewed",
        )
        return ReviewSignal(
            signal_id=signal_id,
            kind="unreviewed_high_risk_hunk",
            target_type="hunk",
            target_id=hunk_id,
            severity="review",
            status="open",
            decision_impact="prevents_no_known_blockers",
            evidence_ids=[],
            policy_rule_id="high_risk_hunk_unreviewed",
            message=f"{path} has a {risk_band}-risk staged hunk that needs review.",
        )

    def _queue(self, *, files: list[dict[str, Any]], hunks: list[dict[str, Any]], signals: list[ReviewSignal]) -> list[dict[str, Any]]:
        queue = [
            {
                "queue_id": signal.signal_id,
                "item_type": "signal",
                "target_id": signal.target_id,
                "status": signal.status,
                "message": signal.message,
                "priority": 100 if signal.severity == "blocker" else 50,
            }
            for signal in signals
            if signal.status == "open"
        ]
        return sorted(queue, key=lambda item: (-item["priority"], item["queue_id"]))

    def _base_snapshot(self, capture) -> dict[str, Any]:
        return {
            "snapshot_id": capture.snapshot_id,
            "review_target": capture.review_target,
            "review_target_fingerprint": capture.review_target_fingerprint.__dict__,
            "workspace_state_fingerprint": capture.workspace_state_fingerprint.__dict__,
            "stale": False,
            "workspace_changed_outside_target": False,
        }

    def _save_snapshot(self, snapshot: dict[str, Any]) -> None:
        snapshot_dir = Path(self.workspace_path) / ".precommit-review" / "snapshots" / snapshot["snapshot_id"]
        os.makedirs(snapshot_dir, exist_ok=True)
        (snapshot_dir / "analysis.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        index_path = Path(self.workspace_path) / ".precommit-review" / "index.json"
        index_path.write_text(json.dumps({"latest_snapshot_id": snapshot["snapshot_id"]}), encoding="utf-8")

    def _latest_snapshot(self) -> str | None:
        index_path = Path(self.workspace_path) / ".precommit-review" / "index.json"
        if not index_path.exists():
            return None
        return json.loads(index_path.read_text(encoding="utf-8")).get("latest_snapshot_id")

    def _read_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        path = Path(self.workspace_path) / ".precommit-review" / "snapshots" / snapshot_id / "analysis.json"
        return json.loads(path.read_text(encoding="utf-8"))


def _split_diff_by_file(diff_text: str) -> dict[str, str]:
    by_file: dict[str, list[str]] = {}
    current_path: str | None = None
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            current_path = parts[3][2:] if len(parts) >= 4 and parts[3].startswith("b/") else None
            if current_path:
                by_file[current_path] = [line]
            continue
        if current_path:
            by_file[current_path].append(line)
    return {path: "\n".join(lines) + "\n" for path, lines in by_file.items()}


def _line_counts(diff_text: str) -> tuple[int, int]:
    additions = 0
    deletions = 0
    for line in diff_text.splitlines():
        if line.startswith(("+++", "---")):
            continue
        if line.startswith("+"):
            additions += 1
        elif line.startswith("-"):
            deletions += 1
    return additions, deletions


def _target_from_snapshot(snapshot: dict[str, Any]):
    from app.services.precommit_review.capture import ReviewTargetFingerprint

    return ReviewTargetFingerprint(**snapshot["review_target_fingerprint"])


def _workspace_from_snapshot(snapshot: dict[str, Any]):
    from app.services.precommit_review.capture import WorkspaceStateFingerprint

    return WorkspaceStateFingerprint(**snapshot["workspace_state_fingerprint"])
