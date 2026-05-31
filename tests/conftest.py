import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import NullPool

import app.db.base  # noqa: F401 — registers all models with Base
from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.models.mixins import Base

_engine = create_async_engine(settings.database_url_test, poolclass=NullPool)


@pytest.fixture(scope="session", autouse=True)
async def create_tables():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True)
async def reset_database():
    table_names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    async with _engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))


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
