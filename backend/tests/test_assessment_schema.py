from app.schemas.assessment import (
    AgentChangeRecord,
    AssessmentManifest,
    ChangedFileDetail,
)


def test_assessment_manifest_accepts_phase1_payload():
    manifest = AssessmentManifest.model_validate(
        {
            "assessment_id": "aca_ws_1",
            "workspace_snapshot_id": "ws_1",
            "repo_key": "demo",
            "status": "ready",
            "agentic_summary": {
                "generated_by": "codex_logs",
                "capture_level": "partial",
                "confidence": "medium",
                "time_window": {
                    "since_commit": "HEAD",
                    "since_commit_time": None,
                },
                "user_design_goal": "用户希望重构 Agentic Change Assessment。",
                "codex_change_summary": "Codex 修改了 assessment builder 和 UI。",
                "main_objective": "围绕 diff review 构建评估工作台。",
                "key_decisions": ["以 diff 为中心"],
                "files_or_areas_changed": ["backend/app"],
                "tests_and_verification": ["pytest backend/tests"],
                "unknowns": ["Codex 日志按 best-effort 采集。"],
            },
            "summary": {
                "headline": "Workspace diff requires review.",
                "overall_risk_level": "medium",
                "coverage_status": "unknown",
                "changed_file_count": 1,
                "unreviewed_file_count": 1,
                "affected_capability_count": 0,
                "missing_test_count": 0,
                "agent_sources": ["git_diff"],
                "recommended_review_order": ["backend/app/main.py"],
            },
            "file_list": [
                {
                    "file_id": "cf_abc123",
                    "path": "backend/app/main.py",
                    "old_path": None,
                    "status": "modified",
                    "additions": 2,
                    "deletions": 1,
                    "risk_level": "medium",
                    "coverage_status": "unknown",
                    "review_status": "unreviewed",
                    "agent_sources": ["git_diff"],
                    "diff_fingerprint": "sha256:abc",
                }
            ],
            "risk_signals_summary": [],
            "agent_sources": ["git_diff"],
            "review_progress": {
                "total": 1,
                "reviewed": 0,
                "needs_follow_up": 0,
                "needs_recheck": 0,
                "unreviewed": 1,
            },
        }
    )

    assert manifest.file_list[0].file_id == "cf_abc123"
    assert manifest.summary.changed_file_count == 1
    assert manifest.agentic_summary.main_objective == "围绕 diff review 构建评估工作台。"


def test_changed_file_detail_models_diff_and_related_agent_record():
    detail = ChangedFileDetail.model_validate(
        {
            "file": {
                "file_id": "cf_abc123",
                "path": "backend/app/main.py",
                "old_path": None,
                "status": "modified",
                "additions": 2,
                "deletions": 1,
                "risk_level": "medium",
                "coverage_status": "unknown",
                "review_status": "unreviewed",
                "agent_sources": ["git_diff"],
                "diff_fingerprint": "sha256:abc",
            },
            "diff_hunks": [
                {
                    "hunk_id": "hunk_001",
                    "old_start": 1,
                    "old_lines": 1,
                    "new_start": 1,
                    "new_lines": 2,
                    "hunk_fingerprint": "sha256:def",
                    "lines": [
                        {"type": "remove", "content": "old"},
                        {"type": "add", "content": "new"},
                    ],
                }
            ],
            "changed_symbols": [],
            "related_agent_records": [
                {
                    "record_id": "acr_git_diff_ws_1",
                    "source": "git_diff",
                    "capture_level": "diff_only",
                    "evidence_sources": ["git_diff", "git_status"],
                    "confidence": {
                        "files_touched": "high",
                        "commands_run": "low",
                        "reasoning_summary": "low",
                        "tests_run": "low",
                    },
                    "task_summary": "Workspace contains uncommitted git changes.",
                    "declared_intent": "",
                    "reasoning_summary": "",
                    "files_touched": ["backend/app/main.py"],
                    "commands_run": [],
                    "tests_run": [],
                    "known_limitations": ["No structured coding-agent log was available."],
                    "raw_log_ref": "",
                }
            ],
            "related_tests": [],
            "impact_facts": [],
            "file_assessment": {
                "why_changed": "No structured agent reason is available.",
                "impact_summary": "Review the diff and related tests.",
                "test_summary": "No direct test evidence was found.",
                "recommended_action": "Review this file manually.",
                "generated_by": "rules",
                "agent_status": "not_run",
                "agent_source": None,
                "confidence": "low",
                "evidence_refs": ["git_diff"],
                "unknowns": ["Codex agent assessment has not run."],
            },
            "review_state": {
                "review_status": "unreviewed",
                "diff_fingerprint": "sha256:abc",
                "reviewer": None,
                "reviewed_at": None,
                "notes": [],
            },
        }
    )

    assert detail.related_agent_records[0].capture_level == "diff_only"
    assert detail.diff_hunks[0].lines[0].type == "remove"


def test_agent_record_requires_fidelity_metadata():
    record = AgentChangeRecord.model_validate(
        {
            "record_id": "acr_git_diff_ws_1",
            "source": "git_diff",
            "capture_level": "diff_only",
            "evidence_sources": ["git_diff", "git_status"],
            "confidence": {
                "files_touched": "high",
                "commands_run": "low",
                "reasoning_summary": "low",
                "tests_run": "low",
            },
            "task_summary": "Workspace contains uncommitted git changes.",
            "declared_intent": "",
            "reasoning_summary": "",
            "files_touched": ["backend/app/main.py"],
            "commands_run": [],
            "tests_run": [],
            "known_limitations": ["No structured coding-agent log was available."],
            "raw_log_ref": "",
        }
    )

    assert record.confidence.files_touched == "high"
