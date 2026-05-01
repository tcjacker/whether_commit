from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.services.precommit_review.builder import PrecommitReviewBuilder


router = APIRouter()


class WorkspaceRequest(BaseModel):
    workspace_path: str


class ReviewStateUpdateRequest(BaseModel):
    workspace_path: str
    status: str


@router.post("/rebuild")
async def rebuild_precommit_review(request: WorkspaceRequest):
    return PrecommitReviewBuilder(request.workspace_path).rebuild()


@router.get("/queue")
async def get_precommit_review_queue(workspace_path: str):
    return PrecommitReviewBuilder(workspace_path).current()


@router.get("/files")
async def get_precommit_review_files(workspace_path: str):
    return PrecommitReviewBuilder(workspace_path).current()


@router.get("/files/{file_id}")
async def get_precommit_review_file(file_id: str, workspace_path: str):
    snapshot = PrecommitReviewBuilder(workspace_path).current()
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
