import os
import json
import uuid
from typing import Dict, Optional, Any

class SnapshotStore:
    """
    Manages the local file snapshots.
    Ensures atomic writes and handles reading of the latest snapshot states.
    """
    def __init__(self, base_dir: str = "data/repos"):
        self.base_dir = base_dir

    def _get_repo_dir(self, repo_key: str) -> str:
        return os.path.join(self.base_dir, repo_key)

    def _get_snapshot_dir(self, repo_key: str, snapshot_id: str) -> str:
        return os.path.join(self._get_repo_dir(repo_key), "snapshots", snapshot_id)

    def _atomic_write(self, file_path: str, data: Dict[str, Any]) -> None:
        """
        Write JSON data atomically to prevent half-written files during crashes.
        """
        tmp_path = f"{file_path}.{uuid.uuid4().hex}.tmp"
        os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
        
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        
        # Atomic rename
        os.replace(tmp_path, file_path)

    def _read_json_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        if not os.path.exists(file_path):
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_overview(self, repo_key: str, snapshot_id: str) -> Optional[Dict[str, Any]]:
        overview_path = os.path.join(self._get_snapshot_dir(repo_key, snapshot_id), "overview.json")
        return self._read_json_file(overview_path)

    def get_change_analysis(self, repo_key: str, snapshot_id: str) -> Optional[Dict[str, Any]]:
        change_path = os.path.join(self._get_snapshot_dir(repo_key, snapshot_id), "change_analysis.json")
        return self._read_json_file(change_path)

    def get_verification(self, repo_key: str, snapshot_id: str) -> Optional[Dict[str, Any]]:
        verification_path = os.path.join(self._get_snapshot_dir(repo_key, snapshot_id), "verification.json")
        return self._read_json_file(verification_path)

    def get_latest_overview(self, repo_key: str) -> Optional[Dict[str, Any]]:
        latest_file = os.path.join(self._get_repo_dir(repo_key), "latest.json")
        latest_info = self._read_json_file(latest_file)
        if not latest_info:
            return None

        workspace_snapshot_id = latest_info.get("workspace_snapshot_id")
        if not workspace_snapshot_id:
            return None

        return self.get_overview(repo_key, workspace_snapshot_id)

    def get_latest_capability(self, repo_key: str, capability_key: str) -> Optional[Dict[str, Any]]:
        overview = self.get_latest_overview(repo_key)
        if not overview:
            return None
        for capability in overview.get("capability_map", []):
            if capability.get("capability_key") == capability_key:
                return capability
        return None

    def save_graph_snapshot(self, repo_key: str, snapshot_id: str, data: Dict[str, Any]) -> None:
        path = os.path.join(self._get_snapshot_dir(repo_key, snapshot_id), "graph_snapshot.json")
        self._atomic_write(path, data)

    def save_change_analysis(self, repo_key: str, snapshot_id: str, data: Dict[str, Any]) -> None:
        path = os.path.join(self._get_snapshot_dir(repo_key, snapshot_id), "change_analysis.json")
        self._atomic_write(path, data)

    def save_verification(self, repo_key: str, snapshot_id: str, data: Dict[str, Any]) -> None:
        path = os.path.join(self._get_snapshot_dir(repo_key, snapshot_id), "verification.json")
        self._atomic_write(path, data)

    def save_overview(self, repo_key: str, snapshot_id: str, data: Dict[str, Any]) -> None:
        path = os.path.join(self._get_snapshot_dir(repo_key, snapshot_id), "overview.json")
        self._atomic_write(path, data)

    def update_latest_pointer(self, repo_key: str, latest_info: Dict[str, Any]) -> None:
        """
        Updates the latest.json pointer to the newly completed overview.
        """
        path = os.path.join(self._get_repo_dir(repo_key), "latest.json")
        self._atomic_write(path, latest_info)

# Global instance for the single-worker process
store = SnapshotStore()
