from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.schemas.assessment import (
    AssessmentManifest,
    ChangedFileDetail,
    RebuildRequest,
    RebuildResponse,
    TestCaseDetail,
    TestManagementSummary,
    TestResultAnalysis,
)
from app.services.agentic_change_assessment.codex_file_assessment import LocalCodexFileAssessmentAdapter
from app.services.jobs.manager import job_manager
from app.services.snapshot_store.store import store as snapshot_store
from app.services.test_management.codex_result_analysis import LocalCodexTestResultAnalysisAdapter
from app.services.test_management.command_runner import (
    CommandValidationError,
    analyze_stored_test_result,
    analyze_test_result,
    run_test_command,
)


router = APIRouter()


def _empty_test_management_summary(repo_key: str, assessment_id: str) -> TestManagementSummary:
    return TestManagementSummary(
        assessment_id=assessment_id,
        repo_key=repo_key,
        changed_test_file_count=0,
        test_case_count=0,
        evidence_grade_counts={},
        command_status_counts={},
        files=[],
        unknowns=[],
    )


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


@router.get("/{assessment_id}/tests", response_model=TestManagementSummary)
async def get_assessment_tests(repo_key: str, assessment_id: str, workspace_path: Optional[str] = None):
    snapshot_id = assessment_id.removeprefix("aca_")
    summary = snapshot_store.get_test_management_summary(repo_key, snapshot_id, workspace_path=workspace_path)
    if not summary:
        manifest = snapshot_store.get_assessment_manifest(repo_key, snapshot_id, workspace_path=workspace_path)
        if not manifest:
            raise HTTPException(status_code=404, detail="ASSESSMENT_NOT_READY: Please trigger a rebuild first.")
        return _empty_test_management_summary(repo_key, assessment_id)
    return TestManagementSummary.model_validate(summary)


@router.get("/{assessment_id}/tests/{test_case_id}", response_model=TestCaseDetail)
async def get_assessment_test_case(
    repo_key: str,
    assessment_id: str,
    test_case_id: str,
    workspace_path: Optional[str] = None,
):
    snapshot_id = assessment_id.removeprefix("aca_")
    detail = snapshot_store.get_test_case_detail(
        repo_key,
        snapshot_id,
        test_case_id,
        workspace_path=workspace_path,
    )
    if not detail:
        raise HTTPException(status_code=404, detail="TEST_CASE_NOT_FOUND")
    return TestCaseDetail.model_validate(detail)


@router.post("/{assessment_id}/tests/{test_case_id}/commands/{command_id}/run")
async def run_assessment_test_command(
    repo_key: str,
    assessment_id: str,
    test_case_id: str,
    command_id: str,
    workspace_path: Optional[str] = None,
):
    if not workspace_path:
        raise HTTPException(status_code=400, detail="workspace_path is required for command execution")
    snapshot_id = assessment_id.removeprefix("aca_")
    detail = snapshot_store.get_test_case_detail(
        repo_key,
        snapshot_id,
        test_case_id,
        workspace_path=workspace_path,
    )
    if not detail:
        raise HTTPException(status_code=404, detail="TEST_CASE_NOT_FOUND")

    command = next(
        (item for item in detail.get("recommended_commands", []) if item.get("command_id") == command_id),
        None,
    )
    if not command:
        raise HTTPException(status_code=404, detail="TEST_COMMAND_NOT_FOUND")

    run_id = f"tcr_{uuid.uuid4().hex[:12]}"
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        result = await asyncio.to_thread(run_test_command, command.get("command", ""), workspace_path)
    except CommandValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    finished_at = datetime.now(timezone.utc).isoformat()
    analysis_payload = analyze_test_result(
        command=command.get("command", ""),
        run_result=result,
        workspace_path=workspace_path,
        focused_scenarios=detail.get("covered_scenarios", []),
    )
    payload = {
        "run_id": run_id,
        "source": "rerun",
        "command_id": command_id,
        "command": command.get("command", ""),
        "started_at": started_at,
        "finished_at": finished_at,
        "captured_at": finished_at,
        "executed_cases": analysis_payload["executed_cases"],
        "analysis": {
            "summary": analysis_payload["summary"],
            "scenarios": analysis_payload["scenarios"],
            "test_data": analysis_payload["test_data"],
            "covered_code_analysis": analysis_payload.get("covered_code_analysis", []),
            "coverage_gaps": analysis_payload["coverage_gaps"],
            "source": analysis_payload["source"],
            "basis": analysis_payload["basis"],
        },
        "evidence_grade": analysis_payload["evidence_grade"],
        **result,
    }
    snapshot_store.save_test_command_run_result(
        repo_key,
        snapshot_id,
        run_id,
        payload,
        workspace_path=workspace_path,
    )

    command["status"] = result["status"]
    command["last_run_id"] = run_id
    detail["test_case"]["last_status"] = result["status"] if result["status"] in {"passed", "failed"} else "unknown"
    detail.setdefault("test_results", [])
    detail["test_results"] = [payload, *detail["test_results"][:4]]
    snapshot_store.save_test_case_detail(
        repo_key,
        snapshot_id,
        test_case_id,
        detail,
        workspace_path=workspace_path,
    )

    summary = snapshot_store.get_test_management_summary(repo_key, snapshot_id, workspace_path=workspace_path)
    if summary:
        status_counts: dict[str, int] = {}
        for file in summary.get("files", []):
            for test_case in file.get("test_cases", []):
                if test_case.get("test_case_id") == test_case_id:
                    test_case["last_status"] = detail["test_case"]["last_status"]
                file_status = "unknown"
                if any(case.get("test_case_id") == test_case_id for case in file.get("test_cases", [])):
                    file_status = result["status"]
                    file["latest_command_status"] = result["status"]
                status_counts[file_status] = status_counts.get(file_status, 0) + 1
        summary["command_status_counts"] = status_counts
        snapshot_store.save_test_management_summary(repo_key, snapshot_id, summary, workspace_path=workspace_path)

    return payload


@router.post("/{assessment_id}/tests/{test_case_id}/results/{run_id}/analyze", response_model=TestResultAnalysis)
async def analyze_assessment_test_result(
    repo_key: str,
    assessment_id: str,
    test_case_id: str,
    run_id: str,
    workspace_path: Optional[str] = None,
    language: str = "zh-CN",
):
    snapshot_id = assessment_id.removeprefix("aca_")
    detail = snapshot_store.get_test_case_detail(
        repo_key,
        snapshot_id,
        test_case_id,
        workspace_path=workspace_path,
    )
    if not detail:
        raise HTTPException(status_code=404, detail="TEST_CASE_NOT_FOUND")

    result = next((item for item in detail.get("test_results", []) if item.get("run_id") == run_id), None)
    if not result:
        raise HTTPException(status_code=404, detail="TEST_RESULT_NOT_FOUND")

    adapter = LocalCodexTestResultAnalysisAdapter(workspace_path=workspace_path, language=language)
    analysis = await asyncio.to_thread(adapter.analyze, detail=detail, result=result)
    if not analysis:
        analysis = analyze_stored_test_result(detail=detail, result=result)
        analysis["basis"] = ["rule_fallback", *analysis.get("basis", [])]
        analysis.setdefault("coverage_gaps", [])
        analysis["coverage_gaps"] = [
            "Codex Agent analysis failed or returned invalid output.",
            *analysis["coverage_gaps"],
        ]
    result["analysis"] = analysis
    snapshot_store.save_test_case_detail(
        repo_key,
        snapshot_id,
        test_case_id,
        TestCaseDetail.model_validate(detail).model_dump(),
        workspace_path=workspace_path,
    )
    return TestResultAnalysis.model_validate(analysis)


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
