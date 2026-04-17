from __future__ import annotations

from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.config.settings import settings

# Session factory – reused across the app lifetime
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=settings.db.get_engine(),
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
