from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    email: EmailStr | None = None


class UserRead(UserBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
