from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class InterviewBase(BaseModel):
    title: str
    description: str | None = None
    role: str | None = None
    difficulty: str | None = None
    interview_type: str = "behavioral"

class InterviewCreate(InterviewBase):
    user_id: UUID
    status: str = "pending"

class InterviewUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    role: str | None = None
    difficulty: str | None = None
    interview_type: str | None = None
    status: str | None = None

class InterviewRead(InterviewBase):
    id: UUID
    user_id: UUID
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
