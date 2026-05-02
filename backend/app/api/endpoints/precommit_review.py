from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.services.precommit_review.builder import PrecommitReviewBuilder
from app.services.precommit_review.verification import VerificationRunner


router = APIRouter()


class WorkspaceRequest(BaseModel):
    workspace_path: str


class ReviewStateUpdateRequest(BaseModel):
    workspace_path: str
    status: str


class VerificationRunRequest(BaseModel):
    workspace_path: str
    snapshot_id: str
    command: str


def _current_or_404(workspace_path: str):
    try:
        return PrecommitReviewBuilder(workspace_path).current()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="PRECOMMIT_REVIEW_NOT_READY") from exc


@router.post("/rebuild")
async def rebuild_precommit_review(request: WorkspaceRequest):
    return PrecommitReviewBuilder(request.workspace_path).rebuild()


@router.get("/snapshots/current")
async def get_current_precommit_snapshot(workspace_path: str):
    return _current_or_404(workspace_path)


@router.get("/queue")
async def get_precommit_review_queue(workspace_path: str):
    return _current_or_404(workspace_path)


@router.get("/files")
async def get_precommit_review_files(workspace_path: str):
    return _current_or_404(workspace_path)


@router.get("/files/{file_id}")
async def get_precommit_review_file(file_id: str, workspace_path: str):
    snapshot = _current_or_404(workspace_path)
    for file in snapshot.get("files", []):
        if file.get("file_id") == file_id:
            return {
                "file": file,
                "hunks": [hunk for hunk in snapshot.get("hunks", []) if hunk.get("file_id") == file_id],
                "signals": [
                    signal
                    for signal in snapshot.get("signals", [])
                    if signal.get("target_id") in {hunk.get("hunk_id") for hunk in snapshot.get("hunks", []) if hunk.get("file_id") == file_id}
                ],
            }
    raise HTTPException(status_code=404, detail="FILE_NOT_FOUND")


@router.post("/signals/{signal_id}/state")
async def update_precommit_review_signal(signal_id: str, request: ReviewStateUpdateRequest):
    return PrecommitReviewBuilder(request.workspace_path).update_signal_state(signal_id, request.status)


@router.post("/hunks/{hunk_id}/state")
async def update_precommit_review_hunk(hunk_id: str, request: ReviewStateUpdateRequest):
    builder = PrecommitReviewBuilder(request.workspace_path)
    snapshot = builder.current()
    hunk = next((item for item in snapshot.get("hunks", []) if item.get("hunk_id") == hunk_id), None)
    if not hunk:
        raise HTTPException(status_code=404, detail="HUNK_NOT_FOUND")
    builder.state_store.update_hunk_state(hunk["hunk_carryover_key"], request.status)
    return builder.rebuild()


@router.post("/files/{file_id}/state")
async def update_precommit_review_file(file_id: str, request: ReviewStateUpdateRequest):
    builder = PrecommitReviewBuilder(request.workspace_path)
    builder.state_store.update_file_state(file_id, request.status)
    return builder.rebuild()


@router.post("/verification/run")
async def run_verification_command(request: VerificationRunRequest):
    return VerificationRunner(request.workspace_path).run(request.snapshot_id, request.command)


@router.get("/verification/runs/{run_id}")
async def get_verification_run(run_id: str, workspace_path: str):
    run = VerificationRunner(workspace_path).get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="VERIFICATION_RUN_NOT_FOUND")
    return run
