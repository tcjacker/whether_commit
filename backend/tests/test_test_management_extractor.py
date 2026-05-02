from app.schemas.assessment import TestCaseDetail, TestManagementSummary
from app.services.agentic_change_assessment.diff_parser import parse_unified_diff_hunks
from app.services.test_management.extractor import TestManagementExtractor


def _detail(path: str, diff: str, *, changed_symbols=None, related_tests=None, hunk_items=None):
    return {
        "file": {
            "file_id": path.replace("/", "_").replace(".", "_"),
            "path": path,
            "status": "modified",
            "additions": diff.count("\n+"),
            "deletions": diff.count("\n-"),
            "risk_level": "low",
            "coverage_status": "unknown",
            "review_status": "unreviewed",
            "agent_sources": ["git_diff"],
            "diff_fingerprint": "sha256:test",
        },
        "diff_hunks": parse_unified_diff_hunks(diff),
        "changed_symbols": changed_symbols or [],
        "related_agent_records": [],
        "related_tests": related_tests or [],
        "impact_facts": [],
        "agent_claims": [],
        "mismatches": [],
        "provenance_refs": [],
        "hunk_review_items": hunk_items or [],
        "file_assessment": {
            "why_changed": "",
            "impact_summary": "",
            "test_summary": "",
            "recommended_action": "",
            "generated_by": "rules",
            "agent_status": "not_run",
            "agent_source": None,
            "confidence": "low",
            "evidence_refs": [],
            "unknowns": [],
        },
        "review_state": {
            "review_status": "unreviewed",
            "diff_fingerprint": "sha256:test",
            "reviewer": None,
            "reviewed_at": None,
            "notes": [],
        },
    }


def test_extracts_added_python_test_case_with_certain_confidence():
    diff = """@@ -0,0 +1,6 @@
+def test_builder_emits_review_signals():
+    result = build_manifest()
+    assert result["review_decision"] == "needs_tests"
+    assert result["weak_test_evidence_count"] == 1
+
+def helper():
"""
    extractor = TestManagementExtractor()
    result = extractor.build(
        assessment_id="aca_ws",
        repo_key="demo",
        file_details={"cf_test": _detail("backend/tests/test_builder.py", diff)},
        changed_file_details={},
        review_graph_data={"nodes": [], "edges": []},
    )

    TestManagementSummary.model_validate(result["summary"])
    case = result["summary"]["files"][0]["test_cases"][0]
    detail = TestCaseDetail.model_validate(result["test_case_details"][case["test_case_id"]]).model_dump()

    assert case["name"] == "test_builder_emits_review_signals"
    assert case["status"] == "added"
    assert case["extraction_confidence"] == "certain"
    assert case["intent_summary"]["source"] == "rule_derived"
    assert case["intent_summary"]["basis"] == ["test_name", "assertions"]
    assert detail["assertions"][0]["content"].strip() == 'assert result["review_decision"] == "needs_tests"'
    assert detail["recommended_commands"][0]["command"] == "uv run pytest backend/tests/test_builder.py"
    assert detail["covered_scenarios"][0]["title"] == "Scenario named by test: test builder emits review signals."
    assert detail["covered_scenarios"][1]["title"] == 'Assertion checks: assert result["review_decision"] == "needs_tests"'


def test_attaches_historical_codex_test_result_only_for_matching_command_scope():
    diff = """@@ -0,0 +1,3 @@
+def test_builder_emits_review_signals():
+    result = build_manifest()
+    assert result["review_decision"] == "needs_tests"
"""
    extractor = TestManagementExtractor()
    result = extractor.build(
        assessment_id="aca_ws",
        repo_key="demo",
        file_details={"cf_test": _detail("backend/tests/test_builder.py", diff)},
        changed_file_details={},
        review_graph_data={"nodes": [], "edges": []},
        command_evidence=[
            {
                "command": "uv run pytest backend/tests/test_other.py",
                "stdout": "1 passed",
            },
            {
                "command": "uv run pytest backend/tests/test_builder.py",
                "stdout": "12 passed",
                "created_at": "2026-04-26T12:00:00Z",
            },
        ],
    )

    case = result["summary"]["files"][0]["test_cases"][0]
    detail = TestCaseDetail.model_validate(result["test_case_details"][case["test_case_id"]]).model_dump()

    assert len(detail["test_results"]) == 1
    historical = detail["test_results"][0]
    assert historical["source"] == "codex_command_log"
    assert historical["status"] == "passed"
    assert historical["captured_at"] == "2026-04-26T12:00:00Z"
    assert historical["analysis"]["basis"] == ["codex_command_log"]


def test_historical_codex_test_result_marks_missing_output_as_gap():
    diff = """@@ -0,0 +1,3 @@
+def test_builder_emits_review_signals():
+    result = build_manifest()
+    assert result["review_decision"] == "needs_tests"
"""
    extractor = TestManagementExtractor()
    result = extractor.build(
        assessment_id="aca_ws",
        repo_key="demo",
        file_details={"cf_test": _detail("backend/tests/test_builder.py", diff)},
        changed_file_details={},
        review_graph_data={"nodes": [], "edges": []},
        command_evidence=[{"command": "uv run pytest backend/tests/test_builder.py"}],
    )

    case = result["summary"]["files"][0]["test_cases"][0]
    detail = TestCaseDetail.model_validate(result["test_case_details"][case["test_case_id"]]).model_dump()

    assert detail["test_results"][0]["source"] == "codex_command_log"
    assert detail["test_results"][0]["status"] == "unknown"
    assert detail["test_results"][0]["analysis"]["coverage_gaps"] == ["command_seen_without_output"]


def test_agent_instruction_contract_gaps_are_exposed_as_test_unknowns():
    diff = """@@ -0,0 +1,3 @@
+def test_builder_emits_review_signals():
+    result = build_manifest()
+    assert result["review_decision"] == "needs_tests"
"""
    extractor = TestManagementExtractor()
    result = extractor.build(
        assessment_id="aca_ws",
        repo_key="demo",
        file_details={"cf_test": _detail("backend/tests/test_builder.py", diff)},
        changed_file_details={},
        review_graph_data={"nodes": [], "edges": []},
        agent_instruction_contract={
            "present_files": ["CLAUDE.md"],
            "satisfied_requirements": ["discoverable_test_names"],
            "missing_requirements": ["test_command_logging"],
            "gaps": ["Agent instructions should require logging the exact command, stdout, stderr, exit code, and individual test case names."],
        },
    )

    case = result["summary"]["files"][0]["test_cases"][0]
    detail = TestCaseDetail.model_validate(result["test_case_details"][case["test_case_id"]]).model_dump()

    assert "Agent instruction gap: Agent instructions should require logging the exact command, stdout, stderr, exit code, and individual test case names." in result["summary"]["unknowns"]
    assert "Agent instruction gap: Agent instructions should require logging the exact command, stdout, stderr, exit code, and individual test case names." in detail["unknowns"]


def test_extracts_modified_python_test_case_when_definition_is_context():
    diff = """@@ -1,5 +1,5 @@
 def test_builder_emits_review_signals():
     result = build_manifest()
-    assert result["review_decision"] == "needs_tests"
+    assert result["review_decision"] == "needs_recheck"
     assert result["weak_test_evidence_count"] == 1
"""
    extractor = TestManagementExtractor()
    result = extractor.build(
        assessment_id="aca_ws",
        repo_key="demo",
        file_details={"cf_test": _detail("backend/tests/test_builder.py", diff)},
        changed_file_details={},
        review_graph_data={"nodes": [], "edges": []},
    )

    case = result["summary"]["files"][0]["test_cases"][0]
    detail = result["test_case_details"][case["test_case_id"]]

    assert case["name"] == "test_builder_emits_review_signals"
    assert case["status"] == "modified"
    assert case["extraction_confidence"] == "certain"
    assert not case["name"].startswith("fallback_")
    assert detail["assertions"][0]["type"] == "remove"
    assert detail["assertions"][1]["type"] == "add"
    assert detail["test_case"]["intent_summary"]["source"] == "rule_derived"
    assert any("Assertion checks" in scenario["title"] for scenario in detail["covered_scenarios"])


def test_mixed_unsupported_javascript_cases_get_heuristic_and_fallback_entries():
    diff = """@@ -1,2 +1,8 @@
 describe("panel", () => {
+  it("renders evidence grade", () => {
+    expect(screen.getByText("direct")).toBeInTheDocument()
+  })
+  test.each([["claimed"], ["inferred"]])("renders %s", grade => {
+    expect(grade).toBeTruthy()
+  })
 })
"""
    extractor = TestManagementExtractor()
    result = extractor.build(
        assessment_id="aca_ws",
        repo_key="demo",
        file_details={"cf_test": _detail("frontend/src/pages/__tests__/TestChangesPage.test.tsx", diff)},
        changed_file_details={},
        review_graph_data={"nodes": [], "edges": []},
    )

    cases = result["summary"]["files"][0]["test_cases"]
    details = [result["test_case_details"][case["test_case_id"]] for case in cases]

    assert cases[0]["name"] == "renders evidence grade"
    assert cases[1]["name"].startswith("parameterized_case_")
    assert [case["extraction_confidence"] for case in cases] == ["heuristic", "fallback"]
    assert details[0]["assertions"][0]["content"].strip() == 'expect(screen.getByText("direct")).toBeInTheDocument()'
    assert details[0]["recommended_commands"][0]["command"] == "npm test -- renders evidence grade"
    assert "parameterized" in details[1]["unknowns"][0]
    assert any("parameterized" in unknown for unknown in result["summary"]["unknowns"])


def test_removed_javascript_simple_test_is_deleted_risk_signal():
    diff = """@@ -1,6 +1,2 @@
 describe("panel", () => {
-  it("renders evidence grade", () => {
-    expect(screen.getByText("direct")).toBeInTheDocument()
-  })
 })
"""
    extractor = TestManagementExtractor()
    result = extractor.build(
        assessment_id="aca_ws",
        repo_key="demo",
        file_details={"cf_test": _detail("frontend/src/pages/__tests__/TestChangesPage.test.tsx", diff)},
        changed_file_details={},
        review_graph_data={"nodes": [], "edges": []},
    )

    case = result["summary"]["files"][0]["test_cases"][0]
    detail = result["test_case_details"][case["test_case_id"]]

    assert case["name"] == "renders evidence grade"
    assert case["status"] == "deleted"
    assert case["extraction_confidence"] == "heuristic"
    assert detail["full_body"][0]["type"] == "remove"
    assert detail["assertions"][0]["type"] == "remove"
    assert "Deleted test case retained as risk signal." in detail["unknowns"]


def test_duplicate_test_names_get_distinct_ids_and_detail_records():
    diff = """@@ -0,0 +1,3 @@
+def test_renders_panel():
+    assert render_panel("summary")
+
@@ -10,0 +14,3 @@
+def test_renders_panel():
+    assert render_panel("detail")
+
"""
    extractor = TestManagementExtractor()
    result = extractor.build(
        assessment_id="aca_ws",
        repo_key="demo",
        file_details={"cf_test": _detail("backend/tests/test_panels.py", diff)},
        changed_file_details={},
        review_graph_data={"nodes": [], "edges": []},
    )

    cases = result["summary"]["files"][0]["test_cases"]
    case_ids = [case["test_case_id"] for case in cases]

    assert [case["name"] for case in cases] == ["test_renders_panel", "test_renders_panel"]
    assert len(case_ids) == 2
    assert len(set(case_ids)) == 2
    assert len(result["test_case_details"]) == 2
    assert set(result["test_case_details"]) == set(case_ids)


def test_deleted_test_case_is_kept_as_risk_signal():
    diff = """@@ -1,4 +0,0 @@
-def test_old_behavior_is_preserved():
-    response = client.get("/health")
-    assert response.status_code == 200
-
"""
    extractor = TestManagementExtractor()
    result = extractor.build(
        assessment_id="aca_ws",
        repo_key="demo",
        file_details={"cf_test": _detail("backend/tests/test_main.py", diff)},
        changed_file_details={},
        review_graph_data={"nodes": [], "edges": []},
    )

    case = result["summary"]["files"][0]["test_cases"][0]
    detail = result["test_case_details"][case["test_case_id"]]

    assert case["status"] == "deleted"
    assert case["extraction_confidence"] == "fallback"
    assert detail["full_body"][0]["type"] == "remove"
    assert detail["assertions"][0]["type"] == "remove"
    assert "Deleted test case" in detail["unknowns"][0]


def test_changed_symbol_name_match_produces_inferred_relationship_and_hunk_evidence():
    diff = """@@ -0,0 +1,3 @@
+def test_builder_links_changed_symbol():
+    assert "AgentClaim" in build_schema_fields()
"""
    changed_detail = _detail(
        "backend/app/schemas/assessment.py",
        "@@ -1,1 +1,2 @@\n class AgentClaim:\n+    pass\n",
        changed_symbols=["AgentClaim"],
        hunk_items=[
            {
                "hunk_id": "hunk_001",
                "file_id": "cf_schema",
                "path": "backend/app/schemas/assessment.py",
                "priority": 80,
                "risk_level": "medium",
                "reasons": ["Public API/type/config surface changed."],
                "fact_basis": ["changed symbol: AgentClaim"],
                "provenance_refs": [],
                "mismatch_ids": [],
            }
        ],
    )

    extractor = TestManagementExtractor()
    result = extractor.build(
        assessment_id="aca_ws",
        repo_key="demo",
        file_details={"cf_test": _detail("backend/tests/test_builder.py", diff)},
        changed_file_details={"cf_schema": changed_detail},
        review_graph_data={"nodes": [], "edges": []},
    )

    case = result["summary"]["files"][0]["test_cases"][0]
    detail = result["test_case_details"][case["test_case_id"]]

    assert detail["covered_changes"][0]["relationship"] == "names_changed_symbol"
    assert detail["covered_changes"][0]["evidence_grade"] == "inferred"
    assert detail["covered_changes"][0]["basis"] == ["test_body_names_changed_symbol"]
    assert detail["covered_changes"][0]["hunk_id"] == "hunk_001"
    assert case["evidence_grade"] == "inferred"
    assert case["weakest_evidence_grade"] == "inferred"
    assert case["highest_risk_covered_hunk_id"] == "hunk_001"
    assert case["covered_changes_preview"][0]["hunk_id"] == "hunk_001"


def test_no_name_match_without_graph_data_uses_unknown_relationship_boundary():
    diff = """@@ -0,0 +1,3 @@
+def test_builder_links_changed_symbol():
+    assert build_schema_fields()
"""
    changed_detail = _detail(
        "backend/app/schemas/assessment.py",
        "@@ -1,1 +1,2 @@\n class AgentClaim:\n+    pass\n",
        changed_symbols=["AgentClaim"],
        hunk_items=[
            {
                "hunk_id": "hunk_001",
                "file_id": "cf_schema",
                "path": "backend/app/schemas/assessment.py",
                "priority": 80,
                "risk_level": "medium",
                "reasons": ["Public API/type/config surface changed."],
                "fact_basis": ["changed symbol: AgentClaim"],
                "provenance_refs": [],
                "mismatch_ids": [],
            }
        ],
    )

    extractor = TestManagementExtractor()
    result = extractor.build(
        assessment_id="aca_ws",
        repo_key="demo",
        file_details={"cf_test": _detail("backend/tests/test_builder.py", diff)},
        changed_file_details={"cf_schema": changed_detail},
        review_graph_data={"nodes": [], "edges": []},
    )

    detail = next(iter(result["test_case_details"].values()))

    assert detail["covered_changes"][0]["relationship"] == "unknown"
    assert detail["covered_changes"][0]["evidence_grade"] == "unknown"
    assert detail["covered_changes"][0]["basis"] == ["graph_data_unavailable"]


def test_same_area_without_graph_support_stays_unknown():
    diff = """@@ -0,0 +1,3 @@
+def test_builder_checks_helper_behavior():
+    assert helper_result()
"""
    changed_detail = _detail(
        "backend/tests/helpers.py",
        "@@ -1,1 +1,2 @@\n def helper_result():\n+    return True\n",
        hunk_items=[
            {
                "hunk_id": "hunk_001",
                "file_id": "cf_helpers",
                "path": "backend/tests/helpers.py",
                "priority": 60,
                "risk_level": "medium",
                "reasons": ["Shared test helper changed."],
                "fact_basis": [],
                "provenance_refs": [],
                "mismatch_ids": [],
            }
        ],
    )

    extractor = TestManagementExtractor()
    result = extractor.build(
        assessment_id="aca_ws",
        repo_key="demo",
        file_details={"cf_test": _detail("backend/tests/test_builder.py", diff)},
        changed_file_details={"cf_helpers": changed_detail},
        review_graph_data={"nodes": [], "edges": []},
    )

    detail = next(iter(result["test_case_details"].values()))

    assert detail["covered_changes"][0]["relationship"] == "unknown"
    assert detail["covered_changes"][0]["evidence_grade"] == "unknown"
    assert "graph_data_unavailable" in detail["covered_changes"][0]["basis"]


def test_unsupportive_graph_data_stays_unknown_with_unavailable_basis():
    diff = """@@ -0,0 +1,3 @@
+def test_builder_checks_schema_behavior():
+    assert build_schema_fields()
"""
    changed_detail = _detail(
        "backend/app/schemas/assessment.py",
        "@@ -1,1 +1,2 @@\n class AgentClaim:\n+    pass\n",
        changed_symbols=["AgentClaim"],
        hunk_items=[
            {
                "hunk_id": "hunk_001",
                "file_id": "cf_schema",
                "path": "backend/app/schemas/assessment.py",
                "priority": 80,
                "risk_level": "medium",
                "reasons": ["Public API/type/config surface changed."],
                "fact_basis": ["changed symbol: AgentClaim"],
                "provenance_refs": [],
                "mismatch_ids": [],
            }
        ],
    )

    extractor = TestManagementExtractor()
    result = extractor.build(
        assessment_id="aca_ws",
        repo_key="demo",
        file_details={"cf_test": _detail("backend/tests/test_builder.py", diff)},
        changed_file_details={"cf_schema": changed_detail},
        review_graph_data={
            "nodes": [{"id": "unrelated"}],
            "edges": [{"source": "frontend/src/App.tsx", "target": "frontend/src/App.test.tsx"}],
        },
    )

    detail = next(iter(result["test_case_details"].values()))

    assert detail["covered_changes"][0]["relationship"] == "unknown"
    assert detail["covered_changes"][0]["evidence_grade"] == "unknown"
    assert "graph_data_unavailable" in detail["covered_changes"][0]["basis"]


def test_supportive_graph_edge_produces_graph_inferred_relationship():
    diff = """@@ -0,0 +1,3 @@
+def test_builder_checks_schema_behavior():
+    assert build_schema_fields()
"""
    changed_detail = _detail(
        "backend/app/schemas/assessment.py",
        "@@ -1,1 +1,2 @@\n class AgentClaim:\n+    pass\n",
        changed_symbols=["AgentClaim"],
        hunk_items=[
            {
                "hunk_id": "hunk_001",
                "file_id": "cf_schema",
                "path": "backend/app/schemas/assessment.py",
                "priority": 80,
                "risk_level": "medium",
                "reasons": ["Public API/type/config surface changed."],
                "fact_basis": ["changed symbol: AgentClaim"],
                "provenance_refs": [],
                "mismatch_ids": [],
            }
        ],
    )

    extractor = TestManagementExtractor()
    result = extractor.build(
        assessment_id="aca_ws",
        repo_key="demo",
        file_details={"cf_test": _detail("backend/tests/test_builder.py", diff)},
        changed_file_details={"cf_schema": changed_detail},
        review_graph_data={
            "nodes": [],
            "edges": [
                {
                    "source": "backend/tests/test_builder.py::test_builder_checks_schema_behavior",
                    "target": "backend/app/schemas/assessment.py::AgentClaim",
                }
            ],
        },
    )

    detail = next(iter(result["test_case_details"].values()))

    assert detail["covered_changes"][0]["relationship"] == "graph_inferred"
    assert detail["covered_changes"][0]["evidence_grade"] == "inferred"
    assert detail["covered_changes"][0]["basis"] == ["review_graph_edge"]


def test_unparsed_changed_test_hunk_uses_fallback_case_with_unknown_intent():
    diff = """@@ -1,2 +1,3 @@
 def helper():
+    assert shared_setup()
     return True
"""
    extractor = TestManagementExtractor()
    result = extractor.build(
        assessment_id="aca_ws",
        repo_key="demo",
        file_details={"cf_test": _detail("backend/tests/test_helpers.py", diff)},
        changed_file_details={},
        review_graph_data={"nodes": [], "edges": []},
    )

    case = result["summary"]["files"][0]["test_cases"][0]
    detail = result["test_case_details"][case["test_case_id"]]

    assert case["name"] == "fallback_hunk_001"
    assert case["extraction_confidence"] == "fallback"
    assert case["intent_summary"] == {"text": "", "source": "unknown", "basis": []}
    assert detail["unknowns"] == ["Could not identify individual test case from changed hunk."]
