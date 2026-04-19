from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.questions import QuestionRead

class SessionCreate(BaseModel):
    user_id: UUID
    interview_id: UUID

class SessionRead(BaseModel):
    id: UUID
    user_id: UUID
    interview_id: UUID
    started_at: datetime | None
    ended_at: datetime | None
    score: float | None
    feedback: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AnswerCreate(BaseModel):
    question_id: UUID
    text: str

class AnswerRead(BaseModel):
    id: UUID
    session_id: UUID
    question_id: UUID
    text: str | None
    score: float | None
    ai_feedback: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class NextQuestionResponse(BaseModel):
    question: QuestionRead | None
    completed: bool
