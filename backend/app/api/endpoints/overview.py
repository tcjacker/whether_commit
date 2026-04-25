from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional
from app.schemas.overview import OverviewResponse, RebuildRequest, RebuildResponse
from app.services.jobs.manager import job_manager
from app.services.snapshot_store.store import store as snapshot_store

router = APIRouter()

@router.get("", response_model=OverviewResponse)
async def get_overview(
    repo_key: str, 
    workspace_snapshot_id: Optional[str] = None, 
    workspace_path: Optional[str] = None,
    use_cache: bool = True
):
    """
    Load the complete overview data for the home page.
    """
    if workspace_snapshot_id:
        overview_data = snapshot_store.get_overview(repo_key, workspace_snapshot_id, workspace_path=workspace_path)
    else:
        overview_data = snapshot_store.get_latest_overview(repo_key, workspace_path=workspace_path)

    if not overview_data:
        raise HTTPException(status_code=404, detail="OVERVIEW_NOT_READY: Please trigger a rebuild first.")

    return OverviewResponse(**overview_data)

@router.post("/rebuild", response_model=RebuildResponse)
async def trigger_rebuild(request: RebuildRequest, background_tasks: BackgroundTasks):
    """
    Trigger a rebuild process for the overview.
    Uses asyncio lock per repo to prevent concurrent builds.
    """
    try:
        job_id = await job_manager.trigger_rebuild(
            repo_key=request.repo_key,
            base_commit_sha=request.base_commit_sha,
            include_untracked=request.include_untracked,
            workspace_path=request.workspace_path
        )
        return RebuildResponse(job_id=job_id, status="pending")
    except RuntimeError as e:
        if str(e) == "REBUILD_ALREADY_RUNNING":
            raise HTTPException(status_code=409, detail="A rebuild job is already running for this repository.")
        raise HTTPException(status_code=500, detail=str(e))
