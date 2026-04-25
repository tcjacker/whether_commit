import unittest

from pydantic import ValidationError

from app.schemas.agent_harness import AgentHarnessReadRequest, AgentHarnessResponse
from app.schemas.overview import OverviewResponse


class AgentHarnessSchemaTest(unittest.TestCase):
    def test_read_request_rejects_unsupported_target_type(self):
        with self.assertRaises(ValidationError):
            AgentHarnessReadRequest.model_validate(
                {
                    "target_type": "shell_command",
                    "target_id": "app/main.py",
                    "reason": "not supported",
                }
            )

    def test_response_supports_fallback_contract(self):
        payload = AgentHarnessResponse.model_validate(
            {
                "status": "fallback",
                "read_requests": [],
                "project_summary": {
                    "overall_assessment": "本次分析已降级为结构化摘要。",
                    "impact_level": "unknown",
                    "impact_basis": [],
                    "priority_themes": [],
                },
                "capabilities": [
                    {
                        "capability_key": "cap-orders",
                        "name": "Orders",
                        "impact_status": "unknown",
                    }
                ],
                "change_themes": [
                    {
                        "theme_key": "theme-orders",
                        "name": "Orders flow",
                    }
                ],
            }
        )

        self.assertEqual(payload.status, "fallback")
        self.assertEqual(payload.project_summary.impact_level, "unknown")
        self.assertEqual(len(payload.capabilities), 1)
        self.assertEqual(len(payload.change_themes), 1)

    def test_overview_response_accepts_agent_harness_summary_fields(self):
        overview = OverviewResponse.model_validate(
            {
                "repo": {"repo_key": "demo", "name": "demo", "default_branch": "main"},
                "snapshot": {
                    "base_commit_sha": "HEAD",
                    "workspace_snapshot_id": "ws_1",
                    "has_pending_changes": True,
                    "status": "ready",
                    "generated_at": "2026-04-11T00:00:00+00:00",
                },
                "project_summary": {
                    "overall_assessment": "本次分析已降级为结构化摘要。",
                    "impact_level": "unknown",
                    "impact_basis": [],
                    "affected_entrypoints": ["GET /health"],
                    "critical_paths": [],
                    "priority_themes": [],
                    "what_this_app_seems_to_do": "demo app",
                    "technical_narrative": "compatibility check",
                    "core_flow": "client -> api",
                },
                "change_themes": [
                    {
                        "theme_key": "theme-orders",
                        "name": "Orders flow",
                    }
                ],
                "agent_harness_status": "fallback",
            }
        )

        self.assertEqual(overview.project_summary.impact_level, "unknown")
        self.assertEqual(overview.agent_harness_status, "fallback")
        self.assertEqual(overview.change_themes[0].name, "Orders flow")

