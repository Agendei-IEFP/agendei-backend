import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import NullPool

import app.db.base  # noqa: F401 — registers all models with Base
from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.models.mixins import Base

_engine = create_async_engine(settings.database_url_test, poolclass=NullPool)


@pytest.fixture(autouse=True)
async def reset_database():
    """Drop and recreate all tables before each test for full isolation."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
async def db_session(reset_database):
    async with _engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(conn, expire_on_commit=False, join_transaction_mode="create_savepoint")
        yield session
        await conn.rollback()


@pytest.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
