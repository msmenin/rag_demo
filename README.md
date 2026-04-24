# RAG Document Assistant — quick CLI

Run these from the repository root (`rag_project/`) unless noted.

## Backend (FastAPI)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --env-file backend/.env
```

If you do not have `backend/.env` yet, copy `backend/.env.example` to `backend/.env` and adjust values.

- API: http://127.0.0.1:8000
- Health: http://127.0.0.1:8000/health
- Docs: http://127.0.0.1:8000/docs

## Frontend (Next.js)

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

- App: http://localhost:3000

Use another port if 3000 is busy:

```bash
npm run dev -- --port 3001
```

`NEXT_PUBLIC_API_URL` in `.env.local` should match your API (default `http://localhost:8000`).

## Inspect documents in the database

Default SQLite file (with `DATABASE_URL=sqlite+aiosqlite:///./rag_app.db` and the server started from the repo root) is `rag_app.db` in the project root.

**List documents (SQL):**

```bash
sqlite3 rag_app.db "SELECT id, workspace_id, filename, file_size, created_at FROM documents ORDER BY created_at DESC;"
```

**List workspaces (to get IDs for the API):**

```bash
sqlite3 rag_app.db "SELECT id, created_at FROM workspaces ORDER BY created_at DESC;"
```

**List documents via API (per workspace):**

```bash
curl "http://127.0.0.1:8000/workspace/<WORKSPACE_ID>/documents/"
```

Replace `<WORKSPACE_ID>` with a UUID from the workspaces query or from `POST /workspace/`.
