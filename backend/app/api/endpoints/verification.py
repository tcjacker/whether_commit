import asyncio
import subprocess
import time
from fastapi import APIRouter, HTTPException

from app.schemas.overview import RunVerificationRequest, RunVerificationResponse
from app.services.snapshot_store.store import store as snapshot_store

router = APIRouter()


@router.get("")
async def get_verification_details(repo_key: str, workspace_path: str | None = None):
    """
    Get detailed verification status and signals.
    """
    latest_overview = snapshot_store.get_latest_overview(repo_key, workspace_path=workspace_path)
    if not latest_overview:
        raise HTTPException(status_code=404, detail="OVERVIEW_NOT_READY: Please trigger a rebuild first.")

    snapshot = latest_overview.get("snapshot") or {}
    snapshot_id = snapshot.get("workspace_snapshot_id")
    if not snapshot_id:
        raise HTTPException(status_code=404, detail="VERIFICATION_UNAVAILABLE: Missing workspace snapshot pointer.")

    verification_data = snapshot_store.get_verification(repo_key, snapshot_id, workspace_path=workspace_path)
    if not verification_data:
        raise HTTPException(
            status_code=404,
            detail="VERIFICATION_UNAVAILABLE: Missing verification snapshot artifact for latest snapshot.",
        )

    return verification_data


@router.post("/run", response_model=RunVerificationResponse)
async def run_verification(req: RunVerificationRequest):
    """
    Run the test suite for the given workspace and return a summary.
    Executes pytest (or falls back to python -m pytest) with a 5-minute timeout.
    """
    import os
    workspace_path = req.workspace_path

    if not os.path.isdir(workspace_path):
        raise HTTPException(status_code=400, detail="WORKSPACE_NOT_FOUND: workspace_path does not exist.")

    start_ms = int(time.monotonic() * 1000)

    try:
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    ["python3", "-m", "pytest", "--tb=no", "-q", "--no-header"],
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=300,
                ),
            ),
            timeout=310,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="TEST_TIMEOUT: Test run exceeded 5 minutes.")

    duration_ms = int(time.monotonic() * 1000) - start_ms
    output = result.stdout + result.stderr

    # Parse pytest summary line: "X passed, Y failed in Zs"
    passed = 0
    total = 0
    import re
    m = re.search(r"(\d+) passed", output)
    if m:
        passed = int(m.group(1))
    m_fail = re.search(r"(\d+) failed", output)
    failed = int(m_fail.group(1)) if m_fail else 0
    total = passed + failed

    status = "passed" if result.returncode == 0 else "failed"
    detail_line = output.strip().splitlines()[-1] if output.strip() else ""

    return RunVerificationResponse(
        status=status,
        passed=passed,
        total=total,
        duration_ms=duration_ms,
        detail=detail_line[:200],
    )
