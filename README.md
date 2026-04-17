# AI Mock Interviews

A FastAPI-based backend for AI-powered mock interviews with PostgreSQL and `pgvector`.

## 🚀 Quick Start

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

## 🛠 Essential Commands

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

## 🗄 Database Info

This project uses **SQLAlchemy** with **Alembic** and **pgvector**.

- **Models**: `app/db/models.py`
- **Migrations**: `migrations/versions/`
