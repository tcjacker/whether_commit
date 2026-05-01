from __future__ import annotations

from app.schemas.assessment import ReviewDecision, ReviewSignal


def decide_review(signals: list[ReviewSignal], snapshot_is_stale: bool) -> ReviewDecision:
    if snapshot_is_stale:
        return "not_recommended"

    open_signals = [signal for signal in signals if signal.status == "open"]
    if any(signal.decision_impact == "forces_not_recommended" for signal in open_signals):
        return "not_recommended"
    if any(signal.decision_impact == "prevents_no_known_blockers" for signal in open_signals):
        return "needs_review"
    return "no_known_blockers"
