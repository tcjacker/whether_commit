import os
import unittest
from unittest.mock import patch

from app.services.overview_inference.llm_reasoning import LLMReasoningService


class ProviderSettingsTest(unittest.TestCase):
    def test_settings_reads_enabled_openai_compatible_provider(self):
        from app.config.settings import ObservabilitySettings

        env = {
            "OBS_REASONING_PROVIDER_ENABLED": "true",
            "OBS_REASONING_PROVIDER_NAME": "openai_compatible",
            "OBS_REASONING_MODEL": "qwen-plus",
            "OBS_REASONING_BASE_URL": "https://example.com/v1/chat/completions",
            "OBS_REASONING_API_KEY": "sk-test",
            "OBS_REASONING_TIMEOUT_SECONDS": "45",
        }

        with patch.dict(os.environ, env, clear=False):
            settings = ObservabilitySettings.from_env()

        self.assertTrue(settings.reasoning_provider_enabled)
        self.assertEqual(settings.reasoning_provider_name, "openai_compatible")
        self.assertEqual(settings.reasoning_model, "qwen-plus")
        self.assertEqual(settings.reasoning_timeout_seconds, 45)

    def test_settings_disable_provider_when_credentials_missing(self):
        from app.config.settings import ObservabilitySettings
        from app.config import settings as settings_module

        env = {
            "OBS_REASONING_PROVIDER_ENABLED": "true",
            "OBS_REASONING_PROVIDER_NAME": "openai_compatible",
            "OBS_REASONING_MODEL": "qwen-plus",
            "OBS_REASONING_BASE_URL": "https://example.com/v1/chat/completions",
        }

        with patch.object(settings_module, "_load_local_env_file", return_value={}), patch.dict(os.environ, env, clear=True):
            settings = ObservabilitySettings.from_env()

        self.assertTrue(settings.reasoning_provider_enabled)
        self.assertIsNone(settings.reasoning_api_key)

    def test_settings_load_from_local_env_file_when_process_env_is_empty(self):
        from app.config import settings as settings_module
        from app.config.settings import ObservabilitySettings

        with patch.object(
            settings_module,
            "_load_local_env_file",
            return_value={
                "OBS_REASONING_PROVIDER_ENABLED": "true",
                "OBS_REASONING_PROVIDER_NAME": "openai_compatible",
                "OBS_REASONING_MODEL": "qwen-plus",
                "OBS_REASONING_BASE_URL": "https://example.com/v1/chat/completions",
                "OBS_REASONING_API_KEY": "sk-local",
            },
        ), patch.dict(os.environ, {}, clear=True):
            settings = ObservabilitySettings.from_env()

        self.assertTrue(settings.reasoning_provider_enabled)
        self.assertEqual(settings.reasoning_api_key, "sk-local")

    def test_unsupported_provider_name_fails_clearly(self):
        from app.config.settings import ObservabilitySettings
        from app.services.overview_inference.provider_clients import build_reasoning_provider

        settings = ObservabilitySettings(
            reasoning_provider_enabled=True,
            reasoning_provider_name="unsupported",
            reasoning_model="demo",
            reasoning_base_url="https://example.com/v1/chat/completions",
            reasoning_api_key="sk-test",
        )

        with self.assertRaisesRegex(ValueError, "Unsupported reasoning provider"):
            build_reasoning_provider(settings)

    def test_missing_credentials_disable_provider_factory(self):
        from app.config.settings import ObservabilitySettings
        from app.services.overview_inference.provider_clients import build_reasoning_provider

        settings = ObservabilitySettings(
            reasoning_provider_enabled=True,
            reasoning_provider_name="openai_compatible",
            reasoning_model="demo",
            reasoning_base_url="https://example.com/v1/chat/completions",
            reasoning_api_key=None,
        )

        provider = build_reasoning_provider(settings)

        self.assertIsNone(provider)


class ProviderBackedLLMReasoningServiceTest(unittest.TestCase):
    def test_from_settings_uses_real_provider_factory_without_network(self):
        from app.config.settings import ObservabilitySettings

        settings = ObservabilitySettings(
            reasoning_provider_enabled=True,
            reasoning_provider_name="openai_compatible",
            reasoning_model="demo-model",
            reasoning_base_url="https://example.com/v1/chat/completions",
            reasoning_api_key="sk-test",
        )

        captured = {}

        def fake_provider(payload):
            captured["payload"] = payload
            return {
                "technical_change_summary": "summary",
                "change_types": ["code_modification"],
                "risk_factors": [],
                "review_recommendations": ["backend/app/api/routes.py"],
                "why_impacted": "normalized facts only",
                "confidence": "low",
                "unknowns": [],
                "validation_gaps": [],
                "evidence_used": ["backend/app/api/routes.py"],
            }

        service = LLMReasoningService.from_settings(settings, provider=fake_provider)
        result = service.reason(
            {
                "normalized_facts": {
                    "changed_files": ["backend/app/api/routes.py"],
                    "changed_symbols": [],
                    "changed_routes": [],
                    "changed_schemas": [],
                    "changed_jobs": [],
                    "direct_impacts": [],
                    "transitive_impacts": [],
                    "graph_edges": [],
                    "verification_evidence": {},
                    "unknowns": [],
                }
            }
        )

        self.assertEqual(result["status"], "accepted")
        self.assertIn("payload", captured)


if __name__ == "__main__":
    unittest.main()
