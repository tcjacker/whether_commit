from __future__ import annotations

import json
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

from app.config.settings import ObservabilitySettings
from app.services.overview_inference.prompt_builder import ReasoningPromptBuilder
from app.services.overview_inference.provider_clients import build_reasoning_provider


class LLMReasoningService:
    """
    Structured reasoning adapter for an external LLM.

    The adapter accepts injectable provider/client objects so tests can use a
    fake implementation without any network dependency.
    """

    REQUIRED_FIELDS = (
        "technical_change_summary",
        "change_types",
        "risk_factors",
        "review_recommendations",
        "why_impacted",
        "confidence",
        "unknowns",
        "validation_gaps",
        "evidence_used",
    )

    ALLOWED_CONFIDENCE = {"high", "medium", "low"}

    def __init__(
        self,
        provider: Callable[[Dict[str, Any]], Any] | None = None,
        client: Any | None = None,
        prompt_builder: ReasoningPromptBuilder | None = None,
    ) -> None:
        self.provider = provider
        self.client = client
        self.prompt_builder = prompt_builder or ReasoningPromptBuilder()

    @classmethod
    def from_settings(
        cls,
        settings: ObservabilitySettings,
        provider: Callable[[Dict[str, Any]], Any] | None = None,
        prompt_builder: ReasoningPromptBuilder | None = None,
    ) -> "LLMReasoningService":
        resolved_provider = provider if provider is not None else build_reasoning_provider(settings)
        return cls(provider=resolved_provider, prompt_builder=prompt_builder)

    def reason(self, prompt_payload: Dict[str, Any]) -> Dict[str, Any]:
        raw_response = self._invoke(prompt_payload)
        parsed, parse_error = self._parse_response(raw_response)
        if parse_error:
            return self._rejected_result(prompt_payload, [parse_error], parsed)

        validation_issues = self._validate(parsed, prompt_payload)
        if validation_issues:
            return self._rejected_result(prompt_payload, validation_issues, parsed)

        reasoning = self._normalize_reasoning(parsed, prompt_payload)
        return {
            "status": "accepted",
            "accepted": True,
            "validation_issues": [],
            "reasoning": reasoning,
        }

    def build_prompt(
        self,
        graph_data: Dict[str, Any],
        change_data: Dict[str, Any],
        verification_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        return self.prompt_builder.build(graph_data, change_data, verification_data)

    def _invoke(self, prompt_payload: Dict[str, Any]) -> Any:
        if self.provider is not None:
            return self.provider(prompt_payload)

        if self.client is None:
            raise RuntimeError("No LLM provider or client configured.")

        for method_name in ("complete", "generate", "chat", "create_completion", "respond"):
            method = getattr(self.client, method_name, None)
            if callable(method):
                return method(prompt_payload)

        if callable(self.client):
            return self.client(prompt_payload)

        raise RuntimeError("Configured LLM client does not expose a supported invocation method.")

    def _parse_response(self, raw_response: Any) -> tuple[Dict[str, Any], Optional[str]]:
        if isinstance(raw_response, dict):
            return raw_response, None

        content: Any = raw_response
        if hasattr(raw_response, "content"):
            content = getattr(raw_response, "content")
        elif hasattr(raw_response, "text"):
            content = getattr(raw_response, "text")

        if isinstance(content, dict):
            return content, None
        if not isinstance(content, str):
            return {}, "LLM response was not JSON-serializable."

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            return {}, f"LLM response was not valid JSON: {exc.msg}"

        if not isinstance(parsed, dict):
            return {}, "LLM response JSON must be an object."

        return parsed, None

    def _validate(self, parsed: Dict[str, Any], prompt_payload: Dict[str, Any]) -> List[str]:
        issues: List[str] = []
        missing = [field for field in self.REQUIRED_FIELDS if field not in parsed]
        if missing:
            issues.append("required_fields")
            issues.append(f"required_fields:{','.join(missing)}")
            return issues

        confidence = parsed.get("confidence")
        if confidence not in self.ALLOWED_CONFIDENCE:
            issues.append("confidence")

        evidence_used = parsed.get("evidence_used", [])
        if not isinstance(evidence_used, list):
            issues.append("evidence_used_type")
            return issues

        normalized_facts = prompt_payload.get("normalized_facts", {})
        allowed_evidence = self._available_evidence_keys(normalized_facts)
        unknown_evidence = [item for item in evidence_used if item not in allowed_evidence]
        if unknown_evidence:
            issues.append(f"unavailable_evidence:{','.join(sorted(set(unknown_evidence)))}")

        return issues

    def _available_evidence_keys(self, normalized_facts: Mapping[str, Any]) -> set[str]:
        allowed: set[str] = set()
        for key in (
            "changed_files",
            "changed_symbols",
            "changed_routes",
            "changed_schemas",
            "changed_jobs",
            "direct_impacts",
            "transitive_impacts",
        ):
            allowed.update(str(item) for item in normalized_facts.get(key, []))
        for edge in normalized_facts.get("graph_edges", []):
            if isinstance(edge, dict):
                source = edge.get("from")
                target = edge.get("to")
                if source:
                    allowed.add(str(source))
                if target:
                    allowed.add(str(target))
                edge_type = edge.get("type")
                if edge_type:
                    allowed.add(str(edge_type))
        allowed.update(str(item) for item in normalized_facts.get("unknowns", []))
        allowed.update(str(key) for key in normalized_facts.get("verification_evidence", {}).keys())
        return allowed

    def _rejected_result(
        self,
        prompt_payload: Dict[str, Any],
        validation_issues: Sequence[str],
        parsed: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        fallback = self._fallback_reasoning(prompt_payload)
        return {
            "status": "rejected",
            "accepted": False,
            "validation_issues": list(validation_issues),
            "reasoning": fallback,
            "parsed_reasoning": parsed or {},
        }

    def _fallback_reasoning(self, prompt_payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized_facts = prompt_payload.get("normalized_facts", {})
        changed_files = list(normalized_facts.get("changed_files", []))
        changed_symbols = list(normalized_facts.get("changed_symbols", []))
        changed_routes = list(normalized_facts.get("changed_routes", []))
        changed_schemas = list(normalized_facts.get("changed_schemas", []))
        changed_jobs = list(normalized_facts.get("changed_jobs", []))
        direct_impacts = list(normalized_facts.get("direct_impacts", []))
        transitive_impacts = list(normalized_facts.get("transitive_impacts", []))
        unknowns = list(normalized_facts.get("unknowns", []))

        summary_bits = [
            f"{len(changed_files)} files",
            f"{len(changed_symbols)} symbols",
            f"{len(changed_routes)} routes",
            f"{len(changed_schemas)} schemas",
            f"{len(changed_jobs)} jobs",
        ]

        change_types: List[str] = []
        if changed_routes:
            change_types.append("flow_change")
        if changed_schemas:
            change_types.append("contract_change")
        if changed_jobs:
            change_types.append("job_change")
        if changed_files:
            change_types.append("code_modification")
        if not change_types:
            change_types.append("code_modification")

        review_recommendations = list(changed_files[:5])
        validation_gaps = list(unknowns)
        if not validation_gaps:
            validation_gaps.append("No explicit verification evidence was available.")

        return {
            "technical_change_summary": "Changed surface: " + ", ".join(summary_bits),
            "change_types": change_types,
            "risk_factors": list(unknowns) or ["Evidence is sparse, so reasoning remains conservative."],
            "review_recommendations": review_recommendations,
            "why_impacted": self._join_nonempty(
                [
                    f"Direct impacts: {', '.join(direct_impacts)}" if direct_impacts else "",
                    f"Transitive impacts: {', '.join(transitive_impacts)}" if transitive_impacts else "",
                    f"Symbols: {', '.join(changed_symbols)}" if changed_symbols else "",
                ]
            )
            or "Impact was inferred conservatively from normalized facts.",
            "confidence": "low",
            "unknowns": unknowns,
            "validation_gaps": validation_gaps,
            "evidence_used": [],
        }

    def _normalize_reasoning(self, parsed: Dict[str, Any], prompt_payload: Dict[str, Any]) -> Dict[str, Any]:
        fallback = self._fallback_reasoning(prompt_payload)
        normalized_facts = prompt_payload.get("normalized_facts", {})
        allowed_files = set(normalized_facts.get("changed_files", [])) | set(fallback["review_recommendations"])
        allowed_change_types = {"flow_change", "contract_change", "job_change", "code_modification"}

        reasoning = dict(fallback)
        reasoning["technical_change_summary"] = self._coerce_text(parsed.get("technical_change_summary")) or fallback["technical_change_summary"]
        reasoning["change_types"] = self._filtered_strings(parsed.get("change_types", []), allowed_change_types) or fallback["change_types"]
        reasoning["risk_factors"] = self._filtered_text_list(parsed.get("risk_factors", [])) or fallback["risk_factors"]
        reasoning["review_recommendations"] = self._filtered_strings(parsed.get("review_recommendations", []), allowed_files) or fallback["review_recommendations"]
        reasoning["why_impacted"] = self._coerce_text(parsed.get("why_impacted")) or fallback["why_impacted"]
        reasoning["confidence"] = parsed.get("confidence") if parsed.get("confidence") in self.ALLOWED_CONFIDENCE else fallback["confidence"]
        reasoning["unknowns"] = self._filtered_text_list(parsed.get("unknowns", [])) or fallback["unknowns"]
        reasoning["validation_gaps"] = self._filtered_text_list(parsed.get("validation_gaps", [])) or fallback["validation_gaps"]
        reasoning["evidence_used"] = self._filtered_text_list(parsed.get("evidence_used", []))
        if parsed.get("change_intent"):
            reasoning["change_intent"] = self._coerce_text(parsed["change_intent"])
        reasoning["llm_reasoning"] = {
            "status": "accepted",
            "validation_issues": [],
        }
        return reasoning

    def _filtered_strings(self, values: Any, allowed: set[str]) -> List[str]:
        if not isinstance(values, list):
            return []
        filtered: List[str] = []
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text and text in allowed and text not in filtered:
                filtered.append(text)
        return filtered

    def _filtered_text_list(self, values: Any) -> List[str]:
        if not isinstance(values, list):
            return []
        filtered: List[str] = []
        for value in values:
            text = self._coerce_text(value)
            if text and text not in filtered:
                filtered.append(text)
        return filtered

    def _coerce_text(self, value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        return text[:240]

    def _join_nonempty(self, parts: Iterable[str]) -> str:
        return " | ".join(part for part in parts if part)
