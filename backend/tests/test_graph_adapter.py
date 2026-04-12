import os
import tempfile
import unittest
from textwrap import dedent

from app.services.graph_adapter.adapter import GraphAdapter


class GraphAdapterTest(unittest.TestCase):
    def test_generate_graph_snapshot_contains_local_import_dependencies_and_typed_modules(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            api_dir = os.path.join(tmp_dir, "app", "api")
            services_dir = os.path.join(tmp_dir, "app", "services")
            repos_dir = os.path.join(tmp_dir, "app", "repositories")
            schemas_dir = os.path.join(tmp_dir, "app", "schemas")

            os.makedirs(api_dir)
            os.makedirs(services_dir)
            os.makedirs(repos_dir)
            os.makedirs(schemas_dir)

            with open(os.path.join(api_dir, "routes.py"), "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        from app.services.order_service import create_order
                        from app.schemas.order_schema import OrderRequest


                        @router.get("/orders")
                        def list_orders():
                            return create_order()
                        """
                    ).strip()
                )

            with open(os.path.join(services_dir, "order_service.py"), "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        from app.repositories.order_repo import fetch_order


                        def create_order():
                            return fetch_order()
                        """
                    ).strip()
                )

            with open(os.path.join(repos_dir, "order_repo.py"), "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        class OrderRepository:
                            pass
                        """
                    ).strip()
                )

            with open(os.path.join(schemas_dir, "order_schema.py"), "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        class OrderRequest:
                            pass
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

        self.assertIn(("mod_app__api", "mod_app__services", "imports"), dependency_edges)
        self.assertIn(("mod_app__api", "mod_app__schemas", "imports"), dependency_edges)
        self.assertIn(("mod_app__services", "mod_app__repositories", "imports"), dependency_edges)

    def test_duplicate_leaf_directory_names_produce_unique_module_ids(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            app_tests_dir = os.path.join(tmp_dir, "app", "tests")
            scripts_tests_dir = os.path.join(tmp_dir, "scripts", "tests")

            os.makedirs(app_tests_dir)
            os.makedirs(scripts_tests_dir)

            with open(os.path.join(scripts_tests_dir, "helper.py"), "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        def helper():
                            return "ok"
                        """
                    ).strip()
                )

            with open(os.path.join(app_tests_dir, "consumer.py"), "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        from scripts.tests.helper import helper


                        def use_helper():
                            return helper()
                        """
                    ).strip()
                )

            adapter = GraphAdapter(workspace_path=tmp_dir)
            result = adapter.generate_graph_snapshot()

        module_ids = [module["module_id"] for module in result["modules"]]
        module_types = {module["module_id"]: module["type"] for module in result["modules"]}
        dependency_edges = {(edge["from"], edge["to"], edge["type"]) for edge in result["dependencies"]}

        self.assertEqual(len(module_ids), len(set(module_ids)))
        self.assertIn("mod_app__tests", module_ids)
        self.assertIn("mod_scripts__tests", module_ids)
        self.assertEqual(module_types["mod_app__tests"], "module")
        self.assertEqual(module_types["mod_scripts__tests"], "module")
        self.assertIn(("mod_app__tests", "mod_scripts__tests", "imports"), dependency_edges)


if __name__ == "__main__":
    unittest.main()
