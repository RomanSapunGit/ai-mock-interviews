from uuid import UUID
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User
from app.schemas.users import UserCreate, UserUpdate
from app.interviews import service as interview_service


async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    db_user = User(**user_in.model_dump())
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def get_user(db: AsyncSession, user_id: UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def update_user(
    db: AsyncSession, db_user: User, user_in: UserUpdate
) -> User:
    update_data = user_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def delete_user(db: AsyncSession, user_id: UUID) -> bool:
    result = await db.execute(delete(User).where(User.id == user_id))
    await db.commit()
    return result.rowcount > 0


async def list_user_interviews(db: AsyncSession, user_id: UUID) -> list:
    return await interview_service.list_user_interviews(db, user_id)
