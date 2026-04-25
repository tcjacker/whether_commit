import tempfile

from app.services.snapshot_store.store import SnapshotStore


def test_save_and_read_assessment_manifest_and_file_detail():
    with tempfile.TemporaryDirectory() as tmp_dir:
        store = SnapshotStore(base_dir=tmp_dir)
        repo_key = "demo"
        snapshot_id = "ws_1"
        manifest = {
            "assessment_id": "aca_ws_1",
            "workspace_snapshot_id": snapshot_id,
            "repo_key": repo_key,
            "status": "ready",
            "summary": {},
            "file_list": [{"file_id": "cf_abc123", "path": "backend/app/main.py"}],
        }
        detail = {
            "file": {"file_id": "cf_abc123", "path": "backend/app/main.py"},
            "diff_hunks": [],
        }

        store.save_assessment_manifest(repo_key, snapshot_id, manifest)
        store.save_assessment_file_detail(repo_key, snapshot_id, "cf_abc123", detail)

        assert store.get_assessment_manifest(repo_key, snapshot_id) == manifest
        assert store.get_assessment_file_detail(repo_key, snapshot_id, "cf_abc123") == detail


def test_get_latest_assessment_manifest_uses_latest_pointer():
    with tempfile.TemporaryDirectory() as tmp_dir:
        store = SnapshotStore(base_dir=tmp_dir)
        repo_key = "demo"
        snapshot_id = "ws_2"
        manifest = {
            "assessment_id": "aca_ws_2",
            "workspace_snapshot_id": snapshot_id,
            "repo_key": repo_key,
            "status": "ready",
        }

        store.save_assessment_manifest(repo_key, snapshot_id, manifest)
        store.update_latest_pointer(repo_key, {"workspace_snapshot_id": snapshot_id})

        assert store.get_latest_assessment_manifest(repo_key) == manifest
