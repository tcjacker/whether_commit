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

        self.assertEqual(result["technical_change_summary"], "No pending change facts were provided.")
        self.assertEqual(result["confidence"], "low")
        self.assertTrue(result["unknowns"])
        self.assertTrue(result["validation_gaps"])


class OverviewInferenceServiceTest(unittest.TestCase):
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
                "change_title": "Workspace diff (1 files)",
                "changed_files": ["app/main.py"],
                "changed_symbols": ["handler"],
                "directly_changed_modules": ["mod_api"],
                "minimal_review_set": ["app/main.py"],
            },
            verification_data={"affected_tests": []},
        )

        self.assertEqual(result["recent_ai_changes"][0]["summary"], "provider summary")
        self.assertEqual(result["project_summary"]["agent_reasoning"]["llm_reasoning"]["status"], "accepted")

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
                "change_title": "Workspace diff (1 files)",
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
                "what_this_app_seems_to_do": "Backend system under technical analysis",
                "technical_narrative": "Analyzed source facts only.",
                "core_flow": "Client -> API Handler -> Service",
                "agent_reasoning": {
                    "technical_change_summary": "1 files changed; 1 symbols and 1 routes were implicated.",
                    "change_types": ["flow_change"],
                    "risk_factors": ["No report-backed verification was linked to the changed paths."],
                    "review_recommendations": ["app/main.py"],
                    "why_impacted": "Changed symbols: handler",
                    "confidence": "low",
                    "unknowns": ["Verification evidence is weak or missing for the changed surface."],
                    "validation_gaps": ["No report-backed test evidence for the changed files."],
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
                    "change_title": "Workspace diff (1 files)",
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
                    "risk_factors": ["No report-backed verification was linked to the changed paths."],
                    "review_recommendations": ["app/main.py"],
                    "linked_tests": [],
                    "verification_coverage": "missing",
                    "confidence": "low",
                }
            ],
            warnings=["Verification evidence is weak or missing for the changed surface."],
        )

        self.assertEqual(
            overview.project_summary.agent_reasoning.validation_gaps,
            ["No report-backed test evidence for the changed files."],
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
                "change_title": "Workspace diff (1 files)",
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
        self.assertIn("No report-backed test evidence for the changed files.", result["warnings"])

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
            project_summary={"what_this_app_seems_to_do": "Backend system under technical analysis"},
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
                "change_title": "Workspace diff (1 files)",
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
        self.assertEqual(overview.project_summary.agent_reasoning.validation_gaps[0], "No report-backed test evidence for the changed files.")

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
                "change_title": "Workspace diff (1 files)",
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
        self.assertEqual(result["project_summary"]["what_this_app_seems_to_do"], "Backend system under technical analysis")
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
                "change_title": "Workspace diff (1 files)",
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
