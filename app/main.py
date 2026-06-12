import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings

if settings.app.SENTRY_DSN_URL:
    import sentry_sdk
    sentry_sdk.init(dsn=settings.app.SENTRY_DSN_URL)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Question generation runs as an in-process background task and does not
    # survive restarts (deploys, OOM kills). Anything still marked
    # "generating" from a previous process is dead — flag it as failed so
    # users can retry instead of waiting forever.
    try:
        from sqlalchemy import update
        from app.db.models import Interview
        from app.db.session import async_session_factory

        async with async_session_factory() as db:
            result = await db.execute(
                update(Interview)
                .where(Interview.status == "generating")
                .values(status="failed")
            )
            await db.commit()
        if result.rowcount:
            logger.warning(
                "Marked %d interview(s) stuck in 'generating' as failed after restart",
                result.rowcount,
            )
    except Exception:
        logger.exception("Startup recovery of stuck interviews failed")
    yield

from app.auth.router import router as auth_router
from app.questions.routes import router as questions_router
from app.interviews.routes import router as interviews_router
from app.users.routes import router as users_router
from app.sessions.routes import router as sessions_router
from app.sessions.ws_routes import router as ws_sessions_router

app = FastAPI(
    title="AI Mock Interview API",
    description="REST API for managing AI mock interviews, questions, user authentication, and evaluation sessions.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://pet-ai-mock-interviews.netlify.app",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(questions_router, prefix="/questions", tags=["Questions"])
app.include_router(interviews_router, prefix="/interviews", tags=["Interviews"])
app.include_router(users_router, prefix="/users", tags=["Users"])
app.include_router(sessions_router, prefix="/sessions", tags=["Sessions"])
app.include_router(ws_sessions_router, prefix="/sessions", tags=["WebSockets"])


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "service": "api"}
