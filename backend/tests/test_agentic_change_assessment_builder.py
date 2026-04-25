from app.services.agentic_change_assessment.builder import AgenticChangeAssessmentBuilder


def test_builder_creates_manifest_and_lazy_file_detail():
    builder = AgenticChangeAssessmentBuilder()
    agent_record = {
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
    change_data = {
        "changed_files": ["backend/app/main.py"],
        "changed_symbols": ["backend.app.main.health"],
        "linked_tests": ["backend/tests/test_main.py"],
        "file_diff_stats": {
            "backend/app/main.py": {
                "added_lines": 2,
                "deleted_lines": 1,
                "change_type": "modified file",
                "snippets": ["new line"],
            }
        },
        "file_diffs": {
            "backend/app/main.py": "@@ -1,1 +1,2 @@\n-old\n+new\n+line\n"
        },
    }
    verification_data = {
        "affected_tests": ["backend/tests/test_main.py"],
        "missing_tests_for_changed_paths": [],
        "evidence_by_path": {
            "backend/tests/test_main.py": {"status": "passed"}
        },
    }

    result = builder.build(
        repo_key="demo",
        workspace_snapshot_id="ws_1",
        change_data=change_data,
        verification_data=verification_data,
        review_graph_data={"nodes": [], "edges": []},
        agent_records=[agent_record],
    )

    assert result["manifest"]["assessment_id"] == "aca_ws_1"
    assert result["manifest"]["file_list"][0]["path"] == "backend/app/main.py"
    file_id = result["manifest"]["file_list"][0]["file_id"]
    assert result["file_details"][file_id]["changed_symbols"] == ["backend.app.main.health"]
    assert result["file_details"][file_id]["related_agent_records"][0]["record_id"] == "acr_git_diff_ws_1"
    assert result["review_state"]["file_reviews"][0]["file_id"] == file_id
    assert result["overview_mirror"]["agentic_change_assessment"]["assessment_id"] == "aca_ws_1"
