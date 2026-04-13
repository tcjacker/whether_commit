import subprocess
from fastapi import APIRouter, HTTPException, Query

from app.services.snapshot_store.store import store as snapshot_store

router = APIRouter()


@router.get("/latest")
async def get_latest_changes(repo_key: str):
    """
    Get the details of the latest pending changes.
    """
    latest_overview = snapshot_store.get_latest_overview(repo_key)
    if not latest_overview:
        raise HTTPException(status_code=404, detail="OVERVIEW_NOT_READY: Please trigger a rebuild first.")

    snapshot = latest_overview.get("snapshot") or {}
    snapshot_id = snapshot.get("workspace_snapshot_id")
    if not snapshot_id:
        raise HTTPException(status_code=404, detail="CHANGE_ANALYSIS_UNAVAILABLE: Missing workspace snapshot pointer.")

    change_data = snapshot_store.get_change_analysis(repo_key, snapshot_id)
    if not change_data:
        raise HTTPException(
            status_code=404,
            detail="CHANGE_ANALYSIS_UNAVAILABLE: Missing change analysis snapshot artifact for latest snapshot.",
        )

    return change_data


@router.get("/file-diff")
async def get_file_diff(
    repo_key: str,
    file_path: str = Query(..., description="Relative file path within the repo"),
):
    """
    Return unified diff for a single file (staged + unstaged changes vs HEAD).
    """
    latest_overview = snapshot_store.get_latest_overview(repo_key)
    if not latest_overview:
        raise HTTPException(status_code=404, detail="OVERVIEW_NOT_READY")

    snapshot = latest_overview.get("snapshot") or {}
    snapshot_id = snapshot.get("workspace_snapshot_id")
    change_data = snapshot_store.get_change_analysis(repo_key, snapshot_id) if snapshot_id else None
    workspace_path = (change_data or {}).get("workspace_path")

    if not workspace_path:
        raise HTTPException(status_code=404, detail="WORKSPACE_PATH_UNAVAILABLE")

    # Sanitize: file_path must not escape the workspace
    import os
    abs_file = os.path.normpath(os.path.join(workspace_path, file_path))
    if not abs_file.startswith(os.path.normpath(workspace_path)):
        raise HTTPException(status_code=400, detail="INVALID_PATH")

    try:
        # Staged diff
        staged = subprocess.run(
            ["git", "diff", "--cached", "--unified=5", "--", file_path],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            timeout=15,
        )
        # Unstaged diff
        unstaged = subprocess.run(
            ["git", "diff", "--unified=5", "--", file_path],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            timeout=15,
        )
        diff_text = (staged.stdout or "") + (unstaged.stdout or "")
        if not diff_text.strip():
            # New untracked file: show full content
            try:
                with open(abs_file, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                lines = content.splitlines()
                diff_text = f"--- /dev/null\n+++ b/{file_path}\n@@ -0,0 +1,{len(lines)} @@\n"
                diff_text += "\n".join(f"+{ln}" for ln in lines)
            except OSError:
                diff_text = ""
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="DIFF_TIMEOUT")

    return {"file_path": file_path, "diff": diff_text}
