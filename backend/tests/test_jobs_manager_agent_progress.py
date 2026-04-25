import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from app.schemas.job import JobState, WorkspaceSnapshotState
from app.services.jobs.manager import JobManager


class JobManagerAgentProgressTest(unittest.IsolatedAsyncioTestCase):
    async def test_pending_changes_rebuild_emits_fine_grained_overview_steps(self):
        manager = JobManager(data_dir=tempfile.mkdtemp())
        repo_key = "demo"
        job = JobState(
            job_id="job_progress_1",
            repo_key=repo_key,
            base_commit_sha="HEAD",
            include_untracked=True,
            workspace_snapshot_id="pending",
            workspace_path="/tmp/demo",
            status="pending",
            step="init",
            progress=0,
            message="init",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        manager.job_registry[job.job_id] = job

        pending_snapshot = WorkspaceSnapshotState(
            repo_key=repo_key,
            base_commit_sha="HEAD",
            workspace_snapshot_id="ws_pending_123",
            has_pending_changes=True,
            changed_files=["app/main.py"],
            status_lines=[" M app/main.py"],
            fingerprint="123",
        )

        graph_payload = {
            "modules": [{"module_id": "mod_app", "name": "app", "type": "module", "linked_symbols": []}],
            "symbols": [],
            "routes": [],
            "dependencies": [],
            "data_objects": [],
            "integrations": [],
        }
        change_payload = {
            "base_commit_sha": "HEAD",
            "workspace_snapshot_id": "ws_pending_123",
            "change_title": "工作区差异（1 个文件）",
            "changed_files": ["app/main.py"],
            "changed_symbols": ["handler"],
            "changed_routes": [],
            "changed_modules": ["mod_app"],
            "directly_changed_modules": ["mod_app"],
            "transitively_affected_modules": [],
            "blast_radius": ["mod_app"],
            "minimal_review_set": ["app/main.py"],
            "linked_tests": [],
            "risk_score": 0.1,
        }
        verification_payload = {
            "build": {"status": "unknown"},
            "unit_tests": {"status": "unknown"},
            "integration_tests": {"status": "unknown"},
            "scenario_replay": {"status": "unknown"},
            "critical_paths": [],
            "unverified_areas": [],
            "verified_changed_modules": [],
            "unverified_changed_modules": ["mod_app"],
            "affected_tests": [],
            "missing_tests_for_changed_paths": ["app/main.py"],
            "critical_changed_paths": [],
            "evidence_by_path": {"app/main.py": "No direct tests found"},
        }
        overview_payload = {
            "snapshot": {"workspace_snapshot_id": "ws_pending_123", "has_pending_changes": True},
            "project_summary": {"overall_assessment": "综合判断", "impact_level": "medium"},
            "recent_ai_changes": [],
            "change_themes": [],
            "capability_map": [],
            "agent_harness_status": "accepted",
            "agent_harness_metadata": {"rounds_used": 2, "requests_used": 1},
        }

        updates = []
        observed_job_steps_during_overview = []
        loop_scheduled_updates = []
        original_update_sync = manager._update_job_status_sync
        overview_steps = {
            "prepare_agent_context",
            "agent_round_1",
            "agent_round_2",
            "validate_agent_output",
            "build_overview_payload",
        }
        in_loop_handoff = False

        def _record_update_sync(job_state, status, step, progress, message):
            if step in overview_steps:
                self.assertTrue(in_loop_handoff, f"{step} should be marshalled through call_soon_threadsafe")
            updates.append(
                {
                    "status": status,
                    "step": step,
                    "progress": progress,
                    "message": message,
                }
            )
            original_update_sync(job_state, status, step, progress, message)

        class _FakeLoop:
            def call_soon_threadsafe(self, callback, *args):
                nonlocal in_loop_handoff
                loop_scheduled_updates.append(
                    {
                        "callback": getattr(callback, "__name__", repr(callback)),
                        "args": args,
                    }
                )
                in_loop_handoff = True
                try:
                    callback(*args)
                finally:
                    in_loop_handoff = False

            async def run_in_executor(self, executor, func, *args):
                return func(*args)

        class _FakeGraphAdapter:
            def __init__(self, workspace_path):
                self.workspace_path = workspace_path

            def generate_graph_snapshot(self):
                return graph_payload

        class _FakeChangeImpactAdapter:
            def __init__(self, workspace_path, base_commit_sha):
                self.workspace_path = workspace_path
                self.base_commit_sha = base_commit_sha

            def generate_change_analysis(self, workspace_snapshot_id):
                return change_payload

        class _FakeVerificationAdapter:
            def __init__(self, workspace_path):
                self.workspace_path = workspace_path

            def aggregate_verification(self, change_data, graph_data=None):
                return verification_payload

        class _FakeOverviewInferenceService:
            def build_overview(
                self,
                repo_key,
                snapshot_id,
                graph_data,
                change_data,
                verification_data,
                progress_reporter=None,
            ):
                assert progress_reporter is not None
                progress_reporter("prepare_agent_context")
                observed_job_steps_during_overview.append(manager.job_registry[job.job_id].step)
                progress_reporter("agent_round_1")
                observed_job_steps_during_overview.append(manager.job_registry[job.job_id].step)
                progress_reporter("agent_round_2")
                observed_job_steps_during_overview.append(manager.job_registry[job.job_id].step)
                progress_reporter("validate_agent_output")
                progress_reporter("build_overview_payload")
                return overview_payload

        with patch.object(manager.workspace_snapshot_service, "capture", return_value=pending_snapshot), patch(
            "app.services.jobs.manager.GraphAdapter", _FakeGraphAdapter
        ), patch(
            "app.services.jobs.manager.ChangeImpactAdapter", _FakeChangeImpactAdapter
        ), patch(
            "app.services.jobs.manager.VerificationAdapter", _FakeVerificationAdapter
        ), patch(
            "app.services.jobs.manager.asyncio.get_running_loop", return_value=_FakeLoop()
        ), patch.object(
            manager,
            "overview_inference_service",
            _FakeOverviewInferenceService(),
        ), patch.object(
            manager,
            "_update_job_status_sync",
            side_effect=_record_update_sync,
        ), patch("app.services.jobs.manager.snapshot_store.save_graph_snapshot"), patch(
            "app.services.jobs.manager.snapshot_store.save_change_analysis"
        ), patch(
            "app.services.jobs.manager.snapshot_store.save_verification"
        ), patch(
            "app.services.jobs.manager.snapshot_store.save_overview"
        ), patch(
            "app.services.jobs.manager.snapshot_store.update_latest_pointer"
        ):
            await manager._run_rebuild_flow(job.job_id, manager._get_repo_lock(repo_key))

        steps = [entry["step"] for entry in updates if entry["status"] in {"running", "success"}]
        self.assertEqual(
            observed_job_steps_during_overview,
            [
                "prepare_agent_context",
                "agent_round_1",
                "agent_round_2",
            ],
        )
        self.assertEqual(
            [entry["args"][2] for entry in loop_scheduled_updates],
            [
                "prepare_agent_context",
                "agent_round_1",
                "agent_round_2",
                "validate_agent_output",
                "build_overview_payload",
            ],
        )
        self.assertEqual(
            steps,
            [
                "capture_working_tree",
                "build_graph_snapshot",
                "analyze_pending_change",
                "aggregate_verification",
                "prepare_agent_context",
                "agent_round_1",
                "agent_round_2",
                "validate_agent_output",
                "build_overview_payload",
                "done",
            ],
        )
        if "agent_round_2" in steps:
            self.assertGreater(steps.index("agent_round_2"), steps.index("agent_round_1"))


if __name__ == "__main__":
    unittest.main()
