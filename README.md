# AI Mock Interviews

A FastAPI-based backend for AI-powered mock interviews with PostgreSQL and `pgvector`.

## Quick Start

### 1. Environment Setup
Create your `.env` file (a template is provided in `.env.example`):
```bash
cp .env.example .env
```

### 2. Run with Docker (Recommended)
Build and start the full environment (API + Database):
```bash
docker compose up --build -d
```
- **API**: [http://localhost:8000](http://localhost:8000)
- **Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Essential Commands

### Dependency Management
- **Install dependencies**: `uv sync`
- **Add a package**: `uv add <package_name>`

### Application Execution
- **Run local dev server**: `uv run uvicorn main:app --reload`
- **Run with Docker**: `docker compose up -d`

### Database Migrations (Alembic)
- **Apply migrations**: `docker compose exec backend uv run alembic upgrade head`
- **Create new migration**: `docker compose exec backend uv run alembic revision --autogenerate -m "Add status column"`

---

## Database Info

This project uses **SQLAlchemy** with **Alembic** and **pgvector**.

- **Models**: `app/db/models.py`
- **Migrations**: `migrations/versions/`

---

## Project Structure

```text
ai-mock-interviews-fullstack/
├── app/                  # FastAPI Backend application
│   ├── ai/               # LLM integrations (LangChain, Prompts, Evaluators)
│   ├── auth/             # JWT authentication & password hashing
│   ├── config/           # Pydantic environment configuration
│   ├── db/               # PostgreSQL connection, Session factory, ORM Models
│   ├── interviews/       # REST endpoints for Interviews
│   ├── questions/        # REST endpoints for Questions processing
│   ├── schemas/          # Pydantic schemas formatting API input/output
│   ├── sessions/         # REST endpoints for active interview Sessions
│   └── users/            # REST endpoints for User accounts
├── frontend/             # React frontend single-page application (SPA)
│   ├── src/
│   │   ├── components/   # Reusable UI component modules (Modals, Navbars)
│   │   ├── context/      # React Context global states (AuthContext)
│   │   ├── pages/        # View routes (Dashboard, Landing, InterviewDetail)
│   │   └── services/     # Axios API logic (interviewService, login, etc)
│   └── vite.config.js    # Vite builder settings
├── migrations/           # Alembic database schema histories
├── pyproject.toml        # Python pip dependencies & uv specs
├── docker-compose.yml    # Full-stack orchestrator
├── Dockerfile            # Python backend docker image builder
└── entrypoint.sh         # Bash startup script (automates migrations + uvicorn)
```
