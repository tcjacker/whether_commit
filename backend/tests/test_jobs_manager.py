import asyncio
import tempfile
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from app.schemas.job import JobState, WorkspaceSnapshotState
from app.services.jobs.manager import JobManager
from app.services.workspace_snapshot.service import WorkspaceSnapshotService


class WorkspaceSnapshotServiceTest(unittest.TestCase):
    def test_capture_builds_stable_snapshot_id(self):
        service = WorkspaceSnapshotService()

        def fake_run(cmd, cwd, capture_output, text, check):
            if cmd[:2] == ["git", "rev-parse"]:
                return SimpleNamespace(stdout="true\n")
            return SimpleNamespace(stdout=" M app/main.py\n?? docs/readme.md\n")

        with tempfile.TemporaryDirectory() as tmp_dir, patch(
            "app.services.workspace_snapshot.service.subprocess.run", side_effect=fake_run
        ):
            snapshot_a = service.capture("demo", tmp_dir, base_commit_sha="HEAD", include_untracked=True)
            snapshot_b = service.capture("demo", tmp_dir, base_commit_sha="HEAD", include_untracked=True)

        self.assertTrue(snapshot_a.has_pending_changes)
        self.assertEqual(snapshot_a.changed_files, ["app/main.py", "docs/readme.md"])
        self.assertEqual(snapshot_a.workspace_snapshot_id, snapshot_b.workspace_snapshot_id)
        self.assertEqual(snapshot_a.fingerprint, snapshot_b.fingerprint)

    def test_capture_accepts_git_worktree_metadata_file(self):
        service = WorkspaceSnapshotService()

        def fake_run(cmd, cwd, capture_output, text, check):
            if cmd[:2] == ["git", "rev-parse"]:
                return SimpleNamespace(stdout="true\n")
            return SimpleNamespace(stdout="")

        with tempfile.TemporaryDirectory() as tmp_dir, patch(
            "app.services.workspace_snapshot.service.subprocess.run", side_effect=fake_run
        ), patch("app.services.workspace_snapshot.service.os.path.exists", return_value=False):
            snapshot = service.capture("demo", tmp_dir, base_commit_sha="HEAD", include_untracked=True)

        self.assertFalse(snapshot.has_pending_changes)
        self.assertEqual(snapshot.changed_files, [])


class JobManagerTest(unittest.IsolatedAsyncioTestCase):
    async def test_trigger_rebuild_resolves_workspace_path_from_local_candidates(self):
        manager = JobManager(data_dir=tempfile.mkdtemp())

        def _discard_task(coro):
            coro.close()
            return None

        with tempfile.TemporaryDirectory() as tmp_root, patch(
            "app.services.jobs.manager.Path.home", return_value=__import__("pathlib").Path(tmp_root)
        ), patch.object(
            manager.workspace_snapshot_service,
            "is_git_workspace",
            side_effect=lambda path: path == f"{tmp_root}/divide_prd_to_ui",
        ), patch(
            "app.services.jobs.manager.asyncio.create_task", side_effect=_discard_task
        ):
            job_id = await manager.trigger_rebuild(repo_key="divide_prd_to_ui")

        self.assertEqual(manager.job_registry[job_id].workspace_path, f"{tmp_root}/divide_prd_to_ui")

    async def test_trigger_rebuild_preserves_include_untracked_flag(self):
        manager = JobManager(data_dir=tempfile.mkdtemp())
        captured = {}

        class _FakeWorkspaceSnapshotService:
            def capture(self, repo_key, workspace_path, base_commit_sha, include_untracked):
                captured["include_untracked"] = include_untracked
                return WorkspaceSnapshotState(
                    repo_key=repo_key,
                    base_commit_sha=base_commit_sha,
                    workspace_snapshot_id="ws_pending_123",
                    has_pending_changes=False,
                    changed_files=[],
                    status_lines=[],
                    fingerprint="123",
                )

        def _discard_task(coro):
            coro.close()
            return None

        with patch.object(manager, "workspace_snapshot_service", _FakeWorkspaceSnapshotService()), patch(
            "app.services.jobs.manager.asyncio.create_task", side_effect=_discard_task
        ), patch(
            "app.services.jobs.manager.snapshot_store.save_overview"
        ), patch("app.services.jobs.manager.snapshot_store.update_latest_pointer"):
            job_id = await manager.trigger_rebuild(
                repo_key="demo",
                base_commit_sha="HEAD",
                include_untracked=False,
                workspace_path="/tmp/demo",
            )
            await manager._run_rebuild_flow(job_id, manager._get_repo_lock("demo"))

        self.assertFalse(captured["include_untracked"])

    async def test_run_rebuild_flow_short_circuits_when_no_pending_changes(self):
        manager = JobManager(data_dir=tempfile.mkdtemp())
        repo_key = "demo"
        job = JobState(
            job_id="job_1",
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

        clean_snapshot = WorkspaceSnapshotState(
            repo_key=repo_key,
            base_commit_sha="HEAD",
            workspace_snapshot_id="ws_clean_123",
            has_pending_changes=False,
            changed_files=[],
            status_lines=[],
            fingerprint="123",
        )

        save_overview_calls = []
        update_latest_calls = []

        with patch.object(manager.workspace_snapshot_service, "capture", return_value=clean_snapshot) as capture_mock, patch(
            "app.services.jobs.manager.GraphAdapter", side_effect=AssertionError("GraphAdapter should not be used")
        ), patch(
            "app.services.jobs.manager.ChangeImpactAdapter", side_effect=AssertionError("ChangeImpactAdapter should not be used")
        ), patch(
            "app.services.jobs.manager.VerificationAdapter", side_effect=AssertionError("VerificationAdapter should not be used")
        ), patch(
            "app.services.jobs.manager.snapshot_store.save_overview",
            side_effect=lambda repo, snapshot_id, payload, **kwargs: save_overview_calls.append((repo, snapshot_id, payload, kwargs)),
        ), patch(
            "app.services.jobs.manager.snapshot_store.save_assessment_manifest"
        ), patch(
            "app.services.jobs.manager.snapshot_store.save_assessment_file_detail"
        ), patch(
            "app.services.jobs.manager.snapshot_store.save_assessment_review_state"
        ), patch(
            "app.services.jobs.manager.snapshot_store.update_latest_pointer",
            side_effect=lambda repo, payload, **kwargs: update_latest_calls.append((repo, payload, kwargs)),
        ):
            await manager._run_rebuild_flow(job.job_id, manager._get_repo_lock(repo_key))

        self.assertEqual(manager.job_registry[job.job_id].status, "success")
        self.assertEqual(manager.job_registry[job.job_id].step, "done")
        self.assertEqual(manager.job_registry[job.job_id].workspace_snapshot_id, "ws_clean_123")
        self.assertEqual(capture_mock.call_count, 1)
        self.assertEqual(len(save_overview_calls), 1)
        self.assertFalse(save_overview_calls[0][2]["snapshot"]["has_pending_changes"])
        self.assertEqual(save_overview_calls[0][3]["workspace_path"], "/tmp/demo")
        self.assertEqual(len(update_latest_calls), 1)
        self.assertFalse(update_latest_calls[0][1]["has_pending_changes"])
        self.assertEqual(update_latest_calls[0][2]["workspace_path"], "/tmp/demo")

    async def test_run_rebuild_flow_runs_analysis_when_changes_exist(self):
        manager = JobManager(data_dir=tempfile.mkdtemp())
        repo_key = "demo"
        job = JobState(
            job_id="job_2",
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

        save_overview_calls = []
        save_assessment_manifest_calls = []
        save_assessment_file_detail_calls = []
        save_assessment_review_state_calls = []
        update_latest_calls = []
        scheduled_steps = []

        class _FakeLoop:
            def call_soon_threadsafe(self, callback, *args):
                if len(args) >= 3:
                    scheduled_steps.append(args[2])
                callback(*args)

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

        with patch.object(manager.workspace_snapshot_service, "capture", return_value=pending_snapshot), patch(
            "app.services.jobs.manager.GraphAdapter", _FakeGraphAdapter
        ), patch(
            "app.services.jobs.manager.ChangeImpactAdapter", _FakeChangeImpactAdapter
        ), patch(
            "app.services.jobs.manager.VerificationAdapter", _FakeVerificationAdapter
        ), patch(
            "app.services.jobs.manager.ReviewGraphAdapter.build",
            return_value={"version": "v1", "summary": {"title": "workspace diff"}, "nodes": [], "edges": [], "unresolved_refs": []},
        ), patch(
            "app.services.jobs.manager.asyncio.get_running_loop", return_value=_FakeLoop()
        ), patch(
            "app.services.jobs.manager.snapshot_store.save_graph_snapshot"
        ) as save_graph_mock, patch(
            "app.services.jobs.manager.snapshot_store.save_change_analysis"
        ) as save_change_mock, patch(
            "app.services.jobs.manager.snapshot_store.save_verification"
        ) as save_verification_mock, patch(
            "app.services.jobs.manager.snapshot_store.save_review_graph"
        ) as save_review_graph_mock, patch(
            "app.services.jobs.manager.snapshot_store.save_assessment_manifest",
            side_effect=lambda repo, snapshot_id, payload, **kwargs: save_assessment_manifest_calls.append((repo, snapshot_id, payload, kwargs)),
        ), patch(
            "app.services.jobs.manager.snapshot_store.save_assessment_file_detail",
            side_effect=lambda repo, snapshot_id, file_id, payload, **kwargs: save_assessment_file_detail_calls.append((repo, snapshot_id, file_id, payload, kwargs)),
        ), patch(
            "app.services.jobs.manager.snapshot_store.save_assessment_review_state",
            side_effect=lambda repo, snapshot_id, payload, **kwargs: save_assessment_review_state_calls.append((repo, snapshot_id, payload, kwargs)),
        ), patch(
            "app.services.jobs.manager.snapshot_store.save_overview",
            side_effect=lambda repo, snapshot_id, payload, **kwargs: save_overview_calls.append((repo, snapshot_id, payload, kwargs)),
        ), patch(
            "app.services.jobs.manager.snapshot_store.update_latest_pointer",
            side_effect=lambda repo, payload, **kwargs: update_latest_calls.append((repo, payload, kwargs)),
        ):
            await manager._run_rebuild_flow(job.job_id, manager._get_repo_lock(repo_key))

        self.assertEqual(manager.job_registry[job.job_id].status, "success")
        self.assertEqual(manager.job_registry[job.job_id].workspace_snapshot_id, "ws_pending_123")
        self.assertIn("prepare_agent_context", scheduled_steps)
        self.assertIn("build_overview_payload", scheduled_steps)
        self.assertEqual(len(save_graph_mock.call_args_list), 1)
        self.assertEqual(len(save_change_mock.call_args_list), 1)
        self.assertEqual(len(save_verification_mock.call_args_list), 1)
        self.assertEqual(len(save_review_graph_mock.call_args_list), 1)
        self.assertEqual(len(save_overview_calls), 1)
        self.assertEqual(save_overview_calls[0][3]["workspace_path"], "/tmp/demo")
        self.assertEqual(len(save_assessment_manifest_calls), 1)
        self.assertEqual(save_assessment_manifest_calls[0][2]["assessment_id"], "aca_ws_pending_123")
        self.assertEqual(save_assessment_manifest_calls[0][3]["workspace_path"], "/tmp/demo")
        self.assertEqual(len(save_assessment_file_detail_calls), 1)
        self.assertEqual(save_assessment_file_detail_calls[0][4]["workspace_path"], "/tmp/demo")
        self.assertEqual(save_assessment_file_detail_calls[0][3]["file"]["path"], "app/main.py")
        self.assertEqual(len(save_assessment_review_state_calls), 1)
        self.assertEqual(save_assessment_review_state_calls[0][2]["scope"], "assessment")
        self.assertIn("agentic_change_assessment", save_overview_calls[0][2])
        self.assertTrue(update_latest_calls[0][1]["has_pending_changes"])
        self.assertEqual(update_latest_calls[0][2]["workspace_path"], "/tmp/demo")


if __name__ == "__main__":
    unittest.main()
