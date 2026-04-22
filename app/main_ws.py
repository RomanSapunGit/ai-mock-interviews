print("DEBUG: main_ws.py starting...")
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
print("DEBUG: main_ws.py imports 1 complete.")
from app.sessions.ws_routes import router as ws_sessions_router
print("DEBUG: main_ws.py imports 2 complete.")
import sentry_sdk
print("DEBUG: main_ws.py imports 3 complete.")

from app.config.settings import settings
print("DEBUG: main_ws.py settings import complete.")


print(f"DEBUG: main_ws.py Sentry DSN: {settings.app.SENTRY_DSN_URL}")
print("DEBUG: Sentry initialized (SKIPPED).")
# try:
#     sentry_sdk.init(dsn=settings.app.SENTRY_DSN_URL, send_default_pii=True)
#     print("DEBUG: Sentry initialized.")
# except Exception as e:
#     print(f"WARNING: Sentry init failed: {e}")

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

print("DEBUG: main_ws.py including routers...")
try:
    app.include_router(ws_sessions_router, prefix="/sessions", tags=["WebSockets"])
    print("DEBUG: main_ws.py routers included.")
except Exception as e:
    print(f"CRITICAL: Router inclusion failed: {e}")
    import traceback
    traceback.print_exc()

@app.get("/health", tags=["System"])
async def health_check():
    print("DEBUG: WS Health check received!")
    return {"status": "ok", "service": "ws"}

print("DEBUG: main_ws.py setup complete.")
