from __future__ import annotations

import ast
from typing import Dict, List, Set


SCHEMA_NAME_SUFFIXES = (
    "Schema",
    "Request",
    "Response",
    "Payload",
    "DTO",
    "Model",
)

DATA_OBJECT_NAME_SUFFIXES = (
    "Entity",
    "Record",
    "Item",
    "Document",
    "State",
    "Object",
    "Model",
)


def _node_overlaps(node: ast.AST, changed_lines: Set[int], include_all: bool) -> bool:
    if include_all:
        return True

    start = getattr(node, "lineno", None)
    end = getattr(node, "end_lineno", start)
    if start is None:
        return False

    return any(line in changed_lines for line in range(start, (end or start) + 1))


def _decorator_names(node: ast.ClassDef) -> Set[str]:
    names: Set[str] = set()
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name):
            names.add(decorator.id)
        elif isinstance(decorator, ast.Attribute):
            names.add(decorator.attr)
        elif isinstance(decorator, ast.Call):
            func = decorator.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return names


def _base_names(node: ast.ClassDef) -> Set[str]:
    names: Set[str] = set()
    for base in node.bases:
        if isinstance(base, ast.Name):
            names.add(base.id)
        elif isinstance(base, ast.Attribute):
            names.add(base.attr)
        elif isinstance(base, ast.Subscript):
            value = base.value
            if isinstance(value, ast.Name):
                names.add(value.id)
            elif isinstance(value, ast.Attribute):
                names.add(value.attr)
    return names


def _is_schema_class(node: ast.ClassDef) -> bool:
    base_names = _base_names(node)
    decorator_names = _decorator_names(node)

    if "BaseModel" in base_names:
        return True
    if "dataclass" in decorator_names:
        return True
    return node.name.endswith(SCHEMA_NAME_SUFFIXES)


def _is_data_object_class(node: ast.ClassDef) -> bool:
    if _is_schema_class(node):
        return True
    return node.name.endswith(DATA_OBJECT_NAME_SUFFIXES)


def extract_changed_schema_facts(tree: ast.AST, changed_lines: Set[int], include_all: bool) -> Dict[str, List[str]]:
    changed_schemas: List[str] = []
    affected_data_objects: List[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not _node_overlaps(node, changed_lines, include_all):
            continue

        if _is_schema_class(node):
            changed_schemas.append(node.name)
        if _is_data_object_class(node):
            affected_data_objects.append(node.name)

    return {
        "changed_schemas": sorted(set(changed_schemas)),
        "affected_data_objects": sorted(set(affected_data_objects)),
    }
