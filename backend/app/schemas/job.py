from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class WorkspaceSnapshotState(BaseModel):
    repo_key: str
    base_commit_sha: str
    workspace_snapshot_id: str
    has_pending_changes: bool
    changed_files: List[str] = []
    status_lines: List[str] = []
    fingerprint: str = ""

class JobState(BaseModel):
    job_id: str
    repo_key: str
    base_commit_sha: str
    include_untracked: bool = True
    workspace_snapshot_id: str
    workspace_path: Optional[str] = None  # 记录本次分析的实际本地路径
    status: str
    step: str
    progress: int
    message: str
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job_001",
                "repo_key": "shop-agent-demo",
                "base_commit_sha": "def456",
                "workspace_snapshot_id": "ws_20260406_a1b2c3",
                "status": "running",
                "step": "analyze_pending_change",
                "progress": 80,
                "message": "Analyzing uncommitted diff",
                "created_at": "2026-04-06T10:00:00Z",
                "updated_at": "2026-04-06T10:00:20Z"
            }
        }
