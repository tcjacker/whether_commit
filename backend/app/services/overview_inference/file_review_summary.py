from __future__ import annotations

from typing import Any, Dict, List


class FileReviewSummaryBuilder:
    """Builds file-level review facts and fallback explanations for overview."""

    def build_clean(self) -> List[Dict[str, Any]]:
        return []

    def build(
        self,
        *,
        change_data: Dict[str, Any],
        verification_data: Dict[str, Any],
        change_risk_summary: Dict[str, Any],
        test_asset_summary: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        changed_files = list(dict.fromkeys(change_data.get("changed_files", [])))
        return [
            self._build_file_summary(
                path,
                change_data=change_data,
                verification_data=verification_data,
                change_risk_summary=change_risk_summary,
                test_asset_summary=test_asset_summary,
            )
            for path in changed_files
        ]

    def _build_file_summary(
        self,
        path: str,
        *,
        change_data: Dict[str, Any],
        verification_data: Dict[str, Any],
        change_risk_summary: Dict[str, Any],
        test_asset_summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        role = self._file_role(path)
        related_entrypoints = self._related_entrypoints(path, change_data, change_risk_summary)
        related_capabilities = self._related_capabilities(path, change_data, change_risk_summary)
        related_tests = self._related_tests(path, change_data, verification_data, test_asset_summary)
        risk_level = self._risk_level(path, verification_data, change_risk_summary, test_asset_summary)
        diff_summary = self._diff_summary(path, change_data)
        diff_snippets = self._diff_snippets(path, change_data, role)
        intent_evidence = self._intent_evidence(path, change_data)

        return {
            "path": path,
            "file_role": role,
            "risk_level": risk_level,
            "diff_summary": diff_summary,
            "diff_snippets": diff_snippets,
            "product_meaning": self._product_meaning(path, role, intent_evidence),
            "intent_evidence": intent_evidence,
            "review_focus": self._review_focus(path, role, risk_level),
            "related_entrypoints": related_entrypoints,
            "related_capabilities": related_capabilities,
            "related_tests": related_tests,
            "evidence_basis": self._evidence_basis(path, verification_data, diff_summary),
            "generated_by": "rules",
        }

    def _file_role(self, path: str) -> str:
        lower = path.lower()
        if "/schemas/" in lower or lower.endswith("api.ts"):
            return "API schema" if path.endswith(".py") else "TS contract"
        if lower.endswith(".test.tsx") or "/tests/" in lower or lower.startswith("tests/") or "test_" in lower:
            return "Test asset"
        if "/services/" in lower:
            return "Internal rule/service"
        if lower.startswith("frontend/") and ("/components/" in lower or "/pages/" in lower):
            return "Frontend display"
        if lower.startswith("docs/") or lower.endswith(".md"):
            return "Documentation"
        if "config" in lower or lower.endswith((".json", ".yml", ".yaml", ".toml")):
            return "Configuration"
        return "Code file"

    def _related_entrypoints(
        self,
        path: str,
        change_data: Dict[str, Any],
        change_risk_summary: Dict[str, Any],
    ) -> List[str]:
        entrypoints: List[str] = []
        for key in ("affected_entrypoints", "changed_routes"):
            entrypoints.extend(change_data.get(key, []))
        for item in change_risk_summary.get("existing_feature_impact", {}).get("affected_capabilities", []):
            if path in item.get("changed_files", []) or not item.get("changed_files"):
                entrypoints.extend(item.get("technical_entrypoints", []))
        return self._unique(entrypoints)

    def _related_capabilities(
        self,
        path: str,
        change_data: Dict[str, Any],
        change_risk_summary: Dict[str, Any],
    ) -> List[str]:
        capabilities: List[str] = []
        for item in change_risk_summary.get("existing_feature_impact", {}).get("affected_capabilities", []):
            if path in item.get("changed_files", []) or not item.get("changed_files"):
                capabilities.append(item.get("name", ""))
        if not capabilities and self._is_test_asset_path(path):
            capabilities.extend(change_data.get("affected_capabilities", []))
        return self._unique(capabilities)

    def _related_tests(
        self,
        path: str,
        change_data: Dict[str, Any],
        verification_data: Dict[str, Any],
        test_asset_summary: Dict[str, Any],
    ) -> List[str]:
        tests: List[str] = []
        evidence = verification_data.get("evidence_by_path", {}).get(path, {})
        if isinstance(evidence, dict):
            tests.extend(evidence.get("linked_tests", []))
        tests.extend(change_data.get("linked_tests", []))
        for item in test_asset_summary.get("test_files", []):
            if path == item.get("path") or path in item.get("covered_paths", []):
                tests.append(item.get("path", ""))
        return self._unique(tests)

    def _risk_level(
        self,
        path: str,
        verification_data: Dict[str, Any],
        change_risk_summary: Dict[str, Any],
        test_asset_summary: Dict[str, Any],
    ) -> str:
        if path in verification_data.get("missing_tests_for_changed_paths", []):
            return "high"
        if path in test_asset_summary.get("coverage_gaps", []):
            return "high"
        for signal in change_risk_summary.get("risk_signals", []):
            if path in signal.get("related_files", []):
                return signal.get("severity", "medium")
        if self._is_test_asset_path(path):
            return "low"
        return "medium"

    def _diff_summary(self, path: str, change_data: Dict[str, Any]) -> str:
        stats = change_data.get("file_diff_stats", {}).get(path, {})
        if stats:
            added = int(stats.get("added_lines", 0) or 0)
            deleted = int(stats.get("deleted_lines", 0) or 0)
            change_type = stats.get("change_type") or self._default_change_type(path)
            if deleted:
                return f"+{added} / -{deleted} lines · {change_type}"
            return f"+{added} lines · {change_type}"
        return f"changed file · {self._default_change_type(path)}"

    def _diff_snippets(self, path: str, change_data: Dict[str, Any], role: str) -> List[Dict[str, str]]:
        stats = change_data.get("file_diff_stats", {}).get(path, {})
        snippets = list(stats.get("snippets", [])) if isinstance(stats, dict) else []
        if snippets:
            return [self._diff_snippet_from_text(snippet) for snippet in snippets[:8]]
        return [
            {"type": "context", "line": "…", "text": f"{role} changed: {path}"},
            {"type": "context", "line": "…", "text": "完整 diff 摘要待 file-diff 规则层补齐。"},
        ]

    def _diff_snippet_from_text(self, snippet: Any) -> Dict[str, str]:
        text = str(snippet)
        if text.startswith("removed: "):
            return {"type": "delete", "line": "-", "text": text.removeprefix("removed: ")}
        return {"type": "add", "line": "+", "text": text}

    def _intent_evidence(self, path: str, change_data: Dict[str, Any]) -> List[str]:
        evidence: List[str] = []
        for item in change_data.get("agent_activity_evidence", []):
            if not isinstance(item, dict):
                continue
            related_files = item.get("related_files", [])
            if path not in related_files:
                continue
            source = item.get("source", "agent")
            summary = item.get("summary", "")
            if summary:
                evidence.append(f"{source}: {summary}")
        return self._unique(evidence)[:3]

    def _product_meaning(self, path: str, role: str, intent_evidence: List[str] | None = None) -> str:
        inferred_intent = self._product_meaning_from_agent_activity(path, intent_evidence or [])
        if inferred_intent:
            return inferred_intent

        lower = path.lower()
        if path.endswith("backend/app/schemas/overview.py") or ("/schemas/" in lower and "overview" in lower):
            return "这个文件把测试资产管理正式变成 overview API 契约的一部分，让用户能在首页看到测试资产是否可信。"
        if path.endswith("test_asset_summary.py"):
            return "这个文件把测试覆盖、缺口和疑似失效测试汇总成规则事实，避免 Agent 直接主观判断测试是否应该保留。"
        if path.endswith("workspace_snapshot/service.py"):
            return "这处改动是为了让本地 workspace 识别更可靠：不只检查 .git 目录，而是用 git 判断当前目录是否处在有效工作树中。"
        if path.endswith("change_impact/adapter.py"):
            return "这处改动是为了把文件级 diff 和 Agent 修改意图沉淀为 overview 的事实输入，支撑首页解释每个文件为什么被改。"
        if path.endswith("file_review_summary.py"):
            return "这处改动是为了把每个变更文件从技术事实转换成开发者能读懂的改动说明，并保留 Agent 日志证据。"
        if lower.endswith("api.ts"):
            return "这个文件把后端 overview 新字段变成前端类型契约，降低首页组件误用测试资产字段的风险。"
        if "test" in lower:
            return "这个文件本身是测试资产，需要说明它覆盖了哪些路径，以及是否仍然命中真实业务入口。"
        if role == "Frontend display":
            return "这个文件改变用户在首页理解变更的方式，需要确认展示顺序是否帮助开发者先看文件、再看风险和测试证据。"
        if role == "Internal rule/service":
            return "这个文件改变内部规则或服务行为，需要结合入口、能力和测试覆盖判断对已有功能的影响。"
        return "这个文件发生了代码变更，需要结合文件角色、关联入口和测试证据判断产品影响。"

    def _product_meaning_from_agent_activity(self, path: str, intent_evidence: List[str]) -> str:
        if not intent_evidence:
            return ""
        text = " ".join(intent_evidence)
        if "测试资产" in text and "overview" in text.lower():
            return "根据 Agent 修改记录，这处改动是为了把测试资产治理接入 overview 首页，让用户能判断测试覆盖是否可信、哪些测试需要维护。"
        if "项目结构" in text and ("diff" in text.lower() or "意义" in text):
            return "根据 Agent 修改记录，这处改动是为了按项目文件结构解释变更：先让用户定位文件，再说明 diff 背后的产品意图。"
        if "graphify" in text.lower():
            return "根据 Agent 修改记录，这处改动是为了把 Graphify/结构图能力转成更贴近开发者的文件级 review 视图。"
        if "agent" in text.lower() and ("风险" in text or "归纳" in text):
            return "根据 Agent 修改记录，这处改动是为了让规则事实先落地，再由 Agent 归纳业务影响和风险说明。"
        return f"根据 Agent 修改记录，这处改动的意图是：{intent_evidence[0].split(': ', 1)[-1]}"

    def _review_focus(self, path: str, role: str, risk_level: str) -> List[str]:
        focus: List[str] = []
        if role in {"API schema", "TS contract"}:
            focus.extend(["确认新字段对旧 snapshot 兼容", "确认前后端字段和枚举保持一致"])
        if role == "Internal rule/service":
            focus.extend(["确认规则事实是否保守", "确认 fallback 不依赖 Agent"])
        if role == "Test asset":
            focus.extend(["确认测试覆盖真实入口", "淘汰只覆盖实现细节的低价值断言"])
        if risk_level == "high":
            focus.insert(0, "优先补齐未验证路径")
        return self._unique(focus or ["确认 diff 意义和关联测试证据一致"])

    def _evidence_basis(self, path: str, verification_data: Dict[str, Any], diff_summary: str) -> List[str]:
        basis = [diff_summary]
        if path in verification_data.get("verified_changed_paths", []):
            basis.append("verified_changed_path")
        if path in verification_data.get("unverified_changed_paths", []):
            basis.append("unverified_changed_path")
        if path in verification_data.get("missing_tests_for_changed_paths", []):
            basis.append("missing_tests_for_changed_path")
        return basis

    def _default_change_type(self, path: str) -> str:
        role = self._file_role(path)
        if role == "API schema":
            return "contract change"
        if role == "TS contract":
            return "typed contract"
        if role == "Internal rule/service":
            return "rule/service change"
        if role == "Test asset":
            return "test change"
        if role == "Frontend display":
            return "UI behavior"
        return "code change"

    def _is_test_asset_path(self, path: str) -> bool:
        lower = path.lower()
        return "/tests/" in lower or lower.startswith("tests/") or "test_" in lower or lower.endswith(".test.tsx")

    def _unique(self, values: List[Any]) -> List[str]:
        return [str(item) for item in dict.fromkeys(values) if item]
