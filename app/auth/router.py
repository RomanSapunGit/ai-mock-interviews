from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.auth.service import create_access_token, hash_password, verify_password
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.users import TokenResponse, UserRead, UserRegister
from app.users.service import get_user_by_email, create_user
from app.schemas.users import UserCreate

router = APIRouter()

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserRegister, db: AsyncSession = Depends(get_db_session)):
    existing = await get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = hash_password(user_in.password)
    db_user = await create_user(db, UserCreate(email=user_in.email, hashed_password=hashed))
    token = create_access_token(db_user.id, db_user.email)
    return TokenResponse(access_token=token, token_type="bearer")

@router.post("/login", response_model=TokenResponse)
async def login(user_in: UserRegister, db: AsyncSession = Depends(get_db_session)):
    user = await get_user_by_email(db, user_in.email)
    if not user or not user.hashed_password or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token, token_type="bearer")

@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
