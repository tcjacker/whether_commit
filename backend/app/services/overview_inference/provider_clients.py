from __future__ import annotations

import json
import urllib.request
from typing import Any, Callable, Dict

from app.config.settings import ObservabilitySettings


def build_reasoning_provider(settings: ObservabilitySettings) -> Callable[[Dict[str, Any]], Any] | None:
    if not settings.reasoning_provider_enabled:
        return None
    if not settings.reasoning_provider_name:
        return None
    if settings.reasoning_provider_name != "openai_compatible":
        raise ValueError(f"Unsupported reasoning provider: {settings.reasoning_provider_name}")
    if not settings.provider_is_configured():
        return None
    return _build_openai_compatible_provider(settings)


def _build_openai_compatible_provider(settings: ObservabilitySettings) -> Callable[[Dict[str, Any]], Any]:
    def provider(prompt_payload: Dict[str, Any]) -> Any:
        request_body = {
            "model": settings.reasoning_model,
            "messages": [
                {
                    "role": "system",
                    "content": "Return structured JSON only. Use only the provided normalized_facts.",
                },
                {
                    "role": "user",
                    "content": json.dumps(prompt_payload, ensure_ascii=True),
                },
            ],
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            settings.reasoning_base_url,
            data=json.dumps(request_body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.reasoning_api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=settings.reasoning_timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        choices = payload.get("choices", [])
        if not choices:
            raise RuntimeError("Reasoning provider returned no choices.")
        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        return content

    return provider
