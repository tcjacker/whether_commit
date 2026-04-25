from __future__ import annotations

from typing import Any, Dict, List

from app.schemas.overview import TestAssetSummary


class TestAssetSummaryBuilder:
    def build_clean(self) -> Dict[str, Any]:
        return TestAssetSummary().model_dump()

    def build(
        self,
        *,
        change_data: Dict[str, Any],
        verification_data: Dict[str, Any],
        capability_map: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        changed_files = list(change_data.get("changed_files", []))
        changed_test_files = [path for path in changed_files if self._is_test_path(path)]
        affected_tests = list(verification_data.get("affected_tests", []))
        coverage_gaps = list(verification_data.get("missing_tests_for_changed_paths", []))
        evidence_by_path = verification_data.get("evidence_by_path", {})

        capability_coverage = self._build_capability_coverage(
            capability_map=capability_map,
            change_data=change_data,
            verification_data=verification_data,
            affected_tests=affected_tests,
        )
        test_files = self._build_test_files(
            changed_test_files=changed_test_files,
            affected_tests=affected_tests,
            coverage_gaps=coverage_gaps,
            capability_coverage=capability_coverage,
            evidence_by_path=evidence_by_path,
            change_data=change_data,
        )
        stale_or_invalid_test_count = sum(
            1 for item in test_files if item["maintenance_status"] in {"update", "retire"}
        )

        health_status = self._health_status(
            affected_tests=affected_tests,
            coverage_gaps=coverage_gaps,
            stale_or_invalid_test_count=stale_or_invalid_test_count,
        )

        return {
            "health_status": health_status,
            "total_test_file_count": len(test_files),
            "affected_test_count": len(affected_tests),
            "changed_test_file_count": len(changed_test_files),
            "stale_or_invalid_test_count": stale_or_invalid_test_count,
            "duplicate_or_low_value_test_count": 0,
            "coverage_gaps": coverage_gaps,
            "recommended_actions": self._recommended_actions(
                coverage_gaps=coverage_gaps,
                changed_test_files=changed_test_files,
                stale_or_invalid_test_count=stale_or_invalid_test_count,
            ),
            "capability_coverage": capability_coverage,
            "test_files": test_files,
        }

    def _build_capability_coverage(
        self,
        *,
        capability_map: List[Dict[str, Any]],
        change_data: Dict[str, Any],
        verification_data: Dict[str, Any],
        affected_tests: List[str],
    ) -> List[Dict[str, Any]]:
        affected_entrypoints = list(
            dict.fromkeys(change_data.get("affected_entrypoints", []) + change_data.get("changed_routes", []))
        )
        verified_paths = list(verification_data.get("verified_changed_paths", []))
        coverage_gaps = list(verification_data.get("missing_tests_for_changed_paths", []))
        changed_files = [path for path in change_data.get("changed_files", []) if not self._is_test_path(path)]

        capabilities = [
            item for item in capability_map if item.get("status") == "recently_changed" or item.get("is_primary_target")
        ]
        if not capabilities and (affected_entrypoints or changed_files or affected_tests):
            capabilities = [
                {
                    "capability_key": self._fallback_capability_key(affected_entrypoints, changed_files),
                    "name": self._fallback_capability_name(affected_entrypoints, changed_files),
                    "linked_routes": affected_entrypoints,
                    "linked_modules": change_data.get("directly_changed_modules", []),
                }
            ]

        result: List[Dict[str, Any]] = []
        for capability in capabilities:
            linked_routes = list(capability.get("linked_routes", [])) or affected_entrypoints
            if coverage_gaps and verified_paths:
                coverage_status = "partial"
            elif coverage_gaps:
                coverage_status = "missing"
            elif affected_tests:
                coverage_status = "covered"
            else:
                coverage_status = "unknown"

            result.append(
                {
                    "capability_key": capability.get("capability_key", ""),
                    "business_capability": capability.get("name", "") or "未命名能力",
                    "coverage_status": coverage_status,
                    "technical_entrypoints": linked_routes,
                    "covered_paths": list(dict.fromkeys(verified_paths + coverage_gaps)),
                    "covering_tests": affected_tests,
                    "gaps": coverage_gaps,
                    "maintenance_recommendation": self._capability_recommendation(coverage_status),
                }
            )
        return result

    def _build_test_files(
        self,
        *,
        changed_test_files: List[str],
        affected_tests: List[str],
        coverage_gaps: List[str],
        capability_coverage: List[Dict[str, Any]],
        evidence_by_path: Dict[str, Any],
        change_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        test_paths = list(
            dict.fromkeys(changed_test_files + [self._test_file_from_test_id(test_id) for test_id in affected_tests])
        )
        test_paths = [path for path in test_paths if path]

        covered_capabilities = [item["business_capability"] for item in capability_coverage if item.get("business_capability")]
        covered_paths = list(dict.fromkeys([path for item in capability_coverage for path in item.get("covered_paths", [])]))
        linked_entrypoints = list(
            dict.fromkeys(
                change_data.get("affected_entrypoints", [])
                + change_data.get("changed_routes", [])
                + [entry for item in capability_coverage for entry in item.get("technical_entrypoints", [])]
            )
        )

        items: List[Dict[str, Any]] = []
        for path in test_paths:
            evidence = evidence_by_path.get(path, {})
            status = evidence.get("status", "unknown") if isinstance(evidence, dict) else "unknown"
            invalidation_reasons: List[str] = []
            if coverage_gaps:
                invalidation_reasons.append("关联业务路径仍有未覆盖或未验证的变更。")
            if not affected_tests and path in changed_test_files:
                invalidation_reasons.append("测试文件发生改动，但当前没有执行报告证明它仍然有效。")

            if invalidation_reasons:
                maintenance_status = "update"
            elif status == "no-evidence":
                maintenance_status = "retire"
                invalidation_reasons.append("测试资产没有映射到有效执行证据。")
            else:
                maintenance_status = "keep"

            items.append(
                {
                    "path": path,
                    "maintenance_status": maintenance_status,
                    "covered_capabilities": covered_capabilities,
                    "covered_paths": covered_paths,
                    "linked_entrypoints": linked_entrypoints,
                    "invalidation_reasons": invalidation_reasons,
                    "recommendation": self._test_file_recommendation(maintenance_status),
                    "evidence_status": status,
                }
            )
        return items

    def _recommended_actions(
        self,
        *,
        coverage_gaps: List[str],
        changed_test_files: List[str],
        stale_or_invalid_test_count: int,
    ) -> List[str]:
        actions: List[str] = []
        if coverage_gaps:
            actions.append("补齐未覆盖业务路径的测试。")
        if changed_test_files:
            actions.append("复核本次改动的测试文件是否仍覆盖真实代码入口。")
        if stale_or_invalid_test_count:
            actions.append("更新或淘汰疑似失效的测试资产。")
        return actions or ["当前未发现需要立即整理的测试资产。"]

    def _health_status(
        self,
        *,
        affected_tests: List[str],
        coverage_gaps: List[str],
        stale_or_invalid_test_count: int,
    ) -> str:
        if coverage_gaps and not affected_tests:
            return "high_risk"
        if coverage_gaps or stale_or_invalid_test_count:
            return "needs_maintenance"
        if affected_tests:
            return "healthy"
        return "unknown"

    def _capability_recommendation(self, coverage_status: str) -> str:
        return {
            "covered": "保留当前覆盖，并在入口变更时同步更新测试断言。",
            "partial": "补齐缺口路径，并确认现有测试仍覆盖真实业务入口。",
            "missing": "优先为该能力补充回归测试。",
            "unknown": "先建立测试到业务能力和代码入口的映射。",
        }[coverage_status]

    def _test_file_recommendation(self, maintenance_status: str) -> str:
        return {
            "keep": "保留该测试，并随业务入口变化同步维护。",
            "update": "更新该测试，使它覆盖当前变更后的真实业务路径。",
            "retire": "确认无有效覆盖后合并或淘汰该测试。",
            "unknown": "补充执行证据后再判断该测试价值。",
        }[maintenance_status]

    def _fallback_capability_key(self, entrypoints: List[str], changed_files: List[str]) -> str:
        basis = entrypoints[0] if entrypoints else (changed_files[0] if changed_files else "unknown")
        return "cap_" + "".join(ch.lower() if ch.isalnum() else "_" for ch in basis).strip("_")

    def _fallback_capability_name(self, entrypoints: List[str], changed_files: List[str]) -> str:
        basis = entrypoints[0] if entrypoints else (changed_files[0] if changed_files else "")
        tokens = [token for token in basis.replace("/", " ").replace("_", " ").split() if token.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}]
        if not tokens:
            return "变更能力"
        return " ".join(token[:1].upper() + token[1:] for token in tokens[:2])

    def _test_file_from_test_id(self, test_id: str) -> str:
        return test_id.split("::", 1)[0]

    def _is_test_path(self, path: str) -> bool:
        normalized = path.lower()
        return "/test" in normalized or "test_" in normalized or normalized.endswith("_test.py")
