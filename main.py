from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.questions.routes import router as questions_router
from app.interviews.routes import router as interviews_router
from app.users.routes import router as users_router
from app.sessions.routes import router as sessions_router

app = FastAPI(title="AI Mock Interview API")

# Allow CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(questions_router, prefix="/questions", tags=["questions"])
app.include_router(interviews_router, prefix="/interviews", tags=["interviews"])
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
