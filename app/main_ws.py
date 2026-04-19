from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.sessions.ws_routes import router as ws_sessions_router
import sentry_sdk

from app.config.settings import settings


sentry_sdk.init(dsn=settings.app.SENTRY_DSN_URL, send_default_pii=True)

app = FastAPI(
    title="AI Mock Interview WebSocket Service",
    description="Dedicated WebSocket service for processing real-time audio streams and AI evaluations during interviews.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_sessions_router, prefix="/sessions", tags=["WebSockets"])
