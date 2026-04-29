# backend-visiable frontend

React + TypeScript + Vite UI for reviewing repository change assessments.

## Commands

Install dependencies:

```bash
npm ci
```

Start the dev server:

```bash
npm run dev
```

Run checks:

```bash
npm run lint
npm run test
npm run build
```

## Backend Proxy

The Vite dev server proxies `/api` and `/health` to `http://localhost:8088` by default. Start the FastAPI backend on that port for local UI development or adjust `vite.config.ts`.
