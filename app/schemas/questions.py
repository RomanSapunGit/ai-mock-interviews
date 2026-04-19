from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class QuestionBase(BaseModel):
    text: str
    category: str | None = None
    difficulty: str | None = None
    question_type: str = "behavioral"
    starter_code: str | None = None
    examples: str | None = None
    order: int = 0


class QuestionCreate(QuestionBase):
    interview_id: UUID


class QuestionUpload(BaseModel):
    text: str
    interview_id: UUID


class QuestionDocument(BaseModel):
    page_content: str
    metadata: dict = Field(default_factory=dict)
    id: str | None = None
    score: float | None = None


class QuestionUpdate(BaseModel):
    text: str | None = None
    category: str | None = None
    difficulty: str | None = None
    question_type: str | None = None
    starter_code: str | None = None
    order: int | None = None


class QuestionRead(QuestionBase):
    id: UUID
    interview_id: UUID
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
