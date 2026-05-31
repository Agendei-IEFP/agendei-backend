from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from typing import AsyncGenerator
from app.core.config import settings

# ── Async — FastAPI ───────────────────────────────────────────────────────
engine = create_async_engine(settings.database_url, echo=settings.env == "development")
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session

# ── Sync — Celery workers ─────────────────────────────────────────────────
sync_engine = create_engine(
    settings.database_url
        .replace("postgresql+asyncpg", "postgresql+psycopg2")
        .replace("postgresql://", "postgresql+psycopg2://"),
    echo=settings.env == "development",
    pool_pre_ping=True,
)
SyncSessionLocal = sessionmaker(sync_engine, class_=Session, expire_on_commit=False)

#
# from typing import AsyncGenerator
#
# from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
#
# from app.core.config import settings
#
# engine = create_async_engine(settings.database_url, echo=settings.env == "development")
#
# SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
#
#
# async def get_db() -> AsyncGenerator[AsyncSession, None]:
#     async with SessionLocal() as session:
#         yield session
