from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.sessions.ws_routes import router as ws_sessions_router
import sentry_sdk
from app.config.settings import settings


try:
    sentry_sdk.init(dsn=settings.app.SENTRY_DSN_URL, send_default_pii=True)
except Exception as e:
    # Sentry is currently disabled/failing due to boot hangs, keeping it silent for now
    pass

app = FastAPI(
    title="AI Mock Interview WebSocket Service",
    description="Dedicated WebSocket service for processing real-time audio streams and AI evaluations during interviews.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
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

try:
    app.include_router(ws_sessions_router, prefix="/sessions", tags=["WebSockets"])
except Exception as e:
    import traceback
    traceback.print_exc()

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "service": "ws"}
