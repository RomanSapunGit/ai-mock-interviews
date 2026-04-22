from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

# Defer heavy imports to speed up initial port binding on Render
def include_ws_routers(app: FastAPI):
    from app.sessions.ws_routes import router as ws_sessions_router
    app.include_router(ws_sessions_router, prefix="/sessions", tags=["WebSockets"])

include_ws_routers(app)

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "service": "ws"}
