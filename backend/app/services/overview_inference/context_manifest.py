from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple

from app.schemas.agent_harness import AgentHarnessReadRequest


@dataclass
class ContextManifest:
    entries: Dict[str, Dict[str, Any]]

    @classmethod
    def from_sources(
        cls,
        graph_data: Dict[str, Any],
        change_data: Dict[str, Any],
        verification_data: Dict[str, Any],
    ) -> "ContextManifest":
        changed_files = list(change_data.get("changed_files", []))
        changed_symbols = list(change_data.get("changed_symbols", []))
        file_contexts = change_data.get("file_contexts", {})
        evidence_by_path = verification_data.get("evidence_by_path", {})

        file_entries = {
            path: file_contexts.get(path, {"path": path})
            for path in changed_files
        }
        symbol_entries = {
            symbol_id: cls._find_symbol_payload(graph_data.get("symbols", []), symbol_id)
            for symbol_id in changed_symbols
        }
        verification_entries = {
            path: evidence_by_path[path]
            for path in changed_files
            if path in evidence_by_path
        }
        call_chain_entries = cls._build_call_chain_entries(graph_data, change_data)

        return cls(
            entries={
                "file": file_entries,
                "symbol": symbol_entries,
                "call_chain": call_chain_entries,
                "verification_context": verification_entries,
            }
        )

    @staticmethod
    def _find_symbol_payload(symbols: Iterable[Dict[str, Any]], symbol_id: str) -> Dict[str, Any]:
        for symbol in symbols:
            if symbol.get("symbol_id") == symbol_id or symbol.get("name") == symbol_id:
                return symbol
        return {"symbol_id": symbol_id}

    @staticmethod
    def _build_call_chain_entries(graph_data: Dict[str, Any], change_data: Dict[str, Any]) -> Dict[str, Any]:
        entries: Dict[str, Any] = {}
        dependencies = list(graph_data.get("dependencies", []))
        for module_id in change_data.get("directly_changed_modules", []):
            edges = [
                edge
                for edge in dependencies
                if edge.get("from") == module_id or edge.get("to") == module_id
            ]
            if edges:
                entries[module_id] = {"module_id": module_id, "edges": edges}
        return entries

    def to_prompt_manifest(self) -> Dict[str, List[str]]:
        return {
            target_type: sorted(values.keys())
            for target_type, values in self.entries.items()
            if values
        }

    def resolve_requests(
        self,
        read_requests: List[AgentHarnessReadRequest],
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        resolved_context: List[Dict[str, Any]] = []
        validation_issues: List[str] = []

        for request in read_requests:
            allowed_targets = self.entries.get(request.target_type, {})
            if request.target_id not in allowed_targets:
                validation_issues.append(f"target_not_allowed:{request.target_type}:{request.target_id}")
                continue

            resolved_context.append(
                {
                    "target_type": request.target_type,
                    "target_id": request.target_id,
                    "content": allowed_targets[request.target_id],
                }
            )

        return resolved_context, validation_issues
