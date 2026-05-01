from app.services.precommit_review.fingerprints import file_id_for_review, hunk_id_for_review, signal_id_for_review


def test_file_id_is_stable_for_same_target_path_and_patch():
    first = file_id_for_review("staged_only", "backend/app/main.py", "diff text")
    second = file_id_for_review("staged_only", "backend/app/main.py", "diff text")

    assert first == second
    assert first.startswith("file_")


def test_hunk_id_depends_on_file_and_normalized_patch():
    file_id = file_id_for_review("staged_only", "backend/app/main.py", "diff text")

    assert hunk_id_for_review(file_id, "+ new\n- old\n") == hunk_id_for_review(file_id, "+ new\n- old\n")
    assert hunk_id_for_review(file_id, "+ new\n- old\n") != hunk_id_for_review(file_id, "+ other\n- old\n")


def test_signal_id_ignores_message_text():
    first = signal_id_for_review("high_risk", "hunk", "hunk_1", ["ev_b", "ev_a"], "rule_1")
    second = signal_id_for_review("high_risk", "hunk", "hunk_1", ["ev_a", "ev_b"], "rule_1")

    assert first == second
    assert first.startswith("sig_")
