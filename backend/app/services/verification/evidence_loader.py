from __future__ import annotations

import json
import os
import xml.etree.ElementTree as ET
from typing import Any, Dict, List


class VerificationEvidenceLoader:
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path

    def load(self) -> Dict[str, Any]:
        result = {
            "unit": [],
            "integration": [],
            "scenario": [],
            "warnings": [],
        }
        result["unit"].extend(self._load_junit_report("pytest.xml", result["warnings"]))
        result["unit"].extend(self._load_junit_report(".agent-test-results/pytest.xml", result["warnings"]))
        result["integration"].extend(self._load_junit_report("integration.xml", result["warnings"]))
        result["integration"].extend(self._load_junit_report(".agent-test-results/integration.xml", result["warnings"]))
        result["scenario"].extend(self._load_scenario_report(result["warnings"]))

        if not result["unit"] and not result["integration"] and not result["scenario"]:
            result["warnings"].append("Verification artifacts missing for unit, integration, and scenario evidence.")
        return result

    def _load_junit_report(self, filename: str, warnings: List[str]) -> List[Dict[str, Any]]:
        path = os.path.join(self.workspace_path, filename)
        if not os.path.exists(path):
            return []

        try:
            root = ET.parse(path).getroot()
        except Exception as exc:
            warnings.append(f"Failed to parse {filename}: {exc}")
            return []

        testcases = []
        for testcase in root.findall(".//testcase"):
            classname = testcase.attrib.get("classname", "").strip()
            name = testcase.attrib.get("name", "").strip()
            status = "passed"
            if testcase.find("failure") is not None or testcase.find("error") is not None:
                status = "failed"

            file_paths: List[str] = []
            for prop in testcase.findall("./properties/property"):
                key = prop.attrib.get("name", "").strip()
                value = prop.attrib.get("value", "").strip()
                if key in {"file_path", "file_paths"} and value:
                    file_paths.extend([item.strip() for item in value.split(",") if item.strip()])
            file_attr = testcase.attrib.get("file", "").strip()
            if file_attr:
                file_paths.append(file_attr)

            testcases.append(
                {
                    "status": status,
                    "test_id": f"{classname}::{name}" if classname else name,
                    "source_report": filename,
                    "file_paths": sorted(set(file_paths)),
                    "scenario_id": None,
                }
            )
        return testcases

    def _load_scenario_report(self, warnings: List[str]) -> List[Dict[str, Any]]:
        path = os.path.join(self.workspace_path, "verification", "scenario_replay.json")
        if not os.path.exists(path):
            return []

        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception as exc:
            warnings.append(f"Failed to parse scenario_replay.json: {exc}")
            return []

        scenarios = []
        for scenario in payload.get("scenarios", []):
            scenarios.append(
                {
                    "status": str(scenario.get("status", "unknown")),
                    "test_id": None,
                    "source_report": "verification/scenario_replay.json",
                    "file_paths": list(scenario.get("file_paths", [])),
                    "scenario_id": scenario.get("scenario_id"),
                }
            )
        return scenarios
