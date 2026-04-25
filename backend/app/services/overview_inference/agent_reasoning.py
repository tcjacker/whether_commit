from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.config.settings import ObservabilitySettings
from app.services.overview_inference.llm_reasoning import LLMReasoningService, ReasoningPromptBuilder


class AgentReasoningService:
    """
    Reasoning layer that prefers LLM-backed analysis when available.

    The service remains conservative: it never invents new code facts, and it
    always falls back to a local fact-only summary when the LLM path is absent
    or fails validation.
    """

    def __init__(
        self,
        llm_reasoning_service: Optional[LLMReasoningService] = None,
        prompt_builder: Optional[ReasoningPromptBuilder] = None,
    ) -> None:
        self.prompt_builder = prompt_builder or ReasoningPromptBuilder()
        self.llm_reasoning_service = llm_reasoning_service

    @classmethod
    def from_settings(
        cls,
        settings: ObservabilitySettings,
        prompt_builder: Optional[ReasoningPromptBuilder] = None,
    ) -> "AgentReasoningService":
        llm_reasoning_service = LLMReasoningService.from_settings(settings, prompt_builder=prompt_builder)
        if llm_reasoning_service.provider is None:
            llm_reasoning_service = None
        return cls(llm_reasoning_service=llm_reasoning_service, prompt_builder=prompt_builder)

    def analyze(
        self,
        graph_data: Dict[str, Any],
        change_data: Dict[str, Any],
        verification_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        local_result = self._local_analyze(graph_data, change_data, verification_data)
        if self.llm_reasoning_service is None:
            local_result["llm_reasoning"] = {"enabled": False, "status": "disabled", "validation_issues": []}
            return local_result

        prompt_payload = self.prompt_builder.build(graph_data, change_data, verification_data)
        try:
            llm_result = self.llm_reasoning_service.reason(prompt_payload)
        except Exception as exc:
            local_result["confidence"] = "low"
            local_result["llm_reasoning"] = {
                "enabled": True,
                "status": "provider_error",
                "validation_issues": [str(exc)],
            }
            return local_result
        local_result["llm_reasoning"] = {
            "enabled": True,
            "status": llm_result.get("status", "rejected"),
            "validation_issues": llm_result.get("validation_issues", []),
        }

        if not llm_result.get("accepted"):
            local_result["confidence"] = "low"
            return local_result

        reasoning = llm_result.get("reasoning", {})
        if reasoning.get("validation_gaps"):
            local_result["validation_gaps"] = self._merge_unique(local_result["validation_gaps"], reasoning["validation_gaps"])
        if reasoning.get("unknowns"):
            local_result["unknowns"] = self._merge_unique(local_result["unknowns"], reasoning["unknowns"])

        local_result["technical_change_summary"] = reasoning.get("technical_change_summary", local_result["technical_change_summary"])
        local_result["change_types"] = self._merge_filtered_change_types(
            local_result["change_types"],
            reasoning.get("change_types", []),
        )
        local_result["risk_factors"] = self._merge_unique(local_result["risk_factors"], reasoning.get("risk_factors", []))
        local_result["review_recommendations"] = self._merge_review_recommendations(
            change_data,
            local_result["review_recommendations"],
            reasoning.get("review_recommendations", []),
        )
        local_result["why_impacted"] = reasoning.get("why_impacted", local_result["why_impacted"])
        local_result["confidence"] = self._lower_confidence(
            local_result["confidence"],
            reasoning.get("confidence", "low"),
        )
        if reasoning.get("change_intent"):
            local_result["change_intent"] = reasoning["change_intent"]
        local_result["llm_reasoning"]["status"] = "accepted"
        return local_result

    def _local_analyze(
        self,
        graph_data: Dict[str, Any],
        change_data: Dict[str, Any],
        verification_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        changed_files: List[str] = list(change_data.get("changed_files", []))
        changed_symbols: List[str] = list(change_data.get("changed_symbols", []))
        changed_routes: List[str] = list(change_data.get("changed_routes", []))
        changed_modules: List[str] = list(change_data.get("directly_changed_modules", []))
        affected_tests: List[str] = list(verification_data.get("affected_tests", []))
        missing_tests: List[str] = list(verification_data.get("missing_tests_for_changed_paths", []))

        if not changed_files:
            return {
                "technical_change_summary": "未提供待分析的变更事实。",
                "change_types": [],
                "risk_factors": [],
                "review_recommendations": [],
                "why_impacted": "标准化输入中不存在变更文件。",
                "confidence": "low",
                "unknowns": ["标准化输入中不存在变更文件。"],
                "validation_gaps": missing_tests or ["缺少可用于验证映射的变更面信息。"],
            }

        change_types: List[str] = []
        if changed_routes:
            change_types.append("flow_change")
        if change_data.get("changed_schemas"):
            change_types.append("contract_change")
        if change_data.get("changed_jobs"):
            change_types.append("job_change")
        if change_data.get("changed_functions") or change_data.get("changed_classes"):
            change_types.append("code_modification")
        if not change_types:
            change_types.append("code_modification")

        risk_factors: List[str] = []
        if not affected_tests:
            risk_factors.append("变更路径未关联到带报告的验证证据。")
        if len(changed_modules) > 3:
            risk_factors.append("工作区差异涉及的模块范围较广。")
        if not graph_data.get("dependencies"):
            risk_factors.append("缺少依赖边，无法充分展开传递影响。")

        why_impacted_parts: List[str] = []
        if changed_symbols:
            why_impacted_parts.append(f"变更符号：{', '.join(changed_symbols[:5])}")
        if changed_routes:
            why_impacted_parts.append(f"变更路由：{', '.join(changed_routes[:3])}")
        if changed_modules:
            why_impacted_parts.append(f"变更模块：{', '.join(changed_modules[:5])}")
        if not why_impacted_parts:
            why_impacted_parts.append("影响范围仅依据文件级变更元数据推断。")

        confidence = "high" if affected_tests and graph_data.get("dependencies") else "medium"
        if not affected_tests or not graph_data.get("dependencies"):
            confidence = "low"

        unknowns: List[str] = []
        if not graph_data.get("dependencies"):
            unknowns.append("依赖图不完整，因此传递影响只能保守推断。")
        if not affected_tests:
            unknowns.append("变更面的验证证据较弱或缺失。")

        # Infer a brief change_intent from available facts
        intent_parts: List[str] = []
        if changed_routes:
            intent_parts.append(f"修改 {len(changed_routes)} 个 API 路由")
        if change_data.get("changed_schemas"):
            intent_parts.append("更新数据契约")
        if change_data.get("changed_jobs"):
            intent_parts.append("调整后台任务")
        if changed_symbols:
            intent_parts.append(f"涉及 {len(changed_symbols)} 个符号")
        if not intent_parts:
            intent_parts.append(f"修改 {len(changed_files)} 个文件")
        change_intent = "本次变更" + "；".join(intent_parts) + "。"

        return {
            "technical_change_summary": (
                f"共变更 {len(changed_files)} 个文件；"
                f"涉及 {len(changed_symbols)} 个符号和 {len(changed_routes)} 条路由。"
            ),
            "change_types": change_types,
            "risk_factors": risk_factors,
            "review_recommendations": list(change_data.get("minimal_review_set", [])),
            "why_impacted": " | ".join(why_impacted_parts),
            "change_intent": change_intent,
            "confidence": confidence,
            "unknowns": unknowns,
            "validation_gaps": missing_tests or (["变更文件缺少带报告的测试证据。"] if not affected_tests else []),
        }

    def _merge_unique(self, base: List[str], additions: List[str]) -> List[str]:
        merged: List[str] = []
        for item in base + additions:
            if item and item not in merged:
                merged.append(item)
        return merged

    def _merge_filtered_change_types(self, base: List[str], additions: List[str]) -> List[str]:
        allowed = {"flow_change", "contract_change", "job_change", "code_modification"}
        merged: List[str] = []
        for item in base + additions:
            if item in allowed and item not in merged:
                merged.append(item)
        return merged or ["code_modification"]

    def _merge_review_recommendations(
        self,
        change_data: Dict[str, Any],
        base: List[str],
        additions: List[str],
    ) -> List[str]:
        allowed = set(change_data.get("changed_files", [])) | set(change_data.get("minimal_review_set", []))
        merged: List[str] = []
        for item in base + additions:
            if item in allowed and item not in merged:
                merged.append(item)
        return merged

    def _lower_confidence(self, local_confidence: str, llm_confidence: str) -> str:
        ranking = {"low": 0, "medium": 1, "high": 2}
        if llm_confidence not in ranking:
            return "low"
        if local_confidence not in ranking:
            return llm_confidence
        return min(local_confidence, llm_confidence, key=lambda level: ranking[level])
