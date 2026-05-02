from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


REQUIREMENT_GAPS = {
    "discoverable_test_names": "Agent instructions should require discoverable test names such as Python test_* or JS/TS test()/it().",
    "discoverable_test_paths": "Agent instructions should require tests to live under tests/, __tests__/, .test.*, .spec.*, or test_*.py paths.",
    "test_command_logging": "Agent instructions should require logging the exact command, stdout, stderr, exit code, and individual test case names.",
    "machine_readable_results": "Agent instructions should require machine-readable artifacts under .agent-test-results/.",
    "final_test_summary": "Agent instructions should require the final response to list changed test cases, covered scenarios, test data, commands, and results.",
}


class AgentInstructionContractReader:
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)

    def read(self) -> Dict[str, Any]:
        files = self._instruction_files()
        if not files:
            return {
                "present_files": [],
                "satisfied_requirements": [],
                "missing_requirements": ["agent_instruction_file"],
                "gaps": ["No AGENTS.md or CLAUDE.md file was found with agent test evidence guidance."],
            }

        combined = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in files).lower()
        satisfied = [
            requirement
            for requirement in REQUIREMENT_GAPS
            if self._satisfies(requirement, combined)
        ]
        missing = [requirement for requirement in REQUIREMENT_GAPS if requirement not in satisfied]
        return {
            "present_files": [path.name for path in files],
            "satisfied_requirements": satisfied,
            "missing_requirements": missing,
            "gaps": [REQUIREMENT_GAPS[requirement] for requirement in missing],
        }

    def _instruction_files(self) -> List[Path]:
        return [path for path in (self.workspace_path / "AGENTS.md", self.workspace_path / "CLAUDE.md") if path.exists()]

    def _satisfies(self, requirement: str, text: str) -> bool:
        checks = {
            "discoverable_test_names": lambda: "test_*" in text and ("test()" in text or "it()" in text),
            "discoverable_test_paths": lambda: all(token in text for token in ("tests/", "__tests__", ".test.", ".spec.", "test_*.py")),
            "test_command_logging": lambda: all(token in text for token in ("exact command", "stdout", "stderr", "exit code")) and "test case" in text,
            "machine_readable_results": lambda: ".agent-test-results" in text and ("junit" in text or "json" in text or "xml" in text),
            "final_test_summary": lambda: all(token in text for token in ("final response", "covered scenarios", "test data", "commands", "results")),
        }
        return checks[requirement]()
