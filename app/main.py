from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.questions.routes import router as questions_router
from app.interviews.routes import router as interviews_router
from app.users.routes import router as users_router
from app.sessions.routes import router as sessions_router
from app.auth.router import router as auth_router
import sentry_sdk

from app.config.settings import settings


print(f"DEBUG: main.py Sentry DSN: {settings.app.SENTRY_DSN_URL}")
print("DEBUG: Sentry initialized (SKIPPED).")
# try:
#     sentry_sdk.init(dsn=settings.app.SENTRY_DSN_URL, send_default_pii=True)
#     print("DEBUG: Sentry initialized.")
# except Exception as e:
#     print(f"WARNING: Sentry init failed: {e}")

app = FastAPI(
    title="AI Mock Interview API",
    description="REST API for managing AI mock interviews, questions, user authentication, and evaluation sessions.",
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

print("DEBUG: main.py including routers...")
try:
    app.include_router(auth_router, prefix="/auth", tags=["Auth"])
    app.include_router(questions_router, prefix="/questions", tags=["Questions"])
    app.include_router(interviews_router, prefix="/interviews", tags=["Interviews"])
    app.include_router(users_router, prefix="/users", tags=["Users"])
    app.include_router(sessions_router, prefix="/sessions", tags=["Sessions"])
    print("DEBUG: main.py routers included.")
except Exception as e:
    print(f"CRITICAL: Router inclusion failed: {e}")
    import traceback
    traceback.print_exc()

@app.get("/health", tags=["System"])
async def health_check():
    print("DEBUG: Health check received!")
    return {"status": "ok", "service": "api"}

print("DEBUG: main.py setup complete.")
