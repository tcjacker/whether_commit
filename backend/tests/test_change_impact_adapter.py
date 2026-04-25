import os
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
