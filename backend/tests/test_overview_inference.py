import unittest
from types import SimpleNamespace

from app.schemas.overview import OverviewResponse
from app.services.capability_inference.service import CapabilityInferenceService
from app.services.overview_inference.agent_reasoning import AgentReasoningService
from app.services.overview_inference.service import OverviewInferenceService


class AgentReasoningServiceTest(unittest.TestCase):
    def test_analyze_returns_explicit_unknowns_without_change_facts(self):
        service = AgentReasoningService()

        result = service.analyze(
            graph_data={"modules": [], "dependencies": []},
            change_data={"changed_files": []},
            verification_data={"affected_tests": []},
        )

        self.assertEqual(result["technical_change_summary"], "未提供待分析的变更事实。")
        self.assertEqual(result["confidence"], "low")
        self.assertTrue(result["unknowns"])
        self.assertTrue(result["validation_gaps"])


class OverviewInferenceServiceTest(unittest.TestCase):
    def test_build_overview_includes_file_review_summaries_for_changed_files(self):
        service = OverviewInferenceService(agent_harness_service=None)

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_file_review",
            graph_data={
                "modules": [
                    {"module_id": "mod_overview_schema", "name": "overview_schema", "type": "schema"},
                    {"module_id": "mod_overview_service", "name": "overview_service", "type": "service"},
                ],
                "symbols": [],
                "routes": [{"method": "GET", "path": "/api/overview", "module": "mod_overview_schema"}],
                "dependencies": [],
            },
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（2 个文件）",
                "changed_files": [
                    "backend/app/schemas/overview.py",
                    "backend/app/services/overview_inference/test_asset_summary.py",
                ],
                "changed_routes": ["GET /api/overview"],
                "affected_entrypoints": ["GET /api/overview"],
                "changed_schemas": ["TestAssetSummary", "OverviewResponse"],
                "directly_changed_modules": ["mod_overview_schema", "mod_overview_service"],
                "linked_tests": ["backend/tests/test_overview_inference.py"],
                "agent_activity_evidence": [
                    {
                        "source": "codex",
                        "summary": "用户要求把测试资产管理接入 overview 首页，并按项目结构解释 diff 意义。",
                        "related_files": ["backend/app/schemas/overview.py"],
                    }
                ],
                "file_diff_stats": {
                    "backend/app/schemas/overview.py": {
                        "added_lines": 64,
                        "deleted_lines": 0,
                        "change_type": "additive contract",
                        "snippets": [
                            "class TestAssetSummary(BaseModel):",
                            "test_asset_summary: TestAssetSummary = TestAssetSummary()",
                        ],
                    }
                },
            },
            verification_data={
                "affected_tests": ["backend/tests/test_overview_inference.py::test_contract"],
                "verified_changed_paths": ["backend/app/schemas/overview.py"],
                "unverified_changed_paths": ["backend/app/services/overview_inference/test_asset_summary.py"],
                "missing_tests_for_changed_paths": ["backend/app/services/overview_inference/test_asset_summary.py"],
                "evidence_by_path": {
                    "backend/app/schemas/overview.py": {
                        "status": "report-backed",
                        "linked_tests": ["backend/tests/test_overview_inference.py::test_contract"],
                    }
                },
            },
        )

        summaries = result["file_review_summaries"]
        self.assertEqual(summaries[0]["path"], "backend/app/schemas/overview.py")
        self.assertEqual(summaries[0]["file_role"], "API schema")
        self.assertEqual(summaries[0]["diff_summary"], "+64 lines · additive contract")
        self.assertEqual(summaries[0]["related_entrypoints"], ["GET /api/overview"])
        self.assertIn("测试资产治理接入 overview 首页", summaries[0]["product_meaning"])
        self.assertEqual(
            summaries[0]["intent_evidence"],
            ["codex: 用户要求把测试资产管理接入 overview 首页，并按项目结构解释 diff 意义。"],
        )
        self.assertIn("backend/tests/test_overview_inference.py", summaries[0]["related_tests"])
        self.assertEqual(summaries[1]["path"], "backend/app/services/overview_inference/test_asset_summary.py")
        self.assertIn("规则事实", summaries[1]["product_meaning"])

    def test_build_overview_includes_test_asset_summary_for_changed_tests(self):
        service = OverviewInferenceService(agent_harness_service=None)

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_test_assets",
            graph_data={
                "modules": [
                    {"module_id": "mod_orders_api", "name": "orders_api", "type": "router"},
                    {"module_id": "mod_orders_service", "name": "orders_service", "type": "service"},
                ],
                "symbols": [],
                "routes": [{"method": "POST", "path": "/orders", "module": "mod_orders_api"}],
                "dependencies": [{"from": "mod_orders_api", "to": "mod_orders_service", "type": "calls"}],
            },
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（3 个文件）",
                "changed_files": [
                    "app/api/orders.py",
                    "app/services/orders.py",
                    "tests/test_orders.py",
                ],
                "changed_routes": ["POST /orders"],
                "affected_entrypoints": ["POST /orders"],
                "directly_changed_modules": ["mod_orders_api", "mod_orders_service"],
                "linked_tests": ["tests/test_orders.py"],
            },
            verification_data={
                "affected_tests": ["tests/test_orders.py::test_submit"],
                "verified_changed_paths": ["app/api/orders.py"],
                "unverified_changed_paths": ["app/services/orders.py"],
                "missing_tests_for_changed_paths": ["app/services/orders.py"],
                "evidence_by_path": {
                    "app/api/orders.py": {
                        "status": "report-backed",
                        "linked_tests": ["tests/test_orders.py::test_submit"],
                    },
                    "app/services/orders.py": {
                        "status": "no-evidence",
                        "linked_tests": [],
                    },
                    "tests/test_orders.py": {
                        "status": "test-file-present",
                        "linked_tests": ["tests/test_orders.py::test_submit"],
                    },
                },
            },
        )

        summary = result["test_asset_summary"]
        self.assertEqual(summary["health_status"], "needs_maintenance")
        self.assertEqual(summary["affected_test_count"], 1)
        self.assertEqual(summary["changed_test_file_count"], 1)
        self.assertEqual(summary["stale_or_invalid_test_count"], 1)
        self.assertIn("app/services/orders.py", summary["coverage_gaps"])
        self.assertEqual(summary["capability_coverage"][0]["business_capability"], "Orders")
        self.assertEqual(summary["capability_coverage"][0]["technical_entrypoints"], ["POST /orders"])
        self.assertEqual(summary["test_files"][0]["path"], "tests/test_orders.py")
        self.assertEqual(summary["test_files"][0]["maintenance_status"], "update")
        self.assertIn("app/services/orders.py", summary["test_files"][0]["covered_paths"])

    def test_build_overview_includes_change_risk_summary_shape(self):
        service = OverviewInferenceService(agent_harness_service=None)

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_shape",
            graph_data={"modules": [], "symbols": [], "routes": [], "dependencies": []},
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（1 个文件）",
                "changed_files": ["app/main.py"],
                "affected_entrypoints": ["GET /health"],
                "directly_changed_modules": ["mod_api"],
            },
            verification_data={
                "affected_tests": [],
                "verified_changed_paths": [],
                "unverified_changed_paths": ["app/main.py"],
                "missing_tests_for_changed_paths": ["app/main.py"],
                "critical_changed_paths": [],
            },
        )

        summary = result["change_risk_summary"]
        self.assertIn("headline", summary)
        self.assertIn("coverage", summary)
        self.assertIn("existing_feature_impact", summary)
        self.assertIn("risk_signals", summary)
        self.assertIn("overall_risk_level", summary["headline"])

    def test_build_overview_rejects_accepted_harness_with_untraceable_impact_basis(self):
        class StubHarnessService:
            def run(self, _graph_data, _change_data, _verification_data):
                return {
                    "status": "accepted",
                    "response": {
                        "status": "accepted",
                        "read_requests": [],
                        "project_summary": {
                            "overall_assessment": "Untraceable summary",
                            "impact_level": "high",
                            "impact_basis": [{"kind": "file", "value": "app/missing.py"}],
                        },
                        "capabilities": [],
                        "change_themes": [],
                        "recent_ai_changes": [],
                    },
                    "metadata": {"rounds_used": 1, "requests_used": 0},
                }

        service = OverviewInferenceService(agent_harness_service=StubHarnessService())

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_invalid_impact_basis",
            graph_data={"modules": [], "symbols": [], "routes": [], "dependencies": []},
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（1 个文件）",
                "changed_files": ["app/main.py"],
                "changed_symbols": ["handler"],
                "directly_changed_modules": ["mod_api"],
                "minimal_review_set": ["app/main.py"],
            },
            verification_data={"affected_tests": []},
        )

        self.assertEqual(result["agent_harness_status"], "validation_failed")
        self.assertEqual(result["recent_ai_changes"][0]["change_id"], "chg_latest")
        self.assertEqual(
            result["project_summary"]["overall_assessment"],
            result["change_risk_summary"]["headline"]["overall_risk_summary"],
        )
        self.assertIn("AGENT_HARNESS_FALLBACK: validation_failed", result["warnings"])

    def test_build_overview_computes_rule_based_risk_summary(self):
        service = OverviewInferenceService(agent_harness_service=None)

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_rule_summary",
            graph_data={
                "modules": [
                    {"module_id": "mod_orders_api", "name": "orders_api", "type": "router"},
                    {"module_id": "mod_orders_service", "name": "orders_service", "type": "service"},
                ],
                "symbols": [],
                "routes": [
                    {"method": "POST", "path": "/orders", "module": "mod_orders_api"},
                ],
                "dependencies": [
                    {"from": "mod_orders_api", "to": "mod_orders_service", "type": "calls"},
                ],
            },
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（2 个文件）",
                "changed_files": ["app/api/orders.py", "app/services/orders.py"],
                "changed_routes": ["POST /orders"],
                "affected_entrypoints": ["POST /orders"],
                "directly_changed_modules": ["mod_orders_api", "mod_orders_service"],
            },
            verification_data={
                "affected_tests": ["tests/test_orders.py::test_submit"],
                "verified_changed_paths": ["app/api/orders.py"],
                "unverified_changed_paths": ["app/services/orders.py"],
                "missing_tests_for_changed_paths": ["app/services/orders.py"],
                "critical_changed_paths": [{"path": "app/services/orders.py", "reason": "checkout"}],
                "verified_changed_modules": ["mod_orders_api"],
                "unverified_changed_modules": ["mod_orders_service"],
                "unverified_impacts": [{"entity_id": "mod_orders_service"}],
            },
        )

        summary = result["change_risk_summary"]
        self.assertEqual(summary["headline"]["overall_risk_level"], "high")
        self.assertEqual(summary["coverage"]["coverage_status"], "weakly_covered")
        self.assertIn("当前覆盖不足", summary["coverage"]["coverage_summary"])
        self.assertEqual(summary["existing_feature_impact"]["affected_capability_count"], 1)
        self.assertEqual(summary["existing_feature_impact"]["affected_capabilities"][0]["name"], "Orders")
        self.assertTrue(summary["risk_signals"])

    def test_build_overview_emits_progress_callbacks_from_internal_agent_phases(self):
        events = []

        class StubHarnessService:
            def run(self, _graph_data, _change_data, _verification_data, progress_reporter=None):
                if progress_reporter is not None:
                    progress_reporter("agent_round_1")
                    progress_reporter("agent_round_2")
                return {
                    "status": "accepted",
                    "response": {
                        "status": "accepted",
                        "read_requests": [],
                        "project_summary": {
                            "overall_assessment": "Harness progress summary",
                            "impact_level": "medium",
                            "impact_basis": [{"path": "app/main.py"}],
                        },
                        "capabilities": [],
                        "change_themes": [],
                        "recent_ai_changes": [],
                    },
                    "metadata": {"rounds_used": 2, "requests_used": 0},
                }

        service = OverviewInferenceService(agent_harness_service=StubHarnessService())

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_progress_callbacks",
            graph_data={"modules": [], "symbols": [], "routes": [], "dependencies": []},
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（1 个文件）",
                "changed_files": ["app/main.py"],
                "changed_symbols": ["handler"],
                "directly_changed_modules": ["mod_api"],
                "minimal_review_set": ["app/main.py"],
            },
            verification_data={"affected_tests": []},
            progress_reporter=events.append,
        )

        self.assertEqual(result["agent_harness_status"], "accepted")
        self.assertEqual(
            events,
            [
                "prepare_agent_context",
                "agent_round_1",
                "agent_round_2",
                "validate_agent_output",
                "build_overview_payload",
            ],
        )

    def test_build_overview_merges_agent_risk_copy_and_preserves_rule_level(self):
        class StubHarnessService:
            def run(self, _graph_data, _change_data, _verification_data, change_risk_summary=None, progress_reporter=None):
                return {
                    "status": "accepted",
                    "response": {
                        "status": "accepted",
                        "read_requests": [],
                        "project_summary": {
                            "overall_assessment": "Agent summary",
                            "impact_level": "medium",
                            "impact_basis": [{"path": "app/main.py"}],
                        },
                        "overall_risk_summary": "这次改动主要风险在未验证服务路径。",
                        "recommended_focus": ["优先补 app/main.py 对应测试"],
                        "business_impact_summary": "主要影响健康检查相关能力。",
                        "capabilities": [],
                        "change_themes": [],
                        "recent_ai_changes": [],
                    },
                    "metadata": {"rounds_used": 1, "requests_used": 0},
                }

        service = OverviewInferenceService(agent_harness_service=StubHarnessService())
        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_agent_merge",
            graph_data={"modules": [], "symbols": [], "routes": [], "dependencies": []},
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（1 个文件）",
                "changed_files": ["app/main.py"],
                "affected_entrypoints": ["GET /health"],
                "directly_changed_modules": ["mod_api"],
            },
            verification_data={
                "affected_tests": [],
                "verified_changed_paths": [],
                "unverified_changed_paths": ["app/main.py"],
                "missing_tests_for_changed_paths": ["app/main.py"],
                "critical_changed_paths": [],
            },
        )

        self.assertEqual(result["change_risk_summary"]["headline"]["overall_risk_level"], "unknown")
        self.assertEqual(
            result["change_risk_summary"]["headline"]["overall_risk_summary"],
            "这次改动主要风险在未验证服务路径。",
        )
        self.assertEqual(result["project_summary"]["overall_assessment"], "这次改动主要风险在未验证服务路径。")
        self.assertEqual(
            result["change_risk_summary"]["existing_feature_impact"]["business_impact_summary"],
            "主要影响健康检查相关能力。",
        )

    def test_build_overview_merges_agent_file_review_copy_without_overwriting_rule_facts(self):
        class StubHarnessService:
            def run(self, _graph_data, _change_data, _verification_data, change_risk_summary=None, progress_reporter=None):
                return {
                    "status": "accepted",
                    "response": {
                        "status": "accepted",
                        "read_requests": [],
                        "project_summary": {
                            "overall_assessment": "Agent summary",
                            "impact_level": "high",
                            "impact_basis": [{"path": "app/main.py"}],
                        },
                        "capabilities": [],
                        "change_themes": [],
                        "recent_ai_changes": [],
                        "file_review_summaries": [
                            {
                                "path": "app/main.py",
                                "product_meaning": "Agent 认为这个文件把健康检查能力暴露给首页用户。",
                                "review_focus": ["确认健康检查入口仍兼容旧调用方"],
                                "risk_level": "low",
                                "diff_summary": "Agent 不应该覆盖规则 diff",
                            },
                            {
                                "path": "app/hallucinated.py",
                                "product_meaning": "不应展示不存在的文件。",
                                "review_focus": ["不应合并"],
                            },
                        ],
                    },
                    "metadata": {"rounds_used": 1, "requests_used": 0},
                }

        service = OverviewInferenceService(agent_harness_service=StubHarnessService())
        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_agent_file_review",
            graph_data={"modules": [], "symbols": [], "routes": [], "dependencies": []},
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（1 个文件）",
                "changed_files": ["app/main.py"],
                "affected_entrypoints": ["GET /health"],
                "directly_changed_modules": ["mod_api"],
            },
            verification_data={
                "affected_tests": [],
                "verified_changed_paths": [],
                "unverified_changed_paths": ["app/main.py"],
                "missing_tests_for_changed_paths": ["app/main.py"],
                "critical_changed_paths": [],
            },
        )

        summary = result["file_review_summaries"][0]
        self.assertEqual(summary["path"], "app/main.py")
        self.assertEqual(summary["product_meaning"], "Agent 认为这个文件把健康检查能力暴露给首页用户。")
        self.assertEqual(summary["review_focus"], ["确认健康检查入口仍兼容旧调用方"])
        self.assertEqual(summary["risk_level"], "high")
        self.assertEqual(summary["diff_summary"], "changed file · code change")
        self.assertEqual(summary["generated_by"], "rules+agent")
        self.assertEqual(len(result["file_review_summaries"]), 1)

    def test_build_overview_falls_back_to_rule_copy_when_agent_fails(self):
        class StubHarnessService:
            def run(self, *_args, **_kwargs):
                return {"status": "fallback", "response": None, "metadata": {"validation_issues": ["timeout"]}}

        service = OverviewInferenceService(agent_harness_service=StubHarnessService())
        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_agent_fallback",
            graph_data={"modules": [], "symbols": [], "routes": [], "dependencies": []},
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（1 个文件）",
                "changed_files": ["app/main.py"],
                "affected_entrypoints": ["GET /health"],
                "directly_changed_modules": ["mod_api"],
            },
            verification_data={
                "affected_tests": [],
                "verified_changed_paths": [],
                "unverified_changed_paths": ["app/main.py"],
                "missing_tests_for_changed_paths": ["app/main.py"],
                "critical_changed_paths": [],
            },
        )

        self.assertEqual(result["agent_harness_status"], "fallback")
        self.assertTrue(result["change_risk_summary"]["headline"]["overall_risk_summary"])
        self.assertIsInstance(result["change_risk_summary"]["headline"]["recommended_focus"], list)
        self.assertEqual(
            result["project_summary"]["overall_assessment"],
            result["change_risk_summary"]["headline"]["overall_risk_summary"],
        )

    def test_build_overview_keeps_project_summary_mirrored_to_change_risk_summary(self):
        service = OverviewInferenceService(agent_harness_service=None)
        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_mirror",
            graph_data={"modules": [], "symbols": [], "routes": [], "dependencies": []},
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（1 个文件）",
                "changed_files": ["app/main.py"],
                "affected_entrypoints": ["GET /health"],
                "directly_changed_modules": ["mod_api"],
            },
            verification_data={
                "affected_tests": [],
                "verified_changed_paths": [],
                "unverified_changed_paths": ["app/main.py"],
                "missing_tests_for_changed_paths": ["app/main.py"],
                "critical_changed_paths": [],
            },
        )

        self.assertEqual(result["project_summary"]["impact_level"], result["change_risk_summary"]["headline"]["overall_risk_level"])
        self.assertEqual(
            result["project_summary"]["overall_assessment"],
            result["change_risk_summary"]["headline"]["overall_risk_summary"],
        )

    def test_build_overview_rejects_mixed_impact_basis_when_any_entry_is_untraceable(self):
        class StubHarnessService:
            def run(self, _graph_data, _change_data, _verification_data):
                return {
                    "status": "accepted",
                    "response": {
                        "status": "accepted",
                        "read_requests": [],
                        "project_summary": {
                            "overall_assessment": "Partially traceable summary",
                            "impact_level": "high",
                            "impact_basis": [
                                {"path": "app/main.py"},
                                {"kind": "file", "value": "app/missing.py"},
                            ],
                        },
                        "capabilities": [],
                        "change_themes": [],
                        "recent_ai_changes": [],
                    },
                    "metadata": {"rounds_used": 1, "requests_used": 0},
                }

        service = OverviewInferenceService(agent_harness_service=StubHarnessService())

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_mixed_invalid_basis",
            graph_data={"modules": [], "symbols": [], "routes": [], "dependencies": []},
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（1 个文件）",
                "changed_files": ["app/main.py"],
                "changed_symbols": ["handler"],
                "directly_changed_modules": ["mod_api"],
                "minimal_review_set": ["app/main.py"],
            },
            verification_data={"affected_tests": []},
        )

        self.assertEqual(result["agent_harness_status"], "validation_failed")
        self.assertIn("untraceable_impact_basis", result["agent_harness_metadata"]["validation_issues"])

    def test_build_overview_rejects_unrelated_module_basis_even_if_module_exists_in_repo_graph(self):
        class StubHarnessService:
            def run(self, _graph_data, _change_data, _verification_data):
                return {
                    "status": "accepted",
                    "response": {
                        "status": "accepted",
                        "read_requests": [],
                        "project_summary": {
                            "overall_assessment": "Repo-graph-only module summary",
                            "impact_level": "medium",
                            "impact_basis": [{"kind": "module", "target_id": "mod_repo_only"}],
                        },
                        "capabilities": [],
                        "change_themes": [],
                        "recent_ai_changes": [],
                    },
                    "metadata": {"rounds_used": 1, "requests_used": 0},
                }

        service = OverviewInferenceService(agent_harness_service=StubHarnessService())

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_unrelated_module_basis",
            graph_data={
                "modules": [
                    {"module_id": "mod_api", "name": "api", "type": "router"},
                    {"module_id": "mod_repo_only", "name": "repo_only", "type": "service"},
                ],
                "symbols": [],
                "routes": [],
                "dependencies": [],
            },
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（1 个文件）",
                "changed_files": ["app/main.py"],
                "changed_symbols": ["handler"],
                "directly_changed_modules": ["mod_api"],
                "minimal_review_set": ["app/main.py"],
            },
            verification_data={"affected_tests": []},
        )

        self.assertEqual(result["agent_harness_status"], "validation_failed")

    def test_build_overview_projects_recent_changes_from_change_themes(self):
        class StubHarnessService:
            def run(self, _graph_data, _change_data, _verification_data):
                return {
                    "status": "accepted",
                    "response": {
                        "status": "accepted",
                        "read_requests": [],
                        "project_summary": {
                            "overall_assessment": "Theme-backed summary",
                            "impact_level": "medium",
                            "impact_basis": [{"path": "app/main.py"}],
                        },
                        "capabilities": [],
                        "change_themes": [
                            {
                                "theme_key": "checkout",
                                "name": "Checkout flow",
                                "summary": "Order submission logic changed.",
                                "capability_keys": ["cap_checkout"],
                                "change_ids": ["chg_checkout"],
                            }
                        ],
                    },
                    "metadata": {"rounds_used": 1, "requests_used": 0},
                }

        service = OverviewInferenceService(agent_harness_service=StubHarnessService())

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_theme_projection",
            graph_data={"modules": [], "symbols": [], "routes": [], "dependencies": []},
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（1 个文件）",
                "changed_files": ["app/main.py"],
                "changed_symbols": ["handler"],
                "changed_routes": ["GET /health"],
                "directly_changed_modules": ["mod_api"],
                "minimal_review_set": ["app/main.py"],
            },
            verification_data={"affected_tests": []},
        )

        self.assertEqual(result["agent_harness_status"], "accepted")
        self.assertEqual(result["change_themes"][0]["theme_key"], "checkout")
        self.assertEqual(result["recent_ai_changes"][0]["change_id"], "chg_checkout")
        self.assertEqual(result["recent_ai_changes"][0]["change_title"], "Checkout flow")
        self.assertEqual(result["recent_ai_changes"][0]["summary"], "Order submission logic changed.")

    def test_build_overview_accepts_target_id_based_impact_basis(self):
        class StubHarnessService:
            def run(self, _graph_data, _change_data, _verification_data):
                return {
                    "status": "accepted",
                    "response": {
                        "status": "accepted",
                        "read_requests": [],
                        "project_summary": {
                            "overall_assessment": "Target-id backed summary",
                            "impact_level": "medium",
                            "impact_basis": [{"target_id": "app/main.py", "kind": "file"}],
                        },
                        "capabilities": [],
                        "change_themes": [],
                        "recent_ai_changes": [],
                    },
                    "metadata": {"rounds_used": 1, "requests_used": 0},
                }

        service = OverviewInferenceService(agent_harness_service=StubHarnessService())

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_target_id_basis",
            graph_data={"modules": [], "symbols": [], "routes": [], "dependencies": []},
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（1 个文件）",
                "changed_files": ["app/main.py"],
                "changed_symbols": ["handler"],
                "directly_changed_modules": ["mod_api"],
                "minimal_review_set": ["app/main.py"],
            },
            verification_data={"affected_tests": []},
        )

        self.assertEqual(result["agent_harness_status"], "accepted")
        self.assertEqual(result["project_summary"]["overall_assessment"], "Target-id backed summary")

    def test_build_overview_accepts_schema_and_job_based_impact_basis(self):
        class StubHarnessService:
            def run(self, _graph_data, _change_data, _verification_data):
                return {
                    "status": "accepted",
                    "response": {
                        "status": "accepted",
                        "read_requests": [],
                        "project_summary": {
                            "overall_assessment": "Schema and job summary",
                            "impact_level": "medium",
                            "impact_basis": [
                                {"kind": "schema", "target_id": "order_schema"},
                                {"kind": "job", "target_id": "nightly_sync"},
                            ],
                        },
                        "capabilities": [],
                        "change_themes": [],
                        "recent_ai_changes": [],
                    },
                    "metadata": {"rounds_used": 1, "requests_used": 0},
                }

        service = OverviewInferenceService(agent_harness_service=StubHarnessService())

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_schema_job_basis",
            graph_data={"modules": [], "symbols": [], "routes": [], "dependencies": []},
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（1 个文件）",
                "changed_files": ["app/main.py"],
                "changed_symbols": ["handler"],
                "changed_schemas": ["order_schema"],
                "changed_jobs": ["nightly_sync"],
                "directly_changed_modules": ["mod_api"],
                "minimal_review_set": ["app/main.py"],
            },
            verification_data={"affected_tests": []},
        )

        self.assertEqual(result["agent_harness_status"], "accepted")
        self.assertEqual(result["project_summary"]["overall_assessment"], "Schema and job summary")

    def test_build_overview_keeps_backward_compatible_accepted_when_impact_basis_is_empty(self):
        class StubHarnessService:
            def run(self, _graph_data, _change_data, _verification_data):
                return {
                    "status": "accepted",
                    "response": {
                        "status": "accepted",
                        "read_requests": [],
                        "project_summary": {
                            "overall_assessment": "Backward compatible summary",
                            "impact_level": "medium",
                            "impact_basis": [],
                        },
                        "capabilities": [],
                        "change_themes": [],
                        "recent_ai_changes": [],
                    },
                    "metadata": {"rounds_used": 1, "requests_used": 0},
                }

        service = OverviewInferenceService(agent_harness_service=StubHarnessService())

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_empty_basis",
            graph_data={"modules": [], "symbols": [], "routes": [], "dependencies": []},
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（1 个文件）",
                "changed_files": ["app/main.py"],
                "changed_symbols": ["handler"],
                "directly_changed_modules": ["mod_api"],
                "minimal_review_set": ["app/main.py"],
            },
            verification_data={"affected_tests": []},
        )

        self.assertEqual(result["agent_harness_status"], "accepted")
        self.assertEqual(result["project_summary"]["overall_assessment"], "Backward compatible summary")

    def test_build_overview_uses_agent_harness_recent_changes_when_accepted(self):
        class StubHarnessService:
            def run(self, _graph_data, _change_data, _verification_data):
                return {
                    "status": "accepted",
                    "response": {
                        "status": "accepted",
                        "read_requests": [],
                        "project_summary": {
                            "overall_assessment": "Agent harness accepted the source-backed summary.",
                            "impact_level": "medium",
                            "impact_basis": [{"path": "app/main.py"}],
                            "priority_themes": ["checkout"],
                        },
                        "capabilities": [],
                        "change_themes": [
                            {
                                "theme_key": "agent_change",
                                "name": "Agent harness synthesized change",
                                "summary": "Harness-specific narrative",
                                "capability_keys": ["cap_checkout"],
                                "change_ids": ["chg_agent"],
                            }
                        ],
                        "recent_ai_changes": [
                            {
                                "change_id": "chg_agent",
                                "change_title": "Agent harness synthesized change",
                                "summary": "Harness-specific narrative",
                                "changed_files": ["app/main.py"],
                                "changed_symbols": ["handler"],
                                "changed_routes": [],
                                "changed_schemas": [],
                                "changed_jobs": [],
                                "change_types": ["flow_change"],
                                "directly_changed_modules": ["mod_api"],
                                "transitively_affected_modules": [],
                                "affected_entrypoints": ["GET /health"],
                                "affected_data_objects": [],
                                "why_impacted": "Harness traced the route impact.",
                                "impact_reasons": ["Harness traced the route impact."],
                                "direct_impacts": ["mod_api"],
                                "transitive_impacts": [],
                                "risk_factors": [],
                                "review_recommendations": ["app/main.py"],
                                "linked_tests": [],
                                "verification_coverage": "missing",
                                "confidence": "medium",
                            }
                        ],
                    },
                    "metadata": {"rounds_used": 1, "requests_used": 0},
                }

        service = OverviewInferenceService(agent_harness_service=StubHarnessService())

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_harness_accepted",
            graph_data={"modules": [], "symbols": [], "routes": [], "dependencies": []},
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（1 个文件）",
                "changed_files": ["app/main.py"],
                "changed_symbols": ["handler"],
                "directly_changed_modules": ["mod_api"],
                "minimal_review_set": ["app/main.py"],
            },
            verification_data={"affected_tests": []},
        )

        self.assertEqual(result["agent_harness_status"], "accepted")
        self.assertEqual(result["project_summary"]["overall_assessment"], "Agent harness accepted the source-backed summary.")
        self.assertEqual(result["change_themes"][0]["theme_key"], "agent_change")
        self.assertEqual(result["recent_ai_changes"][0]["change_id"], "chg_agent")
        self.assertEqual(result["recent_ai_changes"][0]["change_title"], "Agent harness synthesized change")

    def test_build_overview_keeps_source_recent_changes_when_accepted_has_no_change_records(self):
        class StubHarnessService:
            def run(self, _graph_data, _change_data, _verification_data):
                return {
                    "status": "accepted",
                    "response": {
                        "status": "accepted",
                        "read_requests": [],
                        "project_summary": {
                            "overall_assessment": "Accepted without explicit change records",
                            "impact_level": "medium",
                            "impact_basis": [{"path": "app/main.py"}],
                        },
                        "capabilities": [],
                        "change_themes": [],
                        "recent_ai_changes": [],
                    },
                    "metadata": {"rounds_used": 1, "requests_used": 0},
                }

        service = OverviewInferenceService(agent_harness_service=StubHarnessService())

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_keep_source_recent",
            graph_data={"modules": [], "symbols": [], "routes": [], "dependencies": []},
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（1 个文件）",
                "changed_files": ["app/main.py"],
                "changed_symbols": ["handler"],
                "directly_changed_modules": ["mod_api"],
                "minimal_review_set": ["app/main.py"],
            },
            verification_data={"affected_tests": []},
        )

        self.assertEqual(result["agent_harness_status"], "accepted")
        self.assertEqual(result["recent_ai_changes"][0]["change_id"], "chg_latest")

    def test_build_overview_drops_malformed_harness_recent_changes_without_breaking_response(self):
        class StubHarnessService:
            def run(self, _graph_data, _change_data, _verification_data):
                return {
                    "status": "accepted",
                    "response": {
                        "status": "accepted",
                        "read_requests": [],
                        "project_summary": {
                            "overall_assessment": "Accepted with malformed legacy records",
                            "impact_level": "medium",
                            "impact_basis": [{"path": "app/main.py"}],
                        },
                        "capabilities": [],
                        "change_themes": [
                            {
                                "theme_key": "checkout",
                                "name": "Checkout flow",
                                "summary": "Order submission logic changed.",
                                "capability_keys": ["cap_checkout"],
                                "change_ids": ["chg_checkout"],
                            }
                        ],
                        "recent_ai_changes": [{"change_id": "broken_only"}],
                    },
                    "metadata": {"rounds_used": 1, "requests_used": 0},
                }

        service = OverviewInferenceService(agent_harness_service=StubHarnessService())

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_malformed_recent",
            graph_data={"modules": [], "symbols": [], "routes": [], "dependencies": []},
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（1 个文件）",
                "changed_files": ["app/main.py"],
                "changed_symbols": ["handler"],
                "directly_changed_modules": ["mod_api"],
                "minimal_review_set": ["app/main.py"],
            },
            verification_data={"affected_tests": []},
        )

        overview = OverviewResponse(**result)
        self.assertEqual(overview.recent_ai_changes[0].change_id, "chg_checkout")
        self.assertEqual(overview.recent_ai_changes[0].change_title, "Checkout flow")

    def test_build_overview_uses_valid_legacy_recent_changes_when_themes_are_absent(self):
        class StubHarnessService:
            def run(self, _graph_data, _change_data, _verification_data):
                return {
                    "status": "accepted",
                    "response": {
                        "status": "accepted",
                        "read_requests": [],
                        "project_summary": {
                            "overall_assessment": "Legacy-only summary",
                            "impact_level": "medium",
                            "impact_basis": [{"path": "app/main.py"}],
                        },
                        "capabilities": [],
                        "change_themes": [],
                        "recent_ai_changes": [
                            {
                                "change_id": "chg_agent_legacy",
                                "change_title": "Agent legacy change",
                                "summary": "Legacy-compatible accepted output",
                                "changed_files": ["app/main.py"],
                                "changed_symbols": ["handler"],
                                "changed_routes": [],
                                "changed_schemas": [],
                                "changed_jobs": [],
                                "change_types": ["flow_change"],
                                "directly_changed_modules": ["mod_api"],
                                "transitively_affected_modules": [],
                                "affected_entrypoints": [],
                                "affected_data_objects": [],
                                "why_impacted": "Agent legacy reasoning.",
                                "impact_reasons": ["Agent legacy reasoning."],
                                "direct_impacts": ["mod_api"],
                                "transitive_impacts": [],
                                "risk_factors": [],
                                "review_recommendations": ["app/main.py"],
                                "linked_tests": [],
                                "verification_coverage": "missing",
                                "confidence": "medium",
                            }
                        ],
                    },
                    "metadata": {"rounds_used": 1, "requests_used": 0},
                }

        service = OverviewInferenceService(agent_harness_service=StubHarnessService())

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_legacy_recent_changes",
            graph_data={"modules": [], "symbols": [], "routes": [], "dependencies": []},
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（1 个文件）",
                "changed_files": ["app/main.py"],
                "changed_symbols": ["handler"],
                "directly_changed_modules": ["mod_api"],
                "minimal_review_set": ["app/main.py"],
            },
            verification_data={"affected_tests": []},
        )

        self.assertEqual(result["agent_harness_status"], "accepted")
        self.assertEqual(result["recent_ai_changes"][0]["change_id"], "chg_agent_legacy")
        self.assertEqual(result["recent_ai_changes"][0]["change_title"], "Agent legacy change")

    def test_build_overview_uses_provider_backed_reasoning_when_available(self):
        class StubReasoningService:
            def analyze(self, _graph_data, _change_data, _verification_data):
                return {
                    "technical_change_summary": "provider summary",
                    "change_types": ["code_modification"],
                    "risk_factors": [],
                    "review_recommendations": ["app/main.py"],
                    "why_impacted": "provider reasoning",
                    "confidence": "medium",
                    "unknowns": [],
                    "validation_gaps": [],
                    "llm_reasoning": {"enabled": True, "status": "accepted", "validation_issues": []},
                }

        service = OverviewInferenceService(agent_reasoning_service=StubReasoningService())

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_provider",
            graph_data={"modules": [], "symbols": [], "routes": [], "dependencies": []},
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（1 个文件）",
                "changed_files": ["app/main.py"],
                "changed_symbols": ["handler"],
                "directly_changed_modules": ["mod_api"],
                "minimal_review_set": ["app/main.py"],
            },
            verification_data={"affected_tests": []},
        )

        self.assertEqual(result["recent_ai_changes"][0]["summary"], "provider summary")
        self.assertEqual(result["project_summary"]["agent_reasoning"]["llm_reasoning"]["status"], "accepted")

    def test_build_overview_keeps_displayable_fallback_contract_for_harness_failures(self):
        class StubHarnessService:
            def run(self, _graph_data, _change_data, _verification_data):
                return {
                    "status": "validation_failed",
                    "response": None,
                    "metadata": {
                        "rounds_used": 1,
                        "requests_used": 0,
                        "validation_issues": ["missing"],
                    },
                }

        service = OverviewInferenceService(agent_harness_service=StubHarnessService())

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_harness_fallback",
            graph_data={
                "modules": [{"module_id": "mod_api", "name": "api", "type": "router"}],
                "symbols": [{"symbol_id": "sym_handler"}],
                "routes": [{"method": "GET", "path": "/health"}],
                "dependencies": [],
            },
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（1 个文件）",
                "changed_files": ["app/main.py"],
                "changed_symbols": ["handler"],
                "changed_routes": ["GET /health"],
                "directly_changed_modules": ["mod_api"],
                "minimal_review_set": ["app/main.py"],
            },
            verification_data={"affected_tests": []},
        )

        self.assertEqual(result["agent_harness_status"], "validation_failed")
        self.assertEqual(result["change_themes"], [])
        self.assertEqual(result["recent_ai_changes"][0]["change_id"], "chg_latest")
        self.assertTrue(result["project_summary"]["what_this_app_seems_to_do"])
        self.assertEqual(
            result["project_summary"]["overall_assessment"],
            result["change_risk_summary"]["headline"]["overall_risk_summary"],
        )
        self.assertIn("AGENT_HARNESS_FALLBACK: validation_failed", result["warnings"])

    def test_build_overview_surfaces_provider_fallback_warning(self):
        class StubReasoningService:
            def analyze(self, _graph_data, _change_data, _verification_data):
                return {
                    "technical_change_summary": "local summary",
                    "change_types": ["code_modification"],
                    "risk_factors": [],
                    "review_recommendations": ["app/main.py"],
                    "why_impacted": "local reasoning",
                    "confidence": "low",
                    "unknowns": [],
                    "validation_gaps": [],
                    "llm_reasoning": {
                        "enabled": True,
                        "status": "provider_error",
                        "validation_issues": ["provider_exception"],
                    },
                }

        service = OverviewInferenceService(agent_reasoning_service=StubReasoningService())

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_provider_fallback",
            graph_data={"modules": [], "symbols": [], "routes": [], "dependencies": []},
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（1 个文件）",
                "changed_files": ["app/main.py"],
                "changed_symbols": ["handler"],
                "directly_changed_modules": ["mod_api"],
                "minimal_review_set": ["app/main.py"],
            },
            verification_data={"affected_tests": []},
        )

        self.assertIn("LLM_REASONING_FALLBACK: provider_error", result["warnings"])

    def test_overview_response_preserves_agent_reasoning_and_validation_gaps(self):
        overview = OverviewResponse(
            repo={"repo_key": "demo", "name": "demo", "default_branch": "main"},
            snapshot={
                "base_commit_sha": "HEAD",
                "workspace_snapshot_id": "ws_1",
                "has_pending_changes": True,
                "status": "ready",
                "generated_at": "2026-04-11T00:00:00+00:00",
            },
            project_summary={
                "what_this_app_seems_to_do": "正在对后端系统进行技术分析",
                "technical_narrative": "仅基于源代码事实完成分析。",
                "core_flow": "Client -> API Handler -> Service",
                "agent_reasoning": {
                    "technical_change_summary": "1 files changed; 1 symbols and 1 routes were implicated.",
                    "change_types": ["flow_change"],
                    "risk_factors": ["变更路径未关联到带报告的验证证据。"],
                    "review_recommendations": ["app/main.py"],
                    "why_impacted": "Changed symbols: handler",
                    "confidence": "low",
                    "unknowns": ["变更面的验证证据较弱或缺失。"],
                    "validation_gaps": ["变更文件缺少带报告的测试证据。"],
                },
            },
            verification_status={
                "build": {"status": "unknown"},
                "unit_tests": {"status": "unknown"},
                "integration_tests": {"status": "unknown"},
                "scenario_replay": {"status": "unknown"},
                "critical_paths": [],
                "unverified_areas": [],
                "verified_changed_modules": [],
                "unverified_changed_modules": [],
                "affected_tests": [],
                "verified_changed_paths": [],
                "unverified_changed_paths": [],
                "verified_impacts": [],
                "unverified_impacts": [],
                "missing_tests_for_changed_paths": [],
                "critical_changed_paths": [],
                "evidence_by_path": {},
            },
            recent_ai_changes=[
                {
                    "change_id": "chg_latest",
                    "change_title": "工作区差异（1 个文件）",
                    "summary": "1 files changed; 1 symbols and 1 routes were implicated.",
                    "changed_files": ["app/main.py"],
                    "changed_symbols": ["handler"],
                    "changed_routes": ["GET /health"],
                    "changed_schemas": [],
                    "changed_jobs": [],
                    "change_types": ["flow_change"],
                    "directly_changed_modules": ["mod_api"],
                    "transitively_affected_modules": ["mod_services"],
                    "affected_entrypoints": [],
                    "affected_data_objects": [],
                    "why_impacted": "Changed symbols: handler",
                    "impact_reasons": ["Changed symbols: handler"],
                    "direct_impacts": ["mod_api"],
                    "transitive_impacts": ["mod_services"],
                    "risk_factors": ["变更路径未关联到带报告的验证证据。"],
                    "review_recommendations": ["app/main.py"],
                    "linked_tests": [],
                    "verification_coverage": "missing",
                    "confidence": "low",
                }
            ],
            warnings=["变更面的验证证据较弱或缺失。"],
        )

        self.assertEqual(
            overview.project_summary.agent_reasoning.validation_gaps,
            ["变更文件缺少带报告的测试证据。"],
        )
        self.assertEqual(overview.recent_ai_changes[0].impact_reasons, ["Changed symbols: handler"])
        self.assertEqual(overview.recent_ai_changes[0].direct_impacts, ["mod_api"])
        self.assertEqual(overview.recent_ai_changes[0].transitive_impacts, ["mod_services"])

    def test_build_overview_surfaces_richer_reasoning_details(self):
        service = OverviewInferenceService()

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_1",
            graph_data={
                "modules": [{"module_id": "mod_api", "name": "api", "type": "router"}],
                "symbols": [{"symbol_id": "sym_handler"}],
                "routes": [{"method": "GET", "path": "/health"}],
                "dependencies": [{"from": "mod_api", "to": "mod_services", "type": "imports"}],
            },
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（1 个文件）",
                "changed_files": ["app/main.py"],
                "changed_symbols": ["handler"],
                "changed_routes": ["GET /health"],
                "directly_changed_modules": ["mod_api"],
                "transitively_affected_modules": ["mod_services"],
                "minimal_review_set": ["app/main.py"],
                "linked_tests": [],
            },
            verification_data={"affected_tests": []},
        )

        self.assertIn("agent_reasoning", result["project_summary"])
        self.assertIn("validation_gaps", result["project_summary"]["agent_reasoning"])
        self.assertIn("impact_reasons", result["recent_ai_changes"][0])
        self.assertIn("direct_impacts", result["recent_ai_changes"][0])
        self.assertIn("transitive_impacts", result["recent_ai_changes"][0])
        self.assertIn("变更文件缺少带报告的测试证据。", result["warnings"])

    def test_overview_response_accepts_richer_verification_binding_fields(self):
        overview = OverviewResponse(
            repo={"repo_key": "demo", "name": "demo", "default_branch": "main"},
            snapshot={
                "base_commit_sha": "HEAD",
                "workspace_snapshot_id": "ws_1",
                "has_pending_changes": True,
                "status": "ready",
                "generated_at": "2026-04-11T00:00:00+00:00",
            },
            project_summary={"what_this_app_seems_to_do": "正在对后端系统进行技术分析"},
            capability_map=[],
            journeys=[],
            architecture_overview={"nodes": [], "edges": []},
            recent_ai_changes=[],
            verification_status={
                "build": {"status": "unknown"},
                "unit_tests": {"status": "passed"},
                "integration_tests": {"status": "unknown"},
                "scenario_replay": {"status": "unknown"},
                "critical_paths": [],
                "unverified_areas": [],
                "verified_changed_modules": ["mod_app__api"],
                "unverified_changed_modules": ["mod_app__services"],
                "affected_tests": ["tests/test_api.py"],
                "verified_changed_paths": ["app/api/routes.py"],
                "unverified_changed_paths": ["app/services/order_service.py"],
                "verified_impacts": [{"entity_id": "mod_app__api", "reason": "direct_file_change"}],
                "unverified_impacts": [{"entity_id": "mod_app__services", "reason": "missing_report_backed_evidence"}],
                "missing_tests_for_changed_paths": ["app/services/order_service.py"],
                "critical_changed_paths": [{"path": "app/services/order_service.py", "reason": "missing_report_backed_evidence"}],
                "evidence_by_path": {"app/api/routes.py": {"status": "report-backed"}},
            },
            warnings=[],
        )

        self.assertEqual(overview.verification_status.verified_changed_paths, ["app/api/routes.py"])
        self.assertEqual(overview.verification_status.unverified_impacts[0]["entity_id"], "mod_app__services")

    def test_overview_response_accepts_test_asset_summary(self):
        overview = OverviewResponse(
            repo={"repo_key": "demo", "name": "demo", "default_branch": "main"},
            snapshot={
                "base_commit_sha": "HEAD",
                "workspace_snapshot_id": "ws_tests",
                "has_pending_changes": True,
                "status": "ready",
                "generated_at": "2026-04-24T00:00:00+00:00",
            },
            project_summary={"what_this_app_seems_to_do": "正在对后端系统进行技术分析"},
            test_asset_summary={
                "health_status": "needs_maintenance",
                "total_test_file_count": 1,
                "affected_test_count": 1,
                "changed_test_file_count": 1,
                "stale_or_invalid_test_count": 1,
                "duplicate_or_low_value_test_count": 0,
                "coverage_gaps": ["app/services/orders.py"],
                "recommended_actions": ["更新或淘汰疑似失效的测试资产。"],
                "capability_coverage": [
                    {
                        "capability_key": "orders.submit",
                        "business_capability": "订单提交",
                        "coverage_status": "partial",
                        "technical_entrypoints": ["POST /orders"],
                        "covered_paths": ["app/api/orders.py", "app/services/orders.py"],
                        "covering_tests": ["tests/test_orders.py::test_submit"],
                        "gaps": ["app/services/orders.py"],
                        "maintenance_recommendation": "补齐缺口路径，并确认现有测试仍覆盖真实业务入口。",
                    }
                ],
                "test_files": [
                    {
                        "path": "tests/test_orders.py",
                        "maintenance_status": "update",
                        "covered_capabilities": ["订单提交"],
                        "covered_paths": ["app/api/orders.py", "app/services/orders.py"],
                        "linked_entrypoints": ["POST /orders"],
                        "invalidation_reasons": ["关联业务路径仍有未覆盖或未验证的变更。"],
                        "recommendation": "更新该测试，使它覆盖当前变更后的真实业务路径。",
                        "evidence_status": "test-file-present",
                    }
                ],
            },
        )

        self.assertEqual(overview.test_asset_summary.health_status, "needs_maintenance")
        self.assertEqual(overview.test_asset_summary.capability_coverage[0].business_capability, "订单提交")
        self.assertEqual(overview.test_asset_summary.test_files[0].maintenance_status, "update")

    def test_overview_response_preserves_agent_harness_fields(self):
        overview = OverviewResponse(
            repo={"repo_key": "demo", "name": "demo", "default_branch": "main"},
            snapshot={
                "base_commit_sha": "HEAD",
                "workspace_snapshot_id": "ws_harness",
                "has_pending_changes": True,
                "status": "ready",
                "generated_at": "2026-04-11T00:00:00+00:00",
            },
            project_summary={
                "what_this_app_seems_to_do": "正在对后端系统进行技术分析",
                "overall_assessment": "Harness fallback summary",
            },
            recent_ai_changes=[],
            change_themes=[
                {
                    "theme_key": "checkout",
                    "name": "Checkout flow",
                    "summary": "Order submission logic changed.",
                    "capability_keys": ["cap_checkout"],
                    "change_ids": ["chg_agent"],
                }
            ],
            agent_harness_status="timeout",
            agent_harness_metadata={"rounds_used": 2, "validation_issues": ["timeout"]},
        )

        self.assertEqual(overview.agent_harness_status, "timeout")
        self.assertEqual(overview.change_themes[0].theme_key, "checkout")
        self.assertEqual(overview.agent_harness_metadata["rounds_used"], 2)

    def test_build_overview_accepts_structured_impact_items(self):
        service = OverviewInferenceService()

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_1",
            graph_data={
                "modules": [{"module_id": "mod_api", "name": "api", "type": "router"}],
                "symbols": [{"symbol_id": "sym_handler"}],
                "routes": [{"method": "GET", "path": "/health"}],
                "dependencies": [{"from": "mod_api", "to": "mod_services", "type": "imports"}],
            },
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（1 个文件）",
                "changed_files": ["app/main.py"],
                "changed_symbols": ["handler"],
                "changed_routes": ["GET /health"],
                "directly_changed_modules": ["mod_api"],
                "transitively_affected_modules": ["mod_services"],
                "impact_reasons": [
                    {
                        "entity_id": "mod_api",
                        "reason": "direct edit",
                        "evidence": ["app/main.py"],
                        "distance": 0,
                        "direction": "direct",
                    }
                ],
                "direct_impacts": [
                    {
                        "entity_id": "mod_api",
                        "reason": "contains changed handler",
                        "evidence": ["app/main.py"],
                        "distance": 0,
                        "direction": "direct",
                    }
                ],
                "transitive_impacts": [
                    {
                        "entity_id": "mod_services",
                        "reason": "depends on mod_api",
                        "evidence": ["mod_api -> mod_services"],
                        "distance": 1,
                        "direction": "transitive",
                    }
                ],
                "minimal_review_set": ["app/main.py"],
                "linked_tests": [],
            },
            verification_data={"affected_tests": []},
        )

        overview = OverviewResponse(**result)
        self.assertEqual(overview.recent_ai_changes[0].direct_impacts[0].entity_id, "mod_api")
        self.assertEqual(overview.recent_ai_changes[0].transitive_impacts[0].distance, 1)
        self.assertEqual(overview.recent_ai_changes[0].impact_reasons[0].reason, "direct edit")
        self.assertEqual(overview.project_summary.agent_reasoning.validation_gaps[0], "变更文件缺少带报告的测试证据。")

    def test_build_overview_uses_technical_summary_for_backend_repo(self):
        service = OverviewInferenceService()

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_1",
            graph_data={
                "modules": [{"module_id": "mod_api", "name": "api", "type": "router"}],
                "symbols": [{"symbol_id": "sym_handler"}],
                "routes": [{"method": "GET", "path": "/health"}],
                "dependencies": [{"from": "mod_api", "to": "mod_services", "type": "imports"}],
            },
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（1 个文件）",
                "changed_files": ["app/main.py"],
                "changed_symbols": ["handler"],
                "changed_routes": ["GET /health"],
                "directly_changed_modules": ["mod_api"],
                "transitively_affected_modules": ["mod_services"],
                "minimal_review_set": ["app/main.py"],
                "linked_tests": [],
            },
            verification_data={"affected_tests": []},
        )

        self.assertEqual(result["capability_map"], [])
        self.assertEqual(result["journeys"], [])
        self.assertEqual(result["project_summary"]["what_this_app_seems_to_do"], "正在对后端系统进行技术分析")
        self.assertIn("technical_narrative", result["project_summary"])
        self.assertIn("agent_reasoning", result["project_summary"])
        self.assertEqual(result["project_summary"]["agent_reasoning"]["confidence"], "low")
        self.assertEqual(result["architecture_overview"]["nodes"][0]["id"], "mod_api")
        self.assertEqual(result["architecture_overview"]["edges"][0]["source"], "mod_api")

    def test_build_overview_populates_capability_map_when_evidence_is_sufficient(self):
        service = OverviewInferenceService(
            capability_inference_service=CapabilityInferenceService(),
        )

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_capability",
            graph_data={
                "modules": [
                    {"module_id": "mod_app__api", "name": "api", "type": "router"},
                    {"module_id": "mod_app__services", "name": "services", "type": "service"},
                ],
                "symbols": [],
                "routes": [
                    {"method": "GET", "path": "/orders", "module": "mod_app__api"},
                ],
                "dependencies": [{"from": "mod_app__api", "to": "mod_app__services", "type": "calls"}],
            },
            change_data={
                "base_commit_sha": "HEAD",
                "change_title": "工作区差异（1 个文件）",
                "changed_files": ["app/api/orders.py"],
                "changed_symbols": ["list_orders"],
                "changed_routes": ["GET /orders"],
                "directly_changed_modules": ["mod_app__api"],
                "transitively_affected_modules": ["mod_app__services"],
                "minimal_review_set": ["app/api/orders.py"],
                "linked_tests": [],
            },
            verification_data={"affected_tests": [], "unverified_impacts": [{"entity_id": "mod_app__services"}]},
        )

        self.assertEqual(len(result["capability_map"]), 1)
        self.assertEqual(result["capability_map"][0]["status"], "recently_changed")

    def test_build_clean_overview_marks_no_pending_changes(self):
        service = OverviewInferenceService()
        snapshot = SimpleNamespace(
            base_commit_sha="HEAD",
            workspace_snapshot_id="ws_clean_1",
        )

        result = service.build_clean_overview("demo", snapshot)

        self.assertFalse(result["snapshot"]["has_pending_changes"])
        self.assertEqual(result["warnings"], ["NO_PENDING_CHANGES"])
        self.assertEqual(result["recent_ai_changes"], [])


if __name__ == "__main__":
    unittest.main()
