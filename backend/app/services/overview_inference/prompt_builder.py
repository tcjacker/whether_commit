from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping


class ReasoningPromptBuilder:
    """
    Build a bounded, structured prompt payload from normalized facts only.

    The payload is intentionally narrow: the LLM only receives curated facts,
    capped collections, and a fixed output contract.
    """

    MAX_ITEMS = 25
    MAX_EDGES = 40
    MAX_EVIDENCE_ITEMS = 25
    MAX_STRING_LENGTH = 240

    def build(
        self,
        graph_data: Dict[str, Any],
        change_data: Dict[str, Any],
        verification_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        normalized_facts = {
            "changed_files": self._bounded_strings(change_data.get("changed_files", [])),
            "changed_symbols": self._bounded_strings(change_data.get("changed_symbols", [])),
            "changed_routes": self._bounded_strings(change_data.get("changed_routes", [])),
            "changed_schemas": self._bounded_strings(change_data.get("changed_schemas", [])),
            "changed_jobs": self._bounded_strings(change_data.get("changed_jobs", [])),
            "direct_impacts": self._bounded_strings(
                change_data.get("directly_changed_modules", change_data.get("direct_impacts", []))
            ),
            "transitive_impacts": self._bounded_strings(
                change_data.get("transitively_affected_modules", change_data.get("transitive_impacts", []))
            ),
            "graph_edges": self._bounded_edges(graph_data),
            "verification_evidence": self._bounded_mapping(verification_data.get("evidence_by_path", {})),
            "unknowns": self._derive_unknowns(graph_data, verification_data),
        }

        return {
            "task": "backend_overview_reasoning",
            "normalized_facts": normalized_facts,
            "output_contract": {
                "required_fields": [
                    "technical_change_summary",
                    "change_types",
                    "risk_factors",
                    "review_recommendations",
                    "why_impacted",
                    "confidence",
                    "unknowns",
                    "validation_gaps",
                    "evidence_used",
                ],
                "confidence_levels": ["high", "medium", "low"],
            },
            "constraints": [
                "Use only normalized_facts.",
                "Do not invent entities that are not present in normalized_facts.",
                "Preserve unknowns explicitly when evidence is missing.",
                "In evidence_used, cite only specific values from normalized_facts such as file paths, module IDs, route strings, schema names, job names, graph edge endpoints, or verification evidence keys.",
                "Do not cite field names, container names, or paths like normalized_facts.changed_files in evidence_used.",
                "Return all natural-language fields in Simplified Chinese.",
                "Return structured JSON only.",
            ],
        }

    def _bounded_strings(self, values: Iterable[Any]) -> List[str]:
        bounded: List[str] = []
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if not text:
                continue
            bounded.append(text[: self.MAX_STRING_LENGTH])
            if len(bounded) >= self.MAX_ITEMS:
                break
        return bounded

    def _bounded_edges(self, graph_data: Dict[str, Any]) -> List[Dict[str, str]]:
        edges: List[Dict[str, str]] = []
        for edge in graph_data.get("dependencies", graph_data.get("relationships", [])):
            source = edge.get("from") or edge.get("source")
            target = edge.get("to") or edge.get("target")
            edge_type = edge.get("type", "dependency")
            if not source or not target:
                continue
            edges.append(
                {
                    "from": str(source)[: self.MAX_STRING_LENGTH],
                    "to": str(target)[: self.MAX_STRING_LENGTH],
                    "type": str(edge_type)[: self.MAX_STRING_LENGTH],
                }
            )
            if len(edges) >= self.MAX_EDGES:
                break
        return edges

    def _bounded_mapping(self, mapping: Mapping[str, Any]) -> Dict[str, Any]:
        bounded: Dict[str, Any] = {}
        for key, value in list(mapping.items())[: self.MAX_EVIDENCE_ITEMS]:
            bounded[str(key)[: self.MAX_STRING_LENGTH]] = self._sanitize_value(value)
        return bounded

    def _sanitize_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(k)[: self.MAX_STRING_LENGTH]: self._sanitize_value(v) for k, v in list(value.items())[:10]}
        if isinstance(value, list):
            return [self._sanitize_value(item) for item in value[:10]]
        if isinstance(value, tuple):
            return [self._sanitize_value(item) for item in list(value)[:10]]
        if isinstance(value, (str, int, float, bool)) or value is None:
            if isinstance(value, str):
                return value[: self.MAX_STRING_LENGTH]
            return value
        return str(value)[: self.MAX_STRING_LENGTH]

    def _derive_unknowns(self, graph_data: Dict[str, Any], verification_data: Dict[str, Any]) -> List[str]:
        unknowns: List[str] = []
        if not graph_data.get("dependencies") and not graph_data.get("relationships"):
            unknowns.append("依赖图缺失，因此传递影响只能保持保守推断。")
        if not verification_data.get("affected_tests"):
            unknowns.append("变更面缺少验证证据。")
        if not verification_data.get("evidence_by_path"):
            unknowns.append("未提供路径级验证证据。")
        return unknowns
