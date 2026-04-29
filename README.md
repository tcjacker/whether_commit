# backend-visiable

`backend-visiable` is a local-first code review intelligence tool. It analyzes a repository working tree, maps changed files and symbols to tests and review context, and presents an assessment UI for understanding what changed and what still needs verification.

The project has two main parts:

- `backend/`: a FastAPI service that reads a local repository, builds change and review snapshots, and stores JSON artifacts on disk.
- `frontend/`: a React + TypeScript + Vite UI for reviewing assessments, affected files, tests, and evidence.

## Current Status

This project is early-stage software. APIs, snapshot schemas, and UI flows may change between minor versions. The default setup is intended for local development and trusted repositories.

## Features

- Working-tree assessment from git status and diff data.
- Python code graph extraction through AST parsing.
- Review graph mapping for changed files, tests, and evidence.
- Optional LLM-backed reasoning for narrative assessment.
- Local JSON persistence without a database.
- React UI for assessment review and test-change navigation.

## Architecture

```text
frontend/ React UI
  -> FastAPI endpoints under /api
backend/app/
  api/                         request routing
  services/workspace_snapshot/ git status capture
  services/change_impact/      diff and changed entity extraction
  services/graph_adapter/      Python AST graph extraction
  services/review_graph/       review evidence mapping
  services/verification/       test and verification evidence
  services/snapshot_store/     local JSON persistence
```

Runtime data is written under `data/` or `backend/data/` depending on the endpoint/service path. These directories are local-only and ignored by git.

## Requirements

- Python 3.11
- [uv](https://docs.astral.sh/uv/) for Python dependency management
- Node.js 24 or newer
- npm

## Quick Start

Install backend dependencies from the repository root:

```bash
uv sync --python 3.11 --all-groups
```

Run backend tests:

```bash
uv run pytest backend/tests/ -v
```

Start the backend:

```bash
uv run uvicorn --app-dir backend app.main:app --reload --host 0.0.0.0 --port 8000
```

Install and run the frontend:

```bash
cd frontend
npm ci
npm run dev
```

By default, the Vite dev server proxies `/api` and `/health` to `http://localhost:8088`. If your backend is running on port `8000`, either start it on `8088` for frontend development or adjust `frontend/vite.config.ts`.

## Optional LLM Reasoning

LLM reasoning is optional. The backend degrades gracefully when no provider is configured.

To enable it locally:

```bash
cp backend/.env.reasoning.example backend/.env.reasoning.local
```

Then edit `backend/.env.reasoning.local` with your provider settings. Never commit local env files or API keys.

## Development Commands

Backend:

```bash
uv run pytest backend/tests/ -v
uv run pytest backend/tests/test_snapshot_store.py -v
```

Frontend:

```bash
cd frontend
npm run lint
npm run test
npm run build
```

## Security Notes

This project reads local repositories and may invoke local development tools while building assessments. Run it only against repositories you trust, and do not expose the development server to untrusted networks.

Report vulnerabilities using the process in `SECURITY.md`.

## Contributing

Contributions are welcome. Start with `CONTRIBUTING.md` for setup, testing, and pull request expectations.

## License

This project is licensed under the MIT License. See `LICENSE`.
