from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.users import UserRead, UserUpdate
from app.users import service
from app.schemas.interviews import InterviewRead

router = APIRouter()

# User creation happens exclusively through /auth/register so passwords are
# always hashed server-side; there is intentionally no public POST /users.

def _require_self(user_id: UUID, current_user: User) -> None:
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
):
    _require_self(user_id, current_user)
    return current_user

@router.put("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: UUID,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    _require_self(user_id, current_user)
    return await service.update_user(db, current_user, user_in)

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    _require_self(user_id, current_user)
    await service.delete_user(db, user_id)
    return None

@router.get("/{user_id}/interviews", response_model=list[InterviewRead])
async def list_user_interviews(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    _require_self(user_id, current_user)
    return await service.list_user_interviews(db, user_id)
