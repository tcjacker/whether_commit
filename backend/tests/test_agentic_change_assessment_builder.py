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


def test_builder_generates_agentic_file_assessment_from_diff_logs_impact_and_tests():
    builder = AgenticChangeAssessmentBuilder()
    agent_record = {
        "record_id": "acr_codex_ws_2",
        "source": "codex",
        "capture_level": "partial",
        "evidence_sources": ["git_diff", "codex_jsonl"],
        "confidence": {
            "files_touched": "high",
            "commands_run": "medium",
            "reasoning_summary": "medium",
            "tests_run": "high",
        },
        "task_summary": "重构 assessment evidence panel 的生成逻辑。",
        "declared_intent": "让 Verdict、Why、Impact、Tests 基于事实和 Agent 日志生成。",
        "reasoning_summary": "需要避免前端固定文案，改为后端按文件产出审查结论。",
        "files_touched": ["backend/app/services/assessment_agent.py"],
        "commands_run": ["pytest backend/tests/test_agentic_change_assessment_builder.py"],
        "tests_run": [{"command": "pytest backend/tests/test_agentic_change_assessment_builder.py", "status": "passed"}],
        "known_limitations": [],
        "raw_log_ref": "codex://session/ws_2",
    }
    change_data = {
        "changed_files": ["backend/app/services/assessment_agent.py"],
        "changed_symbols": ["backend.app.services.assessment_agent.FileAssessmentAgent"],
        "changed_functions": ["build_file_assessment"],
        "changed_routes": [],
        "file_diff_stats": {
            "backend/app/services/assessment_agent.py": {
                "added_lines": 42,
                "deleted_lines": 3,
                "change_type": "new file",
                "snippets": ["class FileAssessmentAgent:", "def build_file_assessment(self):"],
            }
        },
        "file_diffs": {
            "backend/app/services/assessment_agent.py": "@@ -0,0 +1,2 @@\n+class FileAssessmentAgent:\n+    pass\n"
        },
        "agent_activity_evidence": [
            {
                "source": "codex",
                "summary": "基于 backend/app/services/assessment_agent.py 生成四块 evidence panel 文案",
                "related_files": ["backend/app/services/assessment_agent.py"],
            }
        ],
        "direct_impacts": [
            {
                "entity_type": "module",
                "entity_id": "mod_backend__app__services__assessment_agent",
                "reason": "direct_file_change",
                "evidence": {"files": ["backend/app/services/assessment_agent.py"]},
                "distance": 0,
                "direction": "direct_change",
            }
        ],
    }
    verification_data = {
        "affected_tests": ["backend/tests/test_agentic_change_assessment_builder.py"],
        "missing_tests_for_changed_paths": [],
        "evidence_by_path": {
            "backend/tests/test_agentic_change_assessment_builder.py": {"status": "passed"}
        },
    }

    result = builder.build(
        repo_key="demo",
        workspace_snapshot_id="ws_2",
        change_data=change_data,
        verification_data=verification_data,
        review_graph_data={"nodes": [], "edges": []},
        agent_records=[agent_record],
    )

    file_id = result["manifest"]["file_list"][0]["file_id"]
    assessment = result["file_details"][file_id]["file_assessment"]
    assert "42 added / 3 deleted" in assessment["recommended_action"]
    assert "codex" in assessment["why_changed"]
    assert "生成四块 evidence panel" in assessment["why_changed"]
    assert "FileAssessmentAgent" in assessment["impact_summary"]
    assert "direct_file_change" in assessment["impact_summary"]
    assert "1 related test" in assessment["test_summary"]
    assert "passed" in assessment["test_summary"]
    assert assessment["generated_by"] == "rules"
    assert assessment["agent_status"] == "not_run"
    assert assessment["confidence"] == "medium"
    assert "codex_jsonl" in assessment["evidence_refs"]


def test_builder_adds_manifest_level_agentic_summary_from_codex_logs():
    builder = AgenticChangeAssessmentBuilder()
    agent_record = {
        "record_id": "acr_codex_ws_3",
        "source": "codex",
        "capture_level": "partial",
        "evidence_sources": ["codex_jsonl", "agent_activity_evidence"],
        "confidence": {
            "files_touched": "high",
            "commands_run": "low",
            "reasoning_summary": "medium",
            "tests_run": "low",
        },
        "task_summary": "用户希望把 overview 改成 Agentic Change Assessment，以 diff review 为中心。",
        "declared_intent": "围绕 changed files、Codex/Claude 修改记录和测试覆盖做总评估。",
        "reasoning_summary": "先接入 GitDiffOnlyAdapter，再加入 Codex 日志和右侧 evidence panel。",
        "files_touched": ["backend/app/services/agentic_change_assessment/builder.py"],
        "commands_run": ["pytest backend/tests/test_agentic_change_assessment_builder.py"],
        "tests_run": [{"command": "pytest backend/tests/test_agentic_change_assessment_builder.py", "status": "passed"}],
        "known_limitations": ["日志按 best-effort 关联，可能不完整。"],
        "raw_log_ref": "",
    }
    change_data = {
        "base_commit_sha": "abc123",
        "since_commit_time": "2026-04-25T10:00:00Z",
        "changed_files": ["backend/app/services/agentic_change_assessment/builder.py"],
        "changed_symbols": ["AgenticChangeAssessmentBuilder"],
        "file_diff_stats": {
            "backend/app/services/agentic_change_assessment/builder.py": {
                "added_lines": 12,
                "deleted_lines": 1,
                "change_type": "modified file",
                "snippets": ["agentic_summary"],
            }
        },
        "file_diffs": {
            "backend/app/services/agentic_change_assessment/builder.py": "@@ -1 +1 @@\n+agentic_summary\n"
        },
        "agent_activity_evidence": [
            {
                "source": "codex",
                "summary": "用户确认第一版：读取上次提交后到现在的 Codex 聊天记录，总结用户设计目标和 Codex 变更。",
                "related_files": ["backend/app/services/agentic_change_assessment/builder.py"],
            },
            {
                "source": "codex",
                "summary": "Codex 实现 manifest 级 agentic_summary，并标注 best-effort 日志覆盖。",
                "related_files": ["backend/app/services/agentic_change_assessment/builder.py"],
            },
        ],
    }

    result = builder.build(
        repo_key="demo",
        workspace_snapshot_id="ws_3",
        change_data=change_data,
        verification_data={
            "affected_tests": ["backend/tests/test_agentic_change_assessment_builder.py"],
            "missing_tests_for_changed_paths": [],
            "evidence_by_path": {
                "backend/tests/test_agentic_change_assessment_builder.py": {"status": "passed"}
            },
        },
        review_graph_data={"nodes": [], "edges": []},
        agent_records=[agent_record],
    )

    summary = result["manifest"]["agentic_summary"]
    assert "codex" in result["manifest"]["agent_sources"]
    assert summary["generated_by"] == "codex_logs"
    assert summary["capture_level"] == "partial"
    assert summary["confidence"] == "medium"
    assert summary["time_window"]["since_commit"] == "abc123"
    assert "Agentic Change Assessment" in summary["user_design_goal"]
    assert "manifest 级 agentic_summary" in summary["codex_change_summary"]
    assert "diff review" in summary["main_objective"]
    assert "backend/app/services/agentic_change_assessment/builder.py" in summary["files_or_areas_changed"]
    assert "pytest backend/tests/test_agentic_change_assessment_builder.py" in summary["tests_and_verification"]
    assert any("best-effort" in item for item in summary["unknowns"])


def test_builder_prefers_codex_session_conversation_for_manifest_summary():
    builder = AgenticChangeAssessmentBuilder()
    change_data = {
        "base_commit_sha": "abc123",
        "since_commit_time": "2026-04-25T10:00:00Z",
        "changed_files": ["frontend/src/components/assessment/AssessmentSummaryBar.tsx"],
        "file_diff_stats": {
            "frontend/src/components/assessment/AssessmentSummaryBar.tsx": {
                "added_lines": 18,
                "deleted_lines": 2,
                "change_type": "modified file",
            }
        },
        "file_diffs": {
            "frontend/src/components/assessment/AssessmentSummaryBar.tsx": "@@ -1 +1 @@\n+summary\n"
        },
        "codex_conversation_evidence": {
            "source": "codex_session_jsonl",
            "capture_level": "partial",
            "session_count": 1,
            "message_count": 3,
            "session_ids": ["sess_1"],
            "user_messages": [
                "用户要求接入真正的 Codex session JSONL 解析，把当前 workspace 的 user/assistant 对话按时间窗口抽出来做 chunk summary。"
            ],
            "assistant_messages": [
                "Codex 新增 session reader，按 cwd 和 since_commit_time 过滤会话，并把摘要接到 manifest 顶部。"
            ],
            "source_paths": ["/tmp/rollout.jsonl"],
        },
    }

    result = builder.build(
        repo_key="demo",
        workspace_snapshot_id="ws_4",
        change_data=change_data,
        verification_data={"affected_tests": [], "missing_tests_for_changed_paths": [], "evidence_by_path": {}},
        review_graph_data={"nodes": [], "edges": []},
        agent_records=[],
    )

    summary = result["manifest"]["agentic_summary"]
    assert summary["generated_by"] == "codex_logs"
    assert summary["capture_level"] == "partial"
    assert summary["confidence"] == "medium"
    assert "Codex session JSONL" in summary["user_design_goal"]
    assert "session reader" in summary["codex_change_summary"]
    assert "session JSONL" in summary["main_objective"]
    assert any("解析 Codex session JSONL" in item for item in summary["key_decisions"])


def test_builder_uses_classified_conversation_summary_when_available():
    builder = AgenticChangeAssessmentBuilder()
    change_data = {
        "base_commit_sha": "abc123",
        "since_commit_time": "2026-04-25T10:00:00Z",
        "changed_files": ["backend/app/services/agent_records/codex_sessions.py"],
        "file_diff_stats": {
            "backend/app/services/agent_records/codex_sessions.py": {
                "added_lines": 40,
                "deleted_lines": 1,
                "change_type": "modified file",
            }
        },
        "file_diffs": {
            "backend/app/services/agent_records/codex_sessions.py": "@@ -1 +1 @@\n+classified_summary\n"
        },
        "codex_conversation_evidence": {
            "source": "codex_session_jsonl",
            "capture_level": "partial",
            "classified_summary_source": "codex_llm",
            "session_count": 1,
            "message_count": 8,
            "session_ids": ["sess_1"],
            "user_messages": ["这条原始 user message 不应该优先于分类后的 goal。"],
            "assistant_messages": ["这条原始 assistant message 不应该优先于分类后的 action。"],
            "classified_summary": {
                "goals": ["提高 summary 质量：长对话分段压缩，并按目标、决策、实现动作分类。"],
                "decisions": ["第一版不调用 LLM，保证 rebuild 稳定。"],
                "implementation_actions": ["新增 Codex session chunker，输出 classified_summary。"],
                "tests_and_verification": ["pytest backend/tests/test_codex_session_reader.py"],
            },
        },
    }

    result = builder.build(
        repo_key="demo",
        workspace_snapshot_id="ws_5",
        change_data=change_data,
        verification_data={"affected_tests": [], "missing_tests_for_changed_paths": [], "evidence_by_path": {}},
        review_graph_data={"nodes": [], "edges": []},
        agent_records=[],
    )

    summary = result["manifest"]["agentic_summary"]
    assert "长对话分段压缩" in summary["user_design_goal"]
    assert "session chunker" in summary["codex_change_summary"]
    assert any("不调用 LLM" in item for item in summary["key_decisions"])
    assert "pytest backend/tests/test_codex_session_reader.py" in summary["tests_and_verification"]
    assert any("Codex LLM 二次压缩" in item for item in summary["unknowns"])
