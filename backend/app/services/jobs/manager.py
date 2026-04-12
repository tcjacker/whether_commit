import asyncio
import uuid
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from app.schemas.job import JobState
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

from app.services.graph_adapter.adapter import GraphAdapter
from app.services.change_impact.adapter import ChangeImpactAdapter
from app.services.verification.adapter import VerificationAdapter
from app.services.snapshot_store.store import store as snapshot_store
from app.services.workspace_snapshot.service import WorkspaceSnapshotService
from app.services.overview_inference.service import OverviewInferenceService

class JobManager:
    """
    In-memory job manager for the single-worker MVP process.
    Tracks state of background rebuilds and enforces repo-level concurrency locks.
    """
    def __init__(self, data_dir: str = "data/repos"):
        self.data_dir = data_dir
        self.job_registry: Dict[str, JobState] = {}
        # Concurrency control per repository
        self.repo_locks: Dict[str, asyncio.Lock] = {}
        self.workspace_snapshot_service = WorkspaceSnapshotService()
        self.overview_inference_service = OverviewInferenceService()
        # For CPU bound operations. Fall back cleanly in sandboxes where process pools are restricted.
        try:
            self.process_pool = ProcessPoolExecutor(max_workers=2)
        except Exception:
            self.process_pool = None
        self.thread_pool = ThreadPoolExecutor(max_workers=4)

    def _get_repo_lock(self, repo_key: str) -> asyncio.Lock:
        if repo_key not in self.repo_locks:
            self.repo_locks[repo_key] = asyncio.Lock()
        return self.repo_locks[repo_key]

    def _persist_job_state(self, job: JobState) -> None:
        """
        Write the job state to a local JSON file to ensure recovery.
        """
        job_dir = os.path.join(self.data_dir, job.repo_key, "jobs")
        os.makedirs(job_dir, exist_ok=True)
        job_file = os.path.join(job_dir, f"{job.job_id}.json")
        
        # Simple write since job status isn't as critical as overview snapshot
        with open(job_file, "w", encoding="utf-8") as f:
            if hasattr(job, "model_dump_json"):
                f.write(job.model_dump_json(indent=2))
            else:
                f.write(job.json(indent=2))

    async def trigger_rebuild(
        self,
        repo_key: str,
        base_commit_sha: str = "HEAD",
        include_untracked: bool = True,
        workspace_path: Optional[str] = None,
    ) -> str:
        """
        Start a rebuild job. Raises Exception if already running.
        If workspace_path is provided, it will analyze that absolute path instead of assuming /workspace/repos/{repo_key}
        """
        lock = self._get_repo_lock(repo_key)
        
        if lock.locked():
            raise RuntimeError("REBUILD_ALREADY_RUNNING")

        # Create job
        job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        now = datetime.now(timezone.utc)
        
        # Determine actual workspace path to analyze
        actual_workspace_path = workspace_path if workspace_path else f"/workspace/repos/{repo_key}"

        job = JobState(
            job_id=job_id,
            repo_key=repo_key,
            base_commit_sha=base_commit_sha,
            include_untracked=include_untracked,
            workspace_snapshot_id="pending",
            workspace_path=actual_workspace_path,
            status="pending",
            step="init",
            progress=0,
            message=f"Initializing rebuild job for {actual_workspace_path}",
            created_at=now,
            updated_at=now,
        )
        
        self.job_registry[job_id] = job
        self._persist_job_state(job)
        
        # Start the background async task that will hold the lock and execute the flow
        asyncio.create_task(self._run_rebuild_flow(job_id, lock))
        
        return job_id

    async def _run_rebuild_flow(self, job_id: str, lock: asyncio.Lock) -> None:
        """
        The main rebuild execution flow. Runs as a background task.
        Holds the repo lock until completion.
        """
        async with lock:
            job = self.job_registry.get(job_id)
            if not job:
                return
            
            try:
                # 1. Capture working tree
                await self._update_job_status(job, "running", "capture_working_tree", 10, "Capturing working tree snapshot...")
                workspace_snapshot = self.workspace_snapshot_service.capture(
                    repo_key=job.repo_key,
                    workspace_path=job.workspace_path,
                    base_commit_sha=job.base_commit_sha,
                    include_untracked=job.include_untracked,
                )
                job.workspace_snapshot_id = workspace_snapshot.workspace_snapshot_id
                self._persist_job_state(job)

                if not workspace_snapshot.has_pending_changes:
                    minimal_overview = self.overview_inference_service.build_clean_overview(job.repo_key, workspace_snapshot)
                    snapshot_store.save_overview(job.repo_key, job.workspace_snapshot_id, minimal_overview)
                    snapshot_store.update_latest_pointer(job.repo_key, {
                        "base_commit_sha": job.base_commit_sha,
                        "workspace_snapshot_id": job.workspace_snapshot_id,
                        "has_pending_changes": False,
                        "latest_overview_file": f"snapshots/{job.workspace_snapshot_id}/overview.json",
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    })
                    await self._update_job_status(job, "success", "done", 100, "NO_PENDING_CHANGES")
                    return

                # 2. Build graph snapshot (CPU Bound)
                await self._update_job_status(job, "running", "build_graph_snapshot", 30, "Building code graph snapshot...")
                loop = asyncio.get_running_loop()
                
                # Real integration: Call Graph Adapter
                graph_adapter = GraphAdapter(workspace_path=job.workspace_path)
                graph_executor = self.process_pool or self.thread_pool
                graph_data = await loop.run_in_executor(graph_executor, graph_adapter.generate_graph_snapshot)
                
                # Save snapshot to file system
                snapshot_store.save_graph_snapshot(job.repo_key, job.workspace_snapshot_id, graph_data)
                
                # 3. Analyze pending change (CPU Bound)
                await self._update_job_status(job, "running", "analyze_pending_change", 50, "Analyzing uncommitted diffs...")
                change_adapter = ChangeImpactAdapter(workspace_path=job.workspace_path, base_commit_sha=job.base_commit_sha)
                change_data = await loop.run_in_executor(graph_executor, change_adapter.generate_change_analysis, job.workspace_snapshot_id)
                snapshot_store.save_change_analysis(job.repo_key, job.workspace_snapshot_id, change_data)
                
                # 4. Aggregate verification (I/O Bound)
                await self._update_job_status(job, "running", "aggregate_verification", 70, "Collecting test results...")
                verification_adapter = VerificationAdapter(workspace_path=job.workspace_path)
                verification_data = await loop.run_in_executor(
                    self.thread_pool,
                    verification_adapter.aggregate_verification,
                    change_data,
                    graph_data,
                )
                snapshot_store.save_verification(job.repo_key, job.workspace_snapshot_id, verification_data)
                
                # 5. Infer overview (Mock inference based on graph_data, change_data, verification_data)
                await self._update_job_status(job, "running", "infer_overview", 90, "Inferring application overview...")
                
                overview_data = self.overview_inference_service.build_overview(
                    job.repo_key,
                    job.workspace_snapshot_id,
                    graph_data,
                    change_data,
                    verification_data,
                )
                snapshot_store.save_overview(job.repo_key, job.workspace_snapshot_id, overview_data)
                
                # Update latest pointer
                snapshot_store.update_latest_pointer(job.repo_key, {
                    "base_commit_sha": job.base_commit_sha,
                    "workspace_snapshot_id": job.workspace_snapshot_id,
                    "has_pending_changes": workspace_snapshot.has_pending_changes,
                    "latest_overview_file": f"snapshots/{job.workspace_snapshot_id}/overview.json",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })
                
                # 6. Mark success
                await self._update_job_status(job, "success", "done", 100, "Overview rebuild completed successfully.")
                
            except Exception as e:
                # Mark failure
                await self._update_job_status(job, "failed", job.step, job.progress, f"Error: {str(e)}")

    async def _update_job_status(self, job: JobState, status: str, step: str, progress: int, message: str) -> None:
        job.status = status
        job.step = step
        job.progress = progress
        job.message = message
        job.updated_at = datetime.now(timezone.utc)
        self._persist_job_state(job)

    async def get_job_state(self, job_id: str) -> Optional[JobState]:
        return self.job_registry.get(job_id)

# Global instance for the single-worker process
job_manager = JobManager()
