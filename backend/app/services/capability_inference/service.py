from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List


class CapabilityInferenceService:
    def infer(
        self,
        graph_data: Dict[str, Any],
        change_data: Dict[str, Any],
        verification_data: Dict[str, Any],
        agent_reasoning: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        routes = list(graph_data.get("routes", []))
        modules = {module["module_id"]: module for module in graph_data.get("modules", []) if module.get("module_id")}
        if not routes:
            return []

        route_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for route in routes:
            path = str(route.get("path", "")).strip()
            module_id = route.get("module")
            if not path or not module_id:
                continue
            route_groups[self._route_group_key(path)].append(route)

        direct_modules = set(change_data.get("directly_changed_modules", []))
        transitive_modules = set(change_data.get("transitively_affected_modules", []))
        unverified_impacts = {
            item.get("entity_id")
            for item in verification_data.get("unverified_impacts", [])
            if isinstance(item, dict) and item.get("entity_id")
        }
        reasoning_status = (agent_reasoning.get("llm_reasoning") or {}).get("status")

        capabilities: List[Dict[str, Any]] = []
        for group_key, grouped_routes in sorted(route_groups.items()):
            linked_routes = sorted(
                {
                    f"{route.get('method', 'GET')} {route.get('path')}"
                    for route in grouped_routes
                    if route.get("path")
                }
            )
            linked_modules = sorted(
                {
                    route["module"]
                    for route in grouped_routes
                    if route.get("module") in modules
                    and modules[route["module"]].get("type") in {"router", "service"}
                }
                | direct_modules
                | {module_id for module_id in transitive_modules if module_id in modules and modules[module_id].get("type") == "service"}
            )
            if not linked_routes or not linked_modules:
                continue

            capabilities.append(
                {
                    "capability_key": f"cap_{group_key}",
                    "name": self._display_name(group_key),
                    "status": "recently_changed" if direct_modules or transitive_modules else "stable",
                    "linked_modules": linked_modules,
                    "linked_routes": linked_routes,
                    "reasoning_basis": {
                        "route_group": group_key,
                        "llm_reasoning_status": reasoning_status or "disabled",
                        "unverified_modules": sorted(module_id for module_id in linked_modules if module_id in unverified_impacts),
                    },
                }
            )

        return capabilities

    def _route_group_key(self, path: str) -> str:
        parts = [part for part in path.strip("/").split("/") if part and not part.startswith("{")]
        return parts[0].replace("-", "_") if parts else "root"

    def _display_name(self, group_key: str) -> str:
        return " ".join(part.capitalize() for part in group_key.split("_")) or "Root"
