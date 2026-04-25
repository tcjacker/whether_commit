import tempfile
import unittest
from unittest.mock import patch

from app.services.snapshot_store.store import SnapshotStore


class SnapshotStoreTest(unittest.TestCase):
    def test_save_and_read_assessment_manifest_by_snapshot_id(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = SnapshotStore(base_dir=tmp_dir)
            payload = {
                "assessment_id": "aca_ws_1",
                "workspace_snapshot_id": "ws_1",
                "repo_key": "demo",
                "status": "ready",
                "file_list": [],
            }

            store.save_assessment_manifest("demo", "ws_1", payload)

            self.assertEqual(store.get_assessment_manifest("demo", "ws_1"), payload)

    def test_get_latest_assessment_manifest_returns_snapshot_payload(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = SnapshotStore(base_dir=tmp_dir)
            payload = {
                "assessment_id": "aca_ws_2",
                "workspace_snapshot_id": "ws_2",
                "repo_key": "demo",
                "status": "ready",
                "file_list": [],
            }

            store.save_assessment_manifest("demo", "ws_2", payload)
            store.update_latest_pointer("demo", {"workspace_snapshot_id": "ws_2"})

            self.assertEqual(store.get_latest_assessment_manifest("demo"), payload)

    def test_get_latest_assessment_manifest_returns_none_for_missing_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = SnapshotStore(base_dir=tmp_dir)
            store.update_latest_pointer("demo", {"workspace_snapshot_id": "ws_missing"})

            self.assertIsNone(store.get_latest_assessment_manifest("demo"))

    def test_save_and_read_review_graph_by_snapshot_id(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = SnapshotStore(base_dir=tmp_dir)
            payload = {
                "version": "v1",
                "change_id": "chg_1",
                "summary": {"title": "workspace diff", "direct_feature_count": 1},
                "nodes": [],
                "edges": [],
                "unresolved_refs": [],
            }

            store.save_review_graph("demo", "ws_review_1", payload)

            self.assertEqual(store.get_review_graph("demo", "ws_review_1"), payload)

    def test_get_latest_assessment_manifest_isolated_by_workspace_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = SnapshotStore(base_dir=tmp_dir)
            workspace_a = "/tmp/workspace-a"
            workspace_b = "/tmp/workspace-b"
            payload_a = {
                "assessment_id": "aca_ws_a",
                "workspace_snapshot_id": "ws_a",
                "repo_key": "demo",
                "status": "ready",
                "file_list": [],
            }
            payload_b = {
                "assessment_id": "aca_ws_b",
                "workspace_snapshot_id": "ws_b",
                "repo_key": "demo",
                "status": "ready",
                "file_list": [],
            }

            store.save_assessment_manifest("demo", "ws_a", payload_a, workspace_path=workspace_a)
            store.save_assessment_manifest("demo", "ws_b", payload_b, workspace_path=workspace_b)
            store.update_latest_pointer("demo", {"workspace_snapshot_id": "ws_a"}, workspace_path=workspace_a)
            store.update_latest_pointer("demo", {"workspace_snapshot_id": "ws_b"}, workspace_path=workspace_b)

            self.assertEqual(store.get_latest_assessment_manifest("demo", workspace_path=workspace_a), payload_a)
            self.assertEqual(store.get_latest_assessment_manifest("demo", workspace_path=workspace_b), payload_b)

    def test_get_latest_assessment_manifest_prefers_resolved_workspace_bucket_over_repo_latest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = SnapshotStore(base_dir=tmp_dir)
            workspace_path = "/tmp/demo"
            legacy_payload = {
                "assessment_id": "aca_ws_legacy",
                "workspace_snapshot_id": "ws_legacy",
                "repo_key": "demo",
                "status": "ready",
                "file_list": [],
            }
            workspace_payload = {
                "assessment_id": "aca_ws_workspace",
                "workspace_snapshot_id": "ws_workspace",
                "repo_key": "demo",
                "status": "ready",
                "file_list": [],
            }

            store.save_assessment_manifest("demo", "ws_legacy", legacy_payload)
            store.update_latest_pointer("demo", {"workspace_snapshot_id": "ws_legacy"})

            store.save_assessment_manifest("demo", "ws_workspace", workspace_payload, workspace_path=workspace_path)
            store.update_latest_pointer("demo", {"workspace_snapshot_id": "ws_workspace"}, workspace_path=workspace_path)
            store.update_latest_pointer("demo", {"workspace_snapshot_id": "ws_legacy"})

            with patch.object(store, "_resolve_default_workspace_path", return_value=workspace_path):
                self.assertEqual(store.get_latest_assessment_manifest("demo"), workspace_payload)


if __name__ == "__main__":
    unittest.main()
