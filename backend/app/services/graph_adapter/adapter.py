from typing import List, Dict, Any, Set
import os
import ast

from .call_flow import extract_backend_flow_edges
from .entity_extractors import extract_python_file_entities, module_kind_from_path

class GraphAdapter:
    """
    Adapter for integrating with CodeGraphContext.
    Responsible for generating the unified graph snapshot.
    In this MVP, we implement a lightweight Python AST parser to simulate a real external tool.
    """
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path

    def _parse_python_file(self, file_path: str) -> Dict[str, Any]:
        """Parses a single Python file to extract backend entities and import hints."""
        relative_path = os.path.relpath(file_path, self.workspace_path)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content)
            file_facts = extract_python_file_entities(tree, relative_path)
            file_facts["tree"] = tree
            file_facts["relative_path"] = relative_path
            return file_facts
        except Exception:
            # Skip unparseable files
            return {
                "symbols": [],
                "routes": [],
                "imports": [],
                "imported_aliases": {},
                "entity_groups": {
                    "route_handlers": [],
                    "services": [],
                    "repositories": [],
                    "schemas": [],
                    "workers": [],
                },
                "data_objects": [],
                "tree": None,
                "relative_path": relative_path,
            }

    def _infer_module_type(self, module_name: str, has_routes: bool) -> str:
        return module_kind_from_path(module_name, has_routes=has_routes)

    def _module_id_from_root(self, root: str) -> str:
        rel_root = os.path.relpath(root, self.workspace_path)
        if rel_root in {".", ""}:
            rel_root = "root"
        parts = [part for part in rel_root.split(os.sep) if part and part not in {".", ".."}]
        slug = "__".join(parts) if parts else "root"
        return f"mod_{slug}"

    def _module_aliases_from_root(self, root: str) -> Set[str]:
        rel_root = os.path.relpath(root, self.workspace_path)
        if rel_root in {".", ""}:
            rel_root = "root"
        parts = [part for part in rel_root.split(os.sep) if part and part not in {".", ".."}]
        aliases = {"root" if not parts else parts[-1]}
        if parts:
            aliases.add(".".join(parts))
            aliases.add("/".join(parts))
            aliases.add("__".join(parts))
        return aliases

    def _module_name_from_root(self, root: str) -> str:
        rel_root = os.path.relpath(root, self.workspace_path)
        if rel_root in {".", ""}:
            return "root"
        parts = [part for part in rel_root.split(os.sep) if part and part not in {".", ".."}]
        return parts[-1] if parts else "root"

    def _resolve_import_targets(
        self,
        import_name: str,
        module_lookup: Dict[str, Set[str]],
        current_module_id: str,
        module_catalog: Dict[str, Dict[str, Any]],
    ) -> Set[str]:
        candidates: Set[str] = set()
        trimmed = import_name.lstrip(".")
        if not trimmed:
            return candidates

        parts = [part for part in trimmed.split(".") if part]
        if not parts:
            return candidates

        prefix_parts: List[str] = []
        for part in parts:
            prefix_parts.append(part)
            prefix_key = ".".join(prefix_parts)
            for target_module_id in module_lookup.get(prefix_key, set()):
                if target_module_id != current_module_id:
                    candidates.add(target_module_id)

        for part in parts:
            for target_module_id in module_lookup.get(part, set()):
                if target_module_id != current_module_id:
                    candidates.add(target_module_id)

        for module_id, module_info in module_catalog.items():
            module_parts = module_info["path_parts"]
            if len(module_parts) >= len(parts):
                continue
            if parts[: len(module_parts)] == module_parts and module_id != current_module_id:
                candidates.add(module_id)

        return candidates

    def _unique_dependencies(self, dependencies: List[Dict[str, str]]) -> List[Dict[str, str]]:
        seen = set()
        result = []
        for dependency in dependencies:
            key = (dependency["from"], dependency["to"], dependency["type"])
            if key in seen:
                continue
            seen.add(key)
            result.append(dependency)
        return result

    def _execute_code_graph_context(self) -> Dict[str, Any]:
        """
        Scans the workspace directory and builds a real dependency graph.
        """
        if not os.path.exists(self.workspace_path):
            raise FileNotFoundError(f"Workspace path not found: {self.workspace_path}")

        modules = []
        all_symbols = []
        all_routes = []
        all_data_objects = []
        dependencies = []
        module_imports: Dict[str, Set[str]] = {}
        module_lookup: Dict[str, Set[str]] = {}
        module_catalog: Dict[str, Dict[str, Any]] = {}
        parsed_files: List[Dict[str, Any]] = []
        
        # Walk through the workspace
        for root, _, files in os.walk(self.workspace_path):
            # Skip hidden dirs like .git or __pycache__
            if any(part.startswith('.') or part == '__pycache__' for part in root.split(os.sep)):
                continue
                
            module_files = []
            module_symbols = []
            module_id = self._module_id_from_root(root)
            module_name = self._module_name_from_root(root)
            
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.workspace_path)
                    module_files.append(rel_path)
                    
                    parsed = self._parse_python_file(full_path)
                    parsed["module_id"] = module_id
                    parsed["module_name"] = module_name
                    parsed_files.append(parsed)
                    for sym in parsed["symbols"]:
                        sym["module"] = module_id
                        module_symbols.append(sym["symbol_id"])
                    
                    for route in parsed["routes"]:
                        route["module"] = module_id
                        
                    all_symbols.extend(parsed["symbols"])
                    all_routes.extend(parsed["routes"])
                    for data_object in parsed.get("data_objects", []):
                        data_object["module"] = module_id
                        all_data_objects.append(data_object)
                    module_imports.setdefault(module_id, set()).update(parsed["imports"])
            
            # If a directory has python files, treat it as a module
            if module_files:
                rel_root = os.path.relpath(root, self.workspace_path)
                rel_parts = [part for part in rel_root.split(os.sep) if part and part not in {".", ".."}]
                module_catalog[module_id] = {
                    "name": module_name,
                    "path_parts": rel_parts if rel_parts else ["root"],
                }
                for alias in self._module_aliases_from_root(root):
                    module_lookup.setdefault(alias, set()).add(module_id)
                modules.append({
                    "module_id": module_id,
                    "name": module_name,
                    "type": self._infer_module_type(rel_root, has_routes=bool([route for route in all_routes if route["module"] == module_id])),
                    "files": module_files,
                    "linked_symbols": module_symbols
                })

        module_types = {module["module_id"]: module["type"] for module in modules}

        for module in modules:
            current_module_id = module["module_id"]
            for import_name in module_imports.get(current_module_id, set()):
                for target_module_id in self._resolve_import_targets(
                    import_name,
                    module_lookup,
                    current_module_id,
                    module_catalog,
                ):
                    dependencies.append({
                        "from": current_module_id,
                        "to": target_module_id,
                        "type": "imports",
                    })

        for parsed in parsed_files:
            resolved_imports: Dict[str, Set[str]] = {}
            current_module_id = parsed["module_id"]
            for alias_name, import_meta in parsed.get("imported_aliases", {}).items():
                raw_module_name = import_meta.get("module", "")
                if not raw_module_name:
                    continue
                target_module_ids = self._resolve_import_targets(
                    raw_module_name,
                    module_lookup,
                    current_module_id,
                    module_catalog,
                )
                if target_module_ids:
                    resolved_imports[alias_name] = target_module_ids
            parsed["resolved_imports"] = resolved_imports
            dependencies.extend(
                extract_backend_flow_edges(
                    file_fact=parsed,
                    module_types=module_types,
                )
            )

        return {
            "modules": modules,
            "symbols": all_symbols,
            "routes": all_routes,
            "dependencies": self._unique_dependencies(dependencies),
            "relationships": [
                {
                    "source": dependency["from"],
                    "target": dependency["to"],
                    "type": dependency["type"],
                }
                for dependency in self._unique_dependencies(dependencies)
            ],
            "data_objects": all_data_objects,
            "integrations": []  # Skipped for MVP
        }

    def generate_graph_snapshot(self) -> Dict[str, Any]:
        """
        Main entry point for JobManager to build the graph snapshot.
        """
        try:
            raw_data = self._execute_code_graph_context()
            # Here we could normalize raw_data if needed
            return raw_data
        except Exception as e:
            raise RuntimeError(f"Failed to generate graph snapshot: {str(e)}")
