from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value.strip())
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class ObservabilitySettings:
    reasoning_provider_enabled: bool = False
    reasoning_provider_name: str | None = None
    reasoning_model: str | None = None
    reasoning_base_url: str | None = None
    reasoning_api_key: str | None = None
    reasoning_timeout_seconds: int = 30

    @classmethod
    def from_env(cls) -> "ObservabilitySettings":
        file_values = _load_local_env_file()
        return cls(
            reasoning_provider_enabled=_parse_bool(
                os.getenv("OBS_REASONING_PROVIDER_ENABLED", file_values.get("OBS_REASONING_PROVIDER_ENABLED")),
                default=False,
            ),
            reasoning_provider_name=os.getenv("OBS_REASONING_PROVIDER_NAME", file_values.get("OBS_REASONING_PROVIDER_NAME")),
            reasoning_model=os.getenv("OBS_REASONING_MODEL", file_values.get("OBS_REASONING_MODEL")),
            reasoning_base_url=os.getenv("OBS_REASONING_BASE_URL", file_values.get("OBS_REASONING_BASE_URL")),
            reasoning_api_key=os.getenv("OBS_REASONING_API_KEY", file_values.get("OBS_REASONING_API_KEY")),
            reasoning_timeout_seconds=_parse_int(
                os.getenv("OBS_REASONING_TIMEOUT_SECONDS", file_values.get("OBS_REASONING_TIMEOUT_SECONDS")),
                default=30,
            ),
        )

    def provider_is_configured(self) -> bool:
        return bool(
            self.reasoning_provider_enabled
            and self.reasoning_provider_name
            and self.reasoning_model
            and self.reasoning_base_url
            and self.reasoning_api_key
        )


def _load_local_env_file() -> dict[str, str]:
    env_path = Path(__file__).resolve().parents[2] / ".env.reasoning.local"
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values
