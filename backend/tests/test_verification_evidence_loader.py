import json
import os
import tempfile
import unittest
from textwrap import dedent


class VerificationEvidenceLoaderTest(unittest.TestCase):
    def test_load_returns_missing_when_no_artifacts_exist(self):
        from app.services.verification.evidence_loader import VerificationEvidenceLoader

        with tempfile.TemporaryDirectory() as tmp_dir:
            loader = VerificationEvidenceLoader(workspace_path=tmp_dir)
            result = loader.load()

        self.assertEqual(result["unit"], [])
        self.assertEqual(result["integration"], [])
        self.assertEqual(result["scenario"], [])
        self.assertTrue(any("missing" in item.lower() for item in result["warnings"]))

    def test_load_parses_junit_report_into_normalized_evidence(self):
        from app.services.verification.evidence_loader import VerificationEvidenceLoader

        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "pytest.xml"), "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        <testsuite tests="1" failures="0" errors="0">
                          <testcase classname="tests.test_health" name="test_health_endpoint">
                            <properties>
                              <property name="file_path" value="backend/app/api/routes.py" />
                            </properties>
                          </testcase>
                        </testsuite>
                        """
                    ).strip()
                )

            loader = VerificationEvidenceLoader(workspace_path=tmp_dir)
            result = loader.load()

        self.assertEqual(len(result["unit"]), 1)
        self.assertEqual(result["unit"][0]["status"], "passed")
        self.assertEqual(result["unit"][0]["test_id"], "tests.test_health::test_health_endpoint")
        self.assertEqual(result["unit"][0]["file_paths"], ["backend/app/api/routes.py"])
        self.assertEqual(result["unit"][0]["source_report"], "pytest.xml")

    def test_load_marks_malformed_junit_as_warning(self):
        from app.services.verification.evidence_loader import VerificationEvidenceLoader

        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "pytest.xml"), "w", encoding="utf-8") as f:
                f.write("<testsuite>")

            loader = VerificationEvidenceLoader(workspace_path=tmp_dir)
            result = loader.load()

        self.assertEqual(result["unit"], [])
        self.assertTrue(any("failed to parse" in item.lower() for item in result["warnings"]))

    def test_load_parses_failed_and_passing_scenario_reports(self):
        from app.services.verification.evidence_loader import VerificationEvidenceLoader

        with tempfile.TemporaryDirectory() as tmp_dir:
            scenario_dir = os.path.join(tmp_dir, "verification")
            os.makedirs(scenario_dir, exist_ok=True)
            with open(os.path.join(scenario_dir, "scenario_replay.json"), "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "scenarios": [
                            {"scenario_id": "checkout", "status": "passed", "file_paths": ["app/api/routes.py"]},
                            {"scenario_id": "refund", "status": "failed", "file_paths": ["app/services/refund.py"]},
                        ]
                    },
                    f,
                )

            loader = VerificationEvidenceLoader(workspace_path=tmp_dir)
            result = loader.load()

        self.assertEqual(len(result["scenario"]), 2)
        self.assertEqual(result["scenario"][0]["scenario_id"], "checkout")
        self.assertEqual(result["scenario"][1]["status"], "failed")


if __name__ == "__main__":
    unittest.main()
