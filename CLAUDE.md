# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync --python 3.11 --all-groups

# Run the server (from repo root)
uv run uvicorn --app-dir backend app.main:app --reload --host 0.0.0.0 --port 8000

# Run all tests
uv run pytest backend/tests/ -v

# Run a single test file
uv run pytest backend/tests/test_overview_inference.py -v

# Run a specific test
uv run pytest backend/tests/test_snapshot_store.py::TestSnapshotStore::test_write_read -v
```

## Environment Configuration

LLM reasoning requires `backend/.env.reasoning.local`:
```
OBS_REASONING_PROVIDER_ENABLED=true
OBS_REASONING_PROVIDER_NAME=openai_compatible
OBS_REASONING_MODEL=qwen-plus
OBS_REASONING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
OBS_REASONING_API_KEY=<your-api-key>
OBS_REASONING_TIMEOUT_SECONDS=90
```

Settings are loaded in `backend/app/config/settings.py` via `ObservabilitySettings`. The reasoning provider is optional — the service degrades gracefully if disabled.

## Architecture

This is a FastAPI backend that analyzes a code repository's current working tree and produces an "AI Application Overview" — a synthesized snapshot of the app's structure, pending changes, and verification status.

### Request Flow

```
POST /api/overview/rebuild
  → jobs/manager.py  (background async job, 6 steps)
      1. workspace_snapshot/ — git status capture
      2. graph_adapter/      — Python AST parsing → code graph
      3. change_impact/      — git diff + diff-hunk AST → changed symbols
      4. verification/       — test/CI results aggregation
      5. overview_inference/ — synthesizes all three + calls LLM
      6. snapshot_store/     — atomic JSON write to data/

GET /api/overview?repo_key=...&workspace_snapshot_id=...
  → reads from snapshot_store/
```

### Key Services (`backend/app/services/`)

| Service | Purpose |
|---|---|
| `graph_adapter/` | Walks Python files with AST; extracts modules, symbols, routes, dependencies |
| `change_impact/` | Runs `git diff`, uses diff-hunk-aware AST to identify changed symbols and routes |
| `verification/` | Aggregates test results and CI signals; maps them to changed modules |
| `workspace_snapshot/` | Captures `git status` before analysis begins |
| `overview_inference/` | Combines graph + change + verification; calls LLM for narrative synthesis |
| `capability_inference/` | Maps technical modules to human-readable capability names |
| `jobs/` | Async background job lifecycle manager with per-repo concurrency locks |
| `snapshot_store/` | Atomic JSON read/write under `data/repos/{repo_key}/snapshots/{snapshot_id}/` |

### Data Storage Layout

No database — all persistence is local JSON files:
```
data/repos/{repo_key}/
  meta.json
  latest.json                          # pointer to most recent snapshot
  snapshots/{workspace_snapshot_id}/
    graph_snapshot.json
    change_analysis.json
    verification.json
    overview.json
  jobs/{job_id}.json
```

### API Endpoints (`backend/app/api/`)

- `GET /health`
- `GET /api/overview` — load snapshot; `POST /api/overview/rebuild` — trigger job
- `GET /api/jobs/{job_id}` — poll job status
- `GET /api/changes/latest?repo_key=...`
- `GET /api/capabilities/{capability_key}?repo_key=...`
- `GET /api/verification?repo_key=...`

### Concurrency Model

The job manager uses per-repository `asyncio.Lock` to prevent concurrent rebuilds. CPU-bound AST work can run in `ProcessPoolExecutor` with a `ThreadPoolExecutor` fallback for sandboxed environments.

### Schemas (`backend/app/schemas/`)

All API request/response shapes and internal data transfer objects are Pydantic v2 models defined here. Key types: `JobState`, `OverviewResponse`, `WorkspaceSnapshotState`, `AgentReasoning`, `ArchitectureOverview`.
