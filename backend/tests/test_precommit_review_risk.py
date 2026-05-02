from app.services.precommit_review.risk import score_file_risk


def test_schema_and_missing_tests_make_high_risk():
    risk = score_file_risk("backend/app/schemas/assessment.py", additions=20, deletions=5, has_test_evidence=False)

    assert risk.band == "high"
    assert "modifies_schema_or_migration" in {reason.reason_id for reason in risk.reasons}
    assert "no_related_test_evidence" in {reason.reason_id for reason in risk.reasons}


def test_tests_only_change_reduces_risk():
    risk = score_file_risk("backend/tests/test_example.py", additions=5, deletions=1, has_test_evidence=True)

    assert risk.band == "low"
