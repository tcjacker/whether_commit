import os
import json
import uuid
import hashlib
from pathlib import Path
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

    def _normalize_workspace_path(self, workspace_path: str) -> str:
        return os.path.realpath(workspace_path).rstrip(os.sep)

    def _workspace_id(self, workspace_path: str) -> str:
        normalized = self._normalize_workspace_path(workspace_path)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]

    def _get_workspace_root(self, repo_key: str) -> str:
        return os.path.join(self._get_repo_dir(repo_key), "workspaces")

    def _get_workspace_dir(self, repo_key: str, workspace_path: Optional[str] = None, workspace_id: Optional[str] = None) -> str:
        resolved_workspace_id = workspace_id or (self._workspace_id(workspace_path) if workspace_path else None)
        if not resolved_workspace_id:
            raise ValueError("workspace_path or workspace_id is required")
        return os.path.join(self._get_workspace_root(repo_key), resolved_workspace_id)

    def _get_snapshot_dir(self, repo_key: str, snapshot_id: str, workspace_path: Optional[str] = None) -> str:
        if workspace_path:
            return os.path.join(self._get_workspace_dir(repo_key, workspace_path=workspace_path), "snapshots", snapshot_id)
        return os.path.join(self._get_repo_dir(repo_key), "snapshots", snapshot_id)

    def _assessment_dir(self, repo_key: str, snapshot_id: str, workspace_path: Optional[str] = None) -> str:
        return os.path.join(
            self._get_snapshot_dir(repo_key, snapshot_id, workspace_path=workspace_path),
            "agentic_change_assessment",
        )

    def _locate_snapshot_dir(self, repo_key: str, snapshot_id: str, workspace_path: Optional[str] = None) -> str:
        if workspace_path:
            workspace_snapshot_dir = self._get_snapshot_dir(repo_key, snapshot_id, workspace_path=workspace_path)
            if os.path.exists(workspace_snapshot_dir):
                return workspace_snapshot_dir

        legacy_snapshot_dir = self._get_snapshot_dir(repo_key, snapshot_id)
        if os.path.exists(legacy_snapshot_dir):
            return legacy_snapshot_dir

        workspaces_root = self._get_workspace_root(repo_key)
        if os.path.isdir(workspaces_root):
            for workspace_id in os.listdir(workspaces_root):
                candidate = os.path.join(workspaces_root, workspace_id, "snapshots", snapshot_id)
                if os.path.exists(candidate):
                    return candidate

        return legacy_snapshot_dir

    def _locate_assessment_dir(self, repo_key: str, snapshot_id: str, workspace_path: Optional[str] = None) -> str:
        return os.path.join(
            self._locate_snapshot_dir(repo_key, snapshot_id, workspace_path=workspace_path),
            "agentic_change_assessment",
        )

    def _workspace_latest_path(self, repo_key: str, workspace_path: str) -> str:
        return os.path.join(self._get_workspace_dir(repo_key, workspace_path=workspace_path), "latest.json")

    def _workspace_metadata_path(self, repo_key: str, workspace_path: str) -> str:
        return os.path.join(self._get_workspace_dir(repo_key, workspace_path=workspace_path), "workspace.json")

    def _default_workspace_candidates(self, repo_key: str) -> list[Path]:
        cwd = Path.cwd()
        candidates = [
            Path.home() / repo_key,
            Path("/workspace/repos") / repo_key,
            cwd / repo_key,
            cwd.parent / repo_key,
            cwd.parent.parent / repo_key,
        ]
        unique: list[Path] = []
        seen: set[str] = set()
        for candidate in candidates:
            normalized = str(candidate)
            if normalized in seen:
                continue
            seen.add(normalized)
            unique.append(candidate)
        return unique

    def _resolve_default_workspace_path(self, repo_key: str) -> Optional[str]:
        for candidate in self._default_workspace_candidates(repo_key):
            if candidate.is_dir() and (candidate / ".git").exists():
                return self._normalize_workspace_path(str(candidate))
        return None

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

    def get_change_analysis(self, repo_key: str, snapshot_id: str, workspace_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        change_path = os.path.join(self._locate_snapshot_dir(repo_key, snapshot_id, workspace_path=workspace_path), "change_analysis.json")
        return self._read_json_file(change_path)

    def get_verification(self, repo_key: str, snapshot_id: str, workspace_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        verification_path = os.path.join(self._locate_snapshot_dir(repo_key, snapshot_id, workspace_path=workspace_path), "verification.json")
        return self._read_json_file(verification_path)

    def get_review_graph(self, repo_key: str, snapshot_id: str, workspace_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        review_graph_path = os.path.join(self._locate_snapshot_dir(repo_key, snapshot_id, workspace_path=workspace_path), "review_graph.json")
        return self._read_json_file(review_graph_path)

    def get_assessment_manifest(
        self,
        repo_key: str,
        snapshot_id: str,
        workspace_path: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        path = os.path.join(
            self._locate_assessment_dir(repo_key, snapshot_id, workspace_path=workspace_path),
            "manifest.json",
        )
        return self._read_json_file(path)

    def get_assessment_file_detail(
        self,
        repo_key: str,
        snapshot_id: str,
        file_id: str,
        workspace_path: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        path = os.path.join(
            self._locate_assessment_dir(repo_key, snapshot_id, workspace_path=workspace_path),
            "changed_files",
            f"{file_id}.json",
        )
        return self._read_json_file(path)

    def get_test_management_summary(
        self,
        repo_key: str,
        snapshot_id: str,
        workspace_path: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        path = os.path.join(
            self._locate_assessment_dir(repo_key, snapshot_id, workspace_path=workspace_path),
            "test_management.json",
        )
        return self._read_json_file(path)

    def get_test_case_detail(
        self,
        repo_key: str,
        snapshot_id: str,
        test_case_id: str,
        workspace_path: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        path = os.path.join(
            self._locate_assessment_dir(repo_key, snapshot_id, workspace_path=workspace_path),
            "test_cases",
            f"{test_case_id}.json",
        )
        return self._read_json_file(path)

    def get_latest_assessment_manifest(
        self,
        repo_key: str,
        workspace_path: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        resolved_workspace_path = workspace_path or self._resolve_default_workspace_path(repo_key)
        latest_file = (
            self._workspace_latest_path(repo_key, resolved_workspace_path)
            if resolved_workspace_path
            else os.path.join(self._get_repo_dir(repo_key), "latest.json")
        )
        latest_info = self._read_json_file(latest_file)
        if not latest_info and resolved_workspace_path and workspace_path is None:
            latest_file = os.path.join(self._get_repo_dir(repo_key), "latest.json")
            latest_info = self._read_json_file(latest_file)
        if not latest_info:
            return None

        workspace_snapshot_id = latest_info.get("workspace_snapshot_id")
        if not workspace_snapshot_id:
            return None

        snapshot_workspace_path = resolved_workspace_path or latest_info.get("workspace_path")
        return self.get_assessment_manifest(repo_key, workspace_snapshot_id, workspace_path=snapshot_workspace_path)

    def save_graph_snapshot(self, repo_key: str, snapshot_id: str, data: Dict[str, Any], workspace_path: Optional[str] = None) -> None:
        path = os.path.join(self._get_snapshot_dir(repo_key, snapshot_id, workspace_path=workspace_path), "graph_snapshot.json")
        self._atomic_write(path, data)

    def save_change_analysis(self, repo_key: str, snapshot_id: str, data: Dict[str, Any], workspace_path: Optional[str] = None) -> None:
        path = os.path.join(self._get_snapshot_dir(repo_key, snapshot_id, workspace_path=workspace_path), "change_analysis.json")
        self._atomic_write(path, data)

    def save_verification(self, repo_key: str, snapshot_id: str, data: Dict[str, Any], workspace_path: Optional[str] = None) -> None:
        path = os.path.join(self._get_snapshot_dir(repo_key, snapshot_id, workspace_path=workspace_path), "verification.json")
        self._atomic_write(path, data)

    def save_review_graph(self, repo_key: str, snapshot_id: str, data: Dict[str, Any], workspace_path: Optional[str] = None) -> None:
        path = os.path.join(self._get_snapshot_dir(repo_key, snapshot_id, workspace_path=workspace_path), "review_graph.json")
        self._atomic_write(path, data)

    def save_assessment_manifest(
        self,
        repo_key: str,
        snapshot_id: str,
        data: Dict[str, Any],
        workspace_path: Optional[str] = None,
    ) -> None:
        path = os.path.join(
            self._assessment_dir(repo_key, snapshot_id, workspace_path=workspace_path),
            "manifest.json",
        )
        self._atomic_write(path, data)

    def save_assessment_file_detail(
        self,
        repo_key: str,
        snapshot_id: str,
        file_id: str,
        data: Dict[str, Any],
        workspace_path: Optional[str] = None,
    ) -> None:
        path = os.path.join(
            self._assessment_dir(repo_key, snapshot_id, workspace_path=workspace_path),
            "changed_files",
            f"{file_id}.json",
        )
        self._atomic_write(path, data)

    def save_test_management_summary(
        self,
        repo_key: str,
        snapshot_id: str,
        data: Dict[str, Any],
        workspace_path: Optional[str] = None,
    ) -> None:
        path = os.path.join(
            self._assessment_dir(repo_key, snapshot_id, workspace_path=workspace_path),
            "test_management.json",
        )
        self._atomic_write(path, data)

    def save_test_case_detail(
        self,
        repo_key: str,
        snapshot_id: str,
        test_case_id: str,
        data: Dict[str, Any],
        workspace_path: Optional[str] = None,
    ) -> None:
        path = os.path.join(
            self._assessment_dir(repo_key, snapshot_id, workspace_path=workspace_path),
            "test_cases",
            f"{test_case_id}.json",
        )
        self._atomic_write(path, data)

    def save_test_command_run_result(
        self,
        repo_key: str,
        snapshot_id: str,
        run_id: str,
        data: Dict[str, Any],
        workspace_path: Optional[str] = None,
    ) -> None:
        path = os.path.join(
            self._assessment_dir(repo_key, snapshot_id, workspace_path=workspace_path),
            "test_command_runs",
            f"{run_id}.json",
        )
        self._atomic_write(path, data)

    def save_assessment_review_state(
        self,
        repo_key: str,
        snapshot_id: str,
        data: Dict[str, Any],
        workspace_path: Optional[str] = None,
    ) -> None:
        path = os.path.join(
            self._assessment_dir(repo_key, snapshot_id, workspace_path=workspace_path),
            "review_state.json",
        )
        self._atomic_write(path, data)

    def update_latest_pointer(self, repo_key: str, latest_info: Dict[str, Any], workspace_path: Optional[str] = None) -> None:
        """
        Updates the latest.json pointer to the newly completed assessment.
        """
        payload = dict(latest_info)
        if workspace_path:
            normalized_workspace_path = self._normalize_workspace_path(workspace_path)
            payload["workspace_path"] = normalized_workspace_path
            workspace_latest_path = self._workspace_latest_path(repo_key, normalized_workspace_path)
            self._atomic_write(workspace_latest_path, payload)
            self._atomic_write(
                self._workspace_metadata_path(repo_key, normalized_workspace_path),
                {
                    "workspace_id": self._workspace_id(normalized_workspace_path),
                    "workspace_path": normalized_workspace_path,
                    "repo_key": repo_key,
                    "updated_at": payload.get("updated_at"),
                },
            )

        path = os.path.join(self._get_repo_dir(repo_key), "latest.json")
        self._atomic_write(path, payload)

# Global instance for the single-worker process
store = SnapshotStore()
