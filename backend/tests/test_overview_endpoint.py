import asyncio
import sys
import types
import unittest
import concurrent.futures
from unittest.mock import patch


class _DummyHTTPException(Exception):
    def __init__(self, status_code, detail):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class _DummyAPIRouter:
    def get(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def post(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator


class _DummyFastAPI:
    def __init__(self, *args, **kwargs):
        pass

    def add_middleware(self, *args, **kwargs):
        return None

    def include_router(self, *args, **kwargs):
        return None

    def get(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator


def _install_fastapi_stub():
    if "fastapi" not in sys.modules:
        fastapi_module = types.ModuleType("fastapi")
        fastapi_module.APIRouter = _DummyAPIRouter
        fastapi_module.FastAPI = _DummyFastAPI
        fastapi_module.HTTPException = _DummyHTTPException
        fastapi_module.BackgroundTasks = object
        sys.modules["fastapi"] = fastapi_module

        middleware_module = types.ModuleType("fastapi.middleware")
        cors_module = types.ModuleType("fastapi.middleware.cors")
        cors_module.CORSMiddleware = object
        middleware_module.cors = cors_module
        sys.modules["fastapi.middleware"] = middleware_module
        sys.modules["fastapi.middleware.cors"] = cors_module


_install_fastapi_stub()


class _DummyExecutor:
    def __init__(self, *args, **kwargs):
        pass

    def submit(self, *args, **kwargs):
        raise NotImplementedError

    def shutdown(self, *args, **kwargs):
        return None


concurrent.futures.ProcessPoolExecutor = _DummyExecutor
concurrent.futures.ThreadPoolExecutor = _DummyExecutor

from app.api.endpoints.overview import get_overview  # noqa: E402
from app.api.endpoints.changes import get_latest_changes  # noqa: E402
from app.api.endpoints.verification import get_verification_details  # noqa: E402
from app.api.endpoints.capabilities import get_capability_detail  # noqa: E402
from app.services.snapshot_store.store import store as snapshot_store  # noqa: E402


def _overview_payload(snapshot_id: str):
    return {
        "repo": {"repo_key": "demo", "name": "demo", "default_branch": "main"},
        "snapshot": {
            "base_commit_sha": "HEAD",
            "workspace_snapshot_id": snapshot_id,
            "has_pending_changes": True,
            "status": "ready",
            "generated_at": "2026-04-10T00:00:00Z",
        },
        "project_summary": {"technical_narrative": "demo"},
        "capability_map": [
            {
                "capability_key": "cap_orders",
                "name": "Orders",
                "status": "recently_changed",
                "linked_modules": ["mod_app__api", "mod_app__services"],
                "linked_routes": ["GET /orders"],
                "reasoning_basis": {"route_group": "orders"},
            }
        ],
        "journeys": [],
        "architecture_overview": {"nodes": [], "edges": []},
        "recent_ai_changes": [],
        "verification_status": {
            "build": {"status": "unknown"},
            "unit_tests": {"status": "unknown"},
            "integration_tests": {"status": "unknown"},
            "scenario_replay": {"status": "unknown"},
            "critical_paths": [],
            "unverified_areas": [],
        },
        "warnings": [],
    }


class OverviewEndpointTest(unittest.TestCase):
    def test_get_overview_uses_latest_snapshot_when_no_snapshot_id(self):
        payload = _overview_payload("ws_latest")

        with patch.object(snapshot_store, "get_latest_overview", return_value=payload), patch.object(
            snapshot_store, "get_overview"
        ) as get_overview_mock:
            result = asyncio.run(get_overview(repo_key="demo"))

        self.assertEqual(result.snapshot.workspace_snapshot_id, "ws_latest")
        get_overview_mock.assert_not_called()

    def test_get_overview_honors_workspace_snapshot_id(self):
        payload = _overview_payload("ws_specific")

        with patch.object(snapshot_store, "get_latest_overview") as latest_mock, patch.object(
            snapshot_store, "get_overview", return_value=payload
        ) as get_overview_mock:
            result = asyncio.run(get_overview(repo_key="demo", workspace_snapshot_id="ws_specific"))

        self.assertEqual(result.snapshot.workspace_snapshot_id, "ws_specific")
        get_overview_mock.assert_called_once_with("demo", "ws_specific")
        latest_mock.assert_not_called()

    def test_trigger_rebuild_forwards_include_untracked(self):
        async def _run():
            with patch("app.api.endpoints.overview.job_manager.trigger_rebuild", return_value="job_1") as trigger_mock:
                from app.schemas.overview import RebuildRequest

                request = RebuildRequest(
                    repo_key="demo",
                    base_commit_sha="HEAD",
                    include_untracked=False,
                    workspace_path="/tmp/demo",
                )
                response = await __import__("app.api.endpoints.overview", fromlist=["trigger_rebuild"]).trigger_rebuild(
                    request=request,
                    background_tasks=object(),
                )

            trigger_mock.assert_called_once_with(
                repo_key="demo",
                base_commit_sha="HEAD",
                include_untracked=False,
                workspace_path="/tmp/demo",
            )
            self.assertEqual(response.status, "pending")

        asyncio.run(_run())

    def test_get_latest_changes_reads_snapshot_store(self):
        change_payload = {
            "change_title": "Workspace diff (1 files)",
            "changed_files": ["app/main.py"],
            "impact_reasons": [
                {"entity_id": "mod_app", "reason": "direct_file_change", "distance": 0},
            ],
            "direct_impacts": [
                {
                    "entity_id": "mod_app",
                    "reason": "direct_file_change",
                    "evidence": {"files": ["app/main.py"]},
                    "distance": 0,
                }
            ],
            "transitive_impacts": [
                {
                    "entity_id": "mod_services",
                    "reason": "reachable_via_dependency_graph",
                    "evidence": {"by_direction": {"downstream_dependency": {"from_modules": ["mod_app"]}}},
                    "distance": 1,
                }
            ],
        }
        overview_payload = _overview_payload("ws_latest")

        with patch.object(snapshot_store, "get_latest_overview", return_value=overview_payload), patch.object(
            snapshot_store, "get_change_analysis", return_value=change_payload
        ) as change_mock:
            result = asyncio.run(get_latest_changes(repo_key="demo"))

        self.assertEqual(result, change_payload)
        change_mock.assert_called_once_with("demo", "ws_latest")
        self.assertEqual(result["impact_reasons"], change_payload["impact_reasons"])
        self.assertEqual(result["direct_impacts"], change_payload["direct_impacts"])
        self.assertEqual(result["transitive_impacts"], change_payload["transitive_impacts"])

    def test_get_latest_changes_reports_missing_snapshot_artifact_explicitly(self):
        overview_payload = _overview_payload("ws_latest")

        with patch.object(snapshot_store, "get_latest_overview", return_value=overview_payload), patch.object(
            snapshot_store, "get_change_analysis", return_value=None
        ):
            with self.assertRaises(Exception) as ctx:
                asyncio.run(get_latest_changes(repo_key="demo"))

        self.assertEqual(getattr(ctx.exception, "status_code", None), 404)
        self.assertEqual(
            getattr(ctx.exception, "detail", None),
            "CHANGE_ANALYSIS_UNAVAILABLE: Missing change analysis snapshot artifact for latest snapshot.",
        )

    def test_get_verification_reads_snapshot_store(self):
        verification_payload = {"build": {"status": "unknown"}, "critical_paths": []}
        overview_payload = _overview_payload("ws_latest")

        with patch.object(snapshot_store, "get_latest_overview", return_value=overview_payload), patch.object(
            snapshot_store, "get_verification", return_value=verification_payload
        ) as verification_mock:
            result = asyncio.run(get_verification_details(repo_key="demo"))

        self.assertEqual(result, verification_payload)
        verification_mock.assert_called_once_with("demo", "ws_latest")

    def test_get_verification_reports_missing_snapshot_artifact_explicitly(self):
        overview_payload = _overview_payload("ws_latest")

        with patch.object(snapshot_store, "get_latest_overview", return_value=overview_payload), patch.object(
            snapshot_store, "get_verification", return_value=None
        ):
            with self.assertRaises(Exception) as ctx:
                asyncio.run(get_verification_details(repo_key="demo"))

        self.assertEqual(getattr(ctx.exception, "status_code", None), 404)
        self.assertEqual(
            getattr(ctx.exception, "detail", None),
            "VERIFICATION_UNAVAILABLE: Missing verification snapshot artifact for latest snapshot.",
        )

    def test_capability_detail_reads_from_latest_snapshot(self):
        overview_payload = _overview_payload("ws_latest")

        with patch.object(snapshot_store, "get_latest_overview", return_value=overview_payload):
            result = asyncio.run(get_capability_detail(repo_key="demo", capability_key="cap_orders"))

        self.assertEqual(result["capability_key"], "cap_orders")
        self.assertEqual(result["linked_routes"], ["GET /orders"])

    def test_capability_detail_reports_missing_key_as_404(self):
        overview_payload = _overview_payload("ws_latest")

        with patch.object(snapshot_store, "get_latest_overview", return_value=overview_payload):
            with self.assertRaises(Exception) as ctx:
                asyncio.run(get_capability_detail(repo_key="demo", capability_key="cap_missing"))

        self.assertEqual(getattr(ctx.exception, "status_code", None), 404)
        self.assertEqual(
            getattr(ctx.exception, "detail", None),
            "CAPABILITY_NOT_FOUND: capability_key=cap_missing",
        )


if __name__ == "__main__":
    unittest.main()
