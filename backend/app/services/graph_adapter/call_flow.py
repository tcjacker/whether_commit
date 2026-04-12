import ast
from typing import Any, Dict, List, Optional, Set

from .entity_extractors import (
    classify_class_role,
    classify_function_role,
    collect_annotation_names,
    expression_name,
)


READ_VERBS = ("get", "list", "fetch", "find", "load", "read", "query", "select")
WRITE_VERBS = ("create", "save", "insert", "update", "delete", "remove", "upsert", "write", "persist", "commit")


def _is_read_verb(name: str) -> bool:
    lowered = name.lower()
    return lowered.startswith(READ_VERBS)


def _is_write_verb(name: str) -> bool:
    lowered = name.lower()
    return lowered.startswith(WRITE_VERBS)


def _edge_type_for_call(
    current_module_type: str,
    current_role: str,
    target_module_type: str,
    callee_name: str,
    from_annotation: bool = False,
) -> Optional[str]:
    if target_module_type == "schema":
        if from_annotation and (current_role == "route_handler" or current_module_type == "router"):
            return "validates"
        return "transforms"

    if target_module_type == "repository":
        if _is_write_verb(callee_name):
            return "writes"
        if _is_read_verb(callee_name):
            return "reads"
        return "calls"

    if target_module_type in {"service", "worker"}:
        return "calls"

    return None


def _assignment_targets(node: ast.AST) -> List[str]:
    if isinstance(node, ast.Assign):
        targets: List[str] = []
        for target in node.targets:
            if isinstance(target, ast.Name):
                targets.append(target.id)
        return targets
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return [node.target.id]
    return []


def _bind_instance_targets(
    function_node: ast.AST,
    resolved_imports: Dict[str, Set[str]],
) -> Dict[str, Set[str]]:
    bindings: Dict[str, Set[str]] = {}

    for node in ast.walk(function_node):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = getattr(node, "value", None)
        if not isinstance(value, ast.Call):
            continue

        target_aliases: Set[str] = set()
        if isinstance(value.func, ast.Name) and value.func.id in resolved_imports:
            target_aliases = set(resolved_imports[value.func.id])
        elif isinstance(value.func, ast.Attribute) and isinstance(value.func.value, ast.Name):
            base_name = value.func.value.id
            if base_name in resolved_imports:
                target_aliases = set(resolved_imports[base_name])

        if not target_aliases:
            continue

        for target_name in _assignment_targets(node):
            bindings[target_name] = set(target_aliases)

    return bindings


def _annotation_edges(
    function_node: ast.AST,
    current_module_id: str,
    current_module_type: str,
    current_role: str,
    resolved_imports: Dict[str, Set[str]],
    module_types: Dict[str, str],
) -> List[Dict[str, str]]:
    annotation_names: Set[str] = set()

    if isinstance(function_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        annotation_names.update(collect_annotation_names(function_node.returns))
        for arg in list(function_node.args.args) + list(function_node.args.kwonlyargs):
            annotation_names.update(collect_annotation_names(arg.annotation))
        if function_node.args.vararg:
            annotation_names.update(collect_annotation_names(function_node.args.vararg.annotation))
        if function_node.args.kwarg:
            annotation_names.update(collect_annotation_names(function_node.args.kwarg.annotation))

    edges: List[Dict[str, str]] = []
    for annotation_name in annotation_names:
        for target_module_id in resolved_imports.get(annotation_name, set()):
            edge_type = _edge_type_for_call(
                current_module_type=current_module_type,
                current_role=current_role,
                target_module_type=module_types.get(target_module_id, "module"),
                callee_name=annotation_name,
                from_annotation=True,
            )
            if edge_type:
                edges.append({"from": current_module_id, "to": target_module_id, "type": edge_type})
    return edges


def _call_edges(
    function_node: ast.AST,
    current_module_id: str,
    current_module_type: str,
    current_role: str,
    resolved_imports: Dict[str, Set[str]],
    module_types: Dict[str, str],
) -> List[Dict[str, str]]:
    instance_bindings = _bind_instance_targets(function_node, resolved_imports)
    edges: List[Dict[str, str]] = []

    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call):
            continue

        target_module_ids: Set[str] = set()
        callee_name = expression_name(node.func) or ""

        if isinstance(node.func, ast.Name) and node.func.id in resolved_imports:
            target_module_ids = set(resolved_imports[node.func.id])
            callee_name = node.func.id
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            base_name = node.func.value.id
            if base_name in instance_bindings:
                target_module_ids = set(instance_bindings[base_name])
                callee_name = node.func.attr
            elif base_name in resolved_imports:
                target_module_ids = set(resolved_imports[base_name])
                callee_name = node.func.attr

        if not target_module_ids:
            continue

        for target_module_id in target_module_ids:
            edge_type = _edge_type_for_call(
                current_module_type=current_module_type,
                current_role=current_role,
                target_module_type=module_types.get(target_module_id, "module"),
                callee_name=callee_name,
            )
            if edge_type:
                edges.append({"from": current_module_id, "to": target_module_id, "type": edge_type})

    return edges


def _iter_callable_nodes(tree: ast.AST, relative_path: str) -> List[Dict[str, Any]]:
    callables: List[Dict[str, Any]] = []

    for node in getattr(tree, "body", []):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            callables.append({"node": node, "container_role": None})
        elif isinstance(node, ast.ClassDef):
            class_role = classify_class_role(node, relative_path)
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    callables.append({"node": child, "container_role": class_role})

    return callables


def extract_backend_flow_edges(
    *,
    file_fact: Dict[str, Any],
    module_types: Dict[str, str],
) -> List[Dict[str, str]]:
    tree = file_fact.get("tree")
    if tree is None:
        return []

    current_module_id = file_fact["module_id"]
    current_module_type = module_types.get(current_module_id, "module")
    resolved_imports: Dict[str, Set[str]] = file_fact.get("resolved_imports", {})
    relative_path = file_fact.get("relative_path", "")

    edges: List[Dict[str, str]] = []
    for callable_info in _iter_callable_nodes(tree, relative_path):
        function_node = callable_info["node"]
        current_role = classify_function_role(
            function_node,
            relative_path,
            container_role=callable_info["container_role"],
        )
        edges.extend(
            _annotation_edges(
                function_node=function_node,
                current_module_id=current_module_id,
                current_module_type=current_module_type,
                current_role=current_role,
                resolved_imports=resolved_imports,
                module_types=module_types,
            )
        )
        edges.extend(
            _call_edges(
                function_node=function_node,
                current_module_id=current_module_id,
                current_module_type=current_module_type,
                current_role=current_role,
                resolved_imports=resolved_imports,
                module_types=module_types,
            )
        )

    return edges
