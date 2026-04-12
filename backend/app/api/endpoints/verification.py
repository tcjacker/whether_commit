from fastapi import APIRouter, HTTPException

from app.services.snapshot_store.store import store as snapshot_store

router = APIRouter()


@router.get("")
async def get_verification_details(repo_key: str):
    """
    Get detailed verification status and signals.
    """
    latest_overview = snapshot_store.get_latest_overview(repo_key)
    if not latest_overview:
        raise HTTPException(status_code=404, detail="OVERVIEW_NOT_READY: Please trigger a rebuild first.")

    snapshot = latest_overview.get("snapshot") or {}
    snapshot_id = snapshot.get("workspace_snapshot_id")
    if not snapshot_id:
        raise HTTPException(status_code=404, detail="VERIFICATION_UNAVAILABLE: Missing workspace snapshot pointer.")

    verification_data = snapshot_store.get_verification(repo_key, snapshot_id)
    if not verification_data:
        raise HTTPException(
            status_code=404,
            detail="VERIFICATION_UNAVAILABLE: Missing verification snapshot artifact for latest snapshot.",
        )

    return verification_data
