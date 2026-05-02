from app.schemas.assessment import ReviewSignal
from app.services.precommit_review.policy import decide_review


def test_decision_forces_not_recommended_for_open_blocker():
    signal = ReviewSignal(
        signal_id="sig_failed",
        kind="failed_test",
        target_type="evidence",
        target_id="ev_test",
        severity="blocker",
        status="open",
        decision_impact="forces_not_recommended",
        evidence_ids=["ev_test"],
        policy_rule_id="failed_executed_test",
        message="A test failed.",
    )

    assert decide_review([signal], snapshot_is_stale=False) == "not_recommended"


def test_decision_needs_review_for_open_review_signal():
    signal = ReviewSignal(
        signal_id="sig_hunk",
        kind="unreviewed_high_risk_hunk",
        target_type="hunk",
        target_id="hunk_1",
        severity="review",
        status="open",
        decision_impact="prevents_no_known_blockers",
        evidence_ids=[],
        policy_rule_id="high_risk_hunk_unreviewed",
        message="High risk hunk needs review.",
    )

    assert decide_review([signal], snapshot_is_stale=False) == "needs_review"


def test_decision_returns_no_known_blockers_when_signals_are_resolved():
    signal = ReviewSignal(
        signal_id="sig_hunk",
        kind="unreviewed_high_risk_hunk",
        target_type="hunk",
        target_id="hunk_1",
        severity="review",
        status="reviewed",
        decision_impact="prevents_no_known_blockers",
        evidence_ids=[],
        policy_rule_id="high_risk_hunk_unreviewed",
        message="High risk hunk reviewed.",
    )

    assert decide_review([signal], snapshot_is_stale=False) == "no_known_blockers"


def test_decision_stale_snapshot_is_not_recommended():
    assert decide_review([], snapshot_is_stale=True) == "not_recommended"
