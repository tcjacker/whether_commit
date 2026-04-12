import os
import tempfile
import unittest
from textwrap import dedent

from app.services.graph_adapter.adapter import GraphAdapter


class GraphFlowExtractionTest(unittest.TestCase):
    def test_generate_graph_snapshot_contains_backend_flow_edges(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            api_dir = os.path.join(tmp_dir, "app", "api")
            services_dir = os.path.join(tmp_dir, "app", "services")
            repositories_dir = os.path.join(tmp_dir, "app", "repositories")
            schemas_dir = os.path.join(tmp_dir, "app", "schemas")
            workers_dir = os.path.join(tmp_dir, "app", "workers")

            os.makedirs(api_dir)
            os.makedirs(services_dir)
            os.makedirs(repositories_dir)
            os.makedirs(schemas_dir)
            os.makedirs(workers_dir)

            with open(os.path.join(api_dir, "routes.py"), "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        from fastapi import APIRouter
                        from app.schemas.order_schema import CreateOrderRequest, OrderRecord
                        from app.services.order_service import create_order

                        router = APIRouter()


                        @router.post("/orders")
                        def submit_order(payload: CreateOrderRequest) -> OrderRecord:
                            return create_order(payload)
                        """
                    ).strip()
                )

            with open(os.path.join(services_dir, "order_service.py"), "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        from app.repositories.order_repository import save_order
                        from app.schemas.order_schema import CreateOrderRequest, OrderRecord


                        def create_order(payload: CreateOrderRequest) -> OrderRecord:
                            return save_order(payload)
                        """
                    ).strip()
                )

            with open(os.path.join(repositories_dir, "order_repository.py"), "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        from app.schemas.order_schema import CreateOrderRequest, OrderRecord


                        def save_order(payload: CreateOrderRequest) -> OrderRecord:
                            return OrderRecord(order_id=payload.order_id)
                        """
                    ).strip()
                )

            with open(os.path.join(schemas_dir, "order_schema.py"), "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        from pydantic import BaseModel


                        class CreateOrderRequest(BaseModel):
                            order_id: str


                        class OrderRecord(BaseModel):
                            order_id: str
                        """
                    ).strip()
                )

            with open(os.path.join(workers_dir, "reconcile_worker.py"), "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        from app.services.order_service import create_order
                        from app.schemas.order_schema import CreateOrderRequest


                        def reconcile_orders_job() -> None:
                            create_order(CreateOrderRequest(order_id="seed"))
                        """
                    ).strip()
                )

            adapter = GraphAdapter(workspace_path=tmp_dir)
            result = adapter.generate_graph_snapshot()

        module_types = {module["module_id"]: module["type"] for module in result["modules"]}
        dependency_edges = {(edge["from"], edge["to"], edge["type"]) for edge in result["dependencies"]}

        self.assertEqual(module_types["mod_app__api"], "router")
        self.assertEqual(module_types["mod_app__services"], "service")
        self.assertEqual(module_types["mod_app__repositories"], "repository")
        self.assertEqual(module_types["mod_app__schemas"], "schema")
        self.assertEqual(module_types["mod_app__workers"], "worker")

        self.assertIn(("mod_app__api", "mod_app__services", "calls"), dependency_edges)
        self.assertIn(("mod_app__api", "mod_app__schemas", "validates"), dependency_edges)
        self.assertIn(("mod_app__services", "mod_app__repositories", "writes"), dependency_edges)
        self.assertIn(("mod_app__repositories", "mod_app__schemas", "transforms"), dependency_edges)
        self.assertIn(("mod_app__workers", "mod_app__services", "calls"), dependency_edges)

    def test_generate_graph_snapshot_resolves_simple_attribute_calls(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            services_dir = os.path.join(tmp_dir, "app", "services")
            repositories_dir = os.path.join(tmp_dir, "app", "repositories")

            os.makedirs(services_dir)
            os.makedirs(repositories_dir)

            with open(os.path.join(services_dir, "order_service.py"), "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        from app.repositories.order_repository import OrderRepository


                        def get_order():
                            repo = OrderRepository()
                            return repo.fetch_order()
                        """
                    ).strip()
                )

            with open(os.path.join(repositories_dir, "order_repository.py"), "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        class OrderRepository:
                            def fetch_order(self):
                                return {"ok": True}
                        """
                    ).strip()
                )

            adapter = GraphAdapter(workspace_path=tmp_dir)
            result = adapter.generate_graph_snapshot()

        dependency_edges = {(edge["from"], edge["to"], edge["type"]) for edge in result["dependencies"]}
        self.assertIn(("mod_app__services", "mod_app__repositories", "reads"), dependency_edges)


if __name__ == "__main__":
    unittest.main()
