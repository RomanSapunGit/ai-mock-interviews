from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.users import UserCreate, UserRead, UserUpdate
from app.users import service
from app.schemas.interviews import InterviewRead

router = APIRouter()


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db_session)
):
    existing_user = await service.get_user_by_email(db, user_in.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return await service.create_user(db, user_in)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    db_user = await service.get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.put("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: UUID,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    db_user = await service.get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return await service.update_user(db, db_user, user_in)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    success = await service.delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return None


@router.get("/{user_id}/interviews", response_model=list[InterviewRead]) # Import InterviewRead if needed
async def list_user_interviews(
    user_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    return await service.list_user_interviews(db, user_id)
