from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    hashed_password: str | None = None

class UserUpdate(BaseModel):
    email: EmailStr | None = None

class UserRead(UserBase):
    id: UUID
    created_at: datetime

    full_name: str | None = None
    model_config = ConfigDict(from_attributes=True)

class UserRegister(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
