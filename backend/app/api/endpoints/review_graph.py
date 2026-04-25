from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.services.review_graph.adapter import ReviewGraphAdapter
from app.services.snapshot_store.store import store as snapshot_store

router = APIRouter()


@router.get("/latest")
async def get_latest_review_graph(repo_key: str, workspace_path: str | None = None):
    latest_overview = snapshot_store.get_latest_overview(repo_key, workspace_path=workspace_path)
    if not latest_overview:
        raise HTTPException(status_code=404, detail="OVERVIEW_NOT_READY: Please trigger a rebuild first.")

    snapshot = latest_overview.get("snapshot") or {}
    snapshot_id = snapshot.get("workspace_snapshot_id")
    if snapshot_id:
        prebuilt_review_graph = snapshot_store.get_review_graph(repo_key, snapshot_id, workspace_path=workspace_path)
        if prebuilt_review_graph:
            return prebuilt_review_graph

    change_data = snapshot_store.get_change_analysis(repo_key, snapshot_id, workspace_path=workspace_path) if snapshot_id else None
    verification_data = snapshot_store.get_verification(repo_key, snapshot_id, workspace_path=workspace_path) if snapshot_id else None
    if not change_data or not verification_data:
        raise HTTPException(
            status_code=404,
            detail="REVIEW_GRAPH_INPUT_UNAVAILABLE: Missing change analysis or verification snapshot artifact.",
        )

    repo_root = Path(__file__).resolve().parents[4]
    adapter = ReviewGraphAdapter(mapping_file=repo_root / "review_graph" / "mapping.yaml")
    return adapter.build(repo_key=repo_key, change_data=change_data, verification_data=verification_data)
