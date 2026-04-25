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
        dependencies = list(graph_data.get("dependencies", []))

        route_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for route in routes:
            path = str(route.get("path", "")).strip()
            module_id = route.get("module")
            if not path or not module_id:
                continue
            route_groups[self._route_group_key(path)].append(route)

        direct_modules = set(change_data.get("directly_changed_modules", []))
        transitive_modules = set(change_data.get("transitively_affected_modules", []))
        changed_jobs = list(dict.fromkeys(change_data.get("changed_jobs", [])))
        changed_schemas = list(dict.fromkeys(change_data.get("changed_schemas", [])))
        unverified_impacts = {
            item.get("entity_id")
            for item in verification_data.get("unverified_impacts", [])
            if isinstance(item, dict) and item.get("entity_id")
        }
        reasoning_status = (agent_reasoning.get("llm_reasoning") or {}).get("status")

        capabilities: List[Dict[str, Any]] = []
        route_group_count = len(route_groups)
        for group_key, grouped_routes in sorted(route_groups.items()):
            route_linked_modules = {
                route["module"]
                for route in grouped_routes
                if route.get("module") in modules
                and modules[route["module"]].get("type") in {"router", "service"}
            }
            linked_routes = sorted(
                {
                    f"{route.get('method', 'GET')} {route.get('path')}"
                    for route in grouped_routes
                    if route.get("path")
                }
            )
            local_transitive_modules = self._route_local_transitive_service_modules(
                modules=modules,
                dependencies=dependencies,
                seed_modules=route_linked_modules,
                route_group_count=route_group_count,
            )
            linked_modules = self._expand_linked_modules(
                modules=modules,
                dependencies=dependencies,
                seed_modules=route_linked_modules | local_transitive_modules,
            )

            if not linked_routes or not linked_modules:
                continue

            overlap = route_linked_modules & direct_modules
            is_recently_changed = bool(overlap)
            overlap_count = len(overlap)

            capabilities.append(
                {
                    "capability_key": f"cap_{group_key}",
                    "name": self._display_name(group_key),
                    "source": "route",
                    "status": "recently_changed" if is_recently_changed else "stable",
                    "linked_modules": linked_modules,
                    "linked_routes": linked_routes,
                    "reasoning_basis": {
                        "source": "route",
                        "route_group": group_key,
                        "source_entities": linked_routes,
                        "source_modules": sorted(route_linked_modules),
                        "llm_reasoning_status": reasoning_status or "disabled",
                        "unverified_modules": sorted(m for m in linked_modules if m in unverified_impacts),
                    },
                    "_overlap_count": overlap_count,
                }
            )

        capabilities.extend(
            self._build_entrypoint_capabilities(
                modules=modules,
                dependencies=dependencies,
                direct_modules=direct_modules,
                transitive_modules=transitive_modules,
                changed_jobs=changed_jobs,
                changed_schemas=changed_schemas,
                unverified_impacts=unverified_impacts,
                reasoning_status=reasoning_status or "disabled",
            )
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

    def _expand_linked_modules(
        self,
        *,
        modules: Dict[str, Dict[str, Any]],
        dependencies: List[Dict[str, Any]],
        seed_modules: set[str],
    ) -> List[str]:
        adjacency: Dict[str, set[str]] = defaultdict(set)
        for dependency in dependencies:
            source = dependency.get("from")
            target = dependency.get("to")
            if not source or not target:
                continue
            adjacency[source].add(target)
            adjacency[target].add(source)

        linked_modules = {
            module_id
            for module_id in seed_modules
            if module_id in modules
        }
        for module_id in list(linked_modules):
            linked_modules.update(
                neighbor for neighbor in adjacency.get(module_id, set()) if neighbor in modules
            )
        return sorted(linked_modules)

    def _route_local_transitive_service_modules(
        self,
        *,
        modules: Dict[str, Dict[str, Any]],
        dependencies: List[Dict[str, Any]],
        seed_modules: set[str],
        route_group_count: int,
    ) -> set[str]:
        service_modules = {
            module_id
            for module_id in seed_modules
            if module_id in modules and modules[module_id].get("type") in {"router", "service"}
        }
        transitive_services = {
            module_id
            for module_id, module in modules.items()
            if module.get("type") == "service"
        }
        if route_group_count <= 1:
            return transitive_services

        adjacency: Dict[str, set[str]] = defaultdict(set)
        for dependency in dependencies:
            source = dependency.get("from")
            target = dependency.get("to")
            if not source or not target:
                continue
            adjacency[source].add(target)
            adjacency[target].add(source)

        local_transitives = set()
        for module_id in service_modules:
            for neighbor in adjacency.get(module_id, set()):
                if neighbor in transitive_services:
                    local_transitives.add(neighbor)
        return local_transitives

    def _build_entrypoint_capabilities(
        self,
        *,
        modules: Dict[str, Dict[str, Any]],
        dependencies: List[Dict[str, Any]],
        direct_modules: set[str],
        transitive_modules: set[str],
        changed_jobs: List[str],
        changed_schemas: List[str],
        unverified_impacts: set[str],
        reasoning_status: str,
    ) -> List[Dict[str, Any]]:
        capabilities: List[Dict[str, Any]] = []
        entrypoint_types = ("worker", "schema")
        source_entities_by_type = {
            "worker": changed_jobs,
            "schema": changed_schemas,
        }

        for module_id, module in sorted(modules.items()):
            module_type = module.get("type")
            if module_type not in entrypoint_types:
                continue
            if module_id not in direct_modules and module_id not in transitive_modules:
                continue

            source_entities = source_entities_by_type.get(module_type, [])
            linked_modules = self._expand_linked_modules(
                modules=modules,
                dependencies=dependencies,
                seed_modules={module_id},
            )
            if not linked_modules:
                continue

            overlap = {module_id} & direct_modules
            capability_key = f"cap_{module_type}_{module_id.removeprefix('mod_').replace('__', '_')}"
            display_name = self._display_name(module.get("name") or module_id.removeprefix("mod_"))
            capabilities.append(
                {
                    "capability_key": capability_key,
                    "name": display_name,
                    "source": module_type,
                    "status": "recently_changed" if overlap else "stable",
                    "linked_modules": linked_modules,
                    "linked_routes": [],
                    "reasoning_basis": {
                        "source": module_type,
                        "source_module": module_id,
                        "source_entities": list(source_entities),
                        "source_modules": [module_id],
                        "llm_reasoning_status": reasoning_status,
                        "unverified_modules": sorted(m for m in linked_modules if m in unverified_impacts),
                    },
                    "_overlap_count": len(overlap),
                }
            )

        return capabilities
