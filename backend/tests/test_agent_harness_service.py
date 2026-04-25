import unittest

from app.services.overview_inference.agent_harness import AgentContextHarness
from app.services.overview_inference.service import OverviewInferenceService


class AgentHarnessServiceTest(unittest.TestCase):
    def setUp(self):
        self.graph_data = {
            "modules": [{"module_id": "mod_orders", "name": "orders", "type": "service"}],
            "symbols": [{"symbol_id": "OrderService.submit", "name": "OrderService.submit", "module_id": "mod_orders"}],
            "routes": [{"method": "POST", "path": "/orders"}],
            "dependencies": [{"from": "mod_api", "to": "mod_orders", "type": "calls"}],
        }
        self.change_data = {
            "base_commit_sha": "HEAD",
            "change_title": "工作区差异（1 个文件）",
            "changed_files": ["app/orders.py"],
            "changed_symbols": ["OrderService.submit"],
            "changed_routes": ["POST /orders"],
            "directly_changed_modules": ["mod_orders"],
            "transitively_affected_modules": [],
            "minimal_review_set": ["app/orders.py"],
            "file_contexts": {
                "app/orders.py": {
                    "path": "app/orders.py",
                    "snippet": "def submit_order():\n    return persist_order()",
                }
            },
        }
        self.verification_data = {
            "affected_tests": ["backend/tests/test_orders.py"],
            "missing_tests_for_changed_paths": [],
            "evidence_by_path": {
                "app/orders.py": {
                    "status": "report-backed",
                    "tests": ["backend/tests/test_orders.py"],
                }
            },
        }

    def test_build_overview_completes_second_round_after_context_reads(self):
        provider_calls = []

        def provider(payload):
            provider_calls.append(payload)
            if payload["round"] == 1:
                self.assertIn("app/orders.py", payload["manifest"]["file"])
                self.assertIn("OrderService.submit", payload["manifest"]["symbol"])
                return {
                    "status": "needs_more_context",
                    "read_requests": [
                        {
                            "target_type": "file",
                            "target_id": "app/orders.py",
                            "reason": "Need the changed file body",
                        },
                        {
                            "target_type": "verification_context",
                            "target_id": "app/orders.py",
                            "reason": "Need verification evidence",
                        },
                    ],
                }

            requested = {
                (item["target_type"], item["target_id"]): item["content"] for item in payload["requested_context"]
            }
            self.assertIn(("file", "app/orders.py"), requested)
            self.assertIn(("verification_context", "app/orders.py"), requested)
            self.assertEqual(requested[("file", "app/orders.py")]["path"], "app/orders.py")
            self.assertEqual(requested[("verification_context", "app/orders.py")]["status"], "report-backed")
            return {
                "status": "accepted",
                "read_requests": [],
                "project_summary": {
                    "overall_assessment": "Orders submit path changed with test-backed evidence.",
                    "impact_level": "medium",
                    "impact_basis": [{"target_id": "app/orders.py", "kind": "file"}],
                    "affected_entrypoints": ["POST /orders"],
                    "critical_paths": ["POST /orders -> OrderService.submit"],
                    "verification_gaps": [],
                    "priority_themes": ["orders-submit"],
                },
                "capabilities": [],
                "change_themes": [
                    {
                        "theme_key": "orders-submit",
                        "name": "Orders submit",
                        "summary": "Order submission flow changed.",
                    }
                ],
                "recent_ai_changes": [],
            }

        service = OverviewInferenceService(
            agent_harness_service=AgentContextHarness(provider=provider, max_rounds=2, max_read_requests=2)
        )

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_harness",
            graph_data=self.graph_data,
            change_data=self.change_data,
            verification_data=self.verification_data,
        )

        self.assertEqual(result["agent_harness_status"], "accepted")
        self.assertEqual(result["agent_harness_metadata"]["rounds_used"], 2)
        self.assertEqual(result["agent_harness_metadata"]["requests_used"], 2)
        self.assertEqual(result["project_summary"]["overall_assessment"], "Orders submit path changed with test-backed evidence.")
        self.assertEqual(result["change_themes"][0]["theme_key"], "orders-submit")
        self.assertEqual(len(provider_calls), 2)
        self.assertIn("coverage_summary", provider_calls[0]["facts"])
        self.assertIn("impacted_capabilities", provider_calls[0]["facts"])
        self.assertIn("risk_signals", provider_calls[0]["facts"])
        self.assertIn("top_unverified_paths", provider_calls[0]["facts"])

    def test_agent_harness_emits_progress_callbacks_for_each_round(self):
        events = []

        def provider(payload):
            if payload["round"] == 1:
                return {
                    "status": "needs_more_context",
                    "read_requests": [
                        {
                            "target_type": "file",
                            "target_id": "app/orders.py",
                            "reason": "Need the changed file body",
                        }
                    ],
                }

            return {
                "status": "accepted",
                "read_requests": [],
                "project_summary": {
                    "overall_assessment": "Orders submit path changed with test-backed evidence.",
                    "impact_level": "medium",
                    "impact_basis": [{"target_id": "app/orders.py", "kind": "file"}],
                    "affected_entrypoints": ["POST /orders"],
                    "critical_paths": ["POST /orders -> OrderService.submit"],
                    "verification_gaps": [],
                    "priority_themes": ["orders-submit"],
                },
                "capabilities": [],
                "change_themes": [
                    {
                        "theme_key": "orders-submit",
                        "name": "Orders submit",
                        "summary": "Order submission flow changed.",
                    }
                ],
                "recent_ai_changes": [],
            }

        harness = AgentContextHarness(provider=provider, max_rounds=2, max_read_requests=2)
        result = harness.run(
            self.graph_data,
            self.change_data,
            self.verification_data,
            progress_reporter=events.append,
        )

        self.assertEqual(result["status"], "accepted")
        self.assertEqual(events, ["agent_round_1", "agent_round_2"])

    def test_build_overview_rejects_reads_outside_manifest(self):
        def provider(_payload):
            return {
                "status": "needs_more_context",
                "read_requests": [
                    {
                        "target_type": "file",
                        "target_id": "app/not_in_manifest.py",
                        "reason": "Need a different file",
                    }
                ],
            }

        service = OverviewInferenceService(
            agent_harness_service=AgentContextHarness(provider=provider, max_rounds=2, max_read_requests=2)
        )

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_harness_invalid",
            graph_data=self.graph_data,
            change_data=self.change_data,
            verification_data=self.verification_data,
        )

        self.assertEqual(result["agent_harness_status"], "validation_failed")
        self.assertEqual(result["agent_harness_metadata"]["rounds_used"], 1)
        self.assertIn("target_not_allowed:file:app/not_in_manifest.py", result["agent_harness_metadata"]["validation_issues"])

    def test_context_manifest_keeps_same_target_id_separate_across_target_types(self):
        provider_calls = []

        def provider(payload):
            provider_calls.append(payload)
            if payload["round"] == 1:
                return {
                    "status": "needs_more_context",
                    "read_requests": [
                        {
                            "target_type": "file",
                            "target_id": "shared-node",
                            "reason": "Need file context",
                        },
                        {
                            "target_type": "verification_context",
                            "target_id": "shared-node",
                            "reason": "Need verification context",
                        },
                    ],
                }

            requested_context = payload["requested_context"]
            self.assertEqual(len(requested_context), 2)
            self.assertEqual(
                {(item["target_type"], item["target_id"]) for item in requested_context},
                {
                    ("file", "shared-node"),
                    ("verification_context", "shared-node"),
                },
            )
            file_item = next(item for item in requested_context if item["target_type"] == "file")
            verification_item = next(item for item in requested_context if item["target_type"] == "verification_context")
            self.assertEqual(file_item["content"]["path"], "shared-node")
            self.assertEqual(verification_item["content"]["status"], "report-backed")
            return {
                "status": "accepted",
                "read_requests": [],
                "project_summary": {
                    "overall_assessment": "accepted",
                    "impact_level": "low",
                    "impact_basis": [{"target_id": "shared-node", "kind": "file"}],
                    "affected_entrypoints": [],
                    "critical_paths": [],
                    "verification_gaps": [],
                    "priority_themes": [],
                },
                "capabilities": [],
                "change_themes": [],
                "recent_ai_changes": [],
            }

        service = OverviewInferenceService(
            agent_harness_service=AgentContextHarness(provider=provider, max_rounds=2, max_read_requests=2)
        )

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_harness_shared_target",
            graph_data=self.graph_data,
            change_data={
                **self.change_data,
                "changed_files": ["shared-node"],
                "file_contexts": {"shared-node": {"path": "shared-node", "snippet": "file-body"}},
            },
            verification_data={
                **self.verification_data,
                "evidence_by_path": {"shared-node": {"status": "report-backed", "tests": ["backend/tests/test_orders.py"]}},
            },
        )

        self.assertEqual(result["agent_harness_status"], "accepted")
        self.assertEqual(len(provider_calls), 2)

    def test_build_overview_stops_when_read_request_budget_is_exceeded(self):
        def provider(_payload):
            return {
                "status": "needs_more_context",
                "read_requests": [
                    {
                        "target_type": "file",
                        "target_id": "app/orders.py",
                        "reason": "Need file body",
                    },
                    {
                        "target_type": "verification_context",
                        "target_id": "app/orders.py",
                        "reason": "Need verification evidence",
                    },
                ],
            }

        service = OverviewInferenceService(
            agent_harness_service=AgentContextHarness(provider=provider, max_rounds=2, max_read_requests=1)
        )

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_harness_budget",
            graph_data=self.graph_data,
            change_data=self.change_data,
            verification_data=self.verification_data,
        )

        self.assertEqual(result["agent_harness_status"], "budget_exceeded")
        self.assertEqual(result["agent_harness_metadata"]["rounds_used"], 1)
        self.assertEqual(result["agent_harness_metadata"]["requests_used"], 0)

    def test_build_overview_preserves_base_project_summary_fields_with_explicit_agent_mapping(self):
        def provider(payload):
            if payload["round"] == 1:
                return {
                    "status": "accepted",
                    "read_requests": [],
                    "project_summary": {
                        "overall_assessment": "Harness assessment",
                        "impact_level": "medium",
                        "impact_basis": [{"target_id": "app/orders.py", "kind": "file"}],
                        "priority_themes": ["orders-submit"],
                        "what_this_app_seems_to_do": "should_not_override",
                        "technical_narrative": "should_not_override",
                        "core_flow": "should_not_override",
                    },
                    "capabilities": [],
                    "change_themes": [],
                    "recent_ai_changes": [],
                }
            raise AssertionError("unexpected extra round")

        service = OverviewInferenceService(
            agent_harness_service=AgentContextHarness(provider=provider, max_rounds=2, max_read_requests=2)
        )

        result = service.build_overview(
            repo_key="demo",
            snapshot_id="ws_harness_summary_merge",
            graph_data=self.graph_data,
            change_data=self.change_data,
            verification_data=self.verification_data,
        )

        self.assertEqual(result["project_summary"]["what_this_app_seems_to_do"], "正在对后端系统进行技术分析")
        self.assertIn("已分析 1 个模块", result["project_summary"]["technical_narrative"])
        self.assertEqual(result["project_summary"]["core_flow"], "客户端 -> API 处理器 -> 服务")
        self.assertEqual(result["project_summary"]["overall_assessment"], "Harness assessment")
        self.assertEqual(result["project_summary"]["impact_level"], result["change_risk_summary"]["headline"]["overall_risk_level"])
        self.assertEqual(result["project_summary"]["priority_themes"], ["orders-submit"])


if __name__ == "__main__":
    unittest.main()
