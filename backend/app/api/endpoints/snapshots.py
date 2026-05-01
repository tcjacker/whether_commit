from __future__ import annotations

from fastapi import APIRouter

from app.services.precommit_review.builder import PrecommitReviewBuilder


router = APIRouter()


@router.get("/current")
async def get_current_snapshot(workspace_path: str):
    return PrecommitReviewBuilder(workspace_path).current()
