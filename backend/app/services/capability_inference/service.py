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
        modules = {m["module_id"]: m for m in graph_data.get("modules", []) if m.get("module_id")}
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

            # Modules that own routes in this group (narrow — used for attribution)
            route_linked_modules = {
                route["module"]
                for route in grouped_routes
                if route.get("module") in modules
                and modules[route["module"]].get("type") in {"router", "service"}
            }

            # Full display set: route-owning modules + transitive service modules
            linked_modules = sorted(
                route_linked_modules
                | {m for m in transitive_modules if m in modules and modules[m].get("type") == "service"}
            )

            if not linked_routes or not linked_modules:
                continue

            # Precise attribution: only this capability's route-owning modules matter
            overlap = route_linked_modules & direct_modules
            is_recently_changed = bool(overlap)
            overlap_count = len(overlap)

            capabilities.append(
                {
                    "capability_key": f"cap_{group_key}",
                    "name": self._display_name(group_key),
                    "status": "recently_changed" if is_recently_changed else "stable",
                    "linked_modules": linked_modules,
                    "linked_routes": linked_routes,
                    "reasoning_basis": {
                        "route_group": group_key,
                        "llm_reasoning_status": reasoning_status or "disabled",
                        "unverified_modules": sorted(m for m in linked_modules if m in unverified_impacts),
                    },
                    "_overlap_count": overlap_count,
                }
            )

        # Mark primary target: capability with highest overlap with directly changed modules
        max_overlap = max((c["_overlap_count"] for c in capabilities), default=0)
        for cap in capabilities:
            cap["is_primary_target"] = max_overlap > 0 and cap["_overlap_count"] == max_overlap
            del cap["_overlap_count"]

        return capabilities

    def _route_group_key(self, path: str) -> str:
        parts = [p for p in path.strip("/").split("/") if p and not p.startswith("{")]
        return parts[0].replace("-", "_") if parts else "root"

    def _display_name(self, group_key: str) -> str:
        return " ".join(part.capitalize() for part in group_key.split("_")) or "Root"
