from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.precommit_review.verification import VerificationRunner


router = APIRouter()


class VerificationRunRequest(BaseModel):
    workspace_path: str
    snapshot_id: str
    command: str


@router.post("/run")
async def run_verification_command(request: VerificationRunRequest):
    return VerificationRunner(request.workspace_path).run(request.snapshot_id, request.command)


@router.get("/runs/{run_id}")
async def get_verification_run(run_id: str, workspace_path: str):
    run = VerificationRunner(workspace_path).get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="VERIFICATION_RUN_NOT_FOUND")
    return run
