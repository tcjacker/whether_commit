import ast
import os
from typing import Any, Dict, List, Optional, Set


HTTP_METHOD_NAMES = {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"}
SCHEMA_BASE_NAMES = {"BaseModel", "SQLModel", "DeclarativeBase"}
SCHEMA_SUFFIXES = ("Schema", "Model", "Request", "Response", "Payload", "Record")


def expression_name(node: Optional[ast.AST]) -> Optional[str]:
    if node is None:
        return None
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return expression_name(node.func)
    if isinstance(node, ast.Subscript):
        return expression_name(node.value)
    return None


def collect_annotation_names(node: Optional[ast.AST]) -> Set[str]:
    names: Set[str] = set()
    if node is None:
        return names

    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
        elif isinstance(child, ast.Attribute):
            names.add(child.attr)
    return names


def is_route_handler(node: ast.AST) -> bool:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False

    for decorator in node.decorator_list:
        if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
            continue
        method_name = decorator.func.attr.upper()
        if method_name in HTTP_METHOD_NAMES:
            return True
    return False


def extract_route_metadata(node: ast.AST, relative_path: str) -> List[Dict[str, str]]:
    routes: List[Dict[str, str]] = []
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return routes

    for decorator in node.decorator_list:
        if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
            continue
        method_name = decorator.func.attr.upper()
        if method_name not in HTTP_METHOD_NAMES:
            continue

        path_value = ""
        if decorator.args and isinstance(decorator.args[0], ast.Constant) and isinstance(decorator.args[0].value, str):
            path_value = decorator.args[0].value
        routes.append(
            {
                "method": method_name,
                "path": path_value,
                "handler": node.name,
                "file_path": relative_path,
            }
        )
    return routes


def module_kind_from_path(relative_path: str, has_routes: bool = False) -> str:
    path_parts = [part.lower() for part in relative_path.split(os.sep)]
    file_stem = os.path.splitext(path_parts[-1])[0] if path_parts else ""

    if has_routes or any(part in {"api", "router", "routers", "routes"} for part in path_parts):
        return "router"
    if any("service" in part for part in path_parts) or file_stem.endswith("_service"):
        return "service"
    if any(("repo" in part or "repository" in part) for part in path_parts) or file_stem.endswith("_repo"):
        return "repository"
    if any(("schema" in part or "model" in part) for part in path_parts):
        return "schema"
    if any(("worker" in part or "job" in part or "task" in part) for part in path_parts):
        return "worker"
    return "module"


def classify_function_role(node: ast.AST, relative_path: str, container_role: Optional[str] = None) -> str:
    if is_route_handler(node):
        return "route_handler"
    if container_role in {"service", "repository", "worker"}:
        return container_role
    return module_kind_from_path(relative_path)


def classify_class_role(node: ast.ClassDef, relative_path: str) -> str:
    module_kind = module_kind_from_path(relative_path)
    if module_kind in {"service", "repository", "worker"}:
        return module_kind

    base_names = {expression_name(base) for base in node.bases}
    if any(base_name in SCHEMA_BASE_NAMES for base_name in base_names if base_name):
        return "schema"
    if node.name.endswith(SCHEMA_SUFFIXES):
        return "schema"
    if node.name.endswith(("Repository", "Repo")):
        return "repository"
    if node.name.endswith("Service"):
        return "service"
    if node.name.endswith(("Worker", "Job")):
        return "worker"
    return module_kind


def extract_python_file_entities(
    tree: ast.AST,
    relative_path: str,
) -> Dict[str, Any]:
    symbols: List[Dict[str, Any]] = []
    routes: List[Dict[str, str]] = []
    imports: List[str] = []
    imported_aliases: Dict[str, Dict[str, Any]] = {}
    entity_groups: Dict[str, List[str]] = {
        "route_handlers": [],
        "services": [],
        "repositories": [],
        "schemas": [],
        "workers": [],
    }
    data_objects: List[Dict[str, str]] = []

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
                alias_name = alias.asname or alias.name.split(".")[-1]
                imported_aliases[alias_name] = {"module": alias.name, "symbol": None, "kind": "module"}
            continue

        if isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            if node.level:
                relative_prefix = "." * node.level
                module_name = f"{relative_prefix}{module_name}" if module_name else relative_prefix
            if module_name:
                imports.append(module_name)
            for alias in node.names:
                if alias.name == "*":
                    continue
                imported_aliases[alias.asname or alias.name] = {
                    "module": module_name,
                    "symbol": alias.name,
                    "kind": "symbol",
                }
            continue

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            backend_role = classify_function_role(node, relative_path)
            symbols.append(
                {
                    "symbol_id": f"sym_{node.name}",
                    "name": node.name,
                    "kind": "function",
                    "file_path": relative_path,
                    "language": "python",
                    "backend_role": backend_role,
                }
            )
            if backend_role == "route_handler":
                entity_groups["route_handlers"].append(node.name)
                routes.extend(extract_route_metadata(node, relative_path))
            elif backend_role == "service":
                entity_groups["services"].append(node.name)
            elif backend_role == "repository":
                entity_groups["repositories"].append(node.name)
            elif backend_role == "worker":
                entity_groups["workers"].append(node.name)
            continue

        if isinstance(node, ast.ClassDef):
            backend_role = classify_class_role(node, relative_path)
            symbols.append(
                {
                    "symbol_id": f"sym_{node.name}",
                    "name": node.name,
                    "kind": "class",
                    "file_path": relative_path,
                    "language": "python",
                    "backend_role": backend_role,
                }
            )
            if backend_role == "service":
                entity_groups["services"].append(node.name)
            elif backend_role == "repository":
                entity_groups["repositories"].append(node.name)
            elif backend_role == "schema":
                entity_groups["schemas"].append(node.name)
                data_objects.append(
                    {
                        "data_object_id": f"obj_{node.name}",
                        "name": node.name,
                        "kind": "schema",
                        "file_path": relative_path,
                    }
                )
            elif backend_role == "worker":
                entity_groups["workers"].append(node.name)

    return {
        "symbols": symbols,
        "routes": routes,
        "imports": imports,
        "imported_aliases": imported_aliases,
        "entity_groups": {key: sorted(set(values)) for key, values in entity_groups.items()},
        "data_objects": data_objects,
    }
