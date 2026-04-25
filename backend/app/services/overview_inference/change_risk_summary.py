from __future__ import annotations

from typing import Any, Dict, List

from app.schemas.overview import ChangeRiskSummary


class ChangeRiskSummaryBuilder:
    def build_clean(self) -> Dict[str, Any]:
        return ChangeRiskSummary().model_dump()

    def build(
        self,
        *,
        change_data: Dict[str, Any],
        verification_data: Dict[str, Any],
        capability_map: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        coverage = self._build_coverage(verification_data)
        affected_capabilities = self._build_affected_capabilities(
            capability_map=capability_map,
            change_data=change_data,
            verification_data=verification_data,
        )
        risk_signals = self._build_risk_signals(change_data=change_data, verification_data=verification_data)
        overall_risk_level = self._compute_overall_risk_level(
            coverage=coverage,
            risk_signals=risk_signals,
            verification_data=verification_data,
        )
        business_impact_summary = (
            f"本次改动共影响 {len(affected_capabilities)} 个已有功能，详情见下方能力与技术入口列表。"
            if affected_capabilities
            else "当前未识别出稳定的已有功能影响范围。"
        )
        return {
            "headline": {
                "overall_risk_level": overall_risk_level,
                "overall_risk_summary": self._fallback_risk_summary(overall_risk_level),
                "recommended_focus": self._fallback_recommended_focus(
                    risk_signals=risk_signals,
                    verification_data=verification_data,
                    change_data=change_data,
                ),
            },
            "coverage": coverage,
            "existing_feature_impact": {
                "business_impact_summary": business_impact_summary,
                "affected_capability_count": len(affected_capabilities),
                "affected_capabilities": affected_capabilities,
            },
            "risk_signals": risk_signals,
            "agent_metadata": {
                "agent_based_fields": [
                    "headline.overall_risk_summary",
                    "headline.recommended_focus",
                    "existing_feature_impact.business_impact_summary",
                ],
                "rule_based_fields": [
                    "headline.overall_risk_level",
                    "coverage",
                    "existing_feature_impact.affected_capability_count",
                    "existing_feature_impact.affected_capabilities",
                    "risk_signals",
                ],
            },
        }

    def _build_coverage(self, verification_data: Dict[str, Any]) -> Dict[str, Any]:
        affected_test_count = len(verification_data.get("affected_tests", []))
        verified_changed_path_count = len(verification_data.get("verified_changed_paths", []))
        unverified_changed_path_count = len(verification_data.get("unverified_changed_paths", []))
        missing_test_paths = list(verification_data.get("missing_tests_for_changed_paths", []))
        critical_changed_paths = verification_data.get("critical_changed_paths", [])

        if verified_changed_path_count == 0 and unverified_changed_path_count == 0 and affected_test_count == 0:
            coverage_status = "unknown"
        elif unverified_changed_path_count == 0:
            coverage_status = "well_covered"
        elif critical_changed_paths or unverified_changed_path_count > verified_changed_path_count:
            coverage_status = "weakly_covered"
        else:
            coverage_status = "partially_covered"

        coverage_summary = {
            "well_covered": f"本次改动关联 {affected_test_count} 个测试，当前变更路径均已命中验证。",
            "partially_covered": (
                f"本次改动命中了 {affected_test_count} 个相关测试，但仍有 "
                f"{unverified_changed_path_count} 条变更路径缺少验证。"
            ),
            "weakly_covered": "本次改动存在关键路径或主要变更路径未验证，当前覆盖不足。",
            "unknown": "已提取变更事实，但当前没有足够的验证证据来判断覆盖情况。",
        }[coverage_status]

        return {
            "coverage_status": coverage_status,
            "affected_test_count": affected_test_count,
            "verified_changed_path_count": verified_changed_path_count,
            "unverified_changed_path_count": unverified_changed_path_count,
            "missing_test_paths": missing_test_paths,
            "coverage_summary": coverage_summary,
        }

    def _build_affected_capabilities(
        self,
        *,
        capability_map: List[Dict[str, Any]],
        change_data: Dict[str, Any],
        verification_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        direct_modules = set(change_data.get("directly_changed_modules", []))
        transitive_modules = set(change_data.get("transitively_affected_modules", []))
        affected_entrypoints = list(dict.fromkeys(change_data.get("affected_entrypoints", []) + change_data.get("changed_routes", [])))
        changed_files = list(change_data.get("changed_files", []))
        unverified_modules = set(verification_data.get("unverified_changed_modules", []))
        verified_modules = set(verification_data.get("verified_changed_modules", []))

        items: List[Dict[str, Any]] = []
        for capability in capability_map:
            linked_modules = set(capability.get("linked_modules", []))
            if capability.get("status") != "recently_changed" and not linked_modules.intersection(direct_modules | transitive_modules):
                continue

            verification_status = "partial"
            if linked_modules and linked_modules.issubset(verified_modules):
                verification_status = "verified"
            elif linked_modules and linked_modules.intersection(unverified_modules):
                verification_status = "partial" if linked_modules.intersection(verified_modules) else "unverified"

            impact_basis = []
            for route in capability.get("linked_routes", []):
                if route in affected_entrypoints:
                    impact_basis.append({"kind": "route", "value": route})
            for module_id in sorted(linked_modules.intersection(direct_modules | transitive_modules)):
                impact_basis.append({"kind": "module", "value": module_id})

            items.append(
                {
                    "capability_key": capability.get("capability_key", ""),
                    "name": capability.get("name", ""),
                    "impact_status": "directly_changed" if linked_modules.intersection(direct_modules) else "indirectly_impacted",
                    "technical_entrypoints": capability.get("linked_routes", []) or affected_entrypoints,
                    "changed_files": changed_files,
                    "related_modules": sorted(linked_modules.intersection(direct_modules | transitive_modules)) or sorted(linked_modules),
                    "verification_status": verification_status,
                    "impact_basis": impact_basis,
                }
            )

        return items

    def _build_risk_signals(self, *, change_data: Dict[str, Any], verification_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        signals: List[Dict[str, Any]] = []
        changed_files = list(change_data.get("changed_files", []))
        changed_modules = list(change_data.get("directly_changed_modules", []))
        unverified_paths = list(verification_data.get("unverified_changed_paths", []))
        critical_changed_paths = list(verification_data.get("critical_changed_paths", []))

        if change_data.get("changed_routes") and unverified_paths:
            signals.append(
                {
                    "signal_key": "entrypoint_unverified",
                    "title": "入口变更缺少完整验证",
                    "severity": "high",
                    "reason": "外部入口发生改动，且仍存在未验证路径。",
                    "related_files": changed_files,
                    "related_modules": changed_modules,
                    "mitigation": "优先补齐入口链路相关测试并复查受影响服务。",
                }
            )

        if critical_changed_paths:
            signals.append(
                {
                    "signal_key": "critical_path_changed",
                    "title": "关键路径发生改动",
                    "severity": "high",
                    "reason": "检测到关键路径改动，需要优先人工复核。",
                    "related_files": [item.get("path") for item in critical_changed_paths if isinstance(item, dict) and item.get("path")],
                    "related_modules": changed_modules,
                    "mitigation": "复核关键路径调用链，并补充回归验证。",
                }
            )

        return signals

    def _compute_overall_risk_level(
        self,
        *,
        coverage: Dict[str, Any],
        risk_signals: List[Dict[str, Any]],
        verification_data: Dict[str, Any],
    ) -> str:
        high_signal_count = sum(1 for signal in risk_signals if signal.get("severity") == "high")
        if verification_data.get("critical_changed_paths") and verification_data.get("unverified_changed_paths"):
            return "high"
        if high_signal_count >= 2:
            return "high"
        if coverage.get("coverage_status") == "partially_covered":
            return "medium"
        if coverage.get("coverage_status") == "well_covered":
            return "low"
        return "unknown"

    def _fallback_risk_summary(self, overall_risk_level: str) -> str:
        return {
            "high": "本次改动命中了高风险路径，且存在未完成验证，建议优先检查受影响入口与关键链路。",
            "medium": "本次改动涉及已有能力或关键模块，建议结合受影响入口与验证缺口复核。",
            "low": "本次改动范围较集中，当前未发现明显高风险信号，但仍需按变更入口复核。",
            "unknown": "已提取变更事实，但当前不足以形成稳定风险结论。",
        }[overall_risk_level]

    def _fallback_recommended_focus(
        self,
        *,
        risk_signals: List[Dict[str, Any]],
        verification_data: Dict[str, Any],
        change_data: Dict[str, Any],
    ) -> List[str]:
        focus = [signal["title"] for signal in risk_signals if signal.get("title")]
        focus.extend(verification_data.get("missing_tests_for_changed_paths", [])[:3])
        focus.extend(change_data.get("affected_entrypoints", [])[:3])
        return list(dict.fromkeys(focus))[:3]
