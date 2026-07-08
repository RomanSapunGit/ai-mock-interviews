# AI Mock Interviews

A full-stack platform for practicing job interviews against an AI interviewer. Create an interview for a role and difficulty, let an LLM generate the questions — optionally grounded in your own uploaded material — then run a live session where the interviewer speaks its questions aloud, listens to your spoken answers, evaluates each one, and scores the session with overall feedback.

**Stack**: FastAPI + SQLAlchemy (async) + PostgreSQL/pgvector · React + Vite SPA · LangChain for RAG · any OpenAI-compatible chat LLM (Groq by default) · Groq Whisper for transcription · Google Gemini for embeddings · edge-tts for speech.

## Features

- **Three interview types**: behavioral, verbal technical, and coding (with starter code and examples per question).
- **LLM question generation** as a background task, with the interview moving through `pending → generating → active/failed → completed`.
- **RAG from your own material**: upload PDF/TXT/Markdown; files are chunked and indexed into pgvector, and question generation retrieves from them. Uploaded material is reused for later interviews that don't provide their own.
- **Live voice sessions over WebSocket**: the server streams question text plus TTS audio; you answer by text, code, or streamed microphone audio (transcribed via Whisper). The server evaluates each answer, asks follow-up questions, gives hints on request, and finishes with an overall score and feedback.
- **JWT auth everywhere**: all REST routes and the WebSocket (via `?token=`) are authenticated, with ownership checks on interviews and sessions.

## Quick Start

### 1. Environment setup

```bash
cp .env.example .env
```

Then fill in the required keys (see [Configuration](#configuration) below). At minimum you need `GROQ_API_KEY` and `GEMINI_API_KEY`; with `DEBUG=1` a dev-only `SECRET_KEY` is used automatically.

### 2. Run with Docker (recommended)

```bash
docker compose up --build -d
```

- **Frontend**: [http://localhost:5173](http://localhost:5173) (Vite dev server with hot reload from `frontend/src`)
- **API**: [http://localhost:8000](http://localhost:8000) (also serves the WebSocket endpoint)
- **Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Postgres (pgvector)**: `localhost:5433` (published for running the dev server or Alembic from the host)

Migrations run automatically when the API container starts (`entrypoint.sh`).

## Configuration

All settings are read from the environment (`.env` locally) in `app/config/settings.py`.

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | no | Postgres URL; defaults to the local dev DB. `postgres://` and `?sslmode=require` (Render-style) are normalized for asyncpg automatically. |
| `SECRET_KEY` | prod | JWT signing key. Refuses to start unset unless `DEBUG=1`. |
| `DEBUG` | no | `1` enables the dev-only secret key fallback. |
| `GROQ_API_KEY` | yes | Used for audio transcription (Whisper), and as the default chat-LLM key. |
| `GROQ_WHISPER_MODEL` | no | Transcription model, default `whisper-large-v3-turbo`. |
| `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | no | Point the chat LLM (generation, evaluation, hints) at any OpenAI-compatible endpoint. Defaults to Groq with `llama-3.3-70b-versatile`. Example for Gemini: base URL `https://generativelanguage.googleapis.com/v1beta/openai/`, model `gemini-2.5-flash`. Transcription always stays on Groq. |
| `GEMINI_API_KEY` | yes | Embeddings for the RAG vector store ([get a key](https://aistudio.google.com/apikey)). |
| `GEMINI_EMBEDDING_MODEL` / `GEMINI_EMBEDDING_DIMENSIONS` | no | Default `gemini-embedding-001` at 768 dimensions. |
| `SENTRY_DSN_URL` | no | Enables Sentry error reporting when set. |
| `EXTERNAL_PORT_FRONTEND` | no | Host port for the frontend container, default 5173. |

The frontend reads `VITE_API_BASE_URL` and `VITE_API_WS_URL` at build time (set in `docker-compose.yml` for local dev, in Netlify for production).

## Architecture

```text
ai-mock-interviews-fullstack/
├── app/                  # FastAPI backend
│   ├── main.py           # Single entrypoint: REST + WebSocket, startup recovery of stuck generations
│   ├── ai/               # LLM layer: generator, evaluator, transcriber, tts, embeddings
│   │   └── templates/    # All prompts as markdown, per interview type
│   ├── auth/             # JWT auth, password hashing, ownership dependencies
│   ├── config/           # Environment settings, lazily-built LLM/vector-store clients
│   ├── db/               # Engine, session factory, ORM models
│   ├── interviews/       # Interview CRUD
│   ├── questions/        # Question generation + RAG file indexing
│   ├── sessions/         # Session REST + live WebSocket protocol (ws.py)
│   ├── schemas/          # Pydantic request/response schemas
│   └── users/            # Account endpoints
├── frontend/             # React SPA (Vite)
│   └── src/
│       ├── pages/        # Landing, Dashboard, CreateInterview, InterviewDetail,
│       │                 # InterviewSession (live WS UI), SessionResults
│       ├── services/     # Axios clients per backend domain
│       ├── components/   # Modals, navbars, shared UI
│       └── context/      # AuthContext
├── migrations/           # Alembic revisions
├── docker-compose.yml    # db (pgvector) + api + frontend
└── entrypoint.sh         # Migrations + uvicorn on container start
```

**Data model** (`app/db/models.py`): `User` → `Interview` → `Question` (self-referencing `parent_question_id` for AI follow-ups) and `Session` → `Answer`, with scores and feedback stored per answer and per session. RAG source chunks live only in the pgvector store (managed by langchain-postgres), not in the relational tables.

**Live session protocol**: documented in the module docstring of `app/sessions/ws.py`. Connect to `/sessions/{session_id}/ws?token=<JWT>`; JSON frames both ways plus binary frames for streamed answer audio; all outbound frames go through a single queue so concurrent producers (evaluation, TTS, next question) never interleave writes.

## Development

- **Install dependencies**: `uv sync`
- **Run the backend locally**: `uv run uvicorn app.main:app --reload` (expects Postgres from compose on port 5433, or your own via `DATABASE_URL`)
- **Apply migrations**: `docker compose exec api uv run alembic upgrade head`
- **Create a migration**: `docker compose exec api uv run alembic revision --autogenerate -m "describe change"`
- **API collection**: `insomnia_collection.yaml` covers the REST endpoints.

## Deployment

- **Backend — Render**: the Docker image runs `entrypoint.sh api`, which applies migrations and starts uvicorn on `$PORT` (default 10000). Heavy imports are deferred so the port binds before Render's health-check timeout. Set the environment variables from the table above; Render's `postgres://...?sslmode=require` URL works as-is.
- **Frontend — Netlify**: `netlify.toml` builds `frontend/` with `bun run build` and publishes `dist/`, with an SPA redirect so React Router survives refreshes. Set `VITE_API_BASE_URL` (https) and `VITE_API_WS_URL` (wss) to the Render backend.
