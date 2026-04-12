import unittest

from app.services.overview_inference.agent_reasoning import AgentReasoningService
from app.services.overview_inference.llm_reasoning import LLMReasoningService, ReasoningPromptBuilder


class ReasoningPromptBuilderTest(unittest.TestCase):
    def test_build_uses_only_normalized_facts(self):
        builder = ReasoningPromptBuilder()

        prompt = builder.build(
            graph_data={
                "modules": [{"module_id": "mod_api", "name": "api", "type": "router"}],
                "dependencies": [{"from": "mod_api", "to": "mod_service", "type": "calls"}],
                "raw_graph_notes": "do not leak",
            },
            change_data={
                "changed_files": ["backend/app/api/routes.py"],
                "changed_symbols": ["route_health"],
                "changed_schemas": ["HealthSchema"],
                "changed_jobs": ["cleanup_job"],
                "directly_changed_modules": ["mod_api"],
                "transitively_affected_modules": ["mod_service"],
                "minimal_review_set": ["backend/app/api/routes.py"],
                "unstructured_notes": "ignore this",
            },
            verification_data={
                "affected_tests": ["tests/test_health.py"],
                "evidence_by_path": {"backend/app/api/routes.py": {"status": "covered"}},
                "freeform_verification_notes": "ignore this too",
            },
        )

        self.assertIn("normalized_facts", prompt)
        self.assertEqual(prompt["normalized_facts"]["changed_files"], ["backend/app/api/routes.py"])
        self.assertEqual(prompt["normalized_facts"]["changed_symbols"], ["route_health"])
        self.assertEqual(prompt["normalized_facts"]["changed_schemas"], ["HealthSchema"])
        self.assertEqual(prompt["normalized_facts"]["changed_jobs"], ["cleanup_job"])
        self.assertEqual(prompt["normalized_facts"]["direct_impacts"], ["mod_api"])
        self.assertEqual(prompt["normalized_facts"]["transitive_impacts"], ["mod_service"])
        self.assertEqual(prompt["normalized_facts"]["graph_edges"], [{"from": "mod_api", "to": "mod_service", "type": "calls"}])
        self.assertEqual(prompt["normalized_facts"]["verification_evidence"], {"backend/app/api/routes.py": {"status": "covered"}})
        self.assertNotIn("raw_graph_notes", prompt["normalized_facts"])
        self.assertNotIn("unstructured_notes", prompt["normalized_facts"])
        self.assertNotIn("freeform_verification_notes", prompt["normalized_facts"])

    def test_build_explicitly_requires_concrete_evidence_values(self):
        builder = ReasoningPromptBuilder()

        prompt = builder.build(
            graph_data={"dependencies": []},
            change_data={"changed_files": ["backend/app/api/routes.py"], "directly_changed_modules": ["mod_api"]},
            verification_data={"evidence_by_path": {"backend/app/api/routes.py": {"status": "covered"}}},
        )

        constraints = prompt["constraints"]
        self.assertTrue(any("specific values" in item for item in constraints))
        self.assertTrue(any("field names" in item for item in constraints))


class LLMReasoningServiceTest(unittest.TestCase):
    def test_missing_required_fields_rejects_reasoning(self):
        def provider(_payload):
            return {
                "technical_change_summary": "summary only",
                "confidence": "high",
            }

        service = LLMReasoningService(provider=provider)

        result = service.reason(
            {
                "normalized_facts": {
                    "changed_files": ["backend/app/api/routes.py"],
                    "changed_symbols": ["route_health"],
                    "changed_schemas": [],
                    "changed_jobs": [],
                    "direct_impacts": ["mod_api"],
                    "transitive_impacts": [],
                    "graph_edges": [],
                    "verification_evidence": {},
                    "unknowns": ["missing dependency graph"],
                }
            }
        )

        self.assertEqual(result["status"], "rejected")
        self.assertFalse(result["accepted"])
        self.assertIn("required_fields", result["validation_issues"])
        self.assertEqual(result["reasoning"]["confidence"], "low")

    def test_module_evidence_from_impacts_is_allowed(self):
        def provider(_payload):
            return {
                "technical_change_summary": "summary",
                "change_types": ["code_modification"],
                "risk_factors": [],
                "review_recommendations": ["backend/app/api/routes.py"],
                "why_impacted": "Direct and transitive module impact is supported by normalized facts.",
                "confidence": "medium",
                "unknowns": [],
                "validation_gaps": [],
                "evidence_used": ["mod_api", "mod_service"],
            }

        service = LLMReasoningService(provider=provider)

        result = service.reason(
            {
                "normalized_facts": {
                    "changed_files": ["backend/app/api/routes.py"],
                    "changed_symbols": ["route_health"],
                    "changed_schemas": [],
                    "changed_jobs": [],
                    "direct_impacts": ["mod_api"],
                    "transitive_impacts": ["mod_service"],
                    "graph_edges": [],
                    "verification_evidence": {},
                    "unknowns": [],
                }
            }
        )

        self.assertEqual(result["status"], "accepted")
        self.assertTrue(result["accepted"])
        self.assertNotIn("unavailable_evidence", result["validation_issues"])

    def test_unavailable_evidence_is_rejected(self):
        def provider(_payload):
            return {
                "technical_change_summary": "summary",
                "change_types": ["code_modification"],
                "risk_factors": [],
                "review_recommendations": ["backend/app/api/routes.py"],
                "why_impacted": "references missing entity",
                "confidence": "medium",
                "unknowns": [],
                "validation_gaps": [],
                "evidence_used": ["mod_nonexistent"],
            }

        service = LLMReasoningService(provider=provider)

        result = service.reason(
            {
                "normalized_facts": {
                    "changed_files": ["backend/app/api/routes.py"],
                    "changed_symbols": [],
                    "changed_schemas": [],
                    "changed_jobs": [],
                    "direct_impacts": ["mod_api"],
                    "transitive_impacts": [],
                    "graph_edges": [],
                    "verification_evidence": {},
                    "unknowns": [],
                }
            }
        )

        self.assertEqual(result["status"], "rejected")
        self.assertTrue(any(issue.startswith("unavailable_evidence:") for issue in result["validation_issues"]))


class AgentReasoningServiceTest(unittest.TestCase):
    def test_analyze_keeps_unknowns_explicit_when_evidence_is_missing(self):
        service = AgentReasoningService()

        result = service.analyze(
            graph_data={"modules": [], "dependencies": []},
            change_data={
                "changed_files": ["backend/app/api/routes.py"],
                "changed_symbols": ["route_health"],
                "changed_schemas": [],
                "changed_jobs": [],
                "directly_changed_modules": ["mod_api"],
                "transitively_affected_modules": [],
                "minimal_review_set": ["backend/app/api/routes.py"],
            },
            verification_data={"affected_tests": []},
        )

        self.assertTrue(result["unknowns"])
        self.assertTrue(any("graph" in item.lower() for item in result["unknowns"]))
        self.assertTrue(any("verification" in item.lower() for item in result["unknowns"]))
        self.assertEqual(result["confidence"], "low")


if __name__ == "__main__":
    unittest.main()
