from fastapi import APIRouter, HTTPException
from typing import Optional
from app.schemas.job import JobState
from app.services.jobs.manager import job_manager

router = APIRouter()

@router.get("/{job_id}", response_model=JobState)
async def get_job_status(job_id: str):
    """
    Poll the job status by its ID.
    """
    job = await job_manager.get_job_state(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.get("/{job_id}/stream")
async def stream_job_status(job_id: str):
    """
    SSE stream for job progress. (Phase 2 or later)
    """
    # TODO: Implement SSE logic using EventSourceResponse
    raise HTTPException(status_code=501, detail="SSE streaming not implemented yet")
