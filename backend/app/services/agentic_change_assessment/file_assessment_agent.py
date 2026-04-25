from __future__ import annotations

from typing import Any, Dict, List

from app.services.agentic_change_assessment.codex_file_assessment import (
    CodexFileAssessmentAdapter,
    DisabledCodexFileAssessmentAdapter,
)


class FileAssessmentAgent:
    """
    Builds per-file review narratives from canonical facts plus captured agent evidence.

    This is intentionally local and deterministic for Phase 1. It behaves like an
    agentic assessment layer without making the rule facts depend on an external LLM.
    """

    def __init__(self, codex_adapter: CodexFileAssessmentAdapter | None = None) -> None:
        self.codex_adapter = codex_adapter or DisabledCodexFileAssessmentAdapter()

    def build(
        self,
        *,
        path: str,
        stats: Dict[str, Any],
        coverage_status: str,
        related_tests: List[Dict[str, Any]],
        related_agent_records: List[Dict[str, Any]],
        change_data: Dict[str, Any],
        impact_facts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        rule_assessment = {
            "why_changed": self._why_changed(path, related_agent_records, change_data, stats),
            "impact_summary": self._impact_summary(path, change_data, impact_facts),
            "test_summary": self._test_summary(related_tests, coverage_status),
            "recommended_action": self._recommended_action(stats, coverage_status, related_tests),
            "generated_by": "rules",
            "agent_status": "not_run",
            "agent_source": None,
            "confidence": self._confidence(related_agent_records, related_tests, impact_facts),
            "evidence_refs": self._evidence_refs(related_agent_records, related_tests, impact_facts),
            "unknowns": ["Codex agent assessment has not run."],
        }
        codex_assessment = self.codex_adapter.assess(
            {
                "path": path,
                "stats": stats,
                "coverage_status": coverage_status,
                "related_tests": related_tests,
                "related_agent_records": related_agent_records,
                "change_data": change_data,
                "impact_facts": impact_facts,
                "rule_assessment": rule_assessment,
            }
        )
        if codex_assessment:
            return {
                **rule_assessment,
                **codex_assessment,
                "generated_by": "codex_agent",
                "agent_status": "accepted",
                "agent_source": "codex",
            }
        return rule_assessment

    def _recommended_action(
        self,
        stats: Dict[str, Any],
        coverage_status: str,
        related_tests: List[Dict[str, Any]],
    ) -> str:
        added = int(stats.get("added_lines", 0) or 0)
        deleted = int(stats.get("deleted_lines", 0) or 0)
        change_type = stats.get("change_type", "changed file")
        size = f"{added} added / {deleted} deleted"
        test_statuses = sorted({test.get("last_status", "unknown") for test in related_tests})
        test_phrase = ", ".join(test_statuses) if test_statuses else "no linked test status"

        if coverage_status == "missing":
            return f"Review first: {change_type}, {size}, missing primary test coverage."
        if coverage_status == "covered":
            return f"Review diff semantics: {change_type}, {size}, linked tests are {test_phrase}."
        if coverage_status == "partial":
            return f"Review changed behavior and test gaps: {change_type}, {size}, partial coverage."
        return f"Review manually: {change_type}, {size}, coverage evidence is unknown."

    def _why_changed(
        self,
        path: str,
        related_agent_records: List[Dict[str, Any]],
        change_data: Dict[str, Any],
        stats: Dict[str, Any],
    ) -> str:
        evidence = self._agent_activity_for_path(path, change_data)
        if evidence:
            return " | ".join(evidence[:3])

        record_reasons: List[str] = []
        for record in related_agent_records:
            source = record.get("source", "agent")
            for field in ("declared_intent", "reasoning_summary", "task_summary"):
                value = str(record.get(field, "")).strip()
                if value:
                    record_reasons.append(f"{source}: {value}")
                    break
        if record_reasons:
            return " | ".join(record_reasons[:3])

        snippets = [str(item) for item in stats.get("snippets", []) if item]
        if snippets:
            return f"Derived from diff snippets: {'; '.join(snippets[:3])}"
        return "No structured agent reason is available; assessment is based on git diff facts."

    def _impact_summary(
        self,
        path: str,
        change_data: Dict[str, Any],
        impact_facts: List[Dict[str, Any]],
    ) -> str:
        symbols = self._symbols_for_path(path, change_data)
        direct_impacts = self._direct_impacts_for_path(path, change_data)
        parts: List[str] = []

        if symbols:
            parts.append(f"Changed symbols: {', '.join(symbols[:5])}")
        if direct_impacts:
            impact_text = ", ".join(
                f"{item.get('reason', 'impact')} -> {item.get('entity_id', 'unknown')}"
                for item in direct_impacts[:3]
            )
            parts.append(f"Impact evidence: {impact_text}")
        if impact_facts and not direct_impacts:
            parts.append(f"Graph evidence available: {len(impact_facts)} nearby node(s)")
        if not parts:
            parts.append("Impact is limited to file-level diff facts; no symbol or graph evidence was linked.")
        return " | ".join(parts)

    def _test_summary(self, related_tests: List[Dict[str, Any]], coverage_status: str) -> str:
        if not related_tests:
            return f"No related test evidence was found; coverage status: {coverage_status}."

        statuses = self._counts(test.get("last_status", "unknown") for test in related_tests)
        relationships = self._counts(test.get("relationship", "inferred") for test in related_tests)
        status_text = ", ".join(f"{count} {name}" for name, count in statuses.items())
        relationship_text = ", ".join(f"{count} {name}" for name, count in relationships.items())
        plural = "test" if len(related_tests) == 1 else "tests"
        return (
            f"{len(related_tests)} related {plural}; statuses: {status_text}; "
            f"relationships: {relationship_text}; coverage status: {coverage_status}."
        )

    def _agent_activity_for_path(self, path: str, change_data: Dict[str, Any]) -> List[str]:
        evidence: List[str] = []
        for item in change_data.get("agent_activity_evidence", []):
            if not isinstance(item, dict):
                continue
            if path not in item.get("related_files", []):
                continue
            summary = str(item.get("summary", "")).strip()
            if summary:
                evidence.append(f"{item.get('source', 'agent')}: {summary}")
        return self._unique(evidence)

    def _symbols_for_path(self, path: str, change_data: Dict[str, Any]) -> List[str]:
        module_hint = path.removesuffix(".py").replace("/", ".")
        symbols = [
            symbol
            for symbol in change_data.get("changed_symbols", [])
            if isinstance(symbol, str) and (module_hint in symbol or symbol.split(".")[-1])
        ]
        return self._unique(symbols)

    def _direct_impacts_for_path(self, path: str, change_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        impacts: List[Dict[str, Any]] = []
        for item in change_data.get("direct_impacts", []):
            if not isinstance(item, dict):
                continue
            evidence = item.get("evidence", {})
            files = evidence.get("files", []) if isinstance(evidence, dict) else []
            if path in files:
                impacts.append(item)
        return impacts

    def _counts(self, values: Any) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for value in values:
            name = str(value or "unknown")
            counts[name] = counts.get(name, 0) + 1
        return counts

    def _confidence(
        self,
        related_agent_records: List[Dict[str, Any]],
        related_tests: List[Dict[str, Any]],
        impact_facts: List[Dict[str, Any]],
    ) -> str:
        has_agent_record = any(record.get("source") not in {"git_diff", ""} for record in related_agent_records)
        has_tests = bool(related_tests)
        has_impact = bool(impact_facts)
        if has_agent_record and has_tests and has_impact:
            return "high"
        if has_agent_record or (has_tests and has_impact):
            return "medium"
        return "low"

    def _evidence_refs(
        self,
        related_agent_records: List[Dict[str, Any]],
        related_tests: List[Dict[str, Any]],
        impact_facts: List[Dict[str, Any]],
    ) -> List[str]:
        refs: List[str] = ["git_diff"]
        for record in related_agent_records:
            refs.extend(str(item) for item in record.get("evidence_sources", []) if item)
        if related_tests:
            refs.append("verification")
        if impact_facts:
            refs.append("review_graph")
        return self._unique(refs)

    def _unique(self, values: List[str]) -> List[str]:
        result: List[str] = []
        for value in values:
            if value and value not in result:
                result.append(value)
        return result
