import os
import tempfile
import unittest
from textwrap import dedent

from app.services.verification.adapter import VerificationAdapter


class VerificationAdapterTest(unittest.TestCase):
    def test_defaults_build_status_to_unknown_without_report(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            adapter = VerificationAdapter(workspace_path=tmp_dir)

            result = adapter.aggregate_verification()

        self.assertEqual(result["build"]["status"], "unknown")
        self.assertFalse(result["test_report_present"])
        self.assertIn("No pytest.xml report found in workspace root", result["unverified_areas"])

    def test_change_aware_verification_uses_weak_evidence_without_report(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            adapter = VerificationAdapter(workspace_path=tmp_dir)

            result = adapter.aggregate_verification(
                {
                    "changed_files": ["app/main.py", "tests/test_main.py"],
                    "directly_changed_modules": ["mod_app"],
                    "linked_tests": ["tests/test_main.py"],
                }
            )

        self.assertEqual(result["verified_changed_modules"], [])
        self.assertEqual(result["unverified_changed_modules"], ["mod_app"])
        self.assertEqual(result["evidence_by_path"]["app/main.py"]["strength"], "weak")
        self.assertEqual(result["evidence_by_path"]["app/main.py"]["status"], "test-file-present")
        self.assertEqual(result["evidence_by_path"]["tests/test_main.py"]["strength"], "weak")
        self.assertEqual(result["evidence_by_path"]["tests/test_main.py"]["status"], "test-file-present")

    def test_report_backed_evidence_marks_strong_and_verifies_module(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "pytest.xml"), "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        <testsuite tests="2" failures="0" errors="0">
                          <testcase classname="tests.test_main" name="test_main">
                            <properties>
                              <property name="file_path" value="app/main.py" />
                            </properties>
                          </testcase>
                        </testsuite>
                        """
                    ).strip()
                )

            adapter = VerificationAdapter(workspace_path=tmp_dir)

            result = adapter.aggregate_verification(
                {
                    "changed_files": ["app/main.py", "tests/test_main.py"],
                    "directly_changed_modules": ["mod_app"],
                    "linked_tests": ["tests/test_main.py"],
                }
            )

        self.assertEqual(result["build"]["status"], "unknown")
        self.assertEqual(result["unit_tests"]["status"], "passed")
        self.assertEqual(result["verified_changed_modules"], ["mod_app"])
        self.assertEqual(result["unverified_changed_modules"], [])
        self.assertEqual(result["evidence_by_path"]["app/main.py"]["strength"], "strong")
        self.assertEqual(result["evidence_by_path"]["app/main.py"]["status"], "report-backed")

    def test_agent_test_results_junit_report_is_loaded(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            artifact_dir = os.path.join(tmp_dir, ".agent-test-results")
            os.makedirs(artifact_dir)
            with open(os.path.join(artifact_dir, "pytest.xml"), "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        <testsuite tests="1" failures="0" errors="0">
                          <testcase classname="tests.test_main" name="test_main">
                            <properties>
                              <property name="file_path" value="app/main.py" />
                            </properties>
                          </testcase>
                        </testsuite>
                        """
                    ).strip()
                )

            adapter = VerificationAdapter(workspace_path=tmp_dir)
            result = adapter.aggregate_verification(
                {
                    "changed_files": ["app/main.py"],
                    "directly_changed_modules": ["mod_app"],
                    "linked_tests": ["tests/test_main.py"],
                }
            )

        self.assertTrue(result["test_report_present"])
        self.assertEqual(result["unit_tests"]["status"], "passed")
        self.assertEqual(result["verification_evidence"]["unit"][0]["source_report"], ".agent-test-results/pytest.xml")
        self.assertEqual(result["evidence_by_path"]["app/main.py"]["strength"], "strong")

    def test_change_aware_verification_binds_paths_and_impacts_conservatively(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "pytest.xml"), "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        <testsuite tests="1" failures="0" errors="0">
                          <testcase classname="tests.test_api" name="test_health">
                            <properties>
                              <property name="file_path" value="app/api/routes.py" />
                            </properties>
                          </testcase>
                        </testsuite>
                        """
                    ).strip()
                )

            adapter = VerificationAdapter(workspace_path=tmp_dir)
            result = adapter.aggregate_verification(
                change_data={
                    "changed_files": ["app/api/routes.py", "app/services/order_service.py"],
                    "directly_changed_modules": ["mod_app__api"],
                    "direct_impacts": [{"entity_id": "mod_app__api", "reason": "direct_file_change", "distance": 0}],
                    "transitive_impacts": [
                        {
                            "entity_id": "mod_app__services",
                            "reason": "reachable_via_dependency_graph",
                            "distance": 1,
                        }
                    ],
                    "affected_entrypoints": ["GET /health"],
                    "linked_tests": ["tests/test_api.py"],
                },
                graph_data={
                    "dependencies": [
                        {"from": "mod_app__api", "to": "mod_app__services", "type": "calls"},
                    ]
                },
            )

        self.assertEqual(result["verified_changed_paths"], ["app/api/routes.py"])
        self.assertEqual(result["unverified_changed_paths"], ["app/services/order_service.py"])
        self.assertEqual([item["entity_id"] for item in result["verified_impacts"]], ["mod_app__api"])
        self.assertEqual([item["entity_id"] for item in result["unverified_impacts"]], ["mod_app__services"])
        self.assertEqual(result["critical_changed_paths"][0]["path"], "app/services/order_service.py")
        self.assertEqual(result["critical_changed_paths"][0]["reason"], "missing_report_backed_evidence")

    def test_failed_report_does_not_upgrade_changed_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "pytest.xml"), "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        <testsuite tests="1" failures="1" errors="0">
                          <testcase classname="tests.test_api" name="test_health">
                            <properties>
                              <property name="file_path" value="app/api/routes.py" />
                            </properties>
                            <failure message="boom" />
                          </testcase>
                        </testsuite>
                        """
                    ).strip()
                )

            adapter = VerificationAdapter(workspace_path=tmp_dir)
            result = adapter.aggregate_verification(
                change_data={
                    "changed_files": ["app/api/routes.py"],
                    "directly_changed_modules": ["mod_app__api"],
                    "direct_impacts": [{"entity_id": "mod_app__api", "reason": "direct_file_change"}],
                    "linked_tests": ["tests/test_api.py"],
                }
            )

        self.assertEqual(result["verified_changed_paths"], [])
        self.assertEqual(result["unverified_changed_paths"], ["app/api/routes.py"])


if __name__ == "__main__":
    unittest.main()
