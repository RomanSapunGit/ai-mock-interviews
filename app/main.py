from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


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

# Defer heavy imports to speed up initial port binding on Render
def include_routers(app: FastAPI):
    from app.auth.router import router as auth_router
    from app.questions.routes import router as questions_router
    from app.interviews.routes import router as interviews_router
    from app.users.routes import router as users_router
    from app.sessions.routes import router as sessions_router

    app.include_router(auth_router, prefix="/auth", tags=["Auth"])
    app.include_router(questions_router, prefix="/questions", tags=["Questions"])
    app.include_router(interviews_router, prefix="/interviews", tags=["Interviews"])
    app.include_router(users_router, prefix="/users", tags=["Users"])
    app.include_router(sessions_router, prefix="/sessions", tags=["Sessions"])

include_routers(app)

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "service": "api"}
