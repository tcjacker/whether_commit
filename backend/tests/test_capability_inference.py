import unittest


class CapabilityInferenceServiceTest(unittest.TestCase):
    def test_infers_conservative_capability_from_route_and_service_cluster(self):
        from app.services.capability_inference.service import CapabilityInferenceService

        service = CapabilityInferenceService()
        result = service.infer(
            graph_data={
                "modules": [
                    {"module_id": "mod_app__api", "name": "api", "type": "router"},
                    {"module_id": "mod_app__services", "name": "services", "type": "service"},
                ],
                "routes": [
                    {"method": "GET", "path": "/orders", "module": "mod_app__api"},
                    {"method": "POST", "path": "/orders", "module": "mod_app__api"},
                ],
            },
            change_data={
                "directly_changed_modules": ["mod_app__api"],
                "transitively_affected_modules": ["mod_app__services"],
            },
            verification_data={
                "unverified_impacts": [{"entity_id": "mod_app__services"}],
            },
            agent_reasoning={
                "why_impacted": "Routes and service modules changed.",
                "llm_reasoning": {"status": "accepted"},
            },
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["status"], "recently_changed")
        self.assertEqual(result[0]["linked_modules"], ["mod_app__api", "mod_app__services"])
        self.assertEqual(result[0]["linked_routes"], ["GET /orders", "POST /orders"])

    def test_returns_empty_when_only_technical_modules_exist(self):
        from app.services.capability_inference.service import CapabilityInferenceService

        service = CapabilityInferenceService()
        result = service.infer(
            graph_data={
                "modules": [
                    {"module_id": "mod_scripts", "name": "scripts", "type": "module"},
                    {"module_id": "mod_tests", "name": "tests", "type": "module"},
                ],
                "routes": [],
            },
            change_data={"directly_changed_modules": ["mod_scripts"]},
            verification_data={},
            agent_reasoning={"llm_reasoning": {"status": "disabled"}},
        )

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
