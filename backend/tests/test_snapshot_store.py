import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
