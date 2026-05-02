from pathlib import Path

from app.services.test_management.agent_contract import AgentInstructionContractReader


COMPLETE_CONTRACT = """
# Agent Test Evidence Contract

New tests must use discoverable names such as Python `test_*` functions or JavaScript/TypeScript `test()` / `it()`.
Place tests under `tests/`, `__tests__/`, `.test.*`, `.spec.*`, or `test_*.py` paths.
When running tests, record the exact command, stdout, stderr, exit code, and individual test case names.
Write machine-readable test artifacts under `.agent-test-results/`, for example `--junitxml=.agent-test-results/pytest.xml`.
In the final response, list changed test cases, covered scenarios, test data, commands, and results.
"""


def test_contract_reader_accepts_complete_agent_instructions(tmp_path):
    (tmp_path / "AGENTS.md").write_text(COMPLETE_CONTRACT, encoding="utf-8")

    result = AgentInstructionContractReader(str(tmp_path)).read()

    assert result["present_files"] == ["AGENTS.md"]
    assert result["missing_requirements"] == []
    assert set(result["satisfied_requirements"]) == {
        "discoverable_test_names",
        "discoverable_test_paths",
        "test_command_logging",
        "machine_readable_results",
        "final_test_summary",
    }


def test_contract_reader_reports_missing_logging_and_artifact_requirements(tmp_path):
    (tmp_path / "CLAUDE.md").write_text(
        """
        Write tests when changing behavior.
        Use `test_*` names and place Python tests under `tests/`.
        """,
        encoding="utf-8",
    )

    result = AgentInstructionContractReader(str(tmp_path)).read()

    assert result["present_files"] == ["CLAUDE.md"]
    assert "test_command_logging" in result["missing_requirements"]
    assert "machine_readable_results" in result["missing_requirements"]
    assert any("exact command" in gap for gap in result["gaps"])
    assert any(".agent-test-results" in gap for gap in result["gaps"])


def test_contract_reader_reports_missing_instruction_files(tmp_path):
    result = AgentInstructionContractReader(str(tmp_path)).read()

    assert result["present_files"] == []
    assert "agent_instruction_file" in result["missing_requirements"]
    assert result["gaps"] == ["No AGENTS.md or CLAUDE.md file was found with agent test evidence guidance."]
