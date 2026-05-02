# Contributing

Thanks for helping improve `whether_commit`.

## Development Setup

Install backend dependencies:

```bash
uv sync --python 3.11 --all-groups
```

Install frontend dependencies:

```bash
cd frontend
npm ci
```

## Running Locally

Start the backend:

```bash
uv run uvicorn --app-dir backend app.main:app --reload --host 0.0.0.0 --port 8000
```

Start the frontend:

```bash
cd frontend
npm run dev
```

The frontend dev proxy currently targets `http://localhost:8088`. Use that backend port during UI development or update `frontend/vite.config.ts` locally.

## Tests and Checks

Run backend tests:

```bash
uv run pytest backend/tests/ -v
```

Run frontend checks:

```bash
cd frontend
npm run lint
npm run test
npm run build
```

## Pull Request Guidelines

- Keep changes focused on one problem.
- Add or update tests for behavior changes.
- Update docs when commands, configuration, APIs, or user workflows change.
- Do not commit secrets, local snapshots, `node_modules`, build output, or cache files.
- Include a short summary of verification commands run in the PR description.

## Local Data and Secrets

The following files and directories are local-only:

- `backend/.env.reasoning.local`
- `data/`
- `backend/data/`
- `.venv/`
- `frontend/node_modules/`
- `frontend/dist/`

Use `backend/.env.reasoning.example` as the template for optional reasoning-provider configuration.
