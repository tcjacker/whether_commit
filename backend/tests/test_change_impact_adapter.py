import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from textwrap import dedent

from app.services.change_impact.adapter import ChangeImpactAdapter


class ChangeImpactAdapterTest(unittest.TestCase):
    def test_changed_python_facts_only_include_symbols_overlapping_diff_hunks(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, "sample.py")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        def untouched():
                            return 1

                        def target_function():
                            return 2
                        """
                    ).strip()
                )

            adapter = ChangeImpactAdapter(workspace_path=tmp_dir)
            def fake_git_diff(relative_path, staged=False):
                if staged:
                    return ""
                return (
                    "@@ -1,5 +1,5 @@\n"
                    " def untouched():\n"
                    "     return 1\n"
                    "\n"
                    " def target_function():\n"
                    "-    return 1\n"
                    "+    return 2\n"
                )

            adapter._git_diff_for_file = fake_git_diff

            facts = adapter._extract_changed_python_facts("sample.py", " M")

            self.assertEqual(facts["symbols"], ["target_function"])
            self.assertEqual(facts["functions"], ["target_function"])
            self.assertEqual(facts["classes"], [])

    def test_staged_only_changes_are_used_for_diff_hunks(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, "sample.py")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        def untouched():
                            return 1

                        def staged_only():
                            return 2
                        """
                    ).strip()
                )

            adapter = ChangeImpactAdapter(workspace_path=tmp_dir)

            def fake_git_diff(relative_path, staged=False):
                if staged:
                    return (
                        "@@ -1,5 +1,5 @@\n"
                        " def untouched():\n"
                        "     return 1\n"
                        "\n"
                        " def staged_only():\n"
                        "-    return 1\n"
                        "+    return 2\n"
                    )
                return ""

            adapter._git_diff_for_file = fake_git_diff

            facts = adapter._extract_changed_python_facts("sample.py", " M")

            self.assertEqual(facts["symbols"], ["staged_only"])
            self.assertEqual(facts["functions"], ["staged_only"])
            self.assertEqual(facts["classes"], [])

    def test_untracked_python_file_includes_all_symbols(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, "new_module.py")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        class NewService:
                            pass

                        def create_item():
                            return True
                        """
                    ).strip()
                )

            adapter = ChangeImpactAdapter(workspace_path=tmp_dir)
            facts = adapter._extract_changed_python_facts("new_module.py", "??")

            self.assertEqual(facts["classes"], ["NewService"])
            self.assertEqual(facts["functions"], ["create_item"])
            self.assertEqual(facts["symbols"], ["NewService", "create_item"])

    def test_generate_change_analysis_uses_precise_fields(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.mkdir(os.path.join(tmp_dir, ".git"))
            adapter = ChangeImpactAdapter(workspace_path=tmp_dir)
            adapter._git_status_lines = lambda: [" M app/main.py", "?? tests/test_main.py"]
            adapter._load_graph_snapshot = lambda: {"modules": [], "dependencies": []}
            adapter._extract_changed_python_facts = lambda file_path, status: {
                "symbols": ["target_function"] if file_path == "app/main.py" else ["test_target_function"],
                "functions": ["target_function"] if file_path == "app/main.py" else ["test_target_function"],
                "classes": [],
                "routes": ["GET /health"] if file_path == "app/main.py" else [],
            }

            result = adapter.generate_change_analysis("ws_test")

        self.assertEqual(result["workspace_snapshot_id"], "ws_test")
        self.assertEqual(result["changed_files"], ["app/main.py", "tests/test_main.py"])
        self.assertEqual(result["changed_symbols"], ["target_function", "test_target_function"])
        self.assertEqual(result["changed_functions"], ["target_function", "test_target_function"])
        self.assertEqual(result["changed_routes"], ["GET /health"])
        self.assertEqual(result["directly_changed_modules"], ["mod_app", "mod_tests"])
        self.assertEqual(result["affected_entrypoints"], ["GET /health"])
        self.assertEqual(result["direct_impacts"][0]["entity_id"], "mod_app")
        self.assertTrue(all("entity_id" in item and "reason" in item for item in result["impact_reasons"]))
        self.assertEqual(result["why_impacted"], result["impact_reasons"])

    def test_generate_change_analysis_includes_file_diff_stats(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.mkdir(os.path.join(tmp_dir, ".git"))
            adapter = ChangeImpactAdapter(workspace_path=tmp_dir)
            adapter._git_status_lines = lambda: [" M app/main.py"]
            adapter._load_graph_snapshot = lambda: {"modules": [], "dependencies": []}
            adapter._extract_changed_python_facts = lambda _file_path, _status: {
                "symbols": [],
                "functions": [],
                "classes": [],
                "routes": [],
                "changed_schemas": [],
                "changed_jobs": [],
                "affected_data_objects": [],
            }
            adapter._git_diff_for_file = lambda _file_path, staged=False: (
                ""
                if staged
                else (
                    "@@ -1,3 +1,4 @@\n"
                    " def health():\n"
                    "-    return {'ok': True}\n"
                    "+    return {'ok': True, 'tests': 3}\n"
                    "+\n"
                    "+def ready():\n"
                    "+    return True\n"
                )
            )

            result = adapter.generate_change_analysis("ws_diff")

        stats = result["file_diff_stats"]["app/main.py"]
        self.assertEqual(stats["added_lines"], 4)
        self.assertEqual(stats["deleted_lines"], 1)
        self.assertEqual(stats["change_type"], "modified file")
        self.assertTrue(any("return {'ok': True, 'tests': 3}" in snippet for snippet in stats["snippets"]))
        self.assertIn("@@ -1,3 +1,4 @@", result["file_diffs"]["app/main.py"])

    def test_generate_change_analysis_uses_commit_range_entries_when_base_is_not_head(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.mkdir(os.path.join(tmp_dir, ".git"))
            adapter = ChangeImpactAdapter(workspace_path=tmp_dir, base_commit_sha="main")
            adapter._git_name_status_lines = lambda: ["M\tbackend/tests/test_builder.py"]
            adapter._git_status_lines = lambda: []
            adapter._load_graph_snapshot = lambda: {"modules": [], "dependencies": []}
            adapter._last_commit_timestamp = lambda: 100
            adapter._collect_codex_conversation_evidence = lambda _timestamp: {}
            adapter._git_diff_for_file = lambda _file_path, staged=False: ""
            adapter._extract_changed_python_facts = lambda file_path, status: {
                "symbols": ["test_builder_emits_review_signals"],
                "functions": ["test_builder_emits_review_signals"],
                "classes": [],
                "routes": [],
                "changed_schemas": [],
                "changed_jobs": [],
                "affected_data_objects": [],
            }
            adapter._git_range_diff_for_file = lambda file_path: (
                "@@ -0,0 +1,2 @@\n"
                "+def test_builder_emits_review_signals():\n"
                "+    assert True\n"
            )

            result = adapter.generate_change_analysis("ws_range")

        self.assertEqual(result["base_commit_sha"], "main")
        self.assertEqual(result["changed_files"], ["backend/tests/test_builder.py"])
        self.assertEqual(result["linked_tests"], ["backend/tests/test_builder.py"])
        self.assertIn("test_builder_emits_review_signals", result["changed_symbols"])

    def test_generate_change_analysis_includes_codex_conversation_evidence(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.mkdir(os.path.join(tmp_dir, ".git"))
            adapter = ChangeImpactAdapter(workspace_path=tmp_dir)
            adapter._git_status_lines = lambda: [" M app/main.py"]
            adapter._load_graph_snapshot = lambda: {"modules": [], "dependencies": []}
            adapter._git_diff_for_file = lambda _file_path, staged=False: ""
            adapter._last_commit_timestamp = lambda: 1777111200
            adapter._collect_agent_activity_evidence = lambda _changed_files: []
            adapter._collect_codex_conversation_evidence = lambda since_timestamp: {
                "source": "codex_session_jsonl",
                "capture_level": "partial",
                "session_count": 1,
                "message_count": 2,
                "session_ids": ["sess_1"],
                "user_messages": ["用户要求从 Codex session JSONL 总结本轮设计目标。"],
                "assistant_messages": ["Codex 接入 reader 并写入 manifest summary。"],
                "source_paths": ["/tmp/rollout.jsonl"],
                "seen_since_timestamp": since_timestamp,
            }
            adapter._extract_changed_python_facts = lambda _file_path, _status: {
                "symbols": [],
                "functions": [],
                "classes": [],
                "routes": [],
                "changed_schemas": [],
                "changed_jobs": [],
                "affected_data_objects": [],
            }

            result = adapter.generate_change_analysis("ws_codex_sessions")

        evidence = result["codex_conversation_evidence"]
        self.assertEqual(evidence["source"], "codex_session_jsonl")
        self.assertEqual(evidence["seen_since_timestamp"], 1777111200)
        self.assertIn("设计目标", evidence["user_messages"][0])

    def test_generate_change_analysis_includes_parseable_diff_for_untracked_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.mkdir(os.path.join(tmp_dir, ".git"))
            os.makedirs(os.path.join(tmp_dir, "app"))
            with open(os.path.join(tmp_dir, "app", "new_file.py"), "w", encoding="utf-8") as f:
                f.write("def created():\n")
                f.write("    return True\n")

            adapter = ChangeImpactAdapter(workspace_path=tmp_dir)
            adapter._git_status_lines = lambda: ["?? app/new_file.py"]
            adapter._load_graph_snapshot = lambda: {"modules": [], "dependencies": []}
            adapter._extract_changed_python_facts = lambda _file_path, _status: {
                "symbols": [],
                "functions": [],
                "classes": [],
                "routes": [],
                "changed_schemas": [],
                "changed_jobs": [],
                "affected_data_objects": [],
            }

            result = adapter.generate_change_analysis("ws_untracked")

        diff_text = result["file_diffs"]["app/new_file.py"]
        self.assertIn("--- /dev/null", diff_text)
        self.assertIn("+++ b/app/new_file.py", diff_text)
        self.assertIn("@@ -0,0 +1,2 @@", diff_text)
        self.assertIn("+def created():", diff_text)

    def test_generate_change_analysis_collects_agent_activity_evidence(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.mkdir(os.path.join(tmp_dir, ".git"))
            log_path = os.path.join(tmp_dir, "history.jsonl")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write('{"text":"把 app/main.py 的 diff 意义改成 Agent 归纳的改动说明"}\n')

            adapter = ChangeImpactAdapter(workspace_path=tmp_dir)
            adapter._git_status_lines = lambda: [" M app/main.py"]
            adapter._load_graph_snapshot = lambda: {"modules": [], "dependencies": []}
            adapter._git_diff_for_file = lambda _file_path, staged=False: ""
            adapter._agent_log_candidates = lambda: [Path(log_path)]
            adapter._extract_changed_python_facts = lambda _file_path, _status: {
                "symbols": [],
                "functions": [],
                "classes": [],
                "routes": [],
                "changed_schemas": [],
                "changed_jobs": [],
                "affected_data_objects": [],
            }

            result = adapter.generate_change_analysis("ws_agent_logs")

        evidence = result["agent_activity_evidence"]
        self.assertEqual(evidence[0]["source"], "codex")
        self.assertEqual(evidence[0]["related_files"], ["app/main.py"])
        self.assertIn("Agent 归纳", evidence[0]["summary"])

    def test_generate_change_analysis_collects_codex_sqlite_activity_evidence(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.mkdir(os.path.join(tmp_dir, ".git"))
            sqlite_path = os.path.join(tmp_dir, "logs_2.sqlite")
            conn = sqlite3.connect(sqlite_path)
            conn.execute(
                "create table logs (id integer primary key, ts integer, feedback_log_body text)"
            )
            conn.execute(
                "insert into logs (ts, feedback_log_body) values (?, ?)",
                (
                    1,
                    "实现 backend/app/services/agent_records/agent_log.py，"
                    "用于把 Codex 日志转成 AgentChangeRecord，解释 Why 的修改原因。",
                ),
            )
            conn.commit()
            conn.close()

            adapter = ChangeImpactAdapter(workspace_path=tmp_dir)
            adapter._git_status_lines = lambda: ["?? backend/app/services/agent_records/agent_log.py"]
            adapter._load_graph_snapshot = lambda: {"modules": [], "dependencies": []}
            adapter._agent_log_candidates = lambda: [Path(sqlite_path)]
            adapter._extract_changed_python_facts = lambda _file_path, _status: {
                "symbols": [],
                "functions": [],
                "classes": [],
                "routes": [],
                "changed_schemas": [],
                "changed_jobs": [],
                "affected_data_objects": [],
            }

            os.makedirs(os.path.join(tmp_dir, "backend/app/services/agent_records"))
            with open(os.path.join(tmp_dir, "backend/app/services/agent_records/agent_log.py"), "w", encoding="utf-8") as f:
                f.write("class AgentLogRecordAdapter:\n")
                f.write("    pass\n")

            result = adapter.generate_change_analysis("ws_sqlite_logs")

        evidence = result["agent_activity_evidence"]
        self.assertEqual(evidence[0]["source"], "codex")
        self.assertEqual(evidence[0]["related_files"], ["backend/app/services/agent_records/agent_log.py"])
        self.assertIn("AgentChangeRecord", evidence[0]["summary"])

    def test_generate_change_analysis_filters_codex_sqlite_logs_before_last_commit(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.mkdir(os.path.join(tmp_dir, ".git"))
            sqlite_path = os.path.join(tmp_dir, "logs_2.sqlite")
            conn = sqlite3.connect(sqlite_path)
            conn.execute(
                "create table logs (id integer primary key, ts integer, ts_nanos integer, feedback_log_body text)"
            )
            conn.execute(
                "insert into logs (ts, ts_nanos, feedback_log_body) values (?, ?, ?)",
                (
                    90,
                    0,
                    "旧日志 backend/app/services/agent_records/agent_log.py 不应该进入本轮 summary。",
                ),
            )
            conn.execute(
                "insert into logs (ts, ts_nanos, feedback_log_body) values (?, ?, ?)",
                (
                    110,
                    0,
                    "新日志 backend/app/services/agent_records/agent_log.py 应该进入本轮 summary。",
                ),
            )
            conn.commit()
            conn.close()

            adapter = ChangeImpactAdapter(workspace_path=tmp_dir)
            adapter._git_status_lines = lambda: ["?? backend/app/services/agent_records/agent_log.py"]
            adapter._last_commit_timestamp = lambda: 100
            adapter._load_graph_snapshot = lambda: {"modules": [], "dependencies": []}
            adapter._agent_log_candidates = lambda: [Path(sqlite_path)]
            adapter._extract_changed_python_facts = lambda _file_path, _status: {
                "symbols": [],
                "functions": [],
                "classes": [],
                "routes": [],
                "changed_schemas": [],
                "changed_jobs": [],
                "affected_data_objects": [],
            }

            os.makedirs(os.path.join(tmp_dir, "backend/app/services/agent_records"))
            with open(os.path.join(tmp_dir, "backend/app/services/agent_records/agent_log.py"), "w", encoding="utf-8") as f:
                f.write("class AgentLogRecordAdapter:\n")
                f.write("    pass\n")

            result = adapter.generate_change_analysis("ws_sqlite_logs")

        evidence = result["agent_activity_evidence"]
        self.assertEqual(len(evidence), 1)
        self.assertIn("新日志", evidence[0]["summary"])
        self.assertNotIn("旧日志", evidence[0]["summary"])
        self.assertEqual(result["base_commit_timestamp"], 100)

    def test_agent_activity_evidence_matches_full_raw_log_when_summary_is_truncated(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.mkdir(os.path.join(tmp_dir, ".git"))
            log_path = os.path.join(tmp_dir, "history.jsonl")
            raw_line = (
                'session_loop{thread_id=abc}: Submission sub=Submission { '
                'items: [Text { text: "为 assessment builder 增加 Codex 日志关联测试", kind: User }] } '
                + ("x" * 700)
                + " backend/tests/test_agentic_change_assessment_builder.py"
            )
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(raw_line + "\n")

            adapter = ChangeImpactAdapter(workspace_path=tmp_dir)
            adapter._git_status_lines = lambda: [" M backend/tests/test_agentic_change_assessment_builder.py"]
            adapter._load_graph_snapshot = lambda: {"modules": [], "dependencies": []}
            adapter._git_diff_for_file = lambda _file_path, staged=False: ""
            adapter._agent_log_candidates = lambda: [Path(log_path)]
            adapter._extract_changed_python_facts = lambda _file_path, _status: {
                "symbols": [],
                "functions": [],
                "classes": [],
                "routes": [],
                "changed_schemas": [],
                "changed_jobs": [],
                "affected_data_objects": [],
            }

            result = adapter.generate_change_analysis("ws_long_codex_log")

        evidence = result["agent_activity_evidence"]
        self.assertEqual(evidence[0]["source"], "codex")
        self.assertEqual(evidence[0]["related_files"], ["backend/tests/test_agentic_change_assessment_builder.py"])
        self.assertIn("Codex 日志关联测试", evidence[0]["summary"])

    def test_agent_activity_evidence_filters_raw_codex_telemetry_summaries(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.mkdir(os.path.join(tmp_dir, ".git"))
            log_path = os.path.join(tmp_dir, "history.jsonl")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(
                    "session_loop{thread_id=abc}:submission_dispatch{otel.name=\"op.dispatch.user_turn\"} "
                    "backend/tests/test_agentic_change_assessment_builder.py\n"
                )
                f.write(
                    "The following is the Codex agent history whose request action you are assessing. "
                    "backend/tests/test_agentic_change_assessment_builder.py\n"
                )
                f.write(
                    "Received message {\"type\":\"response.output_item.done\",\"item\":{\"type\":\"function_call\"}} "
                    "backend/tests/test_agentic_change_assessment_builder.py\n"
                )
                f.write(
                    'session_loop{thread_id=abc}: Submission sub=Submission { items: [Text { text: ">>> TRANSCRIPT START", '
                    'kind: User }, Text { text: ">>> TRANSCRIPT DELTA START", kind: User }] } '
                    "backend/tests/test_agentic_change_assessment_builder.py\n"
                )
                f.write(
                    'session_loop{thread_id=abc}: Submission sub=Submission { items: [Text { text: ">>> TRANSCRIPT END", '
                    'kind: User }, Text { text: ">>> TRANSCRIPT DELTA END", kind: User }] } '
                    "backend/tests/test_agentic_change_assessment_builder.py\n"
                )
                f.write(
                    '{"text":"You are a helpful assistant. You will be presented with a user prompt, and your job is to provide a short title for a task."} '
                    "backend/tests/test_agentic_change_assessment_builder.py\n"
                )
                f.write(
                    '{"text":"The Codex agent has requested the following action:"} '
                    "backend/tests/test_agentic_change_assessment_builder.py\n"
                )
                f.write(
                    '{"text":"Assess the exact planned action below. Use read-only tool checks when local state matters."} '
                    "backend/tests/test_agentic_change_assessment_builder.py\n"
                )
                f.write(
                    '{"text":"Planned action JSON:"} '
                    "backend/tests/test_agentic_change_assessment_builder.py\n"
                )
                f.write(
                    '{"text":"{ \\"command\\": [\\"/bin/zsh\\", \\"-lc\\", \\"pytest\\"], '
                    '\\"cwd\\": \\"/tmp\\", \\"justification\\": \\"approval wrapper\\" }"} '
                    "backend/tests/test_agentic_change_assessment_builder.py\n"
                )
                f.write(
                    '{"text":">>> APPROVAL REQUEST START"} '
                    "backend/tests/test_agentic_change_assessment_builder.py\n"
                )
                f.write(
                    '{"text":"[858] tool exec_command result: backend/tests/test_agentic_change_assessment_builder.py pytest output"}\n'
                )
                f.write(
                    '{"text":"\\\\n[908] tool write_stdin result: backend/tests/test_agentic_change_assessment_builder.py vite output"}\n'
                )
                f.write(
                    '{"text":"[794] user: 下面可以接入 Agent 了吗"} '
                    "backend/tests/test_agentic_change_assessment_builder.py\n"
                )
                f.write(
                    '{"text":"为 backend/tests/test_agentic_change_assessment_builder.py 增加 builder 评估回归测试，验证 codex evidence 会进入 Why。"}\n'
                )

            adapter = ChangeImpactAdapter(workspace_path=tmp_dir)
            adapter._git_status_lines = lambda: [" M backend/tests/test_agentic_change_assessment_builder.py"]
            adapter._load_graph_snapshot = lambda: {"modules": [], "dependencies": []}
            adapter._git_diff_for_file = lambda _file_path, staged=False: ""
            adapter._agent_log_candidates = lambda: [Path(log_path)]
            adapter._extract_changed_python_facts = lambda _file_path, _status: {
                "symbols": [],
                "functions": [],
                "classes": [],
                "routes": [],
                "changed_schemas": [],
                "changed_jobs": [],
                "affected_data_objects": [],
            }

            result = adapter.generate_change_analysis("ws_clean_logs")

        evidence = result["agent_activity_evidence"]
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["related_files"], ["backend/tests/test_agentic_change_assessment_builder.py"])
        self.assertIn("builder 评估回归测试", evidence[0]["summary"])
        self.assertNotIn("session_loop", evidence[0]["summary"])
        self.assertNotIn("The following is the Codex agent history", evidence[0]["summary"])
        self.assertNotIn("response.output_item.done", evidence[0]["summary"])
        self.assertNotIn("TRANSCRIPT START", evidence[0]["summary"])
        self.assertNotIn("TRANSCRIPT END", evidence[0]["summary"])
        self.assertNotIn("helpful assistant", evidence[0]["summary"])
        self.assertNotIn("requested the following action", evidence[0]["summary"])
        self.assertNotIn("exact planned action", evidence[0]["summary"])
        self.assertNotIn("Planned action JSON", evidence[0]["summary"])
        self.assertNotIn('"command"', evidence[0]["summary"])
        self.assertNotIn("justification", evidence[0]["summary"])
        self.assertNotIn("APPROVAL REQUEST", evidence[0]["summary"])
        self.assertNotIn("tool exec_command result", evidence[0]["summary"])
        self.assertNotIn("tool write_stdin result", evidence[0]["summary"])
        self.assertNotIn("[794] user", evidence[0]["summary"])

    def test_agent_log_candidates_include_codex_sqlite_logs(self):
        adapter = ChangeImpactAdapter(workspace_path="/tmp/demo")
        candidates = [path.name for path in adapter._agent_log_candidates()]

        self.assertIn("logs_2.sqlite", candidates)

    def test_text_from_agent_log_line_extracts_codex_desktop_text_payload(self):
        adapter = ChangeImpactAdapter(workspace_path="/tmp/demo")
        text = adapter._text_from_agent_log_line(
            'session_loop{thread_id=abc}: Submission sub=Submission { '
            'items: [Text { text: "请修改 backend/app/services/jobs/manager.py 的 rebuild 流程", '
            'kind: User }] }'
        )

        self.assertEqual(text, "请修改 backend/app/services/jobs/manager.py 的 rebuild 流程")

    def test_text_from_agent_log_line_prefers_informative_text_payloads(self):
        adapter = ChangeImpactAdapter(workspace_path="/tmp/demo")
        text = adapter._text_from_agent_log_line(
            'session_loop{thread_id=abc}: Submission sub=Submission { '
            'items: [Text { text: "The following is the Codex agent history whose request action you are assessing.", '
            'kind: User }, Text { text: "为 backend/tests/test_agentic_change_assessment_builder.py 增加 builder 评估回归测试。", '
            'kind: User }] }'
        )

        self.assertEqual(text, "为 backend/tests/test_agentic_change_assessment_builder.py 增加 builder 评估回归测试。")

    def test_agent_activity_evidence_does_not_match_generic_basenames(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.mkdir(os.path.join(tmp_dir, ".git"))
            log_path = os.path.join(tmp_dir, "history.jsonl")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write('{"text":"另一个项目里的 service.py 需要调整生命周期"}\n')

            adapter = ChangeImpactAdapter(workspace_path=tmp_dir)
            adapter._git_status_lines = lambda: [" M backend/app/services/workspace_snapshot/service.py"]
            adapter._load_graph_snapshot = lambda: {"modules": [], "dependencies": []}
            adapter._git_diff_for_file = lambda _file_path, staged=False: ""
            adapter._agent_log_candidates = lambda: [Path(log_path)]
            adapter._extract_changed_python_facts = lambda _file_path, _status: {
                "symbols": [],
                "functions": [],
                "classes": [],
                "routes": [],
                "changed_schemas": [],
                "changed_jobs": [],
                "affected_data_objects": [],
            }

            result = adapter.generate_change_analysis("ws_agent_logs")

        self.assertEqual(result["agent_activity_evidence"], [])

    def test_generate_change_analysis_separates_direct_and_transitive_impacts_using_graph_evidence(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.mkdir(os.path.join(tmp_dir, ".git"))
            adapter = ChangeImpactAdapter(workspace_path=tmp_dir)
            adapter._git_status_lines = lambda: [" M app/api/routes.py"]
            adapter._load_graph_snapshot = lambda: {
                "modules": [
                    {"module_id": "mod_app__api", "name": "api", "type": "router"},
                    {"module_id": "mod_app__services", "name": "services", "type": "service"},
                    {"module_id": "mod_app__repositories", "name": "repositories", "type": "repository"},
                ],
                "dependencies": [
                    {"from": "mod_app__api", "to": "mod_app__services", "type": "imports"},
                    {"from": "mod_app__services", "to": "mod_app__repositories", "type": "calls"},
                ],
            }
            adapter._extract_changed_python_facts = lambda file_path, status: {
                "symbols": ["list_orders"],
                "functions": ["list_orders"],
                "classes": [],
                "routes": ["GET /orders"],
                "changed_schemas": [],
                "changed_jobs": [],
                "affected_data_objects": [],
            }

            result = adapter.generate_change_analysis("ws_graph")

        self.assertEqual(result["directly_changed_modules"], ["mod_app__api"])
        self.assertEqual(result["transitively_affected_modules"], ["mod_app__repositories", "mod_app__services"])
        self.assertEqual([item["entity_id"] for item in result["direct_impacts"]], ["mod_app__api"])
        self.assertEqual(
            [item["entity_id"] for item in result["transitive_impacts"]],
            ["mod_app__repositories", "mod_app__services"],
        )
        self.assertTrue(all(item["reason"] == "direct_file_change" for item in result["direct_impacts"]))
        self.assertTrue(all(item["reason"] == "reachable_via_dependency_graph" for item in result["transitive_impacts"]))
        self.assertTrue(all(item["direction"] == "downstream_dependency" for item in result["transitive_impacts"]))
        self.assertTrue(all("entity_id" in item and "reason" in item for item in result["impact_reasons"]))
        self.assertEqual(result["impact_reasons"], result["why_impacted"])
        self.assertEqual(result["direct_impacts"][0]["evidence"]["files"], ["app/api/routes.py"])
        transitive_evidence = {item["entity_id"]: item for item in result["transitive_impacts"]}
        self.assertEqual(
            transitive_evidence["mod_app__services"]["evidence"]["by_direction"]["downstream_dependency"]["from_modules"],
            ["mod_app__api"],
        )
        self.assertEqual(
            transitive_evidence["mod_app__repositories"]["evidence"]["by_direction"]["downstream_dependency"]["from_modules"],
            ["mod_app__services"],
        )

    def test_generate_change_analysis_propagates_caller_side_transitive_impacts_from_repository_changes(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.mkdir(os.path.join(tmp_dir, ".git"))
            adapter = ChangeImpactAdapter(workspace_path=tmp_dir)
            adapter._git_status_lines = lambda: [" M app/repositories/order_repo.py"]
            adapter._load_graph_snapshot = lambda: {
                "modules": [
                    {"module_id": "mod_app__api", "name": "api", "type": "router"},
                    {"module_id": "mod_app__services", "name": "services", "type": "service"},
                    {"module_id": "mod_app__repositories", "name": "repositories", "type": "repository"},
                ],
                "dependencies": [
                    {"from": "mod_app__api", "to": "mod_app__services", "type": "imports"},
                    {"from": "mod_app__services", "to": "mod_app__repositories", "type": "calls"},
                ],
            }
            adapter._extract_changed_python_facts = lambda file_path, status: {
                "symbols": ["fetch_order"],
                "functions": ["fetch_order"],
                "classes": [],
                "routes": [],
                "changed_schemas": [],
                "changed_jobs": [],
                "affected_data_objects": [],
            }

            result = adapter.generate_change_analysis("ws_repo")

        self.assertEqual(result["directly_changed_modules"], ["mod_app__repositories"])
        transitive_by_id = {item["entity_id"]: item for item in result["transitive_impacts"]}
        self.assertEqual(sorted(transitive_by_id.keys()), ["mod_app__api", "mod_app__services"])
        self.assertTrue(all(item["direction"] == "upstream_dependent" for item in transitive_by_id.values()))
        self.assertEqual(
            transitive_by_id["mod_app__services"]["evidence"]["by_direction"]["upstream_dependent"]["from_modules"],
            ["mod_app__repositories"],
        )
        self.assertEqual(
            transitive_by_id["mod_app__api"]["evidence"]["by_direction"]["upstream_dependent"]["from_modules"],
            ["mod_app__services"],
        )
        self.assertTrue(all("direction" in item for item in result["transitive_impacts"]))


if __name__ == "__main__":
    unittest.main()
