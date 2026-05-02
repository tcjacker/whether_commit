from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RiskReason:
    reason_id: str
    label: str
    weight: int
    evidence_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RiskScore:
    score: int
    band: str
    reasons: list[RiskReason]


def score_file_risk(
    path: str,
    *,
    additions: int,
    deletions: int,
    has_test_evidence: bool,
    is_untracked: bool = False,
) -> RiskScore:
    reasons: list[RiskReason] = []

    def add(reason_id: str, label: str, weight: int) -> None:
        reasons.append(RiskReason(reason_id=reason_id, label=label, weight=weight))

    lowered = path.lower()
    if any(part in lowered for part in ("/config/", ".env", "settings", ".yaml", ".yml", ".toml", ".ini")):
        add("modifies_config_file", "Modifies config file", 25)
    if any(part in lowered for part in ("schema", "migration", "migrations")):
        add("modifies_schema_or_migration", "Modifies schema or migration", 30)
    if any(part in lowered for part in ("auth", "permission", "permissions")):
        add("modifies_auth_or_permission_path", "Modifies auth or permission path", 35)
    if deletions > additions:
        add("deletes_more_than_adds", "Deletes more lines than it adds", 10)
    if additions + deletions > 200:
        add("large_diff_over_200_lines", "Large diff over 200 changed lines", 20)
    if is_untracked:
        add("untracked_file_included", "Untracked file included", 10)
    if "lock" in lowered:
        add("lockfile_changed", "Lockfile changed", 20)
    if _is_test_path(lowered):
        add("touches_tests_only", "Touches tests only", -10)
    elif not has_test_evidence:
        add("no_related_test_evidence", "No related test evidence", 20)

    score = sum(reason.weight for reason in reasons)
    if score >= 50:
        band = "high"
    elif score >= 25:
        band = "medium"
    else:
        band = "low"
    return RiskScore(score=score, band=band, reasons=reasons)


def _is_test_path(path: str) -> bool:
    return "/tests/" in path or path.startswith("tests/") or ".test." in path or path.endswith("_test.py")
