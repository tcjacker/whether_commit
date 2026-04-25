from __future__ import annotations

import ast
import json
import os
import subprocess
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from app.services.change_impact.job_extractors import extract_changed_job_facts
from app.services.change_impact.schema_extractors import extract_changed_schema_facts
from app.services.graph_adapter.adapter import GraphAdapter


class ChangeImpactAdapter:
    """
    Adapter for integrating with code-review-graph or similar impact analysis tools.
    Responsible for generating the change_analysis.json snapshot.
    In this MVP, we use real git commands plus diff-hunk-aware AST extraction.
    """

    SUPPORTED_PATH_SUFFIXES = (".py", ".json", ".md", ".js", ".ts", ".yml", ".yaml")

    def __init__(self, workspace_path: str, base_commit_sha: str = "HEAD"):
        self.workspace_path = workspace_path
        self.base_commit_sha = base_commit_sha

    def _git_status_lines(self) -> List[str]:
        result = subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=self.workspace_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return [line.rstrip("\n") for line in result.stdout.splitlines() if line.rstrip("\n")]

    def _git_diff_for_file(self, file_path: str, staged: bool = False) -> str:
        cmd = ["git", "diff"]
        if staged:
            cmd.append("--cached")
        cmd.extend(["--", file_path])
        result = subprocess.run(
            cmd,
            cwd=self.workspace_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout

    def _parse_status_entry(self, line: str) -> Dict[str, str]:
        if len(line) < 4:
            return {"status": "", "path": ""}

        raw_path = line[3:]
        normalized_path = raw_path.split(" -> ", 1)[1] if " -> " in raw_path else raw_path
        return {"status": line[:2], "path": normalized_path}

    def _parse_changed_lines(self, diff_text: str) -> Set[int]:
        changed_lines: Set[int] = set()
        current_line: int | None = None

        for line in diff_text.splitlines():
            if line.startswith("@@"):
                parts = line.split()
                if len(parts) < 3:
                    current_line = None
                    continue

                new_range = parts[2]
                if not new_range.startswith("+"):
                    current_line = None
                    continue

                range_body = new_range[1:]
                start_str = range_body.split(",", 1)[0]
                current_line = int(start_str)
                continue

            if current_line is None:
                continue

            if line.startswith("+++ ") or line.startswith("--- "):
                continue
            if line.startswith("\\"):
                continue
            if line.startswith("+"):
                changed_lines.add(current_line)
                current_line += 1
                continue
            if line.startswith("-"):
                continue

            current_line += 1

        return changed_lines

    def _change_type_for_status(self, status: str) -> str:
        if status == "??":
            return "new file"
        if "D" in status:
            return "deleted file"
        if "R" in status:
            return "renamed file"
        if "A" in status:
            return "new file"
        if "M" in status:
            return "modified file"
        return "changed file"

    def _diff_text_for_entry(self, path: str, status: str) -> str:
        if status == "??":
            full_path = os.path.join(self.workspace_path, path)
            if not os.path.exists(full_path):
                return ""
            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()[:200]
            except OSError:
                return ""
            header = [
                f"diff --git a/{path} b/{path}",
                "new file mode 100644",
                "index 0000000..0000000",
                "--- /dev/null",
                f"+++ b/{path}",
                f"@@ -0,0 +1,{len(lines)} @@",
            ]
            return "\n".join(header + [f"+{line.rstrip(chr(10))}" for line in lines]) + "\n"

        return "\n".join(
            diff
            for diff in [
                self._git_diff_for_file(path, staged=True),
                self._git_diff_for_file(path, staged=False),
            ]
            if diff
        )

    def _parse_file_diff_stats(self, diff_text: str, status: str) -> Dict[str, Any]:
        added_lines = 0
        deleted_lines = 0
        snippets: List[str] = []

        for raw_line in diff_text.splitlines():
            if raw_line.startswith(("+++", "---", "@@", "diff --git", "index ")):
                continue
            if raw_line.startswith("+"):
                added_lines += 1
                text = raw_line[1:].strip()
                if text and len(snippets) < 8:
                    snippets.append(text[:180])
                continue
            if raw_line.startswith("-"):
                deleted_lines += 1
                text = raw_line[1:].strip()
                if text and len(snippets) < 8:
                    snippets.append(f"removed: {text[:170]}")

        return {
            "added_lines": added_lines,
            "deleted_lines": deleted_lines,
            "change_type": self._change_type_for_status(status),
            "snippets": snippets,
        }

    def _build_file_diff_stats(self, entries: List[Dict[str, str]]) -> Dict[str, Dict[str, Any]]:
        stats_by_path: Dict[str, Dict[str, Any]] = {}
        for entry in entries:
            path = entry["path"]
            try:
                diff_text = self._diff_text_for_entry(path, entry["status"])
            except subprocess.CalledProcessError:
                continue
            stats_by_path[path] = self._parse_file_diff_stats(diff_text, entry["status"])
        return stats_by_path

    def _build_file_diffs(self, entries: List[Dict[str, str]]) -> Dict[str, str]:
        diffs_by_path: Dict[str, str] = {}
        for entry in entries:
            path = entry["path"]
            try:
                diff_text = self._diff_text_for_entry(path, entry["status"])
            except subprocess.CalledProcessError:
                continue
            diffs_by_path[path] = diff_text
        return diffs_by_path

    def _agent_log_candidates(self) -> List[Path]:
        home = Path.home()
        candidates = [
            home / ".codex" / "history.jsonl",
            home / ".codex" / "session_index.jsonl",
        ]
        escaped_workspace = self.workspace_path.replace("/", "-")
        claude_project_dir = home / ".claude" / "projects" / escaped_workspace
        if claude_project_dir.is_dir():
            candidates.extend(sorted(claude_project_dir.glob("*.jsonl")))
            candidates.extend(sorted(claude_project_dir.glob("*.json")))
        return candidates

    def _text_from_agent_log_line(self, raw_line: str) -> str:
        line = raw_line.strip()
        if not line:
            return ""
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return line[:500]

        if isinstance(payload, dict):
            parts: List[str] = []
            for key in ("text", "thread_name", "summary", "content", "message"):
                value = payload.get(key)
                if isinstance(value, str):
                    parts.append(value)
                elif isinstance(value, dict):
                    nested = value.get("content") or value.get("text")
                    if isinstance(nested, str):
                        parts.append(nested)
            return " ".join(parts)[:500]
        return str(payload)[:500]

    def _collect_agent_activity_evidence(self, changed_files: List[str]) -> List[Dict[str, Any]]:
        generic_basenames = {
            "service.py",
            "adapter.py",
            "store.py",
            "manager.py",
            "index.ts",
            "api.ts",
            "types.ts",
        }
        path_needles = {
            path: {
                needle
                for needle in {
                    path.lower(),
                    "/".join(path.lower().split("/")[-3:]),
                    "/".join(path.lower().split("/")[-2:]),
                    os.path.basename(path).lower() if os.path.basename(path).lower() not in generic_basenames else "",
                }
                if needle
            }
            for path in changed_files
            if path
        }
        evidence: List[Dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        for candidate in self._agent_log_candidates():
            if not candidate.exists() or not candidate.is_file():
                continue
            source = "claude_code" if ".claude" in str(candidate) else "codex"
            try:
                lines = candidate.read_text(encoding="utf-8", errors="replace").splitlines()[-400:]
            except OSError:
                continue

            for raw_line in lines:
                text = self._text_from_agent_log_line(raw_line)
                if not text:
                    continue
                lower = text.lower()
                related_files = [
                    path
                    for path, needles in path_needles.items()
                    if any(needle and needle in lower for needle in needles)
                ]
                if not related_files:
                    continue
                summary = " ".join(text.split())[:240]
                key = (source, summary)
                if key in seen:
                    continue
                seen.add(key)
                evidence.append(
                    {
                        "source": source,
                        "summary": summary,
                        "related_files": related_files[:8],
                    }
                )
                if len(evidence) >= 30:
                    return evidence
        return evidence

    def _extract_routes_for_node(self, node: ast.AST) -> List[str]:
        routes: List[str] = []
        decorator_list = getattr(node, "decorator_list", [])

        for decorator in decorator_list:
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                continue
            method = decorator.func.attr.upper()
            if method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                continue
            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                routes.append(f"{method} {decorator.args[0].value}")

        return routes

    def _extract_changed_python_facts(self, file_path: str, status: str) -> Dict[str, List[str]]:
        full_path = os.path.join(self.workspace_path, file_path)
        if not os.path.exists(full_path):
            return {
                "symbols": [],
                "functions": [],
                "classes": [],
                "routes": [],
                "changed_schemas": [],
                "changed_jobs": [],
                "affected_data_objects": [],
            }

        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return {
                "symbols": [],
                "functions": [],
                "classes": [],
                "routes": [],
                "changed_schemas": [],
                "changed_jobs": [],
                "affected_data_objects": [],
            }

        is_untracked = status == "??"
        if is_untracked:
            changed_lines = set()
        else:
            staged_diff = self._git_diff_for_file(file_path, staged=True)
            unstaged_diff = self._git_diff_for_file(file_path, staged=False)
            changed_lines = self._parse_changed_lines(staged_diff) | self._parse_changed_lines(unstaged_diff)

        symbols: List[str] = []
        functions: List[str] = []
        classes: List[str] = []
        routes: List[str] = []
        schema_facts = extract_changed_schema_facts(tree, changed_lines, include_all=is_untracked)
        job_facts = extract_changed_job_facts(tree, changed_lines, include_all=is_untracked)

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue

            start = getattr(node, "lineno", None)
            end = getattr(node, "end_lineno", start)
            if start is None:
                continue

            overlaps_hunk = is_untracked or any(line in changed_lines for line in range(start, end + 1))
            if not overlaps_hunk:
                continue

            symbols.append(node.name)

            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            else:
                functions.append(node.name)
                routes.extend(self._extract_routes_for_node(node))

        return {
            "symbols": sorted(set(symbols)),
            "functions": sorted(set(functions)),
            "classes": sorted(set(classes)),
            "routes": sorted(set(routes)),
            "changed_schemas": sorted(set(schema_facts.get("changed_schemas", []))),
            "changed_jobs": sorted(set(job_facts.get("changed_jobs", []))),
            "affected_data_objects": sorted(set(schema_facts.get("affected_data_objects", []))),
        }

    def _status_entries(self) -> List[Dict[str, str]]:
        entries: List[Dict[str, str]] = []
        for line in self._git_status_lines():
            entry = self._parse_status_entry(line)
            if not entry["path"]:
                continue
            if entry["path"].endswith(self.SUPPORTED_PATH_SUFFIXES):
                entries.append(entry)
        return entries

    def _module_keys_for_files(self, changed_files: List[str]) -> List[str]:
        module_ids = set()
        for path in changed_files:
            parent_dir = os.path.dirname(path)
            if not parent_dir:
                module_ids.add("mod_root")
                continue
            parts = [part for part in parent_dir.split(os.sep) if part and part not in {".", ".."}]
            slug = "__".join(parts) if parts else "root"
            module_ids.add(f"mod_{slug}")
        return sorted(module_ids)

    def _load_graph_snapshot(self) -> Dict[str, Any]:
        try:
            return GraphAdapter(workspace_path=self.workspace_path).generate_graph_snapshot()
        except Exception:
            return {"modules": [], "dependencies": []}

    def _impact_item(
        self,
        *,
        entity_type: str,
        entity_id: str,
        reason: str,
        evidence: Dict[str, Any],
        distance: int,
        direction: str | None = None,
    ) -> Dict[str, Any]:
        item = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "reason": reason,
            "evidence": evidence,
            "distance": distance,
        }
        if direction is not None:
            item["direction"] = direction
        return item

    def _expand_transitive_modules(
        self,
        direct_module_evidence: Dict[str, Dict[str, Any]],
        graph_data: Dict[str, Any],
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        modules = {module["module_id"]: module for module in graph_data.get("modules", []) if module.get("module_id")}
        dependencies = graph_data.get("relationships") or graph_data.get("dependencies", [])
        forward_adjacency: Dict[str, List[Dict[str, str]]] = {}
        reverse_adjacency: Dict[str, List[Dict[str, str]]] = {}
        for dependency in dependencies:
            source = dependency.get("from")
            target = dependency.get("to")
            edge_type = dependency.get("type")
            if not source or not target:
                continue
            edge = {"to": target, "type": edge_type or "dependency"}
            forward_adjacency.setdefault(source, []).append(edge)
            reverse_adjacency.setdefault(target, []).append({
                "to": source,
                "type": edge_type or "dependency",
            })

        direct_modules = set(direct_module_evidence.keys())
        transitive_evidence: Dict[str, Dict[str, Any]] = {}

        def expand_direction(direction: str, adjacency: Dict[str, List[Dict[str, str]]]) -> None:
            visited = set(direct_modules)
            queue = deque((module_id, 0) for module_id in sorted(direct_modules))

            while queue:
                current_module, current_distance = queue.popleft()
                for edge in adjacency.get(current_module, []):
                    target_module = edge["to"]
                    if target_module not in modules or target_module in visited:
                        continue

                    visited.add(target_module)
                    queue.append((target_module, current_distance + 1))
                    evidence = transitive_evidence.setdefault(
                        target_module,
                        {
                            "direction": direction,
                            "directions": [],
                            "by_direction": {},
                            "distance": current_distance + 1,
                        },
                    )
                    if direction not in evidence["directions"]:
                        evidence["directions"].append(direction)
                    if len(evidence["directions"]) > 1:
                        evidence["direction"] = "mixed"
                    elif not evidence.get("direction"):
                        evidence["direction"] = direction
                    evidence["distance"] = min(evidence["distance"], current_distance + 1)
                    direction_evidence = evidence["by_direction"].setdefault(
                        direction,
                        {
                            "direction": direction,
                            "from_modules": [],
                            "dependency_types": [],
                            "paths": [],
                            "distance": current_distance + 1,
                        },
                    )
                    if current_module not in direction_evidence["from_modules"]:
                        direction_evidence["from_modules"].append(current_module)
                    if edge["type"] not in direction_evidence["dependency_types"]:
                        direction_evidence["dependency_types"].append(edge["type"])
                    direction_evidence["paths"].append({"from": current_module, "to": target_module})
                    direction_evidence["distance"] = min(direction_evidence["distance"], current_distance + 1)

        expand_direction("downstream_dependency", forward_adjacency)
        expand_direction("upstream_dependent", reverse_adjacency)

        transitive_modules = sorted(transitive_evidence.keys())
        transitive_items = [
            self._impact_item(
                entity_type="module",
                entity_id=module_id,
                reason="reachable_via_dependency_graph",
                evidence=transitive_evidence[module_id],
                distance=transitive_evidence[module_id]["distance"],
                direction=transitive_evidence[module_id]["direction"],
            )
            for module_id in transitive_modules
        ]
        return transitive_modules, transitive_items

    def _execute_code_review_graph(self) -> Dict[str, Any]:
        """
        Uses git working tree state to find pending changes and analyzes AST only for
        symbols that overlap changed diff hunks.
        """
        if not os.path.exists(os.path.join(self.workspace_path, ".git")):
            return {
                "base_commit_sha": self.base_commit_sha,
                "change_title": "Not a git repository",
                "changed_files": [],
                "changed_symbols": [],
                "changed_functions": [],
                "changed_classes": [],
                "changed_routes": [],
                "changed_schemas": [],
                "changed_jobs": [],
                "affected_data_objects": [],
                "changed_modules": [],
                "directly_changed_modules": [],
                "transitively_affected_modules": [],
                "affected_entrypoints": [],
                "blast_radius": [],
                "direct_impacts": [],
                "transitive_impacts": [],
                "impact_reasons": [],
                "why_impacted": [],
                "minimal_review_set": [],
                "linked_tests": [],
                "risk_score": 0.0,
            }

        try:
            entries = self._status_entries()
            graph_data = self._load_graph_snapshot()

            changed_files: List[str] = [entry["path"] for entry in entries]
            file_diffs = self._build_file_diffs(entries)
            file_diff_stats = {
                entry["path"]: self._parse_file_diff_stats(file_diffs.get(entry["path"], ""), entry["status"])
                for entry in entries
            }
            agent_activity_evidence = self._collect_agent_activity_evidence(changed_files)
            changed_symbols: List[str] = []
            changed_functions: List[str] = []
            changed_classes: List[str] = []
            changed_routes: List[str] = []
            changed_schemas: List[str] = []
            changed_jobs: List[str] = []
            affected_data_objects: List[str] = []
            extracted_by_file: Dict[str, Dict[str, List[str]]] = {}

            for entry in entries:
                file_path = entry["path"]
                if not file_path.endswith(".py"):
                    continue

                extracted = self._extract_changed_python_facts(file_path, entry["status"])
                extracted_by_file[file_path] = extracted
                changed_symbols.extend(extracted["symbols"])
                changed_functions.extend(extracted["functions"])
                changed_classes.extend(extracted["classes"])
                changed_routes.extend(extracted["routes"])
                changed_schemas.extend(extracted.get("changed_schemas", []))
                changed_jobs.extend(extracted.get("changed_jobs", []))
                affected_data_objects.extend(extracted.get("affected_data_objects", []))

            directly_changed_modules = self._module_keys_for_files(changed_files)
            direct_module_evidence: Dict[str, Dict[str, Any]] = {}
            for changed_file in changed_files:
                module_id = self._module_keys_for_files([changed_file])[0]
                evidence = direct_module_evidence.setdefault(
                    module_id,
                    {
                        "files": [],
                        "symbols": [],
                        "functions": [],
                        "classes": [],
                        "routes": [],
                        "schemas": [],
                        "jobs": [],
                        "data_objects": [],
                    },
                )
                if changed_file not in evidence["files"]:
                    evidence["files"].append(changed_file)
                extracted = extracted_by_file.get(changed_file, {})
                for key, value in (
                    ("symbols", extracted.get("symbols", [])),
                    ("functions", extracted.get("functions", [])),
                    ("classes", extracted.get("classes", [])),
                    ("routes", extracted.get("routes", [])),
                    ("schemas", extracted.get("changed_schemas", [])),
                    ("jobs", extracted.get("changed_jobs", [])),
                    ("data_objects", extracted.get("affected_data_objects", [])),
                ):
                    for item in value:
                        if item not in evidence[key]:
                            evidence[key].append(item)

            transitively_affected_modules, transitive_impacts = self._expand_transitive_modules(
                direct_module_evidence,
                graph_data,
            )
            affected_entrypoints = sorted(set(changed_routes))
            blast_radius = sorted(set(directly_changed_modules + transitively_affected_modules))
            direct_impacts = [
                self._impact_item(
                    entity_type="module",
                    entity_id=module_id,
                    reason="direct_file_change",
                    evidence=direct_module_evidence.get(module_id, {"files": []}),
                    distance=0,
                    direction="direct_change",
                )
                for module_id in directly_changed_modules
            ]
            impact_reasons = direct_impacts + transitive_impacts

            return {
                "base_commit_sha": self.base_commit_sha,
                "change_title": f"工作区差异（{len(changed_files)} 个文件）",
                "changed_files": changed_files,
                "file_diff_stats": file_diff_stats,
                "file_diffs": file_diffs,
                "agent_activity_evidence": agent_activity_evidence,
                "changed_symbols": sorted(set(changed_symbols)),
                "changed_functions": sorted(set(changed_functions)),
                "changed_classes": sorted(set(changed_classes)),
                "changed_routes": sorted(set(changed_routes)),
                "changed_schemas": sorted(set(changed_schemas)),
                "changed_jobs": sorted(set(changed_jobs)),
                "affected_data_objects": sorted(set(affected_data_objects)),
                "changed_modules": directly_changed_modules,
                "directly_changed_modules": directly_changed_modules,
                "transitively_affected_modules": transitively_affected_modules,
                "affected_entrypoints": affected_entrypoints,
                "blast_radius": blast_radius,
                "direct_impacts": direct_impacts,
                "transitive_impacts": transitive_impacts,
                "impact_reasons": impact_reasons,
                "why_impacted": impact_reasons,
                "minimal_review_set": changed_files,
                "linked_tests": sorted([path for path in changed_files if "test" in path.lower()]),
                "risk_score": min(1.0, len(changed_files) * 0.1),
            }

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git command failed: {e.stderr}")
        except Exception as e:
            raise RuntimeError(f"Failed to analyze git changes: {str(e)}")

    def _compute_coherence(self, directly_changed_modules: List[str]) -> Dict[str, Any]:
        """
        Groups directly changed modules by their second-level path segment.
        focused = <= 2 distinct groups; mixed = 3 or more.
        """
        groups: Set[str] = set()
        for mod_key in directly_changed_modules:
            parts = mod_key.removeprefix("mod_").split("__")
            group = parts[1] if len(parts) > 1 else parts[0]
            groups.add(group)
        coherence_groups = sorted(groups)
        coherence = "focused" if len(groups) <= 2 else "mixed"
        return {"coherence": coherence, "coherence_groups": coherence_groups}

    def generate_change_analysis(self, workspace_snapshot_id: str) -> Dict[str, Any]:
        """
        Main entry point for JobManager to build the change impact analysis.
        """
        try:
            raw_data = self._execute_code_review_graph()
            raw_data["workspace_snapshot_id"] = workspace_snapshot_id
            raw_data["workspace_path"] = self.workspace_path
            coherence_data = self._compute_coherence(raw_data.get("directly_changed_modules", []))
            raw_data.update(coherence_data)
            return raw_data
        except Exception as e:
            raise RuntimeError(f"Failed to generate change impact analysis: {str(e)}")
