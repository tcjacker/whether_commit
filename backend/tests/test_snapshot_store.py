import tempfile
import unittest
from unittest.mock import patch

from app.services.snapshot_store.store import SnapshotStore


class SnapshotStoreTest(unittest.TestCase):
    def test_save_and_read_overview_by_snapshot_id(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = SnapshotStore(base_dir=tmp_dir)
            repo_key = "demo"
            snapshot_id = "ws_1"
            payload = {
                "repo": {"repo_key": repo_key, "name": repo_key, "default_branch": "main"},
                "snapshot": {
                    "base_commit_sha": "HEAD",
                    "workspace_snapshot_id": snapshot_id,
                    "has_pending_changes": True,
                    "status": "ready",
                    "generated_at": "2026-04-10T00:00:00Z",
                },
            }

            store.save_overview(repo_key, snapshot_id, payload)

            self.assertEqual(store.get_overview(repo_key, snapshot_id), payload)

    def test_get_latest_overview_returns_snapshot_payload(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = SnapshotStore(base_dir=tmp_dir)
            repo_key = "demo"
            snapshot_id = "ws_2"
            payload = {"repo": {"repo_key": repo_key}, "snapshot": {"workspace_snapshot_id": snapshot_id}}

            store.save_overview(repo_key, snapshot_id, payload)
            store.update_latest_pointer(repo_key, {"workspace_snapshot_id": snapshot_id})

            self.assertEqual(store.get_latest_overview(repo_key), payload)

    def test_get_latest_overview_returns_none_for_missing_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = SnapshotStore(base_dir=tmp_dir)
            repo_key = "demo"
            store.update_latest_pointer(repo_key, {"workspace_snapshot_id": "ws_missing"})

            self.assertIsNone(store.get_latest_overview(repo_key))

    def test_save_and_read_review_graph_by_snapshot_id(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = SnapshotStore(base_dir=tmp_dir)
            repo_key = "demo"
            snapshot_id = "ws_review_1"
            payload = {
                "version": "v1",
                "change_id": "chg_1",
                "summary": {"title": "workspace diff", "direct_feature_count": 1},
                "nodes": [],
                "edges": [],
                "unresolved_refs": [],
            }

            store.save_review_graph(repo_key, snapshot_id, payload)

            self.assertEqual(store.get_review_graph(repo_key, snapshot_id), payload)

    def test_get_latest_overview_isolated_by_workspace_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = SnapshotStore(base_dir=tmp_dir)
            repo_key = "demo"
            workspace_a = "/tmp/workspace-a"
            workspace_b = "/tmp/workspace-b"
            payload_a = {"repo": {"repo_key": repo_key}, "snapshot": {"workspace_snapshot_id": "ws_a"}}
            payload_b = {"repo": {"repo_key": repo_key}, "snapshot": {"workspace_snapshot_id": "ws_b"}}

            store.save_overview(repo_key, "ws_a", payload_a, workspace_path=workspace_a)
            store.save_overview(repo_key, "ws_b", payload_b, workspace_path=workspace_b)
            store.update_latest_pointer(repo_key, {"workspace_snapshot_id": "ws_a"}, workspace_path=workspace_a)
            store.update_latest_pointer(repo_key, {"workspace_snapshot_id": "ws_b"}, workspace_path=workspace_b)

            self.assertEqual(store.get_latest_overview(repo_key, workspace_path=workspace_a), payload_a)
            self.assertEqual(store.get_latest_overview(repo_key, workspace_path=workspace_b), payload_b)

    def test_get_latest_overview_prefers_resolved_workspace_bucket_over_repo_latest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = SnapshotStore(base_dir=tmp_dir)
            repo_key = "demo"
            workspace_path = "/tmp/demo"
            legacy_payload = {"repo": {"repo_key": repo_key}, "snapshot": {"workspace_snapshot_id": "ws_legacy"}}
            workspace_payload = {"repo": {"repo_key": repo_key}, "snapshot": {"workspace_snapshot_id": "ws_workspace"}}

            store.save_overview(repo_key, "ws_legacy", legacy_payload)
            store.update_latest_pointer(repo_key, {"workspace_snapshot_id": "ws_legacy"})

            store.save_overview(repo_key, "ws_workspace", workspace_payload, workspace_path=workspace_path)
            store.update_latest_pointer(repo_key, {"workspace_snapshot_id": "ws_workspace"}, workspace_path=workspace_path)

            store.update_latest_pointer(repo_key, {"workspace_snapshot_id": "ws_legacy"})

            with patch.object(store, "_resolve_default_workspace_path", return_value=workspace_path):
                self.assertEqual(store.get_latest_overview(repo_key), workspace_payload)


if __name__ == "__main__":
    unittest.main()
