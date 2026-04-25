from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.schemas.assessment import AssessmentManifest, ChangedFileDetail, RebuildRequest, RebuildResponse
from app.services.agentic_change_assessment.codex_file_assessment import LocalCodexFileAssessmentAdapter
from app.services.jobs.manager import job_manager
from app.services.snapshot_store.store import store as snapshot_store


router = APIRouter()


@router.post("/rebuild", response_model=RebuildResponse)
async def trigger_assessment_rebuild(request: RebuildRequest):
    try:
        job_id = await job_manager.trigger_rebuild(
            repo_key=request.repo_key,
            base_commit_sha=request.base_commit_sha,
            include_untracked=request.include_untracked,
            workspace_path=request.workspace_path,
        )
        return RebuildResponse(job_id=job_id, status="pending")
    except RuntimeError as exc:
        if str(exc) == "REBUILD_ALREADY_RUNNING":
            raise HTTPException(status_code=409, detail="A rebuild job is already running for this repository.")
        raise HTTPException(status_code=500, detail=str(exc))


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


@router.post("/{assessment_id}/files/{file_id}/agent-assessment", response_model=ChangedFileDetail)
async def trigger_file_agent_assessment(
    repo_key: str,
    assessment_id: str,
    file_id: str,
    workspace_path: Optional[str] = None,
    language: str = "zh-CN",
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

    running_detail = dict(detail)
    running_assessment = dict(running_detail.get("file_assessment", {}))
    running_assessment.update(
        {
            "agent_status": "running",
            "agent_source": "codex",
            "unknowns": ["Codex agent assessment is running."],
        }
    )
    running_detail["file_assessment"] = running_assessment
    snapshot_store.save_assessment_file_detail(
        repo_key,
        snapshot_id,
        file_id,
        running_detail,
        workspace_path=workspace_path,
    )

    adapter = LocalCodexFileAssessmentAdapter(workspace_path=workspace_path, language=language)
    codex_assessment = await asyncio.to_thread(adapter.assess, running_detail)

    completed_detail = dict(running_detail)
    completed_assessment = dict(completed_detail.get("file_assessment", {}))
    if codex_assessment:
        completed_assessment.update(
            {
                **codex_assessment,
                "generated_by": "codex_agent",
                "agent_status": "accepted",
                "agent_source": "codex",
            }
        )
    else:
        completed_assessment.update(
            {
                "generated_by": "rules",
                "agent_status": "failed",
                "agent_source": None,
                "unknowns": ["Codex agent assessment failed or returned invalid output."],
            }
        )

    completed_detail["file_assessment"] = completed_assessment
    validated = ChangedFileDetail.model_validate(completed_detail).model_dump()
    snapshot_store.save_assessment_file_detail(
        repo_key,
        snapshot_id,
        file_id,
        validated,
        workspace_path=workspace_path,
    )
    return validated
