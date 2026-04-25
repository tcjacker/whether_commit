from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from app.schemas.assessment import AssessmentManifest, ChangedFileDetail
from app.services.snapshot_store.store import store as snapshot_store


router = APIRouter()


@router.get("/latest", response_model=AssessmentManifest)
async def get_latest_assessment(repo_key: str, workspace_path: Optional[str] = None):
    manifest = snapshot_store.get_latest_assessment_manifest(repo_key, workspace_path=workspace_path)
    if not manifest:
        raise HTTPException(status_code=404, detail="ASSESSMENT_NOT_READY: Please trigger a rebuild first.")
    return AssessmentManifest.model_validate(manifest)


@router.get("/{assessment_id}/files")
async def get_assessment_files(repo_key: str, assessment_id: str, workspace_path: Optional[str] = None):
    snapshot_id = assessment_id.removeprefix("aca_")
    manifest = snapshot_store.get_assessment_manifest(repo_key, snapshot_id, workspace_path=workspace_path)
    if not manifest:
        raise HTTPException(status_code=404, detail="ASSESSMENT_NOT_READY: Please trigger a rebuild first.")
    return {"files": manifest.get("file_list", [])}


@router.get("/{assessment_id}/files/{file_id}", response_model=ChangedFileDetail)
async def get_assessment_file_detail(
    repo_key: str,
    assessment_id: str,
    file_id: str,
    workspace_path: Optional[str] = None,
):
    snapshot_id = assessment_id.removeprefix("aca_")
    detail = snapshot_store.get_assessment_file_detail(
        repo_key,
        snapshot_id,
        file_id,
        workspace_path=workspace_path,
    )
    if not detail:
        raise HTTPException(status_code=404, detail="ASSESSMENT_FILE_NOT_FOUND")
    return ChangedFileDetail.model_validate(detail)
