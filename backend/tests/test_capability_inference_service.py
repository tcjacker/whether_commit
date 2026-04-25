import unittest


class CapabilityInferenceServiceTest(unittest.TestCase):
    def test_infers_route_capability_with_source_metadata(self):
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
                "dependencies": [
                    {"from": "mod_app__api", "to": "mod_app__services", "type": "calls"},
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
        self.assertEqual(result[0]["source"], "route")
        self.assertEqual(result[0]["status"], "recently_changed")
        self.assertEqual(result[0]["linked_modules"], ["mod_app__api", "mod_app__services"])
        self.assertEqual(result[0]["linked_routes"], ["GET /orders", "POST /orders"])
        self.assertEqual(result[0]["reasoning_basis"]["source"], "route")
        self.assertEqual(result[0]["reasoning_basis"]["route_group"], "orders")

    def test_route_transitive_module_stays_local_to_its_route_group(self):
        from app.services.capability_inference.service import CapabilityInferenceService

        service = CapabilityInferenceService()
        result = service.infer(
            graph_data={
                "modules": [
                    {"module_id": "mod_app__orders_api", "name": "orders_api", "type": "router"},
                    {"module_id": "mod_app__users_api", "name": "users_api", "type": "router"},
                    {"module_id": "mod_app__orders_service", "name": "orders_service", "type": "service"},
                ],
                "routes": [
                    {"method": "GET", "path": "/orders", "module": "mod_app__orders_api"},
                    {"method": "GET", "path": "/users", "module": "mod_app__users_api"},
                ],
                "dependencies": [
                    {"from": "mod_app__orders_api", "to": "mod_app__orders_service", "type": "calls"},
                ],
            },
            change_data={
                "directly_changed_modules": ["mod_app__orders_api", "mod_app__users_api"],
                "transitively_affected_modules": ["mod_app__orders_service"],
            },
            verification_data={},
            agent_reasoning={"llm_reasoning": {"status": "disabled"}},
        )

        orders_capability = next(
            cap for cap in result if cap["reasoning_basis"]["route_group"] == "orders"
        )
        users_capability = next(cap for cap in result if cap["reasoning_basis"]["route_group"] == "users")

        self.assertIn("mod_app__orders_service", orders_capability["linked_modules"])
        self.assertNotIn("mod_app__orders_service", users_capability["linked_modules"])

    def test_infers_worker_capability_without_routes(self):
        from app.services.capability_inference.service import CapabilityInferenceService

        service = CapabilityInferenceService()
        result = service.infer(
            graph_data={
                "modules": [
                    {"module_id": "mod_app__workers", "name": "workers", "type": "worker"},
                    {"module_id": "mod_app__services", "name": "services", "type": "service"},
                ],
                "routes": [],
                "dependencies": [
                    {"from": "mod_app__workers", "to": "mod_app__services", "type": "calls"},
                ],
            },
            change_data={
                "directly_changed_modules": ["mod_app__workers"],
                "changed_jobs": ["reconcile_orders_job"],
            },
            verification_data={},
            agent_reasoning={"llm_reasoning": {"status": "disabled"}},
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source"], "worker")
        self.assertEqual(result[0]["reasoning_basis"]["source"], "worker")
        self.assertEqual(result[0]["reasoning_basis"]["source_entities"], ["reconcile_orders_job"])
        self.assertIn("mod_app__workers", result[0]["linked_modules"])
        self.assertEqual(result[0]["linked_routes"], [])

    def test_entrypoint_transitive_module_stays_local_to_its_capability(self):
        from app.services.capability_inference.service import CapabilityInferenceService

        service = CapabilityInferenceService()
        result = service.infer(
            graph_data={
                "modules": [
                    {"module_id": "mod_app__worker_a", "name": "worker_a", "type": "worker"},
                    {"module_id": "mod_app__worker_b", "name": "worker_b", "type": "worker"},
                    {"module_id": "mod_app__service_a", "name": "service_a", "type": "service"},
                    {"module_id": "mod_app__service_b", "name": "service_b", "type": "service"},
                ],
                "routes": [],
                "dependencies": [
                    {"from": "mod_app__worker_a", "to": "mod_app__service_a", "type": "calls"},
                    {"from": "mod_app__worker_b", "to": "mod_app__service_b", "type": "calls"},
                ],
            },
            change_data={
                "directly_changed_modules": ["mod_app__worker_a", "mod_app__worker_b"],
                "transitively_affected_modules": ["mod_app__service_a", "mod_app__service_b"],
                "changed_jobs": ["job_a", "job_b"],
            },
            verification_data={},
            agent_reasoning={"llm_reasoning": {"status": "disabled"}},
        )

        worker_a_capability = next(cap for cap in result if cap["reasoning_basis"]["source_module"] == "mod_app__worker_a")
        worker_b_capability = next(cap for cap in result if cap["reasoning_basis"]["source_module"] == "mod_app__worker_b")

        self.assertIn("mod_app__service_a", worker_a_capability["linked_modules"])
        self.assertNotIn("mod_app__service_b", worker_a_capability["linked_modules"])
        self.assertIn("mod_app__service_b", worker_b_capability["linked_modules"])
        self.assertNotIn("mod_app__service_a", worker_b_capability["linked_modules"])

    def test_infers_schema_capability_without_routes(self):
        from app.services.capability_inference.service import CapabilityInferenceService

        service = CapabilityInferenceService()
        result = service.infer(
            graph_data={
                "modules": [
                    {"module_id": "mod_app__schemas", "name": "schemas", "type": "schema"},
                    {"module_id": "mod_app__repositories", "name": "repositories", "type": "repository"},
                ],
                "routes": [],
                "dependencies": [
                    {"from": "mod_app__repositories", "to": "mod_app__schemas", "type": "transforms"},
                ],
            },
            change_data={
                "directly_changed_modules": ["mod_app__schemas"],
                "changed_schemas": ["CreateOrderRequest"],
            },
            verification_data={},
            agent_reasoning={"llm_reasoning": {"status": "disabled"}},
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source"], "schema")
        self.assertEqual(result[0]["reasoning_basis"]["source"], "schema")
        self.assertEqual(result[0]["reasoning_basis"]["source_entities"], ["CreateOrderRequest"])
        self.assertIn("mod_app__schemas", result[0]["linked_modules"])
        self.assertEqual(result[0]["linked_routes"], [])


if __name__ == "__main__":
    unittest.main()
