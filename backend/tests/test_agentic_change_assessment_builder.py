from app.services.agentic_change_assessment.builder import AgenticChangeAssessmentBuilder


def test_builder_returns_test_management_payload_for_changed_tests():
    builder = AgenticChangeAssessmentBuilder()
    change_data = {
        "changed_files": ["backend/tests/test_builder.py"],
        "changed_symbols": ["test_builder_emits_review_signals"],
        "file_diff_stats": {
            "backend/tests/test_builder.py": {
                "added_lines": 2,
                "deleted_lines": 0,
                "change_type": "modified file",
            }
        },
        "file_diffs": {
            "backend/tests/test_builder.py": (
                "@@ -1,0 +1,2 @@\n"
                "+def test_builder_emits_review_signals():\n"
                "+    assert True\n"
            )
        },
    }

    result = builder.build(
        repo_key="demo",
        workspace_snapshot_id="ws_tests",
        change_data=change_data,
        verification_data={"affected_tests": [], "missing_tests_for_changed_paths": [], "evidence_by_path": {}},
        review_graph_data={"nodes": [], "edges": []},
        agent_records=[],
    )

    test_management = result["test_management"]

    assert test_management["summary"]["test_case_count"] == 1
    assert test_management["summary"]["files"][0]["path"] == "backend/tests/test_builder.py"
    assert test_management["summary"]["files"][0]["test_cases"][0]["name"] == "test_builder_emits_review_signals"


def test_builder_passes_agent_instruction_contract_to_test_management(tmp_path):
    (tmp_path / "CLAUDE.md").write_text(
        "Write tests with test_* names under tests/ when changing behavior.",
        encoding="utf-8",
    )
    builder = AgenticChangeAssessmentBuilder()
    change_data = {
        "workspace_path": str(tmp_path),
        "changed_files": ["backend/tests/test_builder.py"],
        "changed_symbols": ["test_builder_emits_review_signals"],
        "file_diff_stats": {
            "backend/tests/test_builder.py": {
                "added_lines": 2,
                "deleted_lines": 0,
                "change_type": "modified file",
            }
        },
        "file_diffs": {
            "backend/tests/test_builder.py": (
                "@@ -1,0 +1,2 @@\n"
                "+def test_builder_emits_review_signals():\n"
                "+    assert True\n"
            )
        },
    }

    result = builder.build(
        repo_key="demo",
        workspace_snapshot_id="ws_tests",
        change_data=change_data,
        verification_data={"affected_tests": [], "missing_tests_for_changed_paths": [], "evidence_by_path": {}},
        review_graph_data={"nodes": [], "edges": []},
        agent_records=[],
    )

    unknowns = result["test_management"]["summary"]["unknowns"]
    assert any("Agent instruction gap:" in unknown for unknown in unknowns)
    assert any(".agent-test-results" in unknown for unknown in unknowns)


def test_builder_feeds_test_management_evidence_back_to_changed_file_review_data():
    builder = AgenticChangeAssessmentBuilder()
    change_data = {
        "changed_files": ["backend/app/schemas/assessment.py", "backend/tests/test_builder.py"],
        "changed_symbols": ["AgentClaim"],
        "file_diff_stats": {
            "backend/app/schemas/assessment.py": {
                "added_lines": 1,
                "deleted_lines": 0,
                "change_type": "modified file",
            },
            "backend/tests/test_builder.py": {
                "added_lines": 2,
                "deleted_lines": 0,
                "change_type": "modified file",
            },
        },
        "file_diffs": {
            "backend/app/schemas/assessment.py": (
                "@@ -1,1 +1,2 @@\n"
                " class AgentClaim:\n"
                "+    source: str\n"
                "@@ -10,1 +11,2 @@\n"
                " class AgentClaim:\n"
                "+    message_ref: str\n"
            ),
            "backend/tests/test_builder.py": (
                "@@ -0,0 +1,2 @@\n"
                "+def test_builder_links_agent_claim():\n"
                "+    assert AgentClaim(source=\"codex\").source == \"codex\"\n"
            ),
        },
    }

    result = builder.build(
        repo_key="demo",
        workspace_snapshot_id="ws_test_feedback",
        change_data=change_data,
        verification_data={"affected_tests": [], "missing_tests_for_changed_paths": [], "evidence_by_path": {}},
        review_graph_data={"nodes": [], "edges": []},
        agent_records=[],
    )

    changed_file = next(
        item for item in result["manifest"]["file_list"] if item["path"] == "backend/app/schemas/assessment.py"
    )
    changed_detail = result["file_details"][changed_file["file_id"]]
    related_test = changed_detail["related_tests"][0]

    assert related_test["path"] == "backend/tests/test_builder.py"
    assert related_test["evidence_grade"] == "inferred"
    assert "test_management" in related_test["basis"]
    assert changed_file["weakest_test_evidence_grade"] == "inferred"
    assert len(changed_detail["related_tests"]) == 1
    assert [item["hunk_id"] for item in changed_detail["hunk_review_items"]] == ["hunk_001", "hunk_002"]
    assert all(item["fact_basis"][-1] == "test_workbench:inferred" for item in changed_detail["hunk_review_items"])
    assert all("Test workbench links" in item["reasons"][-1] for item in changed_detail["hunk_review_items"])


def test_builder_test_path_detection_includes_root_and_nested_tests_directories():
    builder = AgenticChangeAssessmentBuilder()

    assert builder._is_test_path("__tests__/client.js")
    assert builder._is_test_path("frontend/src/pages/__tests__/client.js")
    assert builder._is_test_path("frontend/src/api/client.spec.ts")
    assert builder._is_test_path("frontend/src/api/client.test.js")


def test_builder_returns_test_management_payload_for_root_level_javascript_tests():
    builder = AgenticChangeAssessmentBuilder()
    change_data = {
        "changed_files": ["__tests__/client.js"],
        "changed_symbols": ["renders client"],
        "file_diff_stats": {
            "__tests__/client.js": {
                "added_lines": 3,
                "deleted_lines": 0,
                "change_type": "modified file",
            }
        },
        "file_diffs": {
            "__tests__/client.js": (
                "@@ -1,0 +1,3 @@\n"
                "+it(\"renders client\", () => {\n"
                "+  expect(client.render()).toBeTruthy()\n"
                "+})\n"
            )
        },
    }

    result = builder.build(
        repo_key="demo",
        workspace_snapshot_id="ws_root_js_tests",
        change_data=change_data,
        verification_data={"affected_tests": [], "missing_tests_for_changed_paths": [], "evidence_by_path": {}},
        review_graph_data={"nodes": [], "edges": []},
        agent_records=[],
    )

    summary = result["test_management"]["summary"]

    assert summary["test_case_count"] == 1
    assert summary["files"][0]["path"] == "__tests__/client.js"


def test_builder_returns_test_management_payload_for_root_level_tests_directory():
    builder = AgenticChangeAssessmentBuilder()
    change_data = {
        "changed_files": ["tests/client.js"],
        "changed_symbols": ["renders client"],
        "file_diff_stats": {
            "tests/client.js": {
                "added_lines": 3,
                "deleted_lines": 0,
                "change_type": "modified file",
            }
        },
        "file_diffs": {
            "tests/client.js": (
                "@@ -1,0 +1,3 @@\n"
                "+it(\"renders client\", () => {\n"
                "+  expect(client.render()).toBeTruthy()\n"
                "+})\n"
            )
        },
    }

    result = builder.build(
        repo_key="demo",
        workspace_snapshot_id="ws_root_tests",
        change_data=change_data,
        verification_data={"affected_tests": [], "missing_tests_for_changed_paths": [], "evidence_by_path": {}},
        review_graph_data={"nodes": [], "edges": []},
        agent_records=[],
    )

    summary = result["test_management"]["summary"]

    assert summary["changed_test_file_count"] == 1
    assert summary["test_case_count"] == 1
    assert summary["files"][0]["path"] == "tests/client.js"


def test_builder_returns_test_management_payload_for_spec_named_javascript_tests():
    builder = AgenticChangeAssessmentBuilder()
    change_data = {
        "changed_files": ["frontend/src/api/client.spec.ts"],
        "changed_symbols": ["renders client"],
        "file_diff_stats": {
            "frontend/src/api/client.spec.ts": {
                "added_lines": 3,
                "deleted_lines": 0,
                "change_type": "modified file",
            }
        },
        "file_diffs": {
            "frontend/src/api/client.spec.ts": (
                "@@ -1,0 +1,3 @@\n"
                "+it(\"renders client\", () => {\n"
                "+  expect(client.render()).toBeTruthy()\n"
                "+})\n"
            )
        },
    }

    result = builder.build(
        repo_key="demo",
        workspace_snapshot_id="ws_spec_tests",
        change_data=change_data,
        verification_data={"affected_tests": [], "missing_tests_for_changed_paths": [], "evidence_by_path": {}},
        review_graph_data={"nodes": [], "edges": []},
        agent_records=[],
    )

    summary = result["test_management"]["summary"]

    assert summary["changed_test_file_count"] == 1
    assert summary["test_case_count"] == 1
    assert summary["files"][0]["path"] == "frontend/src/api/client.spec.ts"


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


def test_builder_emits_v02_review_signals_from_claims_tests_and_hunks():
    builder = AgenticChangeAssessmentBuilder()
    agent_record = {
        "record_id": "acr_codex_ws_6",
        "source": "codex",
        "capture_level": "partial",
        "evidence_sources": ["codex_jsonl"],
        "confidence": {
            "files_touched": "high",
            "commands_run": "medium",
            "reasoning_summary": "medium",
            "tests_run": "low",
        },
        "task_summary": "Agent said it added tests for the API type change.",
        "declared_intent": "Add tests for API response handling.",
        "reasoning_summary": "Need test coverage for changed API client behavior.",
        "files_touched": ["frontend/src/types/api.ts"],
        "commands_run": [],
        "tests_run": [],
        "known_limitations": [],
        "raw_log_ref": "codex://session/sess_6",
    }
    change_data = {
        "base_commit_sha": "abc123",
        "changed_files": ["frontend/src/types/api.ts"],
        "changed_symbols": ["EvidenceGrade"],
        "file_diff_stats": {
            "frontend/src/types/api.ts": {
                "added_lines": 70,
                "deleted_lines": 4,
                "change_type": "modified file",
            }
        },
        "file_diffs": {
            "frontend/src/types/api.ts": "@@ -1,2 +1,4 @@\n export type A = string\n+export type EvidenceGrade = 'claimed'\n+export interface AgentClaim {}\n"
        },
        "codex_conversation_evidence": {
            "source": "codex_session_jsonl",
            "capture_level": "partial",
            "session_ids": ["sess_6"],
            "message_count": 2,
            "user_messages": ["请为 API 类型变化补测试。"],
            "assistant_messages": ["我已经添加测试覆盖 API 类型变化。"],
            "classified_summary": {
                "goals": ["为 API 类型变化补测试。"],
                "decisions": [],
                "implementation_actions": ["修改 frontend/src/types/api.ts。"],
                "tests_and_verification": ["声称添加测试，但没有执行命令。"],
            },
        },
    }

    result = builder.build(
        repo_key="demo",
        workspace_snapshot_id="ws_6",
        change_data=change_data,
        verification_data={
            "affected_tests": [],
            "missing_tests_for_changed_paths": ["frontend/src/types/api.ts"],
            "evidence_by_path": {},
        },
        review_graph_data={"nodes": [], "edges": []},
        agent_records=[agent_record],
    )

    manifest = result["manifest"]
    file_summary = manifest["file_list"][0]
    file_detail = result["file_details"][file_summary["file_id"]]

    assert manifest["mode"] == "working_tree"
    assert manifest["provenance_capture_level"] == "partial"
    assert manifest["review_decision"] == "needs_tests"
    assert manifest["mismatch_count"] == 1
    assert manifest["weak_test_evidence_count"] == 1
    assert manifest["hunk_queue_preview"][0]["priority"] == file_summary["highest_hunk_priority"]
    assert file_summary["mismatch_count"] == 1
    assert file_summary["weakest_test_evidence_grade"] == "claimed"

    assert file_detail["agent_claims"][0]["type"] == "test"
    assert file_detail["agent_claims"][0]["session_id"] == "sess_6"
    assert file_detail["mismatches"][0]["kind"] == "claimed_tested_but_no_executed_test_evidence"
    assert file_detail["related_tests"][0]["evidence_grade"] == "claimed"
    assert file_detail["provenance_refs"][0]["session_id"] == "sess_6"
    assert file_detail["hunk_review_items"][0]["priority"] >= 70


def test_builder_detects_ui_only_and_config_only_claim_mismatches():
    builder = AgenticChangeAssessmentBuilder()
    agent_record = {
        "record_id": "acr_codex_ws_7",
        "source": "codex",
        "capture_level": "partial",
        "evidence_sources": ["codex_jsonl"],
        "confidence": {
            "files_touched": "medium",
            "commands_run": "low",
            "reasoning_summary": "medium",
            "tests_run": "low",
        },
        "task_summary": "This is UI only page polish and config-only cleanup.",
        "declared_intent": "Only frontend UI and config changes.",
        "reasoning_summary": "",
        "files_touched": ["backend/app/services/runtime.py"],
        "commands_run": [],
        "tests_run": [],
        "known_limitations": [],
        "raw_log_ref": "codex://session/sess_7",
    }
    change_data = {
        "changed_files": ["backend/app/services/runtime.py"],
        "changed_symbols": ["RuntimeService"],
        "file_diff_stats": {
            "backend/app/services/runtime.py": {
                "added_lines": 8,
                "deleted_lines": 1,
                "change_type": "modified file",
            }
        },
        "file_diffs": {
            "backend/app/services/runtime.py": "@@ -1,2 +1,3 @@\n class RuntimeService:\n+    enabled = True\n"
        },
        "codex_conversation_evidence": {
            "source": "codex_session_jsonl",
            "capture_level": "partial",
            "session_ids": ["sess_7"],
            "message_count": 2,
            "classified_summary": {
                "goals": ["仅前端页面改造。"],
                "decisions": ["配置 cleanup only。"],
                "implementation_actions": ["config-only cleanup."],
                "tests_and_verification": [],
            },
        },
    }

    result = builder.build(
        repo_key="demo",
        workspace_snapshot_id="ws_7",
        change_data=change_data,
        verification_data={"affected_tests": [], "missing_tests_for_changed_paths": [], "evidence_by_path": {}},
        review_graph_data={"nodes": [], "edges": []},
        agent_records=[agent_record],
    )

    file_summary = result["manifest"]["file_list"][0]
    file_detail = result["file_details"][file_summary["file_id"]]
    mismatch_kinds = {mismatch["kind"] for mismatch in file_detail["mismatches"]}

    assert "claimed_ui_only_but_backend_changed" in mismatch_kinds
    assert "claimed_config_only_but_runtime_code_changed" in mismatch_kinds
    assert file_summary["mismatch_count"] == 2


def test_builder_grades_test_evidence_levels():
    builder = AgenticChangeAssessmentBuilder()

    assert builder._test_evidence_grade(relationship="primary", status="passed", evidence="graph_inference") == "direct"
    assert builder._test_evidence_grade(relationship="secondary", status="passed", evidence="graph_inference") == "indirect"
    assert builder._test_evidence_grade(relationship="primary", status="not_run", evidence="graph_inference") == "not_run"
    assert builder._test_evidence_grade(relationship="inferred", status="unknown", evidence="graph_inference") == "inferred"
    assert builder._test_evidence_grade(relationship="inferred", status="unknown", evidence="agent_claim") == "claimed"


def test_hunk_queue_prioritizes_removed_fallback_and_aligns_provenance_hunk_id():
    builder = AgenticChangeAssessmentBuilder()
    agent_record = {
        "record_id": "acr_codex_ws_8",
        "source": "codex",
        "capture_level": "partial",
        "evidence_sources": ["codex_jsonl"],
        "confidence": {
            "files_touched": "high",
            "commands_run": "low",
            "reasoning_summary": "medium",
            "tests_run": "low",
        },
        "task_summary": "Implement runtime behavior update.",
        "declared_intent": "",
        "reasoning_summary": "",
        "files_touched": ["backend/app/services/runtime.py"],
        "commands_run": [],
        "tests_run": [],
        "known_limitations": [],
        "raw_log_ref": "codex://session/sess_8",
    }
    change_data = {
        "changed_files": ["backend/app/services/runtime.py"],
        "changed_symbols": ["run"],
        "file_diff_stats": {
            "backend/app/services/runtime.py": {
                "added_lines": 2,
                "deleted_lines": 2,
                "change_type": "modified file",
            }
        },
        "file_diffs": {
            "backend/app/services/runtime.py": (
                "@@ -1,3 +1,3 @@\n"
                " def run():\n"
                "-    if not allowed:\n"
                "-        return fallback()\n"
                "+    execute()\n"
                "@@ -10,2 +10,2 @@\n"
                " def other():\n"
                "+    return True\n"
            )
        },
        "codex_conversation_evidence": {
            "source": "codex_session_jsonl",
            "capture_level": "partial",
            "session_ids": ["sess_8"],
            "message_count": 1,
            "classified_summary": {
                "goals": ["实现 runtime behavior update。"],
                "decisions": [],
                "implementation_actions": ["修改 backend/app/services/runtime.py。"],
                "tests_and_verification": [],
            },
        },
    }

    result = builder.build(
        repo_key="demo",
        workspace_snapshot_id="ws_8",
        change_data=change_data,
        verification_data={"affected_tests": [], "missing_tests_for_changed_paths": [], "evidence_by_path": {}},
        review_graph_data={"nodes": [], "edges": []},
        agent_records=[agent_record],
    )

    file_summary = result["manifest"]["file_list"][0]
    hunks = result["file_details"][file_summary["file_id"]]["hunk_review_items"]

    assert hunks[0]["priority"] > hunks[1]["priority"]
    assert "guard_or_fallback_deleted" in hunks[0]["fact_basis"]
    assert hunks[0]["provenance_refs"][0]["hunk_id"] == "hunk_001"
    assert hunks[1]["provenance_refs"][0]["hunk_id"] == "hunk_002"


def test_builder_does_not_spread_path_specific_test_claims_to_every_file():
    builder = AgenticChangeAssessmentBuilder()
    change_data = {
        "changed_files": ["frontend/src/types/api.ts", "frontend/src/components/Button.tsx"],
        "changed_symbols": ["EvidenceGrade", "Button"],
        "file_diff_stats": {
            "frontend/src/types/api.ts": {
                "added_lines": 30,
                "deleted_lines": 2,
                "change_type": "modified file",
            },
            "frontend/src/components/Button.tsx": {
                "added_lines": 3,
                "deleted_lines": 1,
                "change_type": "modified file",
            },
        },
        "file_diffs": {
            "frontend/src/types/api.ts": "@@ -1 +1,2 @@\n+export type EvidenceGrade = 'claimed'\n",
            "frontend/src/components/Button.tsx": "@@ -1 +1 @@\n+export function Button() {}\n",
        },
        "codex_conversation_evidence": {
            "source": "codex_session_jsonl",
            "capture_level": "partial",
            "session_ids": ["sess_9"],
            "message_count": 2,
            "classified_summary": {
                "goals": ["为 frontend/src/types/api.ts 补测试。"],
                "decisions": [],
                "implementation_actions": ["修改 frontend/src/types/api.ts。"],
                "tests_and_verification": ["frontend/src/types/api.ts 的测试已添加，但没有执行命令。"],
            },
        },
    }

    result = builder.build(
        repo_key="demo",
        workspace_snapshot_id="ws_9",
        change_data=change_data,
        verification_data={"affected_tests": [], "missing_tests_for_changed_paths": [], "evidence_by_path": {}},
        review_graph_data={"nodes": [], "edges": []},
        agent_records=[],
    )

    by_path = {
        summary["path"]: result["file_details"][summary["file_id"]]
        for summary in result["manifest"]["file_list"]
    }

    assert by_path["frontend/src/types/api.ts"]["mismatches"][0]["kind"] == "claimed_tested_but_no_executed_test_evidence"
    assert by_path["frontend/src/components/Button.tsx"]["mismatches"] == []


def test_hunk_priority_uses_graduated_scores_instead_of_saturating_common_cases():
    builder = AgenticChangeAssessmentBuilder()
    change_data = {
        "changed_files": ["frontend/src/types/api.ts"],
        "changed_symbols": ["EvidenceGrade"],
        "file_diff_stats": {
            "frontend/src/types/api.ts": {
                "added_lines": 70,
                "deleted_lines": 4,
                "change_type": "modified file",
            }
        },
        "file_diffs": {
            "frontend/src/types/api.ts": "@@ -1 +1,3 @@\n+export type EvidenceGrade = 'unknown'\n+export type ReviewDecision = 'needs_tests'\n"
        },
    }

    result = builder.build(
        repo_key="demo",
        workspace_snapshot_id="ws_10",
        change_data=change_data,
        verification_data={"affected_tests": [], "missing_tests_for_changed_paths": [], "evidence_by_path": {}},
        review_graph_data={"nodes": [], "edges": []},
        agent_records=[],
    )

    file_summary = result["manifest"]["file_list"][0]

    assert file_summary["highest_hunk_priority"] == 50
    assert result["file_details"][file_summary["file_id"]]["hunk_review_items"][0]["risk_level"] == "medium"


def test_builder_uses_structured_codex_refs_for_claim_and_hunk_provenance():
    builder = AgenticChangeAssessmentBuilder()
    change_data = {
        "changed_files": ["frontend/src/api/client.ts"],
        "changed_symbols": ["request"],
        "file_diff_stats": {
            "frontend/src/api/client.ts": {
                "added_lines": 4,
                "deleted_lines": 1,
                "change_type": "modified file",
            }
        },
        "file_diffs": {
            "frontend/src/api/client.ts": "@@ -1,2 +1,4 @@\n try:\n-old\n+new\n"
        },
        "codex_conversation_evidence": {
            "source": "codex_session_jsonl",
            "capture_level": "partial",
            "session_ids": ["sess_structured"],
            "message_count": 1,
            "user_messages": ["请修改 frontend/src/api/client.ts。"],
            "assistant_messages": [],
            "message_refs": [
                {
                    "session_id": "sess_structured",
                    "message_ref": "msg_user_1",
                    "role": "user",
                    "text": "请修改 frontend/src/api/client.ts 并补测试。",
                }
            ],
            "tool_calls": [
                {
                    "session_id": "sess_structured",
                    "tool_call_ref": "call_patch_1",
                    "tool_name": "apply_patch",
                    "arguments": "*** Update File: frontend/src/api/client.ts",
                    "related_files": ["frontend/src/api/client.ts"],
                }
            ],
            "commands": [
                {
                    "session_id": "sess_structured",
                    "tool_call_ref": "call_exec_1",
                    "command": "sed -n '1,80p' frontend/src/api/client.ts",
                    "related_files": ["frontend/src/api/client.ts"],
                }
            ],
            "file_refs": [
                {
                    "session_id": "sess_structured",
                    "message_ref": "",
                    "tool_call_ref": "call_patch_1",
                    "source": "tool:apply_patch",
                    "file_path": "frontend/src/api/client.ts",
                    "confidence": "high",
                }
            ],
            "classified_summary": {
                "goals": ["请修改 frontend/src/api/client.ts 并补测试。"],
                "decisions": [],
                "implementation_actions": ["修改 frontend/src/api/client.ts。"],
                "tests_and_verification": ["npm test -- api"],
            },
        },
    }

    result = builder.build(
        repo_key="demo",
        workspace_snapshot_id="ws_11",
        change_data=change_data,
        verification_data={"affected_tests": [], "missing_tests_for_changed_paths": [], "evidence_by_path": {}},
        review_graph_data={"nodes": [], "edges": []},
        agent_records=[],
    )

    file_summary = result["manifest"]["file_list"][0]
    detail = result["file_details"][file_summary["file_id"]]

    assert detail["agent_claims"][0]["message_ref"] == "msg_user_1"
    assert detail["agent_claims"][0]["session_id"] == "sess_structured"
    assert detail["provenance_refs"][0]["tool_call_ref"] == "call_patch_1"
    assert detail["provenance_refs"][0]["confidence"] == "high"
    assert detail["hunk_review_items"][0]["provenance_refs"][0]["tool_call_ref"] == "call_patch_1"
    assert detail["hunk_review_items"][0]["provenance_refs"][0]["hunk_id"] == "hunk_001"
    assert any(ref["command"] == "sed -n '1,80p' frontend/src/api/client.ts" for ref in detail["provenance_refs"])


def test_builder_uses_codex_command_evidence_for_related_test_grade():
    builder = AgenticChangeAssessmentBuilder()
    change_data = {
        "changed_files": ["frontend/src/api/client.ts"],
        "changed_symbols": ["request"],
        "file_diff_stats": {
            "frontend/src/api/client.ts": {
                "added_lines": 4,
                "deleted_lines": 1,
                "change_type": "modified file",
            }
        },
        "file_diffs": {
            "frontend/src/api/client.ts": "@@ -1 +1 @@\n+new\n"
        },
        "codex_conversation_evidence": {
            "source": "codex_session_jsonl",
            "capture_level": "partial",
            "session_ids": ["sess_command"],
            "message_count": 1,
            "commands": [
                {
                    "session_id": "sess_command",
                    "tool_call_ref": "call_exec_1",
                    "command": "npm test -- api",
                    "related_files": [],
                }
            ],
        },
    }

    result = builder.build(
        repo_key="demo",
        workspace_snapshot_id="ws_12",
        change_data=change_data,
        verification_data={
            "affected_tests": ["frontend/src/api/__tests__/client.test.ts"],
            "missing_tests_for_changed_paths": [],
            "evidence_by_path": {},
        },
        review_graph_data={"nodes": [], "edges": []},
        agent_records=[],
    )

    file_summary = result["manifest"]["file_list"][0]
    related_test = result["file_details"][file_summary["file_id"]]["related_tests"][0]

    assert related_test["last_status"] == "passed"
    assert related_test["evidence_grade"] == "direct"
    assert "command_evidence" in related_test["basis"]
