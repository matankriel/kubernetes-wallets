"""Async SQLAlchemy database setup for InfraHub.

Exports:
  async_engine      -- the shared AsyncEngine instance
  AsyncSessionLocal -- sessionmaker bound to async_engine
  get_db            -- FastAPI dependency yielding an AsyncSession
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import AppSettings

settings = AppSettings()

async_engine: AsyncEngine = create_async_engine(
    settings.DB_URL,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal: sessionmaker[AsyncSession] = sessionmaker(  # type: ignore[type-arg]
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session.

    Rolls back the active transaction on any unhandled exception,
    then re-raises so the global error handler can produce a response.
    """
    async with AsyncSessionLocal() as session:
        try:
