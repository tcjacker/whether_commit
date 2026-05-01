from __future__ import annotations

import hashlib


def _digest(parts: list[str]) -> str:
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:16]


def _normalize_patch(patch_text: str) -> str:
    return "\n".join(line.rstrip() for line in patch_text.strip().splitlines())


def file_id_for_review(review_target: str, path: str, file_diff_fingerprint: str) -> str:
    return f"file_{_digest([review_target, path, file_diff_fingerprint])}"


def hunk_id_for_review(file_id: str, hunk_fingerprint: str) -> str:
    return f"hunk_{_digest([file_id, _normalize_patch(hunk_fingerprint)])}"


def hunk_carryover_key_for_review(path: str, hunk: dict) -> str:
    added = _normalized_hunk_lines(hunk, "add")
    removed = _normalized_hunk_lines(hunk, "remove")
    return f"hunk_key_{_digest([path, *added, *removed])}"


def hunk_resource_id_for_review(snapshot_id: str, path: str, hunk_carryover_key: str, occurrence_index: int) -> str:
    return f"hunk_{_digest([snapshot_id, path, hunk_carryover_key, str(occurrence_index)])}"


def signal_id_for_review(
    signal_kind: str,
    target_type: str,
    target_stable_id: str,
    evidence_fingerprints: list[str],
    policy_rule_id: str,
) -> str:
    return f"sig_{_digest([signal_kind, target_type, target_stable_id, *sorted(evidence_fingerprints), policy_rule_id])}"


def _normalized_hunk_lines(hunk: dict, line_type: str) -> list[str]:
    lines = hunk.get("lines", [])
    return [
        " ".join(str(line.get("content", "")).strip().split())
        for line in lines
        if line.get("type") == line_type
    ]
