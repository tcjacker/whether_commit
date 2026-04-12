from __future__ import annotations

import ast
from typing import Dict, List, Set


JOB_NAME_HINTS = ("job", "worker", "task")
JOB_DECORATOR_HINTS = ("task", "job", "worker", "background", "celery")


def _node_overlaps(node: ast.AST, changed_lines: Set[int], include_all: bool) -> bool:
    if include_all:
        return True

    start = getattr(node, "lineno", None)
    end = getattr(node, "end_lineno", start)
    if start is None:
        return False

    return any(line in changed_lines for line in range(start, (end or start) + 1))


def _decorator_names(node: ast.AST) -> Set[str]:
    names: Set[str] = set()
    decorator_list = getattr(node, "decorator_list", [])
    for decorator in decorator_list:
        if isinstance(decorator, ast.Name):
            names.add(decorator.id.lower())
        elif isinstance(decorator, ast.Attribute):
            names.add(decorator.attr.lower())
        elif isinstance(decorator, ast.Call):
            func = decorator.func
            if isinstance(func, ast.Name):
                names.add(func.id.lower())
            elif isinstance(func, ast.Attribute):
                names.add(func.attr.lower())
    return names


def _is_job_function(node: ast.AST) -> bool:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False

    lowered_name = node.name.lower()
    if any(hint in lowered_name for hint in JOB_NAME_HINTS):
        return True

    decorator_names = _decorator_names(node)
    return any(hint in decorator_name for decorator_name in decorator_names for hint in JOB_DECORATOR_HINTS)


def extract_changed_job_facts(tree: ast.AST, changed_lines: Set[int], include_all: bool) -> Dict[str, List[str]]:
    changed_jobs: List[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not _node_overlaps(node, changed_lines, include_all):
            continue
        if _is_job_function(node):
            changed_jobs.append(node.name)

    return {
        "changed_jobs": sorted(set(changed_jobs)),
    }
