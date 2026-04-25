from fastapi import APIRouter, HTTPException

from app.services.snapshot_store.store import store as snapshot_store

router = APIRouter()

@router.get("/{capability_key}")
async def get_capability_detail(repo_key: str, capability_key: str, workspace_path: str | None = None):
    """
    Get capability details for the drawer view.
    """
    latest_overview = snapshot_store.get_latest_overview(repo_key, workspace_path=workspace_path)
    if not latest_overview:
        raise HTTPException(status_code=404, detail="OVERVIEW_NOT_READY: Please trigger a rebuild first.")

    capability = snapshot_store.get_latest_capability(repo_key, capability_key, workspace_path=workspace_path)
    if not capability:
        raise HTTPException(status_code=404, detail=f"CAPABILITY_NOT_FOUND: capability_key={capability_key}")

    return capability
