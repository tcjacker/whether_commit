from fastapi import APIRouter, HTTPException

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
