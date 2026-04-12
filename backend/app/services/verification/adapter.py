from typing import Dict, Any
import os

from app.services.verification.evidence_loader import VerificationEvidenceLoader

class VerificationAdapter:
    """
    Adapter for aggregating CI, Unit Tests, Integration Tests, and Scenario Replay.
    Responsible for generating the verification.json snapshot.
    In this MVP, we parse a real local JUnit XML report if it exists.
    """
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path

    def _collect_test_results(self) -> Dict[str, Any]:
        """
        Reads verification artifacts via the shared evidence loader.
        """
        evidence = VerificationEvidenceLoader(workspace_path=self.workspace_path).load()
        unit_evidence = evidence.get("unit", [])
        integration_evidence = evidence.get("integration", [])
        scenario_evidence = evidence.get("scenario", [])

        result = {
            "build": {"status": "unknown", "evidence": "no build artifact"},
            "unit_tests": {"passed": 0, "total": 0, "status": "unknown"},
            "integration_tests": {"passed": 0, "total": 0, "status": "unknown"},
            "scenario_replay": {"status": "unknown"},
            "critical_paths": [],
            "unverified_areas": ["Integration tests missing"],
            "test_report_present": False,
        }

        if unit_evidence:
            total = len(unit_evidence)
            passed = sum(1 for item in unit_evidence if item.get("status") == "passed")
            result["unit_tests"] = {
                "passed": passed,
                "total": total,
                "status": "passed" if passed == total else "failed",
            }
            result["test_report_present"] = True
            result["critical_paths"].append({"name": "Core flows", "status": "verified" if passed == total else "warning"})
        else:
            result["unverified_areas"].append("No pytest.xml report found in workspace root")

        if integration_evidence:
            total = len(integration_evidence)
            passed = sum(1 for item in integration_evidence if item.get("status") == "passed")
            result["integration_tests"] = {
                "passed": passed,
                "total": total,
                "status": "passed" if passed == total else "failed",
            }
        if scenario_evidence:
            result["scenario_replay"] = {
                "status": "passed" if all(item.get("status") == "passed" for item in scenario_evidence) else "failed"
            }
        result["unverified_areas"].extend(evidence.get("warnings", []))
        result["verification_evidence"] = evidence
        return result

    def _build_path_evidence(
        self,
        file_path: str,
        linked_tests: list[str],
        test_report_present: bool,
        unit_test_status: str,
    ) -> Dict[str, Any]:
        has_linked_tests = bool(linked_tests)
        is_test_file = "test" in file_path.lower()

        if test_report_present and (has_linked_tests or is_test_file):
            if unit_test_status != "passed":
                return {
                    "strength": "none",
                    "status": "report-failed",
                    "detail": "Report-backed evidence exists, but the linked test execution did not pass.",
                    "linked_tests": linked_tests,
                    "unit_tests_status": unit_test_status,
                }
            return {
                "strength": "strong",
                "status": "report-backed",
                "detail": "JUnit report exists and the path has a test link or is itself a test file.",
                "linked_tests": linked_tests,
                "unit_tests_status": unit_test_status,
            }

        if has_linked_tests or is_test_file:
            return {
                "strength": "weak",
                "status": "test-file-present",
                "detail": "A test file or test link exists, but no executable report evidence was found.",
                "linked_tests": linked_tests,
                "unit_tests_status": unit_test_status,
            }

        return {
            "strength": "none",
            "status": "no-evidence",
            "detail": "No linked tests and no report-backed evidence were found for this path.",
            "linked_tests": [],
            "unit_tests_status": unit_test_status,
        }

    def aggregate_verification(self, change_data: Dict[str, Any] = None, graph_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main entry point for JobManager to build the verification summary.
        If change_data is provided, it binds verification evidence to the changed paths.
        """
        try:
            raw_data = self._collect_test_results()
            
            # Initialize change-aware fields
            raw_data["verified_changed_modules"] = []
            raw_data["unverified_changed_modules"] = []
            raw_data["affected_tests"] = []
            raw_data["verified_changed_paths"] = []
            raw_data["unverified_changed_paths"] = []
            raw_data["verified_impacts"] = []
            raw_data["unverified_impacts"] = []
            raw_data["missing_tests_for_changed_paths"] = []
            raw_data["critical_changed_paths"] = []
            raw_data["evidence_by_path"] = {}
            
            if change_data:
                changed_files = change_data.get("changed_files", [])
                changed_modules = change_data.get("directly_changed_modules", [])
                linked_tests = change_data.get("linked_tests", [])
                report_backed = raw_data.get("test_report_present", False)
                unit_test_status = raw_data.get("unit_tests", {}).get("status", "unknown")
                report_evidence = raw_data.get("verification_evidence", {})
                evidence_by_test_path = self._index_evidence_by_path(report_evidence)
                direct_impacts = change_data.get("direct_impacts", [])
                transitive_impacts = change_data.get("transitive_impacts", [])
                
                raw_data["affected_tests"] = linked_tests
                
                for mod in changed_modules:
                    # Conservative heuristic: only mark verified when there is report-backed evidence.
                    if report_backed and linked_tests and unit_test_status == "passed":
                        raw_data["verified_changed_modules"].append(mod)
                    else:
                        raw_data["unverified_changed_modules"].append(mod)
                
                for file_path in changed_files:
                    linked_evidence = evidence_by_test_path.get(file_path, [])
                    evidence = self._build_path_evidence(
                        file_path=file_path,
                        linked_tests=linked_tests + [item.get("test_id") for item in linked_evidence if item.get("test_id")],
                        test_report_present=report_backed and bool(linked_evidence),
                        unit_test_status=unit_test_status,
                    )
                    raw_data["evidence_by_path"][file_path] = evidence

                    if evidence["strength"] == "strong":
                        raw_data["verified_changed_paths"].append(file_path)
                    else:
                        raw_data["unverified_changed_paths"].append(file_path)
                        if "test" not in file_path.lower():
                            raw_data["critical_changed_paths"].append(
                                {"path": file_path, "reason": "missing_report_backed_evidence"}
                            )
                    if evidence["strength"] == "none" and "test" not in file_path.lower():
                        raw_data["missing_tests_for_changed_paths"].append(file_path)

                verified_modules = set(raw_data["verified_changed_modules"])
                for impact in direct_impacts:
                    entity_id = impact.get("entity_id")
                    if entity_id and entity_id in verified_modules:
                        raw_data["verified_impacts"].append(impact)
                    else:
                        raw_data["unverified_impacts"].append(impact)

                for impact in transitive_impacts:
                    entity_id = impact.get("entity_id")
                    if entity_id and entity_id in verified_modules:
                        raw_data["verified_impacts"].append(impact)
                    else:
                        raw_data["unverified_impacts"].append(impact)

            return raw_data
        except Exception as e:
            # Fallback to unknown state
            return {
                "build": {"status": "unknown", "evidence": "no build artifact"},
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
                "test_report_present": False,
                "error": str(e)
            }

    def _index_evidence_by_path(self, report_evidence: Dict[str, Any]) -> Dict[str, list[Dict[str, Any]]]:
        indexed: Dict[str, list[Dict[str, Any]]] = {}
        for bucket in ("unit", "integration", "scenario"):
            for item in report_evidence.get(bucket, []):
                for file_path in item.get("file_paths", []):
                    indexed.setdefault(file_path, []).append(item)
        return indexed
