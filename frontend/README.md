# BookPilot frontend

Next.js 16 (App Router, Turbopack) + React 19 + Tailwind CSS 4 UI for the BookPilot FastAPI backend.
Plan → outline review → writing → QA → publishing, with a human in the loop at every step.

## Run locally

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev   # http://localhost:3000
```

`NEXT_PUBLIC_API_URL` defaults to `http://localhost:8000`. The backend must allow the frontend origin
(`CORS_ORIGINS` in the backend `.env`). AI actions return the backend's message (e.g. "OPENROUTER_API_KEY is not set")
as a toast when OpenRouter isn't configured; QA without AI, auto-fix, typographic covers and exports still work.

```bash
npm run lint
npm run build && npm start
```

## Docker

```bash
docker build --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000 -t bookpilot-frontend .
docker run -p 3000:3000 bookpilot-frontend
```

`NEXT_PUBLIC_API_URL` is inlined at build time, so rebuild the image to point it at a different API. The image uses
`output: "standalone"` and runs `node server.js`. `docker compose up` from the repo root builds it as the `frontend` service.

## Layout

- `src/app/` – routes: `/` dashboard, `/books` library, `/books/new` wizard, `/books/[id]` workspace, `/settings`
- `src/lib/api.ts` – typed API client (types mirror `app/schemas.py`), `paths` doubles as SWR keys
- `src/lib/hooks.ts` – SWR data hooks (job-aware polling), `useAction` (pending state + error toasts)
- `src/components/book/` – workspace tabs: Overview, Outline, Manuscript, Quality, Publish, Export
- `src/components/wizard/` – new book wizard steps
- `src/components/ui/` – small primitives (button, dialog, tabs, toast…)
